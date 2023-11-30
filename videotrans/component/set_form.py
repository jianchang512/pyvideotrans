# set baidu appid and secrot
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog

from videotrans.configure import config
from videotrans.ui.baidu import Ui_baiduform
from videotrans.ui.chatgpt import Ui_chatgptform
from videotrans.ui.deepl import Ui_deeplform
from videotrans.ui.deeplx import Ui_deeplxform
from videotrans.ui.info import Ui_infoform
from videotrans.ui.tencent import Ui_tencentform


class BaiduForm(QDialog, Ui_baiduform):  # <===
    def __init__(self, parent=None):
        super(BaiduForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))
        # with open(f'{config.rootdir}/style.qss', 'r', encoding='utf-8') as f:
        #     self.setStyleSheet(f.read())

class TencentForm(QDialog, Ui_tencentform):  # <===
    def __init__(self, parent=None):
        super(TencentForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))
        # with open(f'{config.rootdir}/style.qss', 'r', encoding='utf-8') as f:
        #     self.setStyleSheet(f.read())


class DeepLForm(QDialog, Ui_deeplform):  # <===
    def __init__(self, parent=None):
        super(DeepLForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))
        # with open(f'{config.rootdir}/style.qss', 'r', encoding='utf-8') as f:
        #     self.setStyleSheet(f.read())


class InfoForm(QDialog, Ui_infoform):  # <===
    def __init__(self, parent=None):
        super(InfoForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))
        # with open(f'{config.rootdir}/style.qss', 'r', encoding='utf-8') as f:
        #     self.setStyleSheet(f.read())


class DeepLXForm(QDialog, Ui_deeplxform):  # <===
    def __init__(self, parent=None):
        super(DeepLXForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))
        # with open(f'{config.rootdir}/style.qss', 'r', encoding='utf-8') as f:
        #     self.setStyleSheet(f.read())


# set chatgpt api and key
class ChatgptForm(QDialog, Ui_chatgptform):  # <===
    def __init__(self, parent=None):
        super(ChatgptForm, self).__init__(parent)
        self.setupUi(self)
        self.chatgpt_model.addItems(["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4"])
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))
        # with open(f'{config.rootdir}/style.qss', 'r', encoding='utf-8') as f:
        #     self.setStyleSheet(f.read())
