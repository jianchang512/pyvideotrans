import ctypes
import io
import json
import os
import re
import subprocess

# cmd=f"ffmpeg -y -i \"C:/Users/c1/Videos/kx.mp4\" -c:v libx264 -c:a pcm_s16le ceshi.mp4"
#
# p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=True)
#
# while True:
#     try:
#         print(f"是否结束={p.poll()}")
#
#
#         rs=p.wait(5)
#         print("rs后边有没有来到")
#         print(f"{rs=},returncode={p.returncode=}")
#         print(f"out={p.stdout}")
#         break
#     except Exception as e:
#         print("异常"+str(e))


# with open(r'C:\Users\c1\Videos\_video_out\srt\earth.srt', "r", encoding="utf-8") as f:
#     tx = re.split(r"\n\s*?\n", f.read().strip())
#     for (idx, it) in enumerate(tx):
#         c = it.strip().split("\n")
#         start, end = c[1].strip().split(" --> ")
#         text = "".join(c[2:]).strip()
#         print(f"{text=}")



from pydub import AudioSegment
from pydub.silence import detect_nonsilent
merged_audio = AudioSegment.empty()
merged_audio+=AudioSegment.from_wav("./hc22.wav")
#exit()
merged_audio += AudioSegment.silent(duration=82000)
merged_audio.export("./tts.wav", format="wav")