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
        self.extra_body={"thinking": {"type": "enabled" if params.get('zhipuai_thinking') else "disabled"}}
        super().__post_init__()
