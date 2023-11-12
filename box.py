# primary ui
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

import cv2
import numpy

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QSettings, QUrl, pyqtSignal, QThread
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QFileDialog, QMessageBox, QPushButton, \
    QPlainTextEdit, QLabel

import box
from videotrans.configure import boxcfg
from videotrans.configure.boxcfg import logger, rootdir, homedir, lang_code, cfg
from videotrans.ui.toolbox import Ui_MainWindow
from videotrans.util.tools import runffmpeg, transcribe_audio, get_list_voices, create_voice, get_camera_list, get_proxy
import pyaudio, wave
import numpy as np


# 录制
def grab(queue, filename):
    print(f"开始录制视频{boxcfg.luzhicfg['videoFlag']=}")
    fps = 30

    # 尚未开启摄像头cam
    if boxcfg.luzhicfg['videoFlag'] == False:
        capture = cv2.VideoCapture(boxcfg.luzhicfg['camindex'])
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        capture.set(cv2.CAP_PROP_FPS, fps)

        fourcc = 0x7634706d
        video_dir = f'{homedir}/record'
        if not os.path.exists(video_dir):
            os.makedirs(video_dir, exist_ok=True)
        name = f'{video_dir}/{filename}.mp4'
        out = cv2.VideoWriter(name, fourcc, fps, (640, 480), True)
        boxcfg.luzhicfg['camera_start'] = True

    numFrames = 10
    numFramesCnt = 0
    seconds = 1
    printFlag = 0
    start_time = time.time()

    frameCnt = 0
    frameFlag = 0
    prevFrame = 0

    # 录制中
    while boxcfg.luzhicfg['running']:
        if frameFlag == 2:
            frameFlag = 0

        frame = {}
        (grabbed, img) = capture.read()
        if grabbed == False:
            boxcfg.luzhicfg['running'] = False
            break

        if boxcfg.luzhicfg['videoFlag'] == False:
            out.write(img)

        if numFramesCnt <= numFrames:
            if numFramesCnt == numFrames:
                end = time.time()
                seconds = end - start
                fps = (numFrames / seconds)
                numFramesCnt = 0

                printFlag = 1
            if numFramesCnt == 0:
                start = time.time()
            numFramesCnt += 1
        if printFlag == 1:
            cv2.putText(img, f" {int(time.time()-start_time)}s, Frame Rate:{int(fps)}", (1, 20), 2, .8, (0, 255, 0))
        else:
            cv2.putText(img, "Frame Rate = " + "Acquiring ... ", (1, 20), 2, .8, (0, 255, 0))

        frame["img"] = img
        (h, w) = img.shape[:2]
        (B, G, R) = cv2.split(img)
        if queue.qsize() < 1:
            queue.put(frame)
        else:
            pass
            # boxcfg.luzhicfg['running'] = False

        if boxcfg.luzhicfg['running'] == False:
            capture.release()
            boxcfg.luzhicfg['quitFlag'] = True
            break


# 更新视频画面
class OrangeImageWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(OrangeImageWidget, self).__init__(parent)
        self.image = None

    def setImage(self, image):
        self.image = image
        sz = image.size()
        self.setMinimumSize(sz)
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.image:
            qp.drawImage(QtCore.QPoint(0, 0), self.image)
        qp.end()


# 录音

def listen(filename):
    print(f"开始录制音频，{filename=}")
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    WAVE_OUTPUT_FILENAME = f'{homedir}/record/{filename}.wav'

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    print("开始!计时")
    while not boxcfg.luzhicfg['camera_start']:
        time.sleep(0.1)

    frames = []
    while boxcfg.luzhicfg['running']:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    print("录音结束")

    stream.stop_stream()
    stream.close()
    p.terminate()
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()


class DropButton(QPushButton):
    def __init__(self, text=""):
        super(DropButton, self).__init__(text)
        self.setAcceptDrops(True)
        self.clicked.connect(self.get_file)

    def get_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "选择音视频文件", os.path.expanduser('~') + "\\Videos",
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

