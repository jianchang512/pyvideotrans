import asyncio
import threading
import time, re
from pathlib import Path
import aiohttp
from edge_tts.exceptions import NoAudioReceived
from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from edge_tts import Communicate

# --- 常量定义 ---
# 最大并发数，可以根据需要调整，或者放入配置文件
MAX_CONCURRENT_TASKS = int(float(config.settings.get('dubbing_thread', 5)))
# 单个任务的最大重试次数
MAX_RETRIES = 3
# 重试前的等待时间（秒）
RETRY_DELAY = 5


class EdgeTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 将代理设置逻辑统一到 __init__ 中
        self.proxies = None
        # 优先从 edgetts.txt 文件读取代理
        proxy_file = Path(config.ROOT_DIR) / 'edgetts.txt'
        if proxy_file.is_file():
            try:
                self.proxies = 'http://' + proxy_file.read_text(encoding='utf-8').strip()
                config.logger.info(f"从 {proxy_file} 加载代理: {self.proxies}")
            except Exception as e:
                config.logger.error(f"从 {proxy_file} 加载代理失败: {e}")

        # 如果文件代理不存在，则使用父类设置的代理
        if not self.proxies:
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = pro
                config.logger.info(f"使用系统设置的代理: {self.proxies}")

    async def _create_audio_with_retry(self, item, index, total_tasks, semaphore):
        """
        为一个字幕条目创建音频，包含并发控制、延时和重试逻辑。
        """
        # 使用 aenter/aexit 语法来优雅地处理信号量
        async with semaphore:
            # 增加请求前的延时，防止请求过于频繁
            # 使用 await asyncio.sleep() 避免阻塞事件循环
            if self.wait_sec > 0:
                await asyncio.sleep(self.wait_sec)

            # 移除可能存在的说话人标签
            text_to_speak = re.sub(r'\[?spk\-?\d{1,2}\]','',item['text'].strip(),re.I)
            config.logger.info(f"开始处理任务 [{index + 1}/{total_tasks}]: {text_to_speak}")

            for attempt in range(MAX_RETRIES):
                try:
                    communicate = Communicate(
                        text_to_speak,
                        voice=item['role'],
                        rate=self.rate,
                        volume=self.volume,
                        proxy=self.proxies,
                        pitch=self.pitch
                    )
                    await communicate.save(item['filename'])

                    # 成功后，更新进度并立即返回
                    if self.inst:
                        # 基于完成比例的精确进度更新
                        # (index + 1) 表示当前是第几个任务
                        progress = ((index + 1) / total_tasks) * 80
                        if progress > self.inst.precent:
                            self.inst.precent = progress

                    self._signal(text=f'{config.transobj["kaishipeiyin"]} [{index + 1}/{total_tasks}]')
                    config.logger.info(f"任务 [{index + 1}/{total_tasks}] 成功.")
                    return # 成功，退出函数

                except (NoAudioReceived, aiohttp.ClientError) as e:
                    config.logger.warning(
                        f"任务 [{index + 1}/{total_tasks}] 第 {attempt + 1}/{MAX_RETRIES} 次尝试失败: {e}. "
                        f"{RETRY_DELAY} 秒后重试..."
                    )
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        # 所有重试均失败，记录严重错误并抛出异常
                        config.logger.error(f"任务 [{index + 1}/{total_tasks}] 在 {MAX_RETRIES} 次尝试后最终失败。")
                        # 向上抛出异常，由 asyncio.gather 捕获
                        raise Exception(f"配音失败，请检查网络或代理设置: {e}") from e
                except Exception as e:
                    # 捕获其他未知异常
                    config.logger.exception(e, exc_info=True)
                    raise Exception(f"异步合成时发生未知错误: {e}") from e


    async def _task_queue(self):
        """
        创建并并发执行所有配音任务。
        """
        if not self.queue_tts:
            return

        total_tasks = len(self.queue_tts)
        # 创建一个信号量，限制同时运行的任务不超过 MAX_CONCURRENT_TASKS 个
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

        # 为队列中的每个项目创建一个异步任务
        tasks = [
            asyncio.create_task(
                self._create_audio_with_retry(item, i, total_tasks, semaphore)
            )
            for i, item in enumerate(self.queue_tts)
        ]

        # 并发运行所有任务，并等待它们全部完成
        # return_exceptions=False 表示任何一个任务失败，gather会立即抛出该异常
        try:
            await asyncio.gather(*tasks)
            config.logger.info("所有配音任务已成功完成。")
        except Exception as e:
            # 如果 gather 中有任务失败，异常会在这里被捕获
            # 取消所有其他尚未完成的任务，避免不必要的继续执行
            for task in tasks:
                if not task.done():
                    task.cancel()
            # 向上抛出异常，以便外部调用者（如 run 方法）可以捕获它
            raise e
        finally:
            print('配音完毕')


    # 执行入口，外部会调用该方法
    def _exec(self) -> None:
        if self._exit():
            return

        try:
            # asyncio.run 会自动管理事件循环的创建和销毁
            asyncio.run(self._task_queue())
        except Exception as e:
            # 将异步世界中的异常传递到同步世界
            config.logger.error(f"配音主流程发生错误: {e}")
            # 这里可以直接 raise，让外部的 run 方法的 try-except 块来处理
            raise