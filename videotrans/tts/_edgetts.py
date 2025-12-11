import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import functools
import aiohttp
from videotrans.util import tools
from edge_tts import Communicate
from edge_tts.exceptions import NoAudioReceived

from videotrans.configure import config
from videotrans.configure.config import tr,logs
from videotrans.tts._base import BaseTTS

# edge-tts 限流，可能产生大量超时、401等错误

MAX_CONCURRENT_TASKS = int(config.settings.get('edgetts_max_concurrent_tasks',10))
RETRY_NUMS = int(config.settings.get('edgetts_retry_nums',3))+1
RETRY_DELAY = 5
POLL_INTERVAL = 0.1
SIGNAL_TIMEOUT = 2 # 发给UI界面的信号，超时2秒，以防UI卡顿
SAVE_TIMEOUT = 30  # edge_tts可能限流超时，超过30s就认定失败，防止无限挂起

    

# 用于多进程转换
def _convert_to_wav(mp3_file_path, output_wav_file_path):
    cmd = [
        "-y",
        "-i",
        mp3_file_path,
        "-ar",
        "48000",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        output_wav_file_path
    ]
    try:
        tools.runffmpeg(cmd, force_cpu=True)
    except Exception:
        pass
    return True

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
        # 根据角色名获取真实 配音所需的角色
        task_id = f" [{index + 1}/{total_tasks}]"
        if not item.get('text','').strip() or tools.vail_file(item['filename']):
            await self.increment_counter()
            return
        
        try:
            async with semaphore:
                
                if self._stop_event.is_set():
                    return
                msg=""
                for attempt in range(RETRY_NUMS+1):
                    if self._stop_event.is_set():
                        return
                    
                    try:
                        
                        if attempt>0:
                            msg= f'Retry after {attempt}nd  '
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

                        return

                    except asyncio.TimeoutError as e:
                        if attempt < RETRY_NUMS:
                            await asyncio.sleep(RETRY_DELAY)
                        else:
                            logs(f"EdgeTTS配音: 已达到最大重试次数，任务失败 (超时)。",level='error')
                            self.error=e
                            # 失败也是一种完成，直接返回
                            return
                    except (NoAudioReceived, aiohttp.ClientError) as e:
                        self.error=e if not self.useproxy else f'proxy={self.useproxy}, {tr("Please turn off the clear proxy and try again")}:{e}'
                        # 强制禁用代理重试
                        self.useproxy=None
                        if attempt < RETRY_NUMS:
                            await asyncio.sleep(RETRY_DELAY)
                        else:
                            logs(f"{task_id}: 已达到最大重试次数，任务失败。",level='error')
                            # 失败也是一种完成，直接返回
                            return

        except asyncio.CancelledError as e:
            self.error=e
        except Exception as e:
            logs(f"{task_id}: 发生未知严重错误，任务终止。", level="except")
            self.error=e
        finally:
            # 无论成功、失败、取消还是异常，都在这里统一增加计数
            await self.increment_counter()

    async def watchdog(self, tasks):
        """看门狗"""
        await self._stop_event.wait()
        for task in tasks:
            task.cancel()

    async def _exit_monitor(self):
        """退出监控器"""
        while not self._exit():
            if self._stop_event.is_set():
                break
            await asyncio.sleep(POLL_INTERVAL)
        if self._exit():
            self._stop_event.set()
    
    async def _exec(self) -> None:

        if not self.queue_tts:
            return
        
        logs(f'本次EdgeTTS配音：重试延迟:{RETRY_DELAY},出错将重试:{RETRY_NUMS},并发:{MAX_CONCURRENT_TASKS}')
        
        self._stop_event.clear()
        total_tasks = len(self.queue_tts)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        for it in self.queue_tts:
            it['role']=tools.get_edge_rolelist(it['role'],self.language)

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
            logs("整体执行超时！强制取消所有任务。",level='error')
            self._stop_event.set()
            done, pending = await asyncio.wait([all_workers_done, monitor_task], return_when=asyncio.ALL_COMPLETED)
        
        try:
            if monitor_task not in done:
                logs("执行流程：所有配音任务结束。")
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
                with ProcessPoolExecutor(max_workers=min(12,len(self.queue_tts),os.cpu_count())) as pool:
                    for item in self.queue_tts:
                        mp3_path = item['filename'] + ".mp3"
                        if tools.vail_file(mp3_path):
                            all_task.append(pool.submit(_convert_to_wav, mp3_path,item['filename']))
                    completed_tasks = 0
                    for task in all_task:
                        try:
                            task.result()  # 等待任务完成
                            completed_tasks += 1
                            self._signal( text=f"convert wav [{completed_tasks}/{total_tasks}]" )
                        except Exception as e:
                            logs(f"Task {completed_tasks + 1} failed with error: {e}", level="except")
                    
            if err > 0:
                msg=f'[{err}] errors, {ok} succeed'
                self._signal(text=msg)
                logs(f'EdgeTTS配音结束：{msg}')
        finally:
            await asyncio.sleep(0.1)
