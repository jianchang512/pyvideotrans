# zh_recogn 识别
from videotrans.configure import config
from videotrans.util import tools
import os


def recogn(*,
           detect_language=None,
           audio_file=None,
           cache_folder=None,
           model_name="tiny",
           set_p=True,
           inst=None,
           is_cuda=None):
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    
    base_url = 'https://openspeech.bytedance.com/api/v1/vc'
    # 应用 APP ID
        
    appid = config.params['doubao_appid']
    access_token=config.params['doubao_access']
    if not appid or not access_token:
        raise Exception('必须填写豆包应用APP ID和 Access Token')

    files = None
    # 尺寸大于190MB，转为 mp3
    if os.path.getsize(audio_file)>199229440:
        tools.runffmpeg(['-y','-i',audio_file,'-ac','1','-ar','16000',cache_folder+'/doubao-tmp.mp3'])
        audio_file=cache_folder+'/doubao-tmp.mp3'
    with open(audio_file,'rb') as f:
        files=f.read()
    if files is None:
        raise Exception('读取音频文件失败')
    import requests
    if set_p:
        tools.set_process(f"识别可能较久，请耐心等待", 'logs', btnkey=inst.init['btnkey'] if inst else "")
    
    languagelist={"zh":"zh-CN","en":"en-US","ja":"ja-JP","ko":"ko-KR","es":"es-MX","ru":"ru-RU","fr":"fr-FR"}
    langcode=detect_language[:2].lower()
    if langcode not in languagelist:
        raise Exception(f'不支持的语言代码:{langcode=}')
    language=languagelist[langcode]
    
    try:
        res = requests.post(f'{base_url}/submit' , 
            data=files, 
            proxies={"http": "", "https": ""}, 
            params=dict(
                     appid=appid,
                     language=language,
                     use_itn='True',
                     caption_type='speech',
                     max_lines=1#每条字幕只允许一行文字
                     #words_per_line=15,#每行文字最多15个字符
            ),
            headers={
                    'Content-Type': 'audio/wav',
                    'Authorization': 'Bearer; {}'.format(access_token)
            },
            timeout=3600)
        config.logger.info(f'zh_recogn:{res.text}')
        if res.status_code != 200:
            raise Exception(f'请求失败:{res.text=},{res.status_code=},{base_url=}')
        res=res.json()
        if res['code']!=0:
            raise Exception(f'请求失败:{res["message"]}')
        
        job_id = res['id']
        # 获取进度
        response = requests.get(
                '{base_url}/query'.format(base_url=base_url),
                params=dict(
                    appid=appid,
                    id=job_id,
                ),
                proxies={"http": "", "https": ""}, 
                headers={
                   'Authorization': 'Bearer; {}'.format(access_token)
                }
        )
        if response.status_code != 200:
            raise Exception(f'查询任务进度失败:{response.status_code=},{response.text=}')
        
        result=response.json()
        
        srts=[]
        for i,it in enumerate(result['utterances']):
            srt={
                "line":i+1,
                "start_time":it['start_time'],
                "end_time":it['end_time'],
                "endraw":tools.ms_to_time_string(ms=it["end_time"]),
                "startraw":tools.ms_to_time_string(ms=it["start_time"]),                
                "text":it['text']
            }
            srt['time']=f'{srt["startraw"]} --> {srt["endraw"]}'
            srts.append(srt)
        return srts
        
    except Exception as e:
        raise Exception(e)