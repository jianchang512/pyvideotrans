import logging
import re
from dataclasses import dataclass
from typing import List, Union

from videotrans.configure.config import tr, logger, settings,ROOT_DIR
from videotrans.translator._base import BaseTrans
import torch


@dataclass
class HYMT2(BaseTrans):
    localdir:str=None
    def __post_init__(self):
        super().__post_init__()
        self.localdir=f'{ROOT_DIR}/models/models--tencent--Hy-MT2-1.8B'
    def _download(self):
        from videotrans.util.help_down import check_and_down_hf
        check_and_down_hf(
                "Hy-MT2-1.8B",
                'tencent/Hy-MT2-1.8B',
                self.localdir,
                callback=self._process_callback,
                #allow_list=[self.cfg['model_name'],self.cfg['vocab_name']]
        )        
        return True

    def _item_task(self,model,tokenizer, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data


        prompt = f"""Please translate the following text accurately into {self.target_language_name}. You must retain the same number of line breaks in the translation; do not omit, merge, or delete line breaks, and pay attention to their placement.\n\n{text}"""


        messages = [{"role": "user", "content": prompt}]
        inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=4096,
            )
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        return response.strip()