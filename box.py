# -*- coding: utf-8 -*-
# primary ui
import copy
import datetime
import json
import os
import re
import shutil
import sys
import threading
import time

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QSettings, QUrl, pyqtSignal, QThread
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QFileDialog, QMessageBox, QPushButton, \
    QPlainTextEdit, QLabel
from pydub import AudioSegment

from videotrans import VERSION
from videotrans.configure import boxcfg, config
from videotrans.configure.language import language_code_list, english_code_bygpt
from videotrans.configure.config import logger, rootdir, homedir, langlist
from videotrans.translator import deeplxtrans, deepltrans, tencenttrans, baidutrans, googletrans, baidutrans_spider, \
    chatgpttrans, azuretrans, geminitrans
from videotrans.ui.toolbox import Ui_MainWindow
from videotrans.util.tools import transcribe_audio, text_to_speech, set_proxy, runffmpegbox as runffmpeg, \
    get_edge_rolelist, get_subtitle_from_srt, ms_to_time_string, speed_change

from videotrans.configure.config import transobj

if config.is_vlc:
    try:
        import vlc
    except:
        config.is_vlc = False


        class vlc():
            pass

if config.defaulelang == "zh":
    from videotrans.ui.toolbox import Ui_MainWindow
else:
    from videotrans.ui.toolboxen import Ui_MainWindow


class DropButton(QPushButton):
    def __init__(self, text=""):
        super(DropButton, self).__init__(text)
        self.setAcceptDrops(True)
        self.clicked.connect(self.get_file)

    def get_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, transobj['xuanzeyinpinwenjian'],
                                               os.path.expanduser('~') + "\\Videos",
                                               filter="Video/Audio files(*.mp4 *.avi *.mov *.wav *.mp3 *.flac)")
        if fname:
            self.setText(fname)

    def dragEnterEvent(self, event):
        ext = event.mimeData().text().lower().split('.')[1]
        if ext in ["mp4", "avi", "mov", "wav", "mp3", "flac"]:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        filepath = event.mimeData().text()
        self.setText(filepath.replace('file:///', ''))


# 文本框 获取内容
class Textedit(QPlainTextEdit):
    def __init__(self):
        super(Textedit, self).__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        ext = event.mimeData().text().lower().split('.')
        if len(ext) > 0 and ext[-1] in ["txt", "srt"]:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        filepath = event.mimeData().text().replace('file:///', '')
        with open(filepath, 'r', encoding="utf-8") as f:
            self.setPlainText(f.read().strip())


class TextGetdir(QPlainTextEdit):
    def __init__(self):
        super(TextGetdir, self).__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        files = event.mimeData().text().split("\n")
        result = []
        for it in files:
            if it != "" and it.split('.')[-1] in ["mp4", "avi", "mov", "wav", "mp3"]:
                result.append(it)
        if len(result) > 0:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = event.mimeData().text().split("\n")
        result = []
        if self.toPlainText().strip():
            result = self.toPlainText().strip().split("\n")
        for it in files:
            if it != "" and it.split('.')[-1] in ["mp4", "avi", "mov", "wav", "mp3"]:
                f = it.replace('file:///', '')
                if f not in result:
                    result.append(f)
        self.setPlainText("\n".join(result))


