import os
import re
import time
import httpx
import requests
from openai import OpenAI, APIError
from videotrans.configure import config
from videotrans.util import tools



def get_voice(*,text=None, role=None, volume="+0%",pitch="+0Hz", rate=None, language=None,filename=None,set_p=True,inst=None):

    try:
        speed=1.0
        if rate:
            rate=float(rate.replace('%',''))/100
            speed+=rate
        try:
            response=requests.post('https://api.302.ai/v1/audio/speech',headers= {
               'Authorization': f'Bearer {config.params["ai302tts_key"]}',
               'User-Agent': 'python',
               'Content-Type': 'application/json'
            },json={
                "model": config.params['ai302tts_model'],
                "input": text,
                "voice": role,
                "speed":speed
            },verify=False)
            if response.status_code !=200:
                raise Exception(response.text)
            with open(filename,'wb') as f:
                f.write(response.content)
        except ConnectionError as e:
            raise
        except Exception as e:
            raise
        if tools.vail_file(filename) and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p and inst and inst.precent<80:
            inst.precent+=0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ',btnkey=inst.init['btnkey'] if inst else "")
    except Exception as e:
        error=str(e)
        config.logger.error(f"302.ai tts 合成失败：request error:" + str(e))
        if inst and inst.init['btnkey']:
            config.errorlist[inst.init['btnkey']]=error
        raise
    else:
        return True

