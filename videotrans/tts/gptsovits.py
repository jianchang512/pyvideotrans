import shutil
import sys
import os
import time

import requests
from videotrans.configure import config
from videotrans.util import tools


def get_voice(*,text=None, role=None,rate=None, language=None, filename=None,set_p=True):
    print(f'{language=}')
    try:
        api_url=config.params['gptsovits_url'].strip().rstrip('/')
        if not api_url:
            raise Exception("必须填写GPT-SoVITS 的 API 地址")
        api_url='http://'+api_url.replace('http://','')
        config.logger.info(f'GPT-SoVITS API:{api_url}')
        text=text.strip()
        if not text:
            return True
        splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }
        if text[-1] not in splits:
            text+='.'
        if len(text)<4:
            text=f'。{text}，。'
        data={"text":text,"text_language": "zh" if language.startswith('zh') else language ,"extra":config.params['gptsovits_extra'],"ostype":sys.platform}
        if role:
            roledict=tools.get_gptsovits_role()
            if role in roledict:
                data.update(roledict[role])
        print(f'{data=}')
        # role=clone是直接复制
        #克隆声音
        response=requests.post(f"{api_url}",json=data,proxies={"http":"","https":""})
        # 获取响应头中的Content-Type
        content_type = response.headers.get('Content-Type')

        if 'application/json' in content_type:
            # 如果是JSON数据，使用json()方法解析
            data = response.json()
            raise Exception(f"GPT-SoVITS返回错误信息-1:{data['message']}")
        if 'audio/wav' in content_type or 'audio/x-wav' in content_type:
            # 如果是WAV音频流，获取原始音频数据
            with open(filename+".wav", 'wb') as f:
                f.write(response.content)
            print(f'{filename=},开始wav2mp3')
            time.sleep(1)
            if not os.path.exists(filename+".wav"):
                return f'GPT-SoVITS合成声音失败-2:{text=}'
            tools.wav2mp3(filename+".wav",filename)
            if os.path.exists(filename+".wav"):
                os.unlink(filename+".wav")
            return True
        else:
            raise Exception(f"GPT-SoVITS合成声音出错-3：{text=},{response.text=}")
    except Exception as e:
        error=str(e)
        if set_p:
            tools.set_process(error)
        config.logger.error(f"{error}")
        raise Exception(f"{error}")
