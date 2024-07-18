import base64
import shutil
import sys
import os
import time
from pathlib import Path

import requests
from videotrans.configure import config
from videotrans.util import tools
def wav_to_base64(file_path):
    if not file_path or not Path(file_path).exists():
        return None
    with open(file_path, "rb") as wav_file:
        wav_content = wav_file.read()
        base64_encoded = base64.b64encode(wav_content)
        return base64_encoded.decode("utf-8")


def get_voice(*,text=None, role=None,rate=None, volume="+0%",pitch="+0Hz", language=None, filename=None,set_p=True,inst=None):
    try:
        api_url=config.params['cosyvoice_url'].strip().rstrip('/').lower()
        if not api_url:
            raise Exception("必须填写CosyVoice  的 API 地址")
        api_url='http://'+api_url.replace('http://','')
        config.logger.info(f'CosyVoice  API:{api_url}')
        text=text.strip()
        
        if api_url.endswith(':9880'):
            data={
                "text":text,
                "speed":1+float(rate.replace('%','')),
                "new":0,
                
            }
            if not text:
                return True
            rolelist=tools.get_cosyvoice_role()
            if role=='clone':
                #克隆音色
                data['speaker']='中文女'
            elif role in rolelist:
                data['speaker']=rolelist[role]
            else:
                data['speaker']='中文女'
            #克隆声音
            response=requests.post(f"{api_url}",json=data,proxies={"http":"","https":""},timeout=3600)
        else:
            data={"text":text,
                  "lang": "zh" if language.startswith('zh') else language
            }
            if not text:
                return True
            rolelist=tools.get_cosyvoice_role()
            if role=='clone':
                #克隆音色
                data['reference_audio']=wav_to_base64(filename)
                api_url+='/clone_mul'
                data['encode']='base64'
            elif role and role.endswith('.wav'):
                data['reference_audio']= rolelist[role]['reference_audio'] if role in rolelist else None
                if not data['reference_audio']:
                    raise Exception(f'{role} 角色错误-2')
                api_url+='/clone_mul'
            elif role in rolelist:
                data['role']=rolelist[role]
                api_url+='/tts'
            else:
                data['role']='中文女'
            #克隆声音
            response=requests.post(f"{api_url}",data=data,proxies={"http":"","https":""},timeout=3600)
        
        
        
        
        if response.status_code!=200:
            # 如果是JSON数据，使用json()方法解析
            data = response.json()
            raise Exception(f"CosyVoice 返回错误信息-1:{data['msg']}")

        # 如果是WAV音频流，获取原始音频数据
        with open(filename+".wav", 'wb') as f:
            f.write(response.content)
        time.sleep(1)
        if not os.path.exists(filename+".wav"):
            raise Exception(f'CosyVoice 合成声音失败-2:{text=}')
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
            tools.set_process(error,btnkey=inst.init['btnkey'] if inst else "")
        if inst and inst.init['btnkey']:
            config.errorlist[inst.init['btnkey']]=error
        config.logger.error(f"{error}")
        raise
    else:
        return True