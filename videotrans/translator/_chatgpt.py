from videotrans.configure.config import  params
from videotrans.translator._openaicompat import OpenAICampat
from dataclasses import dataclass

from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass
class ChatGPT(OpenAICampat):
    def __post_init__(self):
        self.ainame = "chatgpt"
        self.api_key = params.get('chatgpt_key', '')
        self.api_url = params.get('chatgpt_api', '')
        self.max_tokens = int(params.get('chatgpt_max_token', 8192))
        self.model_name = params.get("chatgpt_model", '')
        _reason=params.get('chatgpt_reasoning_effort')
        self.reasoning_effort=None if not _reason or _reason=='No' else _reason
        super().__post_init__()



