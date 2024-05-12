import os
import shutil
import threading
import time

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSettings, Qt, QSize, QTimer, QPoint
from PySide6.QtWidgets import QMainWindow, QMessageBox, QLabel, QPushButton, QToolBar, QWidget, QVBoxLayout
import warnings

warnings.filterwarnings('ignore')

from videotrans.task.get_role_list import GetRoleWorker
from videotrans.util import tools

from videotrans.translator import TRANSNAMES
from videotrans.configure import config
from videotrans import VERSION
from videotrans.component.controlobj import TextGetdir
from videotrans.ui.en import Ui_MainWindow
from videotrans.box import win

from videotrans import configure
from pathlib import Path


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None,width=1200,height=700):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.width = int(width * 0.8)
        self.height = int(height * 0.8)
        self.bwidth=int(width*0.7)
        self.bheight=int(height*0.7)
        self.lefttopx=int(width*0.15)
        self.lefttopy=int(height*0.15)
        self.resize(self.width, self.height)
        self.show()
        self.task = None
        self.shitingobj = None
        self.youw = None
        self.sepw = None
        self.util = None
        self.moshis=None
        self.app_mode = "biaozhun_jd"
        self.processbtns = {}

        # 当前所有可用角色列表
        self.current_rolelist = []
        config.params['line_roles'] = {}
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
        self.rawtitle = f"{config.transobj['softname']}{VERSION} pyvideotrans.com {' Q群 933714380 ' if config.defaulelang == 'zh' else ''}"
        self.setWindowTitle(self.rawtitle)
        # 检查窗口是否打开
        self.initUI()
        # 渲染后再执行绑定
        # QTimer.singleShot(200, self.bind_action)
        self.bind_action()
        QTimer.singleShot(500, self.start_box)


    def start_box(self):
        # 打开工具箱
        configure.TOOLBOX = win.MainWindow(self)
        configure.TOOLBOX.resize(self.bwidth, self.bheight)
        configure.TOOLBOX.move(QPoint(self.lefttopx,self.lefttopy))

    def initUI(self):

        self.settings = QSettings("Jameson", "VideoTranslate")
        # 获取最后一次选择的目录
        config.last_opendir = self.settings.value("last_dir", config.last_opendir, str)
        # language code
        self.languagename = config.langnamelist
        self.get_setting()

        self.splitter.setSizes([self.width - 400, 400])
        # start

        # 隐藏倒计时
        self.stop_djs.hide()
        self.stop_djs.setStyleSheet("""background-color:#148CD2;color:#ffffff""")
        self.stop_djs.setToolTip(config.transobj['Click to pause and modify subtitles for more accurate processing'])
        # subtitle btn
        self.continue_compos.hide()
        self.continue_compos.setToolTip(config.transobj['Click to start the next step immediately'])
        self.stop_djs.setCursor(Qt.PointingHandCursor)
        self.continue_compos.setCursor(Qt.PointingHandCursor)
        self.startbtn.setCursor(Qt.PointingHandCursor)
        self.btn_get_video.setCursor(Qt.PointingHandCursor)
        self.btn_save_dir.setCursor(Qt.PointingHandCursor)

        self.source_mp4.setAcceptDrops(True)
        self.target_dir.setAcceptDrops(True)
        self.proxy.setText(config.proxy)

        # language
        self.source_language.addItems(self.languagename)
        if config.params['source_language'] and config.params['source_language'] in self.languagename:
            self.source_language.setCurrentText(config.params['source_language'])
        else:
            self.source_language.setCurrentIndex(2)

        # 目标语言改变时，如果当前tts是 edgeTTS，则根据目标语言去修改显示的角色
        self.target_language.addItems(["-"] + self.languagename)

        # 目标语言改变
        self.listen_btn.setCursor(Qt.PointingHandCursor)

        #  translation type
        self.translate_type.addItems(TRANSNAMES)
        translate_name = config.params['translate_type'] if config.params['translate_type'] in TRANSNAMES else TRANSNAMES[0]

        self.translate_type.setCurrentText(translate_name)

        #         model
        self.whisper_type.addItems([config.transobj['whisper_type_all'], config.transobj['whisper_type_split'],
                                    config.transobj['whisper_type_avg']])
        self.whisper_type.setToolTip(config.transobj['fenge_tips'])
        if config.params['whisper_type']:
            d = {"all": 0, 'split': 1, "avg": 2, "": 0}
            self.whisper_type.setCurrentIndex(d[config.params['whisper_type']])
        self.whisper_model.addItems(config.model_list)
        if config.params['whisper_model'] in config.model_list:
            self.whisper_model.setCurrentText(config.params['whisper_model'])
        if config.params['model_type'] == 'openai':
            self.model_type.setCurrentIndex(1)
        elif config.params['model_type'] == 'GoogleSpeech':
            self.model_type.setCurrentIndex(2)
        elif config.params['model_type'] == 'zh_recogn':
            self.model_type.setCurrentIndex(3)
            self.whisper_model.setDisabled(True)
            self.whisper_type.setDisabled(True)
        if config.params['only_video']:
            self.only_video.setChecked(True)
        try:
            self.voice_rate.setValue(int(config.params['voice_rate'].replace('%','')))
        except Exception:
            self.voice_rate.setValue(0)


        self.voice_autorate.setChecked(config.params['voice_autorate'])
        self.video_autorate.setChecked(config.params['video_autorate'])
        self.append_video.setChecked(config.params['append_video'])
        self.auto_ajust.setChecked(config.params['auto_ajust'])

        if config.params['cuda']:
            self.enable_cuda.setChecked(True)

        self.subtitle_type.addItems(
            [
                config.transobj['nosubtitle'],
                config.transobj['embedsubtitle'],
                config.transobj['softsubtitle'],
                config.transobj['embedsubtitle2'],
                config.transobj['softsubtitle2']
            ])
        self.subtitle_type.setCurrentIndex(config.params['subtitle_type'])

        # 字幕编辑
        self.subtitle_area = TextGetdir(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.subtitle_area.setSizePolicy(sizePolicy)
        self.subtitle_area.setMinimumSize(300, 0)
        self.subtitle_area.setPlaceholderText(
            f"{config.transobj['subtitle_tips']}\n\n{config.transobj['meitiaozimugeshi']}")

        self.subtitle_tips = QLabel(config.transobj['zimubianjitishi'])
        self.subtitle_tips.setFixedHeight(30)
        self.subtitle_tips.setToolTip(config.transobj['meitiaozimugeshi'])

        self.subtitle_layout.insertWidget(0, self.subtitle_tips)
        self.subtitle_layout.insertWidget(1, self.subtitle_area)

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
        self.statusLabel = QPushButton(config.transobj["Open Documents"])
        self.statusLabel.setCursor(QtCore.Qt.PointingHandCursor)
        self.statusBar.addWidget(self.statusLabel)

        self.rightbottom = QPushButton(config.transobj['juanzhu'])
        self.rightbottom.setCursor(QtCore.Qt.PointingHandCursor)

        self.container = QToolBar()
        self.container.addWidget(self.rightbottom)
        self.statusBar.addPermanentWidget(self.container)



    def bind_action(self):
        # 设置角色类型，如果当前是OPENTTS或 coquiTTS则设置，如果是edgeTTS，则为No
        from videotrans.mainwin.secwin import SecWindow
        from videotrans.mainwin.subform import Subform
        self.util = SecWindow(self)
        self.subform = Subform(self)
        if config.params['tts_type'] == 'clone-voice':
            self.voice_role.addItems(config.clone_voicelist)
            threading.Thread(target=tools.get_clone_role).start()
        elif config.params['tts_type'] == 'TTS-API':
            self.voice_role.addItems(config.params['ttsapi_voice_role'].strip().split(','))
        elif config.params['tts_type'] == 'GPT-SoVITS':
            rolelist = tools.get_gptsovits_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])

        if config.params['tts_type']:
            if config.params['tts_type'] not in ['edgeTTS','AzureTTS']:
                self.voice_role.addItems(['No'])
            self.util.tts_type_change(config.params['tts_type'])

        # 设置 tts_type
        self.tts_type.addItems(config.params['tts_type_list'])
        self.tts_type.setCurrentText(config.params['tts_type'])

        if config.params['target_language'] and config.params['target_language'] in self.languagename:
            self.target_language.setCurrentText(config.params['target_language'])
            # 根据目标语言更新角色列表
            self.util.set_voice_role(config.params['target_language'])
            # 设置默认角色列表
            if config.params['voice_role'] and config.params['voice_role'] != 'No' and self.current_rolelist and \
                    config.params['voice_role'] in self.current_rolelist:
                self.voice_role.setCurrentText(config.params['voice_role'])
                self.util.show_listen_btn(config.params['voice_role'])

        self.proxy.textChanged.connect(self.util.change_proxy)

        # menubar
        self.import_sub.clicked.connect(self.util.import_sub_fun)
        self.import_sub.setCursor(Qt.PointingHandCursor)
        self.import_sub.setToolTip(config.transobj['daoruzimutips'])

        self.export_sub.setText(config.transobj['Export srt'])
        self.export_sub.clicked.connect(self.util.export_sub_fun)
        self.export_sub.setCursor(Qt.PointingHandCursor)
        self.export_sub.setToolTip(
            config.transobj['When subtitles exist, the subtitle content can be saved to a local SRT file'])


        self.set_line_role.clicked.connect(self.subform.set_line_role_fun)
        self.set_line_role.setCursor(Qt.PointingHandCursor)
        self.set_line_role.setToolTip(config.transobj['Set up separate dubbing roles for each subtitle to be used'])
        self.startbtn.clicked.connect(self.util.check_start)
        self.stop_djs.clicked.connect(self.util.reset_timeid)
        self.continue_compos.clicked.connect(self.util.set_djs_timeout)
        self.btn_get_video.clicked.connect(self.util.get_mp4)
        self.btn_save_dir.clicked.connect(self.util.get_save_dir)

        self.target_language.currentTextChanged.connect(self.util.set_voice_role)
        self.voice_role.currentTextChanged.connect(self.util.show_listen_btn)
        self.listen_btn.clicked.connect(self.util.listen_voice_fun)
        self.translate_type.currentTextChanged.connect(self.util.set_translate_type)
        self.whisper_type.currentIndexChanged.connect(self.util.check_whisper_type)

        self.whisper_model.currentTextChanged.connect(self.util.check_whisper_model)
        self.model_type.currentTextChanged.connect(self.util.model_type_change)
        self.voice_rate.valueChanged.connect(self.util.voice_rate_changed)
        self.voice_autorate.stateChanged.connect(
            lambda: self.util.autorate_changed(self.voice_autorate.isChecked(), "voice"))
        self.video_autorate.stateChanged.connect(lambda: self.util.autorate_changed(self.video_autorate.isChecked(), "video"))
        self.append_video.stateChanged.connect(lambda: self.util.autorate_changed(self.video_autorate.isChecked(), "append_video"))
        self.auto_ajust.stateChanged.connect(
            lambda: self.util.autorate_changed(self.auto_ajust.isChecked(), "auto_ajust"))
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.util.tts_type_change)
        self.addbackbtn.clicked.connect(self.util.get_background)

        self.is_separate.toggled.connect(self.util.is_separate_fun)
        self.enable_cuda.toggled.connect(self.util.check_cuda)


        # 设置QAction的大小
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # 设置QToolBar的大小，影响其中的QAction的大小
        self.toolBar.setIconSize(QSize(100, 45))  # 设置图标大小


        self.actionbaidu_key.triggered.connect(self.subform.set_baidu_key)
        self.actionazure_key.triggered.connect(self.subform.set_azure_key)
        self.actionazure_tts.triggered.connect(self.subform.set_auzuretts_key)
        self.actiongemini_key.triggered.connect(self.subform.set_gemini_key)
        self.actiontencent_key.triggered.connect(self.subform.set_tencent_key)
        self.actionchatgpt_key.triggered.connect(self.subform.set_chatgpt_key)
        self.actiondeepL_key.triggered.connect(self.subform.set_deepL_key)
        self.actionElevenlabs_key.triggered.connect(self.subform.set_elevenlabs_key)
        self.actiondeepLX_address.triggered.connect(self.subform.set_deepLX_address)
        self.actionott_address.triggered.connect(self.subform.set_ott_address)
        self.actionclone_address.triggered.connect(self.subform.set_clone_address)
        self.actiontts_api.triggered.connect(self.subform.set_ttsapi)
        self.actionzhrecogn_api.triggered.connect(self.subform.set_zh_recogn)
        self.actiontrans_api.triggered.connect(self.subform.set_transapi)
        self.actiontts_gptsovits.triggered.connect(self.subform.set_gptsovits)
        self.action_ffmpeg.triggered.connect(lambda: self.util.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.util.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.util.open_url('discord'))
        self.action_models.triggered.connect(lambda: self.util.open_url('models'))
        self.action_dll.triggered.connect(lambda: self.util.open_url('dll'))
        self.action_gtrans.triggered.connect(lambda: self.util.open_url('gtrans'))
        self.action_cuda.triggered.connect(lambda: self.util.open_url('cuda'))
        self.action_online.triggered.connect(lambda: self.util.open_url('online'))
        self.action_website.triggered.connect(lambda: self.util.open_url('website'))
        self.action_aihelp.triggered.connect(lambda: self.util.open_url('aihelp'))
        self.action_blog.triggered.connect(lambda: self.util.open_url('blog'))
        self.statusLabel.clicked.connect(lambda: self.util.open_url('help'))
        self.action_issue.triggered.connect(lambda: self.util.open_url('issue'))
        self.action_tool.triggered.connect(lambda: self.util.open_toolbox(0, False))
        self.actionyoutube.triggered.connect(self.subform.open_youtube)
        self.actionsepar.triggered.connect(self.subform.open_separate)
        self.action_about.triggered.connect(self.util.about)

        self.action_xinshoujandan.triggered.connect(self.util.set_xinshoujandann)

        self.action_biaozhun.triggered.connect(self.util.set_biaozhun)


        self.action_tiquzimu.triggered.connect(self.util.set_tiquzimu)

        self.action_zimu_video.triggered.connect(self.util.set_zimu_video)

        self.action_zimu_peiyin.triggered.connect(self.util.set_zimu_peiyin)

        if self.app_mode == 'biaozhun_jd':
            self.util.set_xinshoujandann()
        elif self.app_mode == 'biaozhun':
            self.util.set_biaozhun()
        elif self.app_mode == 'tiqu':
            self.util.set_tiquzimu()
        elif self.app_mode == 'hebing':
            self.util.set_zimu_video()
        elif self.app_mode == 'peiyin':
            self.util.set_zimu_peiyin()
        self.moshis={
            "biaozhun_jd":self.action_xinshoujandan,
            "biaozhun":self.action_biaozhun,
            "tiqu":self.action_tiquzimu,
            "hebing":self.action_zimu_video,
            "peiyin":self.action_zimu_peiyin
        }
        self.action_yuyinshibie.triggered.connect(lambda: self.util.open_toolbox(0, False))

        self.action_yuyinhecheng.triggered.connect(lambda: self.util.open_toolbox(1, False))

        self.action_yinshipinfenli.triggered.connect(lambda: self.util.open_toolbox(3, False))

        self.action_yingyinhebing.triggered.connect(lambda: self.util.open_toolbox(4, False))


        self.action_hun.triggered.connect(lambda: self.util.open_toolbox(5, False))

        self.action_fanyi.triggered.connect(lambda: self.util.open_toolbox(2, False))

        self.action_clearcache.triggered.connect(self.util.clearcache)
        # 禁止随意移动sp.exe
        if not Path(config.rootdir+'/videotrans').exists() or not Path(config.rootdir+ '/models').exists():
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['sp.exeerror'])
            return False
        import platform

        if platform.system().lower() == 'windows' and (
                platform.release().lower() == 'xp' or int(platform.release()) < 10):
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['only10'])
            return False
        self.rightbottom.clicked.connect(self.util.about)
        #     日志
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['installffmpeg'])
            self.startbtn.setText(config.transobj['installffmpeg'])
            self.startbtn.setDisabled(True)
            self.startbtn.setStyleSheet("""color:#ff0000""")
        from videotrans.task.check_update import CheckUpdateWorker
        from videotrans.task.logs_worker import LogsWorker
        try:
            update_role = GetRoleWorker(parent=self)
            update_role.start()
            self.task_logs = LogsWorker(parent=self)
            self.task_logs.post_logs.connect(self.util.update_data)
            self.task_logs.start()
            self.check_update = CheckUpdateWorker(parent=self)
            self.check_update.start()
        except Exception as e:
            print('threaqd-----' + str(e))

    def closeEvent(self, event):
        # 在关闭窗口前执行的操作
        config.exit_soft = True
        config.current_status = 'end'
        self.hide()

        if configure.TOOLBOX is not None:
            configure.TOOLBOX.close()
        try:
            shutil.rmtree(config.rootdir + "/tmp", ignore_errors=True)
            shutil.rmtree(config.homedir + "/tmp", ignore_errors=True)
        except Exception:
            pass
        try:
            tools.kill_ffmpeg_processes()
        except Exception:
            pass
        time.sleep(1)
        event.accept()

    def get_setting(self):
        self.app_mode = self.settings.value("init_model_functional", "biaozhun_jd")
        # 从缓存获取默认配置
        config.params["baidu_appid"] = self.settings.value("baidu_appid", "")
        config.params["source_language"] = self.settings.value("source_language", "")
        config.params["target_language"] = self.settings.value("target_language", "")
        config.params["voice_role"] = self.settings.value("voice_role", "")
        config.params["voice_autorate"] = self.settings.value("voice_autorate", False, bool)
        config.params["video_autorate"] = self.settings.value("video_autorate", False, bool)
        config.params["append_video"] = self.settings.value("append_video", False, bool)
        config.params["auto_ajust"] = self.settings.value("auto_ajust", True, bool)

        config.params["baidu_miyue"] = self.settings.value("baidu_miyue", "")
        config.params["deepl_authkey"] = self.settings.value("deepl_authkey", "")
        config.params["deepl_api"] = self.settings.value("deepl_api", "")
        config.params["deeplx_address"] = self.settings.value("deeplx_address", "")
        config.params["ott_address"] = self.settings.value("ott_address", "")
        config.params["clone_api"] = self.settings.value("clone_api", "")
        config.params["tencent_SecretId"] = self.settings.value("tencent_SecretId", "")
        config.params["tencent_SecretKey"] = self.settings.value("tencent_SecretKey", "")

        config.params["chatgpt_api"] = self.settings.value("chatgpt_api", "")
        config.params["chatgpt_key"] = self.settings.value("chatgpt_key", "")
        config.params["azure_speech_key"] = self.settings.value("azure_speech_key", "")
        config.params["azure_speech_region"] = self.settings.value("azure_speech_region", "")

        if self.settings.value("clone_voicelist", ""):
            config.clone_voicelist = self.settings.value("clone_voicelist", "").split(',')

        config.params["chatgpt_model"] = self.settings.value("chatgpt_model", config.params['chatgpt_model'])
        os.environ['OPENAI_API_KEY'] = config.params["chatgpt_key"]

        config.params["ttsapi_url"] = self.settings.value("ttsapi_url", "")
        config.params["ttsapi_extra"] = self.settings.value("ttsapi_extra", "pyvideotrans")
        config.params["ttsapi_voice_role"] = self.settings.value("ttsapi_voice_role", "")

        config.params["trans_api_url"] = self.settings.value("trans_api_url", "")
        config.params["trans_secret"] = self.settings.value("trans_secret", "")

        config.params["gptsovits_url"] = self.settings.value("gptsovits_url", "")
        config.params["gptsovits_extra"] = self.settings.value("gptsovits_extra", "pyvideotrans")
        config.params["gptsovits_role"] = self.settings.value("gptsovits_role", "")

        config.params["gemini_key"] = self.settings.value("gemini_key", "")
        config.params["zh_recogn_api"] = self.settings.value("zh_recogn_api", "")

        config.params["azure_api"] = self.settings.value("azure_api", "")
        config.params["azure_key"] = self.settings.value("azure_key", "")
        config.params["azure_model"] = self.settings.value("azure_model", config.params['azure_model'])

        config.params["elevenlabstts_key"] = self.settings.value("elevenlabstts_key", "")

        config.params['translate_type'] = self.settings.value("translate_type", config.params['translate_type'])
        if config.params['translate_type']=='FreeChatGPT':
            config.params['translate_type']='FreeGoogle'
        config.params['subtitle_type'] = self.settings.value("subtitle_type", config.params['subtitle_type'], int)
        config.proxy = self.settings.value("proxy", "", str)
        config.params['voice_rate'] = self.settings.value("voice_rate", config.params['voice_rate'].replace('%','').replace('+',''), str)
        config.params['cuda'] = self.settings.value("cuda", False, bool)
        config.params['only_video'] = self.settings.value("only_video", False, bool)
        config.params['whisper_model'] = self.settings.value("whisper_model", config.params['whisper_model'], str)
        config.params['whisper_type'] = self.settings.value("whisper_type", config.params['whisper_type'], str)
        config.params['model_type'] = self.settings.value("model_type", config.params['model_type'], str)
        config.params['tts_type'] = self.settings.value("tts_type", config.params['tts_type'], str)
        if not config.params['tts_type']:
            config.params['tts_type'] = 'edgeTTS'

    # 存储本地数据
    def save_setting(self):
        self.settings.setValue("init_model_functional", self.app_mode)
        self.settings.setValue("target_dir", config.params['target_dir'])
        self.settings.setValue("source_language", config.params['source_language'])
        self.settings.setValue("target_language", config.params['target_language'])
        self.settings.setValue("proxy", config.proxy)
        self.settings.setValue("whisper_model", config.params['whisper_model'])
        self.settings.setValue("whisper_type", config.params['whisper_type'])
        self.settings.setValue("model_type", config.params['model_type'])
        self.settings.setValue("voice_rate", config.params['voice_rate'].replace('%','').replace('+',''))
        self.settings.setValue("voice_role", config.params['voice_role'])
        self.settings.setValue("zh_recogn_api", config.params['zh_recogn_api'])

        self.settings.setValue("voice_autorate", config.params['voice_autorate'])
        self.settings.setValue("auto_ajust", config.params['auto_ajust'])
        self.settings.setValue("subtitle_type", config.params['subtitle_type'])
        self.settings.setValue("translate_type", config.params['translate_type'])
        self.settings.setValue("cuda", config.params['cuda'])
        self.settings.setValue("only_video", config.params['only_video'])
        self.settings.setValue("tts_type", config.params['tts_type'])
        self.settings.setValue("clone_api", config.params['clone_api'])
        self.settings.setValue("video_autorate", config.params['video_autorate'])
        self.settings.setValue("append_video", config.params['append_video'])
        self.settings.setValue("clone_voicelist", ','.join(config.clone_voicelist))
