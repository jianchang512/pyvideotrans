from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Trustedrouter(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'trustedrouter'
        self.max_tokens = int(params.get('trustedrouter_max_token', 8192))
        self.model_name = params.get('trustedrouter_model', 'deepseek/deepseek-v4-flash')
        self.api_url = 'https://api.trustedrouter.com/v1'
        self.api_key = params.get('trustedrouter_key', '')

        super().__post_init__()
