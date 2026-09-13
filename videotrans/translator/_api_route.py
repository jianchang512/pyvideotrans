from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass
class APIRoute(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'api_route'
        self.max_tokens = int(params.get('api_route_max_token', 8192))
        self.model_name = params.get('api_route_model', 'gpt-5.4-mini')
        self.api_url = 'https://www.api-route.com/v1'
        self.api_key = params.get('api_route_key', '')

        super().__post_init__()
