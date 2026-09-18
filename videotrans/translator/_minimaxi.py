
from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class MiniMax(OpenAICampat):

    def __post_init__(self):
        self.ainame ="minimaxi"
        self.api_key = params.get('minimaxi_apikey', '')
        self.max_tokens =int(params.get('minimaxi_max_token',8192))
        self.model_name =params.get('minimaxi_text_model', 'MiniMax-M3')
        api_url = params.get('minimaxi_apiurl', 'api.minimax.io')
        if not api_url.startswith('https'):
            api_url = 'https://' +api_url
        if not api_url.endswith('/v1'):
            api_url = api_url.strip('/')+"/v1"
        self.api_url=api_url
        self.extra_body={"thinking": {"type": "adaptive" if params.get('minimaxi_thinking') else "disabled"}}
        super().__post_init__()

