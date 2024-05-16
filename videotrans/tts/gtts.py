import os

from gtts import gTTS
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
        if not raw_proxy:
            proxy=tools.set_proxy()
            if proxy:
                shound_del=True
                os.environ['http_proxy'] = proxy
                os.environ['https_proxy'] = proxy
                os.environ['all_proxy'] = proxy


def get_voice(*,text=None, role=None, volume="+0%",pitch="+0Hz", rate=None, language=None,filename=None,set_p=True,inst=None):
    update_proxy(type='set')
    try:
        lans=language.split('-')
        if len(lans)>1:
            language=f'{lans[0]}-{lans[1].upper()}'

        response = gTTS(text,lang=language,lang_check=False)
        response.save(filename)
        if tools.vail_file(filename) and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p and inst and inst.precent<80:
            inst.precent+=0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ',btnkey=inst.init['btnkey'] if inst else "")
    except Exception as e:
        error=str(e)
        if error.lower().find('Failed to connect')>-1:
            if inst and inst.init['btnkey']:
                config.errorlist[inst.init['btnkey']]=f'无法连接到 Google，请正确填写代理地址:{error}'
        config.logger.error(f"gtts 合成失败：request error:" + str(e))
        if inst and inst.init['btnkey']:
            config.errorlist[inst.init['btnkey']]=error
        update_proxy(type='del')
        raise Exception(error)
    else:
        update_proxy(type='del')
        return True
