# -*- coding: utf-8 -*-
import ctypes
import inspect

from videotrans.configure import boxcfg
from videotrans.configure.config import rootdir
from ctypes.util import find_library
import asyncio
import copy
import re
import shutil
import subprocess
import sys
import threading
import time

import speech_recognition as sr
import os

import whisper
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import srt
from datetime import timedelta
import json
import edge_tts
import textwrap
import pygame
from videotrans.translator import baidutrans, googletrans, tencenttrans, chatgpttrans, deepltrans, deeplxtrans, \
    baidutrans_spider

from videotrans.configure import config
from videotrans.configure.config import logger, transobj, queue_logs

# 获取代理，如果已设置os.environ代理，则返回该代理值,否则获取系统代理
from videotrans.tts import get_voice_openaitts, get_voice_edgetts

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

def pygameaudio(filepath):
	pygame.mixer.music.load(filepath)
	pygame.mixer.music.play()
	while pygame.mixer.music.get_busy():
		# 等待音乐播放完成
		pygame.time.Clock().tick(1)

def transcribe_audio(audio_path, model, language):
    model = whisper.load_model(model, download_root=rootdir + "/models")  # Change this to your desired model
    transcribe = model.transcribe(audio_path, language="zh" if language in ["zh-cn", "zh-tw"] else language)
    segments = transcribe['segments']
    result = ""
    for segment in segments:
        startTime = str(0) + str(timedelta(seconds=int(segment['start']))) + ',000'
        endTime = str(0) + str(timedelta(seconds=int(segment['end']))) + ',000'
        text = segment['text']
        segmentId = segment['id'] + 1
        result += f"{segmentId}\n{startTime} --> {endTime}\n{text.strip()}\n\n"
    return result



def find_lib():
    dll = None
    plugin_path = os.environ.get('PYTHON_VLC_MODULE_PATH', None)
    if 'PYTHON_VLC_LIB_PATH' in os.environ:
        try:
            dll = ctypes.CDLL(os.environ['PYTHON_VLC_LIB_PATH'])
        except OSError:
            return
    if plugin_path and not os.path.isdir(plugin_path):
        return
    if dll is not None:
        return dll, plugin_path

    if sys.platform.startswith('win'):
        libname = 'libvlc.dll'
        p = find_library(libname)
        if p is None:
            try:  # some registry settings
                # leaner than win32api, win32con
                import winreg as w
                for r in w.HKEY_LOCAL_MACHINE, w.HKEY_CURRENT_USER:
                    try:
                        r = w.OpenKey(r, 'Software\\VideoLAN\\VLC')
                        plugin_path, _ = w.QueryValueEx(r, 'InstallDir')
                        w.CloseKey(r)
                        break
                    except w.error:
                        pass
            except ImportError:  # no PyWin32
                pass
            if plugin_path is None:
                # try some standard locations.
                programfiles = os.environ["ProgramFiles"]
                homedir = os.environ["HOMEDRIVE"]
                for p in ('{programfiles}\\VideoLan{libname}', '{homedir}:\\VideoLan{libname}',
                          '{programfiles}{libname}', '{homedir}:{libname}'):
                    p = p.format(homedir=homedir,
                                 programfiles=programfiles,
                                 libname='\\VLC\\' + libname)
                    if os.path.exists(p):
                        plugin_path = os.path.dirname(p)
                        break
            if plugin_path is not None:  # try loading
                # PyInstaller Windows fix
                if 'PyInstallerCDLL' in ctypes.CDLL.__name__:
                    ctypes.windll.kernel32.SetDllDirectoryW(None)
                p = os.getcwd()
                os.chdir(plugin_path)
                # if chdir failed, this will raise an exception
                dll = ctypes.CDLL('.\\' + libname)
                # restore cwd after dll has been loaded
                os.chdir(p)
            else:  # may fail
                dll = ctypes.CDLL('.\\' + libname)
        else:
            plugin_path = os.path.dirname(p)
            dll = ctypes.CDLL(p)

    elif sys.platform.startswith('darwin'):
        # FIXME: should find a means to configure path
        d = '/Applications/VLC.app/Contents/MacOS/'
        c = d + 'lib/libvlccore.dylib'
        p = d + 'lib/libvlc.dylib'
        if os.path.exists(p) and os.path.exists(c):
            # pre-load libvlccore VLC 2.2.8+
            ctypes.CDLL(c)
            dll = ctypes.CDLL(p)
            for p in ('modules', 'plugins'):
                p = d + p
                if os.path.isdir(p):
                    plugin_path = p
                    break
        else:  # hope, some [DY]LD_LIBRARY_PATH is set...
            # pre-load libvlccore VLC 2.2.8+
            ctypes.CDLL('libvlccore.dylib')
            dll = ctypes.CDLL('libvlc.dylib')

    else:
        # All other OSes (linux, freebsd...)
        p = find_library('vlc')
        try:
            dll = ctypes.CDLL(p)
        except OSError:  # may fail
            dll = None
        if dll is None:
            try:
                dll = ctypes.CDLL('libvlc.so.5')
            except:
                raise NotImplementedError('Cannot find libvlc lib')

    return dll


