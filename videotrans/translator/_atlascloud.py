from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat


@dataclass(repr=False)
class AtlasCloud(OpenAICampat):

    def __post_init__(self):
        self.ainame = 'atlascloud'
        self.max_tokens = int(params.get('atlascloud_max_token', 8192))
        self.model_name = params.get('atlascloud_model', 'deepseek-ai/deepseek-v4-flash')
        self.api_url = 'https://api.atlascloud.ai/v1'
        self.api_key = params.get('atlascloud_key', '')

        super().__post_init__()
