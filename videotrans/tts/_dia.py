from dataclasses import dataclass
from typing import List, Dict, Union
from gradio_client import handle_file
from videotrans.tts._gradio import GradioBase


@dataclass
class DiaTTS(GradioBase):
    def __post_init__(self):
        self.ainame = "diatts"
        super().__post_init__()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "text_input":data_item['text'].strip(),
            "audio_prompt_input":handle_file(ref_wav),
            "transcription_input":ref_text,
            "api_name":'/generate_audio'
        }
        return self._send(kwargs, data_item)


