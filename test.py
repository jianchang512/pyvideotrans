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

import os
import sys
import winreg
from ctypes.util import find_library

import requests
from PyQt5.QtCore import QUrl, QThread
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent


def get_windows_proxy():
    try:
        # 打开 Windows 注册表
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            # 读取代理设置
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')

            if proxy_enable == 1 and proxy_server:
                return proxy_server

    except Exception as e:
        print(f"Error accessing Windows registry: {e}")

    return None

class W1(QThread):
    def __init__(self):
        super(W1, self).__init__()
    def run(self) -> None:
        mediaPlayer = QMediaPlayer()
        url = QUrl.fromLocalFile(r'C:\Users\c1\Videos\_video_out\1.mp3')
        content = QMediaContent(url)
        mediaPlayer.setMedia(content)
        mediaPlayer.play()
def get_subtitle_from_srt(srtfile):
    with open(srtfile,'r',encoding="utf-8") as f:
        txt=f.read().strip().split("\n")
    # 行号
    line=0
    maxline=len(txt)
    # 行格式
    linepat=r'^\s*?\d+\s*?$'
    # 时间格式
    timepat=r'^\s*?\d+:\d+:\d+\,?\d*?\s*?-->\s*?\d+:\d+:\d+\,?\d*?$'
    result=[]
    for i,t in enumerate(txt):
        # 当前行 小于等于倒数第三行 并且匹配行号，并且下一行匹配时间戳，则是行号
        if i < maxline-2 and re.match(linepat,t) and re.match(timepat,txt[i+1]):
            #   是行
            line+=1
            obj={"line":line,"time":"","text":""}
            result.append(obj)
        elif re.match(timepat,t):
            # 是时间行
            result[line-1]['time']=t
        elif len(t.strip())>0:
            # 是内容
            print(f"{line=},{next=}")
            result[line-1]['text']+=t.strip()
    # 再次遍历，删掉美元text的行
    new_result=[]
    line=1
    for it in result:
        if "text" in it and len(it['text'].strip())>0 and not re.match(r'^[,./?`!@#$%^&*()_+=\\|\[\]{}~\s \n-]*$',it['text']):
            it['line']=line
            startraw, endraw = it['time'].strip().split(" --> ")
            start = startraw.replace(',', '.').split(":")
            start_time = int(int(start[0]) * 3600000 + int(start[1]) * 60000 + float(start[2]) * 1000)
            end = endraw.replace(',', '.').split(":")
            end_time = int(int(end[0]) * 3600000 + int(end[1]) * 60000 + float(end[2]) * 1000)
            # start_time end_time startraw endraw
            it['startraw']=startraw
            it['endraw']=endraw
            it['start_time']=start_time
            it['end_time']=end_time
            new_result.append(it)
            line+=1
    return new_result

print(get_subtitle_from_srt(r'C:\Users\c1\Videos\ceshi2.srt'))