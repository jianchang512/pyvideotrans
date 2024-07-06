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
    config.logger.info('openai模式')
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
    
    inter = 1200000
    normalized_sound = AudioSegment.from_wav(audio_file)  # -20.0
    total_length = 1 + (len(normalized_sound) // inter)

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
        "！"
    ]
    if detect_language[:2].lower() in ['zh', 'ja', 'ko']:
        flag.append(" ")
        maxlen = config.settings['cjk_len']
    else:
        maxlen = config.settings['other_len']
    model = whisper.load_model(
            model_name,
            device="cuda" if is_cuda else "cpu",
            download_root=config.rootdir + "/models"
        )

    def output(srt):
        if set_p:
            if inst and inst.precent < 75:
                inst.precent += 0.1
            tools.set_process(f"{config.transobj['yuyinshibiejindu']} {len(raws)} line",
                              btnkey=inst.init['btnkey'] if inst else "")
            tools.set_process(f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n', 'subtitle')
        else:
            tools.set_process_box(text=f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n', type="set", func_name="shibie")
    


    def append_raws(cur):
        if len(cur['text']) < int(maxlen / 5) and len(raws) > 0:
            raws[-1]['text'] += cur['text'] if detect_language[:2] in ['ja', 'zh', 'ko'] else f' {cur["text"]}'
            raws[-1]['end_time'] = cur['end_time']
            raws[-1][
                'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
        else:
            output(cur)
            raws.append(cur)
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
                    if tmp['end_time']-tmp['start_time']>=1500:
                        tmp["time"] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                        tmp['text']=tmp['text'].strip()
                        append_raws(tmp)
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
                    if not word['word']:
                        continue
                    if word['word'][0] in flag:
                        cur['end_time']=int(word["start"] * 1000)+start_time
                        if cur['end_time']-cur['start_time']<1500:
                            cur['text']+=word['word']
                            continue
                        cur[ 'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        cur['text']=cur['text'].strip()
                        append_raws(cur)
                        if len(word['word'])<2:
                            cur=None
                            continue
                        cur = {
                            "line": len(raws) + 1,
                            "start_time": int(word["start"] * 1000)+start_time,
                            "end_time": int(word["end"] * 1000)+start_time,
                            "text": word["word"][1:]}
                        continue
                    cur['text'] += word["word"]
                    if word["word"][-1] in flag or len(cur['text']) >= maxlen * 1.5:
                        cur['end_time'] = int(word["end"] * 1000)+start_time
                        if cur['end_time']-cur['start_time']<1500:
                            continue
                        cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        cur['text']=cur['text'].strip()
                        append_raws(cur)
                        cur = None

                if cur is not None:
                    cur['end_time'] = int(segment["words"][-1]["end"] * 1000)+start_time
                    if cur['end_time']-cur['start_time']<1500:
                        continue
                    cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                    if len(cur['text']) <= 3:
                        raws[-1]['text'] += cur['text'].strip()
                        raws[-1]['end_time'] = cur['end_time']
                        raws[-1]['time'] = cur['time']
                    else:
                        cur['text']=cur['text'].strip()
                        append_raws(cur)

        except Exception as e:
            raise
    if set_p:
        tools.set_process(f"{config.transobj['yuyinshibiewancheng']} / {len(raws)}", 'logs',btnkey=inst.init['btnkey'] if inst else "")
    if detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
        for i,it in enumerate(raws):
            raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
    return raws

