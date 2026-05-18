import logging
from dataclasses import dataclass
from typing import List, Union

from alibabacloud_alimt20181012 import models as alimt_20181012_models
from alibabacloud_alimt20181012.client import Client as alimt20181012Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from tenacity import retry, retry_if_not_exception_type, wait_fixed, stop_after_attempt, before_log, after_log

from videotrans.configure.excepts import TranslateSrtError, NO_RETRY_EXCEPT
from videotrans.configure.config import params, logger, settings
from videotrans.translator._base import BaseTrans



@dataclass
class Ali(BaseTrans):

    def create_client(self) -> alimt20181012Client:
        cf = open_api_models.Config(
            access_key_id=params.get('ali_id',''),
            access_key_secret=params.get('ali_key','')
        )
        # Endpoint 请参考 https://api.aliyun.com/product/alimt
        cf.endpoint = f'mt.cn-hangzhou.aliyuncs.com'
        return alimt20181012Client(cf)

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        client = self.create_client()
        translate_general_request = alimt_20181012_models.TranslateGeneralRequest(
            format_type='text',
            source_language='auto',
            target_language='zh' if self.target_code[:2] == 'zh' else self.target_code,
            source_text="\n".join(data),
            scene='general'
        )
        runtime = util_models.RuntimeOptions()

        res = client.translate_with_options(translate_general_request, runtime)
        if int(res.body.code) != 200:
            raise TranslateSrtError(f'error:{res.body}')
        return res.body.data.translated
