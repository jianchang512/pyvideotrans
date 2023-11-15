# -*- coding: utf-8 -*-

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
from ..translator import baidu_translate_spider_api
from ..translator.chatgpt import chatgpttrans
from ..translator.baidu import baidutrans
from ..translator.deepl import deepltrans
from ..translator.google import googletrans

from . import config
from .config import logger, transobj, queue_logs

# 获取代理，如果已设置os.environ代理，则返回该代理值,否则获取系统代理
from ..tts.openaitts import get_voice


def set_proxy():
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
                os.environ['http_proxy'] = 'http://%s' % proxy_server.replace("http://", '')
                os.environ['https_proxy'] = 'http://%s' % proxy_server.replace("http://", '')
                return proxy_server
    except Exception as e:
        print(f"Error accessing Windows registry: {e}")
    return None


if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


# delete tmp files
def delete_temp(noextname=""):
    if noextname and os.path.exists(f"{config.rootdir}/tmp/{noextname}"):
        shutil.rmtree(f"{config.rootdir}/tmp/{noextname}")


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


# split audio by silence
def shorten_voice(normalized_sound):
    normalized_sound = match_target_amplitude(normalized_sound, -20.0)
    max_interval = 10000
    buffer = 500
    nonsilent_data = []
    audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.video['voice_silence']),
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
            # 可能存在字幕 语音对应问题
            if silence_duration > 0:
                silence = AudioSegment.silent(duration=silence_duration)
                merged_audio += silence

        merged_audio += segment
    #
    if len(merged_audio) > total_duration:
        merged_audio = merged_audio[:total_duration]
    merged_audio.export(f"{config.rootdir}/tmp/{noextname}/tts-{noextname}.wav", format="wav")
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


def runffmpeg(arg, *, noextname=None):
    # 不需要返回结果，是通过新开 thread 调用
    # if asy:
    #     newcmd = "ffmpeg -hide_banner " + (" ".join(arg) if isinstance(arg, list) else arg)
    #     if config.video['enable_cuda']:
    #         newcmd += "-hwaccel cuda"
    #     logger.info(f"【{noextname}】执行 异步ffmpeg命令：{newcmd}")
    #     res = "ing"
    #     if noextname:
    #         config.queue_novice[noextname] = res
    #     try:
    #         subprocess.run(newcmd, stdout=subprocess.PIPE)
    #         res = "end"
    #         logger.info(f"异步ffmpeg执行成功")
    #     except Exception as e:
    #         res = "error"
    #         logger.error(f"执行异步ffmpeg失败，命令是:{newcmd=}")
    #     if noextname:
    #         config.queue_novice[noextname] = res
    #         logger.info(f"异步ffmpeg 执行外币，设置noextname={noextname}, {config.queue_novice[noextname]=}")
    #     return

    # 需要返回结果： 异步执行 ffmpeg，但同步阻塞等待，直到成功或失败返回
    cmd = "ffmpeg -hide_banner "
    if config.video['enable_cuda']:
        cmd += " -hwaccel cuda "
    if isinstance(arg, list):
        arg = " ".join(arg)
    cmd += arg
    logger.info(f"runffmpeg Will execute: {cmd=}")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    if noextname:
        config.queue_novice[noextname] = 'ing'

    while True:
        try:
            if config.ffmpeg_status == 'stop':
                print("========需要停止")
                set_process(f"ffmpeg停止了")
                p.kill()
            rs = p.wait(1)
            if noextname:
                config.queue_novice[noextname] = "end" if rs==0 else 'error'
            if rs !=0:
                set_process(f"[error]ffmpeg执行结果:失败")
            return True
        except Exception as e:
            print("ffmpeg 等待中:" + str(e))


# 文字合成
def text_to_speech(*, text="", role="", rate=None, filename=None, tts_type=None):
    try:
        if tts_type == "edgeTTS":
            communicate = edge_tts.Communicate(text, role, rate=rate)
            asyncio.run(communicate.save(filename))
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return True
            return None
        elif tts_type == "openaiTTS":
            if not get_voice(text, role, rate, filename):
                logger.error(f"使用openaiTTS合成语音失败")
                open(filename, "w").close()
                return None
    except Exception as e:
        logger.error(f"文字合成出错:{filename=},{tts_type=}," + str(e))
        open(filename, "w").close()


