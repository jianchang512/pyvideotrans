from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Cloudgpu(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'cloudgpu'
        self.max_tokens = int(params.get('cloudgpu_max_token', 8192))
        self.model_name = params.get('cloudgpu_model', 'deepseek-v4.1-flash')
        self.api_url = 'https://cloudgpu.app/v1'
        self.api_key = params.get('cloudgpu_key', '')

        super().__post_init__()
