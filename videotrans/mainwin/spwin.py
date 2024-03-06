import os
import shutil
import threading

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QIcon, QGuiApplication
from PySide6.QtCore import QSettings, Qt, QSize
from PySide6.QtWidgets import QMainWindow, QMessageBox, QLabel, QPushButton, QToolBar, QWidget, QVBoxLayout
import warnings

from videotrans.task.get_role_list import GetRoleWorker
from videotrans.util import tools

warnings.filterwarnings('ignore')

from videotrans.translator import TRANSNAMES
from videotrans.configure import config
from videotrans import VERSION
from videotrans.component.controlobj import TextGetdir
from videotrans.ui.en import Ui_MainWindow

from videotrans.box import win
from videotrans import configure
            


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.task = None
        self.shitingobj = None
        self.youw = None
        self.sepw=None
        self.processbtns = {}
        screen=QGuiApplication.primaryScreen()
        screen_resolution = screen.geometry()
        width, height = screen_resolution.width(), screen_resolution.height()
        self.width = int(width * 0.8)
        self.height=int(height*0.8)        
        self.resize(self.width, self.height)
        # 当前所有可用角色列表
        self.current_rolelist = []
        config.params['line_roles'] = {}
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
        self.rawtitle = f"{config.transobj['softname']}{VERSION}   {' Q群 905581228 / 微信公众号 pyvideotrans' if config.defaulelang=='zh' else ''}"
        self.setWindowTitle(self.rawtitle)
        # 检查窗口是否打开
        self.initUI()
        # 打开工具箱
        configure.TOOLBOX = win.MainWindow()
        configure.TOOLBOX.resize(int(width*0.7), int(height*0.8))
        qtRect=configure.TOOLBOX.frameGeometry()
        qtRect.moveCenter(screen.availableGeometry().center())
        configure.TOOLBOX.move(qtRect.topLeft())

    def initUI(self):

        self.settings = QSettings("Jameson", "VideoTranslate")
        # 获取最后一次选择的目录
        config.last_opendir = self.settings.value("last_dir", config.last_opendir, str)
        # language code
        self.languagename = config.langnamelist
        self.app_mode = 'biaozhun'
        self.splitter.setSizes([self.width - 400, 400])
        # start
        self.get_setting()

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
        self.open_targetdir.setCursor(Qt.PointingHandCursor)

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
        self.translate_type.setCurrentText(
            config.params['translate_type'] if config.params['translate_type'] in TRANSNAMES else TRANSNAMES[0])

        #         model
        self.whisper_type.addItems([config.transobj['whisper_type_all'], config.transobj['whisper_type_split'],config.transobj['whisper_type_avg']])
        self.whisper_type.setToolTip(config.transobj['fenge_tips'])
        if config.params['whisper_type']:
            d={"all":0,'split':1,"avg":2,"":0}
            self.whisper_type.setCurrentIndex(d[config.params['whisper_type']])
        self.whisper_model.addItems(['base', 'small', 'medium','large-v2','large-v3'])
        self.whisper_model.setCurrentText(config.params['whisper_model'])
        if config.params['model_type']=='openai':
            self.model_type.setCurrentIndex(1)
        if config.params['only_video']:
            self.only_video.setChecked(True)


        #
        self.voice_rate.setText(config.params['voice_rate'])
        # self.voice_silence.setText(config.params['voice_silence'])

        self.voice_autorate.setChecked(config.params['voice_autorate'])
        self.video_autorate.setChecked(config.params['video_autorate'])



        if config.params['cuda']:
            self.enable_cuda.setChecked(True)

        # subtitle 0 no 1=embed subtitle 2=softsubtitle
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
        self.subtitle_area.setPlaceholderText(f"{config.transobj['subtitle_tips']}\n\n{config.transobj['meitiaozimugeshi']}")



        self.subtitle_tips=QLabel(config.transobj['zimubianjitishi'])
        self.subtitle_tips.setFixedHeight(30)
        self.subtitle_tips.setToolTip(config.transobj['meitiaozimugeshi'])

        self.subtitle_layout.insertWidget(0, self.subtitle_tips)
        self.subtitle_layout.insertWidget(1, self.subtitle_area)

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
        self.statusLabel = QPushButton(config.transobj["Open Documents"])
        self.statusLabel.setCursor(QtCore.Qt.PointingHandCursor)
        self.statusLabel.setStyleSheet("background-color:#455364;color:#ffffff")


        self.statusBar.addWidget(self.statusLabel)

        self.rightbottom = QPushButton(config.transobj['juanzhu'])
        self.rightbottom.setStyleSheet("background-color:#455364;color:#ffffff;border:0")
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
        # return
        # 设置角色类型，如果当前是OPENTTS或 coquiTTS则设置，如果是edgeTTS，则为No


        if config.params['tts_type'] == 'clone-voice':
            self.voice_role.addItems(config.clone_voicelist)
            threading.Thread(target=tools.get_clone_role).start()
            config.params['is_separate'] = True
            self.is_separate.setChecked(True)
        elif config.params['tts_type']=='TTS-API':
            self.voice_role.addItems(config.params['ttsapi_voice_role'].strip().split(','))
        elif config.params['tts_type']=='GPT-SoVITS':
            rolelist=tools.get_gptsovits_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'] )

        if config.params['tts_type']:
            self.util.tts_type_change(config.params['tts_type'])
            self.voice_role.addItems(['No'])

        # 设置 tts_type
        self.tts_type.addItems(config.params['tts_type_list'])
        self.tts_type.setCurrentText(config.params['tts_type'])

        if config.params['target_language'] and config.params['target_language'] in self.languagename:
            self.target_language.setCurrentText(config.params['target_language'])
            # 根据目标语言更新角色列表
            self.util.set_voice_role(config.params['target_language'])
            #设置默认角色列表
            if config.params['voice_role'] and config.params['voice_role']!='No' and self.current_rolelist and config.params['voice_role'] in self.current_rolelist:
                self.voice_role.setCurrentText(config.params['voice_role'])
                self.util.show_listen_btn(config.params['voice_role'])

        # menubar
        self.import_sub.clicked.connect(self.util.import_sub_fun)
        self.import_sub.setCursor(Qt.PointingHandCursor)
        self.import_sub.setToolTip(config.transobj['daoruzimutips'])

        self.export_sub.setText(config.transobj['Export srt'])
        self.export_sub.clicked.connect(self.util.export_sub_fun)
        self.export_sub.setCursor(Qt.PointingHandCursor)
        self.export_sub.setToolTip(config.transobj['When subtitles exist, the subtitle content can be saved to a local SRT file'])

        self.listen_peiyin.clicked.connect(self.util.shiting_peiyin)
        self.listen_peiyin.setCursor(Qt.PointingHandCursor)
        self.set_line_role.clicked.connect(self.util.set_line_role_fun)
        self.set_line_role.setCursor(Qt.PointingHandCursor)
        self.set_line_role.setToolTip(config.transobj['Set up separate dubbing roles for each subtitle to be used'])
        self.startbtn.clicked.connect(self.util.check_start)
        self.stop_djs.clicked.connect(self.util.reset_timeid)
        self.continue_compos.clicked.connect(self.util.set_djs_timeout)
        self.btn_get_video.clicked.connect(self.util.get_mp4)
        self.btn_save_dir.clicked.connect(self.util.get_save_dir)
        self.open_targetdir.clicked.connect(lambda: self.util.open_dir(self.target_dir.text()))
        self.show_tips.clicked.connect(lambda: self.util.open_dir(self.show_tips.text().split('#')[-1]))
        self.target_language.currentTextChanged.connect(self.util.set_voice_role)
        self.voice_role.currentTextChanged.connect(self.util.show_listen_btn)
        self.listen_btn.clicked.connect(self.util.listen_voice_fun)
        self.translate_type.currentTextChanged.connect(self.util.set_translate_type)
        self.whisper_type.currentIndexChanged.connect(self.util.check_whisper_type)

        self.whisper_model.currentTextChanged.connect(self.util.check_whisper_model)
        self.model_type.currentTextChanged.connect(self.util.model_type_change)
        self.voice_rate.textChanged.connect(self.util.voice_rate_changed)
        self.voice_autorate.stateChanged.connect(
            lambda: self.util.autorate_changed(self.voice_autorate.isChecked(), "voice"))
        self.video_autorate.stateChanged.connect(
            lambda: self.util.autorate_changed(self.video_autorate.isChecked(), "video"))
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.util.tts_type_change)
        self.addbackbtn.clicked.connect(self.util.get_background)


        self.is_separate.toggled.connect(self.util.is_separate_fun)
        self.enable_cuda.toggled.connect(self.util.check_cuda)
        self.actionbaidu_key.triggered.connect(self.util.set_baidu_key)
        self.actionazure_key.triggered.connect(self.util.set_azure_key)
        self.actiongemini_key.triggered.connect(self.util.set_gemini_key)
        self.actiontencent_key.triggered.connect(self.util.set_tencent_key)
        self.actionchatgpt_key.triggered.connect(self.util.set_chatgpt_key)
        self.actiondeepL_key.triggered.connect(self.util.set_deepL_key)
        self.actionElevenlabs_key.triggered.connect(self.util.set_elevenlabs_key)
        self.actiondeepLX_address.triggered.connect(self.util.set_deepLX_address)
        self.actionott_address.triggered.connect(self.util.set_ott_address)
        self.actionclone_address.triggered.connect(self.util.set_clone_address)
        self.actiontts_api.triggered.connect(self.util.set_ttsapi)
        self.actiontts_gptsovits.triggered.connect(self.util.set_gptsovits)
        self.action_ffmpeg.triggered.connect(lambda: self.util.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.util.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.util.open_url('discord'))
        self.action_models.triggered.connect(lambda: self.util.open_url('models'))
        self.action_dll.triggered.connect(lambda: self.util.open_url('dll'))
        self.action_gtrans.triggered.connect(lambda: self.util.open_url('gtrans'))
        self.action_cuda.triggered.connect(lambda: self.util.open_url('cuda'))
        self.action_website.triggered.connect(lambda: self.util.open_url('website'))
        self.statusLabel.clicked.connect(lambda: self.util.open_url('xinshou'))
        self.action_issue.triggered.connect(lambda: self.util.open_url('issue'))
        self.action_tool.triggered.connect(lambda: self.util.open_toolbox(0, False))
        self.actionyoutube.triggered.connect(self.util.open_youtube)
        self.action_about.triggered.connect(self.util.about)
        

        self.action_biaozhun.triggered.connect(self.util.set_biaozhun)
        # self.action_biaozhun.setCursor(Qt.PointingHandCursor)
        self.action_tiquzimu.triggered.connect(self.util.set_tiquzimu)
        # self.action_tiquzimu.setCursor(Qt.PointingHandCursor)
        self.action_tiquzimu_no.triggered.connect(self.util.set_tiquzimu_no)
        # self.action_tiquzimu_no.setCursor(Qt.PointingHandCursor)
        self.action_zimu_video.triggered.connect(self.util.set_zimu_video)
        # self.action_zimu_video.setCursor(Qt.PointingHandCursor)
        self.action_zimu_peiyin.triggered.connect(self.util.set_zimu_peiyin)
        # self.action_zimu_peiyin.setCursor(Qt.PointingHandCursor)
        self.action_yuyinshibie.triggered.connect(lambda: self.util.open_toolbox(2, False))
        # self.action_yuyinshibie.setCursor(Qt.PointingHandCursor)
        self.action_yuyinhecheng.triggered.connect(lambda: self.util.open_toolbox(3, False))
        # self.action_yuyinhecheng.setCursor(Qt.PointingHandCursor)
        self.action_yinshipinfenli.triggered.connect(lambda: self.util.open_toolbox(0, False))
        # self.action_yinshipinfenli.setCursor(Qt.PointingHandCursor)
        self.action_yingyinhebing.triggered.connect(lambda: self.util.open_toolbox(1, False))
        # self.action_yingyinhebing.setCursor(Qt.PointingHandCursor)
        self.action_geshi.triggered.connect(lambda: self.util.open_toolbox(4, False))
        # self.action_geshi.setCursor(Qt.PointingHandCursor)
        self.action_hun.triggered.connect(lambda: self.util.open_toolbox(5, False))
        # self.action_hun.setCursor(Qt.PointingHandCursor)
        self.action_fanyi.triggered.connect(lambda: self.util.open_toolbox(6, False))
        self.action_youtube.triggered.connect(self.util.open_youtube)
        self.action_separate.triggered.connect(self.util.open_separate)
        # 禁止随意移动sp.exe
        if not os.path.exists(os.path.join(config.rootdir,'videotrans')) or not os.path.exists(os.path.join(config.rootdir,'models')):
            QMessageBox.critical(self,config.transobj['anerror'],config.transobj['sp.exeerror'])
            return False
        import platform
        try:
            if platform.system().lower()=='windows' and (platform.release().lower()=='xp' or int(platform.release())<10):
                QMessageBox.critical(self,config.transobj['anerror'],config.transobj['only10'])
                return False
        except:
            pass


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
        # config.exit_ffmpeg=True
        if configure.TOOLBOX is not None:
            configure.TOOLBOX.close()
        if config.current_status == 'ing':
            config.current_status = 'end'
            msg = QMessageBox()
            msg.setWindowTitle(config.transobj['exit'])
            msg.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
            msg.setText(config.transobj['waitclear'])
            msg.addButton(QMessageBox.Yes)
            msg.setIcon(QMessageBox.Information)
            msg.exec()  # 显示消息框
        try:
            shutil.rmtree(config.rootdir+"/tmp",ignore_errors=True)
            shutil.rmtree(config.homedir+"/tmp",ignore_errors=True)
        except:
            pass
        event.accept()

    def get_setting(self):
        # 从缓存获取默认配置
        config.params["baidu_appid"] = self.settings.value("baidu_appid", "")
        config.params["source_language"] = self.settings.value("source_language", "")
        config.params["target_language"] = self.settings.value("target_language", "")
        config.params["voice_role"] = self.settings.value("voice_role", "")
        config.params["voice_autorate"] = self.settings.value("voice_autorate", False,bool)
        config.params["video_autorate"] = self.settings.value("video_autorate", False,bool)


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

        if self.settings.value("clone_voicelist", ""):
            config.clone_voicelist=self.settings.value("clone_voicelist", "").split(',')


        config.params["chatgpt_model"] = self.settings.value("chatgpt_model", config.params['chatgpt_model'])
        if config.params["chatgpt_model"] == 'large':
            config.params["chatgpt_model"] = 'large-v3'
        os.environ['OPENAI_API_KEY'] = config.params["chatgpt_key"]

        config.params["ttsapi_url"] = self.settings.value("ttsapi_url", "")
        config.params["ttsapi_extra"] = self.settings.value("ttsapi_extra", "pyvideotrans")
        config.params["ttsapi_voice_role"] = self.settings.value("ttsapi_voice_role", "")

        config.params["gptsovits_url"] = self.settings.value("gptsovits_url", "")
        config.params["gptsovits_extra"] = self.settings.value("gptsovits_extra", "pyvideotrans")
        config.params["gptsovits_role"] = self.settings.value("gptsovits_role", "")

        config.params["gemini_key"] = self.settings.value("gemini_key", "")

        config.params["azure_api"] = self.settings.value("azure_api", "")
        config.params["azure_key"] = self.settings.value("azure_key", "")
        config.params["azure_model"] = self.settings.value("azure_model", config.params['azure_model'])

        config.params["elevenlabstts_key"] = self.settings.value("elevenlabstts_key", "")

        config.params['translate_type'] = self.settings.value("translate_type", config.params['translate_type'])
        config.params['subtitle_type'] = self.settings.value("subtitle_type", config.params['subtitle_type'], int)
        config.proxy = self.settings.value("proxy", "", str)
        config.params['voice_rate'] = self.settings.value("voice_rate", config.params['voice_rate'], str)
        # config.params['voice_silence'] = self.settings.value("voice_silence", config.params['voice_silence'], str)
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
        self.settings.setValue("target_dir", config.params['target_dir'])
        self.settings.setValue("source_language", config.params['source_language'])
        self.settings.setValue("target_language", config.params['target_language'])
        self.settings.setValue("proxy", config.proxy)
        self.settings.setValue("whisper_model", config.params['whisper_model'])
        self.settings.setValue("whisper_type", config.params['whisper_type'])
        self.settings.setValue("model_type", config.params['model_type'])
        self.settings.setValue("voice_rate", config.params['voice_rate'])
        self.settings.setValue("voice_role", config.params['voice_role'])
        # self.settings.setValue("voice_silence", config.params['voice_silence'])
        self.settings.setValue("voice_autorate", config.params['voice_autorate'])
        self.settings.setValue("video_autorate", config.params['video_autorate'])
        self.settings.setValue("subtitle_type", config.params['subtitle_type'])
        self.settings.setValue("translate_type", config.params['translate_type'])
        self.settings.setValue("cuda", config.params['cuda'])
        self.settings.setValue("only_video", config.params['only_video'])
        self.settings.setValue("tts_type", config.params['tts_type'])
        self.settings.setValue("clone_api", config.params['clone_api'])
        self.settings.setValue("voice_autorate", config.params['voice_autorate'])
        self.settings.setValue("video_autorate", config.params['video_autorate'])
        self.settings.setValue("clone_voicelist", ','.join(config.clone_voicelist) )

