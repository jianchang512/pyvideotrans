from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Atmorouter(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'atmorouter'
        self.max_tokens = int(params.get('atmorouter_max_token', 8192))
        self.model_name = params.get('atmorouter_model', 'zai/glm-5.3')
        self.api_url = 'https://atmorouter.dev/v1'
        self.api_key = params.get('atmorouter_key', '')

        super().__post_init__()
