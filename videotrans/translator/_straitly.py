from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Straitly(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'straitly'
        self.max_tokens = int(params.get('straitly_max_token', 8192))
        self.model_name = params.get('straitly_model', 'deepseek/deepseek-v4-1-flash-1017')
        self.api_url = 'https://api.straitly.ai/v1'
        self.api_key = params.get('straitly_key', '')

        super().__post_init__()
