import json
from dataclasses import dataclass, asdict
from typing import List,  Union

from pathlib import Path
import  time

from videotrans.configure.config import logger, defaulelang, ROOT_DIR, settings
from videotrans.configure import config

from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util.help_down import check_and_down_ms, check_and_down_hf
from videotrans.util.help_misc import is_connect_hf


@dataclass
class MossRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.local_dir=f'{ROOT_DIR}/models/models--OpenMOSS-Team--MOSS-Transcribe-Diarize'
    
    def _download(self):
        if not is_connect_hf():
            check_and_down_hf(model_id=f'openmoss/MOSS-Transcribe-Diarize',
                                    local_dir=self.local_dir,
                                    callback=self._process_callback)
        else:
            check_and_down_hf(model_id=f'OpenMOSS-Team/MOSS-Transcribe-Diarize',
                                    repo_id=f'OpenMOSS-Team/MOSS-Transcribe-Diarize',
                                    local_dir=self.local_dir,
                                    callback=self._process_callback)

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return

        logs_file = f'{config.TEMP_DIR}/{self.uuid}/MOSS-Transcribe-Diarize-{time.time()}.log'
        title = "MOSS-Transcribe-Diarize"
        cut_audio_list_file=None
        from pydub import AudioSegment
        
        if len(AudioSegment.from_file(self.audio_file, format="wav"))>5400000:
            cut_audio_list_file = f'{config.TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'
            Path(cut_audio_list_file).write_text(json.dumps([ asdict(item) for item in self.cut_audio()]), encoding='utf-8')
        
        kwargs = {
            "cut_audio_list": cut_audio_list_file,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "audio_file": self.audio_file,
            "cache_folder": self.cache_folder,
            "hotword":settings.get('hotwords',''),
            "local_dir":self.local_dir
        }
        from videotrans.process.stt_mossasr import mosstrans_asr
        jsdata = self._new_process(callback=mosstrans_asr, title=title, is_cuda=self.is_cuda, kwargs=kwargs)
        logger.debug(f'MOSS-Transcribe-Diarize 返回的字词时间戳数据:{jsdata=}')
        return jsdata
