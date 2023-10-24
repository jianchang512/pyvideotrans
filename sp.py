import asyncio
import re
import shutil
import sys
import webbrowser
import httpx
import speech_recognition as sr
import os
import time
from PySimpleGUI import ErrorElement
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from googletrans import Translator
import PySimpleGUI as sg
import srt
from datetime import timedelta
import glob
import json
from tkinter.filedialog import askdirectory
from tkinter import messagebox
import threading
from config import qu, rootdir, langlist, videolist, timelist, current_status, ishastart, video_config, task_nums, \
    task_threads, layout, voice_list, transobj
import edge_tts

sg.user_settings_filename(path='.')

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


#  获取 支持的语音角色列表
def get_list_voices():
    global voice_list
    v = asyncio.run(edge_tts.list_voices())
    for it in v:
        name = it['ShortName']
        prefix = name.split('-')[0].lower()
        if prefix not in voice_list:
            voice_list[prefix] = ["None", name]
        else:
            voice_list[prefix].append(name)
get_list_voices()
# 根据视频完整路径 返回 字幕文件的路径
def get_thd_min_silence(p):
    thd = 25  # larger more sensitive
    min_silence_len = 1000
    sub_name = p[:-3] + "srt"
    return thd, min_silence_len, sub_name


# 返回切分的音频片段
def shorten_voice(nonsilent_data, max_interval=10000):
    new_data = []
    buffer_time = 2000
    for start_time, end_time in nonsilent_data:
        while end_time - start_time >= max_interval:
            new_end = start_time + max_interval + buffer_time
            new_start = start_time
            new_data.append((new_start, new_end, True))
            start_time += max_interval
        new_data.append((start_time, end_time, False))
    return new_data


# 调整分贝
def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


# 添加字幕，将视频 source_mp4 添加字幕 sub_name 后输出 target_mp4   mp4name=带后缀视频名
# source_mp4 原始mp4完整路径，target_mp4目标存储mp4完整路径 sub_name字幕文件完整路径，mp4name带mp4后缀的原始名
def addsubtitle(source_mp4=None, target_mp4=None, sub_name=None, mp4name=None):
    global videolist
    # 软字幕
    ispeiyin = video_config['voice_replace']
    if ispeiyin != 'None':
        os.system(f"ffmpeg -y -i {source_mp4} -c:v copy -an ./tmp/novoice_{mp4name}")
        os.system(
            f"ffmpeg -y -i ./tmp/novoice_{mp4name} -i ./tmp/{mp4name}.wav -c copy -map 0:v:0 -map 1:a:0 ./tmp/addvoice-{mp4name}")
        source_mp4 = f"./tmp/addvoice-{mp4name}"
    os.system(
        f"ffmpeg -y -i {source_mp4} -i {sub_name} -c copy -c:s mov_text -metadata:s:s:0 language={video_config['subtitle_language']}  {target_mp4}")
    videolist[mp4name] = target_mp4
    updatebtn(mp4name, f"{mp4name}.mp4 finished")


# 拼接配音片段
def merge_audio_segments(segments, start_times, total_duration, mp4name):
    # 创建一个空白的音频段作为初始片段
    merged_audio = AudioSegment.empty()
    # 检查是否需要在第一个片段之前添加静音
    if start_times[0] != 0:
        silence_duration = start_times[0]
        silence = AudioSegment.silent(duration=silence_duration)
        merged_audio += silence

    # 逐个连接音频片段
    for i in range(len(segments)):
        segment = segments[i]
        start_time = start_times[i]
        # 检查前一个片段的结束时间与当前片段的开始时间之间是否有间隔
        if i > 0:
            previous_end_time = start_times[i - 1] + len(segments[i - 1])
            silence_duration = start_time - previous_end_time
            # 可能存在字幕 语音对应问题
            if silence_duration > 0:
                silence = AudioSegment.silent(duration=silence_duration)
                merged_audio += silence

        # 连接当前片段
        merged_audio += segment
    # 检查总时长是否大于指定的时长，并丢弃多余的部分
    if len(merged_audio) > total_duration:
        merged_audio = merged_audio[:total_duration]
    merged_audio.export(f"./tmp/{mp4name}.wav", format="wav")
    return merged_audio


