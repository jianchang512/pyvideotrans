import re
import sys
import webbrowser

import httpx
import speech_recognition as sr
import os, time
from PySimpleGUI import ErrorElement
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from googletrans import Translator
import PySimpleGUI as sg
# https://srt.readthedocs.io/en/latest/api.html
import srt
from datetime import timedelta
import  shutil, glob
import json
from tkinter.filedialog import askdirectory
from tkinter import messagebox
import threading
from config import qu,rootdir,langlist, videolist,timelist,current_status,ishastart,video_config,task_nums,task_threads

sg.user_settings_filename(path='.')
menu_def = [
    ['文件','退出'],
    ['帮助', ['使用说明','关于我们']]
]

layout = [
     [sg.Menu(menu_def, )],
    [
        sg.Column(
            [
                [sg.Text('原始视频目录', background_color="#e3f2fd", text_color='#212121'), sg.InputText(key="source_dir"),
                 sg.Button('选择待翻译视频', key="getsource_dir", enable_events=True, button_color='#018fff', border_width=0)],
                [sg.Text('输出视频位置', background_color="#e3f2fd", text_color='#212121'),
                 sg.InputText(key="target_dir"),
                 sg.Button('选择输出文件夹', key="gettarget_dir", enable_events=True, button_color='#018fff', border_width=0)],
                [sg.Text('网络代理地址', tooltip="类似 http://127.0.0.1:10809", background_color="#e3f2fd",
                         text_color='#212121'),
                 sg.InputText(sg.user_settings_get_entry('proxy', ''), key="proxy",
                              tooltip="类似 http://127.0.0.1:10809 的形式")
                 ],
                [
                    sg.Text('如果你不能直接打开google，需在上方填写代理地址',background_color="#e3f2fd",
                         text_color='#777777'),
                ],
                [
                    sg.Text('视频原始语言', background_color="#e3f2fd", text_color='#212121'),
                    sg.Combo(list(langlist.keys()), default_value=sg.user_settings_get_entry('source_lang', '英语'),
                             readonly=True, key="source_lang", size=(10, None)),
                    sg.Text('翻译目标语言', background_color="#e3f2fd", text_color='#212121'),
                    sg.Combo(list(langlist.keys()), default_value=sg.user_settings_get_entry('target_lang', '中文简'),
                             readonly=True, key="target_lang", size=(10, None)),
                    sg.Text('保留字幕文件', background_color="#e3f2fd", text_color='#212121'),
                    sg.Combo(['保留','不保留'],tooltip="如果保留，下次同一视频切换字幕语种不生效，需要手动删除", default_value=sg.user_settings_get_entry('savesubtitle', '保留'),
                             readonly=True, key="savesubtitle", size=(10, None)),
                ],
                [
                    sg.Text('并发翻译数量', background_color="#e3f2fd", text_color='#212121'),
                    sg.InputText(sg.user_settings_get_entry('concurrent', 2), key="concurrent",
                              tooltip="1-20(cpu的整数倍)",size=(10,1)),
                    sg.Text('显示字幕语种', background_color="#e3f2fd", text_color='#212121'),
                    sg.Combo(['目标语言字幕','双字幕'], default_value=sg.user_settings_get_entry('subtitle_out', '目标语言字幕'),  readonly=True, key="subtitle_out", size=(14, None)),
                ],
                [
                    sg.Text('并非数量即同时翻译的视频数量，建议为2-cpu的整数倍',background_color="#e3f2fd",
                         text_color='#777777'),
                ],
                [
                    sg.Radio("合成软字幕(快),播放器字幕轨道中可启用或禁用", background_color="#e3f2fd", text_color='#212121', tooltip="播放器字幕轨道中可启用可禁用", group_id="subtitle", key="soft_subtitle", default=True),

                    sg.Radio("合成硬字幕(慢),字幕嵌入视频，不依赖播放器功能", background_color="#e3f2fd", text_color='#212121', tooltip="", group_id="subtitle", key="hard_subtitle", default=False),
                ],
                [
                    sg.Button('开始执行', key="startbtn", button_color='#2196f3', size=(16, 2), font=16),
                ],
                [
                    sg.Multiline('', key="logs", expand_x=True, expand_y=True, size=(50, 10), autoscroll=True, background_color="#f1f1f1", text_color='#212121'),
                ]
            ],
            background_color="#e3f2fd",
            expand_x=True,
            expand_y=True,
            size=(640, None)
        ),
        sg.Column(
            [
                [
                    sg.Text("进度显示区", background_color="#e3f2fd", text_color='#212121'),
                ],
                [
                    sg.Column([[]],
                        key="add_row",
                        background_color="#e3f2fd",
                        size=(None, 400),
                        expand_y=True,
                        expand_x=True,
                        scrollable=True,
                        # justification="top",
                        vertical_alignment="top",
                        vertical_scroll_only=True
                    )
                ],
            ],
            # key="add_row",
            background_color="#e3f2fd",
            size=(None, None),
            expand_y=True,
            expand_x=True,
            scrollable=False,
            vertical_scroll_only=True
        )
    ]
]
sg.theme('Material1')
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


