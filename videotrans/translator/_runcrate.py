from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Runcrate(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'runcrate'
        self.max_tokens = int(params.get('runcrate_max_token', 8192))
        self.model_name = params.get('runcrate_model', 'deepseek-ai/DeepSeek-V4.1-Flash')
        self.api_url = 'https://api.runcrate.ai/v1'
        self.api_key = params.get('runcrate_key', '')

        super().__post_init__()
