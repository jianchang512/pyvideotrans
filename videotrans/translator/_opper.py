from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Opper(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'opper'
        self.max_tokens = int(params.get('opper_max_token', 8192))
        self.model_name = params.get('opper_model', 'gpt-5.4-mini')
        self.api_url = 'https://api.opper.ai/v3/compat'
        self.api_key = params.get('opper_key', '')

        super().__post_init__()
