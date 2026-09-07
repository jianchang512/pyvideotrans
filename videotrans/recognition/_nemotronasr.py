import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Union
import time

from videotrans.configure import config
from videotrans.configure.config import  logger, ROOT_DIR
from videotrans.configure.excepts import SpeechToTextError
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util.help_down import check_and_down_hf



@dataclass
class NemotronRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.model_name='nvidia/nemotron-3.5-asr-streaming-0.6b'
        self.local_dir = f'{ROOT_DIR}/models/models--nvidia--nemotron-3.5-asr-streaming-0.6b'
        self.signal(text=f"use {self.model_name}")

    def _download(self):
        check_and_down_hf(self.model_name,self.model_name,self.local_dir,callback=self._process_callback)
        return True
        
    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        self.signal(text=f"loading {self.model_name}")
        logger.debug(f'_exec:{self.model_name=}')

        # 1. 准备数据
        title=f"load {self.model_name}"
        self.signal(text=title)
        logs_file = f'{config.TEMP_DIR}/{self.uuid}/huggingface-pipeasr-{self.detect_language}-{time.time()}.log'
        cut_audio_list_file = f'{config.TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'
        Path(cut_audio_list_file).write_text(json.dumps([ asdict(item) for item in self.cut_audio()]),encoding='utf-8')
        kwargs = {
            "cut_audio_list": cut_audio_list_file,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "local_dir": self.local_dir,
        }
        from videotrans.process.stt_nemotron import nemotron_asr
        raws=self._new_process(callback=nemotron_asr,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        if raws:
            return raws
        raise SpeechToTextError(f'No recognition results found:{self.model_name}')