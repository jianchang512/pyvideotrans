from dataclasses import dataclass
from typing import List, Union, Any

from videotrans.configure.config import  logger, settings, ROOT_DIR
from videotrans.translator._base import BaseTrans
import torch


@dataclass
class HYMT2(BaseTrans):
    hymt2_tokenizer: Any = None
    hymt2_model: Any = None

    def __post_init__(self):
        super().__post_init__()
        self.local_dir = f'{ROOT_DIR}/models/models--tencent--Hy-MT2-1.8B'

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
        self.hymt2_tokenizer = AutoTokenizer.from_pretrained(self.local_dir, trust_remote_code=True)

        # Load model
        self.hymt2_model = AutoModelForCausalLM.from_pretrained(
            self.local_dir,
            device_map=settings.get('device_name', 'auto'),
            dtype='auto',
            trust_remote_code=True,
        )
        logger.debug(f'HY2-MT:running on {self.hymt2_model.device}')
        self.hymt2_model.eval()
        return True

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data

        prompt = f"""Please translate the following text accurately into {self.target_language_name}. You must retain the same number of line breaks in the translation; do not omit, merge, or delete line breaks, and pay attention to their placement.\n\n{text}"""

        messages = [{"role": "user", "content": prompt}]
        inputs = self.hymt2_tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(
            self.hymt2_model.device)

        with torch.no_grad():
            outputs = self.hymt2_model.generate(
                **inputs,
                max_new_tokens=4096,
            )
        response = self.hymt2_tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        return response.strip()
