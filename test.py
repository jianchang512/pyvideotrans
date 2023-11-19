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


import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models

try:
    # 实例化一个认证对象，入参需要传入腾讯云账户 SecretId 和 SecretKey，此处还需注意密钥对的保密
    # 代码泄露可能会导致 SecretId 和 SecretKey 泄露，并威胁账号下所有资源的安全性。以下代码示例仅供参考，建议采用更安全的方式来使用密钥，请参见：https://cloud.tencent.com/document/product/1278/85305
    # 密钥可前往官网控制台 https://console.cloud.tencent.com/cam/capi 进行获取
    cred = credential.Credential("AKIDeFqaIrIXcWO7oIg4gCjPzNdltlcNQNJ5", "jMuOm1BEMeqvyvmbSEufNuPuJcyHavAJ")
    # 实例化一个http选项，可选的，没有特殊需求可以跳过
    httpProfile = HttpProfile()
    httpProfile.endpoint = "tmt.tencentcloudapi.com"

    # 实例化一个client选项，可选的，没有特殊需求可以跳过
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    # 实例化要请求产品的client对象,clientProfile是可选的
    client = tmt_client.TmtClient(cred, "ap-beijing", clientProfile)

    # 实例化一个请求对象,每个接口都会对应一个request对象
    req = models.TextTranslateRequest()
    params = {
        "SourceText": "我是中国人",
        "Source": "auto",
        "Target": "en",
        "ProjectId": 0
    }
    req.from_json_string(json.dumps(params))

    # 返回的resp是一个TextTranslateResponse的实例，与请求对象对应
    resp = client.TextTranslate(req)
    # 输出json格式的字符串回包
    print(resp.TargetText)
except TencentCloudSDKException as err:
    print(err)