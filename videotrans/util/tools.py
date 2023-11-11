import asyncio
import json
import sys

import cv2
import edge_tts

from ..configure import boxcfg
from ..configure.boxcfg import logger, rootdir, cfg
import subprocess
from datetime import timedelta
import os
import whisper


# 获取代理，如果已设置os.environ代理，则返回该代理值,否则获取系统代理
def get_proxy(set_env=False):
    http_proxy = os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY')
    if http_proxy:
        return http_proxy

    if sys.platform != 'win32':
        return None
    try:
        import winreg
        # 打开 Windows 注册表
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            # 读取代理设置
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')

            if proxy_enable == 1 and proxy_server:
                # 是否需要设置代理
                if set_env:
                    os.environ['http_proxy'] = 'http://%s' % proxy_server.replace("http://", '')
                    os.environ['https_proxy'] = 'http://%s' % proxy_server.replace("http://", '')
                return proxy_server

    except Exception as e:
        print(f"Error accessing Windows registry: {e}")

    return None

def runffmpeg(arg):
    logger.info("Will execute: ffmpeg " + " ".join(arg))

    cmd = "ffmpeg "
    if boxcfg.enable_cuda:
        cmd += " -hwaccel cuda "
    if isinstance(arg, list):
        cmd += " ".join(arg)
    else:
        cmd += arg
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)

    while True:
        try:
            print(f"ffmpeg执行状态:{'执行中' if p.poll() is None else '已结束'}")
            print(f"out={p.stdout}")
            rs = p.wait(3)
            print(f"执行结果:{'成功' if rs == 0 else '失败'}")
            if p.returncode != 0:
                logger.error(f"FFmepg exec error:{rs=},{p.returncode=}")
                break
            return True
        except Exception as e:
            print("ffmpeg 等待中:" + str(e))
    raise Exception("ffmpeg exec error")


def transcribe_audio(audio_path, model, language):
    model = whisper.load_model(model, download_root=rootdir + "/models")  # Change this to your desired model
    print("Whisper model loaded." + language)
    transcribe = model.transcribe(audio_path, language="zh" if language in ["zh-cn", "zh-tw"] else language)
    segments = transcribe['segments']
    print(f"{segments=}")
    result = ""
    for segment in segments:
        startTime = str(0) + str(timedelta(seconds=int(segment['start']))) + ',000'
        endTime = str(0) + str(timedelta(seconds=int(segment['end']))) + ',000'
        text = segment['text']
        segmentId = segment['id'] + 1
        result += f"{segmentId}\n{startTime} --> {endTime}\n{text.strip()}\n\n"
    return result


#  get role by edge tts
def get_list_voices():
    voice_list = {}
    if os.path.exists(rootdir + "/voice_list.json"):
        try:
            voice_list = json.load(open(rootdir + "/voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                return voice_list
        except:
            pass
    v = asyncio.run(edge_tts.list_voices())
    for it in v:
        name = it['ShortName']
        prefix = name.split('-')[0].lower()
        if prefix not in voice_list:
            voice_list[prefix] = [name]
        else:
            voice_list[prefix].append(name)
    json.dump(voice_list, open(rootdir + "/voice_list.json", "w"))
    return voice_list


def create_voice(text, role, rate, filename):
    communicate = edge_tts.Communicate(text,
                                       role,
                                       rate=rate
                                       )
    asyncio.run(communicate.save(f"{filename}.wav"))
    return True


def get_camera_list():
    if boxcfg.check_camera_ing:
        return
    boxcfg.check_camera_ing = True
    index = 0
    if len(boxcfg.camera_list) > 0:
        boxcfg.check_camera_ing = False
        return
    print("获取摄像头")
    try:
        while True:
            camera = cv2.VideoCapture(index)
            if not camera.read()[0]:
                break
            else:
                boxcfg.camera_list.append(index)
                index += 1
        camera.release()
    except Exception as e:
        print("获取摄像头出错")
    boxcfg.check_camera_ing = False
