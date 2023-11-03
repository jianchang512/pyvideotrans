import json
import os
import subprocess

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


def ceshi(*arg):
    subprocess.run(["ffmpeg"]+list(arg))

result="如今，语音体验在商业领域已成为一件大事。为了获得良好的体验，您需要实时、准确的转录基础。但大多数自动语音识别服务。"

result_tmp=""
for tmp_i in range(1+len(result)//30):
    result_tmp+=result[tmp_i*30:tmp_i*30+30]+"\n"
result=result_tmp.strip()
print(result)