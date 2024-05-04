import os
import re
import shutil
import time
from pathlib import Path

import requests
from videotrans.configure import config
from videotrans.util import tools


def get_voice(*,text=None, role=None,rate=None, volume="+0%",pitch="+0Hz", language=None, filename=None,set_p=True,inst=None):
    try:
        api_url=config.params['clone_api'].strip().rstrip('/').lower()
        if not api_url:
            raise Exception("get_voice:"+config.transobj['bixutianxiecloneapi'])

        api_url='http://'+api_url.replace('http://','')
        config.logger.info(f'clone-voice:api={api_url}')
        splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }
        text=text.strip()
        if text[-1] not in splits:
            text+='.'
        data={"text":text,"language":language}

        # role=clone是直接复制
        if role!='clone':
            #不是克隆，使用已有声音
            data['voice']=role
            files=None
        else:
            #克隆声音
            files={"audio":open(filename,'rb')}
        res=requests.post(f"{api_url}/apitts",data=data,files=files,proxies={"http":"","https":""},timeout=3600)
        config.logger.info(f'clone-voice:{data=},{res.text=}')

        res=res.json()
        if "code" not in res or res['code']!=0:
            if "msg" in  res and res['msg'].find("non-empty")>0:
                Path(filename).unlink(missing_ok=True)
                return True
            raise Exception(f'{res}')
        if api_url.find('127.0.0.1')>-1 or api_url.find('localhost')>-1:
            tools.wav2mp3(re.sub(r'\\{1,}','/',res['filename']),filename)
        else:
            resb=requests.get(res['url'])
            if resb.status_code!=200:
                raise Exception(f'clonevoice:{res["url"]=}')
            config.logger.info(f'clone-voice:resb={resb.status_code=}')
            with open(filename+".wav",'wb') as f:
                f.write(resb.content)
            time.sleep(1)
            tools.wav2mp3(filename+".wav",filename)
            if os.path.exists(filename+".wav"):
                os.unlink(filename+".wav")
            if tools.vail_file(filename) and config.settings['remove_silence']:
                tools.remove_silence_from_end(filename)
            if set_p and inst and inst.precent < 80:
                inst.precent += 0.1
                tools.set_process(f'{config.transobj["kaishipeiyin"]} ', btnkey=inst.init['btnkey'] if inst else "")
    except Exception as e:
        error=str(e)
        if set_p:
            tools.set_process(error,btnkey=inst.init['btnkey'] if inst else  "")
        config.logger.error(f"cloneVoice合成失败:{error}")
        if inst and inst.init['btnkey']:
            config.errorlist[inst.init['btnkey']]=error
        raise Exception(error)
    else:
        return True