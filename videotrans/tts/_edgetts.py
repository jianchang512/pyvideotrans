import asyncio
from dataclasses import dataclass
from pathlib import Path

import aiohttp
from edge_tts import Communicate
from edge_tts.exceptions import NoAudioReceived

from videotrans.configure import config
from videotrans.tts._base import BaseTTS

# --- 常量定义 ---
# 最大并发数，可以根据需要调整，或者放入配置文件
MAX_CONCURRENT_TASKS = int(float(config.settings.get('dubbing_thread', 5)))
# 单个任务的最大重试次数
RETRY_NUMS = 3
# 重试前的等待时间（秒）
RETRY_DELAY = 5


@dataclass
class EdgeTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        found_proxy = None
        proxy_file = Path(config.ROOT_DIR) / 'edgetts.txt'
        if proxy_file.is_file():
            try:
                proxy_str = proxy_file.read_text(encoding='utf-8').strip()
                if proxy_str:  # 确保文件不是空的
                    found_proxy = 'http://' + proxy_str
                    config.logger.info(f"从 {proxy_file} 加载代理: {found_proxy}")
            except:
                pass

        if not found_proxy:
            pro = self._set_proxy(type='set')
            if pro:
                found_proxy = pro
                config.logger.info(f"使用系统设置的代理: {found_proxy}")

        if found_proxy:
            self.proxies = found_proxy

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
            config.logger.info(
                f"[Edge-TTS]配音 [{index + 1}/{total_tasks}]: {self.rate=},{self.volume=},{self.pitch=}, {item['text']}")

            for attempt in range(RETRY_NUMS):
                try:
                    communicate = Communicate(
                        item['text'],
                        voice=item['role'],
                        rate=self.rate,
                        volume=self.volume,
                        proxy=self.proxies,
                        pitch=self.pitch
                    )
                    await communicate.save(item['filename'] + ".mp3")
                    self.convert_to_wav(item['filename'] + ".mp3", item['filename'])

                    # 成功后，更新进度并立即返回
                    if self.inst:
                        # 基于完成比例的精确进度更新
                        # (index + 1) 表示当前是第几个任务
                        progress = ((index + 1) / total_tasks) * 80
                        if progress > self.inst.precent:
                            self.inst.precent = progress

                    self._signal(text=f'{config.transobj["kaishipeiyin"]} [{index + 1}/{total_tasks}]')
                    config.logger.info(f"[Edge-TTS]配音 [{index + 1}/{total_tasks}] 成功.")
                    return  # 成功，退出函数

                except (NoAudioReceived, aiohttp.ClientError) as e:
                    config.logger.warning(
                        f"[Edge-TTS]配音 [{index + 1}/{total_tasks}] 第 {attempt + 1}/{RETRY_NUMS} 次尝试失败: {e}. "
                        f"{RETRY_DELAY} 秒后重试..."
                    )
                    config.logger.error(f"[Edge-TTS]配音 [{index + 1}/{total_tasks}] 在 {RETRY_NUMS} 次尝试后最终失败。")
                    self.error = str(e)
                    self._signal(text=f"{item.get('line', '')} retry {attempt}: " + self.error)
                    await asyncio.sleep(RETRY_DELAY)
                except Exception as e:
                    # 捕获其他未知异常
                    config.logger.exception(e, exc_info=True)
                    self.error = str(e.args)
                    self._signal(text=f"{item.get('line', '')} retry {attempt}: " + self.error)
                    await asyncio.sleep(RETRY_DELAY)

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
    async def _exec(self) -> None:
        if self._exit():
            return
        await self._task_queue()
