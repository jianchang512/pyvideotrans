
import datetime
import os
from random import random
import time
import numpy as np
import pandas as pd
import re

import torch
import soundfile as sf
from videotrans.util import tools

from videotrans.tts.chatTTSModule import CHATTTS_DIR, chat
from videotrans.tts.chatTTSModule.uilib.cfg import WEB_ADDRESS, SPEAKER_DIR, LOGS_DIR, WAVS_DIR, MODEL_DIR, ROOT_DIR
from videotrans.tts.chatTTSModule.uilib import utils

# def __init__():
    # print('load model chattts')
    # if chat == None:
    #     chat = chatTTS.ChatTTS.ChatTTS.Chat()
    #     chat.load_models(compile=False)
    #     print('load model chattts finish!')
    

def get_voice(*,text=None, role="2222",rate=None, volume="+0%",pitch="+0Hz", language=None, filename=None,set_p=True,inst=None):
    print(f'role={role}')
    data={"text":text.strip(),"voice":role,'prompt':'','is_split':1}
    res = get_file_from_chattts(data)

    tools.wav2mp3(re.sub(r'\\{1,}','/',res['filename']),filename)

def get_file_from_chattts(data):

    # 原始字符串
    text = data.get('text').strip()
    prompt = data.get('prompt').strip()

    # 默认值
    defaults = {
        "custom_voice": 0,
        "voice": 2222,
        "temperature": 0.3,
        "top_p": 0.7,
        "top_k": 20,
        "skip_refine": 0,
        "speed":5,
        "text_seed":42,
        "is_split": 0,
        "refine_max_new_token": 384,
        "infer_max_new_token": 2048,
    }

    voice = int(data.get('voice'))
    is_split = int(data.get('is_split'))

    custom_voice = int(defaults["custom_voice"])
    temperature = float(defaults["temperature"])
    top_p = float(defaults["top_p"])
    top_k = int(defaults["top_k"])
    skip_refine = int(defaults["skip_refine"])
    speed = int(defaults["speed"])
    text_seed = int(defaults["text_seed"])
    refine_max_new_token = int(defaults["refine_max_new_token"])
    infer_max_new_token = int(defaults["infer_max_new_token"])
    
    print(f"[tts]{text=}\n{voice=}\n")

    if not text:
        return None
    
    # 固定音色
    rand_spk=utils.load_speaker(voice)
    if rand_spk is None:    
        print(f'根据seed={voice}获取随机音色')
        torch.manual_seed(voice)
        std, mean = torch.load(f'{CHATTTS_DIR}/asset/spk_stat.pt').chunk(2)
        #rand_spk = chat.sample_random_speaker()        
        rand_spk = torch.randn(768) * std + mean
        # 保存音色
        utils.save_speaker(voice,rand_spk)
    else:
        print(f'固定音色 seed={voice}')

    audio_files = []
    

    start_time = time.time()
    
    # 中英按语言分行
    text_list=[t.strip() for t in text.split("\n") if t.strip()]
    new_text=text_list if is_split==0 else utils.split_text(text_list)
    if text_seed>0:
        torch.manual_seed(text_seed)
    print(f'{text_seed=}')
    print(f'[speed_{speed}]')
    wavs = chat.infer(new_text, use_decoder=True, skip_refine_text=True if int(skip_refine)==1 else False,params_infer_code={
        'spk_emb': rand_spk,
        'prompt':f'[speed_{speed}]',
        'temperature':temperature,
        'top_P':top_p,
        'top_K':top_k,
        'max_new_token':infer_max_new_token
    }, params_refine_text= {'prompt': prompt,'max_new_token':refine_max_new_token},do_text_normalization=False)

    end_time = time.time()
    inference_time = end_time - start_time
    inference_time_rounded = round(inference_time, 2)
    print(f"推理时长: {inference_time_rounded} 秒")

    # 初始化一个空的numpy数组用于之后的合并
    combined_wavdata = np.array([], dtype=wavs[0][0].dtype)  # 确保dtype与你的wav数据类型匹配

    for wavdata in wavs:
        combined_wavdata = np.concatenate((combined_wavdata, wavdata[0]))

    sample_rate = 24000  # Assuming 24kHz sample rate
    audio_duration = len(combined_wavdata) / sample_rate
    audio_duration_rounded = round(audio_duration, 2)
    print(f"音频时长: {audio_duration_rounded} 秒")
    
    
    filename = datetime.datetime.now().strftime('%H%M%S_')+f"use{inference_time_rounded}s-audio{audio_duration_rounded}s-seed{voice}-te{temperature}-tp{top_p}-tk{top_k}-textlen{len(text)}-{str(random())[2:7]}" + ".wav"
    sf.write(WAVS_DIR+'/'+filename, combined_wavdata, 24000)

    audio_files.append({
        "filename": WAVS_DIR + '/' + filename,
        "url": f"http://localhost/static/wavs/{filename}",
        "inference_time": inference_time_rounded,
        "audio_duration": audio_duration_rounded
    })
    result_dict={"code": 0, "msg": "ok", "audio_files": audio_files}
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    # 兼容pyVideoTrans接口调用
    if len(audio_files)==1:
        result_dict["filename"]=audio_files[0]['filename']
        result_dict["url"]=audio_files[0]['url']

    return result_dict

def load_speaker(name):
    speaker_path = f"{SPEAKER_DIR}/{name}.csv"
    if not os.path.exists(speaker_path):
        return None
    try:
        import torch
        d_s = pd.read_csv(speaker_path, header=None).iloc[:, 0]
        tensor = torch.tensor(d_s.values)
    except Exception as e:
        print(e)
        return None
    return tensor