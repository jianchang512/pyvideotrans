import logging
from dataclasses import dataclass


from videotrans.configure import config

from videotrans.tts._base import BaseTTS
from videotrans.util import tools

import argparse
import os

import soundfile as sf
from videotrans.util.helper_supertonic import load_text_to_speech, sanitize_filename, load_voice_style


@dataclass
class SupertonicTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.model_name='Supertone/supertonic-2'
        self.local_dir=f'{config.ROOT_DIR}/models/models--Supertone--supertonic-2'
    def _exec(self):
        self._local_mul_thread()

    def _download(self):
        tools.check_and_down_hf(self.model_name,self.model_name, self.local_dir,
                                    callback=self._progress_callback)

        # data={type,percent,filename,current,total}
    def _progress_callback(self, data):
        msg_type = data.get("type")
        percent = data.get("percent")
        filename = data.get("filename")

        if msg_type == "file":

            # 标签显示当前文件名
            self._signal(text=f"{filename} {percent:.2f}%")

        else:
            # === 情况 B：这是总文件计数 (Fetching 4 files) ===
            # 不要更新进度条！否则会由 100% 突然跳回 25%
            # 建议只在某个副标签显示总进度，或者干脆忽略
            current_file_idx = data.get("current")
            total_files = data.get("total")

            self._signal(text=f"Downloading {current_file_idx}/{total_files} files")


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

