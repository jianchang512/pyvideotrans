# -*- coding: utf-8 -*-
import os

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QFileDialog, QPushButton, QPlainTextEdit

from videotrans.configure.config import tr, params
from videotrans.configure import constants
from videotrans.util._srt_parse import ass_to_srt


# 拖入的本地文件的路径，用 QUrl.toLocalFile() 取：text() 中的 URL 只去掉 file:/// 时，macOS/Linux 的路径会丢失开头的 /，
# 文件名中的 % # [ ] { } ^ ` 等字符也仍是 %25、%23、%5B 这样的编码。
# 拖入的内容中没有本地文件的 URL 时（例如从文本编辑器拖入的路径）返回 []，调用处仍按原来的方式从 text() 读取
def _local_files(mime_data):
    return [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]


class DropButton(QPushButton):
    def __init__(self, text=""):
        super(DropButton, self).__init__(text)
        self.setAcceptDrops(True)
        self.clicked.connect(self.get_file)
        self.filelist = []
        self.setCursor(Qt.PointingHandCursor)

    def get_file(self):
        format_str = " ".join(['*.' + f for f in constants.VIDEO_EXTS + constants.AUDIO_EXITS])
        fnames, _ = QFileDialog.getOpenFileNames(self, tr('xuanzeyinpinwenjian'),
                                                 params['last_opendir'],
                                                 filter=f"Video/Audio files({format_str})")
        namestr = []
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/')
            namestr.append(os.path.basename(it))
            params['last_opendir']=os.path.dirname(it)
        self.filelist = fnames
        self.setText(f'{len(self.filelist)} files \n' + "\n".join(namestr))

    def dragEnterEvent(self, event):
        files = event.mimeData().text().strip().lower()
        allow = True
        for it in files.split("\n"):
            if it.split('.')[-1] not in constants.VIDEO_EXTS + constants.AUDIO_EXITS:
                allow = False
                break
        if allow:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.filelist = _local_files(event.mimeData())
        if not self.filelist:
            filepath = event.mimeData().text().strip().split("\n")
            self.filelist = [file.replace('file:///', '') for file in filepath]
        self.setText(f'{len(self.filelist)} files \n' + "\n".join(os.path.basename(it) for it in self.filelist))



class PeiyinDropButton(QPushButton):
    def __init__(self, text=""):
        super(PeiyinDropButton, self).__init__(text)
        self.setAcceptDrops(True)
        self.clicked.connect(self.get_file)
        self.filelist = []
        self.setCursor(Qt.PointingHandCursor)

    def get_file(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, "Select srt/txt", params['last_opendir'],
                                                 "Text files(*.srt *.txt *.ass)")
        namestr = []
        filelist=[]
        for (i, it) in enumerate(fnames):
            it= it.replace('\\', '/')
            if it.endswith('.ass'):
                new_it=it[:-4]+"-from-ass.srt"
                ass_to_srt(it,new_it)
                filelist.append(new_it)
            else:
                filelist.append(it)
            namestr.append(os.path.basename(it))
            params['last_opendir']=os.path.dirname(it)
        self.filelist = filelist
        self.setText(f'{len(self.filelist)} files \n' + "\n".join(namestr))

    def dragEnterEvent(self, event):
        files = event.mimeData().text().strip().lower()
        allow = True
        for it in files.split("\n"):
            if it.split('.')[-1] not in ['srt','txt']:
                allow = False
                break
        if allow:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.filelist = _local_files(event.mimeData())
        if not self.filelist:
            filepath = event.mimeData().text().strip().split("\n")
            self.filelist = [file.replace('file:///', '') for file in filepath]
        self.setText(f'{len(self.filelist)} files \n' + "\n".join(os.path.basename(it) for it in self.filelist))



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
        files = _local_files(event.mimeData())
        filepath = files[0] if files else event.mimeData().text().replace('file:///', '')
        with open(filepath, 'r', encoding="utf-8") as f:
            self.setPlainText(f.read().strip())

    def setText(self, filepath=None):
        try:
            with open(filepath, 'r', encoding="utf-8") as f:
                self.setPlainText(f.read().strip())
        except Exception:
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
            if it != "" and it.split('.')[-1] in constants.VIDEO_EXTS + constants.AUDIO_EXITS:
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
            if it != "" and it.split('.')[-1] in constants.VIDEO_EXTS + constants.AUDIO_EXITS:
                f = it.replace('file:///', '')
                if f not in result:
                    result.append(f)
        self.setPlainText("\n".join(result))
