# openai
import json
import os
import re
from datetime import timedelta

import zhconv
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.util import tools
import whisper
from whisper.utils import get_writer



def recogn(*,
           detect_language=None,
           audio_file=None,
           cache_folder=None,
           model_name="tiny",
           set_p=True,
           inst=None,
           is_cuda=None):
    print('openai模式')
    if set_p:
        tools.set_process(config.transobj['fengeyinpinshuju'], btnkey=inst.init['btnkey'] if inst else "")
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    noextname = os.path.basename(audio_file)
    tmp_path = f'{cache_folder}/{noextname}_tmp'
    if not os.path.isdir(tmp_path):
        try:
            os.makedirs(tmp_path, 0o777, exist_ok=True)
        except:
            raise Exception(config.transobj["createdirerror"])
    if not tools.vail_file(audio_file):
        raise Exception(f'[error]not exists {audio_file}')
    
    
    raw_subtitles = []

    model = whisper.load_model(
            model_name,
            device="cuda" if is_cuda else "cpu",
            download_root=config.rootdir + "/models"
        )
    last_line=1
    
    inter=1200000
    normalized_sound = AudioSegment.from_wav(audio_file)  # -20.0
    total_length=1+(len(normalized_sound)//inter)

    for i in range(total_length):

        print(f'{i=}')
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):

            return False
        start_time=i*inter
        if i<total_length-1:
            end_time = start_time + inter
        else:
            end_time=len(normalized_sound)


        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        audio_chunk = normalized_sound[start_time:end_time]
        audio_chunk.export(chunk_filename, format="wav")

        text = ""
        try:

            result = model.transcribe(chunk_filename,
                                  language=detect_language,
                                  word_timestamps=True,
                                  initial_prompt=config.settings['initial_prompt_zh'],
                                  condition_on_previous_text=config.settings['condition_on_previous_text']
            )
            srtname=f'{end_time}.srt'

            srt_writer = get_writer("srt", tmp_path)
            srt_writer(result, srtname, {"max_line_count":1,"max_line_width":20 if detect_language.lower()[:2] in ['zh','ja','ko'] else 50})
            with open(tmp_path+f'/{srtname}','r',encoding='utf-8') as f:
                srt_text=f.read()
            tmp_srts=tools.get_subtitle_from_srt(srt_text,is_file=False)
            for n,it in enumerate(tmp_srts):
                print(f'{it["text"]=}')
                if detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
                    tmp_srts[n]['text'] = zhconv.convert(tmp_srts[n]['text'], 'zh-hans')

                tmp_srts[n]['line']=n+last_line
                tmp_srts[n]['start_time']+=start_time
                tmp_srts[n]['end_time']+=start_time
                tmp_srts[n]['endraw'] = tools.ms_to_time_string(ms=tmp_srts[n]['end_time'])
                tmp_srts[n]['startraw'] = tools.ms_to_time_string(ms=tmp_srts[n]['start_time'])
                tmp_srts[n]['time']=f"{tmp_srts[n]['startraw']} --> {tmp_srts[n]['endraw']}"
            raw_subtitles+=tmp_srts


            #clen=
            last_line=len(raw_subtitles)
            if set_p:
                if inst and inst.precent < 75:
                    inst.precent += 0.1
                tools.set_process(f"{config.transobj['yuyinshibiejindu']} {last_line}/{total_length}", btnkey=inst.init['btnkey'] if inst else "")
                
                tools.set_process(srt_text, 'subtitle')
            else:
                tools.set_process_box(text=srt_text, type="set", func_name="shibie")
        except Exception as e:
            print(e)
            #del model
            raise Exception(str(e.args)+str(e))
    if set_p:
        tools.set_process(f"{config.transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}", 'logs',btnkey=inst.init['btnkey'] if inst else "")
    # 写入原语言字幕到目标文件夹


    return raw_subtitles
