# -*- coding: utf-8 -*-
import copy

import re
import shutil
import subprocess
import sys
import os
from datetime import timedelta
import json
import edge_tts


from videotrans.configure import config
import time
from elevenlabs import voices, set_api_key
# 获取代理，如果已设置os.environ代理，则返回该代理值,否则获取系统代理
from videotrans.separate import st
from plyer import notification

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
        print(config.params["elevenlabstts_key"])
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



# 执行 ffmpeg
def runffmpeg(arg, *, noextname=None,
              disable_gpu=False,  # True=禁止使用GPU解码
              no_decode=config.settings['no_decode'], # False=禁止 h264_cuvid 解码，True=尽量使用硬件解码
              de_format=config.settings['hwaccel_output_format'], # 硬件输出格式，模型cuda兼容性差，可选nv12
              is_box=False):
    arg_copy=copy.deepcopy(arg)
    cmd = ["ffmpeg", "-hide_banner", "-ignore_unknown","-vsync", "vfr"]
    # 启用了CUDA 并且没有禁用GPU
    if config.params['cuda'] and not disable_gpu:
        cmd.extend(["-hwaccel", config.settings['hwaccel'], "-hwaccel_output_format", de_format, "-extra_hw_frames", "2"])
        # 如果没有禁止硬件解码，则添加
        if not no_decode:
            cmd.append("-c:v")
            cmd.append("h264_cuvid")
        for i, it in enumerate(arg):
            if i > 0 and arg[i - 1] == '-c:v':
                arg[i] = it.replace('libx264', "h264_nvenc").replace('copy', 'h264_nvenc')
    cmd = cmd + arg
    if noextname:
        config.queue_novice[noextname] = 'ing'
    print(f'{cmd=}')
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         encoding="utf-8",
                         text=True, 
                         creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
    config.logger.info(f"runffmpeg: {' '.join(cmd)}")

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
            #如果启用cuda时出错，则回退cpu
            if config.params['cuda'] and not disable_gpu:
                # 切换为cpu
                if not is_box:
                    set_process(config.transobj['huituicpu'])
                # disable_gpt=True禁用GPU，no_decode=True禁止h264_cuvid解码，
                return runffmpeg(arg_copy,noextname=noextname, disable_gpu=True, is_box=is_box)
            raise Exception(str(e))


