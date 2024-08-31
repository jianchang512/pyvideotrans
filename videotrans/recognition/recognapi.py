# zh_recogn 识别
import requests

from videotrans.configure import config
from videotrans.util import tools


def recogn(*,
           audio_file=None,
           cache_folder=None,
           uuid=None,
           set_p=None,
           inst=None):
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    api_url = config.params['recognapi_url'].strip().rstrip('/').lower()
    if not api_url:
        raise Exception('必须填写自定义api地址' if config.defaulelang == 'zh' else 'Custom api address must be filled in')
    if not api_url.startswith('http'):
        api_url = f'http://{api_url}'
    if config.params['recognapi_key']:
        if api_url.find('?') > 0:
            api_url += f'&sk={config.params["recognapi_key"]}'
        else:
            api_url += f'?sk={config.params["recognapi_key"]}'
    files = {"audio": open(audio_file, 'rb')}

    if set_p:
        tools.set_process(
            f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient',
            type='logs',
            uuid=uuid)
    try:
        res = requests.post(f"{api_url}", files=files, proxies={"http": "", "https": ""}, timeout=3600)
        config.logger.info(f'RECOGN_API:{res=}')
    except Exception as e:
        raise
    else:
        res = res.json()
        if "code" not in res or res['code'] != 0:
            raise Exception(f'{res["msg"]}')
        if "data" not in res or len(res['data']) < 1:
            raise Exception('识别出错')
        '''
        请求发送：以二进制形式发送键名为 audio 的wav格式音频数据，采样率为16k、通道为1
        requests.post(api_url, files={"audio": open(audio_file, 'rb')})
        
        失败时返回
        res={
            "code":1,
            "msg":"错误原因"
        }
        
        成功时返回
        res={
            "code":0,
            "data":[
                {
                    "text":"字幕文字",
                    "time":'00:00:01,000 --> 00:00:06,500'
                },
                {
                    "text":"字幕文字",
                    "time":'00:00:06,900 --> 00:00:12,200'
                },
            ]
        }
        '''
        return res['data']