def set_proxy(set_val=''):
    if set_val=='del':
        # 删除代理
        if os.environ.get('http_proxy'):
            os.environ.pop('http_proxy')
        if os.environ.get('https_proxy'):
            os.environ.pop('https_proxy')
        return None
    if set_val:
        # 设置代理
        if set_val.startswith("http") or set_val.startswith('sock'):
            os.environ['http_proxy'] = set_val
            os.environ['https_proxy'] =set_val
        else:
            set_val=f"http://{set_val}"
            os.environ['http_proxy'] = set_val
            os.environ['https_proxy'] =set_val
        return set_val
    #获取代理
    http_proxy = os.environ.get('http_proxy') or os.environ.get('https_proxy')
    if http_proxy:
        if not http_proxy.startswith("http") and not http_proxy.startswith('sock'):
            http_proxy=f"http://{http_proxy}"
            os.environ['http_proxy'] = http_proxy
            os.environ['https_proxy'] = http_proxy
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
                if proxy_server.startswith("http") or proxy_server.startswith('sock'):
                    os.environ['http_proxy'] = proxy_server
                    os.environ['https_proxy'] =proxy_server
                else:
                    proxy_server= "http://"+proxy_server
                    os.environ['http_proxy'] =proxy_server
                    os.environ['https_proxy'] =proxy_server
                return proxy_server
    except Exception as e:
        print(f"Error accessing Windows registry: {e}")
    return None


# delete tmp files
def delete_temp(noextname=None):
    try:
        if noextname and os.path.exists(f"{config.rootdir}/tmp/{noextname}"):
            shutil.rmtree(f"{config.rootdir}/tmp/{noextname}")
        elif os.path.exists(f"{config.rootdir}/tmp"):
            shutil.rmtree(f"{config.rootdir}/tmp")
    except:
        pass


#  get role by edge tts
def get_edge_rolelist():
    voice_list = {}
    if os.path.exists(config.rootdir + "/voice_list.json"):
        try:
            voice_list = json.load(open(config.rootdir + "/voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                config.edgeTTS_rolelist = voice_list
                return voice_list
        except:
            pass
    try:
        v = asyncio.run(edge_tts.list_voices())
    except Exception as e:
        logger.error('获取edgeTTS角色失败'+str(e))
        print('获取edgeTTS角色失败'+str(e))
    for it in v:
        name = it['ShortName']
        prefix = name.split('-')[0].lower()
        if prefix not in voice_list:
            voice_list[prefix] = ["No", name]
        else:
            voice_list[prefix].append(name)
    json.dump(voice_list, open(config.rootdir + "/voice_list.json", "w"))
    config.edgeTTS_rolelist = voice_list
    return voice_list


# split audio by silence
def shorten_voice(normalized_sound):
    normalized_sound = match_target_amplitude(normalized_sound, -20.0)
    max_interval = 10000
    buffer = 500
    nonsilent_data = []
    audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.params['voice_silence']),
                                    silence_thresh=-20 - 25)
    # print(audio_chunks)
    for i, chunk in enumerate(audio_chunks):
        start_time, end_time = chunk
        n = 0
        while end_time - start_time >= max_interval:
            n += 1
            # new_end = start_time + max_interval+buffer
            new_end = start_time + max_interval + buffer
            new_start = start_time
            nonsilent_data.append((new_start, new_end, True))
            start_time += max_interval
        nonsilent_data.append((start_time, end_time, False))
    return nonsilent_data


#
def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


