# -*- coding: utf-8 -*-
import asyncio
import hashlib
import re
import shutil
import subprocess
import time
import urllib.parse
import httpx
import requests
import speech_recognition as sr
import os
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import srt
from datetime import timedelta
import json
import edge_tts
import openai
import textwrap
import math
import sys
import random

from urllib.parse import quote
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

from . import config
from .config import logger

# windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


# delete tmp files
def delete_temp(dirname="", noextname=""):
    if os.path.exists(f"{config.rootdir}/tmp"):
        shutil.rmtree(f"{config.rootdir}/tmp")
    if os.path.exists(f"{dirname}/{noextname}vocals.wav"):
        os.unlink(f"{dirname}/{noextname}vocals.wav")
    if os.path.exists(f"{dirname}/{noextname}accompaniment.wav"):
        os.unlink(f"{dirname}/{noextname}accompaniment.wav")
    if os.path.exists(f"{dirname}/##{noextname}vocals_tmp"):
        shutil.rmtree(f"{dirname}/##{noextname}vocals_tmp")
    if os.path.exists(f"{dirname}/{noextname}.wav"):
        os.unlink(f"{dirname}/{noextname}.wav")
    if os.path.exists(f"{dirname}/##{noextname}_tmp"):
        shutil.rmtree(f"{dirname}/##{noextname}_tmp")


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
def merge_audio_segments(segments, start_times, total_duration, mp4name):
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
    merged_audio.export(f"{config.rootdir}/tmp/{mp4name}.wav", format="wav")
    return merged_audio


# google api
def googletrans(text, src, dest):
    url = f"https://translate.google.com/m?sl={urllib.parse.quote(src)}&tl={urllib.parse.quote(dest)}&hl={urllib.parse.quote(dest)}&q={urllib.parse.quote(text)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    proxies = None
    if config.video['proxy']:
        proxies = {
            'http': config.video['proxy'],
            'https': config.video['proxy']
        }
    # example
    # proxies = {
    #     'http': 'http://127.0.0.1:10809',
    #     'https': 'http://127.0.0.1:10809'
    # }
    try:
        response = requests.get(url, proxies=proxies, headers=headers, timeout=40)
        if response.status_code != 200:
            return f"error translation code={response.status_code}"
        re_result = re.findall(
            r'(?s)class="(?:t0|result-container)">(.*?)<', response.text)
    except:
        return "[error google api] Please check the connectivity of the proxy or consider changing the IP address."
    return "error on translation" if len(re_result) < 1 else re_result[0]

# baidu translate
def baidutrans(text,src,dest):
    # 拼接appid = 2015063000000001 + q = apple + salt = 1435660288 + 密钥 = 12345678
    salt=int(time.time())
    strtext=f"{config.video['baidu_appid']}{text}{salt}{config.video['baidu_miyue']}"
    print(f"====baidu api translate")
    md5 = hashlib.md5()
    md5.update(strtext.encode('utf-8'))
    sign = md5.hexdigest()
    try:
        res=requests.get(f"http://api.fanyi.baidu.com/api/trans/vip/translate?q={text}&from=auto&to={dest}&appid={config.video['baidu_appid']}&salt={salt}&sign={sign}")
        res=res.json()
        if "error_code" in res:
            return "baidu api error:"+res['error_msg']
        comb=""
        for it in res['trans_result']:
            comb+=it['dst']
        return comb
    except Exception as e:
        return "baidu api error:"+str(e)
########### 百度翻译

