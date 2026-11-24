from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Teamorouter(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'teamorouter'
        self.max_tokens = int(params.get('teamorouter_max_token', 8192))
        self.model_name = params.get('teamorouter_model', 'claude-haiku-5-5')
        self.api_url = 'https://api.teamorouter.com/v1'
        self.api_key = params.get('teamorouter_key', '')

        super().__post_init__()
