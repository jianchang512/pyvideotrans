# -*- coding: utf-8 -*-
import os
import sys
import time

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QVBoxLayout, QFileDialog, QPushButton, \
    QPlainTextEdit

from videotrans.configure import  config

from videotrans.configure.config import transobj

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
        print(f'{files=}')
        for it in files:
            if it != "" and it.split('.')[-1] in ["mp4", "avi", "mov", "wav", "mp3"]:
                result.append(it)
        print(f'{result=}')
        if len(result) > 0:
            event.acceptProposedAction()
            print("jieshou")
        else:
            event.ignore()

    def dropEvent(self, event):
        print('============')
        files = event.mimeData().text().split("\n")
        result = []
        if self.toPlainText().strip():
            result = self.toPlainText().strip().split("\n")
        print(f'dropEvent( {result=})')
        print(f'files={files}')
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
        # if config.is_vlc:
        #     self.instance = vlc.Instance()
        #     self.mediaplayer = self.instance.media_player_new()
        # else:
        self.instance = None
        self.mediaplayer = None
        # self.isPaused = False
        self.setAcceptDrops(True)

        self.createUI()

    def createUI(self):
        layout = QVBoxLayout()
        self.widget = QtWidgets.QWidget(self)
        layout.addWidget(self.widget)
        self.setLayout(layout)

        # self.videoframe = QtWidgets.QFrame()
        # # self.videoframe.setToolTip(transobj['vlctips'] + (transobj['vlctips2'] if not config.is_vlc else ""))
        # self.palette = self.videoframe.palette()
        # self.palette.setColor(QtGui.QPalette.Window,
        #                       QtGui.QColor(0, 0, 0))
        # self.videoframe.setPalette(self.palette)
        # self.videoframe.setAutoFillBackground(True)

        # self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        # self.positionslider.setToolTip("")
        # self.positionslider.setMaximum(1000)

        self.hbuttonbox = QtWidgets.QHBoxLayout()
        # self.playbutton = QtWidgets.QPushButton("Play" if config.is_vlc else "No VLC")
        # self.playbutton.setStyleSheet("""background-color:rgb(50,50,50);""")
        # self.hbuttonbox.addWidget(self.playbutton)

        self.selectbutton = QtWidgets.QPushButton(transobj['sjselectmp4'])
        self.selectbutton.setStyleSheet("""background-color:rgb(10,10,10);""")
        self.selectbutton.setMinimumSize(0,100)
        self.hbuttonbox.addWidget(self.selectbutton)
        self.selectbutton.clicked.connect(self.mouseDoubleClickEvent)

        # if config.is_vlc:
        #     self.positionslider.sliderMoved.connect(self.setPosition)
        #     self.playbutton.clicked.connect(self.PlayPause)
        # else:
        # self.novlcshowvideo = QtWidgets.QLabel()
        # self.novlcshowvideo.setStyleSheet("""color:rgb(255,255,255)""")
        # self.hbuttonbox.addWidget(self.novlcshowvideo)
        #
        # self.hbuttonbox.addStretch(1)
        # self.volumeslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        # self.volumeslider.setMaximum(100)
        # self.volumeslider.setToolTip("调节音量")
        # self.hbuttonbox.addWidget(self.volumeslider)
        # if config.is_vlc:
        #     self.volumeslider.valueChanged.connect(self.setVolume)
        #     self.volumeslider.setValue(self.mediaplayer.audio_get_volume())

        self.vboxlayout = QtWidgets.QVBoxLayout()
        # self.vboxlayout.addWidget(self.videoframe)
        # self.vboxlayout.addWidget(self.positionslider)
        self.vboxlayout.addLayout(self.hbuttonbox)

        self.widget.setLayout(self.vboxlayout)
        # if config.is_vlc:
        #     self.timer = QtCore.QTimer(self)
        #     self.timer.setInterval(200)
        #     self.timer.timeout.connect(self.updateUI)

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

    # def PlayPause(self):
    #     if not self.mediaplayer:
    #         return
    #     if self.filepath is None:
    #         return self.mouseDoubleClickEvent()
    #     if self.mediaplayer.get_state() == vlc.State.Playing:
    #         self.mediaplayer.pause()
    #         self.playbutton.setText("Play")
    #     else:
    #         if self.mediaplayer.play() == -1:
    #             time.sleep(0.2)
    #             return
    #
    #         self.timer.start()
    #         self.mediaplayer.play()
    #         self.playbutton.setText("Pause")

    def OpenFile(self, filepath=None):
        if filepath is not None:
            self.filepath = filepath
        elif self.filepath is None:
            return
        # if not self.mediaplayer:
        #     print(self.filepath)
        self.selectbutton.setText(self.filepath)
        return

