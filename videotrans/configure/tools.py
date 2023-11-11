# -*- coding: utf-8 -*-

import asyncio
import re
import shutil
import subprocess
import sys
import time

import speech_recognition as sr
import os
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
from .config import logger, transobj

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


if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


# delete tmp files
def delete_temp(noextname=""):
    if noextname and os.path.exists(f"{config.rootdir}/tmp/{noextname}"):
        shutil.rmtree(f"{config.rootdir}/tmp/{noextname}")


#  get role by edge tts
def get_list_voices():
    voice_list = {}
    if os.path.exists(config.rootdir + "/voice_list.json"):
        try:
            voice_list = json.load(open(config.rootdir + "/voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
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


def runffmpeg(arg):
    logger.info("Will execute: ffmpeg " + " ".join(arg))
    cmd = "ffmpeg "
    if config.video['enable_cuda']:
        cmd += " -hwaccel cuda "
    if isinstance(arg, list):
        cmd += " ".join(arg)
    else:
        cmd += arg
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)

    while True:
        try:
            if config.current_status == 'stop':
                p.kill()
                return
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

    if os.path.exists(sub_name) or os.path.getsize(sub_name) == 0:
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
                        communicate = edge_tts.Communicate(result,
                                                           config.video['voice_role'],
                                                           rate=rate)
                        tmpname = f"{folder_path}/tts-{start_time}-{index}.mp3"
                        asyncio.run(communicate.save(tmpname))

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
    compos_video(config.video['source_mp4'], noextname, showprocess)


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
def get_large_audio_transcription(noextname, showprocess):
    folder_path = config.rootdir + f'/tmp/{noextname}'
    aud_path = folder_path + f"/{noextname}.wav"
    sub_name = folder_path + f"/{noextname}.srt"
    logger.info(f"{folder_path=}\n{aud_path=}\n{sub_name=}")
    showprocess(f"{noextname} spilt audio", "logs")
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
        showprocess(f"{noextname} subtitle has exits, wait edit subtitle", 'logs')
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
        showprocess(f"{noextname} split voice", 'logs')
        with open(nonslient_file, 'w') as outfile:
            json.dump(nonsilent_data, outfile)

    maxlen = 36 if config.video['target_language'][:2] in ["zh", "ja", "jp", "ko"] else 80
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
        showprocess(f"{noextname} {time_covered:.1f}%", 'logs')
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
                showprocess("whisper error:" + str(e))
                continue
            except Exception as e:
                logger.error("Recognize Error:", str(e))
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
                    logger.info(f"target_language={config.video['target_language']},[translate ok]\n")
                    sub = srt.Subtitle(index=index, start=start, end=end, content=text)
                    subs.append(sub)
                    continue

                logger.info(f"target_language={config.video['target_language']},[translate ok]\n")
            except Exception as e:
                logger.error("Translate Error:", str(e))
                continue

            combo_txt = textwrap.fill(result.strip(), maxlen) + "\n\n"
            sub = srt.Subtitle(index=index, start=start, end=end, content=combo_txt)
            subs.append(sub)
            showprocess(
                srt.compose([srt.Subtitle(index=index, start=start, end=end, content=combo_txt)], reindex=False),
                'subtitle')
    final_srt = srt.compose(subs)
    if config.video['translate_type'] == 'chatGPT':
        showprocess(f"{noextname} wait chatGPT response", 'logs')
        final_srt = chatgpttrans(final_srt)
        if final_srt.startswith('[error]'):
            showprocess(f"{noextname} ChatGPT error:{final_srt}", 'logs')
            logger.error(f"{noextname} ChatGPT error:{final_srt}")
            # show_popup("ChatGPT error", final_srt)
            return
        showprocess(f"{noextname} chatGPT OK", 'logs')
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
        final_srt = "".join(newsubtitle)
    with open(sub_name, 'w', encoding="utf-8") as f:
        f.write(final_srt)
        #     重新填写字幕文本框
        showprocess(final_srt, 'replace_subtitle')

    showprocess(f"{noextname} wait edit subtitle", 'logs')


# 合并
# source_mp4 原始MP4地址，具体到 后缀
# noextname，无后缀的mp4文件名字
# mp4ext .mp4后缀，可能存在大小写问题
def dubbing(noextname, showprocess):
    # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
    folder_path = config.rootdir + f'/tmp/{noextname}'
    normalized_sound = AudioSegment.from_wav(f"{folder_path}/{noextname}.wav")
    total_length = len(normalized_sound) / 1000
    sub_name = f"{folder_path}/{noextname}.srt"
    tts_wav = f"{folder_path}/tts-{noextname}.wav"
    # all audio chunk
    segments = []
    # every start time
    start_times = []
    logger.info(f"准备合成语音 {folder_path=}")
    if (config.video['voice_role'] != 'No') and (not os.path.exists(tts_wav) or os.path.getsize(tts_wav) == 0):
        with open(sub_name, "r", encoding="utf-8") as f:
            showprocess(f"Creating TTS wav {tts_wav}", 'logs')
            tx = re.split(r"\n\s*?\n", f.read().strip())
            logger.info(f"Creating TTS wav {tts_wav}")
            for idx, it in enumerate(tx):
                # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
                if config.current_status == 'stop':
                    raise Exception("You stop it.")

                # 0=行号，1=时间信息，2=内容
                c = it.strip().split("\n")
                start, end = c[1].strip().split(" --> ")
                showprocess(f"subtitle:{start} --> {end}", "logs")
                text = "".join(c[2:]).strip()
                print(f"text====={text}")
                # 无有效内容，跳过
                if re.match(r'^[.,/\\_@#!$%^&*()?？+=\s，。·、！（【】） -]+$', text):
                    continue
                # 转为毫秒
                start = start.replace(',', '.').split(":")
                start_time = int(int(start[0]) * 3600000 + int(start[1]) * 60000 + float(start[2]) * 1000)

                end = end.replace(',', '.').split(":")
                end_time = int(int(end[0]) * 3600000 + int(end[1]) * 60000 + float(end[2]) * 1000)
                start_times.append(start_time)
                # 不是最后一个，则取出下一个的开始时间
                try:
                    rate = int(str(config.video['voice_rate']).replace('%', ''))
                    if rate >= 0:
                        rate = f"+{rate}%"
                    else:
                        rate = f"{rate}%"
                    print(f"start->edge_tts->{idx}")
                    communicate = edge_tts.Communicate(text,
                                                       config.video['voice_role'],
                                                       rate=rate
                                                       )
                    tmpname = f"{folder_path}/tts-{start_time}.mp3"
                    asyncio.run(communicate.save(tmpname))
                    print(f"end=>edge_tts->{idx}")

                    if not os.path.exists(tmpname) or os.path.getsize(tmpname) == 0:
                        segments.append(AudioSegment.silent(duration=end_time - start_time))
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
                    segments.append(AudioSegment.silent(duration=end_time - start_time))
        # merge translate audo
        merge_audio_segments(segments, start_times, total_length * 1000, noextname)


# 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
def compos_video(source_mp4, noextname, showprocess):
    folder_path = config.rootdir + f'/tmp/{noextname}'
    sub_name = f"{folder_path}/{noextname}.srt"
    tts_wav = f"{folder_path}/tts-{noextname}.wav"
    # target  output mp4 filepath
    target_mp4 = f"{config.video['target_dir']}/{noextname}.mp4"
    if not os.path.exists(f"{config.video['target_dir']}/srt"):
        os.makedirs(f"{config.video['target_dir']}/srt", exist_ok=True)
    shutil.copy(sub_name, f"{config.video['target_dir']}/srt/{noextname}.srt")
    logger.info("准备完毕，开始合成视频，" + target_mp4 + "  " + source_mp4)
    novoice_mp4 = None
    embed_srt = None
    novoice_mp4 = f"{folder_path}/novoice.mp4"
    # 需要配音
    if config.video['voice_role'] != 'No':
        if not os.path.exists(tts_wav) or os.path.getsize(tts_wav) == 0:
            print(f"判断tts wav是否存在{tts_wav=}")
            showprocess(f"{transobj['hechengchucuo']} {tts_wav}", 'logs')
            logger.error(f"{transobj['hechengchucuo']} {tts_wav=},size={os.path.getsize(tts_wav)}")
            return
        runffmpeg([
            "-y",
            "-i",
            f'"{source_mp4}"',
            "-c:v",
            # "libx264",
            "copy",
            "-an",
            f'"{novoice_mp4}"'
        ])

    if config.video['subtitle_type'] > 0 and (not os.path.exists(sub_name) or os.path.getsize(sub_name) == 0):
        showprocess(f"{transobj['hechengchucuo']} {sub_name}", 'logs')
        logger.error(f"{transobj['hechengchucuo']} {sub_name=}")
        return
    if config.video['subtitle_type'] == 1:
        # 硬字幕
        embed_srt = f"{config.rootdir}/{noextname}.srt"
        shutil.copy(sub_name, embed_srt)
    print(f"开始合成，voice_role={config.video['voice_role']},subtitle_type={config.video['subtitle_type']}")
    if config.video['voice_role'] != 'No' and config.video['subtitle_type'] > 0:
        if config.video['subtitle_type'] == 1:
            logger.info(f"合成配音+硬字幕")
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
    # 无配音
    elif config.video['subtitle_type'] == 1:
        # 硬字幕无配音 将原始mp4复制到当前文件夹下
        logger.info(f"合成硬字幕无配音")
        runffmpeg([
            "-y",
            "-i",
            f'"{source_mp4}"',
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
        runffmpeg([
            "-y",
            "-i",
            f'"{source_mp4}"',
            "-sub_charenc",
            "UTF-8",
            "-f",
            "srt",
            "-i",
            f'"{sub_name}"',
            "-c:v",
            "libx264",
            # "libx264",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            f"language={config.video['subtitle_language']}",
            f'"{target_mp4}"'
        ])
    if embed_srt and os.path.exists(embed_srt):
        os.unlink(embed_srt)
