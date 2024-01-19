# -*- coding: utf-8 -*-
import hashlib
import time
import requests
from videotrans.configure import config


def baidutrans(text, src, dest, *, set_p=True):
    # 拼接appid = 2015063000000001 + q = apple + salt = 1435660288 + 密钥 = 12345678
    salt = int(time.time())
    strtext = f"{config.params['baidu_appid']}{text}{salt}{config.params['baidu_miyue']}"
    md5 = hashlib.md5()
    md5.update(strtext.encode('utf-8'))
    sign = md5.hexdigest()
    try:
        res = requests.get(
            f"http://api.fanyi.baidu.com/api/trans/vip/translate?q={text}&from=auto&to={dest}&appid={config.params['baidu_appid']}&salt={salt}&sign={sign}")
        res = res.json()
        if "error_code" in res:
            raise Exception("[error]百度翻译失败:" + res['error_msg'])
        comb = ""
        if "trans_result" in res:
            comb = ""
            for it in res['trans_result']:
                comb += it['dst']
        return comb
    except Exception as e:
        config.logger.error("baidu api error:" + str(e))
        raise Exception("[error]百度翻译失败:" + str(e))
