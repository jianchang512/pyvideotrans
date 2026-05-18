from dataclasses import dataclass

from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass
class LocalLLM(OpenAICampat):

    def __post_init__(self):
        self.ainame ="localllm"
        self.api_key =params.get('localllm_key','')
        self.max_tokens =int(params.get('localllm_max_token')) if params.get(
                'localllm_max_token') else 4096
        self.api_url = params.get('localllm_api','')
        self.model_name = params.get("localllm_model",'')
        super().__post_init__()

