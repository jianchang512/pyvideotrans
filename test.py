# import ctypes
# import io
# import json
# import os
# import re
# import subprocess
#
# # cmd=f"ffmpeg -y -i \"C:/Users/c1/Videos/kx.mp4\" -c:v libx264 -c:a pcm_s16le ceshi.mp4"
# #
# # p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=True)
# #
# # while True:
# #     try:
# #         print(f"是否结束={p.poll()}")
# #
# #
# #         rs=p.wait(5)
# #         print("rs后边有没有来到")
# #         print(f"{rs=},returncode={p.returncode=}")
# #         print(f"out={p.stdout}")
# #         break
# #     except Exception as e:
# #         print("异常"+str(e))
#
#
# # with open(r'C:\Users\c1\Videos\_video_out\srt\earth.srt', "r", encoding="utf-8") as f:
# #     tx = re.split(r"\n\s*?\n", f.read().strip())
# #     for (idx, it) in enumerate(tx):
# #         c = it.strip().split("\n")
# #         start, end = c[1].strip().split(" --> ")
# #         text = "".join(c[2:]).strip()
# #         print(f"{text=}")
#
#
#
# from pydub import AudioSegment
# from pydub.silence import detect_nonsilent
# merged_audio = AudioSegment.empty()
# merged_audio+=AudioSegment.from_wav("./hc22.wav")
# #exit()
# merged_audio += AudioSegment.silent(duration=82000)
# merged_audio.export("./tts.wav", format="wav")
import os
import re
import shutil
import subprocess
import time
from datetime import timedelta

# start = timedelta(seconds=12,milliseconds=30)
# print(start)
from pydub import AudioSegment

from videotrans.util.tools import is_novoice_mp4, runffmpeg


def get_video_duration(file_path):
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        f"{file_path}"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration = int(float(result.stdout.strip())*1000)
        return duration
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

def ms_to_time_string(*,ms=0,seconds=None):
    # 计算小时、分钟、秒和毫秒
    if seconds is None:
        td = timedelta(milliseconds=ms)
    else:
        td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000

    # 格式化为字符串
    time_string = f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    return time_string

import cv2
import numpy as np
import os

def add_clip_to_last(novoice_mp4,duration_ms):
    folder="c:/users/c1/videos"
    # 提取 1.mp4 的最后一帧为 1.png
    output_image = f"{folder}/{time.time()}.png"

    cap = cv2.VideoCapture(novoice_mp4)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # 设置最后一帧为输出帧
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(output_image, frame)
        print(f"Successfully saved the last frame as {output_image}")
    else:
        print("Error reading the last frame")
    cap.release()
    # 读取 源视频的帧率
    cap = cv2.VideoCapture(novoice_mp4)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    # 生成 设定时间的片段mp4
    clip_video = f"{folder}/{time.time()}.mp4"
    # 计算生成视频的帧数
    frame_count_new = int(fps * duration_ms / 1000)
    # 用相同的帧生成 output_video
    image = cv2.imread(output_image)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(clip_video, fourcc, fps, (width, height))
    for _ in range(frame_count_new):
        video_writer.write(image)
    video_writer.release()
    # 连接源视频和该片段
    runffmpeg(
        f'-y -i "{novoice_mp4}" -i "{clip_video}" -filter_complex "[0:v]setsar=1[v0];[1:v]setsar=1[v1];[v0][v1]concat=n=2:v=1:a=0[outv]" -map "[outv]" -c:v libx264 -y "{novoice_mp4}-tmp.mp4"')
    os.rename(novoice_mp4,novoice_mp4+'.raw.mp4')
    os.rename(novoice_mp4+"-tmp.mp4",novoice_mp4)

# 连接 1.mp4 和 2.mp4
# output_final = "out.mp4"
# os.system(f"ffmpeg -i 1.mp4 -i 2.mp4 -filter_complex '[0:v][1:v]concat=n=2:v=1:a=0[v]' -map '[v]' -c:v libx264 -y {output_final}")
# print(f"Successfully concatenated 1.mp4 and 2.mp4 to {output_final}")

add_clip_to_last('c:/users/c1/videos/ceshi.mp4',8500)