# 处理各个音频片段到文字并生成字幕文件
def get_large_audio_transcription(aud_path, ext="wav", video_ext='mp4'):
    global videolist
    folder_path = '/'.join(aud_path.split('/')[:-1])
    audio_name = aud_path.split('/')[-1][:-4]
    mp4name = f"{audio_name}.{video_ext}"

    tmp_path = folder_path + f'/##{audio_name}_tmp'
    updatebtn(mp4name, f"{mp4name} spilt audio")
    if current_status == 'stop':
        return
    if not os.path.isdir(tmp_path):
        os.mkdir(tmp_path)

    thd, min_slien, sub_name = get_thd_min_silence(aud_path)
    # 已存在字幕文件则跳过
    if not os.path.exists(sub_name) or os.path.getsize(sub_name) == 0:
        sound = AudioSegment.from_wav(aud_path)
        normalized_sound = match_target_amplitude(sound, -20.0)  # -20.0
        total_length = len(normalized_sound) / 1000
        nonslient_file = f'{tmp_path}/detected_voice.json'
        updatebtn(mp4name, f"{mp4name} create json")
        print(f"【get_large_audio_transcription】sub_name={sub_name}")
        if os.path.exists(nonslient_file):
            with open(nonslient_file, 'r') as infile:
                nonsilent_data = json.load(infile)
        else:
            updatebtn(mp4name, f"{mp4name} create json")
            nonsilent_data = detect_nonsilent(normalized_sound, min_silence_len=min_slien, silence_thresh=-20.0 - thd,
                                              seek_step=1)
            if current_status == 'stop':
                return
            nonsilent_data = shorten_voice(nonsilent_data)
            updatebtn(mp4name, f"{mp4name} split voice")
            with open(nonslient_file, 'w') as outfile:
                json.dump(nonsilent_data, outfile)

        subs = []
        updatebtn(mp4name, f"{mp4name} translate")
        segments = []
        start_times = []

        for i, duration in enumerate(nonsilent_data, start=1):
            if current_status == 'stop':
                return
            start_time, end_time, buffered = duration
            start_times.append(start_time)
            print(f"开始时间：{start_time=},结束时间:{end_time=},{duration=}")
            time_covered = start_time / len(normalized_sound) * 100
            # 进度
            updatebtn(mp4name, f"{mp4name} {time_covered:.1f}%")
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}." + ext
            add_vol = 10
            audio_chunk = normalized_sound[start_time:end_time] + add_vol
            audio_chunk.export(chunk_filename, format=ext)

            # recognize the chunk
            with sr.AudioFile(chunk_filename) as source:
                audio_listened = r.record(source)
                try:
                    text = r.recognize_google(audio_listened, language=video_config['detect_language'])
                    print(f"【get_large_audio_transcription】语音识别为文字:{text=}")
                except sr.UnknownValueError as e:
                    print("Recognize Error: ", str(e), end='; ')
                    segments.append(audio_chunk)
                    continue
                except Exception as e:
                    print("Recognize Error:", str(e), end='; ')
                    segments.append(audio_chunk)
                    continue
                if current_status == 'stop':
                    return
                text = f"{text.capitalize()}. "
                try:
                    # google翻译
                    transd = translator.translate(text, src=video_config['source_language'],
                                                  dest=video_config['target_language'])
                    result = transd.text
                except Exception as e:
                    print("Translate Error:", str(e))
                    segments.append(audio_chunk)
                    continue

                combo_txt = result + '\n\n'
                if buffered:
                    end_time -= 2000
                start = timedelta(milliseconds=start_time)
                end = timedelta(milliseconds=end_time)

                index = len(subs) + 1
                sub = srt.Subtitle(index=index, start=start, end=end, content=combo_txt)
                qu.put(f"{start} --> {end} {combo_txt}")
                subs.append(sub)
                if video_config['voice_replace'] != 'None':
                    communicate = edge_tts.Communicate(result, video_config['voice_replace'],
                                                       rate=video_config['voice_rate'])
                    tmpname = f"./tmp/{start_time}-{index}.mp3"
                    asyncio.run(communicate.save(tmpname))
                    audio_data = AudioSegment.from_file(tmpname, format="mp3")
                    segments.append(audio_data)
                    os.unlink(tmpname)
        merge_audio_segments(segments, start_times, total_length * 1000, mp4name)
        final_srt = srt.compose(subs)
        with open(sub_name, 'w', encoding="utf-8") as f:
            f.write(final_srt)
    else:
        updatebtn(mp4name, "add subtitle")

    updatebtn(mp4name, f"{mp4name} add subtitle")
    # 最终生成的视频地址
    target_mp4 = os.path.join(video_config['target_dir'], f"{mp4name}")
    # 原始视频地址
    source_mp4 = sub_name.replace('.srt', f".{video_ext}")
    # 如果不是MP4，则先转为mp4，然后再转为原格式
    tmpsource_name = None
    if video_ext != 'mp4':
        # 最终转为mp4格式
        target_mp4 = target_mp4.replace(f"{video_ext}", f"_{video_ext}ToMp4.mp4")
        tmpsource_name = os.path.join(rootdir, f"{str(time.time())}.mp4")
        # 转为mp4格式后再添加字幕
        os.system(f"ffmpeg -y -i {source_mp4} {tmpsource_name}")
        source_mp4 = tmpsource_name
    addsubtitle(source_mp4=source_mp4, target_mp4=target_mp4, sub_name=sub_name, mp4name=mp4name)
    if tmpsource_name:
        # 删除临时文件
        os.unlink(tmpsource_name)


