from dataclasses import dataclass
from videotrans.recognition._huggingface import HuggingfaceRecogn
from pathlib import Path
from videotrans.configure.config import ROOT_DIR
from videotrans.util.help_down import check_and_down_hf


@dataclass(repr=False)
class NemotronRecogn(HuggingfaceRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.model_name='nvidia/nemotron-3.5-asr-streaming-0.6b'
        self.local_dir = f'{ROOT_DIR}/models/models--' + self.model_name.replace('/', '--')
        self.signal(text=f"use {self.model_name}")
    def _download(self):
        if not Path(f'{self.local_dir}/model.safetensors').exists():
            check_and_down_hf(self.model_name,self.model_name,self.local_dir,callback=self._process_callback)
