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
    def output(srt,linenums):
        if set_p:
            if inst and inst.precent < 75:
                inst.precent += 0.1
            tools.set_process(f"{config.transobj['yuyinshibiejindu']} {linenums} line",
                              btnkey=inst.init['btnkey'] if inst else "")
            tools.set_process(f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n', 'subtitle')
        else:
            tools.set_process_box(text=f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n', type="set", func_name="shibie")
    
    inter=1200000
    normalized_sound = AudioSegment.from_wav(audio_file)  # -20.0
    total_length=1+(len(normalized_sound)//inter)

    raws = []
    flag = [
                ",",
                ":",
                "'",
                "\"",
                ".",
                "?",
                "!",
                ";",
                ")",
                "]",
                "}",
                ">",
                "，",
                "。",
                "？",
                "；",
                "’",
                "”",
                "》",
                "】",
                "｝",
                "！",
                " "
            ]
    maxlen = config.settings['cjk_len'] if detect_language[:2].lower() in ['zh', 'ja', 'ko'] else config.settings['other_len']
    minlen = 2 if detect_language[:2].lower() in ['zh', 'ja', 'ko'] else maxlen
    for i in range(total_length):
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
        try:
            result = model.transcribe(chunk_filename,
                                  language=detect_language,
                                  word_timestamps=True,
                                  initial_prompt=config.settings['initial_prompt_zh'],
                                  condition_on_previous_text=config.settings['condition_on_previous_text']
            )
            for segment in result['segments']:
                if len(segment['text'].strip()) <= maxlen:
                    tmp = {
                        "line": len(raws) + 1,
                        "start_time": int(segment['words'][0]["start"] * 1000)+start_time,
                        "end_time": int(segment['words'][-1]["end"] * 1000)+start_time,
                        "text": segment["text"].strip()
                    }
                    tmp["time"] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                    output(tmp,len(raws)+1)
                    tmp['text']=tmp['text'].strip()
                    raws.append(tmp)
                    continue

                cur = None
                for word in segment["words"]:
                    if not cur:
                        cur = {
                            "line": len(raws)  + 1,
                            "start_time": int(word["start"] * 1000)+start_time,
                            "end_time": int(word["end"] * 1000)+start_time,
                            "text": word["word"]
                        }
                        continue
                    if word['word'][0] in flag and len(cur['text'].strip()) >= minlen:
                        cur[ 'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        output(cur,len(raws)+1)
                        cur['text']=cur['text'].strip()
                        raws.append(cur)
                        cur = {
                            "line": len(raws) + 1,
                            "start_time": int(word["start"] * 1000)+start_time,
                            "end_time": int(word["end"] * 1000)+start_time,
                            "text": word["word"][1:]}
                        continue
                    cur['text'] += word["word"]
                    if (word["word"][-1] in flag and len(cur['text'].strip()) >= minlen) or len(cur['text']) >= maxlen * 1.5:
                        cur['end_time'] = int(word["end"] * 1000)+start_time
                        cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        output(cur, len(raws) + 1)
                        cur['text']=cur['text'].strip()
                        raws.append(cur)
                        cur = None

                if cur is not None:
                    cur['end_time'] = int(segment["words"][-1]["end"] * 1000)+start_time
                    cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                    if len(cur['text']) <= 3:
                        raws[-1]['text'] += cur['text'].strip()
                        raws[-1]['end_time'] = cur['end_time']
                        raws[-1]['time'] = cur['time']
                    else:
                        output(cur, len(raws) + 1)
                        cur['text']=cur['text'].strip()
                        raws.append(cur)

        except Exception as e:
            raise
    if set_p:
        tools.set_process(f"{config.transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}", 'logs',btnkey=inst.init['btnkey'] if inst else "")
    if detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
        for i,it in enumerate(raws):
            raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
    return raws

