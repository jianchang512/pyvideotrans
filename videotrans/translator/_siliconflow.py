from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass(repr=False)
class SILICONFLOW(OpenAICampat):

    def __post_init__(self):
        self.ainame ='siliconflow'
        self.max_tokens =int(params.get('siliconflow_max_token',8192))
        self.model_name = params.get('siliconflow_model', '')
        self.api_url = "https://api.siliconflow.cn/v1"
        self.api_key = params.get('siliconflow_key', '')
        self.extra_body={"enable_thinking": bool(params.get('siliconflow_thinking'))}
        super().__post_init__()
