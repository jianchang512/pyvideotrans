# -*- coding: utf-8 -*-
import copy
from videotrans.configure.config import rootdir, queuebox_logs
import asyncio
import re
import shutil
import subprocess
import sys
import threading
import os
from faster_whisper import WhisperModel
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from datetime import timedelta
import json
import edge_tts
from videotrans.configure import config
from videotrans.configure.config import logger, transobj, queue_logs
import time
# 获取代理，如果已设置os.environ代理，则返回该代理值,否则获取系统代理
from videotrans.tts import get_voice_openaitts, get_voice_edgetts, get_voice_elevenlabs
import torch
from elevenlabs import  voices

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


def pygameaudio(filepath):
    from videotrans.util.playmp3 import AudioPlayer
    player = AudioPlayer(filepath)
    player.start()


# 获取 elenevlabs 的角色列表
def get_elevenlabs_role(force=False):
    jsonfile = os.path.join(config.rootdir, 'elevenlabs.json')
    namelist = []
    if os.path.exists(jsonfile) and os.path.getsize(jsonfile) > 0:
        with open(jsonfile, 'r', encoding='utf-8') as f:
            cache = json.loads(f.read())
            for it in cache.values():
                namelist.append(it['name'])
    if not force and len(namelist) > 0:
        config.params['elevenlabstts_role'] = namelist
        return namelist
    try:
        voiceslist = voices()
        result = {}
        for it in voiceslist:
            n = re.sub(r'[^a-zA-Z0-9_ -]+', '', it.name).strip()
            result[n] = {"name": n, "voice_id": it.voice_id, 'url': it.preview_url}
            namelist.append(n)
        with open(jsonfile, 'w', encoding="utf-8") as f:
            f.write(json.dumps(result))
    except Exception as e:
        print(e)
    config.params['elevenlabstts_role'] = namelist
    return namelist


def transcribe_audio(audio_path, model, language):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = WhisperModel(model, device=device, compute_type="int8" if device == 'cpu' else "int8_float16",
                         download_root=rootdir + "/models")
    segments, _ = model.transcribe(audio_path,
                                   beam_size=5,
                                   vad_filter=True,
                                   vad_parameters=dict(min_silence_duration_ms=500),
                                   language="zh" if language in ["zh-cn", "zh-tw"] else language)
    result = ""
    idx = 0
    for segment in segments:
        idx += 1
        start = int(segment.start * 1000)
        end = int(segment.end * 1000)
        startTime = ms_to_time_string(ms=start)
        endTime = ms_to_time_string(ms=end)
        text = segment.text
        result += f"{idx}\n{startTime} --> {endTime}\n{text.strip()}\n\n"
    return result


def set_proxy(set_val=''):
    if set_val == 'del':
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
            os.environ['https_proxy'] = set_val
        else:
            set_val = f"http://{set_val}"
            os.environ['http_proxy'] = set_val
            os.environ['https_proxy'] = set_val
        return set_val
    # 获取代理
    http_proxy = os.environ.get('http_proxy') or os.environ.get('https_proxy')
    if http_proxy:
        if not http_proxy.startswith("http") and not http_proxy.startswith('sock'):
            http_proxy = f"http://{http_proxy}"
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
                    os.environ['https_proxy'] = proxy_server
                else:
                    proxy_server = "http://" + proxy_server
                    os.environ['http_proxy'] = proxy_server
                    os.environ['https_proxy'] = proxy_server
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
            os.makedirs(f"{config.rootdir}/tmp",exist_ok=True)
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
        logger.error('获取edgeTTS角色失败' + str(e))
        print('获取edgeTTS角色失败' + str(e))
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



