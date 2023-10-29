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
from pydub.silence import detect_nonsilent, detect_silence
import srt
from datetime import timedelta
import json
import edge_tts
from config import timelist, qu
import config
import logging

logger = logging.getLogger('video_translate')
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


#  获取 支持的语音角色列表
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


def get_thd_min_silence(p):
    thd = 25  # larger more sensitive
    min_silence_len = 1000
    return thd, min_silence_len


# 返回切分的音频片段
def shorten_voice(normalized_sound):
    normalized_sound=match_target_amplitude(normalized_sound,-20.0)
    max_interval=10000
    buffer=2000
    print("silen===")
    nonsilent_data = []
    audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.video_config['voice_silence']),silence_thresh=-20-25)
    #print(audio_chunks)
    for i, chunk in enumerate(audio_chunks):
        start_time, end_time = chunk  
        n=0
        while end_time - start_time >= max_interval:
            n+=1
            new_end = start_time + max_interval+buffer
            new_start = start_time
            nonsilent_data.append((new_start, new_end, True))    
            #normalized_sound[new_start:new_end].export(f"./tmp/raw-i{i}-n{n}.wav",format="wav")
            start_time += max_interval
        nonsilent_data.append((start_time, end_time, False))        
        #print(chunk)
        #normalized_sound[start_time:end_time].export(f"./tmp/raw-i{i}.wav",format="wav")       
        
    return nonsilent_data


# 调整分贝
def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


# 拼接配音片段 ,合并后的音频名字未  视频名字.wav 比如 1.mp4.wav
def merge_audio_segments(segments, start_times, total_duration, mp4name):
    # 创建一个空白的音频段作为初始片段
    merged_audio = AudioSegment.empty()
    # 检查是否需要在第一个片段之前添加静音
    if start_times[0] != 0:
        silence_duration = start_times[0]
        silence = AudioSegment.silent(duration=silence_duration)
        merged_audio += silence

    # 逐个连接音频片段
    for i in range(len(segments)):
        segment = segments[i]
        start_time = start_times[i]
        # 检查前一个片段的结束时间与当前片段的开始时间之间是否有间隔
        if i > 0:
            previous_end_time = start_times[i - 1] + len(segments[i - 1])
            silence_duration = start_time - previous_end_time
            # 可能存在字幕 语音对应问题
            if silence_duration > 0:
                silence = AudioSegment.silent(duration=silence_duration)
                merged_audio += silence
        # 连接当前片段
        merged_audio += segment
    # 检查总时长是否大于指定的时长，并丢弃多余的部分
    if len(merged_audio) > total_duration:
        merged_audio = merged_audio[:total_duration]
    merged_audio.export(f"./tmp/{mp4name}.wav", format="wav")
    return merged_audio


