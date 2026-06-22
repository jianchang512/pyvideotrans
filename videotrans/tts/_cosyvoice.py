from dataclasses import dataclass
from typing import Union, Dict, List
from pathlib import Path
import wave

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
        if not ref_wav or not Path(ref_wav).exists() or Path(ref_wav).stat().st_size == 0:
            return f"CosyVoice reference audio is empty or missing: {ref_wav}"
        with wave.open(ref_wav, "rb") as wav_file:
            if wav_file.getnframes() == 0:
                return f"CosyVoice reference audio has no frames: {ref_wav}"
        prompt_text = (prompt_text or "").strip()
        if "<|endofprompt|>" not in prompt_text:
            prompt_text = f"You are a helpful assistant.<|endofprompt|>{prompt_text}"
        kwargs = {
            "tts_text": data_item.get('text', '').strip(),
            "mode_checkbox_group": "3s极速复刻",
            "prompt_wav_upload": handle_file(ref_wav),
            "prompt_wav_record": handle_file(ref_wav),
            "prompt_text": prompt_text,
            "instruct_text": '',#instruct_text,
            "seed": 0,
            "speed": self.speed,
            "stream": False,
            "api_name": "/generate_audio"
        }
        return self._send(kwargs, data_item)
