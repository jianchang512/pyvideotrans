# -*- coding: utf-8 -*-

import httpx
import json

from videotrans.configure import config
from videotrans.util import tools


def deeplxtrans(text, to_lang,*,set_p=True):
    data = {
        "text": text,
        "source_lang": "auto",
        "target_lang": "ZH" if to_lang.startswith('zh') else to_lang
    }
    config.logger.info(f"deeplx:{data=}")
    try:
        url=config.params['deeplx_address'].replace('/translate','')+'/translate'
        if not url.startswith('http'):
            url=f"http://{url}"
        response = httpx.post(url=url,data=json.dumps(data))
        try:
            result = response.json()
        except Exception as e:
            msg=f"[error]deeplx error: "+response.text
            config.logger.error(msg)
            if set_p:
                tools.set_process(msg)
            return msg
        if response.status_code != 200 or result['code'] != 200:
            config.logger.error(f"[error]deeplx translate:{result=}")
            return f"[error]deeplx translate:{response.status_code=},{result['code']=}"
        return result['data']
    except Exception as e:
        res = f"[error]DeepLX error:" + str(e)
        if set_p:
            tools.set_process(res)
        config.logger.error(f"deeplx error:{res=}")
        return res
