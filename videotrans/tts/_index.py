from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import handle_file

from videotrans.configure.config import params
from videotrans.tts._gradio import GradioBase


@dataclass
class IndexTTS(GradioBase):
    def __post_init__(self):
        self.ainame = "indextts"
        super().__post_init__()


    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "prompt": handle_file(ref_wav),
            "text": data_item['text'].strip(),
            "api_name": '/gen_single'
        }
        # 0=v1 1=v2
        if int(params.get('index_tts_version', 1)) == 1:
            kwargs['emo_control_method'] = 'Same as the voice reference'
            kwargs['emo_ref_path'] = handle_file(ref_wav)
        return self._send(kwargs, data_item)