# google 翻译
def googletrans(text, src, dest):
    url = f"https://translate.google.com/m?sl={urllib.parse.quote(src)}&tl={urllib.parse.quote(dest)}&hl={urllib.parse.quote(dest)}&q={urllib.parse.quote(text)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    proxies = None
    if "http_proxy" in os.environ:
        proxies = {
            'http': os.environ['http_proxy'],
            'https': os.environ['https_proxy']
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




# 修改速率
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


def get_large_audio_transcription(aud_path, mp4name, sub_name, showprocess):
    # 视频所在路径
    folder_path = '/'.join(aud_path.split('/')[:-1])
    # 不带后缀的音频名字
    audio_name = aud_path.split('/')[-1][:-4]
    logger.info(f"[get_large_audio_transcription] {aud_path=}\n{folder_path=}\n{audio_name=}\n{sub_name=}")
    # 创建保存片段的临时目录
    tmp_path = folder_path + f'/##{audio_name}_tmp'
    showprocess(mp4name, f"{mp4name} spilt audio")
    if config.current_status == 'stop':
        return
    if not os.path.isdir(tmp_path):
        os.makedirs(tmp_path, 0o777, exist_ok=True)
    r = sr.Recognizer()
    # thd, min_slien = get_thd_min_silence(aud_path)
    # 已存在字幕文件则跳过
    if not os.path.exists(sub_name) or os.path.getsize(sub_name) == 0:
        # sound = AudioSegment.from_wav(aud_path)
        normalized_sound = AudioSegment.from_wav(aud_path)  # -20.0
        total_length = len(normalized_sound) / 1000
        nonslient_file = f'{tmp_path}/detected_voice.json'
        showprocess(mp4name, f"{mp4name} create json")

        if os.path.exists(nonslient_file):
            with open(nonslient_file, 'r') as infile:
                nonsilent_data = json.load(infile)
        else:
            showprocess(mp4name, f"{mp4name} create json")

            if config.current_status == 'stop':
                return
            nonsilent_data =  shorten_voice(normalized_sound)
            '''
            audio_chunks = detect_silence(normalized_sound, min_silence_len=int(config.video_config['voice_silence']))
            if len(audio_chunks)==1 and (audio_chunks[0][1]-audio_chunks[0][0]>60000):
                # 一个，强制分割
                new_audio_chunks=[]
                pos=0
                while pos<audio_chunks[0][1]:
                    end=pos+60000
                    end = audio_chunks[0][1] if end>audio_chunks[0][1] else end
                    new_audio_chunks.append([pos,end])
                    pos=end
                audio_chunks=new_audio_chunks

            for i, chunk in enumerate(audio_chunks):
                print(chunk)
                start, end = chunk
                nonsilent_data.append([start, end, False])
            '''
            showprocess(mp4name, f"{mp4name} split voice")
            with open(nonslient_file, 'w') as outfile:
                json.dump(nonsilent_data, outfile)

        subs = []
        showprocess(mp4name, f"{mp4name} translate")
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
            showprocess(mp4name, f"{mp4name} {time_covered:.1f}%")
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            add_vol = 0
            audio_chunk = normalized_sound[start_time:end_time] + add_vol
            audio_chunk.export(chunk_filename, format="wav")

            # recognize the chunk
            with sr.AudioFile(chunk_filename) as source:
                audio_listened = r.record(source)
                try:
                    text = r.recognize_whisper(audio_listened,
                                               language="zh" if config.video_config['detect_language'] == "zh-cn" or
                                                                config.video_config['detect_language'] == "zh-tw" else
                                               config.video_config['detect_language'], model=config.video_config['whisper_model'])
                except sr.UnknownValueError as e:
                    logger.error("Recognize Error: ", str(e), end='; ')
                    segments.append(audio_chunk)
                    continue
                except Exception as e:
                    logger.error("Recognize Error:", str(e), end='; ')
                    segments.append(audio_chunk)
                    continue
                if config.current_status == 'stop':
                    return
                text = f"{text.capitalize()}. "
                try:
                    result = googletrans(text, config.video_config['source_language'],
                                         config.video_config['target_language'])
                    logger.info(f"target_language={config.video_config['target_language']}\n---text={result=}")
                except Exception as e:
                    logger.error("Translate Error:", str(e))
                    segments.append(audio_chunk)
                    continue
                isemtpy=True
                if not re.fullmatch(r'^[./\\。，/\s]*$',result.strip(),re.I):
                    isemtpy=False
                    combo_txt = result + '\n\n'
                    if buffered:
                        end_time -= 2000
                    start = timedelta(milliseconds=start_time)
                    end = timedelta(milliseconds=end_time)

                    index = len(subs) + 1
                    sub = srt.Subtitle(index=index, start=start, end=end, content=combo_txt)
                    qu.put(f"{start} --> {end} {combo_txt}")
                    subs.append(sub)
                    
                if config.video_config['voice_role'] != 'No':
                    if isemtpy:
                        segments.append(AudioSegment.silent(duration=end_time - start_time))
                        continue
                    try:    
                        communicate = edge_tts.Communicate(result,
                                                           config.video_config['voice_role'],
                                                           rate=config.video_config['voice_rate'])
                        tmpname = f"./tmp/{start_time}-{index}.mp3"
                        asyncio.run(communicate.save(tmpname))
                    
                        audio_data = AudioSegment.from_file(tmpname, format="mp3")
                        wavlen = end_time - start_time
                        mp3len = len(audio_data)
                        print(f"原wav长度是:{wavlen=},当前mp3长度是:{mp3len=}")
                        if config.video_config['voice_autorate'] and (mp3len - wavlen > 1000):
                            # 最大加速2倍
                            speed = mp3len / wavlen
                            speed = 2 if speed > 2 else speed
                            print(f"新mp3len 大于 wavlen 500，需要加速 {speed} 倍")
                            audio_data = speed_change(audio_data, speed)
                            print(f"加速后的新长度为:{len(audio_data)}")
                    except:
                        audio_data = AudioSegment.silent(duration=end_time - start_time)
                    segments.append(audio_data)

        merge_audio_segments(segments, start_times, total_length * 1000, mp4name)
        final_srt = srt.compose(subs)
        with open(sub_name, 'w', encoding="utf-8") as f:
            f.write(final_srt)
    else:
        showprocess(mp4name, "add subtitle")
    showprocess(mp4name, f"{mp4name} add subtitle")
    # 最终生成的视频地址
    target_mp4 = config.video_config['target_dir']+f"/{mp4name}"
    # 原始视频地址
    source_mp4 = folder_path + f"/{mp4name}"
    logger.info(f"{target_mp4=}\n{source_mp4=}")
    # 合并
    if config.video_config['voice_role'] != 'No':
        os.system(f"ffmpeg -y -i {source_mp4} -c:v copy -an ./tmp/novoice_{mp4name}")
        os.system(
            f"ffmpeg -y -i ./tmp/novoice_{mp4name} -i ./tmp/{mp4name}.wav -c copy -map 0:v:0 -map 1:a:0 ./tmp/addvoice-{mp4name}")
        source_mp4 = f"./tmp/addvoice-{mp4name}"
        if not config.video_config['insert_subtitle']:
            shutil.move(source_mp4,target_mp4)
    if config.video_config['insert_subtitle']:
        os.system(
            f"ffmpeg -y -i {source_mp4} -i {sub_name} -c copy -c:s mov_text -metadata:s:s:0 language={config.video_config['subtitle_language']}  {target_mp4}")
    showprocess(mp4name, f"{mp4name}.mp4 finished")


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
