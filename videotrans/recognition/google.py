import json
import os
import re
import time
from datetime import timedelta

from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.util import tools


# split audio by silence
def shorten_voice_old(normalized_sound):
    normalized_sound = tools.match_target_amplitude(normalized_sound, -20.0)
    max_interval = config.settings['interval_split'] * 1000
    buffer = int(config.settings['voice_silence'])
    nonsilent_data = []
    audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.settings['voice_silence']),
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


def recogn(*,
           detect_language=None,
           audio_file=None,
           cache_folder=None,
           set_p=True,
           inst=None):
    if set_p:
        tools.set_process(config.transobj['fengeyinpinshuju'], btnkey=inst.init['btnkey'] if inst else "")
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    proxy = tools.set_proxy()
    if proxy:
        os.environ['http_proxy'] = proxy
        os.environ['https_proxy'] = proxy
    noextname = os.path.basename(audio_file)
    tmp_path = f'{cache_folder}/{noextname}_tmp'
    if not os.path.isdir(tmp_path):
        try:
            os.makedirs(tmp_path, 0o777, exist_ok=True)
        except:
            raise Exception(config.transobj["createdirerror"])
    if not tools.vail_file(audio_file):
        raise Exception(f'[error]not exists {audio_file}')
    normalized_sound = AudioSegment.from_wav(audio_file)  # -20.0
    nonslient_file = f'{tmp_path}/detected_voice.json'
    if tools.vail_file(nonslient_file):
        with open(nonslient_file, 'r') as infile:
            nonsilent_data = json.load(infile)
    else:
        nonsilent_data = shorten_voice_old(normalized_sound)
        with open(nonslient_file, 'w') as outfile:
            json.dump(nonsilent_data, outfile)

    raw_subtitles = []
    total_length = len(nonsilent_data)
    start_t = time.time()

    import speech_recognition as sr
    try:
        recognizer = sr.Recognizer()
    except Exception as e:
        raise Exception(f'使用Google识别需要设置代理')

    for i, duration in enumerate(nonsilent_data):
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return False
        start_time, end_time, buffered = duration
        if start_time == end_time:
            end_time += int(config.settings['voice_silence'])

        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        audio_chunk = normalized_sound[start_time:end_time]
        audio_chunk.export(chunk_filename, format="wav")

        text = ""
        try:
            with sr.AudioFile(chunk_filename) as source:
                # Record the audio data
                audio_data = recognizer.record(source)
                try:
                    # Recognize the speech
                    text = recognizer.recognize_google(audio_data, language=detect_language)
                except sr.UnknownValueError:
                    text = ""
                    print("Speech recognition could not understand the audio.")
                except sr.RequestError as e:
                    raise Exception(f"Google识别出错，请检查代理是否正确：{e}")
        except Exception as e:
            raise Exception('Google识别出错：' + str(e.args))

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
        srt_line = {"line": len(raw_subtitles) + 1, "time": f"{start} --> {end}", "text": text}
        raw_subtitles.append(srt_line)
        if set_p:
            if inst and inst.precent < 55:
                inst.precent += 0.1
            tools.set_process(f"{config.transobj['yuyinshibiejindu']} {srt_line['line']}/{total_length}",
                              btnkey=inst.init['btnkey'] if inst else "")
            msg = f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n"
            tools.set_process(msg, 'subtitle')
        else:
            tools.set_process_box(text=f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n", type="set",
                                  func_name="shibie")
    if set_p:
        tools.set_process(f"{config.transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}", 'logs',
                          btnkey=inst.init['btnkey'] if inst else "")
    # 写入原语言字幕到目标文件夹
    return raw_subtitles
