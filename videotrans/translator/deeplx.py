# -*- coding: utf-8 -*-

import httpx
import json

from ..configure import config
from ..util import tools
from ..configure.config import logger


def deeplxtrans(text, to_lang):
    data = {
        "text": text,
        "source_lang": "auto",
        "target_lang": to_lang[:2]
    }
    logger.info(f"deeplx:{data=}")
    try:
        url=config.video['deeplx_address'].replace('/translate','')+'/translate'
        if not url.startswith('http'):
            url=f"http://{url}"
        response = httpx.post(url=url,data=json.dumps(data))
        try:
            result = response.json()
        except Exception as e:
            msg=f"[error]deeplx翻译出错:返回内容 "+response.text
            logger.error(msg)
            tools.set_process(msg)
            return msg
        if response.status_code != 200 or result['code'] != 200:
            logger.error(f"[error]deeplx translate:{result=}")
            return f"[error]deeplx translate:{response.status_code=},{result['code']=}"
        return result['data']
    except Exception as e:
        res = f"[error]DeepLX翻译出错:" + str(e)
        tools.set_process(res)
        logger.error(f"deeplx error:{res=}")
        return res
