from dataclasses import dataclass
from videotrans.configure.config import params
from videotrans.translator._openaicompat import OpenAICampat

@dataclass
class AzureGPT(OpenAICampat):

    def __post_init__(self):
        self.ainame="azure"
        self.api_key=params.get("azure_key",'')
        self.api_url=params.get("azure_api",'')
        self.model_name = params.get("azure_model",'')
        super().__post_init__()

