from dataclasses import dataclass
from typing import Union, Dict, List

from gradio_client import handle_file
from videotrans.configure.config import params
from videotrans.tts._gradio import GradioBase



@dataclass
class CosyVoice(GradioBase):
    def __post_init__(self):
        self.ainame = "cosyvoice"
        super().__post_init__()
        self.speed = max(0.5, min(2.0, self.get_speed()))

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1)->Union[str, None]:
        ref_wav,prompt_text = self.get_ref_wav(data_item)
        # 参考音频对应文本内容
        # 提示词，克隆时放入参考音频文本中
        instruct_text = params.get('cosyvoice_instruct_text', '')
        if instruct_text:
            prompt_text = f'You are a helpful assistant.{instruct_text}<|endofprompt|>{prompt_text}'
        kwargs = {
            "tts_text": data_item.get('text', '').strip(),
            "mode_checkbox_group": "3s极速复刻",
            "prompt_wav_upload": handle_file(ref_wav),
            "prompt_wav_record": handle_file(ref_wav),
            "prompt_text": prompt_text,
            "instruct_text": instruct_text,
            "seed": 0,
            "speed": self.speed,
            "stream": False,
            "api_name": "/generate_audio"

        }
        return self._send(kwargs, data_item)

