# -*- coding: utf-8 -*-

import asyncio
import re
import shutil
import urllib.parse
import httpx
import requests
import speech_recognition as sr
import os
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import srt
from datetime import timedelta
import json
import edge_tts
import config
from config import logger
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#  get role by edge tts
def get_list_voices():
    voice_list = {}
    v = asyncio.run(edge_tts.list_voices())
    for it in v:
        name = it['ShortName']
        prefix = name.split('-')[0].lower()
        if prefix not in voice_list:
            voice_list[prefix] = ["No", name]
        else:
            voice_list[prefix].append(name)
    return voice_list

# split audio by silence
def shorten_voice(normalized_sound):
    normalized_sound=match_target_amplitude(normalized_sound,-20.0)
    max_interval=10000
    buffer=500
    nonsilent_data = []
    audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.video['voice_silence']),silence_thresh=-20-25)
    #print(audio_chunks)
    for i, chunk in enumerate(audio_chunks):
        start_time, end_time = chunk  
        n=0
        while end_time - start_time >= max_interval:
            n+=1
            # new_end = start_time + max_interval+buffer
            new_end = start_time + max_interval+buffer
            new_start = start_time
            nonsilent_data.append((new_start, new_end, True))
            start_time += max_interval
        nonsilent_data.append((start_time, end_time, False))
    return nonsilent_data


#
def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


# join all short audio to one ,eg name.mp4  name.mp4.wav
def merge_audio_segments(segments, start_times, total_duration, mp4name):
    merged_audio = AudioSegment.empty()
    # start is not 0
    if start_times[0] != 0:
        silence_duration = start_times[0]
        silence = AudioSegment.silent(duration=silence_duration)
        merged_audio += silence

    # join
    for i in range(len(segments)):
        segment = segments[i]
        start_time = start_times[i]
        # add silence
        if i > 0:
            previous_end_time = start_times[i - 1] + len(segments[i - 1])
            silence_duration = start_time - previous_end_time
            # 可能存在字幕 语音对应问题
            if silence_duration > 0:
                silence = AudioSegment.silent(duration=silence_duration)
                merged_audio += silence

        merged_audio += segment
    #
    if len(merged_audio) > total_duration:
        merged_audio = merged_audio[:total_duration]
    merged_audio.export(f"{config.rootdir}/tmp/{mp4name}.wav", format="wav")
    return merged_audio


# google api
def googletrans(text, src, dest):
    url = f"https://translate.google.com/m?sl={urllib.parse.quote(src)}&tl={urllib.parse.quote(dest)}&hl={urllib.parse.quote(dest)}&q={urllib.parse.quote(text)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    proxies = None
    if config.video['proxy']:
        proxies = {
            'http': config.video['proxy'],
            'https': config.video['proxy']
        }
    # example
    # proxies = {
    #     'http': 'http://127.0.0.1:10809',
    #     'https': 'http://127.0.0.1:10809'
    # }
    try:
        response = requests.get(url, proxies=proxies, headers=headers, timeout=40)
        if response.status_code != 200:
            return f"error translation code={response.status_code}"
        re_result = re.findall(
            r'(?s)class="(?:t0|result-container)">(.*?)<', response.text)
    except:
        return "[error google api] Please check the connectivity of the proxy or consider changing the IP address."
    return "error on translation" if len(re_result) < 1 else re_result[0]




# speed change
def speed_change(sound, speed=1.0):
    # Manually override the frame_rate. This tells the computer how many
    # samples to play per second
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    })
    # convert the sound with altered frame rate to a standard frame rate
    # so that regular playback programs will work right. They often only
    # know how to play audio at standard frame rate (like 44.1k)
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)

