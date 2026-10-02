from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Infistar(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'infistar'
        self.max_tokens = int(params.get('infistar_max_token', 8192))
        self.model_name = params.get('infistar_model', 'gpt-5.4-mini')
        self.api_url = 'https://infistar.cc/v1'
        self.api_key = params.get('infistar_key', '')

        super().__post_init__()
