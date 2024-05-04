# zh_recogn 识别
from videotrans.configure import config
from videotrans.util import tools


def recogn(*,
           audio_file=None,
           cache_folder=None,
           set_p=None,
           inst=None):
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    api_url = config.params['zh_recogn_api'].strip().rstrip('/').lower()
    if not api_url:
        raise Exception('必须填写地址')
    if not api_url.startswith('http'):
        api_url = f'http://{api_url}'
    if not api_url.endswith('/api'):
        api_url += '/api'
    files = {"audio": open(audio_file, 'rb')}
    import requests
    if set_p:
        tools.set_process(f"识别可能较久，请耐心等待，进度可查看zh_recogn终端", 'logs', btnkey=inst.init['btnkey'] if inst else "")
    try:
        res = requests.post(f"{api_url}", files=files, proxies={"http": "", "https": ""}, timeout=3600)
        config.logger.info(f'zh_recogn:{res=}')
    except Exception as e:
        raise Exception(e)
    else:
        res = res.json()
        if "code" not in res or res['code'] != 0:
            raise Exception(f'{res["msg"]}')
        if "data" not in res or len(res['data']) < 1:
            raise Exception('识别出错')
        return res['data']
