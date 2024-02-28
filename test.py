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


#from videotrans.util import tools


#tools.get_subtitle_from_srt(r'C:\Users\c1\Videos\dev\0001.srt',is_file=True)


# 整体识别，全部传给模型
from faster_whisper import WhisperModel

from videotrans.util import tools


def all_recogn(wavfile,*, detect_language=None, model_name="base"):
    try:
        model = WhisperModel(model_name, device="cpu",
                             download_root="./models",
                             local_files_only=True)
        segments, info = model.transcribe(wavfile,
                                          word_timestamps=True,
                                          language=detect_language,
                                          initial_prompt="转录为中文简体。")

        raw_subtitles=[]
        # 存储每个字的信息
        word_list=[]
        for segment in segments:
            word_list.extend(list(segment.words))
            print(f'{segment.words[0].start},{segment.text}')

        #保留最后一句
        last=[]
        #首选分割符号
        split_line=[".","?","!","。","？","！"]
        #次级分割符号
        split_second=[",","，"," ","、","/"]
        for i,word in enumerate(word_list):
            if i>0 and len(last)>=30 and (word.word[-1].strip() in split_second or word.word.strip() in split_second):
                last.append(word)
                raw_subtitles.append({
                    "start_time": last[0].start,
                    "end_time": last[-1].end,
                    "text": "".join([t.word for t in last]),
                    "time":tools.ms_to_time_string(seconds=last[0].start)+" --> "+tools.ms_to_time_string(seconds=last[-1].end),
                    "line":len(raw_subtitles)+1,
                    "ditt":last[-1].end-last[0].start
                })
                last = []
            # 首选分割
            elif i>0 and (word.word[-1].strip() in split_line or word.word.strip() in split_line):
                last.append(word)
                raw_subtitles.append({
                    "start_time":last[0].start,
                    "end_time":last[-1].end,
                    "time":tools.ms_to_time_string(seconds=last[0].start)+" --> "+tools.ms_to_time_string(seconds=last[-1].end),
                    "text":"".join([t.word for t in last]),
                    "line":len(raw_subtitles)+1,
                    "ditt":last[-1].end-last[0].start
                })
                last=[]
            # 大于 300ms强制分割
            elif i>0 and (word.start - word_list[i-1].end>=0.3):
                if len(last)>0:
                    raw_subtitles.append({
                        "start_time":last[0].start,
                        "end_time":last[-1].end,
                        "text":"".join([t.word for t in last]),
                        "time":tools.ms_to_time_string(seconds=last[0].start)+" --> "+tools.ms_to_time_string(seconds=last[-1].end),
                        "line":len(raw_subtitles)+1,
                        "ditt":last[-1].end-last[0].start
                    })
                last=[word]
            #大于30个字符，并且在次级分割
            else:
                last.append(word)

        for i,it in enumerate(raw_subtitles):
            raw_subtitles[i]['text']=it['text'].replace('&#39;',"'")

        print(raw_subtitles)
    except Exception as e:
        raise Exception(f'whole all {str(e)}')

all_recogn(r'C:\Users\c1\Videos\60.wav')