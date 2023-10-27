import re
import shutil
import sys
import os
import time
import PySimpleGUI as sg
from tkinter.filedialog import askdirectory
from tkinter import messagebox
import threading
from config import qu, rootdir, langlist, timelist, video_config, layout, transobj
import config
from tools import get_list_voices, get_large_audio_transcription, testproxy, logger

sg.user_settings_filename(path='.')
voice_list = get_list_voices()


def running(p):
    # 所在目录
    dirname = os.path.dirname(p)
    # 去掉名字中的空格
    mp4nameraw = os.path.basename(p)
    mp4name = re.sub(r"\s", '', mp4nameraw, 0, re.I)
    if mp4nameraw != mp4name:
        os.rename(p, os.path.join(os.path.dirname(p), mp4name))
    #  整理后的视频名字不带后缀，和后缀，比如 1123  mp4
    noextname = os.path.splitext(mp4name)[0]
    # 字幕文件
    sub_name = f"{dirname}/{noextname}.srt"
    # 音频文件
    a_name = f"{dirname}/{noextname}.wav"
    showprocess(mp4name, f"{mp4name} start")
    if os.path.exists(sub_name):
        os.unlink(sub_name)

    if not os.path.exists(a_name):
        showprocess(mp4name, f"{mp4name} split audio")
        os.system(f"ffmpeg -i {dirname}/{mp4name} -acodec pcm_s16le -f s16le -ac 1  -f wav {a_name}")
    # 如果选择了去掉背景音，则重新整理为 a_name{voial}.wav
    if video_config['voice_replace'] != 'No' and video_config['remove_background'] == 'Yes':
        import warnings
        warnings.filterwarnings('ignore')
        from spleeter.separator import Separator
        separator = Separator('spleeter:2stems', multiprocess=False)
        separator.separate_to_file(a_name, destination=dirname, filename_format="{filename}{instrument}.{codec}")
        # 新的名字
        a_name = f"{dirname}/{noextname}vocals.wav"
    get_large_audio_transcription(a_name, mp4name, sub_name, showprocess)
    showprocess(mp4name, f"{mp4name} end")
    config.current_status = "stop"
    window['startbtn'].update(text=transobj['end'])
    shutil.rmtree("./tmp")
    if os.path.exists(f"{dirname}/{noextname}vocals.wav"):
        os.unlink(f"{dirname}/{noextname}vocals.wav")
    if os.path.exists(f"{dirname}/##{noextname}vocals_tmp"):
        shutil.rmtree(f"{dirname}/##{noextname}vocals_tmp")
    if os.path.exists(f"{dirname}/{noextname}.wav"):
        os.unlink(f"{dirname}/{noextname}.wav")
    if os.path.exists(f"{dirname}/##{noextname}_tmp"):
        shutil.rmtree(f"{dirname}/##{noextname}_tmp")


# 显示字幕
def showsubtitle():
    while True:
        if config.current_status == 'stop':
            return
        if not qu.empty():
            try:
                window['subtitle_area'].update(value=qu.get() + "\n", autoscroll=True, append=True)
            except Exception as e:
                pass
        else:
            time.sleep(1)


def testgoogle():
    proxy = window['proxy'].get().strip()
    if not proxy:
        return
    if not testproxy(proxy):
        config.current_status = "stop"
        window['startbtn'].update(text=transobj["stop"])
        messagebox.showerror(transobj["proxyerrortitle"], transobj["proxyerrorbody"], parent=window.TKroot)


# 显示进度
def showprocess(name, text):
    if name not in timelist:
        timelist[name] = int(time.time())
    dur = int(time.time()) - timelist[name]
    window['process'].update(value=f"[{dur}s]{text}\n", autoscroll=True, append=True)


# 设置可用的语音角色
def set_default_voice(t):
    try:
        vt = langlist[t][0].split('-')[0]
        if vt not in voice_list:
            window['voice_replace'].update(value="No", values=["No"])
        window['voice_replace'].update(value="No", values=voice_list[vt])
    except:
        window['voice_replace'].update(value="No", values=[it for item in list(voice_list.values()) for it in item])


if __name__ == "__main__":

    sg.theme('Material1')
    window = sg.Window(transobj['softname'],
                       layout,
                       size=(1100, 500),
                       icon=os.path.join(rootdir, "icon.ico"),
                       resizable=True)
    while_ready = False
    while True:
        event, values = window.read(timeout=100)
        # 选择目标输出视频文件夹
        if event == 'gettarget_dir':
            window['target_dir'].update(askdirectory())
        elif event == 'target_lang':
            t = window['target_lang'].get()
            set_default_voice(t)
        elif event == 'startbtn':
            if not os.path.exists(os.path.join(rootdir, "tmp")):
                os.mkdir(os.path.join(rootdir, 'tmp'))
            # 重置初始化
            window['process'].update(value="")
            window['subtitle_area'].update(value="")
            timelist = {}
            # 已在执行中，点击停止
            if config.current_status == 'ing':
                config.current_status = 'stop'
                window['startbtn'].update(text=transobj['stop'])
                continue

            source_mp4 = window['source_mp4'].get()
            target_dir = window['target_dir'].get()
            # 原视频位置
            if not source_mp4:
                logger.error(f"not source_mp4 {source_mp4}")
                messagebox.showerror(transobj['anerror'], transobj['selectvideodir'], parent=window.TKroot)
                config.current_status = "stop"
                continue
            # 目标存放地址
            if not target_dir:
                target_dir = os.path.join(os.path.dirname(source_mp4), "_video_out").replace('\\', '/')
                window['target_dir'].update(value=target_dir)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, 0o777, exist_ok=True)
            # 原语言
            source_lang = window['source_lang'].get()
            target_lang = window['target_lang'].get()
            if source_lang == target_lang:
                messagebox.showerror(transobj['anerror'], transobj['sourenotequaltarget'], parent=window.TKroot)
                continue
            rate = window['voice_rate'].get().strip()
            rate = int(rate)
            if rate > 0:
                video_config['voice_rate'] = f"+{rate}%"
            elif rate < 0:
                video_config['voice_rate'] = f"{rate}%"
            else:
                video_config['voice_rate'] = f"+0%"

            video_config['source_mp4'] = source_mp4
            video_config['target_dir'] = target_dir
            video_config['source_language'] = langlist[source_lang][0]
            video_config['detect_language'] = langlist[source_lang][0]

            video_config['target_language'] = langlist[target_lang][0]
            video_config['subtitle_language'] = langlist[target_lang][1]
            video_config['voice_replace'] = window['voice_replace'].get()
            video_config['remove_background'] = window['remove_background'].get()

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
            sg.user_settings_set_entry('source_lang', source_lang)
            sg.user_settings_set_entry('target_lang', target_lang)
            sg.user_settings_set_entry('remove_background', video_config['remove_background'])
            sg.user_settings_set_entry('voice_rate', str(rate).replace('%', ''))

            threading.Thread(target=testgoogle, ).start()
            config.current_status = "ing"
            window['startbtn'].update(text=transobj['running'])
            logger.info(f"running----------{config.current_status=}")
            threading.Thread(target=running, args=(window['source_mp4'].get(),)).start()
            threading.Thread(target=showsubtitle).start()
        elif event == sg.WIN_CLOSED or event == transobj['exit']:
            config.current_status = 'stop'
            sys.exit()

        if not while_ready:
            while_ready = True
            set_default_voice(sg.user_settings_get_entry('target_lang', window['target_lang'].get()))
    window.close()
