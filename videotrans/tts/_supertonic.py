import logging
from dataclasses import dataclass
from typing import Union, Dict, List
from videotrans.configure.config import ROOT_DIR, settings, logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
import soundfile as sf
from videotrans.util.helper_supertonic import load_text_to_speech, load_voice_style
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log


@dataclass
class SupertonicTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.model_name='Supertone/supertonic-3'
        self.local_dir=f'{ROOT_DIR}/models/models--Supertone--supertonic-3'
        self.speed=self.get_speed()

    def _download(self):
        tools.check_and_down_hf(self.model_name,self.model_name, self.local_dir,
                                    callback=self._process_callback)


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        role=data_item.get('role','F1')
        text_to_speech = load_text_to_speech(f"{self.local_dir}/onnx", False)
        style = load_voice_style([f"{self.local_dir}/voice_styles/{role}.json"], verbose=False)
        wav, duration = text_to_speech(
                       data_item.get('text'), self.language[:2], style, 10, self.speed
                    )
        w = wav[0, : int(text_to_speech.sample_rate * duration.item())]  # [T_trim]
        sf.write(data_item['filename']+'-tmp.wav', w, text_to_speech.sample_rate)
        self.convert_to_wav(data_item['filename'] +'-tmp.wav', data_item['filename'])