# -*- coding: utf-8 -*-
import copy
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import timedelta
from pathlib import Path

import requests

from videotrans.configure import config
# 根据 gptsovits config.params['gptsovits_role'] 返回以参考音频为key的dict

# 获取代理，如果已设置os.environ代理，则返回该代理值,否则获取系统代理


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


def get_cosyvoice_role():
    rolelist = {
        "clone": 'clone'
    }
    if config.defaulelang == 'zh':
        rolelist['中文男'] = '中文男'
        rolelist['中文女'] = '中文女'
        rolelist['英文男'] = '英文男'
        rolelist['英文女'] = '英文女'
        rolelist['日语男'] = '日语男'
        rolelist['韩语女'] = '韩语女'
        rolelist['粤语女'] = '粤语女'
    else:
        rolelist['Chinese Male'] = '中文男'
        rolelist['Chinese Female'] = '中文女'
        rolelist['English Male'] = '英文男'
        rolelist['English Female'] = '英文女'
        rolelist['Japanese Male'] = '日语男'
        rolelist['Korean Female'] = '韩语女'
        rolelist['Cantonese Female'] = '粤语女'
    if not config.params['cosyvoice_role'].strip():
        return rolelist
    for it in config.params['cosyvoice_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"reference_audio": tmp[0], "reference_text": tmp[1]}
    return rolelist


def get_fishtts_role():
    if not config.params['fishtts_role'].strip():
        return None
    rolelist = {}
    for it in config.params['fishtts_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"reference_audio": tmp[0], "reference_text": tmp[1]}
    return rolelist


def pygameaudio(filepath):
    from videotrans.util.playmp3 import AudioPlayer
    player = AudioPlayer(filepath)
    player.start()


# 获取 elenevlabs 的角色列表
def get_elevenlabs_role(force=False):
    jsonfile = os.path.join(config.ROOT_DIR, 'elevenlabs.json')
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
        config.params['proxy'] = None
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
        config.params['proxy'] = set_val
        os.environ['http_proxy'] = set_val
        os.environ['https_proxy'] = set_val
        os.environ['all_proxy'] = set_val
        return set_val

    # 获取代理
    http_proxy = config.params['proxy'] or os.environ.get('http_proxy') or os.environ.get('https_proxy')
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
        pass
    return None


def get_302ai_doubao(role_name=None):
    zh = {
        "爽快思思": "zh_female_shuangkuaisisi_moon_bigtts",
        "温暖阿虎": "zh_male_wennuanahu_moon_bigtts",
        "少年梓辛": "zh_male_shaonianzixin_moon_bigtts",
        "邻家女孩": "zh_female_linjianvhai_moon_bigtts",
        "渊博小叔": "zh_male_yuanboxiaoshu_moon_bigtts",
        "阳光青年": "zh_male_yangguangqingnian_moon_bigtts",
        "京腔侃爷": "zh_male_jingqiangkanye_moon_bigtts",
        "湾湾小何": "zh_female_wanwanxiaohe_moon_bigtts",
        "湾区大叔": "zh_female_wanqudashu_moon_bigtts",
        "呆萌川妹": "zh_female_daimengchuanmei_moon_bigtts",
        "广州德哥": "zh_male_guozhoudege_moon_bigtts",
        "北京小爷": "zh_male_beijingxiaoye_moon_bigtts",
        "浩宇小哥": "zh_male_haoyuxiaoge_moon_bigtts",
        "广西远舟": "zh_male_guangxiyuanzhou_moon_bigtts",
        "妹坨洁儿": "zh_female_meituojieer_moon_bigtts",
        "豫州子轩": "zh_male_yuzhouzixuan_moon_bigtts",
        "高冷御姐": "zh_female_gaolengyujie_moon_bigtts",
        "傲娇霸总": "zh_male_aojiaobazong_moon_bigtts",
        "魅力女友": "zh_female_meilinvyou_moon_bigtts",
        "深夜播客": "zh_male_shenyeboke_moon_bigtts",
        "柔美女友": "zh_female_sajiaonvyou_moon_bigtts",
        "撒娇学妹": "zh_female_yuanqinvyou_moon_bigtts"
    }
    en = {
        "爽快思思": "zh_female_shuangkuaisisi_moon_bigtts",
        "温暖阿虎": "zh_male_wennuanahu_moon_bigtts",
        "少年梓辛": "zh_male_shaonianzixin_moon_bigtts",
        "京腔侃爷": "zh_male_jingqiangkanye_moon_bigtts"
    }
    ja = {
        "和音": "multi_male_jingqiangkanye_moon_bigtts",
        "晴子": "multi_female_shuangkuaisisi_moon_bigtts",
        "朱美": "multi_female_gaolengyujie_moon_bigtts",
        "広志": "multi_male_wanqudashu_moon_bigtts"
    }
    if role_name:
        if role_name in zh:
            return zh[role_name]
        if role_name in en:
            return en[role_name]
        if role_name in ja:
            return ja[role_name]
        return role_name

    return {
        "zh": list(zh.keys()),
        "ja": list(ja.keys()),
        "en": list(en.keys())
    }


#  get role by edge tts
def get_edge_rolelist():
    voice_list = {}
    if vail_file(config.ROOT_DIR + "/voice_list.json"):
        try:
            voice_list = json.load(open(config.ROOT_DIR + "/voice_list.json", "r", encoding="utf-8"))
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
        with open(config.ROOT_DIR + "/voice_list.json", "w",encoding='utf-8') as f:
            f.write(json.dumps(voice_list))
        config.edgeTTS_rolelist = voice_list
        return voice_list
    except Exception as e:
        config.logger.error('获取edgeTTS角色失败' + str(e))


def get_azure_rolelist():
    voice_list = {}
    if vail_file(config.ROOT_DIR + "/azure_voice_list.json"):
        try:
            voice_list = json.load(open(config.ROOT_DIR + "/azure_voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                config.AzureTTS_rolelist = voice_list
                return voice_list
        except:
            pass
    return voice_list


# 执行 ffmpeg
def runffmpeg(arg, *, noextname=None, uuid=None,force_cpu=False):
    arg_copy = copy.deepcopy(arg)

    cmd = [config.FFMPEG_BIN, "-hide_banner", "-ignore_unknown"]
    # 启用了CUDA 并且没有禁用GPU
    # 默认视频编码 libx264 / libx265
    default_codec = f"libx{config.settings['video_codec']}"

    for i, it in enumerate(arg):
        if arg[i] == '-i' and i < len(arg) - 1:
            arg[i + 1] = Path(arg[i + 1]).as_posix()
            if not vail_file(arg[i + 1]):
                raise Exception(f'..{arg[i + 1]} {config.transobj["vlctips2"]}')

    if not force_cpu and default_codec in arg and config.video_codec != default_codec:
        if not config.video_codec:
            config.video_codec = get_video_codec()

        for i, it in enumerate(arg):
            if i > 0 and arg[i - 1] == '-c:v' and arg[i] !='copy':
                arg[i] = config.video_codec
            elif it == '-crf' and config.settings['cuda_qp'] and re.search(r'\sh(264|evc)_nvenc\s'," ".join(cmd),re.I):
                arg[i] = '-qp'
                if arg[i]=='copy':
                    arg[i+1]='0'


    cmd += arg
    if Path(cmd[-1]).is_file():
        cmd[-1] = Path(cmd[-1]).as_posix()
    # 插入自定义 ffmpeg 参数
    if config.settings['ffmpeg_cmd']:
        for it in config.settings['ffmpeg_cmd'].split(' '):
            cmd.insert(-1, str(it))
    if noextname:
        config.queue_novice[noextname] = 'ing'
    try:
        config.logger.info(f'{force_cpu=},{cmd=}')
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
        # 处理视频时如果出错，尝试回退
        if not force_cpu and cmd[-1].endswith('.mp4'):
            # 存在视频的copy操作时，尝试回退使用重新编码
            # 切换为cpu
            set_process(text=config.transobj['huituicpu'], uuid=uuid)
            config.logger.error(f'cuda上执行出错，退回到CPU执行')
            for i, it in enumerate(arg_copy):
                if i > 0 and arg_copy[i - 1] == '-c:v' and arg_copy[i] not in ['copy','libx264','libx265']:
                    arg_copy[i] = default_codec
            return runffmpeg(arg_copy, noextname=noextname,force_cpu=True)
        if noextname:
            config.queue_novice[noextname] = "error"
        config.logger.error(f'cmd执行出错抛出异常{force_cpu=}:{cmd=},{str(e.stderr)}')
        raise
    except Exception as e:
        config.logger.exception(e)
        raise


# run ffprobe 获取视频元信息
def runffprobe(cmd):
    try:
        if Path(cmd[-1]).is_file():
            cmd[-1] = Path(cmd[-1]).as_posix()
        p = subprocess.run([config.FFPROBE_BIN] + cmd,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           encoding="utf-8",
                           text=True,
                           check=True,
                           creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
        if p.stdout:
            return p.stdout.strip()
        config.logger.error(str(p) + str(p.stderr))
        raise Exception(str(p.stderr))
    except subprocess.CalledProcessError as e:
        config.logger.exception(e)
        msg = f'ffprobe error,:{str(e)}{str(e.stdout)},{str(e.stderr)}'
        msg = msg.replace('\n', ' ')
        raise Exception(msg)
    except Exception as e:
        raise


# 获取视频信息
def get_video_info(mp4_file, *, video_fps=False, video_scale=False, video_time=False, get_codec=False):
    mp4_file = Path(mp4_file).as_posix()
    out = runffprobe(
        ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', os.path.normpath(mp4_file)])
    if out is False:
        raise Exception(f'ffprobe error:dont get video information')
    out = json.loads(out)
    result = {
        "video_fps": 30,
        "video_codec_name": "",
        "audio_codec_name": "",
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

    if video_time:
        return result['time']
    if video_fps:
        return ['video_fps']
    if video_scale:
        return result['width'], result['height']
    if get_codec:
        return result['video_codec_name'], result['audio_codec_name']
    return result


# 获取某个视频的时长 s
def get_video_duration(file_path):
    return get_video_info(file_path, video_time=True)


# 获取某个视频的fps
def get_video_fps(file_path):
    return get_video_info(file_path, video_fps=True)


# 获取宽高分辨率
def get_video_resolution(file_path):
    return get_video_info(file_path, video_scale=True)


# 获取视频编码和
def get_codec_name(file_path):
    return get_video_info(file_path, video_scale=True)


# 从原始视频分离出 无声视频 cuda + h264_cuvid
def split_novoice_byraw(source_mp4, novoice_mp4, noextname, lib="copy"):
    cmd = [
        "-y",
        "-i",
        Path(source_mp4).as_posix(),
        "-an",
        "-c:v",
        lib,
        "-crf",
        "0",
        f'{novoice_mp4}'
    ]
    return runffmpeg(cmd, noextname=noextname)


# 从原始视频中分离出音频 cuda + h264_cuvid
def split_audio_byraw(source_mp4, targe_audio, is_separate=False, uuid=None):
    source_mp4 = Path(source_mp4).as_posix()
    targe_audio = Path(targe_audio).as_posix()
    cmd = [
        "-y",
        "-i",
        source_mp4,
        "-vn",
        "-ac",
        "1",
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
        path = Path(targe_audio).parent.as_posix()
        vocal_file = path + '/vocal.wav'
        if not vail_file(vocal_file):
            set_process(text=config.transobj['Separating vocals and background music, which may take a longer time'],
                        uuid=uuid)
            try:
                st.start(audio=tmpfile, path=path, uuid=uuid)
            except Exception as e:
                msg = f"separate vocal and background music:{str(e)}"
                set_process(text=msg, uuid=uuid)
                raise Exception(msg)
        if not vail_file(vocal_file):
            return False
    except Exception as e:
        msg = f"separate vocal and background music:{str(e)}"
        set_process(text=msg, uuid=uuid)
        raise


# 将字符串做 md5 hash处理
def get_md5(input_string: str):
    md5 = hashlib.md5()
    md5.update(input_string.encode('utf-8'))
    return md5.hexdigest()


def conver_to_16k(audio, target_audio):
    return runffmpeg([
        "-y",
        "-i",
        Path(audio).as_posix(),
        "-ac",
        "1",
        "-ar",
        "16000",
        Path(target_audio).as_posix(),
    ])


#  背景音乐是wav,配音人声是m4a，都在目标文件夹下，合并后最后文件仍为 人声文件，时长需要等于人声
def backandvocal(backwav, peiyinm4a):
    backwav = Path(backwav).as_posix()
    peiyinm4a = Path(peiyinm4a).as_posix()
    tmpwav = Path((os.environ["TEMP"] or os.environ['temp']) + f'/{time.time()}-1.m4a').as_posix()
    tmpm4a = Path((os.environ["TEMP"] or os.environ['temp']) + f'/{time.time()}.m4a').as_posix()
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
        Path(wavfile).as_posix(),
        "-c:a",
        "aac",
        "-ar",
        "48000",
        Path(m4afile).as_posix()
    ]
    if extra:
        cmd = cmd[:3] + extra + cmd[3:]
    return runffmpeg(cmd)


# wav转为 mp3 cuda + h264_cuvid
def wav2mp3(wavfile, mp3file, extra=None):
    cmd = [
        "-y",
        "-i",
        Path(wavfile).as_posix(),
        "-ar",
        "48000",
        Path(mp3file).as_posix()
    ]
    if extra:
        cmd = cmd[:3] + extra + cmd[3:]
    return runffmpeg(cmd)


def whisper16mp3(wavfile, mp3file):
    cmd = [
        "-y",
        "-i",
        Path(wavfile).as_posix(),
        "-ar",
        "16000",
        Path(mp3file).as_posix()
    ]
    return runffmpeg(cmd)


# m4a 转为 wav cuda + h264_cuvid
def m4a2wav(m4afile, wavfile):
    cmd = [
        "-y",
        "-i",
        Path(m4afile).as_posix(),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "128k",
        "-c:a",
        "pcm_s16le",
        Path(wavfile).as_posix()
    ]
    return runffmpeg(cmd)


# 创建 多个连接文件
def create_concat_txt(filelist, concat_txt=None):
    txt = []
    for it in filelist:
        if not Path(it).exists() or Path(it).stat().st_size == 0:
            continue
        txt.append(f"file '{os.path.basename(it)}'")
    if len(txt) < 1:
        raise Exception(f'file list no vail')
    with Path(concat_txt).open('w',encoding='utf-8') as f:
        f.write("\n".join(txt))
        f.flush()
    return concat_txt


# 多个视频片段连接 cuda + h264_cuvid
def concat_multi_mp4(*, out=None, concat_txt=None):
    video_codec = config.settings['video_codec']
    if out:
        out = Path(out).as_posix()
    os.chdir(os.path.dirname(concat_txt))
    runffmpeg(
        ['-y', '-f', 'concat', '-i', concat_txt, '-c:v', f"libx{video_codec}", '-an', '-crf',
         f'{config.settings["crf"]}', '-preset', config.settings['preset'], out])
    os.chdir(config.ROOT_DIR)
    return True


# 多个音频片段连接 
def concat_multi_audio(*, out=None, concat_txt=None):
    if out:
        out = Path(out).as_posix()

    os.chdir(os.path.dirname(concat_txt))
    runffmpeg(['-y', '-f', 'concat', '-i', concat_txt, '-c:a', 'aac', out])
    os.chdir(config.TEMP_DIR)
    return True


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


def show_popup(title, text, parent=None):
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox

    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
    msg.setText(text)
    msg.addButton(QMessageBox.Yes)
    msg.addButton(QMessageBox.Cancel)
    msg.setWindowModality(Qt.ApplicationModal)  # 设置为应用模态
    msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)  # 置于顶层
    msg.setIcon(QMessageBox.Information)
    x = msg.exec()  # 显示消息框
    return x


'''
格式化毫秒或秒为符合srt格式的 2位小时:2位分:2位秒,3位毫秒 形式
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

# 将不规范的 时:分:秒,|.毫秒格式为  aa:bb:cc,ddd形式
# eg  001:01:2,4500  01:54,14 等做处理
def format_time(s_time="", separate=','):
    if not s_time.strip():
        return f'00:00:00{separate}000'
    hou, min, sec,ms = 0, 0, 0,0

    tmp = s_time.strip().split(':')
    if len(tmp) >= 3:
        hou,min,sec = tmp[-3].strip(),tmp[-2].strip(),tmp[-1].strip()
    elif len(tmp) == 2:
        min,sec = tmp[0].strip(),tmp[1].strip()
    elif len(tmp) == 1:
        sec = tmp[0].strip()
    
    if re.search(r',|\.', str(sec)):
        t = re.split(r',|\.', str(sec))
        sec = t[0].strip()
        ms=t[1].strip()
    else:
        ms = 0
    hou = f'{int(hou):02}'[-2:]
    min = f'{int(min):02}'[-2:]
    sec = f'{int(sec):02}'
    ms = f'{int(ms):03}'[-3:]
    return f"{hou}:{min}:{sec}{separate}{ms}"

# 将 datetime.timedelta 对象的秒和微妙转为毫秒整数值
def toms(td):
    return (td.seconds * 1000) + int(td.microseconds / 1000)

# 将 时:分:秒,毫秒 转为毫秒整数值
def get_ms_from_hmsm(time_str):
    h,m,sec2ms=0,0,'00,000'
    tmp0= time_str.split(":")
    if len(tmp0)==3:
        h,m,sec2ms=tmp0[0],tmp0[1],tmp0[2]
    elif len(tmp0)==2:
        m,sec2ms=tmp0[0],tmp0[1]
        
    tmp=sec2ms.split(',')
    ms=tmp[1] if len(tmp)==2 else 0
    sec=tmp[0]
    
    return int(int(h) * 3600000 + int(m) * 60000 +int(sec)*1000 + int(ms))

# 合法的srt字符串转为 dict list
def srt_str_to_listdict(content):
    import srt
    line=0
    result=[]
    for sub in srt.parse(content):
        line+=1
        it={
            "start_time":toms(sub.start),
            "end_time":toms(sub.end),
            "line":line,
            "text":sub.content
        }
        it['startraw']=ms_to_time_string(ms=it['start_time'])
        it['endraw']=ms_to_time_string(ms=it['end_time'])
        it["time"]=f"{it['startraw']} --> {it['endraw']}"
        result.append(it)
    return result

# 将字符串或者字幕文件内容，格式化为有效字幕数组对象
# 格式化为有效的srt格式
def format_srt(content):
    result=[]
    try:
        result=srt_str_to_listdict(content)
    except Exception:
        result=srt_str_to_listdict(process_text_to_srt_str(content))        
    return result
    



# 将srt文件或合法srt字符串转为字典对象
def get_subtitle_from_srt(srtfile, *, is_file=True):
    def _readfile(file):
        content=""
        try:
            with open(file,'r',encoding='utf-8') as f:
                content=f.read().strip()
        except Exception as e:
            try:
                with open(file,'r', encoding='gbk') as f:
                    content = f.read().strip()
            except Exception as e:
                config.logger.exception(e,exc_info=True)
        return content

    content=''
    if is_file:
        # 未知bug，srtfile存在却偶发读为空，似乎某处资源未释放，临时措施
        retry=3
        while retry>0:
            content=_readfile(srtfile)
            if len(content)>0:
                break
            time.sleep(2)
            retry-=1
    else:
        content = srtfile.strip()

    if len(content) < 1:
        raise Exception(f"srt is empty:{srtfile=},{content=}")

    result = format_srt(content)

    # txt 文件转为一条字幕
    if len(result) < 1:
        result = [
            {"line": 1, "time": "00:00:00,000 --> 00:00:02,000", "text": "\n".join(content)}
        ]
    return result


# 将srt字幕转为 ass字幕
def srt2ass(srt_file, ass_file, maxlen=40):
    srt_list = get_subtitle_from_srt(srt_file)
    text = ""
    for i, it in enumerate(srt_list):
        it['text'] = textwrap.fill(it['text'], maxlen, replace_whitespace=False).strip()
        text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}\n\n"
    tmp_srt = config.TEMP_DIR + f"/{time.time()}.srt"
    with open(tmp_srt, 'w', encoding='utf-8', errors='ignore') as f:
        f.write(text)

    runffmpeg(['-y', '-i', tmp_srt, ass_file])
    with open(ass_file, 'r', encoding='utf-8') as f:
        ass_str = f.readlines()

    for i, it in enumerate(ass_str):
        if it.find('Style: ') == 0:
            ass_str[
                i] = 'Style: Default,{fontname},{fontsize},{fontcolor},&HFFFFFF,{fontbordercolor},{fontbackcolor},0,0,0,0,100,100,0,0,1,1,0,2,10,10,{subtitle_bottom},1'.format(
                fontname=config.settings['fontname'], fontsize=config.settings['fontsize'],
                fontcolor=config.settings['fontcolor'],
                fontbordercolor=config.settings['fontbordercolor'],
                fontbackcolor=config.settings['fontbordercolor'],
                subtitle_bottom=config.settings['subtitle_bottom'])
            break

    with open(ass_file, 'w', encoding='utf-8') as f:
        f.write("".join(ass_str))


# 将字幕字典列表写入srt文件
def save_srt(srt_list, srt_file):
    txt = get_srt_from_list(srt_list)
    with open(srt_file,"w", encoding="utf-8") as f:
        f.write(txt)
    return True

def get_current_time_as_yymmddhhmmss(format='hms'):
  """将当前时间转换为 YYMMDDHHmmss 格式的字符串。"""
  now = datetime.datetime.now()
  return now.strftime("%y%m%d%H%M%S" if format!='hms' else "%H%M%S")

def get_srt_from_list(srt_list):
    txt = ""
    line = 0
    # it中可能含有完整时间戳 it['time']   00:00:01,123 --> 00:00:12,345
    # 开始和结束时间戳  it['startraw']=00:00:01,123  it['endraw']=00:00:12,345
    # 开始和结束毫秒数值  it['start_time']=126 it['end_time']=678
    for it in srt_list:
        line += 1
        if "startraw" not in it:
            # 存在完整开始和结束时间戳字符串 时:分:秒,毫秒 --> 时:分:秒,毫秒
            if 'time' in it:
                startraw, endraw = it['time'].strip().split(" --> ")
                startraw = format_time(startraw.strip().replace('.', ','), ',')
                endraw = format_time(endraw.strip().replace('.', ','), ',')
            elif 'start_time' in it and 'end_time' in it:
                # 存在开始结束毫秒数值
                startraw = ms_to_time_string(ms=it['start_time'])
                endraw = ms_to_time_string(ms=it['end_time'])
            else:
                raise Exception(
                    f'字幕中不存在 time/startraw/start_time 任何有效时间戳形式' if config.defaulelang == 'zh' else 'There is no time/startraw/start_time in the subtitle in any valid timestamp form.')
        else:
            # 存在单独开始和结束  时:分:秒,毫秒 字符串
            startraw = it['startraw']
            endraw = it['endraw']
        txt += f"{line}\n{startraw} --> {endraw}\n{it['text']}\n\n"
    return txt




# 判断 novoice.mp4是否创建好
def is_novoice_mp4(novoice_mp4, noextname, uuid=None):
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
            return
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
            set_process(
                text=f"{noextname} {'分离音频和画面' if config.defaulelang == 'zh' else 'spilt audio and video'} {size}",
                uuid=uuid)
            time.sleep(3)
            t += 3
            continue
        return True


def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


# 从视频中切出一段时间的视频片段 cuda + h264_cuvid
def cut_from_video(*, ss="", to="", source="", pts="", out=""):
    video_codec = config.settings['video_codec']
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
                  '-preset', config.settings['preset'],
                  f'{out}'
                  ]
    return runffmpeg(cmd)


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
        "16000",
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
            config.params["clone_voicelist"] = ["clone"] + res.json()
            set_process(type='set_clone_role')
            return True
        raise Exception(
            f"code={res.status_code},{config.transobj['You must deploy and start the clone-voice service']}")
    except Exception as e:
        if set_p:
            raise
    return False


# 综合写入日志，默认sp界面
# type=logs|error|subtitle|end|stop|succeed|set_precent|replace_subtitle|.... 末尾显示类型，
# uuid 任务的唯一id，用于确定插入哪个子队列
# nologs=False不写入日志
def set_process(*, text="", type="logs", uuid=None, nologs=False):
    try:
        if text:
            if not nologs:
                if type == 'error':
                    config.logger.error(text)
                else:
                    config.logger.info(text)
            # 移除html
            if type == 'error':
                text = text.replace('\\n', ' ').strip()
        log = {"text": text, "type": type, "uuid": uuid}
        if uuid:
            config.push_queue(uuid, log)
        else:
            config.global_msg.append(log)
    except Exception:
        pass


def send_notification(title, message):
    if config.exec_mode=='api':
        return
    from plyer import notification
    try:
        notification.notify(
            title=title[:60],
            message=message[:120],
            ticker="pyVideoTrans",
            app_name="pyVideoTrans",  # config.uilanglist['SP-video Translate Dubbing'],
            app_icon=config.ROOT_DIR + '/videotrans/styles/icon.ico',
            timeout=10  # Display duration in seconds
        )
    except:
        pass


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
        if format in ['wav', 'mp3', 'm4a']:
            audio = AudioSegment.from_file(input_file_path, format=format if format in ['wav', 'mp3'] else 'mp4')
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
        if format in ['wav', 'mp3', 'm4a']:
            trimmed_audio.export(input_file_path, format=format if format in ['wav', 'mp3'] else 'mp4')
            return input_file_path
        try:
            trimmed_audio.export(input_file_path + ".mp3", format="mp3")
            runffmpeg(['-y', '-i', input_file_path + ".mp3", input_file_path])
        except Exception:
            pass
        return input_file_path
    return trimmed_audio


def remove_qsettings_data():
    try:
        Path(config.ROOT_DIR + "/videotrans/params.json").unlink(missing_ok=True)
        Path(config.ROOT_DIR + "/videotrans/cfg.json").unlink(missing_ok=True)
    except Exception:
        pass


def open_url(url=None, title: str = None):
    import webbrowser
    if url:
        return webbrowser.open_new_tab(url)
    title_url_dict = {
        'blog': "https://tts.pyvideotrans.com/",
        'ffmpeg': "https://www.ffmpeg.org/download.html",
        'git': "https://github.com/jianchang512/pyvideotrans",
        'issue': "https://github.com/jianchang512/pyvideotrans/issues",
        'discord': "https://discord.gg/7ZWbwKGMcx",
        'models': "https://github.com/jianchang512/stt/releases/tag/0.0",
        'dll': "https://github.com/jianchang512/stt/releases/tag/v0.0.1",
        'stt': "https://github.com/jianchang512/stt/",
        'gtrans': "https://pyvideotrans.com/15.html",
        'cuda': "https://pyvideotrans.com/gpu.html",
        'website': "https://pyvideotrans.com",
        'help': "https://pyvideotrans.com",
        'xinshou': "https://pyvideotrans.com/getstart",
        "about": "https://pyvideotrans.com/about",
        'download': "https://github.com/jianchang512/pyvideotrans/releases",
        'openvoice': "https://github.com/kungful/openvoice-api"
    }
    if title and title in title_url_dict:
        return webbrowser.open_new_tab(title_url_dict[title])


def open_dir(dirname=None):
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
    p = Path(file)
    if not p.exists() or not p.is_file():
        return False
    if p.stat().st_size == 0:
        return False
    return True


# 获取最终视频应该输出的编码格式
def get_video_codec():
    plat = platform.system()
    # 264 / 265
    video_codec = int(config.settings['video_codec'])
    hhead = 'hevc' if video_codec != 264 else 'h264'
    mp4_test = config.ROOT_DIR + "/videotrans/styles/no-remove.mp4"
    if not Path(mp4_test).is_file():
        return f'libx{video_codec}'
    mp4_target = config.TEMP_DIR + "/test.mp4"
    codec = ''
    if plat in ['Windows', 'Linux']:
        import torch
        if torch.cuda.is_available():
            codec = f'{hhead}_nvenc'
        elif plat == 'Windows':
            codec = f'{hhead}_qsv'
        elif plat == 'Linux':
            codec = f'{hhead}_vaapi'
    elif plat == 'Darwin':
        codec = f'{hhead}_videotoolbox'

    if not codec:
        return f"libx{video_codec}"

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
        if sys.platform == 'win32':
            try:
                codec = f"{hhead}_amf"
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
                codec = f"libx{video_codec}"
        else:            
            codec = f"libx{video_codec}"
    return codec


# 设置ass字体格式
def set_ass_font(srtfile=None):
    if not os.path.exists(srtfile) or os.path.getsize(srtfile) == 0:
        return os.path.basename(srtfile)
    runffmpeg(['-y', '-i', srtfile, f'{srtfile}.ass'])
    assfile = f'{srtfile}.ass'
    with open(assfile, 'r', encoding='utf-8') as f:
        ass_str = f.readlines()

    for i, it in enumerate(ass_str):
        if it.find('Style: ') == 0:
            ass_str[
                i] = 'Style: Default,{fontname},{fontsize},{fontcolor},&HFFFFFF,{fontbordercolor},&H0,0,0,0,0,100,100,0,0,1,1,0,2,10,10,{subtitle_bottom},1'.format(
                fontname=config.settings['fontname'], fontsize=config.settings['fontsize'],
                fontcolor=config.settings['fontcolor'], fontbordercolor=config.settings['fontbordercolor'],
                subtitle_bottom=config.settings['subtitle_bottom'])
            break

    with open(assfile, 'w', encoding='utf-8') as f:
        f.write("".join(ass_str))
    return assfile


# 删除翻译结果的特殊字符
def cleartext(text: str):
    return text.replace('"', '').replace("'", '').replace('&#39;', '').replace('&quot;', "").strip()


# 如果仅相差一行，直接拆分最后一行内容为两行
'''
['你好啊', ' 朋友们', '今天是', '星期几你好啊朋友们哈哈今天天气不错哦是吧', 'hello, my friend, today is']
['你好啊', ' 朋友们', '今天是', '星期几你好啊朋友们哈哈今天天气不错哦是吧', 'hello, my friend', ' today is']

['你好啊', ' 朋友们', '今天是', '星期几你好啊朋友们哈哈今天天气不错哦是吧', 'hello  my friend  today is monday is it']
['你好啊', ' 朋友们', '今天是', '星期几你好啊朋友们哈哈今天天气不错哦是吧', 'hello  my friend  today is', ' monday is it']

['你好啊', ' 朋友们', '今天是', '星期几你好啊朋友们哈哈今天天气不错哦是吧']
['你好啊', ' 朋友们', '今天是', '星期几你好啊朋友们哈哈今天天', '气不错哦是吧']

['你好啊', ' 朋友们', '今天是', '星期几你好啊,朋友们!哈哈!今天天气不错哦,是吧！']
['你好啊', ' 朋友们', '今天是', '星期几你好啊,朋友们!哈哈!今天天气不错哦', '是吧']
'''


def split_line(sep_list):
    # 先移除最后一行开头结尾的无效字符
    sep = sep_list[-1].strip()
    if not sep:
        return False
    flag = [",", ".", "?", ";", ":", "'", "\"", "-", "_", "/", "\\", "+", "-", "=", "!", "*", "(", ")", "{", "}", "，",
            "。", "·", "？", "！", "（", "）", "｛", "｝", "【", "】"]
    if sep[0] in flag:
        sep = sep[1:].strip()
    if sep and sep[-1] in flag:
        sep = sep[:-1].strip()

    # 移除后最后一行 无有效文字或字符少于3
    if not sep or len(sep) < 3:
        return False

    # 先尝试标点符号拆分
    res1 = re.split(r'[,.，。；？?、]', sep)
    if len(res1) > 1:
        sep_list[-1] = ",".join(res1[:-1])
        sep_list.append(res1[-1])
        return sep_list

    # 再尝试空格拆分，
    res2 = sep.split(" ")
    # 不存在空格 强制按字符分割
    if len(res2) < 2:
        pos = int(len(sep) / -3)
        sep_list[-1] = sep[:pos]
        sep_list.append(sep[pos:])
        return sep_list

    # 存在一个空格则平分
    if len(res2) == 2:
        sep_list[-1] = res2[0]
        sep_list.append(res2[1])
        return sep_list

    # 取后三分之一
    pos = int(len(res2) / -3)
    sep_list[-1] = " ".join(res2[:pos])
    sep_list.append(" ".join(res2[pos:]))
    return sep_list


# 删除临时文件
def _unlink_tmp():
    try:
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
    except Exception:
        pass
    try:
        shutil.rmtree(config.TEMP_HOME, ignore_errors=True)
    except Exception:
        pass


# 启动删除未使用的 临时文件夹，处理关闭时未能正确删除而遗留的
def del_unused_tmp():
    remain = Path(config.TEMP_DIR).name

    def get_tmplist(pathdir):
        dirs = []
        for p in Path(pathdir).iterdir():
            if p.is_dir() and re.match(r'tmp\d{4}', p.name) and p.name != remain:
                dirs.append(p.resolve().as_posix())
        return dirs

    wait_remove = [*get_tmplist(config.ROOT_DIR), *get_tmplist(config.HOME_DIR)]

    try:
        for p in wait_remove:
            shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass


def shutdown_system():
    # 获取当前操作系统类型
    system = platform.system()

    if system == "Windows":
        # Windows 下的关机命令
        subprocess.call("shutdown /s /t 1")
    elif system == "Linux":
        # Linux 下的关机命令
        subprocess.call("poweroff")
    elif system == "Darwin":
        # macOS 下的关机命令
        subprocess.call("sudo shutdown -h now", shell=True)
    else:
        print(f"Unsupported system: {system}")


def format_video(name, target_dir=None):
    raw_pathlib = Path(name)
    raw_basename = raw_pathlib.name
    raw_noextname = raw_pathlib.stem
    ext = raw_pathlib.suffix
    raw_dirname = raw_pathlib.parent.resolve().as_posix()

    obj = {
        "name": name,
        # 处理后 移动后符合规范的目录名
        "dirname": raw_dirname,
        # 符合规范的基本名带后缀
        "basename": raw_basename,
        # 符合规范的不带后缀
        "noextname": raw_noextname,
        # 扩展名
        "ext": ext[1:]
        # 最终存放目标位置，直接存到这里
    }
    rule=r'[\[\]\{\}\$\`\*\?\"\|]'
    if re.search(rule,raw_noextname) or re.search(r'[\s\.]$',raw_noextname):
        # 规范化名字
        raw_noextname=re.sub(rule,'-',raw_noextname)
        raw_noextname=re.sub(r'[\.\s ]$','-',raw_noextname)
        
        new_name=f'{raw_dirname}/{raw_noextname}{ext}'
        shutil.copy2(name,new_name)
        obj['name']=new_name
        obj['noextname']=raw_noextname
        obj['basename']=f'{raw_noextname}{ext}'
        obj['shound_del_name']=new_name

    if target_dir:
        obj['target_dir'] = Path(f'{target_dir}/{raw_noextname}').as_posix()

    obj['uuid'] = get_md5(f'{name}-{time.time()}')
    return obj

# 获取 prompt提示词
def get_prompt(ainame,is_srt=True):
    prompt_file=get_prompt_file(ainame=ainame,is_srt=is_srt)
    return Path(prompt_file).read_text(encoding='utf-8')

# 获取当前需要操作的prompt txt文件
def get_prompt_file(ainame,is_srt=True):
    prompt_path = f'{config.ROOT_DIR}/videotrans/'
    prompt_name = f'{ainame}{"" if config.defaulelang == "zh" else "-en"}.txt'
    if is_srt and config.settings.get('aisendsrt',False):
        prompt_path += 'prompts/srt/'
    return f'{prompt_path}{prompt_name}'
    
# 将普通文本转为合法的srt字符串
def process_text_to_srt_str(input_text:str):
    if is_srt_string(input_text):
       return input_text
       
    # 将文本按换行符切割成列表
    text_lines = [line.strip() for line in input_text.replace("\r","").splitlines() if line.strip()]
      
    # 分割大于50个字符的行
    text_str_list = []
    for line in text_lines:
        if len(line) > 50:
            # 按标点符号分割为多个字符串
            split_lines = re.split(r'[,.，。]', line)
            text_str_list.extend([l.strip() for l in split_lines if l.strip()])
        else:
            text_str_list.append(line)
    # 创建字幕字典对象列表
    dict_list = []
    start_time_in_seconds = 0  # 初始时间，单位秒

    for i, text in enumerate(text_str_list, start=1):
        # 计算开始时间和结束时间（每次增加1s）
        start_time = ms_to_time_string(seconds=start_time_in_seconds)
        end_time = ms_to_time_string(seconds=start_time_in_seconds + 1)
        start_time_in_seconds += 1

        # 创建字幕字典对象
        srt = f"{i}\n{start_time} --> {end_time}\n{text}"
        dict_list.append(srt)
    
    return "\n\n".join(dict_list)


# 判断是否是srt字符串
def is_srt_string(input_text):
    input_text = input_text.strip()
    if not input_text:
        return False
    
    # 将文本按换行符切割成列表
    text_lines = input_text.replace("\r","").splitlines()
    if len(text_lines)<3:
        return False
               
    # 正则表达式：第一行应为1到2个纯数字
    first_line_pattern = r'^\d{1,2}$'
    
    # 正则表达式：第二行符合时间格式
    second_line_pattern = r'^\s*?\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*$'
    
    # 如果前两行符合条件，返回原字符串
    if not re.match(first_line_pattern, text_lines[0].strip()) or not re.match(second_line_pattern, text_lines[1].strip()):
        return False
    return True

def clean_srt(srt):
    # 替换特殊符号
    srt=re.sub(r'&gt;','>',srt)
    # ：: 换成 :
    srt=re.sub(r'([：:])\s*',':',srt)
    # ,， 换成 ,
    srt=re.sub(r'([,，])\s*',',',srt)
    # 秒和毫秒间的.换成,
    srt=re.sub(r'(:\d+)\.\s*?(\d+)',r'\1,\2',srt)
    # 时间行前后加空格
    time_line=r'(\s?\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s?)'
    srt=re.sub(time_line,r"\n\1 --> \2\n",srt)

    # 去除多余的空行
    srt="\n".join([it.strip() for it in srt.splitlines() if it.strip()])

    # 删掉以空格或换行连接的多个时间行
    time_line2=r'(\s\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s)(?:\s*\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s*)'
    srt=re.sub(time_line2,r'\n\1 --> \2\n',srt)

    srt="\n".join([it.strip() for it in srt.splitlines() if it.strip()])

    # 行号前添加换行符
    srt=re.sub(r'\s?(\d+)\s+?(\d+:\d+:\d+)',r"\n\n\1\n\2",srt)
    return srt.strip().replace('&#39;', '"').replace('&quot;', "'")
