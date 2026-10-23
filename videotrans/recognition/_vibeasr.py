import json
from dataclasses import dataclass, asdict
from typing import List,  Union

from pathlib import Path
import  time

from pydub import AudioSegment

from videotrans.configure.config import logger, defaulelang, ROOT_DIR, settings
from videotrans.configure import config
from videotrans.process.vad import get_speech_timestamp_silero

from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util._srt_parse import ms_to_time_string
from videotrans.util.help_down import check_and_down_hf


@dataclass(repr=False)
class VibeasrRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.model_name='microsoft/VibeVoice-ASR-HF'
        self.local_dir=f'{ROOT_DIR}/models/models--microsoft--VibeVoice-ASR-HF'

    def _download(self):
        _repid=f'microsoft/VibeVoice-ASR-HF'
        check_and_down_hf(model_id=_repid,
                                    repo_id=_repid,
                                    local_dir=self.local_dir,
                                    callback=self._process_callback)

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return

        logs_file = f'{config.TEMP_DIR}/{self.uuid}/vibeasr-{time.time()}.log'
        title = f"VibeVoice-ASR {self.model_name}"

        # 不使用 VibeVoice-ASR 内部自动断句，因中文下会生成十几秒到几十秒的超长断句
        cut_audio_list_file = f'{config.TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'
        Path(cut_audio_list_file).write_text(json.dumps([ asdict(item) for item in self.cut_audio()]),encoding='utf-8')

        kwargs = {
            "cut_audio_list": cut_audio_list_file,
            "logs_file": logs_file,
            "model_name": self.model_name,
            "local_dir":self.local_dir,
            "hotword":settings.get('hotwords'),
            "detect_language":self.detect_language
        }
        from videotrans.process.stt_vibeasr import videasr_fun
        jsdata = self._new_process(callback=videasr_fun, title=title, is_cuda=self.is_cuda, kwargs=kwargs)
        return jsdata


