# set baidu appid and secrot
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog

from videotrans.configure import config
from videotrans.ui.azure import Ui_azureform
from videotrans.ui.baidu import Ui_baiduform
from videotrans.ui.chatgpt import Ui_chatgptform
from videotrans.ui.deepl import Ui_deeplform
from videotrans.ui.deeplx import Ui_deeplxform
from videotrans.ui.gemini import Ui_geminiform
from videotrans.ui.info import Ui_infoform
from videotrans.ui.setlinerole import Ui_setlinerole
from videotrans.ui.tencent import Ui_tencentform
from videotrans.ui.elevenlabs import Ui_elevenlabsform
from videotrans.ui.youtube import Ui_youtubeform

class SetLineRole(QDialog, Ui_setlinerole):  # <===
    def __init__(self, parent=None):
        super(SetLineRole, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))

class BaiduForm(QDialog, Ui_baiduform):  # <===
    def __init__(self, parent=None):
        super(BaiduForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))

class YoutubeForm(QDialog, Ui_youtubeform):  # <===
    def __init__(self, parent=None):
        super(YoutubeForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))


class TencentForm(QDialog, Ui_tencentform):  # <===
    def __init__(self, parent=None):
        super(TencentForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))


class DeepLForm(QDialog, Ui_deeplform):  # <===
    def __init__(self, parent=None):
        super(DeepLForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))

class ElevenlabsForm(QDialog, Ui_elevenlabsform):  # <===
    def __init__(self, parent=None):
        super(ElevenlabsForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))


class InfoForm(QDialog, Ui_infoform):  # <===
    def __init__(self, parent=None):
        super(InfoForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))


class DeepLXForm(QDialog, Ui_deeplxform):  # <===
    def __init__(self, parent=None):
        super(DeepLXForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))

# set chatgpt api and key
class ChatgptForm(QDialog, Ui_chatgptform):  # <===
    def __init__(self, parent=None):
        super(ChatgptForm, self).__init__(parent)
        self.setupUi(self)
        self.chatgpt_model.addItems(config.chatgpt_model_list)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
class GeminiForm(QDialog, Ui_geminiform):  # <===
    def __init__(self, parent=None):
        super(GeminiForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))

class AzureForm(QDialog, Ui_azureform):  # <===
    def __init__(self, parent=None):
        super(AzureForm, self).__init__(parent)
        self.setupUi(self)
        self.azure_model.addItems(config.chatgpt_model_list)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))