def get_large_audio_transcriptioncli(noextname, mp4ext, showprocess):
    folder_path = config.rootdir + f'/tmp/{noextname}'
    aud_path = folder_path + f"/{noextname}.wav"
    sub_name = folder_path + f"/{noextname}.srt"
    mp4name = f"{noextname}{mp4ext}"
    showprocess(f"{mp4name} spilt audio", "logs")
    if config.current_status == 'stop':
        raise Exception("You stop it.")
    tmp_path = folder_path + f'/##{noextname}_tmp'
    if not os.path.isdir(tmp_path):
        os.makedirs(tmp_path, 0o777, exist_ok=True)
    r = sr.Recognizer()

    if not os.path.exists(sub_name) or os.path.getsize(sub_name) == 0:
        normalized_sound = AudioSegment.from_wav(aud_path)  # -20.0
        total_length = len(normalized_sound) / 1000
        nonslient_file = f'{tmp_path}/detected_voice.json'
        if os.path.exists(nonslient_file):
            with open(nonslient_file, 'r') as infile:
                nonsilent_data = json.load(infile)
        else:
            if config.current_status == 'stop':
                raise Exception("You stop it.")
            nonsilent_data = shorten_voice(normalized_sound)
            showprocess(f"{mp4name} split voice", 'logs')
            with open(nonslient_file, 'w') as outfile:
                json.dump(nonsilent_data, outfile)

        # subtitle
        subs = []
        # all audio chunk
        segments = []
        # every start time
        start_times = []

        # max words every line
        maxlen = 36 if config.video['target_language'][:2] in ["zh", "ja", "jp", "ko"] else 80
        for i, duration in enumerate(nonsilent_data):
            if config.current_status == 'stop':
                raise Exception("You stop it.")
            start_time, end_time, buffered = duration

            start_times.append(start_time)
            logger.info(f"{start_time=},{end_time=},{duration=}")
            time_covered = start_time / len(normalized_sound) * 100
            # 进度
            showprocess(f"{mp4name} {time_covered:.1f}%", 'logs')
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            add_vol = 0
            audio_chunk = normalized_sound[start_time:end_time] + add_vol
            audio_chunk.export(chunk_filename, format="wav")

            # recognize the chunk
            with sr.AudioFile(chunk_filename) as source:
                audio_listened = r.record(source)
                logger.info(f"sr.AudioFile:{chunk_filename=}")
                try:
                    options = {"download_root": config.rootdir + "/models"}
                    text = r.recognize_whisper(audio_listened,
                                               language="zh" if config.video['detect_language'] == "zh-cn" or
                                                                config.video['detect_language'] == "zh-tw" else
                                               config.video['detect_language'],
                                               model=config.video['whisper_model'],
                                               load_options=options)
                except sr.UnknownValueError as e:
                    logger.error("Recognize Error: ", str(e))
                    segments.append(audio_chunk)
                    continue
                except Exception as e:
                    logger.error("Recognize Error:", str(e))
                    segments.append(audio_chunk)
                    continue
                if config.current_status == 'stop':
                    raise Exception("You stop it.")
                text = f"{text.capitalize()}. "
                try:
                    print(f"translate_type============={config.video['translate_type']}")
                    if config.video['translate_type'] == 'google':
                        result = googletrans(text, config.video['source_language'],
                                             config.video['target_language'])
                        print(f"{result=}")
                    elif config.video['translate_type'] == 'baidu':
                        result = baidutrans(text, 'auto', config.video['target_language'])
                    elif config.video['translate_type'] == 'chatGPT':
                        result = chatgpttrans(text)

                    logger.info(f"target_language={config.video['target_language']},[translate ok]\n")
                except Exception as e:
                    logger.error("Translate Error:", str(e))
                    segments.append(audio_chunk)
                    continue
                # exists text vaild
                isemtpy = True
                if not re.fullmatch(r'^[./\\。，/\s]*$', result.strip(), re.I):
                    isemtpy = False
                    combo_txt = result + '\n\n'
                    if len(result) > maxlen:
                        if maxlen == 36:
                            # zh ja ko
                            result_tmp = ""
                            for tmp_i in range(1 + len(result) // maxlen):
                                result_tmp += result[tmp_i * maxlen:tmp_i * maxlen + maxlen] + "\n"
                            combo_txt = result_tmp.strip() + '\n\n'
                        else:
                            # en
                            combo_txt = textwrap.fill(result, maxlen) + "\n\n"
                    if buffered:
                        end_time -= 500
                    start = timedelta(milliseconds=start_time)
                    end = timedelta(milliseconds=end_time)

                    index = len(subs) + 1

                    sub = srt.Subtitle(index=index, start=start, end=end, content=combo_txt)
                    showprocess(f"{start} --> {end} {combo_txt}", 'subtitle')
                    subs.append(sub)

                #  voice role
                if config.video['voice_role'] != 'No':
                    if isemtpy:
                        segments.append(AudioSegment.silent(duration=end_time - start_time))
                        continue
                    try:
                        rate = int(str(config.video['voice_rate']).replace('%', ''))
                        if rate >= 0:
                            rate = f"+{rate}%"
                        else:
                            rate = f"{rate}%"
                        tmpname = f"{folder_path}/tts-{start_time}-{index}.mp3"
                        tts_result = text_to_speech(
                            text=result,
                            role=config.video['voice_role'],
                            rate=rate,
                            filename=tmpname,
                            tts_type=config.video['tts_type'])
                        if not tts_result:
                            showprocess(f"tts合成出错:{result=}", 'logs')
                            segments.append(audio_chunk)
                            continue

                        audio_data = AudioSegment.from_file(tmpname, format="mp3")
                        wavlen = end_time - start_time
                        mp3len = len(audio_data)
                        if config.video['voice_autorate'] and (mp3len - wavlen > 1000):
                            # 最大加速2倍
                            speed = mp3len / wavlen
                            speed = 2 if speed > 2 else speed
                            showprocess(f"new mp3 length bigger than wav ,speed up {speed} ", 'logs')
                            audio_data = speed_change(audio_data, speed)
                            showprocess(f"change after:{len(audio_data)}", 'logs')

                        segments.append(audio_data)
                    except Exception as e:
                        logger.error("Create voice role error:" + str(e))
                        print(e)
                        segments.append(audio_chunk)
        # merge translate audo
        merge_audio_segments(segments, start_times, total_length * 1000, noextname)
        final_srt = srt.compose(subs)
        with open(sub_name, 'w', encoding="utf-8") as f:
            f.write(final_srt)
    showprocess(f"{mp4name} add subtitle", 'logs')
    compos_video(config.video['source_mp4'], noextname)


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


# noextname 是去掉 后缀mp4的视频文件名字
# 所有临时文件保存在 /tmp/noextname文件夹下
# 分批次读取
def recognition_translation_split(noextname):
    set_process("准备分割数据后进行语音识别")
    folder_path = config.rootdir + f'/tmp/{noextname}'
    aud_path = folder_path + f"/{noextname}.wav"
    sub_name = folder_path + f"/{noextname}.srt"
    logger.info(f"{folder_path=}\n{aud_path=}\n{sub_name=}")
    if config.current_status == 'stop':
        raise Exception("You stop it.")
    # create
    # temp dir
    tmp_path = folder_path + f'/##{noextname}_tmp'
    if not os.path.isdir(tmp_path):
        try:
            os.makedirs(tmp_path, 0o777, exist_ok=True)
        except:
            show_popup(transobj["anerror"], transobj["createdirerror"])

    # 已存在字幕文件
    if os.path.exists(sub_name) and os.path.getsize(sub_name) > 0:
        set_process(f"{noextname} 字幕文件已存在，直接使用", 'logs')
        return

    normalized_sound = AudioSegment.from_wav(aud_path)  # -20.0
    nonslient_file = f'{tmp_path}/detected_voice.json'
    if os.path.exists(nonslient_file) and os.path.getsize(nonslient_file):
        with open(nonslient_file, 'r') as infile:
            nonsilent_data = json.load(infile)
    else:
        if config.current_status == 'stop':
            raise Exception("You stop it.")
        nonsilent_data = shorten_voice(normalized_sound)
        set_process(f"{noextname} 对音频文件按静音片段分割处理", 'logs')
        with open(nonslient_file, 'w') as outfile:
            json.dump(nonsilent_data, outfile)


    # subtitle
    subs = []
    r = sr.Recognizer()
    logger.info("for i in nonsilent_data")
    for i, duration in enumerate(nonsilent_data):
        if config.current_status == 'stop':
            raise Exception("You stop it.")
        start_time, end_time, buffered = duration
        logger.info(f"{start_time=},{end_time=},{duration=}")
        time_covered = start_time / len(normalized_sound) * 100
        # 进度
        set_process(f"{noextname} 音频处理进度{time_covered:.1f}%", 'logs')
        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        add_vol = 0
        audio_chunk = normalized_sound[start_time:end_time] + add_vol
        audio_chunk.export(chunk_filename, format="wav")

        # recognize the chunk
        with sr.AudioFile(chunk_filename) as source:
            audio_listened = r.record(source)
            logger.info(f"sr.AudioFile:{chunk_filename=}")
            if config.current_status == 'stop':
                raise Exception("You stop it.")
            try:
                options = {"download_root": config.rootdir + "/models"}
                text = r.recognize_whisper(audio_listened,
                                           language="zh" if config.video['detect_language'] == "zh-cn" or
                                                            config.video['detect_language'] == "zh-tw" else
                                           config.video['detect_language'],
                                           model=config.video['whisper_model'],
                                           load_options=options)
            except sr.UnknownValueError as e:
                logger.error("Recognize Error: ", str(e))
                set_process("[error]:语音识别出错了:" + str(e))
                continue
            except Exception as e:
                logger.error("Recognize Error:", str(e))
                set_process("[error]:语音识别出错了:" + str(e))
                continue
            if config.current_status == 'stop':
                raise Exception("You stop it.")
            text = f"{text.capitalize()}. "
            # 翻译
            try:
                index = len(subs) + 1
                if buffered:
                    end_time -= 500
                start = timedelta(milliseconds=start_time)
                end = timedelta(milliseconds=end_time)
                if config.video['translate_type'] == 'google':
                    result = googletrans(text, config.video['source_language'],
                                         config.video['target_language'])
                elif config.video['translate_type'] == 'baidu':
                    result = baidutrans(text, 'auto', config.video['target_language_baidu'])
                elif config.video['translate_type'] == 'baidu(noKey)':
                    result = baidu_translate_spider_api.baidutrans(text, 'auto', config.video['target_language_baidu'])
                elif config.video['translate_type'] == 'DeepL':
                    result = deepltrans(text, config.video['target_language_deepl'])
                elif config.video['translate_type'] == 'chatGPT':
                    result = chatgpttrans(text)
                    logger.info(f"target_language={config.video['target_language']},[translate ok]\n")
                    sub = srt.Subtitle(index=index, start=start, end=end, content=text)
                    subs.append(sub)
                    continue

                logger.info(f"target_language={config.video['target_language']},[translate ok]\n")
            except Exception as e:
                logger.error("Translate Error:", str(e))
                continue

            combo_txt = result.strip() + "\n\n"
            sub = srt.Subtitle(index=index, start=start, end=end, content=combo_txt)
            subs.append(sub)
            set_process( srt.compose([srt.Subtitle(index=index, start=start, end=end, content=combo_txt)], reindex=False), 'subtitle')
    final_srt = srt.compose(subs)
    if config.video['translate_type'] == 'chatGPT':
        set_process(f"{noextname} 等待 chatGPT 返回响应", 'logs')
        final_srt = chatgpttrans(final_srt)
        if final_srt.startswith('[error]'):
            config.current_status = "stop"
            config.subtitle_end = False
            set_process(f"[error]:{noextname} ChatGPT 翻译出错:{final_srt}", 'logs')
            logger.error(f"[error]:{noextname} ChatGPT 翻译出错:{final_srt}")
            return
        set_process(f"{noextname} chatGPT OK", 'logs')

    #    对字幕进行单行截断操作

    final_srt=subtitle_wrap(final_srt)
    if not final_srt.strip():
        set_process(f"[error]{noextname} 字幕创建失败", 'logs')
        config.current_status = "stop"
        config.subtitle_end = False
        return
    with open(sub_name, 'w', encoding="utf-8") as f:
        f.write(final_srt.strip())
        #     重新填写字幕文本框
        set_process(final_srt.strip(), 'replace_subtitle')

    set_process(f"{noextname} 字幕处理完成，等待修改", 'logs')

def subtitle_wrap(final_srt):
    maxlen = 36 if config.video['target_language'][:2] in ["zh", "ja", "jp", "ko"] else 80
    newsubtitle = []
    number = 0
    for it in re.split(r"\n\s*?\n", final_srt.strip()):
        c = it.strip().split("\n")
        if len(c) < 2:
            logger.error(f"no vail subtitle:{it=}")
            continue
        start, end = c[1].strip().split(" --> ")
        if len(c) < 3:
            continue
        text = "".join(c[2:]).strip()
        if re.match(r'^[.,/\\_@#!$%^&*()?？+=\s，。·、！（【】） -]+$', text):
            continue
        number += 1
        newsubtitle.append(f"{number}\n{start} --> {end}\n{textwrap.fill(text, maxlen)}\n\n")
    final_srt = "".join(newsubtitle).strip()
    return final_srt

# 一次性读取
def recognition_translation_all(noextname):
    folder_path = config.rootdir + f'/tmp/{noextname}'
    audio_path = folder_path + f"/{noextname}.wav"
    sub_name = folder_path + f"/{noextname}.srt"
    model=config.video['whisper_model']
    language=config.video['detect_language']
    set_process(f"准备进行整体语音识别,可能耗时较久，请等待:{model}模型")
    model = whisper.load_model(model, download_root=config.rootdir + "/models")  # Change this to your desired model
    transcribe = model.transcribe(audio_path, language="zh" if language in ["zh-cn", "zh-tw"] else language,)
    segments = transcribe['segments']
    subtitles=""
    for segment in segments:
        startTime = str(0) + str(timedelta(seconds=int(segment['start']))) + ',000'
        endTime = str(0) + str(timedelta(seconds=int(segment['end']))) + ',000'
        text=segment['text'].strip()
        logger.info(f"识别结果:{segment['id'] + 1}\n{startTime} --> {endTime}\n{text}\n")
        set_process(f"识别到字幕：{startTime} --> {endTime}")
        # 无有效字符
        if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$',text) or len(text)<=1:
            continue
        if config.video['translate_type'] == 'chatGPT':
            # 如果是 chatGPT，直接组装字幕
            subtitles += f"{segment['id'] + 1}\n{startTime} --> {endTime}\n{text}\n\n"
            continue
        # 开始翻译
        new_text=text
        if config.video['translate_type'] == 'google':
            new_text = googletrans(text, config.video['source_language'],
                                 config.video['target_language'])
            if new_text.startswith('[error]'):
                time.sleep(3)
                new_text = googletrans(text, config.video['source_language'],config.video['target_language'])
        elif config.video['translate_type'] == 'baidu':
            new_text = baidutrans(text, 'auto', config.video['target_language_baidu'])
        elif config.video['translate_type'] == 'baidu(noKey)':
            new_text = baidu_translate_spider_api.baidutrans(text, 'auto', config.video['target_language_baidu'])
        elif config.video['translate_type'] == 'DeepL':
            new_text = deepltrans(text, config.video['target_language_deepl'])
        current_sub= f"{segment['id'] + 1}\n{startTime} --> {endTime}\n{new_text}\n\n"
        subtitles += current_sub

        set_process(current_sub,'subtitle')

    if config.video['translate_type'] == 'chatGPT':
        set_process(f"等待 chatGPT 返回响应", 'logs')
        subtitles = chatgpttrans(subtitles)
        if subtitles.startswith('[error]'):
            config.current_status = "stop"
            config.subtitle_end = False
            set_process(f"[error]:ChatGPT 翻译出错:{subtitles}", 'logs')
            logger.error(f"[error]:ChatGPT 翻译出错:{subtitles}")
            return
        set_process(f"chatGPT OK", 'logs')

        # newsubtitle = []
        # number = 0
        # for it in re.split(r"\n\s*?\n", subtitles.strip()):
        #     c = it.strip().split("\n")
        #     if len(c) < 2:
        #         logger.error(f"no vail subtitle:{it=}")
        #         continue
        #     start, end = c[1].strip().split(" --> ")
        #     if len(c) < 3:
        #         continue
        #     text = "".join(c[2:]).strip()
        #     if re.match(r'^[.,/\\_@#!$%^&*()?？+=\s，。·、！（【】） -]+$', text):
        #         continue
        #     number += 1
        #     newsubtitle.append(f"{number}\n{start} --> {end}\n{textwrap.fill(text, maxlen)}\n\n")
        # subtitles = "".join(newsubtitle)
    #对字幕单独截断处理
    subtitles=subtitle_wrap(subtitles.strip())
    with open(sub_name, 'w', encoding="utf-8") as f:
        f.write(subtitles.strip())
        set_process(subtitles.strip(), 'replace_subtitle')
    set_process(f"{noextname} 字幕处理完成，等待修改", 'logs')
    return True


# 合并
# source_mp4 原始MP4地址，具体到 后缀
# noextname，无后缀的mp4文件名字
# mp4ext .mp4后缀，可能存在大小写问题
# 配音预处理，去掉无效字符，整理开始时间
def dubbing(noextname):
    # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
    folder_path = config.rootdir + f'/tmp/{noextname}'
    normalized_sound = AudioSegment.from_wav(f"{folder_path}/{noextname}.wav")
    total_length = len(normalized_sound) / 1000
    sub_name = f"{folder_path}/{noextname}.srt"
    tts_wav = f"{folder_path}/tts-{noextname}.wav"
    logger.info(f"准备合成语音 {folder_path=}")
    # 整合一个队列到 exec_tts 执行
    queue_tts = []
    if (config.video['voice_role'] != 'No') and (not os.path.exists(tts_wav) or os.path.getsize(tts_wav) == 0):
        with open(sub_name, "r", encoding="utf-8") as f:

            tx = re.split(r"\n\s*?\n", f.read().strip())
            logger.info(f"Creating TTS wav {tts_wav}")
            for idx, it in enumerate(tx):
                # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
                if config.current_status == 'stop':
                    raise Exception("You stop it.")

                # 0=行号，1=时间信息，2=内容
                c = it.strip().split("\n")
                startraw, endraw = c[1].strip().split(" --> ")
                text = "".join(c[2:]).strip()
                # 无有效内容，跳过
                if not text or len(text)<=1 or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                    continue
                # 转为毫秒
                start = startraw.replace(',', '.').split(":")
                start_time = int(int(start[0]) * 3600000 + int(start[1]) * 60000 + float(start[2]) * 1000)

                end = endraw.replace(',', '.').split(":")
                end_time = int(int(end[0]) * 3600000 + int(end[1]) * 60000 + float(end[2]) * 1000)

                rate = int(str(config.video['voice_rate']).replace('%', ''))
                if rate >= 0:
                    rate = f"+{rate}%"
                else:
                    rate = f"{rate}%"
                queue_tts.append({
                    "text": text,
                    "role": config.video['voice_role'],
                    "start_time": start_time,
                    "end_time": end_time,
                    "rate": rate,
                    "startraw": startraw,
                    "endraw": endraw,
                    "filename": f"{folder_path}/tts-{start_time}.mp3"})
        exec_tts(queue_tts, total_length, noextname)


# 执行tts并行
def exec_tts(queue_tts, total_length, noextname):
    queue_copy = copy.deepcopy(queue_tts)
    set_process(f"准备进行 {config.video['tts_type']} 语音合成，角色:{config.video['voice_role']}", 'logs')

    def get_item(q):
        return {"text": q['text'], "role": q['role'], "rate": q['rate'], "filename": q["filename"],
                "tts_type": config.video['tts_type']}

    # 需要并行的数量3
    while len(queue_tts) > 0:
        tolist = [threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0)))]
        if len(queue_tts) > 0:
            tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))
        if len(queue_tts) > 0:
            tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))

        for t in tolist:
            t.start()
        for t in tolist:
            t.join()
    segments = []
    start_times = []
    try:
        for it in queue_copy:
            start_times.append(it['start_time'])
            if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                set_process(f"[error]: 此 {it['startraw']} - {it['endraw']} 时间段内字幕合成语音失败", 'logs')
                continue
            audio_data = AudioSegment.from_file(it['filename'], format="mp3")
            wavlen = it['end_time'] - it['start_time']
            mp3len = len(audio_data)
            if wavlen>0 and  mp3len - wavlen:
                speed = mp3len / wavlen
                speed = 2 if speed > 2 else speed
                # 音频加速 最大加速2倍
                if config.video['voice_autorate']:
                    logger.info(f"new mp3 length bigger than wav ,speed up {speed} ")
                    audio_data = speed_change(audio_data, speed)
                    logger.info(f"change after:{len(audio_data)}")

            segments.append(audio_data)
        merge_audio_segments(segments, start_times, total_length * 1000, noextname)
    except Exception as e:
        logger.error("exec_tts 出错了？？？" + str(e))
        set_process(f"[error]合成语音有出错:" + str(e))


