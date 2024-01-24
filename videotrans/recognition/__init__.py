# 语音识别
import json
import os
import re
import threading
import time
from datetime import timedelta

from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.util import tools


# 统一入口
def run(*, type="all", detect_language=None, audio_file=None,cache_folder=None,model_name=None,set_p=True):
    if type == "all":
        return all_recogn(detect_language=detect_language, audio_file=audio_file,cache_folder=cache_folder,model_name=model_name,set_p=set_p)
    return split_recogn(detect_language=detect_language, audio_file=audio_file,cache_folder=cache_folder,model_name=model_name,set_p=set_p)


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


def shibie(*, duration=None, i=None, line=None, tmp_path=None, detect_language=None, normalized_sound=None,model_name="base"):
    r = WhisperModel(model_name, device="cuda" if config.params['cuda'] else "cpu",
                     compute_type=config.settings['cuda_com_type'],
                     download_root=config.rootdir + "/models",
                     cpu_threads=1,
                     num_workers=1, local_files_only=True)
    if config.current_status != 'ing' and config.box_status!='ing':
        raise config.Myexcept("Has stop")
    start_time, end_time, buffered = duration
    if start_time == end_time:
        end_time += 200

    chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
    audio_chunk = normalized_sound[start_time:end_time]
    audio_chunk.export(chunk_filename, format="wav")

    if config.current_status != 'ing':
        raise config.Myexcept("Has stop .")
    text = ""
    try:
        segments, _ = r.transcribe(chunk_filename,
                                   beam_size=config.settings['beam_size'],
                                   best_of=config.settings['best_of'],
                                   condition_on_previous_text=False, 
                                   language=detect_language)
        for t in segments:
            text += t.text + " "
    except Exception as e:
        tools.set_process("[error]:" + str(e))
        return

    if config.current_status == 'stop':
        raise config.Myexcept("Has stop it.")
    text = f"{text.capitalize()}. ".replace('&#39;', "'")
    text = re.sub(r'&#\d+;', '', text).strip()
    if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
        return
    start = timedelta(milliseconds=start_time)
    stmp = str(start).split('.')
    if len(stmp) == 2:
        start = f'{stmp[0]},{int(int(stmp[-1]) / 1000)}'
    end = timedelta(milliseconds=end_time)
    etmp = str(end).split('.')
    if len(etmp) == 2:
        end = f'{etmp[0]},{int(int(etmp[-1]) / 1000)}'
    srt_line = {"line": line, "time": f"{start} --> {end}", "text": text}
    config.temp[i] = srt_line
    r = None


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
    wavfile = cache_folder + "/tmp.wav"
    tools.m4a2wav(audio_file, wavfile)
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
    # offset = 0
    split_size = int(config.settings['split_threads'])
    if split_size<1:
        split_size=os.cpu_count()
    total_length = len(nonsilent_data)
    thread_chunk = [nonsilent_data[i:i + split_size] for i in range(0, len(nonsilent_data), split_size)]

    start_t = time.time()
    for (j, it) in enumerate(thread_chunk):
        config.temp = {}
        threads = []
        line = 0
        for i, duration in enumerate(it):
            line = (j * split_size) + i + 1
            config.temp[i] = None
            threads.append(threading.Thread(target=shibie,
                                            kwargs={"i": i, "duration": duration, "line": line, "tmp_path": tmp_path,
                                                    "detect_language": detect_language,
                                                    "model_name":model_name,
                                                    "normalized_sound": normalized_sound}))
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        tools.set_process(f"{config.transobj['yuyinshibiejindu']} {line}/{total_length}")
        config.temp = [x for x in list(config.temp.values()) if x is not None]
        raw_subtitles.extend(config.temp)
        msg = ""
        for t in config.temp:
            msg += f"{t['line']}\n{t['time']}\n{t['text']}\n\n"
        if set_p:
            tools.set_process(msg, 'subtitle')

    print(f'用时 {time.time() - start_t}')
    if set_p:
        tools.set_process(f"{config.transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}", 'logs')
    # 写入原语言字幕到目标文件夹
    # self.save_srt_target(raw_subtitles, self.targetdir_source_sub)
    if os.path.exists(wavfile):
        os.unlink(wavfile)
    return raw_subtitles


# 整体识别，全部传给模型
def all_recogn(*, detect_language=None, audio_file=None, cache_folder=None,model_name="base",set_p=True):
    if set_p:
        tools.set_process(f"{config.params['whisper_model']} {config.transobj['kaishishibie']}")
    down_root = os.path.normpath(config.rootdir + "/models")
    try:
        start_t = time.time()
        model = WhisperModel(model_name, device="cuda" if config.params['cuda'] else "cpu",
                             compute_type=config.settings['cuda_com_type'],
                             download_root=down_root,
                             num_workers=config.settings['whisper_worker'],
                             cpu_threads=os.cpu_count() if config.settings['whisper_threads'] < 1 else config.settings['whisper_threads'],
                             local_files_only=True)
        wavfile = cache_folder + "/tmp.wav"
        tools.m4a2wav(audio_file, wavfile)
        segments, info = model.transcribe(wavfile,
                                          beam_size=config.settings['beam_size'],
                                          best_of=config.settings['best_of'],
                                          condition_on_previous_text=False, 
                                          vad_filter=True,
                                          vad_parameters=dict(
                                              min_silence_duration_ms=int(config.params['voice_silence']),
                                              max_speech_duration_s=15), language=detect_language)

        # 保留原始语言的字幕
        raw_subtitles = []
        sidx = -1
        for segment in segments:
            if config.current_status != 'ing' and config.box_status !='ing':
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

        # 写入翻译前的原语言字幕到目标文件夹
        print(f'用时 {time.time() - start_t}')
        model = None
        if os.path.exists(wavfile):
            os.unlink(wavfile)
        return raw_subtitles
    except Exception as e:
        raise Exception(f'whole all {str(e)}')
