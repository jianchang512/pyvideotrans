# -*- coding: utf-8 -*-
import copy
import hashlib
import platform
import random

import re
import shutil
import subprocess
import sys
import os
from datetime import timedelta
import json
from pathlib import Path

import requests


from videotrans.configure import config
import time


# 获取代理，如果已设置os.environ代理，则返回该代理值,否则获取系统代理


# 根据 gptsovits config.params['gptsovits_role'] 返回以参考音频为key的dict

def get_gptsovits_role():
    if not config.params['gptsovits_role'].strip():
        return None
    rolelist = {}
    for it in config.params['gptsovits_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 3:
            continue
        rolelist[tmp[0]] = {"refer_wav_path": tmp[0], "prompt_text": tmp[1], "prompt_language": tmp[2]}
    return rolelist


def pygameaudio(filepath):
    from videotrans.util.playmp3 import AudioPlayer
    player = AudioPlayer(filepath)
    player.start()


# 获取 elenevlabs 的角色列表
def get_elevenlabs_role(force=False):
    jsonfile = os.path.join(config.rootdir, 'elevenlabs.json')
    namelist = []
    if vail_file(jsonfile):
        with open(jsonfile, 'r', encoding='utf-8') as f:
            cache = json.loads(f.read())
            for it in cache.values():
                namelist.append(it['name'])
    if not force and len(namelist) > 0:
        config.params['elevenlabstts_role'] = namelist
        return namelist
    try:
        from elevenlabs import voices, set_api_key
        if config.params["elevenlabstts_key"]:
            set_api_key(config.params["elevenlabstts_key"])
        voiceslist = voices()
        result = {}
        for it in voiceslist:
            n = re.sub(r'[^a-zA-Z0-9_ -]+', '', it.name).strip()
            result[n] = {"name": n, "voice_id": it.voice_id, 'url': it.preview_url}
            namelist.append(n)
        with open(jsonfile, 'w', encoding="utf-8") as f:
            f.write(json.dumps(result))
        config.params['elevenlabstts_role'] = namelist
        return namelist
    except Exception as e:
        print(e)


def set_proxy(set_val=''):
    if set_val == 'del':
        config.proxy = None
        # 删除代理
        if os.environ.get('http_proxy'):
            os.environ.pop('http_proxy')
        if os.environ.get('https_proxy'):
            os.environ.pop('https_proxy')
        return None
    if set_val:
        # 设置代理
        if not set_val.startswith("http") and not set_val.startswith('sock'):
            set_val = f"http://{set_val}"
        config.proxy = set_val
        os.environ['http_proxy']=set_val
        os.environ['https_proxy']=set_val
        os.environ['all_proxy']=set_val
        return set_val

    # 获取代理
    http_proxy = config.proxy or os.environ.get('http_proxy') or os.environ.get('https_proxy')
    if http_proxy:
        if not http_proxy.startswith("http") and not http_proxy.startswith('sock'):
            http_proxy = f"http://{http_proxy}"
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
            if proxy_server:
                # 是否需要设置代理
                if not proxy_server.startswith("http") and not proxy_server.startswith('sock'):
                    proxy_server = "http://" + proxy_server
                try:
                    requests.head(proxy_server, proxies={"http": "", "https": ""})
                except Exception:
                    return None
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
            os.makedirs(f"{config.rootdir}/tmp", exist_ok=True)
    except:
        pass


#  get role by edge tts
def get_edge_rolelist():
    voice_list = {}
    if vail_file(config.rootdir + "/voice_list.json"):
        try:
            voice_list = json.load(open(config.rootdir + "/voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                config.edgeTTS_rolelist = voice_list
                return voice_list
        except:
            pass
    try:
        import edge_tts
        import asyncio
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        else:
            asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        v = asyncio.run(edge_tts.list_voices())
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
    except Exception as e:
        config.logger.error('获取edgeTTS角色失败' + str(e))
        print('获取edgeTTS角色失败' + str(e))


def get_azure_rolelist():
    voice_list = {}
    if vail_file(config.rootdir + "/azure_voice_list.json"):
        try:
            voice_list = json.load(open(config.rootdir + "/azure_voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                config.AzureTTS_rolelist = voice_list
                return voice_list
        except:
            pass
    return voice_list


# 执行 ffmpeg
def runffmpeg(arg, *, noextname=None,
              is_box=False,
              fps=None):
    config.logger.info(f'runffmpeg-arg={arg}')
    arg_copy = copy.deepcopy(arg)

    if fps:
        cmd = ["ffmpeg", "-hide_banner", "-ignore_unknown", "-vsync", '1', '-r', f'{fps}']
    else:
        cmd = ["ffmpeg", "-hide_banner", "-ignore_unknown", "-vsync", f"{config.settings['vsync']}"]
    # 启用了CUDA 并且没有禁用GPU
    # 默认视频编码 libx264 / libx265
    default_codec=f"libx{config.settings['video_codec']}"

    for i, it in enumerate(arg):
        if arg[i] == '-i' and i < len(arg) - 1:
            arg[i + 1] = os.path.normpath(arg[i + 1]).replace('\\','/')
            if not vail_file(arg[i + 1]):
                raise Exception(f'..{arg[i + 1]} {config.transobj["vlctips2"]}')

    if default_codec in arg and config.video_codec != default_codec:
        if not config.video_codec:
            config.video_codec=get_video_codec()
        for i, it in enumerate(arg):
            if i > 0 and arg[i - 1] == '-c:v':
                arg[i] = config.video_codec

    cmd = cmd + arg
    config.logger.info(f'runffmpeg-tihuan:{cmd=}')
    if noextname:
        config.queue_novice[noextname] = 'ing'
    try:
        subprocess.run(cmd,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       encoding="utf-8",
                       check=True,
                       text=True,
                       creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
        if noextname:
            config.queue_novice[noextname] = "end"
        return True
    except subprocess.CalledProcessError as e:       
        retry=False
        config.logger.error(f'出错了:{cmd=}')
        config.logger.error(f'before:{retry=},{arg_copy=}')
        # 处理视频时如果出错，尝试回退
        if cmd[-1].endswith('.mp4'):
            #存在视频的copy操作时，尝试回退使用重新编码
            if "copy" in cmd:
                for i, it in enumerate(arg_copy):
                    if i > 0 and arg_copy[i - 1] == '-c:v' and it=='copy':
                        arg_copy[i] = config.video_codec if config.video_codec is not None else default_codec
                        retry=True
            #如果不是copy并且也不是 libx264，则替换为libx264编码
            if not retry and config.video_codec!= default_codec:
                config.video_codec=default_codec
                # 切换为cpu
                if not is_box:
                    set_process(config.transobj['huituicpu'])
                config.logger.error(f'cuda上执行出错，退回到CPU执行')
                for i, it in enumerate(arg_copy):
                    if i > 0 and arg_copy[i - 1] == '-c:v' and it!= default_codec:
                        arg_copy[i] = default_codec
                        retry=True
            config.logger.error(f'after:{retry=},{arg_copy=}')
            if retry:
                return runffmpeg(arg_copy, noextname=noextname, is_box=is_box)
        if noextname:
            config.queue_novice[noextname] = "error"
        config.logger.error(f'cmd执行出错抛出异常:{cmd=},{str(e.stderr)}')
        raise Exception(str(e.stderr))
    except Exception as e:
        config.logger.error(f'执行出错 Exception:{cmd=},{str(e)}')
        raise Exception(str(e))


# run ffprobe 获取视频元信息
def runffprobe(cmd):
    # cmd[-1] = os.path.normpath(cmd[-1])
    try:
        p = subprocess.run( cmd if isinstance(cmd,str) else ['ffprobe'] + cmd,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           encoding="utf-8",
                           text=True,
                           check=True,
                           creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
        if p.stdout:
            return p.stdout.strip()
        raise Exception(str(p.stderr))
    except subprocess.CalledProcessError as e:
        msg = f'ffprobe error,:{str(e.stdout)},{str(e.stderr)}'
        msg = msg.replace('\n', ' ')
        raise Exception(msg)
    except Exception as e:
        raise Exception(f'ffprobe except,{cmd=}:{str(e)}')


# 获取视频信息
def get_video_info(mp4_file, *, video_fps=False, video_scale=False, video_time=False, nocache=False):
    # 如果存在缓存并且没有禁用缓存
    if not nocache and mp4_file in config.video_cache:
        result = config.video_cache[mp4_file]
    else:
        out = runffprobe(['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mp4_file])
        if out is False:
            raise Exception(f'ffprobe error:dont get video information')
        out = json.loads(out)
        result = {
            "video_fps": 30,
            "video_codec_name": "",
            "audio_codec_name": "aac",
            "width": 0,
            "height": 0,
            "time": 0,
            "streams_len": 0,
            "streams_audio": 0
        }
        if "streams" not in out or len(out["streams"]) < 1:
            raise Exception(f'ffprobe error:streams is 0')

        if "format" in out and out['format']['duration']:
            result['time'] = int(float(out['format']['duration']) * 1000)
        for it in out['streams']:
            result['streams_len'] += 1
            if it['codec_type'] == 'video':
                result['video_codec_name'] = it['codec_name']
                result['width'] = int(it['width'])
                result['height'] = int(it['height'])

                fps_split = it['r_frame_rate'].split('/')
                if len(fps_split) != 2 or fps_split[1] == '0':
                    fps1 = 30
                else:
                    fps1 = round(int(fps_split[0]) / int(fps_split[1]), 2)

                fps_split = it['avg_frame_rate'].split('/')
                if len(fps_split) != 2 or fps_split[1] == '0':
                    fps = fps1
                else:
                    fps = round(int(fps_split[0]) / int(fps_split[1]), 2)

                result['video_fps'] = fps if fps >= 16 and fps <= 60 else 30
            elif it['codec_type'] == 'audio':
                result['streams_audio'] += 1
                result['audio_codec_name'] = it['codec_name']
        if not nocache:
            config.video_cache[mp4_file] = result

    if video_time:
        return result['time']
    if video_fps:
        return ['video_fps']
    if video_scale:
        return result['width'], result['height']
    return result


# 获取某个视频的时长 s
def get_video_duration(file_path):
    return get_video_info(file_path, video_time=True, nocache=True)


# 获取某个视频的fps
def get_video_fps(file_path):
    return get_video_info(file_path, video_fps=True)


# 获取宽高分辨率
def get_video_resolution(file_path):
    return get_video_info(file_path, video_scale=True)


# 视频转为 mp4格式 nv12 + not h264_cuvid
def conver_mp4(source_file, out_mp4, *, is_box=False):
    video_codec=config.settings['video_codec']
    return runffmpeg([
        '-y',
        '-i',
        os.path.normpath(source_file),
        '-c:v',
        f'libx{video_codec}',
        "-c:a",
        "aac",
        '-crf', f'{config.settings["crf"]}',
        '-preset', 'slow',
        out_mp4
    ], is_box=is_box)


# 从原始视频分离出 无声视频 cuda + h264_cuvid
def split_novoice_byraw(source_mp4, novoice_mp4, noextname, lib="copy"):
    cmd = [
        "-y",
        "-i",
        f'{source_mp4}',
        "-an",
        "-c:v",
        lib,
        "-crf",
        "0",
        f'{novoice_mp4}'
    ]
    return runffmpeg(cmd, noextname=noextname)


# 从原始视频中分离出音频 cuda + h264_cuvid
def split_audio_byraw(source_mp4, targe_audio, is_separate=False,btnkey=None):
    cmd = [
        "-y",
        "-i",
        source_mp4,
        "-vn",
        "-c:a",
        "aac",
        targe_audio
    ]
    rs = runffmpeg(cmd)
    if not is_separate:
        return rs
    # 继续人声分离
    tmpdir = config.TEMP_DIR + f"/{time.time()}"
    os.makedirs(tmpdir, exist_ok=True)
    tmpfile = tmpdir + "/raw.wav"
    runffmpeg([
        "-y",
        "-i",
        source_mp4,
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-c:a",
        "pcm_s16le",
        tmpfile
    ])
    from videotrans.separate import st
    try:
        path = os.path.dirname(targe_audio)
        vocal_file = os.path.join(path, 'vocal.wav')
        if not vail_file(vocal_file):
            set_process(config.transobj['Separating vocals and background music, which may take a longer time'])
            try:
                st.start(audio=tmpfile, path=path,btnkey=btnkey)
            except Exception as e:
                msg = f"separate vocal and background music:{str(e)}"
                set_process(msg)
                raise Exception(msg)
        if not vail_file(vocal_file):
            return False
    except Exception as e:
        msg = f"separate vocal and background music:{str(e)}"
        set_process(msg)
        raise Exception(msg)


def conver_to_8k(audio, target_audio):
    return runffmpeg([
        "-y",
        "-i",
        audio,
        "-ac",
        "1",
        "-ar",
        "8000",
        target_audio,
    ])


#  背景音乐是wav,配音人声是m4a，都在目标文件夹下，合并后最后文件仍为 人声文件，时长需要等于人声
def backandvocal(backwav, peiyinm4a):
    tmpwav = os.path.join(os.environ["TEMP"] or os.environ['temp'], f'{time.time()}-1.m4a')
    tmpm4a = os.path.join(os.environ["TEMP"] or os.environ['temp'], f'{time.time()}.m4a')
    # 背景转为m4a文件,音量降低为0.8
    wav2m4a(backwav, tmpm4a, ["-filter:a", f"volume={config.settings['backaudio_volume']}"])
    runffmpeg(['-y', '-i', peiyinm4a, '-i', tmpm4a, '-filter_complex',
               "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', '-c:a', 'aac', tmpwav])
    shutil.copy2(tmpwav, peiyinm4a)
    # 转为 m4a


# wav转为 m4a cuda + h264_cuvid
def wav2m4a(wavfile, m4afile, extra=None):
    cmd = [
        "-y",
        "-i",
        wavfile,
        "-c:a",
        "aac",
        m4afile
    ]
    if extra:
        cmd = cmd[:3] + extra + cmd[3:]
    return runffmpeg(cmd)


# wav转为 mp3 cuda + h264_cuvid
def wav2mp3(wavfile, mp3file, extra=None):
    cmd = [
        "-y",
        "-i",
        wavfile,
        mp3file
    ]
    if extra:
        cmd = cmd[:3] + extra + cmd[3:]
    return runffmpeg(cmd)


# m4a 转为 wav cuda + h264_cuvid
def m4a2wav(m4afile, wavfile):
    cmd = [
        "-y",
        "-i",
        m4afile,
        "-ac",
        "1",
        "-ar",
        "8000",
        "-b:a",
        "128k",
        "-c:a",
        "pcm_s16le",
        wavfile
    ]
    return runffmpeg(cmd)


# 创建 多个视频的连接文件
def create_concat_txt(filelist, filename):
    txt = []
    for it in filelist:
        txt.append(f"file '{it}'")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(txt))
    return filename


# 多个视频片段连接 cuda + h264_cuvid
def concat_multi_mp4(*, filelist=[], out=None, maxsec=None, fps=None):
    # 创建txt文件
    txt = config.TEMP_DIR + f"/{time.time()}.txt"
    video_codec=config.settings['video_codec']
    create_concat_txt(filelist, txt)
    if maxsec:
        return runffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', txt, '-c:v', f"libx{video_codec}", '-t', f"{maxsec}", '-crf',
                          f'{config.settings["crf"]}', '-preset', 'slow', '-an', out], fps=fps)
    return runffmpeg(
        ['-y', '-f', 'concat', '-safe', '0', '-i', txt, '-c:v', f"libx{video_codec}", '-an', '-crf', f'{config.settings["crf"]}',
         '-preset', 'slow', out], fps=fps)


# 多个音频片段连接 
def concat_multi_audio(*, filelist=[], out=None):
    # 创建txt文件
    txt = config.TEMP_DIR + f"/{time.time()}.txt"
    create_concat_txt(filelist, txt)
    return runffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', txt, '-c:a', 'aac', out])


# mp3 加速播放 cuda + h264_cuvid
def speed_up_mp3(*, filename=None, speed=1, out=None):
    return runffmpeg([
        "-y",
        "-i",
        filename,
        "-af",
        f'atempo={speed}',
        out
    ])


def precise_speed_up_audio(*, file_path=None, out=None, target_duration_ms=None, max_rate=100):
    from pydub import AudioSegment
    audio = AudioSegment.from_file(file_path)

    # 首先确保原时长和目标时长单位一致（毫秒）
    current_duration_ms = len(audio)
    # 计算音频变速比例
    # current_duration_ms = len(audio)
    # speedup_ratio = current_duration_ms / target_duration_ms
    # 计算速度变化率
    speedup_ratio = current_duration_ms / target_duration_ms
    if target_duration_ms <= 0 or speedup_ratio <= 1:
        return True
    rate = min(max_rate, speedup_ratio)
    # 变速处理
    try:
        fast_audio = audio.speedup(playback_speed=rate)
        # 如果处理后的音频时长稍长于目标时长，进行剪裁
        if len(fast_audio) > target_duration_ms:
            fast_audio = fast_audio[:target_duration_ms]
    except Exception:
        fast_audio = audio[:target_duration_ms]

    if out:
        fast_audio.export(out, format=out.split('.')[-1])
        return True
    fast_audio.export(file_path, format=file_path.split('.')[-1])
    # 返回速度调整后的音频
    return True


def show_popup(title, text,parent=None):
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox

    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
    msg.setText(text)
    msg.addButton(QMessageBox.Yes)
    msg.addButton(QMessageBox.Cancel)
    msg.setWindowModality(Qt.ApplicationModal)  # 设置为应用模态
    msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)  # 置于顶层


    # msg.addButton(a2)
    msg.setIcon(QMessageBox.Information)
    x = msg.exec()  # 显示消息框
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

    time_string = f"{hours}:{minutes}:{seconds},{milliseconds}"
    return format_time(time_string, ',')


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


# 将字符串或者字幕文件内容，格式化为有效字幕数组对象
# 格式化为有效的srt格式
# content是每行内容，按\n分割的，
def format_srt(content):
    # 去掉空行
    content = [it for it in content if it.strip()]
    if len(content) < 1:
        return []
    result = []
    maxindex = len(content) - 1
    # 时间格式
    timepat = r'^\s*?\d+:\d+:\d+([\,\.]\d*?)?\s*?-->\s*?\d+:\d+:\d+([\,\.]\d*?)?\s*?$'
    textpat = r'^[,./?`!@#$%^&*()_+=\\|\[\]{}~\s \n-]*$'
    for i, it in enumerate(content):
        # 当前空行跳过
        if not it.strip():
            continue
        it = it.strip()
        is_time = re.match(timepat, it)
        if is_time:
            # 当前行是时间格式，则添加
            result.append({"time": it, "text": []})
        elif i == 0:
            # 当前是第一行，并且不是时间格式，跳过
            continue
        elif re.match(r'^\s*?\d+\s*?$', it) and i < maxindex and re.match(timepat, content[i + 1]):
            # 当前不是时间格式，不是第一行，并且都是数字，并且下一行是时间格式，则当前是行号，跳过
            continue
        elif len(result) > 0 and not re.match(textpat, it):
            # 当前不是时间格式，不是第一行，（不是行号），并且result中存在数据，则是内容，可加入最后一个数据

            result[-1]['text'].append(it.capitalize())

    # 再次遍历，去掉text为空的
    result = [it for it in result if len(it['text']) > 0]

    if len(result) > 0:
        for i, it in enumerate(result):
            result[i]['line'] = i + 1
            result[i]['text'] = "\n".join([tx.capitalize() for tx in it['text']])
            s, e = (it['time'].replace('.', ',')).split('-->')
            s = format_time(s, ',')
            e = format_time(e, ',')
            result[i]['time'] = f'{s} --> {e}'
    return result


def get_subtitle_from_srt(srtfile, *, is_file=True):
    if is_file:
        if os.path.getsize(srtfile) == 0:
            raise Exception(config.transobj['zimuwenjianbuzhengque'])
        try:
            with open(srtfile, 'r', encoding='utf-8') as f:
                content = f.read().strip().splitlines()
        except:
            try:
                with open(srtfile, 'r', encoding='gbk') as f:
                    content = f.read().strip().splitlines()
            except Exception as e:
                raise Exception(f'get srtfile error:{str(e)}')
    else:
        content = srtfile.strip().splitlines()
    if len(content) < 1:
        raise Exception("srt content is 0")

    result = format_srt(content)
    if len(result) < 1:
        return []

    new_result = []
    line = 1
    for it in result:
        if "text" in it and len(it['text'].strip()) > 0:
            it['line'] = line
            startraw, endraw = it['time'].strip().split("-->")

            startraw = format_time(startraw.strip().replace(',', '.').replace('，', '.').replace('：', ':'), '.')
            start = startraw.split(":")

            endraw = format_time(endraw.strip().replace(',', '.').replace('，', '.').replace('：', ':'), '.')
            end = endraw.split(":")

            start_time = int(int(start[0]) * 3600000 + int(start[1]) * 60000 + float(start[2]) * 1000)
            end_time = int(int(end[0]) * 3600000 + int(end[1]) * 60000 + float(end[2]) * 1000)
            it['startraw'] = startraw
            it['endraw'] = endraw
            it['start_time'] = start_time
            it['end_time'] = end_time
            new_result.append(it)
            line += 1
    if len(new_result)<1:
        raise Exception(config.transobj['zimuwenjianbuzhengque'])

    return new_result


# 将 时:分:秒,|.毫秒格式为  aa:bb:cc,|.ddd形式
def format_time(s_time="", separate=','):
    if not s_time.strip():
        return f'00:00:00{separate}000'
    s_time = s_time.strip()
    hou, min, sec = "00", "00", f"00{separate}000"
    tmp = s_time.split(':')
    if len(tmp) >= 3:
        hou = tmp[-3].strip()
        min = tmp[-2].strip()
        sec = tmp[-1].strip()
    elif len(tmp) == 2:
        min = tmp[0].strip()
        sec = tmp[1].strip()
    elif len(tmp) == 1:
        sec = tmp[0].strip()

    if re.search(r',|\.', str(sec)):
        sec, ms = re.split(r',|\.', str(sec))
        sec = sec.strip()
        ms = ms.strip()
    else:
        ms = '000'
    hou = hou if hou != "" else "00"
    if len(hou) < 2:
        hou = f'0{hou}'
    hou = hou[-2:]

    min = min if min != "" else "00"
    if len(min) < 2:
        min = f'0{min}'
    min = min[-2:]

    sec = sec if sec != "" else "00"
    if len(sec) < 2:
        sec = f'0{sec}'
    sec = sec[-2:]

    ms_len = len(ms)
    if ms_len < 3:
        for i in range(3 - ms_len):
            ms = f'0{ms}'
    ms = ms[-3:]
    return f"{hou}:{min}:{sec}{separate}{ms}"


# 判断 novoice.mp4是否创建好
def is_novoice_mp4(novoice_mp4, noextname):
    # 预先创建好的
    # 判断novoice_mp4是否完成
    t = 0
    if noextname not in config.queue_novice and vail_file(novoice_mp4):
        return True
    if noextname in config.queue_novice and config.queue_novice[noextname] == 'end':
        return True
    last_size = 0
    while True:
        if config.current_status != 'ing':
            raise Exception("stop")
        if vail_file(novoice_mp4):
            current_size = os.path.getsize(novoice_mp4)
            if last_size > 0 and current_size == last_size and t > 600:
                return True
            last_size = current_size

        if noextname not in config.queue_novice:
            msg = f"{noextname} split no voice videoerror:{config.queue_novice=}"
            raise Exception(msg)
        if config.queue_novice[noextname] == 'error':
            msg = f"{noextname} split no voice videoerror"
            raise Exception(msg)

        if config.queue_novice[noextname] == 'ing':
            size = f'{round(last_size / 1024 / 1024, 2)}MB' if last_size > 0 else ""
            set_process(f"{noextname} {'分离音频和画面' if config.defaulelang == 'zh' else 'spilt audio and video'} {size}")
            time.sleep(3)
            t += 3
            continue
        return True

def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)




# 从视频中切出一段时间的视频片段 cuda + h264_cuvid
def cut_from_video(*, ss="", to="", source="", pts="", out="", fps=None):
    video_codec=config.settings['video_codec']
    cmd1 = [
        "-y",
        "-ss",
        format_time(ss, '.')]
    if to != '':
        cmd1.append("-to")
        cmd1.append(format_time(to, '.'))  # 如果开始结束时间相同，则强制持续时间1s)
    cmd1.append('-i')
    cmd1.append(source)

    if pts:
        cmd1.append("-vf")
        cmd1.append(f'setpts={pts}*PTS')
    cmd = cmd1 + ["-c:v",
                  f"libx{video_codec}",
                  '-an',
                  '-crf', f'{config.settings["crf"]}',
                  '-preset', 'slow',
                  f'{out}'
                  ]
    return runffmpeg(cmd, fps=fps)


# 从音频中截取一个片段
def cut_from_audio(*, ss, to, audio_file, out_file):
    cmd = [
        "-y",
        "-i",
        audio_file,
        "-ss",
        format_time(ss, '.'),
        "-to",
        format_time(to, '.'),
        "-ar",
        "8000",
        out_file
    ]
    return runffmpeg(cmd)


# 获取clone-voice的角色列表
def get_clone_role(set_p=False):
    if not config.params['clone_api']:
        if set_p:
            raise Exception(config.transobj['bixutianxiecloneapi'])
        return False
    try:
        url = config.params['clone_api'].strip().rstrip('/') + "/init"
        res = requests.get('http://' + url.replace('http://', ''), proxies={"http": "", "https": ""})
        if res.status_code == 200:
            config.clone_voicelist = ["clone"] + res.json()
            set_process('', 'set_clone_role')
            return True
        raise Exception(
            f"code={res.status_code},{config.transobj['You must deploy and start the clone-voice service']}")
    except Exception as e:
        if set_p:
            raise Exception(f'clone-voice:{str(e)}')
    return False


# 工具箱写入日志队列
def set_process_box(text, type='logs', *, func_name=""):
    set_process(text, type, qname="box", func_name=func_name)


# 综合写入日志，默认sp界面
def set_process(text, type="logs", *, qname='sp', func_name="", btnkey="",nologs=False):
    try:
        if text:
            if not nologs:
                if type == 'error':
                    config.logger.error(text)
                else:
                    config.logger.info(text)

            # 移除html
            if type == 'error':
                text = re.sub(r'</?!?[a-zA-Z]+[^>]*?>','',text,re.I|re.M|re.S)
                text = text.replace('\\n',' ').strip()

        if qname == 'sp':
            config.queue_logs.put_nowait({"text": text, "type": type, "btnkey": btnkey})
        elif qname == 'box':
            config.queuebox_logs.put_nowait({"text": text, "type": type, "func_name": func_name})
        else:
            print(f'[{type}]: {text}')
    except Exception as e:
        pass


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

            # 如果是子目录，递归调用删除函数
            elif os.path.isdir(item_path):
                delete_files(item_path)
    except:
        pass


def send_notification(title, message):
    from plyer import notification
    try:
        notification.notify(
            title=title[:60],
            message=message[:120],
            ticker="pyVideoTrans",
            app_name="pyVideoTrans",  # config.uilanglist['SP-video Translate Dubbing'],
            app_icon=os.path.join(config.rootdir, 'videotrans/styles/icon.ico'),
            timeout=10  # Display duration in seconds
        )
    except:
        pass


# 判断是否需要重命名，如果需要则重命名并转移
def rename_move(file, *, is_dir=False):
    patter = r'[ \s`"\'!@#$%^&*()=+,?\|{}\[\]]+'
    if re.search(patter, file):
        if is_dir:
            os.makedirs(config.homedir + "/target_dir", exist_ok=True)
            return True, config.homedir + "/target_dir", False
        dirname = os.path.dirname(file)
        basename = os.path.basename(file)
        # 目录不规则，迁移目录
        if re.search(patter, dirname):
            basename = re.sub(patter, '', basename, 0, re.I)
            basename = basename.replace(':', '')
            os.makedirs(config.homedir + "/rename", exist_ok=True)
            newfile = config.homedir + f"/rename/{basename}"
            shutil.copy2(file, newfile)
        else:
            # 目录规则仅名称不规则，只修改名称
            basename = re.sub(patter, '', basename, 0, re.I)
            basename = basename.replace(':', '')
            newfile = dirname + "/" + basename
            shutil.copy2(file, newfile)

        return True, newfile, basename
    return False, False, False


# 获取音频时长
def get_audio_time(audio_file):
    # 如果存在缓存并且没有禁用缓存
    out = runffprobe(['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', audio_file])
    if out is False:
        raise Exception(f'ffprobe error:dont get video information')
    out = json.loads(out)
    return float(out['format']['duration'])


def kill_ffmpeg_processes():
    import platform
    import signal
    import getpass
    try:
        system_platform = platform.system()
        current_user = getpass.getuser()

        if system_platform == "Windows":
            subprocess.call(f"taskkill /F /FI \"USERNAME eq {current_user}\" /IM ffmpeg.exe", shell=True)
        elif system_platform == "Linux" or system_platform == "Darwin":
            process = subprocess.Popen(['ps', '-U', current_user], stdout=subprocess.PIPE)
            out, err = process.communicate()

            for line in out.splitlines():
                if b'ffmpeg' in line:
                    pid = int(line.split(None, 1)[0])
                    os.kill(pid, signal.SIGKILL)
    except:
        pass


# input_file_path 可能是字符串：文件路径，也可能是音频数据
def remove_silence_from_end(input_file_path, silence_threshold=-50.0, chunk_size=10, is_start=True):
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    """
    Removes silence from the end of an audio file.

    :param input_file_path: path to the input mp3 file
    :param silence_threshold: the threshold in dBFS considered as silence
    :param chunk_size: the chunk size to use in silence detection (in milliseconds)
    :return: an AudioSegment without silence at the end
    """
    # Load the audio file
    format = "wav"
    if isinstance(input_file_path, str):
        format = input_file_path.split('.')[-1].lower()
        if format in ['wav', 'mp3','m4a']:
            audio = AudioSegment.from_file(input_file_path, format=format if format in ['wav','mp3'] else 'mp4')
        else:
            # 转为mp3
            try:
                runffmpeg(['-y', '-i', input_file_path, input_file_path + ".mp3"])
                audio = AudioSegment.from_file(input_file_path + ".mp3", format="mp3")
            except Exception:
                return input_file_path

    else:
        audio = input_file_path

    # Detect non-silent chunks
    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=chunk_size,
        silence_thresh=silence_threshold
    )

    # If we have nonsilent chunks, get the start and end of the last nonsilent chunk
    if nonsilent_chunks:
        start_index, end_index = nonsilent_chunks[-1]
    else:
        # If the whole audio is silent, just return it as is
        return input_file_path

    # Remove the silence from the end by slicing the audio segment
    trimmed_audio = audio[:end_index]
    if is_start and nonsilent_chunks[0] and nonsilent_chunks[0][0] > 0:
        trimmed_audio = audio[nonsilent_chunks[0][0]:end_index]
    if isinstance(input_file_path, str):
        if format in ['wav', 'mp3','m4a']:
            trimmed_audio.export(input_file_path, format=format if format in ['wav','mp3'] else 'mp4')
            return input_file_path
        try:
            trimmed_audio.export(input_file_path + ".mp3", format="mp3")
            runffmpeg(['-y', '-i', input_file_path + ".mp3", input_file_path])
        except Exception:
            pass
        return input_file_path
    return trimmed_audio


# 从 google_url 中获取可用地址
def get_google_url():
    google_url = 'https://translate.google.com'
    if vail_file(config.rootdir+'/google.txt'):
        with open(os.path.join(config.rootdir, 'google.txt'), 'r') as f:
            t = f.read().strip().splitlines()
            urls = [x for x in t if x.strip() and x.startswith('http')]
            if len(urls) > 0:
                n = 0
                while n < 5:
                    google_url = random.choice(urls).rstrip('/')
                    try:
                        res = requests.head(google_url, proxies={"http": "", "https": ""})
                        if res.status_code == 200:
                            return google_url
                    except:
                        msg = (f'测试失败: {google_url}')
                        config.logger.error(msg)
                        continue
                    finally:
                        n += 1
                raise Exception(f'从google.txt中随机获取5次url，均未找到可用的google翻译反代地址，请检查')
    return google_url


def remove_qsettings_data(organization="Jameson", application="VideoTranslate"):
    from PySide6.QtCore import QSettings
    import platform

    # Create a QSettings object with the specified organization and application
    settings = QSettings(organization, application)

    # Clear all settings in QSettings
    settings.clear()
    settings.sync()  # Make sure changes are written to the disk

    # Determine if the platform is Windows
    if platform.system() == "Windows":
        # On Windows, the settings are stored in the registry, so no further action is needed
        return
    try:
        # On MacOS and Linux, settings are usually stored in a config file within the user's home directory
        config_dir = os.path.join(os.path.expanduser("~"), ".config", organization)
        config_file_path = os.path.join(config_dir, f"{application}.ini")

        # Check if the config file exists and remove it
        if os.path.isfile(config_file_path):
            os.remove(config_file_path)
        # If the whole directory for the organization should be removed, you would use shutil.rmtree as follows
        # Warning: This will remove all settings for all applications under this organization
        elif os.path.isdir(config_dir):
            shutil.rmtree(config_dir, ignore_errors=True)
    except Exception:
        pass


# 格式化视频信息
def format_video(name, out=None):
    from pathlib import Path
    raw_pathlib=Path(name)
    raw_basename = raw_pathlib.name
    raw_noextname=raw_pathlib.stem
    ext = raw_pathlib.suffix
    raw_dirname = raw_pathlib.parent.resolve().as_posix()

    output_path=Path(f'{out}/{raw_noextname}' if out else f'{raw_dirname}/_video_out/{raw_noextname}')
    output_path.mkdir(parents=True, exist_ok=True)
    obj = {
        "raw_name": name,
        # 原始视频所在原始目录
        "raw_dirname": raw_dirname,
        # 原始视频原始名字带后缀
        "raw_basename": raw_basename,
        # 原始视频名字不带后缀
        "raw_noextname": raw_noextname,
        # 原始后缀不带 .
        "raw_ext": ext[1:],
        # 处理后 移动后符合规范的目录名
        "dirname": "",
        # 符合规范的基本名带后缀
        "basename": "",
        # 符合规范的不带后缀
        "noextname": "",
        # 扩展名
        "ext": ext[1:],
        # 最终存放目标位置，直接存到这里
        "output": output_path.as_posix(),
        "unid": "",
        "source_mp4": name,
        # 临时存放，当名字符合规范时，和output相同
        "linshi_output": ""
    }
    obj['linshi_output'] = obj['output']
    h = hashlib.md5()
    h.update(obj['raw_name'].encode('utf-8'))
    obj['unid'] = h.hexdigest()

    if re.match(r'^([a-zA-Z]:)?/[a-zA-Z0-9_/.-]+$', name):
        # 符合规则，原始和目标相同
        obj['dirname'] = obj['raw_dirname']
        obj['basename'] = obj['raw_basename']
        obj['noextname'] = obj['raw_noextname']
    else:
        # 不符合，需要移动到 tmp 下
        obj['noextname'] = obj['unid']
        obj['basename'] = f'{obj["noextname"]}.{obj["raw_ext"]}'
        obj['dirname'] = config.TEMP_DIR + f"/{obj['noextname']}"
        obj['dirname'] = config.TEMP_DIR + f"/{obj['noextname']}"
        obj['source_mp4'] = f'{obj["dirname"]}/{obj["basename"]}'
        # 目标存放位置，完成后再复制
        obj['linshi_output'] = config.TEMP_DIR + f'/{obj["noextname"]}/_video_out'
        Path(obj['linshi_output']).mkdir(parents=True, exist_ok=True)
    return obj


def open_dir(self, dirname=None):
    if not dirname:
        return
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    dirname = dirname.strip()
    if not os.path.isdir(dirname):
        dirname = os.path.dirname(dirname)
    if not dirname or not os.path.isdir(dirname):
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(dirname))



def vail_file(file=None):
    if not file:
        return False
    p=Path(file)
    if not p.exists() or not p.is_file():
        return False
    if p.stat().st_size<1:
        return False
    return True


# 获取最终视频应该输出的编码格式
def get_video_codec():
    plat=platform.system()
    # 264 / 265
    video_codec=int(config.settings['video_codec'])
    hhead='h264'
    if video_codec!=264:
        hhead='hevc'
    mp4_test=config.rootdir+"/videotrans/styles/no-remove.mp4"
    if not Path(mp4_test).is_file():
        return f'libx{video_codec}'
    mp4_target=config.TEMP_DIR+"/test.mp4"
    codec=''
    if plat in ['Windows','Linux']:
        import torch    
        if torch.cuda.is_available():
            codec=f'{hhead}_nvenc'
        elif plat=='Windows':
            codec=f'{hhead}_qsv'
        elif plat=='Linux':
            codec=f'{hhead}_vaapi'
    elif plat=='Darwin':
        codec=f'{hhead}_videotoolbox'

    if not codec:
        return f"libx{video_codec}"

    print(f'{codec=}')
    try:
        Path(config.TEMP_DIR).mkdir(exist_ok=True)
        subprocess.run([
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-ignore_unknown",
            "-i",
            mp4_test,
            "-c:v",
            codec,
            mp4_target
        ],
        check=True,
        creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print('error='+str(e))
        if sys.platform=='win32':
            try:
                codec=f"{hhead}_amf"
                subprocess.run([
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-ignore_unknown",
                    "-i",
                    mp4_test,
                    "-c:v",
                    codec,
                    mp4_target
                ],
                    check=True,
                    creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
            except Exception:
                codec=f"libx{video_codec}"
    return codec



# 设置ass字体格式
def set_ass_font(srtfile=None):
    if not os.path.exists(srtfile) or os.path.getsize(srtfile)==0:
        return os.path.basename(srtfile)
    runffmpeg(['-y','-i',srtfile,f'{srtfile}.ass'])
    assfile=f'{srtfile}.ass'
    with open(assfile,'r',encoding='utf-8') as f:
        ass_str=f.readlines()
    
    for i,it in enumerate(ass_str):
        if it.find('Style: ')==0:
            ass_str[i]='Style: Default,{fontname},{fontsize},{fontcolor},&HFFFFFF,{fontbordercolor},&H0,0,0,0,0,100,100,0,0,1,1,0,2,10,10,{subtitle_bottom},1'.format(fontname=config.settings['fontname'],fontsize=config.settings['fontsize'],fontcolor=config.settings['fontcolor'],fontbordercolor=config.settings['fontbordercolor'],subtitle_bottom=config.settings['subtitle_bottom'])
            break
    
    with open(assfile,'w',encoding='utf-8') as f:
        f.write("".join(ass_str))
    return os.path.basename(assfile)