# VLC播放器
class Player(QtWidgets.QWidget):
    """A simple Media Player using VLC and Qt
    """

    def __init__(self, parent=None):
        self.first = True
        self.filepath = None

        super(Player, self).__init__(parent)
        if config.is_vlc:
            self.instance = vlc.Instance()
            self.mediaplayer = self.instance.media_player_new()
        else:
            self.instance = None
            self.mediaplayer = None
        self.isPaused = False
        self.setAcceptDrops(True)

        self.createUI()

    def createUI(self):
        layout = QVBoxLayout()
        self.widget = QtWidgets.QWidget(self)
        layout.addWidget(self.widget)
        self.setLayout(layout)

        self.videoframe = QtWidgets.QFrame()
        self.videoframe.setToolTip(transobj['vlctips'] + (transobj['vlctips2'] if not config.is_vlc else ""))
        self.palette = self.videoframe.palette()
        self.palette.setColor(QtGui.QPalette.Window,
                              QtGui.QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        # self.positionslider.setToolTip("")
        self.positionslider.setMaximum(1000)

        self.hbuttonbox = QtWidgets.QHBoxLayout()
        self.playbutton = QtWidgets.QPushButton("Play" if config.is_vlc else "No VLC")
        self.playbutton.setStyleSheet("""background-color:rgb(50,50,50);""")
        self.hbuttonbox.addWidget(self.playbutton)

        self.selectbutton = QtWidgets.QPushButton(transobj['selectmp4'])
        self.selectbutton.setStyleSheet("""background-color:rgb(50,50,50);""")
        self.hbuttonbox.addWidget(self.selectbutton)
        self.selectbutton.clicked.connect(self.mouseDoubleClickEvent)

        if config.is_vlc:
            self.positionslider.sliderMoved.connect(self.setPosition)
            self.playbutton.clicked.connect(self.PlayPause)
        else:
            self.novlcshowvideo = QtWidgets.QLabel()
            self.novlcshowvideo.setStyleSheet("""color:rgb(255,255,255)""")
            self.hbuttonbox.addWidget(self.novlcshowvideo)

        self.hbuttonbox.addStretch(1)
        self.volumeslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.volumeslider.setMaximum(100)
        # self.volumeslider.setToolTip("调节音量")
        self.hbuttonbox.addWidget(self.volumeslider)
        if config.is_vlc:
            self.volumeslider.valueChanged.connect(self.setVolume)
            self.volumeslider.setValue(self.mediaplayer.audio_get_volume())

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addWidget(self.videoframe)
        self.vboxlayout.addWidget(self.positionslider)
        self.vboxlayout.addLayout(self.hbuttonbox)

        self.widget.setLayout(self.vboxlayout)
        if config.is_vlc:
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(200)
            self.timer.timeout.connect(self.updateUI)

    def mouseDoubleClickEvent(self, e=None):
        fname, _ = QFileDialog.getOpenFileName(self, transobj['selectmp4'], os.path.expanduser('~') + "\\Videos",
                                               "Video files(*.mp4 *.avi *.mov)")
        if fname:
            self.OpenFile(fname)

    def dragEnterEvent(self, event):
        print(event.mimeData().text())
        ext = event.mimeData().text().lower().split('.')[1]
        print(f"{ext=}")
        if ext in ["mp4", "avi", "mov"]:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        filepath = event.mimeData().text()
        self.OpenFile(filepath.replace('file:///', ''))

    def PlayPause(self):
        if not self.mediaplayer:
            return
        if self.filepath is None:
            return self.mouseDoubleClickEvent()
        if self.mediaplayer.get_state() == vlc.State.Playing:
            self.mediaplayer.pause()
            self.playbutton.setText("Play")
        else:
            if self.mediaplayer.play() == -1:
                time.sleep(0.2)
                return

            self.timer.start()
            self.mediaplayer.play()
            self.playbutton.setText("Pause")

    def OpenFile(self, filepath=None):
        if filepath is not None:
            self.filepath = filepath
        elif self.filepath is None:
            return
        if not self.mediaplayer:
            print(self.filepath)
            self.novlcshowvideo.setText(self.filepath)
            return

        self.media = self.instance.media_new(self.filepath)
        self.mediaplayer.set_media(self.media)
        self.media.parse()
        if sys.platform.startswith('linux'):  # for Linux using the X Server
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32":  # for Windows
            self.mediaplayer.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin":  # for MacOS
            self.mediaplayer.set_nsobject(int(self.videoframe.winId()))
        self.PlayPause()

    def setVolume(self, Volume):
        self.mediaplayer.audio_set_volume(Volume)

    def setPosition(self, position):
        print(f"{position=}")
        self.mediaplayer.set_position(position / 1000.0)

    def updateUI(self):
        percent = int(self.mediaplayer.get_position() * 1000)
        self.positionslider.setValue(percent)
        # 结束重放
        if self.mediaplayer.get_state() == vlc.State.Ended:
            self.setPosition(0.0)
            self.positionslider.setValue(0)
            self.playbutton.setText("Play")
            print("播放完毕停止了")
            self.timer.stop()
            self.mediaplayer.stop()
            self.OpenFile()


# 执行 ffmpeg 线程
class Worker(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, cmd_list, func_name="", parent=None):
        super(Worker, self).__init__(parent)
        self.cmd_list = cmd_list
        self.func_name = func_name

    def run(self):
        for cmd in self.cmd_list:
            logger.info(f"Will execute: ffmpeg {cmd=}")
            try:
                print(f'{cmd=}')
                print(runffmpeg(cmd))
                # m = re.search(r"-i\s\"?(.*?)\"?\s", cmd, re.I | re.S)
            except Exception as e:
                logger.error("FFmepg exec error:" + str(e))
                return f'[error]{str(e)}'
        self.post_message("end", "End\n")

    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))


# 执行语音识别
class WorkerWhisper(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, audio_path, model, language, func_name, parent=None):
        super(WorkerWhisper, self).__init__(parent)
        self.func_name = func_name
        self.audio_path = audio_path
        self.model = model
        self.language = language

    def run(self):
        text = transcribe_audio(self.audio_path, self.model, self.language)
        self.post_message("end", text)

    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))


