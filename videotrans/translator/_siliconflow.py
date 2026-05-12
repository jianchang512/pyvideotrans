from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class SILICONFLOW(OpenAICampat):

    def __post_init__(self):
        self.ainame ='siliconflow'
        self.max_tokens =int(params.get('guiji_max_tokens',8192))
        self.model_name = params.get('guiji_model', '')
        self.api_url = "https://api.siliconflow.cn/v1"
        self.api_key = params.get('guiji_key', '')
        super().__post_init__()
