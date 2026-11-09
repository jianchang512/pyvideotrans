from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Standardcompute(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'standardcompute'
        self.max_tokens = int(params.get('standardcompute_max_token', 8192))
        self.model_name = params.get('standardcompute_model', 'StandardCompute')
        self.api_url = 'https://api.stdcmpt.com/v1'
        self.api_key = params.get('standardcompute_key', '')

        super().__post_init__()
