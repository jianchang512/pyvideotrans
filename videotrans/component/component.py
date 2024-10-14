# -*- coding: utf-8 -*-
import os

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QFileDialog, QPushButton, QPlainTextEdit

from videotrans.configure import config
from videotrans.configure.config import transobj


class DropButton(QPushButton):
    def __init__(self, text=""):
        super(DropButton, self).__init__(text)
        self.setAcceptDrops(True)
        self.clicked.connect(self.get_file)
        self.filelist = []
        self.setCursor(Qt.PointingHandCursor)

    def get_file(self):
        format_str = " ".join(['*.' + f for f in config.VIDEO_EXTS + config.AUDIO_EXITS])
        fnames, _ = QFileDialog.getOpenFileNames(self, transobj['xuanzeyinpinwenjian'],
                                                 config.params['last_opendir'],
                                                 filter=f"Video/Audio files({format_str})")
        namestr = []
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/')
            namestr.append(os.path.basename(it))
        self.filelist = fnames
        self.setText(f'{len(self.filelist)} files \n'+"\n".join(namestr))

    def dragEnterEvent(self, event):
        files = event.mimeData().text().strip().lower()
        allow = True
        for it in files.split("\n"):
            if it.split('.')[-1] not in config.VIDEO_EXTS + config.AUDIO_EXITS:
                allow = False
                break
        if allow:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        filepath = event.mimeData().text().strip().split("\n")
        self.filelist = [file.replace('file:///', '') for file in filepath]
        self.setText(f'{len(self.filelist)} files')


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

    def setText(self, filepath=None):
        try:
            with open(filepath, 'r', encoding="utf-8") as f:
                self.setPlainText(f.read().strip())
        except:
            with open(filepath, 'r', encoding="GBK") as f:
                self.setPlainText(f.read().strip())


class TextGetdir(QPlainTextEdit):
    def __init__(self):
        super(TextGetdir, self).__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        files = event.mimeData().text().split("\n")
        result = []
        for it in files:
            if it != "" and it.split('.')[-1] in config.VIDEO_EXTS + config.AUDIO_EXITS:
                result.append(it)
        if len(result) > 0:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = event.mimeData().text().split("\n")
        result = []
        if self.toPlainText().strip():
            result = self.toPlainText().strip().split("\n")
        for it in files:
            if it != "" and it.split('.')[-1] in config.VIDEO_EXTS + config.AUDIO_EXITS:
                f = it.replace('file:///', '')
                if f not in result:
                    result.append(f)
        self.setPlainText("\n".join(result))