# join all short audio to one ,eg name.mp4  name.mp4.wav
def merge_audio_segments(segments, start_times, total_duration, noextname):
    merged_audio = AudioSegment.empty()
    # start is not 0
    if start_times[0] != 0:
        silence_duration = start_times[0]
        silence = AudioSegment.silent(duration=silence_duration)
        merged_audio += silence

    # join
    for i in range(len(segments)):
        segment = segments[i]
        start_time = start_times[i]
        # add silence
        if i > 0:
            previous_end_time = start_times[i - 1] + len(segments[i - 1])
            silence_duration = start_time - previous_end_time
            # 前面一个和当前之间存在静音区间
            if silence_duration > 0:
                silence = AudioSegment.silent(duration=silence_duration)
                merged_audio += silence

        merged_audio += segment
    if total_duration > 0 and (len(merged_audio) < total_duration):
        # 末尾补静音
        silence = AudioSegment.silent(duration=total_duration - len(merged_audio))
        merged_audio += silence
    # 如果新长度大于原时长，则末尾截断
    if total_duration > 0 and (len(merged_audio) > total_duration):
        # 截断前先保存原完整文件
        merged_audio.export(f'{config.params["target_dir"]}/{noextname}/{config.params["target_language"]}-nocut.wav',
                            format="wav")
        merged_audio = merged_audio[:total_duration]
    # 创建配音后的文件
    merged_audio.export(f"{config.rootdir}/tmp/{noextname}/tts-{noextname}.wav", format="wav")
    shutil.copy(
        f"{config.rootdir}/tmp/{noextname}/tts-{noextname}.wav",
        f"{config.params['target_dir']}/{noextname}/{config.params['target_language']}.wav"
    )
    return merged_audio


# speed change
def speed_change(sound, speed=1.0):
    # Manually override the frame_rate. This tells the computer how many
    # samples to play per second
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    })
    # convert the sound with altered frame rate to a standard frame rate
    # so that regular playback programs will work right. They often only
    # know how to play audio at standard frame rate (like 44.1k)
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)