# run ffprobe 获取视频元信息
def runffprobe(cmd):
    try:
        cmd[-1]=os.path.normpath(rf'{cmd[-1]}')
        p = subprocess.Popen(['ffprobe']+cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,encoding="utf-8", text=True,
                             creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
        out, errs = p.communicate()
        if p.returncode == 0:
            return out.strip()
        raise Exception(f'ffprobe error:{str(errs)}')
    except subprocess.CalledProcessError as e:
        raise Exception(f'ffprobe call error:{str(e)}')
    except Exception as e:
        raise Exception(f'ffprobe except error:{str(e)}')


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
def conver_mp4(source_file, out_mp4,*,is_box=False):
    return runffmpeg([
        '-y',
        '-i',
        os.path.normpath(source_file),
        '-c:v',
        'libx264',
        "-c:a",
        "aac",
        out_mp4
    ], no_decode=True, de_format=config.settings['hwaccel_output_format'],is_box=is_box)


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
def split_audio_byraw(source_mp4, targe_audio,is_separate=False):
    cmd = [
        "-y",
        "-i",
        source_mp4,
        "-vn",
        "-c:a",
        "copy",
        targe_audio
    ]
    if not is_separate:
        return runffmpeg(cmd)
    # 继续人声分离
    runffmpeg([
        "-y",
        "-i",
        source_mp4,
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        targe_audio
    ])
    try:
        path=os.path.dirname(targe_audio)
        if not os.path.exists(os.path.join(path,'vocal.wav')):
            set_process(config.transobj['Separating vocals and background music, which may take a longer time'])
            try:
                gr = st.uvr(model_name="HP2", save_root=path, inp_path=targe_audio)
                print(next(gr))
                print(next(gr))
            except Exception as e:
                msg=f"separate vocal and background music:{str(e)}"
                set_process(msg)
                raise Exception(msg)
        # 再将 vocal.wav 转为1通道，8000采样率，方便识别
        runffmpeg([
            "-y",
            "-i",
            os.path.join(path,'vocal.wav'),
            "-ac",
            "1",
            "-ar",
            "8000",
            os.path.join(path,'vocal8000.wav'),
        ])
    except Exception as e:
        print("end")
        msg=f"separate vocal and background music:{str(e)}"
        set_process(msg)
        raise Exception(msg)

#  背景音乐是wav,配音人声是m4a，都在目标文件夹下，合并后最后文件仍为 人声文件，时长需要等于人声
def backandvocal(backwav,peiyinm4a):
    tmpwav=os.path.join(os.environ["TEMP"] or os.environ['temp'],f'{time.time()}.wav')
    tmpm4a=os.path.join(os.environ["TEMP"] or os.environ['temp'],f'{time.time()}.m4a')
    # 背景转为m4a文件,音量降低为0.8
    wav2m4a(backwav,tmpm4a,["-filter:a","volume=0.8"])
    runffmpeg(['-y', '-i', peiyinm4a, '-i', tmpm4a, '-filter_complex',"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', tmpwav])
    shutil.copy2(tmpwav,peiyinm4a)
    # 转为 m4a


# wav转为 m4a cuda + h264_cuvid
def wav2m4a(wavfile, m4afile,extra=None):
    cmd = [
        "-y",
        "-i",
        wavfile,
        "-c:a",
        "aac",
        m4afile
    ]
    if extra:
        cmd=cmd[:3]+extra+cmd[3:]
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
        '-crf', '13', '-to', f'{totime}', '-y', out], no_decode=True,de_format="nv12")


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
# def text_to_speech(*, text="", role="", rate='+0%', filename=None, tts_type=None, play=False):
#     try:
#         if rate != '+0%':
#             set_process(f'text to speech speed {rate}')
#         if tts_type == "edgeTTS":
#             if not get_voice_edgetts(text=text, role=role, rate=rate, filename=filename):
#                 raise Exception(f"edgeTTS error")
#         elif tts_type == "openaiTTS":
#             if not get_voice_openaitts(text, role, rate, filename):
#                 raise Exception(f"openaiTTS error")
#         elif tts_type == 'elevenlabsTTS':
#             if not get_voice_elevenlabs(text, role, rate, filename):
#                 raise Exception(f"elevenlabsTTS error")
#         if os.path.exists(filename) and os.path.getsize(filename) > 0:
#             if play:
#                 threading.Thread(target=pygameaudio, args=(filename,)).start()
#             return True
#         return False
#     except Exception as e:
#         raise Exception(f"text to speech:{filename=},{tts_type=}," + str(e))


def show_popup(title, text):
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QMessageBox
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
    msg.setText(text)
    msg.addButton(QMessageBox.Yes)
    msg.addButton(QMessageBox.Cancel)
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
            raise Exception(config.transobj['zimuwenjianbuzhengque'])
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


# 工具箱写入日志队列
def set_process_box(text, type='logs'):
    set_process(text, type, "box")

# 综合写入日志，默认sp界面
def set_process(text, type="logs", qname='sp'):
    try:
        if text:
            log_msg = text.strip()
            if log_msg.startswith("[error"):
                config.logger.error(log_msg)
            else:
                config.logger.info(log_msg)

        if qname == 'sp':
            config.queue_logs.put_nowait({"text": text, "type": type,"btnkey":config.btnkey})
        elif qname=='box':
            config.queuebox_logs.put_nowait({"text": text, "type": type})
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
                print(f"Deleted: {item_path}")

            # 如果是子目录，递归调用删除函数
            elif os.path.isdir(item_path):
                delete_files(item_path)
    except:
        pass


def send_notification(title, message):
    notification.notify(
        title=title,
        message=message,
        ticker="视频翻译与配音",
        app_name="视频翻译与配音",#config.uilanglist['SP-video Translate Dubbing'],
        app_icon=os.path.join(config.rootdir,'videotrans/styles/icon.ico'),
        timeout=10  # Display duration in seconds
    )
