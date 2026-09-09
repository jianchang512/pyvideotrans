from dataclasses import dataclass
from videotrans.recognition._huggingface import HuggingfaceRecogn


@dataclass
class NemotronRecogn(HuggingfaceRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.model_name='nvidia/nemotron-3.5-asr-streaming-0.6b'
