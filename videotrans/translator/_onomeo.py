from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Onomeo(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'onomeo'
        self.max_tokens = int(params.get('onomeo_max_token', 8192))
        self.model_name = params.get('onomeo_model', 'deepseek-v4.1-flash')
        self.api_url = 'https://onomeo.com/v1'
        self.api_key = params.get('onomeo_key', '')

        super().__post_init__()