# 添加字幕，将 视频 source_mp4 添加字幕 sub_name 后输出 target_mp4   mp4name=带后缀视频名
def addsubtitle(source_mp4=None,target_mp4=None,sub_name=None,mp4name=None):
    global videolist
    if video_config['subtitle_type'] == 'soft':
        # 软字幕
        os.system(
            f"ffmpeg -y -i {source_mp4} -i {sub_name} -c copy -c:s mov_text -metadata:s:s:0 language={video_config['subtitle_language']}  {target_mp4}")
    else:
        try:
            updatebtn(mp4name, f"{mp4name} 开始硬字幕合成，用时会较久")
            # 硬字幕直接用名字
            srtname=os.path.basename(sub_name)
            os.system(f"ffmpeg -y -i \"{source_mp4}\" -vf subtitles=\"{srtname}.srt\" \"{target_mp4}\"")
        except Exception as e:
            print(e)
    videolist[mp4name] = target_mp4
    updatebtn(mp4name, f"{mp4name}.mp4 处理完成")

# 处理各个音频片段到文字并生成字幕文件
def get_large_audio_transcription(aud_path, ext="wav",video_ext='mp4'):
    global videolist
    """
    Splitting the large audio file into chunks
    and apply speech recognition on each of these chunks
    """

    folder_path = '/'.join(aud_path.split('/')[:-1])
    audio_name = aud_path.split('/')[-1][:-4]
    mp4name=f"{audio_name}.{video_ext}"

    tmp_path = folder_path + f'/##{audio_name}_tmp'
    updatebtn(mp4name, f"视频{mp4name} 正在切分音频")
    qu.put(f"【get_large_audio_transcription】待处理音频 {audio_name=},{tmp_path=}")
    if current_status == 'stop':
        return
    if not os.path.isdir(tmp_path):
        os.mkdir(tmp_path)

    thd, min_slien, sub_name = get_thd_min_silence(aud_path)
    # 已存在字幕文件则跳过
    if not os.path.exists(sub_name) or os.path.getsize(sub_name) == 0:
        sound = AudioSegment.from_wav(aud_path)
        normalized_sound = match_target_amplitude(sound, -20.0)  # -20.0
        qu.put("【get_large_audio_transcription】length of audio_segment={} seconds".format(len(normalized_sound) / 1000))
        nonslient_file = f'{tmp_path}/detected_voice.json'
        qu.put(f"【get_large_audio_transcription】生成语言文件:{nonslient_file=}")
        updatebtn(mp4name, f"视频{mp4name} 生成语言文件")
        print(f"【get_large_audio_transcription】sub_name={sub_name}")
        if os.path.exists(nonslient_file):
            with open(nonslient_file, 'r') as infile:
                nonsilent_data = json.load(infile)
        else:
            qu.put(f"【get_large_audio_transcription】正在创建语音切分标识文件...")
            updatebtn(mp4name, f"视频{mp4name} 正在创建语音切分标识文件")
            nonsilent_data = detect_nonsilent(normalized_sound, min_silence_len=min_slien, silence_thresh=-20.0 - thd, seek_step=1)
            if current_status == 'stop':
                return
            qu.put(f"【get_large_audio_transcription】detect_nonsilent 完成，开始 shorten_voice...")
            nonsilent_data = shorten_voice(nonsilent_data)
            updatebtn(mp4name, f"视频{mp4name} 开始切分音频小片段")
            qu.put(f"【get_large_audio_transcription】shorten_voice 完成，创建{nonslient_file=}...")
            with open(nonslient_file, 'w') as outfile:
                json.dump(nonsilent_data, outfile)

        # whole_text = ""
        # whole_trans = ""
        subs = []
        updatebtn(mp4name, f"视频{mp4name} 开始翻译")
        for i, duration in enumerate(nonsilent_data, start=1):
            if current_status == 'stop':
                return
            start_time, end_time, buffered = duration
            # start_min = start_time // 1000 / 60
            # end_min = end_time // 1000 / 60
            # i_covered = i / len(nonsilent_data) * 100
            time_covered = start_time / len(normalized_sound) * 100
            # 进度
            updatebtn(mp4name, f"视频{mp4name} 翻译进度{time_covered:.1f}%")
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}." + ext  # os.path.join(tmp_path, f"c{i}_{start_time}_{end_time}."+ext)
            qu.put(f"【get_large_audio_transcription】 正在处理:chunk_filename={chunk_filename}")
            add_vol = 10
            audio_chunk = normalized_sound[start_time:end_time] + add_vol
            audio_chunk.export(chunk_filename, format=ext)

            # recognize the chunk
            with sr.AudioFile(chunk_filename) as source:
                qu.put(f"【get_large_audio_transcription】 source={source}")
                audio_listened = r.record(source)
                try:
                    #################### modify language= to define the language to detect ##########
                    ## You can find all the possible languages here:
                    # https://cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages
                    text = r.recognize_google(audio_listened, language=video_config['detect_language'])
                    print(f"【get_large_audio_transcription】语音识别为文字:{text=}")
                except sr.UnknownValueError as e:
                    print("Recognize Error: ", str(e), end='; ')
                    continue
                except Exception as e:
                    print("Recognize Error:", str(e), end='; ')
                    continue
                if current_status == 'stop':
                    return
                text = f"{text.capitalize()}. "  # .decode('utf-8').encode('gbk')
                try:
                    #################### modify src='ja', dest="zh-cn" to define the source and target language ##########
                    ## You can find all the possible language here:
                    # https://py-googletrans.readthedocs.io/en/latest/#googletrans-languages
                    # google翻译
                    transd = translator.translate(text, src=video_config['source_language'],
                                                  dest=video_config['target_language'])  # en zh-cn
                    result = transd.text  # .decode('utf-8').encode('gbk')
                except Exception as e:
                    print("Translate Error:", str(e))
                    continue
                # subtitles
                if video_config['subtitle_out']=='双字幕':
                    combo_txt = text + '\n' + result + '\n\n'
                else:
                    combo_txt = result + '\n\n'
                if buffered:
                    # start_time += 2000
                    end_time -= 2000
                start = timedelta(milliseconds=start_time)
                end = timedelta(milliseconds=end_time)

                index = len(subs) + 1
                sub = srt.Subtitle(index=index, start=start, end=end, content=combo_txt)
                subs.append(sub)

                # whole_text += text
                # whole_trans += result

        final_srt = srt.compose(subs)
        # todo 字幕合并
        with open(sub_name, 'w', encoding="utf-8") as f:
            f.write(final_srt)
        qu.put(f"【get_large_audio_transcription】生成字幕文件:final_str")
    else:
        qu.put(f"字幕文件已存在，直接使用 {sub_name=}")
        updatebtn(mp4name, "开始合成字幕")

    # shutil.rmtree(tmp_path)
    # if os.path.exists(aud_path):
    #     os.remove(aud_path)
    updatebtn(mp4name, f"视频{mp4name} 开始合成字幕")
    # 最终生成的视频地址
    target_mp4 = os.path.join(video_config['target_dir'], f"{mp4name}")
    # 原始视频地址
    source_mp4 = sub_name.replace('.srt', f".{video_ext}")
    # 如果不是MP4，则先转为mp4，然后再转为原格式
    tmpsource_name=None
    if video_ext != 'mp4':
        # 最终转为mp4格式
        target_mp4=target_mp4.replace(f"{video_ext}", f"_{video_ext}ToMp4.mp4")
        tmpsource_name= os.path.join(rootdir,f"{str(time.time())}.mp4")
        # 转为mp4格式后再添加字幕
        os.system(f"ffmpeg -y -i {source_mp4} {tmpsource_name}")
        source_mp4=tmpsource_name
    addsubtitle(source_mp4=source_mp4,target_mp4=target_mp4,sub_name=sub_name,mp4name=mp4name)
    if tmpsource_name:
        # 删除临时文件
        os.unlink(tmpsource_name)

