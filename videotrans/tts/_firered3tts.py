from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import handle_file
from videotrans.tts._gradio import GradioBase
from videotrans.util.help_misc import vail_file


_LANGUAGE={
"ar":"Arabic",
"yue":"Cantonese",
"zh":"Chinese",
"cz":"Czech",
"nl":"Dutch",
"en":"English",
"fr":"French",
"de":"German",
"el":"Greek",
"hi":"Hindi",
"id":"Indonesian",
"it":"Italian",
"ja":"Japanese",
"ko":"Korean",
"pl":"Polish",
"pt":"Portuguese",
"ro":"Romanian",
"ru":"Russian",
"es":"Spanish",
"th":"Thai",
"tr":"Turkish",
"uk":"Ukrainian",
"vi":"Vietnamese"
}

@dataclass
class FireRed3TTS(GradioBase):
    def __post_init__(self):
        self.ainame = "firered3tts"
        super().__post_init__()
       

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if vail_file(data_item['filename']):return
        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "text":data_item['text'].strip(),
            "prompt_text":ref_text,
            "prompt_audio":handle_file(ref_wav),
            "inference_cfg":2.0,
            "n_timesteps":10,
            "seed":1234,
            "do_tn":True,
            "language": _LANGUAGE.get(self.language.split('-')[0],"Auto-detect"),
            "api_name":'/voice_clone'
        }

        return self._send(kwargs, data_item)
