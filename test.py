'''
import requests
from PySide6.QtCore import QSettings

from videotrans.configure import config

url=QSettings("Jameson", "VideoTranslate").value("clone_api", "")
print(f'{url=}')
if not url:
    print(config.transobj['bixutianxiecloneapi'])
else:
    try:
        url = url.strip().rstrip('/') + "/init"
        res = requests.get('http://' + url.replace('http://', ''))
        if res.status_code == 200:
            print(res.json)
            print("\nOK\n")
        else:
            raise Exception(f"code={res.status_code},{config.transobj['You must deploy and start the clone-voice service']}")
    except Exception as e:
        print(f'[error]:clone-voice:{str(e)}')


input("Press Enter for quit")
'''

# from videotrans.separate import st
# try:
#     gr = st.uvr(model_name="HP2", save_root="./", inp_path=r'C:/Users/c1/Videos/240.wav')
#     print(next(gr))
#     print(next(gr))
# except Exception as e:
#     msg=f"separate vocal and background music:{str(e)}"
#     #set_process(msg)
#     print(msg)


## 获取识别文字
# import os
# from faster_whisper import WhisperModel
# model = WhisperModel("base", device="cpu",
#                              download_root="./models",
#                              local_files_only=True)
# data=[]
#
# for i in range(0,24):
#     name=f'output0{str(i).zfill(2)}.wav'
#     if not os.path.exists(f'c:/users/c1/videos/_video_out/{name}'):
#         continue
#     segments, info = model.transcribe(f'c:/users/c1/videos/_video_out/{name}',
#                                           beam_size=1,
#                                           best_of=1,
#                                           condition_on_previous_text=False,language="zh")
#     res=[]
#     for segment in segments:
#         res.append(segment.text.strip())
#     data.append(f"wavs/{name}|{'.'.join(res)}|coqui")
#
# with open("./metadata_train.csv","w",encoding='utf-8') as f:
#     f.write("\n".join(data))

# import requests
# lang=["zh-hans","zh-hant","en","fr","de","ja","ko","ru","es","th","it","pt","vi","ar","tr","hi","hu"]
#
# auth=requests.get('https://edge.microsoft.com/translate/auth')
#
# for it in lang:
#     url=f'https://api-edge.cognitive.microsofttranslator.com/translate?from=&to={it}&api-version=3.0&includeSentenceLength=true'
#     res=requests.post(url,json=[{"Text":"hello,my friend\nI am from China"}],headers={"Authorization":f"Bearer {auth.text}"})
#     print(res.json())


# from videotrans.util import tools
#
# cmd=["-y",'-ss', '0', '-to', '00:00:01.300', '-i', 'C:/Users/c1/Videos/pyvideotrans/renamemp4/_video_out/31-副本/novoice.mp4', '-vf', 'setpts=1.96*PTS', '-c:v', 'libx264', '-crf', '13', 'F:/python/pyvideo/tmp/31-副本/novoice_tmp.mp4']
#
# tools.runffmpeg(cmd)
# import time

# a="有新的版本哦，快去升级吧"
# length=len(a)
# while 1:
#     for i in range(length):
#         if i==0:
#             print(a)
#         elif i==length-1:
#             print(a[i]+a[:i])
#         else:
#             print(a[i:]+a[:i])
#         time.sleep(0.1)
#     time.sleep(5)


# from videotrans.util import tools


# tools.get_subtitle_from_srt(r'C:\Users\c1\Videos\dev\0001.srt',is_file=True)


# import re
#
# def format_time(s_time="",separate=','):
#     if not s_time.strip():
#         return f'00:00:00.000'
#     hou,min,sec="00","00","00.000"
#     tmp=s_time.split(':')
#     if len(tmp)>=3:
#         hou=tmp[-3]
#         min=tmp[-2]
#         sec=tmp[-1]
#     elif len(tmp)==2:
#         min=tmp[0]
#         sec=tmp[1]
#     elif len(tmp)==1:
#         sec=tmp[0]
#
#     if re.search(r',|\.',str(sec)):
#         sec,ms=re.split(r',|\.',str(sec))
#     else:
#         ms='000'
#     hou=hou if hou!="" else "00"
#     if len(hou)<2:
#         hou=f'0{hou}'
#     hou=hou[-2:]
#
#     min=min if min!="" else "00"
#     if len(min)<2:
#         min=f'0{min}'
#     min=min[-2:]
#
#     sec=sec if sec!="" else "00"
#     if len(sec)<2:
#         sec=f'0{sec}'
#     sec=sec[-2:]
#
#     ms_len=len(ms)
#     if ms_len<3:
#         for i in range(3-ms_len):
#             ms=f'0{ms}'
#     ms=ms[-3:]
#     return f"{hou}:{min}:{sec}{separate}{ms}"
#
# print(format_time('',','))


#
# import httpx, json,requests
#
# deeplx_api = "https://service-2rlyleme-1259515617.gz.tencentapigw.com.cn/translate"
#
# data = {
#     "text": "你好我的朋友",
#     "source_lang": "auto",
#     "target_lang": "en"
# }
# res=requests.post(url=deeplx_api, json=data)
# print(res.json())
import textwrap

from videotrans.util.tools import get_subtitle_from_srt

maxlen = 24
source_sub = get_subtitle_from_srt(r'C:\Users\c1\Videos\_video_out\1\zh-cn.srt')
source_length = len(source_sub)
subtitles=''

for i, it in enumerate(source_sub):
    if source_length > 0 and i < source_length:
        subtitles += "\n" + textwrap.fill(source_sub[i]['text'], maxlen).strip()
    subtitles += "\n\n"
print(subtitles)