# 获取百度翻译的cookie和token
# This is the 2.11 Requests cipher string, containing 3DES.
CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)
def get_baiducookie_token(max_try_nums=3):
    """:type
    max_try_nums : 最大重试次数
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{}.0.4472.124 Safari/537.36'.format(random.choice([100,101,102,103,104,105,106]))
    }

    session = requests.Session()
    session.get("http://www.baidu.com",headers=headers)
    res = session.get("https://fanyi.baidu.com/?aldtype=85#zh/en/%E4%BB%8A%E5%A4%A9%E6%98%AF%E4%B8%AA%E5%BC%80%E5%BF%83%E7%9A%84%E6%97%A5%E5%AD%90",headers=headers)
    BAIDUID = re.findall(r"BAIDUID_BFESS=(.*?):",res.headers.get("Set-Cookie",""))
    token = re.findall(r"token: '(.*)'",res.text)
    if max_try_nums<0:
        return "",""
    if not bool(BAIDUID) or not bool(token): # 有一个没取到都会有问题
        return get_baiducookie_token(max_try_nums=max_try_nums-1)
    return BAIDUID[0] ,token[0]

# 获取百度翻译的sign
def baidufanyi_sign(src):

    def a(r):
        if isinstance(r, list):
            t = [0] * len(r)
            for o in range(len(r)):
                t[o] = r[o]
            return t
        return list(r)

    def n(r, o):
        for t in range(0, len(o) - 2, 3):
            a = o[t + 2]
            a = ord(a) - 87 if a >= "a" else int(a)
            a = r >> a if o[t + 1] == "+" else r << a
            r = r + a & 4294967295 if o[t] == "+" else r ^ a
        return r

    def e(r):
        o = re.findall(r'[\uD800-\uDBFF][\uDC00-\uDFFF]', r)
        if o is None:
            t = len(r)
            if t > 30:
                r = "" + r[:10] + r[math.floor(t / 2) - 5:math.floor(t / 2) + 5] + r[-10:]
        else:
            e = re.split(r'[\uD800-\uDBFF][\uDC00-\uDFFF]', r)
            f = []
            for C in range(len(e)):
                if e[C] != "":
                    f.extend(a(list(e[C])))
                if C != len(e) - 1:
                    f.append(o[C])
            g = len(f)
            if g > 30:
                r = ''.join(f[:10]) + ''.join(f[math.floor(g / 2) - 5:math.floor(g / 2) + 5]) + ''.join(f[-10:])

        u = None
        l = "" + chr(103) + chr(116) + chr(107)
        u = i if i is not None else "320305.131321201" or ""
        d = u.split(".")
        m = int(d[0]) if d[0] else 0
        s = int(d[1]) if d[1] else 0
        S = []
        c = 0
        for v in range(len(r)):
            A = ord(r[v])
            if A < 128:
                S.append(A)
            else:
                if A < 2048:
                    S.append(A >> 6 | 192)
                else:
                    if 55296 == (64512 & A) and v + 1 < len(r) and 56320 == (64512 & ord(r[v + 1])):
                        A = 65536 + ((1023 & A) << 10) + (1023 & ord(r[v + 1]))
                        S.append(A >> 18 | 240)
                        S.append(A >> 12 & 63 | 128)
                        v += 1
                    else:
                        S.append(A >> 12 | 224)
                        S.append(A >> 6 & 63 | 128)
                S.append(63 & A | 128)

        p = m
        F = "" + chr(43) + chr(45) + chr(97) + ("" + chr(94) + chr(43) + chr(54))
        D = "" + chr(43) + chr(45) + chr(51) + ("" + chr(94) + chr(43) + chr(98)) + ("" + chr(43) + chr(45) + chr(102))
        for b in range(len(S)):
            p += S[b]
            p = n(p, F)
        p = n(p, D)
        p ^= s
        if p < 0:
            p = (2147483647 & p) + 2147483648
        p %= 1000000
        return str(p) + "." + str(p ^ m)

    i = None
    return e(src)

# ja3指纹验证 高版本python urllib3 不兼容低版本的简单处理方案 urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
class DESAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).proxy_manager_for(*args, **kwargs)
# 百度翻译 api
def baidutrans(text, src, dest):
    session = requests.Session()

    session.mount('https://fanyi.baidu.com', DESAdapter())


    session.proxies = None
    if config.video.get("proxy",""):
        proxies = {
            'http': config.video['proxy'],
            'https': config.video['proxy']
        }
        session.proxies = proxies

    sign = baidufanyi_sign(text)
    BAIDUID,token = get_baiducookie_token()
    # print(sign,BAIDUID,token)
    url = "https://fanyi.baidu.com/v2transapi"

    payload = f"from={src}&to={dest}&query={quote(text)}&transtype=realtime&simple_means_flag=3&sign={sign}&token={token}&domain=common"
    headers = {
        'authority': 'fanyi.baidu.com',
        'accept': '*/*',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://fanyi.baidu.com',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://fanyi.baidu.com/translate?aldtype=16047&query=&keyfrom=baidu&smartresult=dict&lang=auto2zh',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cookie': f'BIDUPSID={BAIDUID}; BAIDUID={BAIDUID}:FG=1;'
    }

    try:

        response = session.post(url, headers=headers, data=payload,timeout=6)
        # print(response.json())
        if response.status_code != 200:
            return f"error translation code={response.status_code}"
        re_result = response.json().get("trans_result",{}).get("data",[])
        # print("re_result",re_result)
    except:
        return "[error google api] Please check the connectivity of the proxy or consider changing the IP address."
    return "error on translation" if len(re_result) < 1 else re_result[0].get("dst","")

##########

# by chatGPT
def chatgpttrans(text):
    if re.match(r'^[.,=_?!@#$%^&*()+\s -]+$',text):
        return text
    if config.video['proxy']:
        proxies = {
            'http': 'http://%s' % config.video['proxy'].replace("http://",''),
            'https': 'http://%s' % config.video['proxy'].replace("http://",'')
        }
        # openai.proxy = proxies
    if config.video['chatgpt_api']:
        openai.api_base=config.video['chatgpt_api']
    openai.api_key=config.video['chatgpt_key']

    print(f"openai.base=={openai.api_base}")

    messages = [
        {'role': 'system',
         'content':f"  You are a professional translation engine, please translate the text into a concise,  elegant and fluent content, without referencing machine translations.   You must only translate the text, never interpret it. Translate to {config.video['target_language_chatgpt']}, If translation is not possible or there are errors in the translation, do not i am sorry, do not prompt for errors, and directly force the translation" },
        {'role': 'user', 'content': f"{text}\n"},
    ]
    print(messages)
    try:
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=messages,
            max_tokens=2048
        )
    except Exception as e:
        return f"chatgpt translate error:"+str(e)
    if response['code']!=0 and response['message']:
        return response['message']
    data=response.data
    print(data)
    for choice in data.choices:
        if 'text' in choice:
            return choice.text
    result= data.choices[0].message.content.strip()
    if re.match(r"Sorry, but I'm unable to translate the content",result,re.I):
        return "no translate"
    return result


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


def runffmpeg(*arg):
    logger.info("Will execute: ffmpeg " + " ".join(arg))
    try:
        subprocess.run("ffmpeg " + " ".join(arg), check=True, shell=True)
    except Exception as e:
        logger.error("FFmepg exec error:" + str(e))


#
def get_large_audio_transcription(aud_path, mp4name, sub_name, showprocess):
    # raw video directory
    folder_path = '/'.join(aud_path.split('/')[:-1])
    # no ext audio name use create tmp dir
    audio_name = aud_path.split('/')[-1][:-4]
    logger.info(f"[get_large_audio_transcription] {aud_path=}\n{folder_path=}\n{audio_name=}\n{sub_name=}")
    # temp dir
    tmp_path = folder_path + f'/##{audio_name}_tmp'
    showprocess(f"{mp4name} spilt audio", "logs")
    if config.current_status == 'stop':
        return
    if not os.path.isdir(tmp_path):
        os.makedirs(tmp_path, 0o777, exist_ok=True)
    r = sr.Recognizer()

    if os.path.exists(sub_name):
        os.unlink(sub_name)

    normalized_sound = AudioSegment.from_wav(aud_path)  # -20.0
    total_length = len(normalized_sound) / 1000
    nonslient_file = f'{tmp_path}/detected_voice.json'
    if os.path.exists(nonslient_file):
        with open(nonslient_file, 'r') as infile:
            nonsilent_data = json.load(infile)
    else:
        if config.current_status == 'stop':
            return
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
    maxlen = 36 if config.video['target_language'][:2] in ["zh", "ja","jp", "ko"] else 80
    for i, duration in enumerate(nonsilent_data):
        if config.current_status == 'stop':
            return
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
                return
            text = f"{text.capitalize()}. "
            try:
                print(f"translate_type============={config.video['translate_type']}")
                if config.video['translate_type']=='google':
                    result = googletrans(text, config.video['source_language'],
                                         config.video['target_language'])
                elif config.video['translate_type']=='baidu':
                    result = baidutrans(text, 'auto', config.video['target_language'])
                elif config.video['translate_type']=='chatGPT':
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
                    if maxlen==36:
                        #zh ja ko
                        result_tmp = ""
                        for tmp_i in range(1 + len(result) // maxlen):
                            result_tmp += result[tmp_i * maxlen:tmp_i * maxlen + maxlen] + "\n"
                        combo_txt = result_tmp.strip() + '\n\n'
                    else:
                        #en
                        combo_txt=textwrap.fill(result,maxlen)+"\n\n"
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
                    tmpname = f"{config.rootdir}/tmp/{start_time}-{index}.mp3"
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
    merge_audio_segments(segments, start_times, total_length * 1000, mp4name)
    final_srt = srt.compose(subs)
    with open(sub_name, 'w', encoding="utf-8") as f:
        f.write(final_srt)
    showprocess(f"{mp4name} add subtitle", 'logs')

    # target  output mp4 filepath
    target_mp4 = config.video['target_dir'] + f"/{mp4name}"
    # raw mp4 filepath
    source_mp4 = folder_path + f"/{mp4name}"
    logger.info(f"{target_mp4=}\n{source_mp4=}")
    # has voice role and create novoice mp4
    if config.video['voice_role'] != 'No':
        runffmpeg(f"-y -i {source_mp4} -c:v copy -an {config.rootdir}/tmp/novoice_{mp4name}")

    if config.video['voice_role'] != 'No' and config.video['subtitle_type'] > 0:
        # embed subtitle
        if config.video['subtitle_type'] == 1:
            shutil.copy(sub_name, f"{config.rootdir}/{mp4name}.srt")
            runffmpeg(
                f"-y -i {config.rootdir}/tmp/novoice_{mp4name}  -i {config.rootdir}/tmp/{mp4name}.wav  -c:v libx264 -c:a aac -vf subtitles={mp4name}.srt {target_mp4}")
        else:
            # soft subtitle
            runffmpeg(
                f"-y -i {config.rootdir}/tmp/novoice_{mp4name}  -i {config.rootdir}/tmp/{mp4name}.wav -sub_charenc UTF-8 -f srt  -i {sub_name} -c:v libx264 -c:a aac -c:s mov_text -metadata:s:s:0 language={config.video['subtitle_language']} {target_mp4}")
    elif config.video['voice_role'] != 'No':
        # only voice dubbing no subtitle
        runffmpeg(
            f"-y -i {config.rootdir}/tmp/novoice_{mp4name}  -i {config.rootdir}/tmp/{mp4name}.wav  -c:v libx264 -c:a aac  {target_mp4}")
    # inert subtitle
    elif config.video['subtitle_type'] == 1:
        # no voice dubble only  embed subtitle
        shutil.copy(sub_name, f"{config.rootdir}/{mp4name}.srt")
        runffmpeg(
            f"-y -i {source_mp4}  -c:v libx264 -c:a aac -vf subtitles={mp4name}.srt {target_mp4}")
    elif config.video['subtitle_type'] == 2:
        # no voice dubble only soft subtitle
        runffmpeg(
            f"-y -i {source_mp4} -sub_charenc UTF-8 -f srt -i {sub_name} -c:v libx264  -c:s mov_text -metadata:s:s:0 language={config.video['subtitle_language']} {target_mp4}")
    showprocess(f"{mp4name}.mp4 ended", 'logs')


# 测试 google
def testproxy(proxy):
    if not proxy:
        proxy = None
    status = False
    try:
        with httpx.Client(proxies=proxy) as client:
            r = client.get('https://www.google.com', timeout=30)
            logger.info(f'google.com code={r.status_code=}')
            if r.status_code == 200:
                status = True
    except Exception as e:
        logger.error(str(e))
    return status