# 执行 ffmpeg
def runffmpeg(arg, *, noextname=None, disable_gpu=False, no_decode=False, de_format="cuda", is_box=False):
    arg_copy=copy.deepcopy(arg)
    cmd = ["ffmpeg", "-hide_banner", "-ignore_unknown","-vsync", "vfr"]
    # 启用了CUDA 并且没有禁用GPU
    if config.params['cuda'] and not disable_gpu:
        cmd.extend(["-hwaccel", "cuvid", "-hwaccel_output_format", de_format, "-extra_hw_frames", "2"])
        # 如果第一个输入是视频，需要解码
        if not no_decode:
            cmd.append("-c:v")
            cmd.append("h264_cuvid")
        for i, it in enumerate(arg):
            if i > 0 and arg[i - 1] == '-c:v':
                arg[i] = it.replace('libx264', "h264_nvenc").replace('copy', 'h264_nvenc')
            # else:
            #     arg[i] = arg[i].replace('scale=', 'scale_cuda=')

    cmd = cmd + arg
    if noextname:
        config.queue_novice[noextname] = 'ing'
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
    logger.info(f"runffmpeg: {' '.join(cmd)}")

    while True:
        try:
            # 等待0.1未结束则异常
            outs, errs = p.communicate(timeout=0.5)
            errs = str(errs)
            if errs:
                errs = errs.replace('\\\\', '\\').replace('\r', ' ').replace('\n', ' ')
                errs = errs[errs.find("Error"):]
            # 如果结束从此开始执行
            if p.returncode == 0:
                if noextname:
                    config.queue_novice[noextname] = "end"
                # 成功
                return True
            if noextname:
                config.queue_novice[noextname] = "error"
            # 失败
            raise Exception(f'ffmpeg error:{errs=}')
        except subprocess.TimeoutExpired as e:
            # 如果前台要求停止
            if config.current_status != 'ing' and not is_box:
                try:
                    p.terminate()
                    p.kill()
                except:
                    pass
                return False
        except Exception as e:
            if config.params['cuda'] and not disable_gpu:
                # 切换为cpu
                if not is_box:
                    set_process(transobj['huituicpu'])
                return runffmpeg(arg_copy,noextname=noextname, disable_gpu=True, no_decode=True, de_format="nv12", is_box=is_box)
            raise Exception(str(e))


# run ffprobe 获取视频元信息
def runffprobe(cmd):
    try:
        p = subprocess.Popen(['ffprobe']+cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,encoding="utf-8", text=True,
                             creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
        out, errs = p.communicate()
        if p.returncode == 0:
            return out.strip()
        else:
            pass
            set_process(f'ffprobe error:{str(errs)}')
        return False
    except subprocess.CalledProcessError as e:
        set_process(f'ffprobe error:{str(e)}')
        return False


# 获取视频信息
def get_video_info(mp4_file, *, video_fps=False, video_scale=False, video_time=False, nocache=False):
    # 如果存在缓存并且没有禁用缓存
    if not nocache and mp4_file in config.video_cache:
        result = config.video_cache[mp4_file]
    else:
        out = runffprobe(['-v','quiet','-print_format','json','-show_format','-show_streams',mp4_file])
        if out is False:
            raise Exception(f'ffprobe error:dont get video information')
        out = json.loads(out)
        result = {
            "video_fps": 0,
            "video_codec_name": "h264",
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
                fps, c = it['r_frame_rate'].split('/')
                if not c or c == '0':
                    c = 1
                    fps = int(fps)
                else:
                    fps = round(int(fps) / int(c))
                result['video_fps'] = fps
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
def conver_mp4(source_file, out_mp4):
    return runffmpeg([
        '-y',
        '-i',
        os.path.normpath(source_file),
        '-c:v',
        'libx264',
        "-c:a",
        "aac",
        out_mp4
    ], no_decode=True, de_format="nv12")


# 从原始视频分离出 无声视频 cuda + h264_cuvid
def split_novoice_byraw(source_mp4, novoice_mp4, noextname):
    cmd = [
        "-y",
        "-i",
        f'{source_mp4}',
        "-an",
        "-c:v",
        "copy",
        f'{novoice_mp4}'
    ]
    return runffmpeg(cmd, noextname=noextname)


# 从原始视频中分离出音频 cuda + h264_cuvid
def split_audio_byraw(source_mp4, targe_audio):
    cmd = [
        "-y",
        "-i",
        f'{source_mp4}',
        "-vn",
        "-c:a",
        "copy",
        f'{targe_audio}'
    ]
    return runffmpeg(cmd)


# wav转为 m4a cuda + h264_cuvid
def wav2m4a(wavfile, m4afile):
    cmd = [
        "-y",
        "-i",
        wavfile,
        "-c:a",
        "aac",
        m4afile
    ]
    return runffmpeg(cmd)


# m4a 转为 wav cuda + h264_cuvid
def m4a2wav(m4afile, wavfile):
    cmd = [
        "-y",
        "-i",
        m4afile,
        "-ac",
        "1",
        wavfile
    ]
    return runffmpeg(cmd)


# 取出最后一帧图片 nv12 + h264_cuvid
def get_lastjpg_fromvideo(file_path, img):
    return runffmpeg(
        ['-y', '-sseof', '-3', '-i', f'{file_path}', '-q:v', '1', '-qmin:v', '1', '-qmax:v', '1', '-update', 'true',
         f'{img}'], de_format="nv12")


# 根据图片创建一定时长的视频 nv12 +  not h264_cuvid
def create_video_byimg(*, img=None, fps=30, scale=None, totime=None, out=None):
    return runffmpeg([
        '-loop', '1', '-i', f'{img}', '-vf', f'fps={fps},scale={scale[0]}:{scale[1]}', '-c:v', "libx264",
        '-crf', '13', '-to', f'{totime}', '-y', out], disable_gpu=True,de_format="nv12", no_decode=True)


# 创建 多个视频的连接文件
def create_concat_txt(filelist, filename):
    txt = []
    for it in filelist:
        txt.append(f"file '{it}'")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(txt))
    return filename


# 多个视频片段连接 cuda + h264_cuvid
def concat_multi_mp4(*, filelist=[], out=None):
    # 创建txt文件
    txt = config.TEMP_DIR + f"/{time.time()}.txt"
    create_concat_txt(filelist, txt)
    return runffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', txt, '-c:v', "copy", '-crf', '13', '-an',
                      out])


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


