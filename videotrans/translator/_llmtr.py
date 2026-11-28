from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class Llmtr(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'llmtr'
        self.max_tokens = int(params.get('llmtr_max_token', 8192))
        self.model_name = params.get('llmtr_model', 'qwen/qwen3.8-flash')
        self.api_url = 'https://llmtr.com/v1'
        self.api_key = params.get('llmtr_key', '')

        super().__post_init__()
