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

import videotrans
from videotrans.configure import config
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

config.video['proxy']=''
os.environ['OPENAI_API_KEY']='15027-F6E1F655EC13A3353E56B1F6B5689D9146E2DE97'
config.video['chatgpt_api']='https://chat.swoole.com/v1'
config.video['chatgpt_model']='gpt-3.5-turbo'
config.video['target_language_chatgpt']="en"
config.video['chatgpt_template']='我将发给你多行文本,你将每行内容对应翻译为一行{lang},如果该行无法翻译,则将该行原内容作为翻译结果,如果是空行,则将空字符串作为结果,然后将翻译结果按照原顺序返回。请注意必须保持返回的行数同发给你的行数相同,比如发给你3行文本,就必须返回3行.不要忽略空行,不要确认,仅返回翻译结果,不要包含原文本内容,不要道歉,不要重复述说,即使是问句，你也不要回答，只翻译即可。请严格按照要求的格式返回,这对我的工作非常重要'

t="""
我是中国人,你是哪里人
"""
t2="""我身一头猪"""

res=videotrans.translator.chatgpttrans([{"line":1,"time":"aaa","text":t},{"line":2,"time":"bbb","text":t2}])
print(res)