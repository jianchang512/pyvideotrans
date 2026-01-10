# stt项目识别接口
import json
import re, os, requests
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.process import paraformer, funasr_mlt
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


@dataclass
class FunasrRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()

    # 获取进度
    def _process(self, logs_file):
        last_mtime = 0
        while 1:
            _p = Path(logs_file)
            if _p.is_file() and _p.stat().st_mtime != last_mtime:
                last_mtime = _p.stat().st_mtime
                _tmp = json.loads(_p.read_text(encoding='utf-8'))
                self._signal(text=_tmp.get('text'), type=_tmp.get('type', 'logs'))
                if _tmp.get('type', '') == 'error':
                    return
            time.sleep(0.5)

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        if self.model_name == 'paraformer-zh' and self.detect_language[:2].lower() not in ['zh', 'en']:
            self.model_name = 'FunAudioLLM/Fun-ASR-MLT-Nano-2512' if self.detect_language[:2] not in ['zh','en','ja','yu'] else 'FunAudioLLM/Fun-ASR-Nano-2512'
        elif self.model_name == 'SenseVoiceSmall':
            self.model_name = 'iic/SenseVoiceSmall'
        elif self.model_name == 'Fun-ASR-Nano-2512':
            if self.detect_language[:2] not in ['zh', 'en', 'ja', 'yu']:
                self.model_name = f'FunAudioLLM/Fun-ASR-MLT-Nano-2512'
            else:
                self.model_name = f'FunAudioLLM/Fun-ASR-Nano-2512'
        elif self.model_name != 'paraformer-zh':
            self.model_name = f'FunAudioLLM/Fun-ASR-MLT-Nano-2512'

        self._signal(text=f"load {self.model_name}")

        logs_file = f'{config.TEMP_DIR}/{self.uuid}/funasr-{self.detect_language}-{time.time()}.log'
        kwars = {
            "cut_audio_list": self.cut_audio() if self.model_name != 'paraformer-zh' else None,
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "ROOT_DIR": config.ROOT_DIR,
            "logs_file": logs_file,
            "defaulelang": config.defaulelang,
            "is_cuda": self.is_cuda,
            "audio_file": self.audio_file,
            "TEMP_ROOT": config.TEMP_ROOT,
            "max_speakers": self.max_speakers,
            "cache_folder": self.cache_folder

        }
        # 获取进度
        threading.Thread(target=self._process, args=(logs_file,), daemon=True).start()
        raws = []
        with ProcessPoolExecutor(max_workers=1) as executor:
            # 提交任务，并显式传入参数，确保子进程拿到正确的参数
            future = executor.submit(
                paraformer if self.model_name == 'paraformer-zh' else funasr_mlt,
                **kwars
            )
            raws = future.result()
        if isinstance(raws,str):
            raise RuntimeError(raws)
        return raws
