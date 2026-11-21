from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Aigrow(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'aigrow'
        self.max_tokens = int(params.get('aigrow_max_token', 8192))
        self.model_name = params.get('aigrow_model', 'claude-haiku-5.5')
        self.api_url = 'https://aigrow.gg/v1'
        self.api_key = params.get('aigrow_key', '')

        super().__post_init__()
