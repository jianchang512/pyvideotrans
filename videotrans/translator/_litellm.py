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
        self.reasoning_effort = None if not _reason or _reason == 'default' else _reason

        super().__post_init__()

    def _create_completion(self, kwargs):
        """Route the request through the litellm SDK instead of the OpenAI SDK.

        The user hosts their own LiteLLM proxy and supplies its URL + key, so we
        prefix the model with ``litellm_proxy/`` to make the SDK forward the call
        to that proxy (which then routes to whichever provider serves the alias).
        ``drop_params=True`` keeps a single config working across every model the
        proxy can route to.
        """
        import litellm

        call_kwargs = dict(kwargs)
        model_name = call_kwargs.get('model', '')
        if self.api_url and not model_name.startswith('litellm_proxy/'):
            call_kwargs['model'] = f'litellm_proxy/{model_name}'
            call_kwargs['api_base'] = self.api_url
        if self.api_key:
            call_kwargs['api_key'] = self.api_key
        call_kwargs['drop_params'] = True

        return litellm.completion(**call_kwargs, extra_body=self.extra_body)
