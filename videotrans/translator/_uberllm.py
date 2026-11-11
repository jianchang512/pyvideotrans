from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Uberllm(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'uberllm'
        self.max_tokens = int(params.get('uberllm_max_token', 8192))
        self.model_name = params.get('uberllm_model', 'deepseek/deepseek-v4.1-flash')
        self.api_url = 'https://api.uberllm.dev/v1'
        self.api_key = params.get('uberllm_key', '')

        super().__post_init__()
