import os

import requests
from gtts import gTTS

from videotrans.configure import config
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
    update_proxy(type='set')
    try:
        lans = language.split('-')
        if len(lans) > 1:
            language = f'{lans[0]}-{lans[1].upper()}'

        response = gTTS(text, lang=language, lang_check=False)
        response.save(filename)
        if tools.vail_file(filename) and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p:
            if inst and inst.precent < 80:
                inst.precent += 0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ', type="logs", uuid=uuid)
    except requests.ConnectionError as e:
        config.logger.exception(e)
        raise Exception(str(e))
    except Exception as e:
        config.logger.exception(e)
        raise
    finally:
        if shound_del:
            update_proxy(type='del')
    return True
