import json
import os
from typing import Union, List

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tmt.v20180321 import tmt_client, models

from videotrans.configure import config
from videotrans.translator._base import BaseTrans


class Tencent(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aisendsrt=False
        proxy = os.environ.get('http_proxy')
        if proxy:
            del os.environ['http_proxy']
            del os.environ['https_proxy']
            del os.environ['all_proxy']

    def _item_task(self, data: Union[List[str], str]) -> str:

        cred = credential.Credential(config.params.get('tencent_SecretId','').strip(), config.params['tencent_SecretKey'])
        # 实例化一个http选项，可选的，没有特殊需求可以跳过
        httpProfile = HttpProfile(proxy="")
        httpProfile.endpoint = "tmt.tencentcloudapi.com"

        # 实例化一个client选项，可选的，没有特殊需求可以跳过
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        # 实例化要请求产品的client对象,clientProfile是可选的
        client = tmt_client.TmtClient(cred, "ap-beijing", clientProfile)

        reqdata = {
            "SourceText": "\n".join(data),
            "Source": 'zh' if self.source_code.lower()=='zh-cn' else self.source_code,
            "Target": 'zh' if self.target_code.lower()=='zh-cn' else self.target_code,
            "ProjectId": 0,
        }
        if config.params['tencent_termlist']:
            reqdata['TermRepoIDList'] = config.params['tencent_termlist'].split(',')

        req = models.TextTranslateRequest()
        config.logger.info(f'[腾讯]请求数据:{reqdata=}')
        req.from_json_string(json.dumps(reqdata))
        resp = client.TextTranslate(req)
        config.logger.info(f'[腾讯]返回:{resp.TargetText=}')
        return resp.TargetText.strip()