# 合成
class WorkerTTS(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, parent=None, *,
                 text=None,
                 role=None,
                 rate=None,
                 filename=None,
                 tts_type=None,
                 func_name=None,
                 voice_autorate=False,
                 tts_issrt=False):
        super(WorkerTTS, self).__init__(parent)
        self.func_name = func_name
        self.text = text
        self.role = role
        self.rate = rate
        self.filename = filename
        self.tts_type = tts_type
        self.tts_issrt = tts_issrt
        self.voice_autorate = voice_autorate
        self.tmpdir = f'{homedir}/tmp'
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir, exist_ok=True)

    def run(self):
        print(f"start hecheng {self.tts_type=},{self.role=},{self.rate=},{self.filename=}")

        if self.tts_issrt:
            print(f'tts_issrt')
            try:
                q = self.before_tts()
            except Exception as e:
                print(e)
                self.post_message('end', f'before dubbing error:{str(e)}')
                return
            try:
                self.exec_tts(q)
            except Exception as e:
                self.post_message('end', f'srt create dubbing error:{str(e)}')
                return
        else:
            mp3 = self.filename.replace('.wav', '.mp3')
            text_to_speech(
                text=self.text,
                role=self.role,
                rate=self.rate,
                filename=mp3,
                tts_type=self.tts_type
            )
            runffmpeg([
                '-y',
                '-i',
                f'{mp3}',
                "-c:a",
                "pcm_s16le",
                f'{self.filename}',
            ])
            os.unlink(mp3)
        self.post_message("end", "Ended")

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
        # 如果仅仅生成配音，则不限制时长
        # 整合一个队列到 exec_tts 执行
        queue_tts = []
        # 获取字幕
        print(f'before-tts,{self.text=}')
        subs = get_subtitle_from_srt(self.text, is_file=False)
        print(f'{subs=}')
        rate = int(str(self.rate).replace('%', ''))
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for it in subs:
            queue_tts.append({
                "text": it['text'],
                "role": self.role,
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "rate": rate,
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "filename": f"{self.tmpdir}/tts-{it['start_time']}.mp3"})
        print(queue_tts)
        return queue_tts

    # 执行 tts配音，配音后根据条件进行视频降速或配音加速处理
    def exec_tts(self, queue_tts):
        queue_copy = copy.deepcopy(queue_tts)

        def get_item(q):
            return {"text": q['text'], "role": q['role'], "rate": q['rate'], "filename": q["filename"],
                    "tts_type": self.tts_type}

        # 需要并行的数量3
        while len(queue_tts) > 0:
            try:
                tolist = [threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0)))]
                if len(queue_tts) > 0:
                    tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))
                if len(queue_tts) > 0:
                    tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))

                for t in tolist:
                    t.start()
                for t in tolist:
                    t.join()
            except Exception as e:
                self.post_message('end', f'[error]regcon error:{str(e)}')
                return False
        segments = []
        start_times = []
        # 如果设置了视频自动降速 并且有原音频，需要视频自动降速
        if len(queue_copy) < 1:
            return self.post_message('end', f'出错了，{queue_copy=}')
        try:
            # 偏移时间，用于每个 start_time 增减
            offset = 0
            # 将配音和字幕时间对其，修改字幕时间
            print(f'{queue_copy=}')
            srtmeta = []
            for (idx, it) in enumerate(queue_copy):
                srtmeta_item = {
                    'dubbing_time': -1,
                    'source_time': -1,
                    'speed_up': -1,
                }
                logger.info(f'\n\n{idx=},{it=}')
                it['start_time'] += offset
                it['end_time'] += offset
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    start_times.append(it['start_time'])
                    segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                    queue_copy[idx] = it
                    continue
                audio_data = AudioSegment.from_file(it['filename'], format="mp3")
                mp3len = len(audio_data)

                # 原字幕发音时间段长度
                wavlen = it['end_time'] - it['start_time']

                if wavlen == 0:
                    queue_copy[idx] = it
                    continue
                # 新配音时长
                srtmeta_item['dubbing_time'] = mp3len
                srtmeta_item['source_time'] = wavlen
                srtmeta_item['speed_up'] = 0
                # 新配音大于原字幕里设定时长
                diff = mp3len - wavlen
                if diff > 0 and self.voice_autorate:
                    speed = mp3len / wavlen
                    speed = 1.8 if speed > 1.8 else speed
                    srtmeta_item['speed_up'] = speed
                    # 新的长度
                    mp3len = mp3len / speed
                    diff = mp3len - wavlen
                    if diff < 0:
                        diff = 0
                    # 音频加速 最大加速2倍
                    audio_data = speed_change(audio_data, speed)
                    # 增加新的偏移
                    offset += diff
                elif diff > 0:
                    offset += diff
                it['end_time'] = it['start_time'] + mp3len
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                queue_copy[idx] = it
                start_times.append(it['start_time'])
                segments.append(audio_data)
                srtmeta.append(srtmeta_item)
            # 原 total_length==0，说明没有上传视频，仅对已有字幕进行处理，不需要裁切音频
            self.merge_audio_segments(segments, start_times)
        except Exception as e:
            self.post_message('end', f"[error] exec_tts :" + str(e))
            return False
        return True

    # join all short audio to one ,eg name.mp4  name.mp4.wav
    def merge_audio_segments(self, segments, start_times):
        print("merge")
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
        # 创建配音后的文件
        merged_audio.export(self.filename, format="wav")

        return merged_audio

    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initUI()
        self.setWindowIcon(QIcon("./icon.ico"))
        self.setWindowTitle(f"Video Toolbox {VERSION}")

    def closeEvent(self, event):
        # 拦截窗口关闭事件，隐藏窗口而不是真正关闭
        self.hide()
        event.ignore()

    def hideWindow(self):
        # 示例按钮点击时调用，隐藏窗口
        self.hide()

    def initUI(self):
        self.settings = QSettings("Jameson", "VideoTranslate")
        # tab-1
        self.yspfl_video_wrap = Player(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.yspfl_video_wrap.sizePolicy().hasHeightForWidth())
        self.yspfl_video_wrap.setSizePolicy(sizePolicy)
        self.yspfl_widget.insertWidget(0, self.yspfl_video_wrap)
        self.yspfl_video_wrap.setStyleSheet("""background-color:rgb(10,10,10)""")
        self.yspfl_video_wrap.setAcceptDrops(True)

        # 启动音视频分离
        self.yspfl_startbtn.clicked.connect(self.yspfl_start_fn)
        self.yspfl_openbtn1.clicked.connect(lambda: self.yspfl_open_fn("video"))
        self.yspfl_openbtn2.clicked.connect(lambda: self.yspfl_open_fn("wav"))

        # tab-2 音视频字幕合并
        self.ysphb_selectvideo.clicked.connect(lambda: self.ysphb_select_fun("video"))
        self.ysphb_selectwav.clicked.connect(lambda: self.ysphb_select_fun("wav"))
        self.ysphb_selectsrt.clicked.connect(lambda: self.ysphb_select_fun("srt"))
        self.ysphb_startbtn.clicked.connect(self.ysphb_start_fun)
        self.ysphb_opendir.clicked.connect(lambda: self.opendir_fn(os.path.dirname(self.ysphb_out.text())))

        # tab-3 语音识别 先添加按钮
        self.shibie_dropbtn = DropButton(transobj['xuanzeyinshipin'])
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.shibie_dropbtn.sizePolicy().hasHeightForWidth())
        self.shibie_dropbtn.setSizePolicy(sizePolicy)
        self.shibie_dropbtn.setMinimumSize(0, 150)
        self.shibie_widget.insertWidget(0, self.shibie_dropbtn)

        self.langauge_name = list(langlist.keys())  # list(language_code_list["zh"].keys())
        self.shibie_language.addItems(self.langauge_name)
        self.shibie_model.addItems(["base", "small", "medium", "large", "large-v3"])
        self.shibie_startbtn.clicked.connect(self.shibie_start_fun)
        self.shibie_savebtn.clicked.connect(self.shibie_save_fun)

        # tab-4 语音合成
        self.hecheng_plaintext = Textedit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.hecheng_plaintext.sizePolicy().hasHeightForWidth())
        self.hecheng_plaintext.setSizePolicy(sizePolicy)
        self.hecheng_plaintext.setMinimumSize(0, 150)
        self.hecheng_layout.insertWidget(0, self.hecheng_plaintext)
        self.hecheng_language.addItems(['-'] + self.langauge_name)
        self.hecheng_role.addItems(['No'])
        self.hecheng_language.currentTextChanged.connect(self.hecheng_language_fun)
        self.hecheng_startbtn.clicked.connect(self.hecheng_start_fun)
        self.hecheng_opendir.clicked.connect(lambda: self.opendir_fn(self.hecheng_out.text().strip()))
        # 设置 tts_type
        self.tts_type.addItems(config.params['tts_type_list'])
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.tts_type_change)
        self.tts_issrt.stateChanged.connect(self.tts_issrt_change)

        # tab-5 格式转换
        self.geshi_input = TextGetdir()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.geshi_result.sizePolicy().hasHeightForWidth())
        self.geshi_input.setSizePolicy(sizePolicy)
        self.geshi_input.setMinimumSize(300, 0)

        self.geshi_input.setPlaceholderText(transobj['tuodongdaoci'])
        self.geshi_input.setReadOnly(True)
        self.geshi_layout.insertWidget(0, self.geshi_input)
        self.geshi_mp4.clicked.connect(lambda: self.geshi_start_fun("mp4"))
        self.geshi_avi.clicked.connect(lambda: self.geshi_start_fun("avi"))
        self.geshi_mov.clicked.connect(lambda: self.geshi_start_fun("mov"))
        self.geshi_mp3.clicked.connect(lambda: self.geshi_start_fun("mp3"))
        self.geshi_wav.clicked.connect(lambda: self.geshi_start_fun("wav"))
        self.geshi_output.clicked.connect(lambda: self.opendir_fn(f'{homedir}/conver'))
        if not os.path.exists(f'{homedir}/conver'):
            os.makedirs(f'{homedir}/conver', exist_ok=True)

        # 混流
        self.hun_file1btn.clicked.connect(lambda: self.hun_get_file('file1'))
        self.hun_file2btn.clicked.connect(lambda: self.hun_get_file('file2'))
        self.hun_startbtn.clicked.connect(self.hun_fun)
        self.hun_opendir.clicked.connect(lambda: self.opendir_fn(self.hun_out.text()))

        # 翻译
        proxy = set_proxy()
        if proxy:
            self.fanyi_proxy.setText(proxy)
        self.languagename = list(langlist.keys())
        self.fanyi_target.addItems(["-"] + self.languagename)
        self.fanyi_import.clicked.connect(self.fanyi_import_fun)
        self.fanyi_start.clicked.connect(self.fanyi_start_fun)
        self.fanyi_translate_type.addItems(
            ["google", "baidu", "chatGPT", 'Azure', 'Gemini', "tencent", "DeepL", "DeepLX", "baidu(noKey)"])

        self.fanyi_sourcetext = Textedit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.geshi_result.sizePolicy().hasHeightForWidth())
        self.fanyi_sourcetext.setSizePolicy(sizePolicy)
        self.fanyi_sourcetext.setMinimumSize(300, 0)

        self.fanyi_sourcetext.setPlaceholderText(transobj['tuodongfanyi'])

        self.fanyi_layout.insertWidget(0, self.fanyi_sourcetext)

        # self.statusBar.addWidget(QLabel("如果你无法播放视频，请去下载VLC解码器 www.videolan.org/vlc"))
        self.statusBar.addPermanentWidget(QLabel("github.com/jianchang512/pyvideotrans"))

    # 获取wav件
    def hun_get_file(self, name='file1'):
        fname, _ = QFileDialog.getOpenFileName(self, "Select wav", os.path.expanduser('~'),
                                               "Audio files(*.wav)")
        if fname:
            if name == 'file1':
                self.hun_file1.setText(fname.replace('file:///', '').replace('\\', '/'))
            else:
                self.hun_file2.setText(fname.replace('file:///', '').replace('\\', '/'))

    # 文本翻译，导入文本文件
    def fanyi_import_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select txt or srt", os.path.expanduser('~'),
                                               "Text files(*.srt *.txt)")
        if fname:
            with open(fname.replace('file:///', ''), 'r', encoding='utf-8') as f:
                self.fanyi_sourcetext.setPlainText(f.read().strip())

    def render_play(self, t):
        if t != 'ok':
            return
        self.yspfl_video_wrap.close()
        self.yspfl_video_wrap = None
        self.yspfl_video_wrap = Player(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.yspfl_video_wrap.sizePolicy().hasHeightForWidth())
        self.yspfl_video_wrap.setSizePolicy(sizePolicy)
        self.yspfl_widget.insertWidget(0, self.yspfl_video_wrap)
        self.yspfl_video_wrap.setStyleSheet("""background-color:rgb(10,10,10)""")
        self.yspfl_video_wrap.setAcceptDrops(True)

    def opendir_fn(self, dirname=None):
        if not dirname:
            return
        if not os.path.isdir(dirname):
            dirname = os.path.dirname(dirname)
        QDesktopServices.openUrl(QUrl(f"file:{dirname.strip()}"))

    # 通知更新ui
    def receiver(self, json_data):
        data = json.loads(json_data)
        # fun_name 方法名，type类型，text具体文本
        if data['func_name'] == "yspfl_end":
            # 音视频分离完成了
            self.yspfl_startbtn.setText(transobj["zhixingwc"] if data['type'] == "end" else transobj["zhixinger"])
            self.yspfl_startbtn.setDisabled(False)
        elif data['func_name'] == 'ysphb_end':
            self.ysphb_startbtn.setText(transobj["zhixingwc"] if data['type'] == "end" else transobj["zhixinger"])
            self.ysphb_startbtn.setDisabled(False)
            self.ysphb_opendir.setDisabled(False)
            if data['type'] == 'end':
                basename = os.path.basename(self.ysphb_videoinput.text())
                if os.path.exists(rootdir + f"/{basename}.srt"):
                    os.unlink(rootdir + f"/{basename}.srt")
        elif data['func_name'] == 'shibie_next':
            #     转换wav完成，开始最终识别
            self.shibie_start_next_fun()
        elif data['func_name'] == "shibie_end":
            # 识别执行完成
            self.disabled_shibie(False)
            if data['type'] == 'end':
                self.shibie_startbtn.setText(transobj["zhixingwc"])
                self.shibie_text.insertPlainText(data['text'])
            else:
                self.shibie_startbtn.setText(transobj["zhixinger"])
        elif data['func_name'] == 'hecheng_end':
            self.hecheng_startbtn.setText(transobj["zhixingwc"] if data['type'] == 'end' else transobj["zhixinger"])
            self.hecheng_startbtn.setDisabled(False)
        elif data['func_name'] == 'geshi_end':
            boxcfg.geshi_num -= 1
            self.geshi_result.insertPlainText(data['text'])
            if boxcfg.geshi_num <= 0:
                self.disabled_geshi(False)
                self.geshi_result.insertPlainText(transobj["zhixingwc"])
                self.geshi_input.clear()
        elif data['func_name'] == 'hun_end':
            self.hun_startbtn.setDisabled(False)
            self.hun_out.setDisabled(False)
        elif data['func_name'] == 'fanyi_end':
            self.fanyi_start.setDisabled(False)
            self.fanyi_start.setText(transobj['starttrans'])
            self.fanyi_targettext.setPlainText(data['text'])

    # tab-1 音视频分离启动
    def yspfl_start_fn(self):
        if not self.yspfl_video_wrap.filepath:
            return QMessageBox.critical(self, transobj['anerror'], transobj['selectvideodir'])
        file = self.yspfl_video_wrap.filepath
        basename = os.path.basename(file)
        video_out = f"{homedir}/{basename}"
        if not os.path.exists(video_out):
            os.makedirs(video_out, exist_ok=True)
        self.yspfl_task = Worker(
            [['-y', '-i', file, '-an', f"{video_out}/{basename}.mp4", f"{video_out}/{basename}.wav"]], "yspfl_end",
            self)
        self.yspfl_task.update_ui.connect(self.receiver)
        self.yspfl_task.start()
        self.yspfl_startbtn.setText(transobj['running'])
        self.yspfl_startbtn.setDisabled(True)

        self.yspfl_videoinput.setText(f"{video_out}/{basename}.mp4")
        self.yspfl_wavinput.setText(f"{video_out}/{basename}.wav")

    # 音视频打开目录
    def yspfl_open_fn(self, name):
        pathdir = homedir
        if name == "video":
            pathdir = os.path.dirname(self.yspfl_videoinput.text())
        elif name == "wav":
            pathdir = os.path.dirname(self.yspfl_wavinput.text())
        QDesktopServices.openUrl(QUrl(f"file:{pathdir}"))

    # tab-2音视频合并
    def ysphb_select_fun(self, name):
        if name == "video":
            mime = "Video files(*.mp4 *.avi *.mov)"
            showname = " Video "
        elif name == "wav":
            mime = "Audio files(*.mp3 *.wav *.flac)"
            showname = " Audio "
        else:
            mime = "Srt files(*.srt)"
            showname = " srt "
        fname, _ = QFileDialog.getOpenFileName(self, f"Select {showname} file", os.path.expanduser('~') + "\\Videos",
                                               mime)
        if not fname:
            return

        if name == "video":
            self.ysphb_videoinput.setText(fname)
        elif name == "wav":
            self.ysphb_wavinput.setText(fname)
        else:
            self.ysphb_srtinput.setText(fname)
        print(fname)

    def ysphb_start_fun(self):
        # 启动合并
        videofile = self.ysphb_videoinput.text()
        basename = os.path.basename(videofile)
        srtfile = self.ysphb_srtinput.text()
        wavfile = self.ysphb_wavinput.text()

        if not videofile or not os.path.exists(videofile):
            QMessageBox.critical(self, transobj['anerror'], transobj['selectvideodir'])
            return
        if not wavfile and not srtfile:
            QMessageBox.critical(self, transobj['anerror'], transobj['yinpinhezimu'])
            return
        if not os.path.exists(wavfile) and not os.path.exists(srtfile):
            QMessageBox.critical(self, transobj['anerror'], transobj["yinpinhezimu"])
            return

        savedir = f"{homedir}/hebing-{basename}"
        if not os.path.exists(savedir):
            os.makedirs(savedir, exist_ok=True)

        cmds = []
        if wavfile and srtfile:
            tmpname = f'{config.rootdir}/tmp/{time.time()}.mp4'
            srtfile = srtfile.replace('\\', '/').replace(':', '\\\\:')
            cmds = [
                ['-y', '-i', f'{videofile}', '-i', f'{wavfile}', '-filter_complex', "[0:a][1:a]amerge=inputs=2[aout]",
                 '-map', '0:v', '-map', "[aout]", '-c:v', 'libx264', '-c:a', 'aac', tmpname],
                ['-y', '-i', f'{tmpname}', "-vf", f"subtitles={srtfile}", f'{savedir}/{basename}.mp4']
            ]
        else:
            cmd = ['-y', '-i', f'{videofile}']
            if wavfile:
                # 只存在音频，不存在字幕
                cmd += ['-i', f'{wavfile}', '-filter_complex', "[0:a][1:a]amerge=inputs=2[aout]", '-map', '0:v', '-map',
                        "[aout]", '-c:v', 'libx264', '-c:a', 'aac']
            elif srtfile:
                srtfile = srtfile.replace('\\', '/').replace(':', '\\\\:')
                cmd += ["-vf", f"subtitles={srtfile}"]

            cmd += [f'{savedir}/{basename}.mp4']
            cmds = [cmd]
        self.ysphb_task = Worker(cmds, "ysphb_end", self)
        self.ysphb_task.update_ui.connect(self.receiver)
        self.ysphb_task.start()

        self.ysphb_startbtn.setText(transobj["running"])
        self.ysphb_startbtn.setDisabled(True)
        self.ysphb_out.setText(f"{savedir}/{basename}.mp4")
        self.ysphb_opendir.setDisabled(True)

    # tab-3 语音识别 预执行，检查
    def shibie_start_fun(self):
        model = self.shibie_model.currentText()
        if not os.path.exists(rootdir + f"/models/{model}.pt"):
            return QMessageBox.critical(self, transobj['anerror'], transobj['modellost'])
        file = self.shibie_dropbtn.text()
        if not file or not os.path.exists(file):
            return QMessageBox.critical(self, transobj['anerror'], transobj['bixuyinshipin'])
        basename = os.path.basename(file)
        self.shibie_startbtn.setText(transobj["running"])
        self.disabled_shibie(True)
        self.shibie_text.clear()

        if os.path.splitext(basename)[-1].lower() in [".mp4", ".avi", ".mov"]:
            out_file = f"{homedir}/tmp/{basename}.wav"
            if not os.path.exists(f"{homedir}/tmp"):
                os.makedirs(f"{homedir}/tmp")
            try:
                print(f'{file=}')
                self.shibie_dropbtn.setText(out_file)
                self.shibie_ffmpeg_task = Worker([
                    ['-y', '-i', file, out_file]
                ], "shibie_next", self)
                self.shibie_ffmpeg_task.update_ui.connect(self.receiver)
                self.shibie_ffmpeg_task.start()
            except Exception as e:
                logger.error("执行语音识别前，先从视频中分离出音频失败：" + str(e))
                self.shibie_startbtn.setText("执行")
                self.disabled_shibie(False)
                QMessageBox.critical(self, transobj['anerror'], str(e))
        else:
            # 是音频，直接执行
            self.shibie_start_next_fun()

    # 最终执行
    def shibie_start_next_fun(self):
        file = self.shibie_dropbtn.text()
        if not os.path.exists(file):
            return QMessageBox.critical(self, transobj['anerror'], transobj['chakanerror'])
        model = self.shibie_model.currentText()
        self.shibie_task = WorkerWhisper(file, model, language_code_list["zh"][self.shibie_language.currentText()][0],
                                         "shibie_end", self)
        self.shibie_task.update_ui.connect(self.receiver)
        self.shibie_task.start()

    def shibie_save_fun(self):
        srttxt = self.shibie_text.toPlainText().strip()
        if not srttxt:
            return QMessageBox.critical(self, transobj['anerror'], transobj['srtisempty'])
        dialog = QFileDialog()
        dialog.setWindowTitle(transobj['savesrtto'])
        dialog.setNameFilters(["subtitle files (*.srt)"])
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.exec_()
        if not dialog.selectedFiles():  # If the user closed the choice window without selecting anything.
            return
        else:
            path_to_file = dialog.selectedFiles()[0]
        with open(path_to_file + f"{'' if path_to_file.endswith('.srt') else '.srt'}", "w") as file:
            file.write(srttxt)

    # 禁用启用按钮
    def disabled_shibie(self, type):
        self.shibie_startbtn.setDisabled(type)
        self.shibie_dropbtn.setDisabled(type)
        self.shibie_language.setDisabled(type)
        self.shibie_model.setDisabled(type)

    # tab-4 语音合成
    def hecheng_start_fun(self):
        txt = self.hecheng_plaintext.toPlainText().strip()
        language = self.hecheng_language.currentText()
        role = self.hecheng_role.currentText()
        rate = int(self.hecheng_rate.value())
        tts_type = self.tts_type.currentText()

        if not txt:
            return QMessageBox.critical(self, transobj['anerror'], transobj['neirongweikong'])
        if language == '-' or role == 'No':
            return QMessageBox.critical(self, transobj['anerror'], transobj['yuyanjuesebixuan'])
        if tts_type == 'openaiTTS' and not config.params['chatgpt_key']:
            return QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + "chatGPT key")
        elif tts_type == 'coquiTTS' and not config.params['coquitts_key']:
            return QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + " coquiTTS key")
        # 文件名称
        filename = self.hecheng_out.text()
        if filename and re.search(r'\\|/', filename):
            filename=""
        if not filename:
            filename = f"tts-{role}-{rate}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
        else:
            filename = filename.replace('.wav', '') + ".wav"
        if not os.path.exists(f"{homedir}/tts"):
            os.makedirs(f"{homedir}/tts", exist_ok=True)
        wavname = f"{homedir}/tts/{filename}"
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"-{rate}%"

        issrt = self.tts_issrt.isChecked()
        self.hecheng_task = WorkerTTS(self,
                                      text=txt,
                                      role=role,
                                      rate=rate,
                                      filename=wavname,
                                      tts_type=self.tts_type.currentText(),
                                      func_name="hecheng_end",
                                      voice_autorate=issrt and self.voice_autorate.isChecked(),
                                      tts_issrt=issrt)
        self.hecheng_task.update_ui.connect(self.receiver)
        self.hecheng_task.start()
        self.hecheng_startbtn.setText(transobj["running"])
        self.hecheng_startbtn.setDisabled(True)
        self.hecheng_out.setText(wavname)
        self.hecheng_out.setDisabled(True)

    def tts_issrt_change(self, state):
        if state:
            self.voice_autorate.setDisabled(False)
        else:
            self.voice_autorate.setDisabled(True)

    # tts类型改变
    def tts_type_change(self, type):
        if type == "openaiTTS":
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['openaitts_role'].split(","))
        elif type == 'coquiTTS':
            self.hecheng_role.addItems(config.params['coquitts_role'].split(","))
        elif type == 'edgeTTS':
            self.hecheng_language_fun(self.hecheng_language.currentText())

    # 合成语言变化，需要获取到角色
    def hecheng_language_fun(self, t):
        if self.tts_type.currentText() != "edgeTTS":
            return
        self.hecheng_role.clear()
        if t == '-':
            self.hecheng_role.addItems(['No'])
            return
        voice_list = config.edgeTTS_rolelist#get_edge_rolelist()
        if not voice_list:
            self.hecheng_language.setCurrentText('-')
            QMessageBox.critical(self, transobj['anerror'], transobj['nojueselist'])
            return
        try:
            vt = langlist[t][0].split('-')[0]#language_code_list['zh'][t][0].split('-')[0]
            print(f"{vt=}")
            if vt not in voice_list:
                self.hecheng_role.addItems(['No'])
                QMessageBox.critical(self, transobj['anerror'], f'{transobj["buzhichijuese"]}:{t}_{vt}')
                return
            if len(voice_list[vt]) < 2:
                self.hecheng_language.setCurrentText('-')
                QMessageBox.critical(self, transobj['anerror'], f'{transobj["buzhichijuese"]}:{t}_{vt}')
                return
            self.hecheng_role.addItems(voice_list[vt])
        except Exception as e:
            print(e)
            self.hecheng_role.addItems(["No"])

    # tab-5 转换
    def geshi_start_fun(self, ext):
        filelist = self.geshi_input.toPlainText().strip().split("\n")
        filelist_vail = []
        for it in filelist:
            if it and os.path.exists(it) and it.split('.')[-1].lower() in ['mp4', 'avi', 'mov', 'mp3', 'wav']:
                filelist_vail.append(it)
        if len(filelist_vail) < 1:
            return QMessageBox.critical(self, transobj['anerror'], transobj['nowenjian'])
        self.geshi_input.setPlainText("\n".join(filelist_vail))
        self.disabled_geshi(True)
        boxcfg.geshi_num = len(filelist_vail)
        cmdlist = []
        savedir = f"{homedir}/conver"
        if not os.path.exists(savedir):
            os.makedirs(savedir, exist_ok=True)
        for it in filelist_vail:
            basename = os.path.basename(it)
            ext_this = basename.split('.')[-1].lower()
            if ext == ext_this:
                boxcfg.geshi_num -= 1
                self.geshi_result.insertPlainText(f"{it} -> {ext}")
                continue
            if ext_this in ["wav", "mp3"] and ext in ["mp4", "mov", "avi"]:
                self.geshi_result.insertPlainText(f"{it} {transobj['yinpinbuke']} {ext} ")
                boxcfg.geshi_num -= 1
                continue
            cmdlist.append(['-y', '-i', f'{it}', f'{savedir}/{basename}.{ext}'])

        if len(cmdlist) < 1:
            self.geshi_result.insertPlainText(transobj["quanbuend"])
            self.disabled_geshi(False)
            return
        self.geshi_task = Worker(cmdlist, "geshi_end", self)
        self.geshi_task.update_ui.connect(self.receiver)
        self.geshi_task.start()

    # 禁用按钮
    def disabled_geshi(self, type):
        self.geshi_mp4.setDisabled(type)
        self.geshi_avi.setDisabled(type)
        self.geshi_mov.setDisabled(type)
        self.geshi_mp3.setDisabled(type)
        self.geshi_wav.setDisabled(type)

    # 音频混流
    def hun_fun(self):
        out = self.hun_out.text().strip()
        if out and os.path.isfile(out):
            out=""
        if not out:
            out = f'{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.wav'
        elif not out.endswith('.wav'):
            out += '.wav'
            out = out.replace('\\', '').replace('/', '')
        dirname = homedir + "/hun_liu"
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        savename = f'{dirname}/{out}'

        self.hun_out.setText(savename)

        file1 = self.hun_file1.text()
        file2 = self.hun_file2.text()

        cmd = ['-y', '-i', file1, '-i', file2, '-filter_complex',
               "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', savename]
        self.geshi_task = Worker([cmd], "hun_end", self)
        self.geshi_task.update_ui.connect(self.receiver)
        self.geshi_task.start()
        self.hun_startbtn.setDisabled(True)
        self.hun_out.setDisabled(True)

    # 翻译开始
    def fanyi_start_fun(self):
        target_language = self.fanyi_target.currentText()
        translate_type = self.fanyi_translate_type.currentText()
        if target_language == '-':
            return QMessageBox.critical(self, transobj['anerror'], transobj["fanyimoshi1"])
        proxy = self.fanyi_proxy.text()
        if proxy:
            set_proxy(proxy)
        issrt = self.fanyi_issrt.isChecked()
        source_text = self.fanyi_sourcetext.toPlainText().strip()
        if not source_text:
            return QMessageBox.critical(self, transobj['anerror'], transobj["wenbenbukeweikong"])
        # target_language = langlist[target_language][0]
        config.baidu_appid = self.settings.value("baidu_appid", "")
        config.baidu_miyue = self.settings.value("baidu_miyue", "")
        config.deepl_authkey = self.settings.value("deepl_authkey", "")
        config.deeplx_address = self.settings.value("deeplx_address", "")
        config.chatgpt_api = self.settings.value("chatgpt_api", "")
        config.chatgpt_key = self.settings.value("chatgpt_key", "")
        config.tencent_SecretId = self.settings.value("tencent_SecretId", "")
        config.tencent_SecretKey = self.settings.value("tencent_SecretKey", "")
        # os.environ['OPENAI_API_KEY'] = self.cfg['chatgpt_key']
        # google language code

        if translate_type == 'google':
            target_language = langlist[target_language][0]
        elif translate_type == 'baidu(noKey)':
            target_language = langlist[target_language][2]
        elif translate_type == 'baidu':
            # baidu language code
            target_language = langlist[target_language][2]
            if not config.baidu_appid or not config.baidu_miyue:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + 'Baidu key')
                return
        elif translate_type == 'tencent':
            #     腾讯翻译
            target_language = langlist[target_language][4]
            if not config.tencent_SecretId or not config.tencent_SecretKey:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + ' Tencent key')
                return
        elif translate_type == 'chatGPT':
            # chatGPT 翻译
            target_language = english_code_bygpt[self.languagename.index(target_language)]
            if not config.chatgpt_key:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + 'ChatGPT key')
                return
        elif translate_type == 'DeepL' or translate_type == 'DeepLX':
            # DeepL翻译
            if translate_type == 'DeepL' and not config.deepl_authkey:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + ' DeepL key')
                return
            if translate_type == 'DeepLX' and not config.deeplx_address:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + ' DeepLX url')
                return
            target_language_deepl = langlist[target_language][3]
            if target_language_deepl == 'No':
                QMessageBox.critical(self, transobj['anerror'], 'DeepL ' + transobj['buzhichifanyi'])
                return
        self.fanyi_task = FanyiWorker(translate_type, target_language, source_text, issrt, self)
        self.fanyi_task.ui.connect(self.receiver)
        self.fanyi_task.start()
        self.fanyi_start.setDisabled(True)
        self.fanyi_start.setText(transobj["running"])
        self.fanyi_targettext.clear()


