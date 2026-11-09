from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass(repr=False)
class HuoShan(OpenAICampat):

    def __post_init__(self):
        self.ainame ="zijie"
        self.api_key =params.get('zijiehuoshan_key','')
        self.api_url ='https://ark.cn-beijing.volces.com/api/v3'
        self.max_tokens =int(params.get('zijiehuoshan_max_token',32768))
        self.model_name =params.get("zijiehuoshan_model",'')
        # default 时不添加参数，是否思考跟随模型默认；none 关闭思考
        effort=params.get('zijiehuoshan_reasoning_effort')
        if effort!='default':
            self.reasoning_effort=effort
            self.extra_body={"thinking": {"type": "enabled" if effort !='none' else "disabled"}}
        super().__post_init__()

