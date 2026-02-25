import logging
from dataclasses import dataclass


from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang

from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
import argparse
import os

import soundfile as sf
from videotrans.util.helper_supertonic import load_text_to_speech, sanitize_filename, load_voice_style


@dataclass
class SupertonicTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.model_name='Supertone/supertonic-2'
        self.local_dir=f'{ROOT_DIR}/models/models--Supertone--supertonic-2'
    def _exec(self):
        self._local_mul_thread()

    def _download(self):
        tools.check_and_down_hf(self.model_name,self.model_name, self.local_dir,
                                    callback=self._process_callback)



    def _item_task(self, data_item: dict = None):
        if self._exit() or not data_item.get('text','').strip():
            return

        if self._exit() or tools.vail_file(data_item['filename']):
            return
        speed = 1.0
        if self.rate:
            rate = float(self.rate.replace('%', '')) / 100
            speed += rate

        role=data_item.get('role','F1')
        
        text_to_speech = load_text_to_speech(f"{self.local_dir}/onnx", False)


        style = load_voice_style([f"{self.local_dir}/voice_styles/{role}.json"], verbose=False)
        wav, duration = text_to_speech(
                       data_item.get('text'), self.language[:2], style, 10, speed
                    )
                    
        w = wav[0, : int(text_to_speech.sample_rate * duration.item())]  # [T_trim]
        sf.write(data_item['filename']+'-tmp.wav', w, text_to_speech.sample_rate)
        
        
        self.convert_to_wav(data_item['filename'] +'-tmp.wav', data_item['filename'])

