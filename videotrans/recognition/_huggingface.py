import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Union

from pydub import AudioSegment

from videotrans.configure.config import ROOT_DIR, logger, settings
from videotrans.configure import config
from videotrans.configure.excepts import SpeechToTextError
from videotrans.process import faster_whisper, pipe_asr,glmasr_asr
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools


@dataclass
class HuggingfaceRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.local_dir = f'{ROOT_DIR}/models/models--' + self.model_name.replace('/', '--')
        self.signal(text=f"use {self.model_name}")
        self.audio_duration=len(AudioSegment.from_wav(self.audio_file))

    def _download(self):
        tools.check_and_down_hf(self.model_name,self.model_name,self.local_dir,callback=self._process_callback)

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        self.signal(text=f"loading {self.model_name}")
        logger.debug(f'[HuggingfaceRecogn]_exec:{self.model_name=}')

        result = self._pipe_asr()
        if result:
            return result
        raise SpeechToTextError(f'No recognition results found:{self.model_name}')

    def _pipe_asr(self)->Union[List[SrtItem], None]:
        # 1. 准备数据
        title=f"load {self.model_name}"
        self.signal(text=title)
        logs_file = f'{config.TEMP_DIR}/{self.uuid}/huggingface-pipeasr-{self.detect_language}-{time.time()}.log'
        cut_audio_list_file = f'{config.TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'
        Path(cut_audio_list_file).write_text(json.dumps([ asdict(item) for item in self.cut_audio()]),encoding='utf-8')
        kwargs = {
            "cut_audio_list": cut_audio_list_file,
            "prompt": settings.get(
                f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "audio_file": None,
            "local_dir": self.local_dir,
            "jianfan": self.jianfan
        }
        raws=self._new_process(callback=pipe_asr if self.model_name!='zai-org/GLM-ASR-Nano-2512' else glmasr_asr,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        return raws

  