import os
import re
import time
import httpx
from openai import OpenAI, APIError
from videotrans.configure import config
from videotrans.util import tools

def get_url(url=""):
    if not url or url.find(".openai.com")>-1:
        return "https://api.openai.com/v1"
    url=url.rstrip('/').lower()
    if not url.startswith('http'):
        url='http://'+url
    if re.match(r'.*/v1/(chat/)?completions/?$',url):
        return re.sub(r'/v1/.*$','/v1',url)
    if re.match(r'^https?://[^/]+?$',url):
        return url+"/v1"
    return url

def get_voice(*,text=None, role=None, rate=None, language=None,filename=None,set_p=True,is_test=False,inst=None):
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
        if config.current_status != 'ing' and config.box_tts != 'ing' and not is_test:
            return False
        speed=1.0
        if rate:
            rate=float(rate.replace('%',''))/100
            speed+=rate
        try:
            client = OpenAI(base_url=api_url, http_client=httpx.Client(proxies=proxies))
            response = client.audio.speech.create(
                model="tts-1",
                voice=role,
                input=text,
                speed=speed
            )
            response.stream_to_file(filename)
        except APIError as e:
            raise Exception(f'{e.message=}')
        except Exception as e:
            raise Exception(e)
        if os.path.exists(filename) and os.path.getsize(filename)>0 and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p and inst and inst.precent<80:
            inst.precent+=0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ',btnkey=inst.btnkey if inst else "")
    except Exception as e:
        error=str(e)
        if error.lower().find('connect timeout')>-1 or error.lower().find('ConnectTimeoutError')>-1:
            if inst and inst.btnkey:
                config.errorlist[inst.btnkey]=f'无法连接到 {api_url}，请正确填写代理地址:{error}'
            return False
        if error and re.search(r'Rate limit',error,re.I) is not None:
            if set_p:
                tools.set_process(f'chatGPT请求速度被限制，暂停30s后自动重试',btnkey=inst.btnkey if inst else "")
            time.sleep(30)
            return get_voice(text=text, role=role, rate=rate, filename=filename)
        config.logger.error(f"openaiTTS合成失败：request error:" + str(e))
        if inst and inst.btnkey:
            config.errorlist[inst.btnkey]=error

