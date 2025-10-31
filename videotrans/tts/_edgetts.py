import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
import functools
import aiohttp
from edge_tts import Communicate
from edge_tts.exceptions import NoAudioReceived

from videotrans.configure import config
from videotrans.configure.config import tr,logs
from videotrans.tts._base import BaseTTS

# edge-tts 限流，可能产生大量超时、401等错误
from videotrans.util import tools

MAX_CONCURRENT_TASKS = 6
RETRY_NUMS = 3
RETRY_DELAY = 3
POLL_INTERVAL = 0.1
SIGNAL_TIMEOUT = 2 # 发给UI界面的信号，超时2秒，以防UI卡顿
SAVE_TIMEOUT = 30  # edge_tts可能限流超时，超过30s就认定失败，防止无限挂起

@dataclass
class EdgeTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self._stop_event = asyncio.Event()
        self.ends_counter = 0
        self.lock = asyncio.Lock()
        # 默认跟随设置使用代理，如果不想使用，单独根目录下创建 edgetts-noproxy.txt 文件
        self.useproxy=None if not self.proxy_str or Path(f'{config.ROOT_DIR}/edgetts-noproxy.txt').exists() else self.proxy_str
        

    def _exit(self):
        if config.exit_soft or (config.current_status != 'ing' and config.box_tts != 'ing' and not self.is_test):
            return True
        return False

    async def increment_counter(self):
        async with self.lock:
            self.ends_counter += 1

    async def _create_audio_with_retry(self, item, index, total_tasks, semaphore):

        task_id = f" [{index + 1}/{total_tasks}]"
        if not item.get('text','').strip() or tools.vail_file(item['filename']):
            await self.increment_counter()
            return
        
        try:
            async with semaphore:
                
                if self._stop_event.is_set():
                    return
                msg=""
                for attempt in range(RETRY_NUMS):
                    if self._stop_event.is_set():
                        return
                    
                    try:
                        logs(f"{task_id}: 开始第 {attempt + 1} 次尝试。")
                        if attempt>0:
                            msg= f'Retry after {attempt}nd  '
                        # print(f'{self.useproxy=}')
                        communicate = Communicate(
                            item['text'], voice=item['role'], rate=self.rate,
                            volume=self.volume, proxy=self.useproxy, pitch=self.pitch, connect_timeout=5
                        )
                        # 防止WebSocket连接或数据读取无限挂起
                        await asyncio.wait_for(
                            communicate.save(item['filename'] + ".mp3"),
                            timeout=SAVE_TIMEOUT
                        )
                        

                        if self._stop_event.is_set(): return
                        loop = asyncio.get_running_loop()
                        signal_with_args = functools.partial(
                            self._signal, 
                            text=f'{tr("kaishipeiyin")} {msg}[{self.ends_counter + 1}/{total_tasks}]'
                        )
                        
                        try:
                            await asyncio.wait_for(
                                loop.run_in_executor(None, signal_with_args),
                                timeout=SIGNAL_TIMEOUT
                            )
                        except asyncio.TimeoutError:
                            logs(f"{task_id}: 发送 UI 信号超时！",level='warn')

                        logs(f"{task_id}: 成功。")
                        return

                    except asyncio.TimeoutError as e:
                        logs(f"{task_id}: 第 {attempt + 1} 次尝试超时 (SAVE_TIMEOUT={SAVE_TIMEOUT}s)",level='warn')
                        if attempt < RETRY_NUMS - 1:
                            await asyncio.sleep(RETRY_DELAY)
                        else:
                            logs(f"{task_id}: 已达到最大重试次数，任务失败 (超时)。",level='warn')
                            self.error=e
                            # 失败也是一种完成，直接返回
                            return
                    except (NoAudioReceived, aiohttp.ClientError) as e:
                        self.error=e if not self.useproxy else f'proxy={self.useproxy}, {tr("Please turn off the clear proxy and try again")}:{e}'
                        logs(f"{task_id}: 第 {attempt + 1} 次尝试失败，{self.useproxy=} : {e}",level='warn')
                        # 强制禁用代理重试
                        self.useproxy=None
                        if attempt < RETRY_NUMS - 1:
                            await asyncio.sleep(RETRY_DELAY)
                        else:
                            logs(f"{task_id}: 已达到最大重试次数，任务失败。",level='warn')
                            # 失败也是一种完成，直接返回
                            return

        except asyncio.CancelledError as e:
            logs(f"{task_id}: 被 cancel() 强制中断。")
            self.error=e
        except Exception as e:
            logs(f"{task_id}: 发生未知严重错误，任务终止。", level="except")
            self.error=e
        finally:
            # 无论成功、失败、取消还是异常，都在这里统一增加计数
            await self.increment_counter()
            logs(f'[任务:{index+1} 彻底结束, 当前总完成数: {self.ends_counter}]')

    async def watchdog(self, tasks):
        """看门狗"""
        await self._stop_event.wait()
        logs("看门狗：检测到停止信号！正在取消所有任务...")
        for task in tasks:
            task.cancel()

    async def _exit_monitor(self):
        """退出监控器"""
        while not self._exit():
            if self._stop_event.is_set():
                break
            await asyncio.sleep(POLL_INTERVAL)
        if self._exit():
            logs("监控器：检测到 self._exit() 为 True，正在设置停止事件...")
            self._stop_event.set()
    
    async def _exec(self) -> None:

        if not self.queue_tts:
            return
        
        self._stop_event.clear()
        total_tasks = len(self.queue_tts)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

        worker_tasks = [
            asyncio.create_task(
                self._create_audio_with_retry(item, i, total_tasks, semaphore)
            )
            for i, item in enumerate(self.queue_tts)
        ]

        if not worker_tasks:
            return

        monitor_task = asyncio.create_task(self._exit_monitor())
        watchdog_task = asyncio.create_task(self.watchdog(worker_tasks))
        
        all_workers_done = asyncio.gather(*worker_tasks, return_exceptions=True)
        
        # 为整体等待添加超时，防止无限挂起（例如所有任务都超时但未取消）
        try:
            done, pending = await asyncio.wait(
                [all_workers_done, monitor_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=total_tasks * SAVE_TIMEOUT * 2  # 总任务 * 每个超时 * 2（缓冲）
            )
        except asyncio.TimeoutError:
            logs("整体执行超时！强制取消所有任务。",level='warn')
            self._stop_event.set()
            done, pending = await asyncio.wait([all_workers_done, monitor_task], return_when=asyncio.ALL_COMPLETED)
        
        try:
            if monitor_task in done:
                logs("执行流程：由“退出监控器”触发终止。")
            else:
                logs("执行流程：所有配音任务正常完成。")
                monitor_task.cancel()

            watchdog_task.cancel()
            for task in pending:
                task.cancel()
            
            await asyncio.gather(all_workers_done, monitor_task, watchdog_task, return_exceptions=True)
            
            final_count = self.ends_counter
            if final_count != total_tasks:
                logs(
                    f"!!!!!!!!!!!!!!!!!! 任务计数不匹配 !!!!!!!!!!!!!!!!!!"
                    f"预期任务数: {total_tasks}, 实际完成数: {final_count}."
                    f"丢失了 {total_tasks - final_count} 个任务的状态。"
                    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
                    level="error"
                )
            else:
                logs(f"所有 {total_tasks} 个任务的状态已确认。")
            
            
            # ======== 转换wav阶段 ========
            from videotrans.util import tools
            ok, err = 0, 0
            for i, item in enumerate(self.queue_tts):
                if config.exit_soft:
                    return
                mp3_path = item['filename'] + ".mp3"
                if tools.vail_file(mp3_path):
                    ok += 1
                else:
                    err += 1

            if ok>0:
                all_task = []
                from concurrent.futures import ThreadPoolExecutor
                self._signal(text=f'convert wav {total_tasks}')
                with ThreadPoolExecutor(max_workers=min(12,len(self.queue_tts),os.cpu_count())) as pool:
                    for item in self.queue_tts:
                        mp3_path = item['filename'] + ".mp3"
                        if tools.vail_file(mp3_path):
                            all_task.append(pool.submit(self.convert_to_wav, mp3_path,item['filename']))
                    if len(all_task) > 0:
                        _ = [i.result() for i in all_task]

            if err > 0:
                msg=f'[{err}] subtitle dubbing errors, {ok} successes'
                self._signal(text=msg)
                logs(f'EdgeTTS ended: {msg}')
        finally:
            await asyncio.sleep(0.1)
