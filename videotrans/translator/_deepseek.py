# -*- coding: utf-8 -*-
from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class DeepSeek(OpenAICampat):

    def __post_init__(self):
        self.ainame="deepseek"
        self.model_name = params.get('deepseek_model', "deepseek-v4-flash")
        self.api_url = 'https://api.deepseek.com/v1/'
        self.api_key = params.get('deepseek_key', '')
        self.max_tokens=int(params.get('deepseek_max_token', 65536))
        self.reasoning_effort="high" if params.get('deepseek_thinking') else None
        self.extra_body={"thinking": {"type": "enabled" if params.get('deepseek_thinking') else "disabled"}}
        super().__post_init__()
