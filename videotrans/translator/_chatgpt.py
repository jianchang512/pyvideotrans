import re
from dataclasses import dataclass
from videotrans.configure.config import  params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class ChatGPT(OpenAICampat):
    def __post_init__(self):
        self.ainame = "chatgpt"
        self.api_key = params.get('chatgpt_key', '')
        self.api_url = params.get('chatgpt_api', '')
        self.model_name = params.get("chatgpt_model", '')
        super().__post_init__()



