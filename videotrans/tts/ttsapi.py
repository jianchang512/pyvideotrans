import os
import re
import sys

import requests

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.util import tools

shound_del = False


def update_proxy(type='set'):
    global shound_del
    if type == 'del' and shound_del:
        del os.environ['http_proxy']
        del os.environ['https_proxy']
        del os.environ['all_proxy']
        shound_del = False
    elif type == 'set':
        raw_proxy = os.environ.get('http_proxy')
        if not raw_proxy:
            proxy = tools.set_proxy()
            if proxy:
                shound_del = True
                os.environ['http_proxy'] = proxy
                os.environ['https_proxy'] = proxy
                os.environ['all_proxy'] = proxy


def get_voice(*, text=None, role=None, volume="+0%", pitch="+0Hz", rate=None, language=None, filename=None, set_p=True,
              inst=None, uuid=None):
    try:
        api_url = config.params['ttsapi_url'].strip().rstrip('/')
        if len(config.params['ttsapi_url'].strip()) < 10:
            raise Exception(
                'TTSAPI  接口不正确，请到设置中重新填写' if config.defaulelang == 'zh' else 'TTSAPI  interface is not correct, please go to Settings to fill in again')
        config.logger.info(f'TTS-API:api={api_url}')
        if not re.search(r'localhost', api_url) and not re.match(r'https?://(\d+\.){3}\d+', api_url):
            update_proxy(type='set')

        data = {"text": text.strip(), "language": language, "extra": config.params['ttsapi_extra'], "voice": role,
                "ostype": sys.platform, rate: rate}

        resraw = requests.post(f"{api_url}", data=data, verify=False)
        res = resraw.json()
        if "code" not in res or "msg" not in res:
            raise Exception(f'TTS-API:{res}')
        if res['code'] != 0:
            raise Exception(f'TTS-API:{res["msg"]}')

        url = res['data']
        res = requests.get(url)
        if res.status_code != 200:
            raise Exception(f'TTS-API:{url}')
        with open(filename, 'wb') as f:
            f.write(res.content)
        if tools.vail_file(filename) and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p:
            if inst and inst.precent < 80:
                inst.precent += 0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ', type="logs", uuid=uuid)
    except requests.ConnectionError as e:
        raise LogExcept(str(e))
    except Exception as e:
        error = str(e)
        if set_p:
            tools.set_process(error, type="logs", uuid=uuid)
        config.logger.error(f"TTS-API自定义失败:{error}")
        raise LogExcept(e)
    finally:
        if shound_del:
            update_proxy(type='del')
    return True