# 从视频 p 中提取出 音频 wav 并调用 get_large_audio_transcription 完成操作
def get_sub_given_path(p, video_ext='mp4'):
    global current_status
    mp4name = os.path.basename(p)
    a_name = p[:-4] + ".wav"
    sub_name = p[:-4] + ".srt"
    print(f"{sub_name=}")
    if (not os.path.exists(sub_name)) or os.path.getsize(sub_name) < 1:
        if not os.path.exists(a_name):
            updatebtn(mp4name, f"{mp4name} split audio")
            os.system(f"ffmpeg -i {p} -acodec pcm_s16le -f s16le -ac 1 -ar 16000 -f wav {a_name}")
    get_large_audio_transcription(a_name, ext="wav", video_ext=video_ext)
    updatebtn(mp4name, f"{mp4name} end")


# 支持的文件类型
def get_ps(folder):
    extens = ["mp4", "avi", "mkv", "mpg"]
    ps = []
    for exten in extens:
        ps += glob.glob(f"{folder}**/*.{exten}", recursive=True)
    ps = [pps.replace("\\", "/") for pps in ps]
    return ps


def running(p):
    global videolist, task_nums
    mp4name = os.path.basename(p).lower()
    updatebtn(mp4name, f"{mp4name} start")
    _, _, sub_name = get_thd_min_silence(p)

    if os.path.exists(sub_name) and video_config['savesubtitle'] == 'No':
        os.unlink(sub_name)
    if os.path.exists(sub_name):
        os.unlink(sub_name)
    get_sub_given_path(p, video_ext=mp4name.split('.')[-1])
    task_nums.append(1)


# 遍历所有视频并开始处理
def search_nc(folders_nc):
    global current_status, task_nums, task_threads
    ps = get_ps(folders_nc)
    for p in ps:
        mp4name = os.path.basename(p).lower()
        try:
            if isinstance(window.find_element(mp4name, silent_on_error=True), ErrorElement):
                window.extend_layout(window['add_row'], [createrow(mp4name)])
            else:
                window[f"{mp4name}-col"].update(visible=True)
                if name not in videolist:
                    videolist[name] = f"{name} waitting start"
        except:
            window.extend_layout(window['add_row'], [createrow(mp4name)])

    for p in ps:
        if current_status == 'stop':
            return
        while True:
            try:
                task_nums.pop()
            except:
                time.sleep(10)
                continue
            t1 = threading.Thread(target=running, args=(p,))
            t1.start()
            task_threads.append(t1)
            print(f'增减线程 t1={p}')
            break
    while True:
        if current_status == "stop":
            break
        time.sleep(1)
        alive = False
        for t in task_threads:
            if t.is_alive():
                alive = True
        if not alive and ishastart:
            current_status = "stop"
            break
    window['startbtn'].update(text='All End')
    shutil.rmtree("./tmp")


# 更新按钮上文字
def updatebtn(name, text):
    if name not in timelist:
        timelist[name] = int(time.time())
    dur = int(time.time()) - timelist[name]
    window[name].update(value=f"[{dur}s]{text}")


# 添加一个按钮
def createrow(name):
    global videolist
    if name not in videolist:
        videolist[name] = f"{name} waitting"
    row = [
        sg.pin(
            sg.Col(
                [
                    [
                        sg.Text(videolist[name], key=name, expand_x=True)
                    ]
                ],
                key=f"{name}-col"
            )
        )
    ]
    window['add_row'].contents_changed()
    return row


# 显示日志
def wrlog():
    while True:
        if current_status == 'stop':
            return
        if not qu.empty():
            try:
                window['logs'].update(value=qu.get() + "\n", autoscroll=True, append=True)
            except Exception as e:
                pass
        else:
            time.sleep(1)


# 测试 google
def testproxy():
    global current_status
    proxy = window['proxy'].get().strip()
    if not proxy:
        proxy = None
    print(f"{proxy=}")
    status = False
    try:
        with httpx.Client(proxies=proxy) as client:
            r = client.get('https://www.google.com', timeout=30)
            print(f'r==========={r.status_code=}')
            if r.status_code == 200:
                status = True
    except Exception as e:
        print(str(e))
    if not status:
        current_status = "stop"
        window['startbtn'].update(text="Stop")
        messagebox.showerror(transobj["proxyerrortitle"], transobj["proxyerrorbody"], parent=window.TKroot)


