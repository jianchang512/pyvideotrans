import os
import re
import time

import httpx

from openai import OpenAI
from videotrans.configure import config
from videotrans.configure.config import logger
from videotrans.util import tools


def get_voice(text, role, rate, filename):
    proxies = None
    if config.video['proxy']:
        proxies = {
            'http://': 'http://%s' % config.video['proxy'].replace("http://", ''),
            'https://': 'http://%s' % config.video['proxy'].replace("http://", '')
        }
    else:
        serv = os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY')
        if serv:
            proxies = {
                'http://': 'http://%s' % serv.replace("http://", ''),
                'https://': 'http://%s' % serv.replace("http://", '')
            }
    try:
        speed=1.0
        if rate:
            rate=float(rate.replace('%',''))/100
            speed+=rate
        client = OpenAI(base_url=None if not config.video['chatgpt_api'] else config.video['chatgpt_api'], http_client=httpx.Client(proxies=proxies))
        response = client.audio.speech.create(
            model="tts-1",
            voice=role,
            input=text,
            speed=speed
        )
        response.stream_to_file(filename)
        return True
    except Exception as e:
        error=str(e)
        if error and re.search(r'Rate limit',error,re.I) is not None:
            tools.set_process(f'chatGPT请求速度被限制，暂停30s后自动重试')
            time.sleep(30)
            return get_voice(text, role, rate, filename)
        logger.error(f"openaiTTS合成失败：request error:" + str(e))
        tools.set_process(f"openaiTTS 合成失败：request error:" + str(e))
    return False