#
def get_large_audio_transcription(aud_path, mp4name, sub_name, showprocess):
    # raw video directory
    folder_path = '/'.join(aud_path.split('/')[:-1])
    # no ext audio name use create tmp dir
    audio_name = aud_path.split('/')[-1][:-4]
    logger.info(f"[get_large_audio_transcription] {aud_path=}\n{folder_path=}\n{audio_name=}\n{sub_name=}")
    # temp dir
    tmp_path = folder_path + f'/##{audio_name}_tmp'
    showprocess(f"{mp4name} spilt audio","logs")
    if config.current_status == 'stop':
        return
    if not os.path.isdir(tmp_path):
        os.makedirs(tmp_path, 0o777, exist_ok=True)
    r = sr.Recognizer()
    # 已存在字幕文件则跳过
    if os.path.exists(sub_name):
        os.unlink(sub_name)

    normalized_sound = AudioSegment.from_wav(aud_path)  # -20.0
    total_length = len(normalized_sound) / 1000
    nonslient_file = f'{tmp_path}/detected_voice.json'
    if os.path.exists(nonslient_file):
        with open(nonslient_file, 'r') as infile:
            nonsilent_data = json.load(infile)
    else:
        showprocess(f"{mp4name} create json",'logs')

        if config.current_status == 'stop':
            return
        nonsilent_data =  shorten_voice(normalized_sound)
        showprocess(f"{mp4name} split voice",'logs')
        with open(nonslient_file, 'w') as outfile:
            json.dump(nonsilent_data, outfile)

    subs = []
    showprocess(f"{mp4name} translate",'logs')
    segments = []
    start_times = []
    for i, duration in enumerate(nonsilent_data):
        if config.current_status == 'stop':
            return
        start_time, end_time, buffered = duration
        start_times.append(start_time)
        logger.info(f"开始时间：{start_time=},结束时间:{end_time=},{duration=}")
        time_covered = start_time / len(normalized_sound) * 100
        # 进度
        showprocess(f"{mp4name} {time_covered:.1f}%",'logs')
        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        add_vol = 0
        audio_chunk = normalized_sound[start_time:end_time] + add_vol
        audio_chunk.export(chunk_filename, format="wav")

        # recognize the chunk
        with sr.AudioFile(chunk_filename) as source:
            audio_listened = r.record(source)
            try:
                text = r.recognize_whisper(audio_listened,
                                           language="zh" if config.video['detect_language'] == "zh-cn" or
                                                            config.video['detect_language'] == "zh-tw" else
                                           config.video['detect_language'], model=config.video['whisper_model'])
            except sr.UnknownValueError as e:
                logger.error("Recognize Error: ", str(e))
                segments.append(audio_chunk)
                continue
            except Exception as e:
                logger.error("Recognize Error:", str(e))
                segments.append(audio_chunk)
                continue
            if config.current_status == 'stop':
                return
            text = f"{text.capitalize()}. "
            try:
                result = googletrans(text, config.video['source_language'],
                                     config.video['target_language'])
                logger.info(f"target_language={config.video['target_language']}\n---text={result=}")
            except Exception as e:
                logger.error("Translate Error:", str(e))
                segments.append(audio_chunk)
                continue
            isemtpy=True
            if not re.fullmatch(r'^[./\\。，/\s]*$',result.strip(),re.I):
                isemtpy=False
                combo_txt = result + '\n\n'
                if buffered:
                    end_time -= 500
                start = timedelta(milliseconds=start_time)
                end = timedelta(milliseconds=end_time)

                index = len(subs) + 1
                sub = srt.Subtitle(index=index, start=start, end=end, content=combo_txt)
                showprocess(f"{start} --> {end} {combo_txt}",'subtitle')
                subs.append(sub)

            if config.video['voice_role'] != 'No':
                if isemtpy:
                    segments.append(AudioSegment.silent(duration=end_time - start_time))
                    continue
                try:
                    rate=int(str(config.video['voice_rate']).replace('%',''))
                    if rate>=0:
                        rate=f"+{rate}%"
                    else:
                        rate=f"{rate}%"
                    communicate = edge_tts.Communicate(result,
                                                       config.video['voice_role'],
                                                       rate=rate)
                    tmpname = f"{config.rootdir}/tmp/{start_time}-{index}.mp3"
                    asyncio.run(communicate.save(tmpname))

                    audio_data = AudioSegment.from_file(tmpname, format="mp3")
                    wavlen = end_time - start_time
                    mp3len = len(audio_data)
                    if config.video['voice_autorate'] and (mp3len - wavlen > 1000):
                        # 最大加速2倍
                        speed = mp3len / wavlen
                        speed = 2 if speed > 2 else speed
                        showprocess(f"new mp3 length biger than wav  500ms，speed up {speed} ",'logs')
                        audio_data = speed_change(audio_data, speed)
                        showprocess(f"change after:{len(audio_data)}",'logs')
                except Exception as e:
                    print("##########################\n#####################")
                    print(e)
                    audio_data = AudioSegment.silent(duration=end_time - start_time)
                segments.append(audio_data)

    merge_audio_segments(segments, start_times, total_length * 1000, mp4name)
    final_srt = srt.compose(subs)
    with open(sub_name, 'w', encoding="utf-8") as f:
        f.write(final_srt)

    showprocess(f"{mp4name} add subtitle",'logs')
    # target  output mp4 filepath
    target_mp4 = config.video['target_dir']+f"/{mp4name}"
    # raw mp4 filepath
    source_mp4 = folder_path + f"/{mp4name}"
    logger.info(f"{target_mp4=}\n{source_mp4=}")
    # add voice role audio
    if config.video['voice_role'] != 'No':
        os.system(f"ffmpeg -y -i {source_mp4} -c:v copy -an {config.rootdir}/tmp/novoice_{mp4name}")
        os.system(
            f"ffmpeg -y -i {config.rootdir}/tmp/novoice_{mp4name} -i {config.rootdir}/tmp/{mp4name}.wav -c copy -map 0:v:0 -map 1:a:0 {config.rootdir}/tmp/addvoice-{mp4name}")
        source_mp4 = f"{config.rootdir}/tmp/addvoice-{mp4name}"
        if not config.video['insert_subtitle']:
            shutil.move(source_mp4,target_mp4)
    # else:

    # inert subtitle
    if config.video['insert_subtitle']:
        os.system(
            f"ffmpeg -y -i {source_mp4} -i {sub_name} -c copy -c:s mov_text -metadata:s:s:0 language={config.video['subtitle_language']}  {target_mp4}")
    showprocess(f"{mp4name}.mp4 ended",'logs')


# 测试 google
def testproxy(proxy):
    if not proxy:
        proxy = None
    status = False
    try:
        with httpx.Client(proxies=proxy) as client:
            r = client.get('https://www.google.com', timeout=30)
            logger.info(f'google.com code={r.status_code=}')
            if r.status_code == 200:
                status = True
    except Exception as e:
        logger.error(str(e))
    return status
