import json
from dataclasses import dataclass, asdict
from typing import List,  Union

from pathlib import Path
import  time

from videotrans.configure.config import logger, defaulelang, ROOT_DIR, settings
from videotrans.configure import config

from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools
from videotrans.process import qwen3asr_fun


@dataclass
class QwenasrlocalRecogn(BaseRecogn):

    def _download(self):
        if defaulelang == 'zh':
            tools.check_and_down_ms(f'Qwen/Qwen3-ASR-{self.model_name}', callback=self._process_callback,
                                    local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-ASR-{self.model_name}')
        else:
            tools.check_and_down_hf(model_id=f'Qwen3-ASR-{self.model_name}',
                                    repo_id=f'Qwen/Qwen3-ASR-{self.model_name}',
                                    local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-ASR-{self.model_name}',
                                    callback=self._process_callback)

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return

        logs_file = f'{config.TEMP_DIR}/{self.uuid}/qwen3tts-{time.time()}.log'
        title = "Qwen3-ASR"
        cut_audio_list_file = f'{config.TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'
        Path(cut_audio_list_file).write_text(json.dumps([ asdict(item) for item in self.cut_audio()]), encoding='utf-8')
        kwargs = {
            "cut_audio_list": cut_audio_list_file,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "audio_file": self.audio_file,
            "model_name": self.model_name,
            "hotword":settings.get('hotwords'),
        }
        jsdata = self._new_process(callback=qwen3asr_fun, title=title, is_cuda=self.is_cuda, kwargs=kwargs)
        logger.debug(f'Qwen-asr返回的字词时间戳数据:{jsdata=}')
        return jsdata
