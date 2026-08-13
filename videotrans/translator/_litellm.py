from dataclasses import dataclass

from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

# Default endpoint of a locally running LiteLLM proxy (`litellm --port 4000`).
DEFAULT_LITELLM_API = 'http://localhost:4000/v1'


@dataclass
class LiteLLM(OpenAICampat):
    """LiteLLM AI gateway channel.

    LiteLLM exposes 100+ LLM providers (OpenAI, Anthropic, Azure, Bedrock,
    Gemini, and more) behind a single OpenAI-compatible API. Unlike the other
    OpenAI-compatible channels the endpoint is user configurable, because a
    LiteLLM proxy is self-hosted; it defaults to the local proxy address.
    """

    def __post_init__(self):
        self.ainame = 'litellm'
        self.max_tokens = int(params.get('litellm_max_token', 8192))
        self.model_name = params.get('litellm_model', "")
        self.api_url = params.get('litellm_api', '') or DEFAULT_LITELLM_API
        self.api_key = params.get('litellm_key', '')
        _reason = params.get('litellm_reasoning_effort')
        self.reasoning_effort = None if not _reason or _reason == 'No' else _reason

        super().__post_init__()
