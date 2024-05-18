import os
import re
import time
import httpx
from openai import OpenAI, APIError
from videotrans.configure import config
from videotrans.util import tools


shound_del=False
def update_proxy(type='set'):
    global shound_del
    if type=='del' and shound_del:
        del os.environ['http_proxy']
        del os.environ['https_proxy']
        del os.environ['all_proxy']
        shound_del=False
    elif type=='set':
        raw_proxy=os.environ.get('http_proxy')
        print(f'当前代理:{raw_proxy=}')
        if not raw_proxy:
            proxy=tools.set_proxy()
            if proxy:
                print(f'设置代理:{proxy=}')
                shound_del=True
                os.environ['http_proxy'] = proxy
                os.environ['https_proxy'] = proxy
                os.environ['all_proxy'] = proxy


def get_url(url=""):
    
    if not url.startswith('http'):
        url='http://'+url    
    # 删除末尾 /
    url=url.rstrip('/').lower()
    if not url or url.find(".openai.com")>-1:
        return "https://api.openai.com/v1"
    # 存在 /v1/xx的，改为 /v1
    if re.match(r'.*/v1/(chat)?(/?completions)?$',url):
        return re.sub(r'/v1.*$','/v1',url)
    # 不是/v1结尾的改为 /v1
    if url.find('/v1')==-1:
        return url+"/v1"
    return url

def get_voice(*,text=None, role=None, volume="+0%",pitch="+0Hz", rate=None, language=None,filename=None,set_p=True,inst=None):
    api_url=get_url(config.params['chatgpt_api'])
    if not re.search(r'localhost',api_url) and not re.match(r'https?://(\d+\.){3}\d+',api_url):
        update_proxy(type='set')
    try:
        speed=1.0
        if rate:
            rate=float(rate.replace('%',''))/100
            speed+=rate
        try:
            client = OpenAI(base_url=api_url, http_client=httpx.Client())
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
        if tools.vail_file(filename) and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p and inst and inst.precent<80:
            inst.precent+=0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ',btnkey=inst.init['btnkey'] if inst else "")
    except Exception as e:
        error=str(e)
        if error.lower().find('connect timeout')>-1 or error.lower().find('ConnectTimeoutError')>-1:
            if inst and inst.init['btnkey']:
                config.errorlist[inst.init['btnkey']]=f'无法连接到 {api_url}，请正确填写代理地址:{error}'
            return False
        if error and re.search(r'Rate limit',error,re.I) is not None:
            if set_p:
                tools.set_process(f'chatGPT请求速度被限制，暂停30s后自动重试',btnkey=inst.init['btnkey'] if inst else "")
            time.sleep(30)
            return get_voice(text=text, role=role, rate=rate, filename=filename)
        config.logger.error(f"openaiTTS合成失败：request error:" + str(e))
        if inst and inst.init['btnkey']:
            config.errorlist[inst.init['btnkey']]=error
        update_proxy(type='del')
        raise Exception(error)
    else:
        return True
    finally:
        update_proxy(type='del')

