import json
import os,sys
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union

from alibabacloud_alimt20181012.client import Client as alimt20181012Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_alimt20181012 import models as alimt_20181012_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

from videotrans.configure import config
from videotrans.translator._base import BaseTrans

@dataclass
class Ali(BaseTrans):
    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False

        proxy = os.environ.get('http_proxy')
        if proxy:
            if 'http_proxy' in os.environ: del os.environ['http_proxy']
            if 'https_proxy' in os.environ: del os.environ['https_proxy']
            if 'all_proxy' in os.environ: del os.environ['all_proxy']

    
    
    def create_client(self) -> alimt20181012Client:
        """
        使用AK&SK初始化账号Client
        @return: Client
        @throws Exception
        """
        cf = open_api_models.Config(
            access_key_id= config.params['ali_id'],
            access_key_secret= config.params['ali_key']
        )
        # Endpoint 请参考 https://api.aliyun.com/product/alimt
        cf.endpoint = f'mt.cn-hangzhou.aliyuncs.com'
        return alimt20181012Client(cf)
    
    def _item_task(self, data: Union[List[str], str]) -> str:
        client = self.create_client()
        translate_general_request = alimt_20181012_models.TranslateGeneralRequest(
            format_type='text',
            source_language='auto',
            target_language= 'zh' if self.target_code[:2]=='zh' else self.target_code ,
            source_text="\n".join(data),
            scene='general'
        )
        runtime = util_models.RuntimeOptions()
        
        try:
            res=client.translate_with_options(translate_general_request, runtime)
            config.logger.info(f'ali：{res.body=}')
            if int(res.body.code)!=200:
                raise Exception(f'error:{res.body.code}')
            return res.body.data.translated
        except Exception as error:
            raise
        