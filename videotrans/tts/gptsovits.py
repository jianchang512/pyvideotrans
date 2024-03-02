import shutil
import sys

import requests
from videotrans.configure import config
from videotrans.util import tools


def get_voice(*,text=None, role=None,rate=None, language=None, filename=None,set_p=True):

    try:
        api_url=config.params['gptsovits_url'].strip().rstrip('/')
        if not api_url:
            raise Exception("必须填写GPT-SoVITS 的 API 地址")
        api_url='http://'+api_url.replace('http://','')
        config.logger.info(f'GPT-SoVITS API:{api_url}')

        data={"text":text.strip(),"text_language": "zh" if language.startswith('zh') else language ,"extra":config.params['gptsovits_extra'],"ostype":sys.platform}
        if role:
            roledict=tools.get_gptsovits_role()
            if role in roledict:
                data.update(roledict[role])
        print(f'{data=}')
        # role=clone是直接复制
        #克隆声音
        response=requests.post(f"{api_url}",json=data,proxies={"http":"","https":""})
        try:
            # 获取响应头中的Content-Type
            content_type = response.headers.get('Content-Type')

            if 'application/json' in content_type:
                # 如果是JSON数据，使用json()方法解析
                data = response.json()
                raise Exception(data['message'])
            elif 'audio/wav' in content_type or 'audio/x-wav' in content_type:
                # 如果是WAV音频流，获取原始音频数据
                
                with open(filename+".wav", 'wb') as f:
                    f.write(response.content)
                tools.wav2mp3(filename+".wav",filename)
                return True
            else:
                raise Exception("请求GPTSoVITS出现未知错误")
        except Exception as e:
            raise Exception(f"请求GPT-SoVITS出错：{str(e)}")
    except Exception as e:
        error=str(e)
        if set_p:
            tools.set_process(error)
        config.logger.error(f"{error}")
        raise Exception(f"{error}")
