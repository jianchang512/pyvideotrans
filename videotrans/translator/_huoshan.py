from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class HuoShan(OpenAICampat):

    def __post_init__(self):
        self.ainame ="zijie"
        self.api_key =params.get('zijiehuoshan_key','')
        self.api_url ='https://ark.cn-beijing.volces.com/api/v3'
        self.max_tokens =32768
        self.model_name =params.get("zijiehuoshan_model",'')
        super().__post_init__()

