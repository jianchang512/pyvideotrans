import asyncio
import base64
import copy
import inspect
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from tenacity import RetryError

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.configure.config import tr,logs

from videotrans.util import tools

"""
edge-tts 当前线程中async异步任务
其他渠道多线程执行
self.error中可能是异常对象或字符串

run->exec->[local_mutli]->item_task

"""


@dataclass
class BaseTTS(BaseCon):
    # 配音渠道
    tts_type:int=0
    # 存放字幕信息队列
    queue_tts: List[Dict[str, Any]] = field(default_factory=list, repr=False)
    # queue_tts 数量
    len: int = field(init=False)
    # 语言代码
    language: Optional[str] = None
    # 唯一uid
    uuid: Optional[str] = None
    # 是否立即播放
    play: bool = False
    # 是否测试
    is_test: bool = False

    # 音量 音速 音调，默认 edge-tts格式
    volume: str = field(default='+0%', init=False)
    rate: str = field(default='+0%', init=False)
    pitch: str = field(default='+0Hz', init=False)

    # 是否完成
    has_done: int = field(default=0, init=False)

    # 每次任务后暂停时间
    wait_sec: float = float(config.settings.get('dubbing_wait', 0))
    # 并发线程数量
    dub_nums: int = int(float(config.settings.get('dubbing_thread', 1)))
    # 存放消息
    error: Optional[Any] = None
    # 配音api地址
    api_url: str = field(default='', init=False)

    def __post_init__(self):
        super().__post_init__()
        if not self.queue_tts:
            raise RuntimeError(tr("No subtitles required"))

        self.len = len(self.queue_tts)
        self.queue_tts = copy.deepcopy(self.queue_tts)
        self._cleantts()

    def _cleantts(self):
        normalizer = None
        if self.language[:2] == 'zh':
            from videotrans.util.cn_tn import TextNorm
            normalizer = TextNorm(to_banjiao=True)
        elif self.language[:2] == 'en':
            from videotrans.util.en_tn import EnglishNormalizer
            normalizer = EnglishNormalizer()
        for i, it in enumerate(self.queue_tts):
            text = it.get('text', '').strip()
            if text and normalizer:
                self.queue_tts[i]['text'] = normalizer(text)

        if "volume" in self.queue_tts[0]:
            self.volume = self.queue_tts[0]['volume']
        if "rate" in self.queue_tts[0]:
            self.rate = self.queue_tts[0]['rate']
        if "pitch" in self.queue_tts[0]:
            self.pitch = self.queue_tts[0]['pitch']

        if re.match(r'^\d+(\.\d+)?%$', self.rate):
            self.rate = f'+{self.rate}'
        if re.match(r'^\d+(\.\d+)?%$', self.volume):
            self.volume = f'+{self.volume}'
        if re.match(r'^\d+(\.\d+)?Hz$', self.pitch, re.I):
            self.pitch = f'+{self.pitch}'

        if not re.match(r'^[+-]\d+(\.\d+)?%$', self.rate):
            self.rate = '+0%'
        if not re.match(r'^[+-]\d+(\.\d+)?%$', self.volume):
            self.volume = '+0%'
        if not re.match(r'^[+-]\d+(\.\d+)?Hz$', self.pitch, re.I):
            self.pitch = '+0Hz'
        self.pitch = self.pitch.replace('%', '')

    # 入口 调用子类 _exec() 然后创建线程池调用 _item_task 或直接在 _exec 中实现逻辑
    # 若捕获到异常，则直接抛出  出错时发送停止信号
    # run->exec->_local_mul_thread->item_task
    # run->exec->item_task
    def run(self) -> None:
        if self._exit(): return
        Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        self._signal(text="")
        loop=None
        try:
            # 检查 self._exec 是不是一个异步函数 (coroutine)
            if inspect.iscoroutinefunction(self._exec):
                # 如果是异步函数，我们需要一个事件循环来运行它
                try:
                    # 尝试获取当前线程正在运行的事件循环
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # 如果没有，这是最常见的情况：在一个新线程中运行异步代码
                    # 我们将手动创建并管理循环，以确保优雅关闭
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # 运行主任务
                    loop.run_until_complete(self._exec())
                else:
                    # 如果有，就在现有循环上运行它并等待完成
                    loop.run_until_complete(self._exec())
            else:
                # 可能调用多线程，此时无法捕获异常
                self._exec()
        except RuntimeError as e:
            # 这个捕获现在更有意义，因为它可能捕获到循环相关的错误
            logs(f'TTS 线程运行时发生错误: {e}',level='warn')
            if 'Event loop is closed' in str(e):
                logs("捕获到 'Event loop is closed' 错误，这通常是关闭时序问题。",level='warn')
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception:
            raise
        finally:
            # 只有当 self._exec 是异步函数时，我们才需要处理事件循环
            if inspect.iscoroutinefunction(self._exec) and loop and not loop.is_closed():
                logs("开始执行事件循环的关闭流程...")
                try:
                    # 步骤 1: 取消所有剩余的任务
                    tasks = asyncio.all_tasks(loop=loop)
                    for task in tasks:
                        task.cancel()

                    # 步骤 2: 聚合所有任务，等待它们完成取消
                    group = asyncio.gather(*tasks, return_exceptions=True)
                    loop.run_until_complete(group)
                    import gc
                    gc.collect()
                    loop.run_until_complete(asyncio.sleep(0))
                    # 步骤 3: 关闭异步生成器
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception as e:
                    logs(f"在关闭事件循环时发生错误: {e}", level="except")
                finally:
                    # 步骤 4: 最终关闭事件循环
                    logs("事件循环已关闭。")
                    loop.close()

        # 试听或测试时播放
        if self.play:
            if tools.vail_file(self.queue_tts[0]['filename']):
                tools.pygameaudio(self.queue_tts[0]['filename'])
                return
            raise self.error if isinstance(self.error,Exception)  else RuntimeError(str(self.error))

        # 记录成功数量
        succeed_nums = 0
        for it in self.queue_tts:
            if not it['text'].strip() or tools.vail_file(it['filename']):
                succeed_nums += 1
        # 只有全部配音都失败，才视为失败
        if succeed_nums < 1:
            if config.exit_soft: return
            if isinstance(self.error,Exception):
                raise self.error
            raise RuntimeError((tr("Dubbing failed"))+str(self.error))

        self._signal(
            text=tr("Dubbing succeeded {}，failed {}",succeed_nums,len(self.queue_tts) - succeed_nums))


    # 用于除  edge-tts 之外的渠道，在此进行单或多线程气动。调用 _item_task
    # exec->_local_mul_thread->item_task
    def _local_mul_thread(self) -> None:
        if self._exit(): return

        # 单个字幕行，无需多线程
        if len(self.queue_tts) == 1 or self.dub_nums == 1:
            for k, item in enumerate(self.queue_tts):
                if not item.get('text'):
                    continue
                try:
                    self._item_task(item)
                except Exception as e:
                    self.error = e
                finally:
                    self._signal(text=f'TTS[{k+1}/{self.len}]')
                time.sleep(self.wait_sec)
            return

        all_task = []
        with ThreadPoolExecutor(max_workers=self.dub_nums) as pool:
            for k, item in enumerate(self.queue_tts):
                if not item.get('text'):
                    continue
                all_task.append(pool.submit(self._item_task, item))

            completed_tasks = 0
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                finally:
                    self._signal(text=f"TTS: [{completed_tasks}/{self.len}] ...")
    # 实际业务逻辑 子类实现 在此创建线程池，或单线程时直接创建逻辑
    def _exec(self) -> None:
        pass

    # 每条字幕任务，由线程池调用 data_item 是 queue_tts 中每个元素
    def _item_task(self, data_item: Union[Dict, List, None]) -> Union[bool, None]:
        pass


    def _exit(self):
        if config.exit_soft or (config.current_status != 'ing' and config.box_tts != 'ing' and not self.is_test):
            return True
        return False
