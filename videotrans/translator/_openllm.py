from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

# Cloud endpoint. A local OpenLLM daemon (http://127.0.0.1:8787/v1, no key) can be set in the dialog.
DEFAULT_OPENLLM_API = 'https://www.openllm.sh/v1'


@dataclass(repr=False)
class Openllm(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'openllm'
        self.max_tokens = int(params.get('openllm_max_token', 8192))
        self.model_name = params.get('openllm_model', 'plus')
        self.api_url = params.get('openllm_api', '') or DEFAULT_OPENLLM_API
        # The local daemon needs no key, but the OpenAI SDK rejects an empty one
        self.api_key = params.get('openllm_key', '') or 'openllm'

        super().__post_init__()
