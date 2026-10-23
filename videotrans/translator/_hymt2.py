from dataclasses import dataclass
from typing import Any
from pathlib import Path
from videotrans.configure.config import  logger, settings, ROOT_DIR
from videotrans.translator._base import BaseTrans
import torch


@dataclass
class HYOBJ:
    hymt2_tokenizer: Any = None
    hymt2_model: Any = None



@dataclass(repr=False)
class HYMT2(BaseTrans):
    hy:Any=None
    def __post_init__(self):
        super().__post_init__()
        self.local_dir = f'{ROOT_DIR}/models/models--tencent--Hy-MT2-1.8B'
        self.hy=HYOBJ()

    def _download(self):
        from videotrans.util.help_down import check_and_down_hf, check_and_down_ms
        from videotrans.util.help_misc import is_connect_hf
        if is_connect_hf():
            check_and_down_hf(
                "Hy-MT2-1.8B",
                'tencent/Hy-MT2-1.8B',
                self.local_dir,
                callback=self._process_callback)
        else:
            check_and_down_ms(
                'Tencent-Hunyuan/Hy-MT2-1.8B',
                local_dir=self.local_dir,
                callback=self._process_callback)

        from transformers import AutoModelForCausalLM, AutoTokenizer

        # Load tokenizer
        self.hy.hymt2_tokenizer = AutoTokenizer.from_pretrained(self.local_dir, trust_remote_code=True)

        # Load model
        device=settings.get('device_name','auto')
        if device=='auto':
            import torch
            device="cpu" if not self.is_cuda or not torch.cuda.is_available() else "cuda"
        self.hy.hymt2_model = AutoModelForCausalLM.from_pretrained(
            self.local_dir,
            device_map=device,
            dtype='auto',
            trust_remote_code=True,
        )
        logger.debug(f'HY2-MT:running on {self.hy.hymt2_model.device}')
        self.hy.hymt2_model.eval()
        return True

    def _item_task(self, data: str) -> str:
        if self._exit(): return
        text = data

        prompt=Path(f'{ROOT_DIR}/videotrans/prompts/text/hymt.txt').read_text(encoding="utf-8").replace("{lang}",self.target_code).replace('{batch_input}',text)

        messages = [{"role": "user", "content": prompt}]
        inputs = self.hy.hymt2_tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(
            self.hy.hymt2_model.device)

        with torch.no_grad():
            outputs = self.hy.hymt2_model.generate(
                **inputs,
                max_new_tokens=8092,
            )
        response = self.hy.hymt2_tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        return response.strip()

    def _unload(self):
        try:
            self.hy.hymt2_model=None
            self.hy.hymt2_tokenizer=None
            self.hy=None
        except BaseException:
            pass