# 语音识别
import json
import os
import re
import threading
import time
from datetime import timedelta
import torch
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.util import tools


# 统一入口
def run(*, type="all", detect_language=None, audio_file=None,cache_folder=None,model_name=None,set_p=True):
    if type == "all":
        print(f'____{audio_file=}')
        rs= all_recogn(detect_language=detect_language, audio_file=audio_file,cache_folder=cache_folder,model_name=model_name,set_p=set_p)
    else:
        rs=split_recogn(detect_language=detect_language, audio_file=audio_file,cache_folder=cache_folder,model_name=model_name,set_p=set_p)
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except:
        pass
    return rs


#
def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


# split audio by silence
def shorten_voice(normalized_sound):
    normalized_sound = match_target_amplitude(normalized_sound, -20.0)
    max_interval = 10000
    buffer = 500
    nonsilent_data = []
    audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.params['voice_silence']),
                                    silence_thresh=-20 - 25)
    # print(audio_chunks)
    for i, chunk in enumerate(audio_chunks):
        start_time, end_time = chunk
        n = 0
        while end_time - start_time >= max_interval:
            n += 1
            # new_end = start_time + max_interval+buffer
            new_end = start_time + max_interval + buffer
            new_start = start_time
            nonsilent_data.append((new_start, new_end, True))
            start_time += max_interval
        nonsilent_data.append((start_time, end_time, False))
    return nonsilent_data


# 预先分割识别
def split_recogn(*, detect_language=None, audio_file=None, cache_folder=None,model_name="base",set_p=True):
    if set_p:
        tools.set_process(config.transobj['fengeyinpinshuju'])
    if config.current_status != 'ing' and config.box_status!='ing':
        return False
    noextname=os.path.basename(audio_file)
    tmp_path = f'{cache_folder}/{noextname}_tmp'
    if not os.path.isdir(tmp_path):
        try:
            os.makedirs(tmp_path, 0o777, exist_ok=True)
        except:
            raise config.Myexcept(config.transobj["createdirerror"])
    if audio_file.endswith('.m4a'):
        wavfile = cache_folder + "/tmp.wav"
        tools.m4a2wav(audio_file, wavfile)
    else:
        wavfile=audio_file
    if not os.path.exists(wavfile):
        raise Exception(f'[error]not exists {wavfile}')
    normalized_sound = AudioSegment.from_wav(wavfile)  # -20.0
    nonslient_file = f'{tmp_path}/detected_voice.json'
    if os.path.exists(nonslient_file) and os.path.getsize(nonslient_file):
        with open(nonslient_file, 'r') as infile:
            nonsilent_data = json.load(infile)
    else:
        if config.current_status == 'stop':
            raise config.Myexcept("Has stop")
        nonsilent_data = shorten_voice(normalized_sound)
        with open(nonslient_file, 'w') as outfile:
            json.dump(nonsilent_data, outfile)

    raw_subtitles = []
    total_length = len(nonsilent_data)
    start_t = time.time()
    try:
        model = WhisperModel(model_name, device="cuda" if config.params['cuda'] else "cpu",
                         compute_type=config.settings['cuda_com_type'],
                         download_root=config.rootdir + "/models",
                         cpu_threads=1,num_workers=1, local_files_only=True)
    except Exception as e:
        raise Exception(str(e.args))
    for i, duration in enumerate(nonsilent_data):
        # config.temp = {}
        if config.current_status != 'ing' and config.box_status != 'ing':
            del model
            raise config.Myexcept("Has stop")
        start_time, end_time, buffered = duration
        if start_time == end_time:
            end_time += 200

        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        audio_chunk = normalized_sound[start_time:end_time]
        audio_chunk.export(chunk_filename, format="wav")

        if config.current_status != 'ing':
            del model
            raise config.Myexcept("Has stop .")
        text = ""
        try:
            segments, _ = model.transcribe(chunk_filename,
                                           beam_size=config.settings['beam_size'],
                                           best_of=config.settings['best_of'],
                                           condition_on_previous_text=config.settings['condition_on_previous_text'],
                                           temperature=0 if config.settings['temperature']==0 else [0.0,0.2,0.4,0.6,0.8,1.0],
                                           language=detect_language)
            for t in segments:
                text += t.text + " "
        except Exception as e:
            del model
            raise  Exception(str(e.args))

        text = f"{text.capitalize()}. ".replace('&#39;', "'")
        text = re.sub(r'&#\d+;', '', text).strip()
        if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
            continue
        start = timedelta(milliseconds=start_time)
        stmp = str(start).split('.')
        if len(stmp) == 2:
            start = f'{stmp[0]},{int(int(stmp[-1]) / 1000)}'
        end = timedelta(milliseconds=end_time)
        etmp = str(end).split('.')
        if len(etmp) == 2:
            end = f'{etmp[0]},{int(int(etmp[-1]) / 1000)}'
        srt_line = {"line": len(raw_subtitles)+1, "time": f"{start} --> {end}", "text": text}
        raw_subtitles.append(srt_line)
        tools.set_process(f"{config.transobj['yuyinshibiejindu']} {srt_line['line']}/{total_length}")
        if set_p:
            msg = f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n"
            tools.set_process(msg, 'subtitle')

    print(f'用时 {time.time() - start_t}')
    if set_p:
        tools.set_process(f"{config.transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}", 'logs')
    # 写入原语言字幕到目标文件夹
    if os.path.exists(wavfile):
        os.unlink(wavfile)
    return raw_subtitles


