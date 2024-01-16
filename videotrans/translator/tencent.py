import json
import re
import time

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tmt.v20180321 import tmt_client, models
from videotrans.configure import config
from videotrans.configure.config import logger
from videotrans.util  import tools

def tencenttrans(text, src, dest,*,set_p=True):
    try:
        # 实例化一个认证对象，入参需要传入腾讯云账户 SecretId 和 SecretKey，此处还需注意密钥对的保密
        # 代码泄露可能会导致 SecretId 和 SecretKey 泄露，并威胁账号下所有资源的安全性。以下代码示例仅供参考，建议采用更安全的方式来使用密钥，请参见：https://cloud.tencent.com/document/product/1278/85305
        # 密钥可前往官网控制台 https://console.cloud.tencent.com/cam/capi 进行获取
        cred = credential.Credential(config.params['tencent_SecretId'], config.params['tencent_SecretKey'])
        # 实例化一个http选项，可选的，没有特殊需求可以跳过
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tmt.tencentcloudapi.com"

        # 实例化一个client选项，可选的，没有特殊需求可以跳过
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        # 实例化要请求产品的client对象,clientProfile是可选的
        client = tmt_client.TmtClient(cred, "ap-beijing", clientProfile)

        # 实例化一个请求对象,每个接口都会对应一个request对象
        req = models.TextTranslateRequest()
        params = {
            "SourceText": text,
            "Source": "auto",
            "Target": dest,
            "ProjectId": 0
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个TextTranslateResponse的实例，与请求对象对应
        resp = client.TextTranslate(req)
        return resp.TargetText
    except Exception as e:
        err=str(e)
        if re.search(r'LimitExceeded',err,re.I):
            if set_p:
                tools.set_process("超出腾讯翻译频率或配额限制，暂停5秒")
            time.sleep(5)
            return tencenttrans(text, src, dest,set_p=set_p)
        logger.error("tencent api error:" + str(e))
        if set_p:
            tools.set_process("[error]腾讯翻译失败:" + str(e))
        return "tencent api error:" + str(e)
