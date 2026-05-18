from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import handle_file
from videotrans.tts._gradio import GradioBase


@dataclass
class SparkTTS(GradioBase):
    def __post_init__(self):
        self.ainame = "sparktts"
        super().__post_init__()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "text":data_item['text'].strip(),
            "prompt_text":ref_text,
            "prompt_wav_upload":handle_file(ref_wav),
            "prompt_wav_record":handle_file(ref_wav),
            "api_name":'/voice_clone'
        }
        return self._send(kwargs, data_item)