# 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
def compos_video(source_mp4, noextname):
    folder_path = config.rootdir + f'/tmp/{noextname}'
    sub_name = f"{folder_path}/{noextname}.srt"
    tts_wav = f"{folder_path}/tts-{noextname}.wav"
    source_wav = f"{folder_path}/{noextname}.wav"
    # target  output mp4 filepath
    target_mp4 = f"{config.video['target_dir']}/{noextname}.mp4"
    set_process(f"合并后将创建到 {target_mp4}")
    if not os.path.exists(f"{config.video['target_dir']}/srt"):
        os.makedirs(f"{config.video['target_dir']}/srt", exist_ok=True)
    shutil.copy(sub_name, f"{config.video['target_dir']}/srt/{noextname}.srt")
    logger.info("准备完毕，开始合成视频，" + target_mp4 + "  " + source_mp4)
    embed_srt = None
    # 预先创建好的
    novoice_mp4 = f"{folder_path}/novoice.mp4"
    # 判断novoice_mp4是否完成
    while True:
        if noextname not in config.queue_novice:
            msg = f"抱歉，视频{noextname} 预处理 novoice 失败,请重试"
            set_process(msg)
            raise Exception(msg)
        if config.queue_novice[noextname] == 'error':
            msg = f"抱歉，视频{noextname} 预处理 novoice 失败"
            set_process(msg)
            raise Exception(msg)

        if config.queue_novice[noextname] == 'ing':
            set_process(f"{noextname} 所需资源未准备完毕，请稍等..{config.queue_novice[noextname]=}")
            logger.info(f"{noextname} 所需资源未准备完毕，请稍等..")
            time.sleep(3)
            continue
        break

    # 需要配音
    if config.video['voice_role'] != 'No':
        if not os.path.exists(tts_wav) or os.path.getsize(tts_wav) == 0:
            set_process(f"[error] 配音文件创建失败: {tts_wav}", 'logs')
            logger.error(f"{transobj['hechengchucuo']} {tts_wav=},size={os.path.getsize(tts_wav)}")
            return
    # 需要字幕
    if config.video['subtitle_type'] > 0 and (not os.path.exists(sub_name) or os.path.getsize(sub_name) == 0):
        set_process(f"[error]未创建成功有效的字幕文件 {sub_name}", 'logs')
        logger.error(f"{transobj['hechengchucuo']} {sub_name=}")
        return
    if config.video['subtitle_type'] == 1:
        # 硬字幕
        embed_srt = f"{config.rootdir}/{noextname}.srt"
        shutil.copy(sub_name, embed_srt)

    # 有字幕有配音
    if config.video['voice_role'] != 'No' and config.video['subtitle_type'] > 0:
        if config.video['subtitle_type'] == 1:
            logger.info(f"合成配音+硬字幕")
            set_process(f"{noextname} 合成配音+硬字幕")
            # 需要配音+硬字幕
            runffmpeg([
                "-y",
                "-i",
                f'"{novoice_mp4}"',
                "-i",
                f'"{tts_wav}"',
                "-c:v",
                "libx264",
                # "libx264",
                "-c:a",
                "aac",
                # "pcm_s16le",
                "-vf",
                f"subtitles={noextname}.srt",
                f'"{target_mp4}"'
            ])
        else:
            logger.info(f"合成配音+软字幕")
            set_process(f"{noextname} 合成配音+软字幕")
            # 配音+软字幕
            runffmpeg([
                "-y",
                "-i",
                f'"{novoice_mp4}"',
                "-i",
                f'"{tts_wav}"',
                "-sub_charenc",
                "UTF-8",
                "-f",
                "srt",
                "-i",
                f'"{sub_name}"',
                "-c:v",
                "libx264",
                # "libx264",
                "-c:a",
                "aac",
                "-c:s",
                "mov_text",
                "-metadata:s:s:0",
                f"language={config.video['subtitle_language']}",
                f'"{target_mp4}"'
            ])
    elif config.video['voice_role'] != 'No':
        # 配音无字幕
        logger.info(f"合成配音+无字幕")
        set_process(f"{noextname} 合成配音，无字幕")
        runffmpeg([
            "-y",
            "-i",
            f'"{novoice_mp4}"',
            "-i",
            f'"{tts_wav}"',
            "-c:v",
            "copy",
            # "libx264",
            "-c:a",
            "aac",
            # "pcm_s16le",
            f'"{target_mp4}"'
        ])
    # 无配音 使用 novice.mp4 和 原始 wav合并
    elif config.video['subtitle_type'] == 1:
        # 硬字幕无配音 将原始mp4复制到当前文件夹下
        logger.info(f"合成硬字幕无配音")
        set_process(f"{noextname} 合成硬字幕，无配音")
        runffmpeg([
            "-y",
            "-i",
            f'"{novoice_mp4}"',
            "-i",
            f'"{source_wav}"',
            "-c:v",
            "libx264",
            # "libx264",
            "-c:a",
            "aac",
            # "pcm_s16le",
            "-vf",
            f"subtitles={noextname}.srt",
            f'"{target_mp4}"',
        ])
    elif config.video['subtitle_type'] == 2:
        # 软字幕无配音
        logger.info(f"合成软字幕")
        set_process(f"{noextname} 合成软字幕，无配音")
        runffmpeg([
            "-y",
            "-i",
            f'"{novoice_mp4}"',
            "-i",
            f'"{source_wav}"',
            "-sub_charenc",
            "UTF-8",
            "-f",
            "srt",
            "-i",
            f'"{sub_name}"',
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            # "libx264",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            f"language={config.video['subtitle_language']}",
            f'"{target_mp4}"'
        ])
    if embed_srt and os.path.exists(embed_srt):
        os.unlink(embed_srt)
    set_process(f"{noextname} 视频合成完毕")


# 写入日志队列
def set_process(text, type="logs"):
    try:
        text = text.replace('[error]','<span style="color:#f00">出错:</span>')+"<br>" if type == "logs" else text
        queue_logs.put_nowait({"text": text, "type": type})
    except:
        pass
