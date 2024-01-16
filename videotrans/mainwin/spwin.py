import os
import shutil
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import  QIcon
from PyQt5.QtCore import QSettings,  Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QMessageBox,  QLabel, QPushButton, QToolBar,  QWidget, QVBoxLayout,   QApplication
import warnings
warnings.filterwarnings('ignore')

from videotrans.configure.config import langlist, transobj
from videotrans import VERSION
from videotrans.configure import config
from videotrans.component.controlobj import TextGetdir

from videotrans.util.tools import show_popup
from videotrans.mainwin.secwin import SecWindow
from videotrans.task.check_update import CheckUpdateWorker
from videotrans.task.logs_worker import LogsWorker
if config.defaulelang == "zh":
    from videotrans.ui.cn import Ui_MainWindow
else:
    from videotrans.ui.en import Ui_MainWindow

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.task = None
        self.toolboxobj = None
        self.shitingobj = None
        self.youw = None
        self.processbtns = {}

        screen_resolution = QApplication.desktop().screenGeometry()
        width, height = screen_resolution.width(), screen_resolution.height()
        self.width=int(width*0.8)
        if self.width<1400:
            self.width=1400
        elif self.width>1900:
            self.width=1800
        self.resize(self.width, height-220)


        # 当前所有可用角色列表
        self.current_rolelist = []
        config.params['line_roles'] = {}
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
        self.rawtitle = f"{'视频翻译配音' if config.defaulelang != 'en' else ' Video Translate & Dubbing'} {VERSION}"
        self.setWindowTitle(self.rawtitle)

        # 检查窗口是否打开
        # if self.isVisible():
        self.initUI()
        self.show()


    def initUI(self):

        self.util=SecWindow(self)
        self.settings = QSettings("Jameson", "VideoTranslate")
        # 获取最后一次选择的目录
        self.last_dir = self.settings.value("last_dir", ".", str)
        # language code
        self.languagename = list(langlist.keys())
        self.app_mode = 'biaozhun'
        self.splitter.setSizes([self.width-400, 400])
        # start
        self.get_setting()
        self.startbtn.clicked.connect(self.util.check_start)
        try:
            if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
                self.startbtn.setText(transobj['installffmpeg'])
                self.startbtn.setDisabled(True)
                self.startbtn.setStyleSheet("""color:#ff0000""")
        except:
            pass

        # 隐藏倒计时
        self.stop_djs.clicked.connect(self.util.reset_timeid)
        self.stop_djs.hide()
        # subtitle btn
        self.continue_compos.hide()
        self.continue_compos.clicked.connect(self.util.set_djs_timeout)

        # select and save
        self.btn_get_video.clicked.connect(self.util.get_mp4)
        self.source_mp4.setAcceptDrops(True)
        self.btn_save_dir.clicked.connect(self.util.get_save_dir)
        self.target_dir.setAcceptDrops(True)
        self.proxy.setText(config.proxy)
        self.open_targetdir.clicked.connect(lambda: self.util.open_dir(self.target_dir.text()))

        # language
        self.source_language.addItems(self.languagename)
        self.source_language.setCurrentIndex(2)

        # 目标语言改变时，如果当前tts是 edgeTTS，则根据目标语言去修改显示的角色
        self.target_language.addItems(["-"] + self.languagename)
        # 目标语言改变
        self.target_language.currentTextChanged.connect(self.util.set_voice_role)
        self.voice_role.currentTextChanged.connect(self.util.show_listen_btn)

        self.listen_btn.hide()
        self.listen_btn.clicked.connect(self.util.listen_voice_fun)

        #  translation type
        self.translate_type.addItems(
            ["google", "baidu", "chatGPT", "Azure", 'Gemini', "tencent", "DeepL", "DeepLX"])
        self.translate_type.setCurrentText(config.params['translate_type'])
        self.translate_type.currentTextChanged.connect(self.util.set_translate_type)

        #         model
        self.whisper_type.addItems([transobj['whisper_type_all'], transobj['whisper_type_split']])
        self.whisper_type.currentIndexChanged.connect(self.util.check_whisper_type)
        if config.params['whisper_type']:
            self.whisper_type.setCurrentIndex(0 if config.params['whisper_type'] == 'all' else 1)
        self.whisper_model.addItems(['base', 'small', 'medium', 'large-v3'])
        self.whisper_model.setCurrentText(config.params['whisper_model'])
        self.whisper_model.currentTextChanged.connect(self.util.check_whisper_model)

        #
        self.voice_rate.setText(config.params['voice_rate'])
        self.voice_rate.textChanged.connect(self.util.voice_rate_changed)
        self.voice_silence.setText(config.params['voice_silence'])

        self.voice_autorate.stateChanged.connect(
            lambda: self.util.autorate_changed(self.voice_autorate.isChecked(), "voice"))
        self.video_autorate.stateChanged.connect(
            lambda: self.util.autorate_changed(self.video_autorate.isChecked(), "video"))

        # 设置角色类型，如果当前是OPENTTS或 coquiTTS则设置，如果是edgeTTS，则为No
        if config.params['tts_type'] == 'edgeTTS':
            self.voice_role.addItems(['No'])
        elif config.params['tts_type'] == 'openaiTTS':
            self.voice_role.addItems(['No'] + config.params['openaitts_role'].split(','))
        elif config.params['tts_type'] == 'coquiTTS':
            self.voice_role.addItems(['No'] + config.params['coquitts_role'].split(','))
        elif config.params['tts_type'] == 'elevenlabsTTS':
            self.voice_role.addItems(['No'] + config.params['elevenlabstts_role'])
        # 设置 tts_type
        self.tts_type.addItems(config.params['tts_type_list'])
        self.tts_type.setCurrentText(config.params['tts_type'])
        self.util.tts_type_change(config.params['tts_type'])
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.util.tts_type_change)

        self.enable_cuda.stateChanged.connect(self.util.check_cuda)
        self.enable_cuda.setChecked(config.params['cuda'])

        # subtitle 0 no 1=embed subtitle 2=softsubtitle
        self.subtitle_type.addItems([transobj['nosubtitle'], transobj['embedsubtitle'], transobj['softsubtitle']])
        self.subtitle_type.setCurrentIndex(config.params['subtitle_type'])

        # 字幕编辑
        self.subtitle_area = TextGetdir(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.subtitle_area.setSizePolicy(sizePolicy)
        self.subtitle_area.setMinimumSize(300, 0)
        self.subtitle_area.setPlaceholderText(transobj['subtitle_tips'])

        self.subtitle_layout.insertWidget(0, self.subtitle_area)

        self.import_sub.clicked.connect(self.util.import_sub_fun)

        self.listen_peiyin.setDisabled(True)
        self.listen_peiyin.clicked.connect(self.util.shiting_peiyin)
        self.set_line_role.clicked.connect(self.util.set_line_role_fun)

        # 创建 Scroll Area
        self.scroll_area.setWidgetResizable(True)

        # 创建一个 QWidget 作为 Scroll Area 的 viewport
        viewport = QWidget(self.scroll_area)
        self.scroll_area.setWidget(viewport)

        # 创建一个垂直布局管理器，用于在 viewport 中放置按钮
        self.processlayout = QVBoxLayout(viewport)
        # 设置布局管理器的对齐方式为顶部对齐
        self.processlayout.setAlignment(Qt.AlignTop)

        # menubar
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
        self.action_tool.triggered.connect(self.util.open_toolbox)
        self.actionyoutube.triggered.connect(self.util.open_youtube)
        self.action_about.triggered.connect(self.util.about)
        self.action_clone.triggered.connect(lambda: show_popup(transobj['yinsekaifazhong'], transobj['yinsekelong']))

        # 设置QAction的大小
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # 设置QToolBar的大小，影响其中的QAction的大小
        self.toolBar.setIconSize(QSize(100, 45))  # 设置图标大小
        self.action_biaozhun.triggered.connect(self.util.set_biaozhun)
        self.action_tiquzimu.triggered.connect(self.util.set_tiquzimu)
        self.action_tiquzimu_no.triggered.connect(self.util.set_tiquzimu_no)
        self.action_zimu_video.triggered.connect(self.util.set_zimu_video)
        self.action_zimu_peiyin.triggered.connect(self.util.set_zimu_peiyin)
        self.action_yuyinshibie.triggered.connect(lambda: self.util.open_toolbox(2))
        self.action_yuyinhecheng.triggered.connect(lambda: self.util.open_toolbox(3))
        self.action_yinshipinfenli.triggered.connect(lambda: self.util.open_toolbox(0))
        self.action_yingyinhebing.triggered.connect(lambda: self.util.open_toolbox(1))
        self.action_geshi.triggered.connect(lambda: self.util.open_toolbox(4))
        self.action_hun.triggered.connect(lambda: self.util.open_toolbox(5))
        self.action_fanyi.triggered.connect(lambda: self.util.open_toolbox(6))

        # 底部状态栏
        self.statusLabel = QLabel(transobj['modelpathis'] + " /models")
        self.statusLabel.setStyleSheet("color:#00a67d")
        self.statusBar.addWidget(self.statusLabel)

        rightbottom = QPushButton(transobj['juanzhu'])
        rightbottom.clicked.connect(self.util.about)
        rightbottom.setStyleSheet("background-color:#32414B;color:#ffffff")
        rightbottom.setCursor(QtCore.Qt.PointingHandCursor)

        self.container = QToolBar()
        self.container.addWidget(rightbottom)
        self.statusBar.addPermanentWidget(self.container)



        #     日志
        self.task_logs = LogsWorker(self)
        self.task_logs.post_logs.connect(self.util.update_data)
        self.task_logs.start()

        self.check_update = CheckUpdateWorker(self)
        self.check_update.start()


    def closeEvent(self, event):
        # 在关闭窗口前执行的操作
        if self.toolboxobj is not None:
            self.toolboxobj.close()
        if config.current_status == 'ing':
            config.current_status = 'end'
            msg = QMessageBox()
            msg.setWindowTitle(transobj['exit'])
            msg.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
            msg.setText(transobj['waitclear'])
            msg.addButton(transobj['queding'], QMessageBox.AcceptRole)
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
        config.params["chatgpt_model"] = self.settings.value("chatgpt_model", config.params['chatgpt_model'])
        if config.params["chatgpt_model"] == 'large':
            config.params["chatgpt_model"]='large-v3' 
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
