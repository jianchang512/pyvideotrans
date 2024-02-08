import shutil
import requests
from videotrans.configure import config
from videotrans.util import tools


def get_voice(*,text=None, role=None,rate=None, language=None, filename=None,set_p=True):

    try:
        api_url=config.params['clone_api'].strip().rstrip('/')
        if not api_url:
            raise Exception("get_voice:"+config.transobj['bixutianxiecloneapi'])
        api_url='http://'+api_url.replace('http://','')
        config.logger.info(f'clone-voice:api={api_url}')
        print(f'{api_url=}')

        data={"text":text.strip(),"language":language}
        # role=clone是直接复制
        if role!='clone':
            #不是克隆，使用已有声音
            data['voice']=role
            files=None
        else:
            #克隆声音
            files={"audio":open(filename,'rb')}
        res=requests.post(f"{api_url}/apitts",data=data,files=files,proxies={"http":"","https":""})
        res=res.json()
        if "code" not in res or res['code']!=0:
            raise Exception(f'[error]clone:{res}')
        if api_url.find('127.0.0.1')>-1:
            shutil.copy2(res['filename'],filename)
        else:
            res=requests.get(res['url'])
            if res.status_code!=200:
                raise Exception(f'[error]save {res["url"]}')
            with open(filename,'wb') as f:
                f.write(res.content)
        return True
    except Exception as e:
        error=str(e)
        if set_p:
            tools.set_process(error)
        config.logger.error(f"cloneVoice合成失败:{error},{api_url=}")
        raise Exception(f"cloneVoice 合成失败:{error}")