# 整体识别，全部传给模型
def all_recogn(*, detect_language=None, audio_file=None, cache_folder=None,model_name="base",set_p=True):
    if set_p:
        tools.set_process(f"{config.params['whisper_model']} {config.transobj['kaishishibie']}")
    down_root = os.path.normpath(config.rootdir + "/models")
    model=None
    try:
        start_t = time.time()
        model = WhisperModel(model_name, device="cuda" if config.params['cuda'] else "cpu",
                             compute_type=config.settings['cuda_com_type'],
                             download_root=down_root,
                             num_workers=config.settings['whisper_worker'],
                             cpu_threads=os.cpu_count() if int(config.settings['whisper_threads']) < 1 else int(config.settings['whisper_threads']),
                             local_files_only=True)
        if audio_file.endswith('.m4a'):
            wavfile = cache_folder + "/tmp.wav"
            tools.m4a2wav(audio_file, wavfile)
        else:
            wavfile=audio_file
        if not os.path.exists(wavfile):
            raise Exception(f'[error]not exists {wavfile}')
        segments, info = model.transcribe(wavfile,
                                          beam_size=config.settings['beam_size'],
                                          best_of=config.settings['best_of'],
                                          condition_on_previous_text=config.settings['condition_on_previous_text'],
                                          vad_filter=config.settings['vad'],

                                          temperature=0 if config.settings['temperature']==0 else [0.0,0.2,0.4,0.6,0.8,1.0],
                                          vad_parameters=dict(
                                              min_silence_duration_ms=int(config.params['voice_silence']),
                                              max_speech_duration_s=15), language=detect_language)

        # 保留原始语言的字幕
        raw_subtitles = []
        sidx = -1
        print(info.duration)
        for segment in segments:
            if config.current_status != 'ing' and config.box_status !='ing':
                del model
                raise config.Myexcept("Had stop")
            sidx += 1
            start = int(segment.start * 1000)
            end = int(segment.end * 1000)
            if start == end:
                end += 200
            startTime = tools.ms_to_time_string(ms=start)
            endTime = tools.ms_to_time_string(ms=end)
            text = segment.text.strip().replace('&#39;', "'")
            text = re.sub(r'&#\d+;', '', text)
            # 无有效字符
            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(text) <= 1:
                continue
            # 原语言字幕
            s = {"line": len(raw_subtitles) + 1, "time": f"{startTime} --> {endTime}", "text": text}
            raw_subtitles.append(s)
            if set_p:
                tools.set_process(f'{s["line"]}\n{startTime} --> {endTime}\n{text}\n\n', 'subtitle')
                tools.set_process( f'{config.transobj["zimuhangshu"]} {s["line"]}, {round(segment.end * 100 / info.duration, 2)}%')
            else:
                tools.set_process_box(f'{s["line"]}\n{startTime} --> {endTime}\n{text}\n\n', func_name="set_subtitle")


        # 写入翻译前的原语言字幕到目标文件夹
        print(f'用时 {time.time() - start_t}')

        if os.path.exists(wavfile):
            os.unlink(wavfile)
        return raw_subtitles
    except Exception as e:
        raise Exception(f'whole all {str(e)}')
    finally:
        try:
            if model:
                del model
        except:
            pass
