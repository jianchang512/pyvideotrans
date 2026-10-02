from dataclasses import dataclass, field
from typing import List, Dict
from typing import Union
import httpx
from deepgram.core import ApiError
from videotrans.configure.config import params
from videotrans.tts._base import BaseTTS
from deepgram import DeepgramClient

# 仅支持 aura-2 模型

@dataclass(repr=False)
class DeepgramTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        httpx.HTTPTransport(proxy=self.proxy_str)
        self.speed = self.get_speed()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if self._exit() or not data_item.get('text', '').strip():
            return
        try:
            deepgram = DeepgramClient(api_key=params.get('deepgram_apikey'))
            with open(data_item['filename'] + ".mp3", "wb") as f:
                for chunk in deepgram.speak.v1.audio.generate(
                        text=data_item["text"],
                        model=f"aura-2-{data_item['role']}-{self.language.split('-')[0]}",
                        speed=self.speed,
                ):
                    f.write(chunk)
            self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])
        except ApiError as e:
            return e.body
