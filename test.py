import io
import json
import os
import subprocess
import time

import pydub
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_silence, detect_nonsilent



def silen(filename):
    max_interval=10000
    buffer_time=2000
    print("silen===")
    nonsilent_data = []
    normalized_sound = AudioSegment.from_wav(filename)
    audio_chunks = detect_silence(normalized_sound, min_silence_len=300,silence_thresh=-20)
    print(audio_chunks)
    for i, chunk in enumerate(audio_chunks):
        start_time, end_time = chunk  
        n=0
        while end_time - start_time >= max_interval:
            n+=1
            new_end = start_time + max_interval + buffer_time
            new_start = start_time
            nonsilent_data.append((new_start, new_end, True))    
            normalized_sound[new_start:new_end].export(f"./tmp/raw-i{i}-n{n}.wav",format="wav")
            start_time += max_interval
        nonsilent_data.append((start_time, end_time, False))        
        print(chunk)
        normalized_sound[start_time:end_time].export(f"./tmp/raw-i{i}.wav",format="wav")       
        
    return nonsilent_data


def nosilen(filename):
    print("\nnosilen")
    nonsilent_data = []
    normalized_sound = AudioSegment.from_wav(filename)
    audio_chunks=detect_nonsilent(normalized_sound, min_silence_len=300, seek_step=1,silence_thresh=-25 )
    #print(audio_chunks)
    if len(audio_chunks)==1 and (audio_chunks[0][1]-audio_chunks[0][0]>60000):
        # 一个，强制分割
        new_audio_chunks=[]
        pos=0
        while pos<audio_chunks[0][1]:
            print(f">60s,强制分割 {pos=}")
            end=pos+60000
            end = audio_chunks[0][1] if end>audio_chunks[0][1] else end
            new_audio_chunks.append([pos,end])
            pos=end
        audio_chunks=new_audio_chunks

    for i, chunk in enumerate(audio_chunks):
        #print(chunk)
        start, end = chunk
        nonsilent_data.append([start, end, False])
    print(nonsilent_data)


# print("start")
# subprocess.run(["ffmpeg","-i","C:/Users/c1/Videos/cn.mp4","C:/Users/c1/Videos/cn-2.mp4"])
# subprocess.run(["php","C:/Users/c1/Videos/1.php","ar1"])
# print("end")

#
# def ceshi(*arg):
#     subprocess.run(["ffmpeg"]+list(arg))
# import numpy as np
# import soundfile as sf
# import torch
# import whisper
# model=whisper.load_model("large", download_root="./models")
# r = sr.Recognizer()
# t=time.time()
# with sr.AudioFile("./tmp/1.wav") as source:
#     audio_data = r.record(source)
#
#     wav_bytes = audio_data.get_wav_data(convert_rate=16000)
#     wav_stream = io.BytesIO(wav_bytes)
#     audio_array, sampling_rate = sf.read(wav_stream)
#     audio_array = audio_array.astype(np.float32)
#     result=model.transcribe(
#         audio_array,
#         language="zh",
#         task=None,
#         fp16=False
#     )
#     # print(result)
#     for it in result['segments']:
#         print(f"[{it['start']} -> {it['end']}] {it['text']}")
#
# print(f"time==={time.time()-t}")
import re
from datetime import datetime,timedelta
sub_name="C:/Users/c1/Videos/1.srt"
def dubbing(sub_name):
    content=[]
    # all audio chunk
    segments = []
    # every start time
    start_times = []
    with open(sub_name,"r",encoding="utf-8") as f:
        tx=re.split(r"\n\n",f.read().strip(),re.I|re.S)
        for it in tx:
            c=it.strip().split("\n")
            start, end=c[1].strip().split("-->")
            text="".join(c[2:]).strip()
            start=start.replace(',',':').split(":")
            start_time=int(timedelta(hours=int(start[0]),minutes=int(start[1]),seconds=int(start[2]),milliseconds=int(start[3])).total_seconds()*1000)
            end=end.replace(',',':').split(":")
            end_time=int(timedelta(hours=int(end[0]),minutes=int(end[1]),seconds=int(end[2]),milliseconds=int(end[3])).total_seconds()*1000)

            start_times.append(start_time)
            content.append({"start_time":start,"end_time":end,"text":text})
            try:
                rate = int(str(config.video['voice_rate']).replace('%', ''))
                if rate >= 0:
                    rate = f"+{rate}%"
                else:
                    rate = f"{rate}%"
                communicate = edge_tts.Communicate(text,
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
                    showprocess(f"new mp3 length bigger than wav ,speed up {speed} ", 'logs')
                    audio_data = speed_change(audio_data, speed)
                    showprocess(f"change after:{len(audio_data)}", 'logs')
                segments.append(audio_data)
            except Exception as e:
                logger.error("Create voice role error:" + str(e))
                print(e)
                segments.append(AudioSegment.silent(duration=end_time - start_time))
    # merge translate audo
    merge_audio_segments(segments, start_times, total_length * 1000, mp4name)


