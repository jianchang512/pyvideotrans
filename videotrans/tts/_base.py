import asyncio
import base64
import copy
import inspect
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.configure._except import DubbSrtError
from videotrans.util import tools


@dataclass
class BaseTTS(BaseCon):
    queue_tts: Optional[List[Dict[str, Any]]] = field(default=None, repr=False)
    language: Optional[str] = None
    inst: Optional[Any] = None  # inst 类型未知，使用 Any
    uuid: Optional[str] = None
    play: bool = False
    is_test: bool = False

    volume: str = field(default='+0%', init=False)
    rate: str = field(default='+0%', init=False)
    pitch: str = field(default='+0Hz', init=False)

    len: int = field(init=False)
    has_done: int = field(default=0, init=False)
    proxies: Optional = field(default=None, init=False)
    copydata: List = field(default_factory=list, init=False)
    wait_sec: float = field(init=False)
    dub_nums: int = field(init=False)
    error: str = field(default='', init=False)
    api_url: str = field(default='', init=False)

    def __post_init__(self):
        super().__init__()

        if not self.queue_tts:
            raise Exception("No data")

        self.len = len(self.queue_tts)
        self.queue_tts = copy.deepcopy(self.queue_tts)

        self.wait_sec = float(config.settings.get('dubbing_wait', 0))
        self.dub_nums = int(float(config.settings.get('dubbing_thread', 1))) if self.len > 1 else 1

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
            text = re.sub(r'\[?spk\-?\d{1,}\]', '', it.get('text', '').strip(), re.I)
            if normalizer:
                text = normalizer(text)
            if not text:
                # 移除该条目
                self.queue_tts.pop(i)
            else:
                self.queue_tts[i]['text'] = text

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
        Path(config.TEMP_HOME).mkdir(parents=True, exist_ok=True)
        self._signal(text="")
        if len(self.queue_tts) < 1:
            raise RuntimeError('没有需要配音的字幕' if config.defaulelang == 'zh' else 'No subtitles required')
        try:
            # 检查 self._exec 是不是一个异步函数 (coroutine)
            if inspect.iscoroutinefunction(self._exec):
                # 如果是异步函数，我们需要一个事件循环来运行它
                try:
                    # 尝试获取当前线程正在运行的事件循环
                    loop = asyncio.get_running_loop()
                except:
                    # 如果没有，说明在同步环境中，使用 asyncio.run()
                    asyncio.run(self._exec())
                else:
                    # 如果有，就在现有循环上运行它并等待完成
                    loop.run_until_complete(self._exec())
            else:
                # 可能调用多线程，此时无法捕获异常
                self._exec()
        except Exception as e:
            raise DubbSrtError(f'{e}:{self.__class__.__name__}') from e
        finally:
            if self.shound_del:
                self._set_proxy(type='del')

        # 是否播放
        if self.play:
            if tools.vail_file(self.queue_tts[0]['filename']):
                threading.Thread(target=tools.pygameaudio, args=(self.queue_tts[0]['filename'],)).start()
                return
            raise DubbSrtError((self.error if self.error else "Test Error") + self.__class__.__name__)

        # 记录成功数量
        succeed_nums = 0
        for it in self.queue_tts:
            if it['text'].strip() and tools.vail_file(it['filename']):
                succeed_nums += 1
        # 只有全部配音都失败，才视为失败
        if succeed_nums < 1:
            msg = ('配音全部失败 ' if config.defaulelang == 'zh' else 'Dubbing failed ') + self.error
            self._signal(text=msg, type="error")
            raise DubbSrtError(f'{msg}:{self.__class__.__name__}')

        self._signal(
            text=f"配音成功{succeed_nums}个，失败 {len(self.queue_tts) - succeed_nums}个" if config.defaulelang == 'zh' else f"Dubbing succeeded {succeed_nums}，failed {len(self.queue_tts) - succeed_nums}")
        # 去除末尾静音
        if config.settings['remove_silence']:
            for it in self.queue_tts:
                if tools.vail_file(it['filename']):
                    tools.remove_silence_from_end(it['filename'])

    # 用于除  edge-tts 之外的渠道，在此进行单或多线程气动。调用 _item_task
    # exec->_local_mul_thread->item_task
    def _local_mul_thread(self) -> None:
        if self._exit():
            return
        if self.api_url and len(self.api_url) < 10:
            raise RuntimeError(
                f'{self.__class__.__name__} API 接口不正确，请到设置中重新填写' if config.defaulelang == 'zh' else 'clone-voice API interface is not correct, please go to Settings to fill in again')

        # 只有全部配音都失败，才视为失败，因此拦截 _item_task 的所有异常
        if len(self.queue_tts) == 1 or self.dub_nums == 1:
            for k, item in enumerate(self.queue_tts):
                if k > 0:
                    time.sleep(self.wait_sec)
                # 屏蔽异常，其他继续
                try:
                    self._item_task(item)
                except Exception as e:
                    self.error = str(e)
            return

        all_task = []
        with ThreadPoolExecutor(max_workers=self.dub_nums) as pool:
            for k, item in enumerate(self.queue_tts):
                all_task.append(pool.submit(self._item_task, item))
            _ = [i.result() for i in all_task]

    # 实际业务逻辑 子类实现 在此创建线程池，或单线程时直接创建逻辑
    def _exec(self) -> None:
        pass

    # 每条字幕任务，由线程池调用 data_item 是 queue_tts 中每个元素
    def _item_task(self, data_item: Union[Dict, List, None]) -> Union[bool, None]:
        pass

    def _base64_to_audio(self, encoded_str: str, output_path: str) -> None:
        if not encoded_str:
            raise ValueError("Base64 encoded string is empty.")
        # 如果存在data前缀，则按照前缀中包含的音频格式保存为转换格式
        if encoded_str.startswith('data:audio/'):
            output_ext = Path(output_path).suffix.lower()[1:]
            mime_type, encoded_str = encoded_str.split(',', 1)  # 提取 Base64 数据部分
            # 提取音频格式 (例如 'mp3', 'wav')
            audio_format = mime_type.split('/')[1].split(';')[0].lower()
            support_format = {
                "mpeg": "mp3",
                "wav": "wav",
                "ogg": "ogg",
                "aac": "aac"
            }
            base64data_ext = support_format.get(audio_format, "")
            if base64data_ext and base64data_ext != output_ext:
                # 格式不同需要转换格式
                # 将base64编码的字符串解码为字节
                wav_bytes = base64.b64decode(encoded_str)
                # 将解码后的字节写入文件
                with open(output_path + f'.{base64data_ext}', "wb") as wav_file:
                    wav_file.write(wav_bytes)

                tools.runffmpeg([
                    "-y", "-i", output_path + f'.{base64data_ext}', "-b:a", "128k", output_path
                ])
                return
        # 将base64编码的字符串解码为字节
        wav_bytes = base64.b64decode(encoded_str)
        # 将解码后的字节写入文件
        with open(output_path, "wb") as wav_file:
            wav_file.write(wav_bytes)

    def _audio_to_base64(self, file_path: str) -> Union[None, str]:
        if not file_path or not Path(file_path).exists():
            return None
        with open(file_path, "rb") as wav_file:
            wav_content = wav_file.read()
            base64_encoded = base64.b64encode(wav_content)
            return base64_encoded.decode("utf-8")

    def _exit(self):
        if config.exit_soft or (config.current_status != 'ing' and config.box_tts != 'ing' and not self.is_test):
            return True
        return False
