
from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class MiniMax(OpenAICampat):

    def __post_init__(self):
        self.ainame ="minimax"
        self.api_key = params.get('minimax_key', '')
        self.max_tokens =int(params.get('minimax_max_tokens',8192))
        self.model_name =params.get('minimax_model', 'MiniMax-M2.7')
        api_url = params.get('minimax_api', 'api.minimax.io')
        if not self.api_url.startswith('https'):
            self.api_url = 'https://' +api_url
        if not self.api_url.endswith('/v1'):
            self.api_url = api_url.strip('/')+"/v1"
        super().__post_init__()

