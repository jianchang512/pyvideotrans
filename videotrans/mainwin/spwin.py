import os
import shutil
import threading
import time

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings, Qt, QSize, QTimer
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QLabel, QPushButton, QToolBar, QWidget, QVBoxLayout, QApplication
import warnings

from videotrans.task.get_role_list import GetRoleWorker

warnings.filterwarnings('ignore')

from videotrans.translator import TRANSNAMES
from videotrans.configure import config
from videotrans import VERSION, configure
from videotrans.component.controlobj import TextGetdir
from videotrans.ui.en import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.task = None
        self.shitingobj = None
        self.youw = None
        self.processbtns = {}
        screen_resolution = QApplication.desktop().screenGeometry()
        width, height = screen_resolution.width(), screen_resolution.height()
        self.width = int(width * 0.8)
        if self.width < 1400:
            self.width = 1400
        elif self.width > 1900:
            self.width = 1800
        self.resize(self.width, height - 220)
        # 当前所有可用角色列表
        self.current_rolelist = []
        config.params['line_roles'] = {}
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
        self.rawtitle = f"{config.transobj['softname']} {VERSION}"
        self.setWindowTitle(self.rawtitle)
        # 检查窗口是否打开
        self.initUI()

    def initUI(self):

        self.settings = g
        # 获取最后一次选择的目录
        self.last_dir = self.settings.value("last_dir", ".", str)
        # language code
        self.languagename = config.langnamelist
        self.app_mode = 'biaozhun'
        self.splitter.setSizes([self.width - 400, 400])
        # start
        self.get_setting()

        # 隐藏倒计时
        self.stop_djs.hide()
        # subtitle btn
        self.continue_compos.hide()

        # select and save

        self.source_mp4.setAcceptDrops(True)
        self.target_dir.setAcceptDrops(True)
        self.proxy.setText(config.proxy)

        # language
        self.source_language.addItems(self.languagename)
        self.source_language.setCurrentIndex(2)

        # 目标语言改变时，如果当前tts是 edgeTTS，则根据目标语言去修改显示的角色
        self.target_language.addItems(["-"] + self.languagename)
        # 目标语言改变

        self.listen_btn.hide()

        #  translation type
        self.translate_type.addItems(TRANSNAMES)
        self.translate_type.setCurrentText(
            config.params['translate_type'] if config.params['translate_type'] in TRANSNAMES else TRANSNAMES[0])

        #         model
        self.whisper_type.addItems([config.transobj['whisper_type_all'], config.transobj['whisper_type_split']])
        if config.params['whisper_type']:
            self.whisper_type.setCurrentIndex(0 if config.params['whisper_type'] == 'all' else 1)
        self.whisper_model.addItems(['base', 'small', 'medium', 'large-v3'])
        self.whisper_model.setCurrentText(config.params['whisper_model'])

        #
        self.voice_rate.setText(config.params['voice_rate'])
        self.voice_silence.setText(config.params['voice_silence'])

        # 设置角色类型，如果当前是OPENTTS或 coquiTTS则设置，如果是edgeTTS，则为No
        if config.params['tts_type'] == 'edgeTTS':
            self.voice_role.addItems(['No'])
        elif config.params['tts_type'] == 'openaiTTS':
            self.voice_role.addItems(['No'] + config.params['openaitts_role'].split(','))
        elif config.params['tts_type'] == 'elevenlabsTTS':
            self.voice_role.addItems(['No'])
        # 设置 tts_type
        self.tts_type.addItems(config.params['tts_type_list'])
        self.tts_type.setCurrentText(config.params['tts_type'])

        self.enable_cuda.setChecked(config.params['cuda'])

        # subtitle 0 no 1=embed subtitle 2=softsubtitle
        self.subtitle_type.addItems(
            [config.transobj['nosubtitle'], config.transobj['embedsubtitle'], config.transobj['softsubtitle']])
        self.subtitle_type.setCurrentIndex(config.params['subtitle_type'])

        # 字幕编辑
        self.subtitle_area = TextGetdir(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.subtitle_area.setSizePolicy(sizePolicy)
        self.subtitle_area.setMinimumSize(300, 0)
        self.subtitle_area.setPlaceholderText(config.transobj['subtitle_tips'])

        self.subtitle_layout.insertWidget(0, self.subtitle_area)

        self.listen_peiyin.setDisabled(True)

        # 创建 Scroll Area
        self.scroll_area.setWidgetResizable(True)

        # 创建一个 QWidget 作为 Scroll Area 的 viewport
        viewport = QWidget(self.scroll_area)
        self.scroll_area.setWidget(viewport)

        # 创建一个垂直布局管理器，用于在 viewport 中放置按钮
        self.processlayout = QVBoxLayout(viewport)
        # 设置布局管理器的对齐方式为顶部对齐
        self.processlayout.setAlignment(Qt.AlignTop)

        # 底部状态栏
        self.statusLabel = QLabel(config.transobj['modelpathis'] + " /models")
        self.statusLabel.setStyleSheet("color:#00a67d")
        self.statusBar.addWidget(self.statusLabel)

        self.rightbottom = QPushButton(config.transobj['juanzhu'])
        self.rightbottom.setStyleSheet("background-color:#32414B;color:#ffffff")
        self.rightbottom.setCursor(QtCore.Qt.PointingHandCursor)

        self.container = QToolBar()
        self.container.addWidget(self.rightbottom)
        self.statusBar.addPermanentWidget(self.container)

        # 设置QAction的大小
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # 设置QToolBar的大小，影响其中的QAction的大小
        self.toolBar.setIconSize(QSize(100, 45))  # 设置图标大小
        # time.sleep(2)
        # self.show()
        self.bind_action()

    def bind_action(self):
        from videotrans.mainwin.secwin import SecWindow
        self.util = SecWindow(self)

        # menubar
        self.import_sub.clicked.connect(self.util.import_sub_fun)
        self.listen_peiyin.clicked.connect(self.util.shiting_peiyin)
        self.set_line_role.clicked.connect(self.util.set_line_role_fun)
        self.startbtn.clicked.connect(self.util.check_start)
        self.stop_djs.clicked.connect(self.util.reset_timeid)
        self.continue_compos.clicked.connect(self.util.set_djs_timeout)
        self.btn_get_video.clicked.connect(self.util.get_mp4)
        self.btn_save_dir.clicked.connect(self.util.get_save_dir)
        self.open_targetdir.clicked.connect(lambda: self.util.open_dir(self.target_dir.text()))
        self.target_language.currentTextChanged.connect(self.util.set_voice_role)
        self.voice_role.currentTextChanged.connect(self.util.show_listen_btn)
        self.listen_btn.clicked.connect(self.util.listen_voice_fun)
        self.translate_type.currentTextChanged.connect(self.util.set_translate_type)
        self.whisper_type.currentIndexChanged.connect(self.util.check_whisper_type)

        self.whisper_model.currentTextChanged.connect(self.util.check_whisper_model)
        self.voice_rate.textChanged.connect(self.util.voice_rate_changed)
        self.voice_autorate.stateChanged.connect(
            lambda: self.util.autorate_changed(self.voice_autorate.isChecked(), "voice"))
        self.video_autorate.stateChanged.connect(
            lambda: self.util.autorate_changed(self.video_autorate.isChecked(), "video"))
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.util.tts_type_change)

        self.enable_cuda.stateChanged.connect(self.util.check_cuda)
        self.actionbaidu_key.triggered.connect(self.util.set_baidu_key)
        self.actionazure_key.triggered.connect(self.util.set_azure_key)
        self.actiongemini_key.triggered.connect(self.util.set_gemini_key)
        self.actiontencent_key.triggered.connect(self.util.set_tencent_key)
        self.actionchatgpt_key.triggered.connect(self.util.set_chatgpt_key)
        self.actiondeepL_key.triggered.connect(self.util.set_deepL_key)
        self.actionElevenlabs_key.triggered.connect(self.util.set_elevenlabs_key)
        self.actiondeepLX_address.triggered.connect(self.util.set_deepLX_address)
        self.action_ffmpeg.triggered.connect(lambda: self.util.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.util.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.util.open_url('discord'))
        self.action_website.triggered.connect(lambda: self.util.open_url('website'))
        self.action_issue.triggered.connect(lambda: self.util.open_url('issue'))
        self.action_tool.triggered.connect(lambda: self.util.open_toolbox(0, False))
        self.actionyoutube.triggered.connect(self.util.open_youtube)
        self.action_about.triggered.connect(self.util.about)

        self.action_biaozhun.triggered.connect(self.util.set_biaozhun)
        self.action_tiquzimu.triggered.connect(self.util.set_tiquzimu)
        self.action_tiquzimu_no.triggered.connect(self.util.set_tiquzimu_no)
        self.action_zimu_video.triggered.connect(self.util.set_zimu_video)
        self.action_zimu_peiyin.triggered.connect(self.util.set_zimu_peiyin)
        self.action_yuyinshibie.triggered.connect(lambda: self.util.open_toolbox(2, False))
        self.action_yuyinhecheng.triggered.connect(lambda: self.util.open_toolbox(3, False))
        self.action_yinshipinfenli.triggered.connect(lambda: self.util.open_toolbox(0, False))
        self.action_yingyinhebing.triggered.connect(lambda: self.util.open_toolbox(1, False))
        self.action_geshi.triggered.connect(lambda: self.util.open_toolbox(4, False))
        self.action_hun.triggered.connect(lambda: self.util.open_toolbox(5, False))
        self.action_fanyi.triggered.connect(lambda: self.util.open_toolbox(6, False))
        self.rightbottom.clicked.connect(self.util.about)
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.startbtn.setText(config.transobj['installffmpeg'])
            self.startbtn.setDisabled(True)
            self.startbtn.setStyleSheet("""color:#ff0000""")
        #     日志
        from videotrans.task.check_update import CheckUpdateWorker
        from videotrans.task.logs_worker import LogsWorker
        update_role = GetRoleWorker(self)
        update_role.start()

        self.task_logs = LogsWorker(self)
        self.task_logs.post_logs.connect(self.util.update_data)
        self.task_logs.start()
        self.check_update = CheckUpdateWorker(self)
        self.check_update.start()

    def closeEvent(self, event):
        # 在关闭窗口前执行的操作
        if configure.TOOLBOX is not None:
            configure.TOOLBOX.close()
        if config.current_status == 'ing':
            config.current_status = 'end'
            msg = QMessageBox()
            msg.setWindowTitle(config.transobj['exit'])
            msg.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
            msg.setText(config.transobj['waitclear'])
            msg.addButton(config.transobj['queding'], QMessageBox.AcceptRole)
            msg.setIcon(QMessageBox.Information)
            msg.exec_()  # 显示消息框
            event.accept()
        else:
            event.accept()

    def get_setting(self):
        # 从缓存获取默认配置
        config.params["baidu_appid"] = self.settings.value("baidu_appid", "")
        config.params["baidu_miyue"] = self.settings.value("baidu_miyue", "")
        config.params["deepl_authkey"] = self.settings.value("deepl_authkey", "")
        config.params["deeplx_address"] = self.settings.value("deeplx_address", "")
        config.params["tencent_SecretId"] = self.settings.value("tencent_SecretId", "")
        config.params["tencent_SecretKey"] = self.settings.value("tencent_SecretKey", "")

        config.params["chatgpt_api"] = self.settings.value("chatgpt_api", "")
        config.params["chatgpt_key"] = self.settings.value("chatgpt_key", "")

        if self.settings.value("chatgpt_template", ""):
            config.params["chatgpt_template"] = self.settings.value("chatgpt_template", "")
        if self.settings.value("azure_template", ""):
            config.params["azure_template"] = self.settings.value("azure_template", "")
        if self.settings.value("gemini_template", ""):
            config.params["gemini_template"] = self.settings.value("gemini_template", "")

        config.params["chatgpt_model"] = self.settings.value("chatgpt_model", config.params['chatgpt_model'])
        if config.params["chatgpt_model"] == 'large':
            config.params["chatgpt_model"] = 'large-v3'
        os.environ['OPENAI_API_KEY'] = config.params["chatgpt_key"]

        config.params["gemini_key"] = self.settings.value("gemini_key", "")

        config.params["azure_api"] = self.settings.value("azure_api", "")
        config.params["azure_key"] = self.settings.value("azure_key", "")
        config.params["azure_model"] = self.settings.value("azure_model", config.params['azure_model'])

        config.params["elevenlabstts_key"] = self.settings.value("elevenlabstts_key", "")

        config.params['translate_type'] = self.settings.value("translate_type", config.params['translate_type'])
        config.params['subtitle_type'] = self.settings.value("subtitle_type", config.params['subtitle_type'], int)
        config.proxy = self.settings.value("proxy", "", str)
        config.params['voice_rate'] = self.settings.value("voice_rate", config.params['voice_rate'], str)
        config.params['voice_silence'] = self.settings.value("voice_silence", config.params['voice_silence'], str)
        config.params['cuda'] = self.settings.value("cuda", False, bool)
        config.params['whisper_model'] = self.settings.value("whisper_model", config.params['whisper_model'], str)
        config.params['whisper_type'] = self.settings.value("whisper_type", config.params['whisper_type'], str)
        config.params['tts_type'] = self.settings.value("tts_type", config.params['tts_type'], str)
        if not config.params['tts_type']:
            config.params['tts_type'] = 'edgeTTS'

    # 存储本地数据
    def save_setting(self):
        self.settings.setValue("target_dir", config.params['target_dir'])
        self.settings.setValue("proxy", config.proxy)
        self.settings.setValue("whisper_model", config.params['whisper_model'])
        self.settings.setValue("whisper_type", config.params['whisper_type'])
        self.settings.setValue("voice_rate", config.params['voice_rate'])
        self.settings.setValue("voice_silence", config.params['voice_silence'])
        self.settings.setValue("voice_autorate", config.params['voice_autorate'])
        self.settings.setValue("video_autorate", config.params['video_autorate'])
        self.settings.setValue("subtitle_type", config.params['subtitle_type'])
        self.settings.setValue("translate_type", config.params['translate_type'])
        self.settings.setValue("enable_cuda", config.params['cuda'])
        self.settings.setValue("tts_type", config.params['tts_type'])
        self.settings.setValue("tencent_SecretKey", config.params['tencent_SecretKey'])
        self.settings.setValue("tencent_SecretId", config.params['tencent_SecretId'])
        self.settings.setValue("elevenlabstts_key", config.params["elevenlabstts_key"])