# 从视频 p 中提取出 音频 wav 并调用 get_large_audio_transcription 完成操作
def get_sub_given_path(p,video_ext='mp4'):
    global current_status
    mp4name = os.path.basename(p)
    a_name = p[:-4] + ".wav"
    qu.put(f"【get_sub_given_path】p==={p},a_name={a_name}")
    sub_name = p[:-4] + ".srt"
    print(f"{sub_name=}")
    if (not os.path.exists(sub_name)) or os.path.getsize(sub_name) < 1:
        if not os.path.exists(a_name):
            updatebtn(mp4name, f"视频{mp4name} 正在提取音频")
            os.system(f"ffmpeg -i {p} -acodec pcm_s16le -f s16le -ac 1 -ar 16000 -f wav {a_name}")
    qu.put(f"【get_sub_given_path】 音频文件 a_name={a_name} 已提取.")
    get_large_audio_transcription(a_name, ext="wav",video_ext=video_ext)
    updatebtn(mp4name, f"视频{mp4name} 翻译完成")

def get_ps(folder):
    extens = ["mp4", "avi", "mkv", "mpg"]
    ps = []
    for exten in extens:
        ps += glob.glob(f"{folder}**/*.{exten}", recursive=True)
    ps = [pps.replace("\\", "/") for pps in ps]
    return ps