def runffmpegbox(arg):
    cmd = ["ffmpeg","-hide_banner","-vsync","0"]
    if config.params['cuda']:
        cmd.extend(["-hwaccel", "cuda","-hwaccel_output_format","cuda"])
        for i, it in enumerate(arg):
            if i>0 and arg[i-1]=='-c:v':
                arg[i]=it.replace('libx264',"h264_nvenc").replace('copy','h264_nvenc')
    cmd = cmd + arg

    print(f"runffmpeg: {cmd=}")
    p = subprocess.run(cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
    if p.returncode==0:
        return True
    print(str(p.stderr))
    return False


# 执行 ffmpeg
def runffmpeg(arg, *, noextname=None, error_exit=True):
    cmd = ["ffmpeg","-hide_banner","-vsync","0"]
    if config.params['cuda']:
        cmd.extend(["-hwaccel", "cuda","-hwaccel_output_format","cuda"])
        for i, it in enumerate(arg):
            if i>0 and arg[i-1]=='-c:v':
                arg[i]=it.replace('libx264',"h264_nvenc").replace('copy','h264_nvenc')
            
    cmd = cmd + arg

    if noextname:
        config.queue_novice[noextname] = 'ing'
    p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
    def set_result(code,errs=""):
        if code == 0:
            config.queue_novice[noextname] = "end"
            return True
        else:
            config.queue_novice[noextname] = "error"
            set_process(f"[error]ffmpeg error: {cmd=},\n{errs=}")
            if config.params['cuda']:
                set_process("[error] Please try upgrading the graphics card driver and reconfigure CUDA")
            return False
    while True:
        try:
            #等待0.1未结束则异常
            outs, errs = p.communicate(timeout=0.5)
            errs=str(errs)
            if errs:
                errs = errs.replace('\\\\','\\').replace('\r',' ').replace('\n',' ')
                errs=errs[errs.find("Error"):]

            # 如果结束从此开始执行
            if set_result(p.returncode,str(errs)):
                # 成功
                return True
            # 失败
            if error_exit and config.params['cuda']:
                set_process("[error] Please try upgrading the graphics card driver and reconfigure CUDA")
            elif error_exit:
                set_process(f'ffmpeg error:{errs=}','error')
            return False
        except subprocess.TimeoutExpired as e:
            # 如果前台要求停止
            if config.current_status != 'ing':
                try:
                    p.terminate()
                    p.kill()
                except:
                    pass
                return False
        except Exception as e:
            #出错异常
            if error_exit and config.params['cuda']:
                set_process("[error] Please try upgrading the graphics card driver and reconfigure CUDA",'error')
            else:
                set_process(f"[error]ffmpeg执行结果:失败 {cmd=},\n{str(e)}",'error' if error_exit else 'logs')
            return False



# run ffprobe 获取视频元信息
def runffprobe(cmd):
    try:
        result = subprocess.run(f'ffprobe {cmd}', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if result.returncode == 0:
            return result.stdout.strip()
        set_process(f'ffprobe error:{result.stdout=},{result.stderr=}')
        return False
    except subprocess.CalledProcessError as e:
        set_process(f'ffprobe error:{str(e)}')
        return False


# 获取某个视频的时长 s
def get_video_duration(file_path):
    duration = runffprobe(
        f' -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"')
    if not duration:
        return False
    return int(float(duration) * 1000)


# 获取某个视频的fps
def get_video_fps(file_path):
    res = runffprobe(
        f'-v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "{file_path}"')
    if not res:
        return False
    f,s=res.split('/')
    fps=30
    try:
        f=int(f)
        if s:
            s=str(s).strip()
        if s and int(s)>0:
            fps=round(f/int(s),1)
        else:
            fps=f
    except:
        pass
    return fps


# 获取宽高分辨率
def get_video_resolution(file_path):
    width = runffprobe(f'-v error -select_streams v:0 -show_entries stream=width -of csv=s=x:p=0 "{file_path}"')
    height = runffprobe(f'-v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "{file_path}"')
    if not width or not height:
        return False
    return int(width), int(height)


# 取出最后一帧图片
def get_lastjpg_fromvideo(file_path, img):
    return runffmpeg(['-y','-sseof','-3','-i',f'{file_path}','-vsync','0','-q:v','1','-qmin:v','1','-qmax:v','1','-update','true',f'{img}'])


# 文字合成
def text_to_speech(*, text="", role="", rate='+0%', filename=None, tts_type=None, play=False):
    try:
        if rate !='+0%':
            set_process(f'text to speech speed {rate}')
        if tts_type == "edgeTTS":
            if not get_voice_edgetts(text=text, role=role, rate=rate, filename=filename):
                logger.error(f"edgeTTS error")
                open(filename, "w").close()
                return False
        elif tts_type == "openaiTTS":
            if not get_voice_openaitts(text, role, rate, filename):
                logger.error(f"openaiTTS error")
                open(filename, "w").close()
                return False
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            if play:
                threading.Thread(target=pygameaudio, args=(filename, )).start()            
            return True
        return False
    except Exception as e:
        logger.error(f"text to speech:{filename=},{tts_type=}," + str(e))
        open(filename, "w").close()
        return False


def show_popup(title, text):
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setWindowIcon(QIcon(config.rootdir + "/icon.ico"))
    msg.setText(text)
    msg.addButton(transobj['queding'], QMessageBox.AcceptRole)
    msg.addButton("Cancel", QMessageBox.RejectRole)
    msg.setIcon(QMessageBox.Information)
    # msg.setStandardButtons(QMessageBox.Ok)
    x = msg.exec_()  # 显示消息框

    return x


'''
print(ms_to_time_string(ms=12030))
-> 00:00:12,030
'''


def ms_to_time_string(*, ms=0, seconds=None):
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



# 从字幕文件获取格式化后的字幕信息
'''
[
{'line': 13, 'time': '00:01:56,423 --> 00:02:06,423', 'text': '因此，如果您准备好停止沉迷于不太理想的解决方案并开始构建下一个
出色的语音产品，我们已准备好帮助您实现这一目标。深度图。没有妥协。唯一的机会..', 'startraw': '00:01:56,423', 'endraw': '00:02:06,423', 'start_time'
: 116423, 'end_time': 126423}, 
{'line': 14, 'time': '00:02:06,423 --> 00:02:07,429', 'text': '机会..', 'startraw': '00:02:06,423', 'endraw': '00:02
:07,429', 'start_time': 126423, 'end_time': 127429}
]
'''


def get_subtitle_from_srt(srtfile, *, is_file=True):
    if is_file:
        with open(srtfile, 'r', encoding="utf-8") as f:
            txt = f.read().strip().split("\n")
    else:
        txt = srtfile.strip().strip().split("\n")
    # 行号
    line = 0
    maxline = len(txt)
    # 行格式
    linepat = r'^\s*?\d+\s*?$'
    # 时间格式
    timepat = r'^\s*?\d+:\d+:\d+\,?\d*?\s*?-->\s*?\d+:\d+:\d+\,?\d*?$'
    result = []
    # print(f'{maxline=}')
    for i, t in enumerate(txt):
        # print(f'{i=},{t=}，i+1={txt[i+1]}')
        # 当前行 小于等于倒数第三行 并且匹配行号，并且下一行匹配时间戳，则是行号
        if i < maxline - 2 and re.match(linepat, t) and re.match(timepat, txt[i + 1]):
            # print('匹配那个1')
            #   是行
            line += 1
            obj = {"line": line, "time": "", "text": ""}
            result.append(obj)
        elif re.match(timepat, t):
            # print('匹配那个2')
            # 是时间行
            result[line - 1]['time'] = t
        elif len(t.strip()) > 0:
            # print('匹配那个3')
            # 是内容
            txt_tmp = t.strip().replace('&#39;', "'")
            txt_tmp = re.sub(r'&#\d+;', '', txt_tmp)
            result[line - 1]['text'] += txt_tmp
    # 再次遍历，删掉美元text的行
    new_result = []
    line = 1
    for it in result:
        if "text" in it and len(it['text'].strip()) > 0 and not re.match(r'^[,./?`!@#$%^&*()_+=\\|\[\]{}~\s \n-]*$',
                                                                         it['text']):
            it['line'] = line
            startraw, endraw = it['time'].strip().split(" --> ")
            start = startraw.replace(',', '.').split(":")
            start_time = int(int(start[0]) * 3600000 + int(start[1]) * 60000 + float(start[2]) * 1000)
            end = endraw.replace(',', '.').split(":")
            end_time = int(int(end[0]) * 3600000 + int(end[1]) * 60000 + float(end[2]) * 1000)
            it['startraw'] = startraw
            it['endraw'] = endraw
            it['start_time'] = start_time
            it['end_time'] = end_time
            new_result.append(it)
            line += 1
    return new_result


# 判断 novoice.mp4是否创建好
def is_novoice_mp4(novoice_mp4, noextname):
    # 预先创建好的
    # 判断novoice_mp4是否完成
    t = 0
    if noextname not in config.queue_novice and os.path.exists(novoice_mp4) and os.path.getsize(novoice_mp4)>0:
        return True
    last_size=0
    while True:
        if config.current_status != 'ing':
            return False
        if os.path.exists(novoice_mp4):
            current_size=os.path.getsize(novoice_mp4)
            if last_size>0 and current_size==last_size and t>300:
                return True
            last_size=current_size
            
        if noextname not in config.queue_novice:
            msg = f"{noextname} split no voice videoerror:{config.queue_novice=}"
            set_process(msg)
            return False
        if config.queue_novice[noextname] == 'error':
            msg = f"{noextname} split no voice videoerror"
            set_process(msg)
            return False

        if config.queue_novice[noextname] == 'ing':
            size= f'{round(last_size/1024/1024, 2)}MB' if last_size>0 else ""
            set_process(f"{noextname} split video and audio {size}")
            time.sleep(3)
            t += 3
            continue
        return True


# 从视频中切出一段时间的视频片段
def cut_from_video(*, ss="", to="", source="", pts="", out=""):
    cmd = [
        "-y",
        "-ss",
        ss.replace(",", '.'),
        "-i",
        f'{source}',
        "-vf",
        f'setpts={pts}*PTS',
        "-c:v",
        "libx264",
        "-crf",
        "0",
        f'{out}'
    ]
    if to != '':
        cmd.insert(3, "-to")
        cmd.insert(4, to.replace(',', '.'))  # 如果开始结束时间相同，则强制持续时间1s)
    runffmpeg(cmd)

# 写入日志队列
def set_process(text, type="logs"):
    try:
        if text:
            log_msg = text.replace('<br>', "").replace('<strong>','').replace('</strong>','').strip()
            if log_msg.startswith("[error"):
                logger.error(log_msg)
            else:
                logger.info(log_msg)
        # if type == 'logs':
        #     text = text.
        queue_logs.put_nowait({"text": text, "type": type})
    except Exception as e:
        pass


def is_vlc():
    try:
        if find_lib() is None:
            config.is_vlc = False
        else:
            config.is_vlc = True
    except:
        config.is_vlc = False


# 获取目录下的所有文件和子目录
def delete_files(directory, ext):
    try:
        files_and_dirs = os.listdir(directory)

        # 遍历文件和子目录
        for item in files_and_dirs:
            item_path = os.path.join(directory, item)
            # 如果是文件，且是 mp3 文件，删除之
            if os.path.isfile(item_path) and item.lower().endswith(ext):
                os.remove(item_path)
                print(f"Deleted: {item_path}")

            # 如果是子目录，递归调用删除函数
            elif os.path.isdir(item_path):
                delete_files(item_path)
    except:
        pass

# 将 config.params['line_roles'] 返回按行数：角色名的键值对
def get_line_role(params):
    if "line_roles" not in config.params:
        return None
    result={}
    for role,nums in config.params['line_roles'].items():
        narr=re.split(r'\,|，',nums)
        for it in narr:
            result[f'{it}']=role
    return result