# 设置可用的语音角色
def set_default_voice(t):
    print(f"设置了目标语言：" + t)
    # 翻译的目标语言
    try:
        vt = langlist[t][0].split('-')[0]
        print(f"设置目标语言{t=},{vt=}")
        if vt not in voice_list:
            window['voice_replace'].update(value="None", values=["None"])
        window['voice_replace'].update(value="None", values=voice_list[vt])
    except:
        window['voice_replace'].update(value="None", values=[it for item in list(voice_list.values()) for it in item])


if __name__ == "__main__":
    if not os.path.exists(os.path.join(rootdir, "tmp")):
        os.mkdir(os.path.join(rootdir, 'tmp'))
    sg.theme('Material1')
    window = sg.Window(transobj['softname'], layout, size=(1100, 500), icon=os.path.join(rootdir, "icon.ico"),
                       resizable=True)
    while_ready = False
    while True:
        event, values = window.read(timeout=100)
        # 选择源视频文件夹
        if event == 'getsource_dir':
            window['source_dir'].update(askdirectory())
        # 选择目标输出视频文件夹
        elif event == 'gettarget_dir':
            window['target_dir'].update(askdirectory())
        elif event == 'target_lang':
            t = window['target_lang'].get()
            set_default_voice(t)
        elif event == 'startbtn':
            # 重置初始化
            if ishastart:
                hasvideos = list(videolist.keys())
                if len(hasvideos) > 0:
                    for name in hasvideos:
                        window[f"{name}-col"].update(visible=False)
                videolist = {}
                timelist = {}
            ishastart = True
            # 已在执行中，点击停止
            if current_status == 'ing':
                current_status = 'stop'
                window['startbtn'].update(text="Stoped")
                continue

            source_dir = window['source_dir'].get()
            target_dir = window['target_dir'].get()
            # 原视频位置
            if not source_dir:
                messagebox.showerror(transobj['anerror'], transobj['selectvideodir'], parent=window.TKroot)
                current_status = "stop"
                continue
            # 目标存放地址
            if not target_dir:
                target_dir = os.path.join(os.path.dirname(source_dir), "_video_out").replace('\\', '/')
                os.makedirs(target_dir, 0o777, exist_ok=True)
                window['target_dir'].update(value=target_dir)
            video_config['source_dir'] = source_dir
            video_config['target_dir'] = target_dir
            # 原语言
            source_lang = window['source_lang'].get()
            target_lang = window['target_lang'].get()
            if source_lang == target_lang:
                messagebox.showerror(transobj['anerror'], transobj['sourenotequaltarget'], parent=window.TKroot)
                continue
            video_config['source_language'] = langlist[source_lang][0]
            video_config['detect_language'] = langlist[source_lang][0]
            video_config['target_language'] = langlist[target_lang][0]
            video_config['subtitle_language'] = langlist[target_lang][1]
            video_config['savesubtitle'] = window['savesubtitle'].get()
            video_config['voice_replace'] = window['voice_replace'].get()
            rate = window['voice_rate'].get().strip()
            rate = int(rate)
            if rate > 0:
                video_config['voice_rate'] = f"+{rate}%"
            elif rate < 0:
                video_config['voice_rate'] = f"{rate}%"
            else:
                video_config['voice_rate'] = f"+0%"

            # 设置代理
            proxy = window['proxy'].get()
            if len(proxy) > 0 and not re.match(r'^(https?)|(sock5?)://', proxy, re.I):
                messagebox.showerror(title=transobj['proxyerrortitle'], message=transobj['proxyerrorbody'],
                                     parent=window.TKroot)
                continue
            elif len(proxy) > 0:
                os.environ['http_proxy'] = proxy
                os.environ['https_proxy'] = proxy
                sg.user_settings_set_entry('proxy', proxy)
            try:
                concurrent = int(window['concurrent'].get())
            except:
                concurrent = 1
            sg.user_settings_set_entry('concurrent', concurrent)
            sg.user_settings_set_entry('source_lang', source_lang)
            sg.user_settings_set_entry('target_lang', target_lang)
            sg.user_settings_set_entry('savesubtitle', video_config['savesubtitle'])
            sg.user_settings_set_entry('voice_rate', str(rate).replace('%',''))

            task_nums = list(range(concurrent))
            threading.Thread(target=testproxy).start()

            current_status = "ing"
            window['startbtn'].update(text=transobj['running'])

            translator = Translator(service_urls=['translate.googleapis.com'])
            r = sr.Recognizer()
            threading.Thread(target=search_nc, args=(window['source_dir'].get(),)).start()
            threading.Thread(target=wrlog).start()
        elif event == sg.WIN_CLOSED or event == transobj['exit']:
            current_status = 'stop'
            sys.exit()

        if not while_ready:
            while_ready = True
            set_default_voice(sg.user_settings_get_entry('target_lang', window['target_lang'].get()))
    window.close()
