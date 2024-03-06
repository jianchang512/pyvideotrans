import shutil
import sys

import requests
from videotrans.configure import config
from videotrans.util import tools


def get_voice(*,text=None, role=None,rate=None, language=None, filename=None,set_p=True):

    try:
        api_url=config.params['ttsapi_url'].strip().rstrip('/')
        if not api_url:
            raise Exception("get_voice:"+config.transobj['ttsapi_nourl'])
        config.logger.info(f'TTS-API:api={api_url}')

        data={"text":text.strip(),"language":language,"extra":config.params['ttsapi_extra'],"voice":role,"ostype":sys.platform,rate:rate}
        # role=clone是直接复制
        #克隆声音
        # files={"audio":open(filename,'rb')} files=files,
        print(f'{api_url=}')
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
            return True
        except:
            raise Exception(f"返回非标准json数据:{resraw.text}" if config.defaulelang=='zh' else f"The return data is not in standard json format:{resraw.text}")
    except Exception as e:
        error=str(e)
        if set_p:
            tools.set_process(error)
        config.logger.error(f"TTS-API自定义失败:{error}")
        raise Exception(f"TTS-API:{error}")
