import re
import shutil
import requests
from videotrans.configure import config
from videotrans.util import tools


def get_voice(*,text=None, role=None,rate=None, language=None, filename=None,set_p=True):

    try:
        api_url=config.params['clone_api']
        m=re.match(r'^(https?://[\w.:-]+)/?',api_url)
        if not m:
            raise Exception(config.transobj['You must deploy and start the clone-voice service'])
        data={"text":text.strip(),"language":language}
        # role=clone是直接复制
        if role!='clone':
            #不是克隆，使用已有声音
            data['voice']=role
            files=None
        else:
            #克隆声音
            files={"audio":open(filename,'rb')}
        res=requests.post(f"{m.groups()[0]}/apitts",data=data,files=files)
        res=res.json()
        if "code" not in res or res['code']!=0:
            raise Exception(f'[error]clone:{res}')
        tmpname=""
        if re.match(r'^https?://127\.0\.0\.1',api_url):
            #tmpname=res['filename']
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
        config.logger.error(f"cloneVoice合成失败:{error}")
        raise Exception(f"cloneVoice 合成失败:{error}")