try:
    import vlc


    # VLC播放器
    class Player(QtWidgets.QWidget):
        """A simple Media Player using VLC and Qt
        """

        def __init__(self, parent=None):
            self.first = True
            self.filepath = None
            super(Player, self).__init__(parent)
            self.instance = vlc.Instance()
            self.mediaplayer = self.instance.media_player_new()
            self.isPaused = False
            self.setAcceptDrops(True)

            self.createUI()

        def createUI(self):
            layout = QVBoxLayout()
            self.widget = QtWidgets.QWidget(self)
            layout.addWidget(self.widget)
            self.setLayout(layout)

            self.videoframe = QtWidgets.QFrame()
            self.videoframe.setToolTip("拖动视频到此播放或者双击选择视频")
            self.palette = self.videoframe.palette()
            self.palette.setColor(QtGui.QPalette.Window,
                                  QtGui.QColor(0, 0, 0))
            self.videoframe.setPalette(self.palette)
            self.videoframe.setAutoFillBackground(True)

            self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
            self.positionslider.setToolTip("进度")
            self.positionslider.setMaximum(1000)
            self.positionslider.sliderMoved.connect(self.setPosition)

            self.hbuttonbox = QtWidgets.QHBoxLayout()
            self.playbutton = QtWidgets.QPushButton("点击播放")
            self.playbutton.setStyleSheet("""background-color:rgb(50,50,50);border-color:rgb(210,210,210)""")
            self.hbuttonbox.addWidget(self.playbutton)
            self.selectbutton = QtWidgets.QPushButton("选择一个视频")
            self.selectbutton.setStyleSheet("""background-color:rgb(50,50,50);border-color:rgb(210,210,210)""")
            self.hbuttonbox.addWidget(self.selectbutton)
            self.playbutton.clicked.connect(self.PlayPause)
            self.selectbutton.clicked.connect(self.mouseDoubleClickEvent)

            self.hbuttonbox.addStretch(1)
            self.volumeslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
            self.volumeslider.setMaximum(100)
            self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
            self.volumeslider.setToolTip("调节音量")
            self.hbuttonbox.addWidget(self.volumeslider)
            self.volumeslider.valueChanged.connect(self.setVolume)

            self.vboxlayout = QtWidgets.QVBoxLayout()
            self.vboxlayout.addWidget(self.videoframe)
            self.vboxlayout.addWidget(self.positionslider)
            self.vboxlayout.addLayout(self.hbuttonbox)

            self.widget.setLayout(self.vboxlayout)

            self.timer = QtCore.QTimer(self)

            self.timer.setInterval(200)
            self.timer.timeout.connect(self.updateUI)

        def mouseDoubleClickEvent(self, e=None):
            fname, _ = QFileDialog.getOpenFileName(self, "打开视频文件", os.path.expanduser('~') + "\\Videos",
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
            if self.filepath is None:
                return self.mouseDoubleClickEvent()
            if self.mediaplayer.get_state() == vlc.State.Playing:
                self.mediaplayer.pause()
                self.playbutton.setText("播放")
            else:
                if self.mediaplayer.play() == -1:
                    time.sleep(0.2)
                    # self.OpenFile()
                    return

                self.timer.start()
                self.mediaplayer.play()
                self.playbutton.setText("暂停")

        def OpenFile(self, filepath=None):
            if filepath is not None:
                self.filepath = filepath
            elif self.filepath is None:
                return
            self.media = self.instance.media_new(self.filepath)
            self.mediaplayer.set_media(self.media)

            self.media.parse()
            # self.setWindowTitle(self.media.get_meta(0))

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
            # 打开时先暂停
            # if self.first and self.mediaplayer.get_state() == vlc.State.Playing:
            #     self.first = False
            #     self.mediaplayer.pause()
            #     self.playbutton.setText("播放")

            # 结束重放
            if self.mediaplayer.get_state() == vlc.State.Ended:
                self.setPosition(0.0)
                self.positionslider.setValue(0)
                self.playbutton.setText("播放")
                print("播放完毕停止了")
                self.timer.stop()
                self.mediaplayer.stop()
                self.OpenFile()

except Exception as e:
    logger.error("VLC:"+str(e))
    class Player(QtWidgets.QWidget):
        """A simple Media Player using VLC and Qt
        """

        def __init__(self, parent=None):
            self.first = True
            self.filepath = None
            super(Player, self).__init__(parent)
            self.isPaused = False
            self.setAcceptDrops(True)
            self.createUI()

        def createUI(self):
            layout = QVBoxLayout()
            self.widget = QtWidgets.QWidget(self)
            layout.addWidget(self.widget)
            self.setLayout(layout)

            self.videoframe = QtWidgets.QFrame()
            self.videoframe.setToolTip("需要安装VLC解码器")
            self.palette = self.videoframe.palette()
            self.palette.setColor(QtGui.QPalette.Window,
                                  QtGui.QColor(0, 0, 0))
            self.videoframe.setPalette(self.palette)
            self.videoframe.setAutoFillBackground(True)

            self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
            self.positionslider.setToolTip("进度")
            self.positionslider.setMaximum(1000)

            self.hbuttonbox = QtWidgets.QHBoxLayout()
            self.playbutton = QtWidgets.QPushButton("请安装VLC解码器")
            self.playbutton.setStyleSheet("""background-color:rgb(50,50,50);border-color:rgb(210,210,210)""")
            self.hbuttonbox.addWidget(self.playbutton)
            self.selectbutton = QtWidgets.QPushButton("请安装VLC解码器")
            self.selectbutton.setStyleSheet("""background-color:rgb(50,50,50);border-color:rgb(210,210,210)""")
            self.hbuttonbox.addWidget(self.selectbutton)

            self.hbuttonbox.addStretch(1)
            self.volumeslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
            self.volumeslider.setMaximum(100)
            # self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
            self.volumeslider.setToolTip("调节音量")
            self.hbuttonbox.addWidget(self.volumeslider)

            self.vboxlayout = QtWidgets.QVBoxLayout()
            self.vboxlayout.addWidget(self.videoframe)
            self.vboxlayout.addWidget(self.positionslider)
            self.vboxlayout.addLayout(self.hbuttonbox)

            self.widget.setLayout(self.vboxlayout)


# 执行 ffmpeg 线程
class Worker(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, cmd_list, func_name="",parent=None):
        super(Worker, self).__init__(parent)
        self.cmd_list = cmd_list
        self.func_name = func_name



    def run(self):
        print(self.cmd_list)
        for cmd in self.cmd_list:
            logger.info(f"Will execute: ffmpeg {cmd}")
            try:
                runffmpeg(cmd)
                m = re.search(r"-i\s\"?(.*?)\"?\s", cmd, re.I | re.S)
                self.post_message("end", f"{'' if not m or not m.group(1) else m.group(1)}完成\n")
            except Exception as e:
                logger.error("FFmepg exec error:" + str(e))

    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))