class FanyiWorker(QThread):
    ui = pyqtSignal(str)

    def __init__(self, type, target_language, text, issrt, parent=None):
        super(FanyiWorker, self).__init__(parent)
        self.type = type
        self.target_language = target_language
        self.text = text
        self.issrt = issrt
        self.srts = ""

    def run(self):
        # 开始翻译,从目标文件夹读取原始字幕
        if not self.issrt:
            if self.type == 'chatGPT':
                self.srts = chatgpttrans(self.text, self.target_language, set_p=False)
            elif self.type == 'Azure':
                self.srts = azuretrans(self.text, self.target_language, set_p=False)
            elif self.type == 'Gemini':
                self.srts = geminitrans(self.text, self.target_language, set_p=False)
            elif self.type == 'google':
                self.srts = googletrans(self.text, 'auto', self.target_language, set_p=False)
            elif self.type == 'baidu':
                self.srts = baidutrans(self.text, 'auto', self.target_language, set_p=False)
            elif self.type == 'baidu(noKey)':
                self.srts = baidutrans_spider(self.text, 'auto', self.target_language, set_p=False)
            elif self.type == 'tencent':
                self.srts = tencenttrans(self.text, 'auto', self.target_language, set_p=False)
            elif self.type == 'DeepL':
                self.srts = deepltrans(self.text, self.target_language, set_p=False)
            elif self.type == 'DeepLX':
                self.srts = deeplxtrans(self.text, self.target_language, set_p=False)
        else:
            try:
                rawsrt = get_subtitle_from_srt(self.text, is_file=False)
            except Exception as e:
                print(f"整理格式化原始字幕信息出错:" + str(e), 'error')
                return ""
            if self.type in ['chatGPT', 'Azure', 'Gemini']:
                if self.type == 'chatGPT':
                    srt = chatgpttrans(rawsrt, self.target_language, set_p=False)
                elif self.type == 'Azure':
                    srt = azuretrans(rawsrt, self.target_language, set_p=False)
                elif self.type == 'Gemini':
                    srt = geminitrans(rawsrt, self.target_language, set_p=False)
                srts_tmp = ""
                for it in srt:
                    srts_tmp += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
                self.srts = srts_tmp
            else:
                # 其他翻译，逐行翻译
                for (i, it) in enumerate(rawsrt):
                    new_text = it['text']
                    if self.type == 'google':
                        new_text = googletrans(it['text'],
                                               'auto',
                                               self.target_language, set_p=False)
                    elif self.type == 'baidu':
                        new_text = baidutrans(it['text'], 'auto', self.target_language, set_p=False)
                    elif self.type == 'tencent':
                        new_text = tencenttrans(it['text'], 'auto', self.target_language, set_p=False)
                    elif self.type == 'baidu(noKey)':
                        new_text = baidutrans_spider(it['text'], 'auto', self.target_language, set_p=False)
                    elif self.type == 'DeepL':
                        new_text = deepltrans(it['text'], self.target_language, set_p=False)
                    elif self.type == 'DeepLX':
                        new_text = deeplxtrans(it['text'], self.target_language, set_p=False)
                    new_text = re.sub(r'&#\d+;', '', new_text.replace('&#39;', "'"))
                    # 更新字幕区域
                    self.srts += f"{it['line']}\n{it['time']}\n{new_text}\n\n"
        self.ui.emit(json.dumps({"func_name": "fanyi_end", "type": "end", "text": self.srts}))


if __name__ == "__main__":
    threading.Thread(target=get_edge_rolelist)

    if not os.path.exists(homedir):
        os.makedirs(homedir, exist_ok=True)
    if not os.path.exists(homedir + "/tmp"):
        os.makedirs(homedir + "/tmp", exist_ok=True)

    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        with open(f'{config.rootdir}/videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
            main.setStyleSheet(f.read())
        import qdarkstyle

        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    except:
        pass

    main.show()
    threading.Thread(target=set_proxy).start()
    if shutil.which('ffmpeg') is None:
        QMessageBox.critical(main, transobj['anerror'], transobj['ffmpegno'])

    sys.exit(app.exec())