# 文字合成
def text_to_speech(*, text="", role="", rate='+0%', filename=None, tts_type=None, play=False):
    try:
        if rate != '+0%':
            set_process(f'text to speech speed {rate}')
        if tts_type == "edgeTTS":
            if not get_voice_edgetts(text=text, role=role, rate=rate, filename=filename):
                raise Exception(f"edgeTTS error")
        elif tts_type == "openaiTTS":
            if not get_voice_openaitts(text, role, rate, filename):
                raise Exception(f"openaiTTS error")
        elif tts_type == 'elevenlabsTTS':
            if not get_voice_elevenlabs(text, role, rate, filename):
                raise Exception(f"elevenlabsTTS error")
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            if play:
                threading.Thread(target=pygameaudio, args=(filename,)).start()
            return True
        return False
    except Exception as e:
        raise Exception(f"text to speech:{filename=},{tts_type=}," + str(e))


def show_popup(title, text):
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
    msg.setText(text)
    msg.addButton(transobj['queding'], QMessageBox.AcceptRole)
    msg.addButton("Cancel", QMessageBox.RejectRole)
    msg.setIcon(QMessageBox.Information)
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
        if os.path.getsize(srtfile)==0:
            raise Exception(transobj['zimuwenjianbuzhengque'])
        with open(srtfile, 'r', encoding="utf-8") as f:
            txt = f.read().strip().split("\n")
    else:
        txt = srtfile.strip().split("\n")
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
        try:
            t = t.replace('\ufeff', '')
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
        except Exception as e:
            raise Exception(f'{i=},{t=},{str(e)}')
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
    if noextname not in config.queue_novice and os.path.exists(novoice_mp4) and os.path.getsize(novoice_mp4) > 0:
        return True
    if noextname in config.queue_novice and config.queue_novice[noextname] == 'end':
        return True
    last_size = 0
    while True:
        if config.current_status != 'ing':
            raise Exception("Had stop")
        if os.path.exists(novoice_mp4):
            current_size = os.path.getsize(novoice_mp4)
            if last_size > 0 and current_size == last_size and t > 300:
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
            set_process(f"{noextname} split video and audio {size}")
            time.sleep(3)
            t += 3
            continue
        return True


# 从视频中切出一段时间的视频片段 cuda + h264_cuvid
def cut_from_video(*, ss="", to="", source="", pts="", out=""):
    cmd1 = [
        "-y",
        "-ss",
        ss.replace(",", '.')]
    if to != '':
        cmd1.append("-to")
        cmd1.append(to.replace(',', '.'))  # 如果开始结束时间相同，则强制持续时间1s)
    cmd1.append('-i')
    cmd1.append(source)

    if pts:
        cmd1.append("-vf")
        cmd1.append(f'setpts={pts}*PTS')
    cmd = cmd1 + ["-c:v",
                  "libx264",
                  "-crf",
                  "13",
                  f'{out}'
                  ]
    return runffmpeg(cmd)


# 写入日志队列
def set_process_box(text, type='logs'):
    set_process(text, type, "box")


def set_process(text, type="logs", qname='sp'):
    try:
        if text:
            log_msg = text.strip()
            if log_msg.startswith("[error"):
                logger.error(log_msg)
            else:
                logger.info(log_msg)
        if config.exec_mode=='cli':
            print(f'[{type}] {text}')
            return
        if qname == 'sp':
            queue_logs.put_nowait({"text": text, "type": type,"btnkey":config.btnkey})
        else:
            queuebox_logs.put_nowait({"text": text, "type": type})
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
                print(f"Deleted: {item_path}")

            # 如果是子目录，递归调用删除函数
            elif os.path.isdir(item_path):
                delete_files(item_path)
    except:
        pass

