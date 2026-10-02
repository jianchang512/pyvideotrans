from dataclasses import dataclass

from alibabacloud_alimt20181012 import models as alimt_20181012_models
from alibabacloud_alimt20181012.client import Client as alimt20181012Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from videotrans.configure.excepts import TranslateSrtError
from videotrans.configure.config import params
from videotrans.translator._base import BaseTrans



@dataclass(repr=False)
class Ali(BaseTrans):

    @staticmethod
    def create_client() -> alimt20181012Client:
        cf = open_api_models.Config(
            access_key_id=params.get('ali_id',''),
            access_key_secret=params.get('ali_key','')
        )
        # Endpoint 请参考 https://api.aliyun.com/product/alimt
        cf.endpoint = f'mt.cn-hangzhou.aliyuncs.com'
        return alimt20181012Client(cf)

    def _item_task(self,data: str) -> str:
        if self._exit(): return
        client = self.create_client()
        translate_general_request = alimt_20181012_models.TranslateGeneralRequest(
            format_type='text',
            source_language='auto',
            target_language=self.target_code,
            source_text=data,
            scene='general'
        )
        runtime = util_models.RuntimeOptions()

        res = client.translate_with_options(translate_general_request, runtime)
        if int(res.body.code) != 200:
            raise TranslateSrtError(f'error:{res.body}')
        return res.body.data.translated
