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
from faster_whisper import WhisperModel

model = WhisperModel("large-v2", download_root="./models")
