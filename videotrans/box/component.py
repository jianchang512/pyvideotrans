# -*- coding: utf-8 -*-
import os

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QVBoxLayout, QFileDialog, QPushButton, QPlainTextEdit

from videotrans.configure.config import transobj


class DropButton(QPushButton):
    def __init__(self, text=""):
        super(DropButton, self).__init__(text)
        self.setAcceptDrops(True)
        self.clicked.connect(self.get_file)

    def get_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, transobj['xuanzeyinpinwenjian'],
                                               os.path.expanduser('~') + "\\Videos",
                                               filter="Video/Audio files(*.mp4 *.avi *.mov *.wav *.mp3 *.m4a *.aac *.flac)")
        if fname:
            self.setText(fname)

    def dragEnterEvent(self, event):
        ext = event.mimeData().text().lower().split('.')[1]
        if ext in ["mp4", "avi", "mov", "m4a", "wav", "aac", "mp3", "flac"]:
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
            if it != "" and it.split('.')[-1] in ["mp4", "avi", "mov", "wav", "mp3", "m4a", "aac", "flac"]:
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
            if it != "" and it.split('.')[-1] in ["mp4", "avi", "mov", "wav", "mp3", "m4a", "aac", "flac"]:
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

        self.instance = None
        self.mediaplayer = None
        self.setAcceptDrops(True)
        self.createUI()

    def createUI(self):
        layout = QVBoxLayout()
        self.widget = QtWidgets.QWidget(self)
        layout.addWidget(self.widget)
        self.setLayout(layout)

        self.hbuttonbox = QtWidgets.QHBoxLayout()

        self.selectbutton = QtWidgets.QPushButton(transobj['sjselectmp4'])
        self.selectbutton.setStyleSheet("""background-color:rgb(10,10,10);""")
        self.selectbutton.setMinimumSize(0, 100)
        self.hbuttonbox.addWidget(self.selectbutton)
        self.selectbutton.clicked.connect(self.mouseDoubleClickEvent)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addLayout(self.hbuttonbox)

        self.widget.setLayout(self.vboxlayout)

    def mouseDoubleClickEvent(self, e=None):
        fname, _ = QFileDialog.getOpenFileName(self, transobj['selectmp4'], os.path.expanduser('~') + "\\Videos",
                                               "Video files(*.mp4 *.avi *.mov)")
        if fname:
            self.OpenFile(fname)

    def dragEnterEvent(self, event):
        ext = event.mimeData().text().lower().split('.')[1]
        if ext in ["mp4", "avi", "mov"]:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        filepath = event.mimeData().text()
        self.OpenFile(filepath.replace('file:///', ''))

    def OpenFile(self, filepath=None):
        if filepath is not None:
            self.filepath = filepath
        elif self.filepath is None:
            return
        self.selectbutton.setText(self.filepath)
        return
