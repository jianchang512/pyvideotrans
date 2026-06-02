
from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class MiniMax(OpenAICampat):

    def __post_init__(self):
        self.ainame ="minimax"
        self.api_key = params.get('minimax_key', '')
        self.max_tokens =int(params.get('minimax_max_tokens',8192))
        self.model_name =params.get('minimax_model', 'MiniMax-M3')
        api_url = params.get('minimax_api', 'api.minimax.io')
        if not api_url.startswith('https'):
            api_url = 'https://' +api_url
        if not api_url.endswith('/v1'):
            api_url = api_url.strip('/')+"/v1"
        self.api_url=api_url
        super().__post_init__()

