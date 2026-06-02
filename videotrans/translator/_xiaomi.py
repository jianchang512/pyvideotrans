from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class XiaoMi(OpenAICampat):

    def __post_init__(self):
        self.ainame ='xiaomi'
        self.max_tokens =int(params.get('xiaomi_maxtoken', 40960))
        self.model_name = params.get('xiaomi_model')
        self.api_url = 'https://api.xiaomimimo.com/v1/'
        self.api_key = params.get('xiaomi_key', '')
        self.extra_body={
                "thinking": {"type": "disabled" if params.get('xiaomi_thinking') else 'disabled'}
        }
        super().__post_init__()