def running(p):
    global videolist,task_nums
    qu.put(f"【search_nc】开始处理视频p={p}")
    mp4name = os.path.basename(p).lower()
    updatebtn(mp4name, f"视频{mp4name} 开始处理")
    _, _, sub_name = get_thd_min_silence(p)

    if os.path.exists(sub_name) and video_config['savesubtitle']=='不保留':
        os.unlink(sub_name)
    if os.path.exists(sub_name):
        qu.put(f"【search_nc】字幕文件已存在，跳过:{sub_name=}!")
        get_sub_given_path(p, video_ext=mp4name.split('.')[-1])
    else:
        get_sub_given_path(p, video_ext=mp4name.split('.')[-1])
        qu.put(f"【search_nc】视频{mp4name}结束了.")
    task_nums.append(1)

def search_nc(folders_nc):
    global current_status,task_nums,task_threads
    ps = get_ps(folders_nc)
    for p in ps:
        mp4name = os.path.basename(p).lower()
        try:
            if isinstance(window.find_element(mp4name, silent_on_error=True), ErrorElement):
                window.extend_layout(window['add_row'], [createrow(mp4name)])
            else:
                window[f"{mp4name}-col"].update(visible=True)
                if name not in videolist:
                    videolist[name] = f"{name} 等待处理"
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
            t1=threading.Thread(target=running,args=(p,))
            t1.start()
            task_threads.append(t1)
            print(f'增减线程 t1={p}')
            break
    while True:
        if current_status == "stop":
            break
        time.sleep(1)
        alive=False
        for t in task_threads:
            if t.is_alive():
                alive=True
        if not alive and ishastart:
            current_status = "stop"
            break
    window['startbtn'].update(text='执行结束')

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
        videolist[name] = f"{name} 等待处理"
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


# https://stackoverflow.com/questions/67009452/adding-subtitles-to-video-with-python
# https://towardsdatascience.com/extracting-audio-from-video-using-python-58856a940fd

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

