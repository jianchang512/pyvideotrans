from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Requesty(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'requesty'
        self.max_tokens = int(params.get('requesty_max_token', 8192))
        self.model_name = params.get('requesty_model', 'openai/gpt-5.4-mini')
        self.api_url = 'https://router.requesty.ai/v1'
        self.api_key = params.get('requesty_key', '')

        super().__post_init__()
