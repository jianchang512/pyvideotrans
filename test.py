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

w=W1()
w.start()