def testproxy():
    global current_status
    proxy=window['proxy'].get().strip()
    if not proxy:
        proxy=None
    print(f"{proxy=}")
    status=False
    try:
        with httpx.Client(proxies=proxy) as client:
            r=client.get('https://www.google.com',timeout=30)
            print(f'r==========={r.status_code=}')
            if r.status_code == 200:
                status=True
    except Exception as e:
        print(str(e))
    if not status:
        current_status="stop"
        window['startbtn'].update(text="已停止")
        messagebox.showerror("代理错误","无法访问google服务，请正确设置代理",parent=window.TKroot)

if __name__ == "__main__":
    window = sg.Window('视频字幕翻译', layout,  size=(1100, 500), icon=os.path.join(rootdir, "icon.ico"), resizable=True)

    while True:
        event, values = window.read(timeout=100)
        # 选择源图片文件夹
        if event == 'getsource_dir':
            window['source_dir'].update(askdirectory())
        # 选择目标图片文件夹
        elif event == 'gettarget_dir':
            window['target_dir'].update(askdirectory())
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
                window['startbtn'].update(text="已停止")
                continue


            source_dir = window['source_dir'].get()
            target_dir = window['target_dir'].get()
            # 原视频位置
            if not source_dir:
                messagebox.showerror('出错了', '必须选择要翻译的视频', parent=window.TKroot)
                current_status = "stop"
                continue
            # 目标存放地址
            if not target_dir:
                target_dir = os.path.join(os.path.dirname(source_dir), "_video_out").replace('\\', '/')
                os.makedirs(target_dir, 0o777, exist_ok=True)
                # 存到目录的riwen子文件夹下
                window['target_dir'].update(value=target_dir)
            video_config['source_dir'] = source_dir
            video_config['target_dir'] = target_dir
            # 原语言
            source_lang = window['source_lang'].get()
            target_lang = window['target_lang'].get()
            if source_lang == target_lang:
                messagebox.showerror('出错了', '源语言和目标语言相同', parent=window.TKroot)
                continue
            sg.user_settings_set_entry('source_lang', source_lang)
            sg.user_settings_set_entry('target_lang', target_lang)
            video_config['source_language'] = langlist[source_lang][0]
            video_config['detect_language'] = langlist[source_lang][0]
            video_config['target_language'] = langlist[target_lang][0]
            video_config['subtitle_language'] = langlist[target_lang][1]
            video_config['subtitle_out'] = window['subtitle_out'].get()
            video_config['savesubtitle'] = window['savesubtitle'].get()
            sg.user_settings_set_entry('subtitle_out', video_config['subtitle_out'])
            sg.user_settings_set_entry('savesubtitle', video_config['savesubtitle'])
            # 字幕类型
            if window['soft_subtitle'].get():
                video_config['subtitle_type'] = 'soft'
            else:
                video_config['subtitle_type'] = 'hard'
            # 设置代理
            proxy = window['proxy'].get()
            if len(proxy) > 0 and not re.match(r'^(https?)|(sock5?)://', proxy, re.I):
                messagebox.showerror(title="代理错误", message="填写 http://127.0.0.1:10809 类似的代理", parent=window.TKroot)
                continue
            elif len(proxy) > 0:
                os.environ['http_proxy'] = proxy
                os.environ['https_proxy'] = proxy
                sg.user_settings_set_entry('proxy', proxy)
            try:
                concurrent=int(window['concurrent'].get())
            except:
                concurrent=1
            sg.user_settings_set_entry('concurrent',concurrent)




            task_nums=list(range(concurrent))
            threading.Thread(target=testproxy).start()

            current_status = "ing"
            window['startbtn'].update(text="执行中")

            translator = Translator(service_urls=['translate.googleapis.com'])
            r = sr.Recognizer()

            threading.Thread(target=search_nc, args=(window['source_dir'].get(),)).start()
            threading.Thread(target=wrlog).start()
        elif event == sg.WIN_CLOSED or event== '退出':
            current_status = 'stop'
            sys.exit()
        elif event=='关于我们':
            webbrowser.open("https://v.wonyes.org/about", new=0)
        elif event=='使用说明':
            webbrowser.open("https://v.wonyes.org/help", new=0)
    window.close()
