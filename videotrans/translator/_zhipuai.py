from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class ZhipuAI(OpenAICampat):

    def __post_init__(self):
        self.ainame ='zhipuai'
        self.max_tokens =int(params.get('zhipuai_max_token',4095))
        self.model_name = params.get('zhipuai_model', "glm-4.5-flash")
        self.api_url = 'https://open.bigmodel.cn/api/paas/v4/'
        self.api_key = params.get('zhipuai_key', '')
        effort=params.get('zhipuai_reasoning_effort')
        if effort!='default':
            self.reasoning_effort=effort
            self.extra_body={"thinking": 'enabled' if effort!='none' else 'disabled'}
        super().__post_init__()
