import os
import sys

import requests
from videotrans.configure import config
from videotrans.util import tools


def get_voice(*,text=None, role=None,rate=None, language=None, filename=None,set_p=True,is_test=False,inst=None):

    try:
        api_url=config.params['ttsapi_url'].strip().rstrip('/')
        if not api_url:
            raise Exception("get_voice:"+config.transobj['ttsapi_nourl'])
        config.logger.info(f'TTS-API:api={api_url}')
        if config.current_status != 'ing' and config.box_tts != 'ing' and not is_test:
            return False
        data={"text":text.strip(),"language":language,"extra":config.params['ttsapi_extra'],"voice":role,"ostype":sys.platform,rate:rate}

        resraw=requests.post(f"{api_url}",data=data,proxies={"http":"","https":""},verify=False)
        try:
            res=resraw.json()
            if "code" not in res or "msg" not in res:
                raise Exception(f'TTS-API:{res}')
            if res['code']!=0:
                raise Exception(f'TTS-API:{res["msg"]}')

            url=res['data']
            res=requests.get(url)
            if res.status_code!=200:
                raise Exception(f'TTS-API:{url}')
            with open(filename,'wb') as f:
                f.write(res.content)
            if os.path.exists(filename) and os.path.getsize(filename)>0 and config.settings['remove_silence']:
                tools.remove_silence_from_end(filename)
            if set_p and inst and inst.precent < 80:
                inst.precent += 0.1
                tools.set_process(f'{config.transobj["kaishipeiyin"]} ', btnkey=inst.btnkey if inst else "")
        except:
            raise Exception(f"返回非标准json数据:{resraw.text}" if config.defaulelang=='zh' else f"The return data is not in standard json format:{resraw.text}")
    except Exception as e:
        error=str(e)
        if set_p:
            tools.set_process(error,btnkey=inst.btnkey if inst else "")
        config.logger.error(f"TTS-API自定义失败:{error}")
        if inst and inst.btnkey:
            config.errorlist[inst.btnkey]=error
