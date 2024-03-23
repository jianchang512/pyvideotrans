import os
import re
import time
import httpx
from openai import OpenAI
from videotrans.configure import config
from videotrans.util import tools

def get_url(url=""):
    if not url or url.find(".openai.com")>-1:
        return "https://api.openai.com/v1"
    url=url.rstrip('/').lower()
    if not url.startswith('http'):
        url='http://'+url
    if not url.endswith('/v1'):
        return url+"/v1"
    return "https://api.openai.com/v1"

def get_voice(*,text=None, role=None, rate=None, language=None,filename=None,set_p=True):
    api_url=get_url(config.params['chatgpt_api'])
    proxies=None
    if not re.search(r'localhost',api_url) and not re.match(r'https?://(\d+\.){3}\d+',api_url):
        serv = tools.set_proxy()
        if serv:
            proxies = {
                'http://': serv,
                'https://': serv
            }
    try:
        if config.current_status != 'ing' and config.box_tts != 'ing':
            return False
        speed=1.0
        if rate:
            rate=float(rate.replace('%',''))/100
            speed+=rate
        print(f'{api_url=}')
        client = OpenAI(base_url=api_url, http_client=httpx.Client(proxies=proxies))
        response = client.audio.speech.create(
            model="tts-1",
            voice=role,
            input=text,
            speed=speed
        )
        response.stream_to_file(filename)
        if os.path.exists(filename) and os.path.getsize(filename)>0 and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
    except Exception as e:
        error=str(e)
        if error and re.search(r'Rate limit',error,re.I) is not None:
            if set_p:
                tools.set_process(f'chatGPT请求速度被限制，暂停30s后自动重试')
            time.sleep(30)
            return get_voice(text=text, role=role, rate=rate, filename=filename)
        config.logger.error(f"openaiTTS合成失败：request error:" + str(e))
        raise Exception(f" openaiTTS:" + str(e))