# 执行语音识别
class WorkerWhisper(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, audio_path, model, language, func_name,parent=None):
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

    def __init__(self, text, role, rate, filename, func_name,parent=None):
        super(WorkerTTS, self).__init__(parent)
        self.func_name = func_name
        self.text = text
        self.role = role
        self.rate = rate
        self.filename = filename

    def run(self):
        text = create_voice(self.text, self.role, self.rate, self.filename)
        self.post_message("end", text)

    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))


# 录制线程
class WorkerVideo(QThread):
    update_ui = pyqtSignal(str)

    def __init__(self, filename, func_name, is_video, is_audio,parent=None):
        super(WorkerVideo, self).__init__(parent)
        self.func_name = func_name
        self.filename = filename
        self.is_video = is_video
        self.is_audio = is_audio

    def run(self):
        tasklist = []
        if self.is_video:
            tasklist.append(threading.Thread(target=grab, args=(boxcfg.luzhicfg['queue'], self.filename,)))
        if self.is_audio:
            tasklist.append(threading.Thread(target=listen, args=(self.filename,)))
        for t in tasklist:
            t.start()
        print(f"{self.filename=},{self.is_video=},{self.is_audio=}")
        for t in tasklist:
            t.join()
        mp4 = f"{homedir}/record/{self.filename}.mp4"
        wav = f"{homedir}/record/{self.filename}.wav"
        if self.is_video and self.is_audio:
            out = f"{homedir}/record/{self.filename}-end.mp4"
            runffmpeg([
                '-y',
                '-i',
                f'"{mp4}"',
                '-i',
                f'"{wav}"',
                '-c:v',
                'libx264',
                "-c:a",
                "aac",
                f'"{out}"',
            ])
            os.unlink(mp4)
            os.unlink(wav)
        elif self.is_video:
            out = mp4
        elif self.is_audio:
            out = wav
        self.post_message("end", out)

    def post_message(self, type, text):
        self.update_ui.emit(json.dumps({"func_name": self.func_name, "type": type, "text": text}))


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initUI()
        self.setWindowIcon(QIcon("./icon.ico"))
        self.setWindowTitle("视频工具箱 V0.9.0 - wonyes.org")

    def initUI(self):
        self.settings = QSettings("Jameson", "VideoTranslate")
        boxcfg.enable_cuda = self.settings.value("enable_cuda", False, bool)


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
        self.ysphb_opendir.clicked.connect(lambda :self.opendir_fn(os.path.dirname(self.ysphb_out.text())))

        # tab-3 语音识别 先添加按钮
        self.shibie_dropbtn = DropButton("点击选择或拖拽音视频文件到此处")
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.shibie_dropbtn.sizePolicy().hasHeightForWidth())
        self.shibie_dropbtn.setSizePolicy(sizePolicy)
        self.shibie_dropbtn.setMinimumSize(0, 150)
        self.shibie_widget.insertWidget(0, self.shibie_dropbtn)

        self.langauge_name = list(lang_code.keys())
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

        # tab-5 格式转换
        self.geshi_input = TextGetdir()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        # sizePolicy.setWidthForHeight(self.geshi_input.sizePolicy().hasWidthForHeight())
        self.geshi_input.setSizePolicy(sizePolicy)
        self.geshi_input.setMinimumSize(300, 0)
        self.geshi_input.setPlaceholderText("拖动要转换的文件到此处松开")
        self.geshi_layout.insertWidget(0, self.geshi_input)
        self.geshi_mp4.clicked.connect(lambda: self.geshi_start_fun("mp4"))
        self.geshi_avi.clicked.connect(lambda: self.geshi_start_fun("avi"))
        self.geshi_mov.clicked.connect(lambda: self.geshi_start_fun("mov"))
        self.geshi_mp3.clicked.connect(lambda: self.geshi_start_fun("mp3"))
        self.geshi_wav.clicked.connect(lambda: self.geshi_start_fun("wav"))

        # tab-6 录制摄像头
        self.get_camera_status = False

        self.luzhi_startbtn.clicked.connect(self.luzhi_startCapture_fun)
        self.luzhi_stopbtn.clicked.connect(self.luzhi_quitCapture_fun)
        self.luzhi_camera.currentIndexChanged.connect(self.luzhi_toggle_camera_fun)
        self.luzhi_camera.setDisabled(True)

        w = self.luzhi_video.width()
        h = self.luzhi_video.height()
        self.luzhi_video = OrangeImageWidget(self.luzhi_video)
        self.luzhi_video.resize(w, h)
        self.luzhi_video.setMouseTracking(True)
        self.luzhi_video.installEventFilter(self)
        self.luzhi_check.clicked.connect(self.luzhi_set_caplist)
        self.cnt = 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.luzhi_update_frame_fun)
        self.timer.start(1)
        self.luzhi_opendir.clicked.connect(lambda: self.opendir_fn(self.luzhi_out.text()))

        self.statusBar.addWidget(QLabel("如果你无法播放视频，请去下载VLC解码器 www.videolan.org/vlc"))
        self.statusBar.addPermanentWidget(QLabel("github.com/jianchang512/pyvideotrans"))

    def opendir_fn(self, dirname=None):
        if not dirname:
            return
        if not os.path.isdir(dirname):
            dirname = os.path.dirname(dirname)
        QDesktopServices.openUrl(QUrl(f"file:{dirname}"))

    # 通知更新ui
    def receiver(self, json_data):
        data = json.loads(json_data)
        # fun_name 方法名，type类型，text具体文本
        if data['func_name'] == "yspfl_end":
            # 音视频分离完成了
            self.yspfl_startbtn.setText("执行完成" if data['type'] == "end" else "执行出错")
            self.yspfl_startbtn.setDisabled(False)
        elif data['func_name'] == 'ysphb_end':
            self.ysphb_startbtn.setText("执行完成" if data['type'] == "end" else "执行出错")
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
                self.shibie_startbtn.setText("执行完成")
                self.shibie_text.insertPlainText(data['text'])
            else:
                self.shibie_startbtn.setText("执行出错")
        elif data['func_name'] == 'hecheng_end':
            self.hecheng_startbtn.setText("执行完成" if data['type'] == 'end' else "执行出错")
            self.hecheng_startbtn.setDisabled(False)
        elif data['func_name'] == 'geshi_end':
            cfg['geshi_num'] -= 1
            self.geshi_result.insertPlainText(data['text'])
            if cfg['geshi_num'] <= 0:
                self.disabled_geshi(False)
                self.geshi_result.insertPlainText("全部转换完成")
        elif data['func_name'] == 'luzhi_end':
            self.luzhi_opendir.setDisabled(False)
            self.luzhi_startbtn.setText("开始录制")
            self.luzhi_opendir.setText("打开输出目录")
            self.luzhi_out.setText(data['text'])
            self.luzhi_tips.setText("本次录制完成")

    # tab-1 音视频分离启动
    def yspfl_start_fn(self):
        if not self.yspfl_video_wrap.filepath:
            return QMessageBox.critical(self, "出错了", "必须选择视频文件")
        file = self.yspfl_video_wrap.filepath
        basename = os.path.basename(file)
        video_out = f"{homedir}/{basename}"
        if not os.path.exists(video_out):
            os.makedirs(video_out, exist_ok=True)
        self.yspfl_task = Worker([f' -y -i "{file}" -an "{video_out}/{basename}.mp4" "{video_out}/{basename}.wav"'],"yspfl_end",self)
        self.yspfl_task.update_ui.connect(self.receiver)
        self.yspfl_task.start()
        self.yspfl_startbtn.setText("执行中...")
        self.yspfl_startbtn.setDisabled(True)

        self.yspfl_videoinput.setText(f"{video_out}/{basename}.mp4")
        self.yspfl_wavinput.setText(f"{video_out}/{basename}.wav")

    # 音视频打开目录
    def yspfl_open_fn(self, name):
        pathdir = homedir
        if name == "video":
            pathdir = os.path.basename(self.yspfl_videoinput.text())
        elif name == "wav":
            pathdir = os.path.basename(self.yspfl_wavinput.text())
        QDesktopServices.openUrl(QUrl(f"file:{pathdir}"))

    # tab-2音视频合并
    def ysphb_select_fun(self, name):
        if name == "video":
            mime = "Video files(*.mp4 *.avi *.mov)"
            showname = "视频"
        elif name == "wav":
            mime = "Audio files(*.mp3 *.wav *.flac)"
            showname = "音频"
        else:
            mime = "Srt files(*.srt)"
            showname = "字幕"
        fname, _ = QFileDialog.getOpenFileName(self, f"选择{showname}文件", os.path.expanduser('~') + "\\Videos", mime)
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
            QMessageBox.critical(self, "出错了", "必须选择视频")
            return
        if not wavfile and not srtfile:
            QMessageBox.critical(self, "出错了", "音频和字幕至少要选择一个")
            return
        if not os.path.exists(wavfile) and not os.path.exists(srtfile):
            QMessageBox.critical(self, "出错了", "音频和字幕至少要选择一个")
            return

        savedir = f"{homedir}/hebing-{basename}"

        cmd = f' -y -i "{videofile}" '
        if wavfile and os.path.exists(wavfile):
            cmd += f' -i "{wavfile}" -c:v libx264 -c:a aac'
        else:
            cmd += f" -c:v libx264 "
        if srtfile and os.path.exists(srtfile):
            shutil.copy(srtfile, rootdir + f"/{basename}.srt")
            cmd += f" -vf subtitles={basename}.srt"
        if not os.path.exists(savedir):
            os.makedirs(savedir, exist_ok=True)
        cmd += f" {savedir}/{basename}.mp4"
        self.ysphb_task = Worker([cmd], "ysphb_end",self)
        self.ysphb_task.update_ui.connect(self.receiver)
        self.ysphb_task.start()
        self.ysphb_startbtn.setText("执行中...")
        self.ysphb_startbtn.setDisabled(True)
        self.ysphb_out.setText(f" {savedir}/{basename}.mp4")
        self.ysphb_opendir.setDisabled(True)



    # tab-3 语音识别 预执行，检查
    def shibie_start_fun(self):
        model = self.shibie_model.currentText()
        if not os.path.exists(rootdir + f"/models/{model}.pt"):
            return QMessageBox.critical(self, "出错了", "所选模型不存在，请先去下载后放在 /models 目录下")
        file = self.shibie_dropbtn.text()
        if not file or not os.path.exists(file):
            return QMessageBox.critical(self, "出错了", "必须选择有效的音视频文件")
        basename = os.path.basename(file)
        print(os.path.splitext(basename)[-1].lower())
        self.shibie_startbtn.setText("执行中...")
        self.disabled_shibie(True)
        self.shibie_text.clear()
        if os.path.splitext(basename)[-1].lower() in [".mp4", ".avi", ".mov"]:
            out_file = f"{homedir}/tmp/{basename}.wav"
            try:
                self.shibie_dropbtn.setText(out_file)
                self.shibie_ffmpeg_task = Worker([f' -y -i "{file}" -vn -c:a aac "{out_file}"'],
                                                 "shibie_next",self)
                self.shibie_ffmpeg_task.update_ui.connect(self.receiver)
                self.shibie_ffmpeg_task.start()
            except Exception as e:
                logger.error("执行语音识别前，先从视频中分离出音频失败：" + str(e))
                self.shibie_startbtn.setText("执行")
                self.disabled_shibie(False)
                QMessageBox.critical(self, "失败了", str(e))
        else:
            # 是音频，直接执行
            self.shibie_start_next_fun()

    # 最终执行
    def shibie_start_next_fun(self):
        file = self.shibie_dropbtn.text()
        model = self.shibie_model.currentText()
        print(f"{file=}")
        self.shibie_task = WorkerWhisper(file, model, lang_code[self.shibie_language.currentText()][0], "shibie_end",self)
        self.shibie_task.update_ui.connect(self.receiver)
        self.shibie_task.start()

    def shibie_save_fun(self):
        srttxt = self.shibie_text.toPlainText().strip()
        if not srttxt:
            return QMessageBox.critical(self, "出错了", "字幕内容为空")
        dialog = QFileDialog()
        dialog.setWindowTitle("选择保存字幕文件到..")
        dialog.setNameFilters(["subtitle files (*.srt)"])
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.exec_()
        if not dialog.selectedFiles():  # If the user closed the choice window without selecting anything.
            return
        else:
            path_to_file = dialog.selectedFiles()[0]

        # Create that file and work on it, for example:

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

        if not txt:
            return QMessageBox.critical(self, "出错了", "内容不能为空")
        if language == '-' or role == 'No':
            return QMessageBox.critical(self, "出错了", "语言和角色必须选择")

        if not os.path.exists(f"{homedir}/tts"):
            os.makedirs(f"{homedir}/tts", exist_ok=True)
        wavname = f"{homedir}/tts/tts-{role}-{rate}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"-{rate}%"
        self.hecheng_task = WorkerTTS(txt, role, rate, wavname, "hecheng_end",self)
        self.hecheng_task.update_ui.connect(self.receiver)
        self.hecheng_task.start()
        self.hecheng_startbtn.setText("执行中...")
        self.hecheng_startbtn.setDisabled(True)
        self.hecheng_out.setText(wavname + ".wav")

    # 合成语言变化，需要获取到角色
    def hecheng_language_fun(self, t):
        self.hecheng_role.clear()
        print(f"{t=}")
        if t == '-':
            self.hecheng_role.addItems(['No'])
            return
        voice_list = get_list_voices()
        if not voice_list:
            self.hecheng_language.setCurrentText('-')
            QMessageBox.critical(self, "出错了", '未获取到角色列表')
            return
        try:
            vt = lang_code[t][0].split('-')[0]
            print(f"{vt=}")
            if vt not in voice_list:
                self.hecheng_role.addItems(['No'])
                QMessageBox.critical(self, "出错了", f'不支持该语音角色:{t}_{vt}')
                return
            if len(voice_list[vt]) < 2:
                self.hecheng_language.setCurrentText('-')
                QMessageBox.critical(self, "出错了", f'不支持该语音角色:{t}_{vt}')
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
            return QMessageBox.critical(self, "出错了", "不存在有效文件")
        self.geshi_input.setPlainText("\n".join(filelist_vail))
        self.disabled_geshi(True)
        cfg['geshi_num'] = len(filelist_vail)
        cmdlist = []
        savedir = f"{homedir}/conver"
        if not os.path.exists(savedir):
            os.makedirs(savedir, exist_ok=True)
        for it in filelist_vail:
            basename = os.path.basename(it)
            ext_this = basename.split('.')[-1].lower()
            if ext == ext_this:
                cfg['geshi_num'] -= 1
                self.geshi_result.insertPlainText(f"{it} 无需转为 {ext}")
                continue
            if ext_this in ["wav", "mp3"] and ext in ["mp4", "mov", "avi"]:
                self.geshi_result.insertPlainText(f"{it} 音频不可转为 {ext}视频")
                cfg['geshi_num'] -= 1
                continue
            cmdlist.append(f'-y -i "{it}" "{savedir}/{basename}.{ext}"')

        if len(cmdlist) < 1:
            self.geshi_result.insertPlainText("全部转换完成")
            self.disabled_geshi(False)
            return
        self.geshi_task = Worker(cmdlist, "geshi_end",self)
        self.geshi_task.update_ui.connect(self.receiver)
        self.geshi_task.start()

    # 禁用按钮
    def disabled_geshi(self, type):
        self.geshi_mp4.setDisabled(type)
        self.geshi_avi.setDisabled(type)
        self.geshi_mov.setDisabled(type)
        self.geshi_mp3.setDisabled(type)
        self.geshi_wav.setDisabled(type)

    # tab-6 设置可用摄像头
    def luzhi_set_caplist(self):
        print("set 高亮进入@@@@@@@@@@@@@@@@@@@@")
        print("set 重新获取")
        get_camera_list()
        self.luzhi_camera.clear()
        print(boxcfg.camera_list)
        self.luzhi_camera.addItems(["不使用摄像头"] + [f"{i}号摄像头" for i in boxcfg.camera_list])
        self.luzhi_camera.setDisabled(False)

    # 选择摄像头变化
    def luzhi_toggle_camera_fun(self, index):
        print(f"change=={index=}")
        if len(boxcfg.camera_list) >= 1:
            boxcfg.luzhicfg['camindex'] = index - 1

    # 开启摄像头
    def luzhi_startCapture_fun(self):
        start_audio = self.luzhi_audio.isChecked()
        if boxcfg.luzhicfg['camindex'] < 0 and not start_audio:
            return QMessageBox.critical(self, "出错了", "摄像头和录制麦克风至少选择一个")
        self.luzhi_startbtn.setDisabled(True)
        self.luzhi_stopbtn.setDisabled(False)
        self.luzhi_audio.setDisabled(True)
        self.luzhi_camera.setDisabled(True)
        self.luzhi_opendir.setDisabled(True)
        boxcfg.luzhicfg['running'] = True
        boxcfg.luzhicfg['video_running'] = True
        self.thefilename = f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

        self.luzhi_video.setStyleSheet("""background-color:rgb(0,0,0)""")

        if boxcfg.luzhicfg['camindex'] >= 0 and start_audio:
            if self.cnt == 0:
                self.cnt = 1
            self.luzhi_tips.setText("正在录制视频和音频...")
            # boxcfg.luzhicfg['capture_thread'] = threading.Thread(target=grab, args=(boxcfg.luzhicfg['queue'],self.thefilename,start_audio,))
            # boxcfg.luzhicfg['capture_thread'].start()
        elif boxcfg.luzhicfg['camindex'] >= 0:
            self.luzhi_tips.setText("正在录制视频...")
        elif start_audio:
            self.luzhi_tips.setText("正在录制音频...")
            boxcfg.luzhicfg['audio_thread'] = threading.Thread(target=listen, args=(self.thefilename,))
            boxcfg.luzhicfg['audio_thread'].start()
        self.luzhi_task = WorkerVideo(self.thefilename, "luzhi_end", boxcfg.luzhicfg['camindex'] >= 0, start_audio,self)
        self.luzhi_task.update_ui.connect(self.receiver)
        self.luzhi_task.start()

    # 退出
    def luzhi_quitCapture_fun(self):
        boxcfg.luzhicfg['running'] = False
        self.luzhi_stopbtn.setDisabled(True)
        self.luzhi_camera.setDisabled(False)
        self.luzhi_startbtn.setDisabled(False)
        self.luzhi_startbtn.setText("开始录制")
        self.luzhi_audio.setDisabled(False)
        print("quit video !")
        self.luzhi_opendir.setDisabled(True)
        self.luzhi_opendir.setText("正在处理录制数据...")
        self.luzhi_tips.setText("处理录制数据中...")

    # 更新视频画面
    def luzhi_update_frame_fun(self):
        if not boxcfg.luzhicfg['queue'].empty():
            if boxcfg.luzhicfg['video_running'] == True:
                self.luzhi_startbtn.setText('录制中...')

                frame = boxcfg.luzhicfg['queue'].get()
                img = frame["img"]
                img = numpy.array(img)

                img_height, img_width, img_colors = img.shape

                scale_w = float(self.luzhi_video.width()) / float(img_width)
                scale_h = float(self.luzhi_video.height()) / float(img_height)
                scale = min([scale_w, scale_h])

                # if scale == 0:
                scale = 1

                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                height, width, bpc = img.shape
                bpl = bpc * width
                image = QtGui.QImage(img.data, width, height, bpl, QtGui.QImage.Format_RGB888)
                self.luzhi_video.setImage(image)
            else:
                self.luzhi_startbtn.setText('开始录制')


if __name__ == "__main__":
    threading.Thread(target=get_list_voices)

    if not os.path.exists(homedir):
        os.makedirs(homedir, exist_ok=True)
    if not os.path.exists(homedir + "/tmp"):
        os.makedirs(homedir + "/tmp", exist_ok=True)

    app = QApplication(sys.argv)
    main = MainWindow()
    if sys.platform == 'win32':
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    main.show()
    # threading.Thread(target=get_camera_list).start()
    get_proxy(True)
    if shutil.which('ffmpeg') is None:
        QMessageBox.critical(main, "温馨提示", "未找到 ffmpeg，软件不可用，请去 ffmpeg.org 下载并加入到系统环境变量")

    sys.exit(app.exec())
