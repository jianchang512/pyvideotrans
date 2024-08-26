import shutil
import threading
import time
import warnings

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QSettings, Qt, QSize, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QMessageBox, QLabel, QPushButton, QToolBar, QWidget, QVBoxLayout

from videotrans.task.job import start_thread
from videotrans.winform import fn_videoandaudio, fn_videoandsrt

warnings.filterwarnings('ignore')

from videotrans.util import tools
from videotrans.translator import TRANSNAMES
from videotrans.configure import config
from videotrans import VERSION
from videotrans.component.controlobj import TextGetdir
from videotrans.ui.en import Ui_MainWindow
from pathlib import Path
import platform

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None, width=1200, height=700):
        super(MainWindow, self).__init__(parent)

        self.width = int(width * 0.8)
        self.height = int(height * 0.8)
        self.bwidth = int(width * 0.7)
        self.bheight = int(height * 0.7)
        self.lefttopx = int(width * 0.15)
        self.lefttopy = int(height * 0.15)
        self.resize(self.width, self.height)

        self.task = None
        self.shitingobj = None
        self.util = None
        self.moshis = None
        # 各个子窗口

        self.app_mode = "biaozhun" if not config.params['app_mode'] else config.params['app_mode']
        self.processbtns = {}

        # 当前所有可用角色列表
        self.current_rolelist = []
        config.params['line_roles'] = {}
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
        self.rawtitle = f"{config.transobj['softname']}{VERSION}  {'使用文档' if config.defaulelang == 'zh' else 'Documents'}  pyvideotrans.com "
        self.setWindowTitle(self.rawtitle)
        self.setupUi(self)
        self.initUI()
        self.bind_action()
        self.show()
        QTimer.singleShot(200, self.start_subform)

    def start_subform(self):
        # 打开工具箱
        from videotrans.winform import baidu, ai302, ai302tts, fn_audiofromvideo, azure, azuretts, chatgpt, chattts, clone, \
            cosyvoice, deepL, deepLX, doubao, elevenlabs, fn_fanyisrt, fishtts, gemini, gptsovits, fn_hebingsrt, fn_hunliu, \
            localllm, ott, fn_peiyin, fn_recogn, fn_separate, setini, tencent, transapi, ttsapi, fn_vas, fn_watermark, fn_youtube, \
            zh_recogn, zijiehuoshan

        self.actionbaidu_key.triggered.connect(baidu.open)
        self.actionazure_key.triggered.connect(azure.open)
        self.actionazure_tts.triggered.connect(azuretts.open)
        self.actiongemini_key.triggered.connect(gemini.open)
        self.actiontencent_key.triggered.connect(tencent.open)
        self.actionchatgpt_key.triggered.connect(chatgpt.open)
        self.actionai302_key.triggered.connect(ai302.open)
        self.actionlocalllm_key.triggered.connect(localllm.open)
        self.actionzijiehuoshan_key.triggered.connect(zijiehuoshan.open)
        self.actiondeepL_key.triggered.connect(deepL.open)
        self.actionElevenlabs_key.triggered.connect(elevenlabs.open)
        self.actiondeepLX_address.triggered.connect(deepLX.open)
        self.actionott_address.triggered.connect(ott.open)
        self.actionclone_address.triggered.connect(clone.open)
        self.actionchattts_address.triggered.connect(chattts.open)
        self.actionai302tts_address.triggered.connect(ai302tts.open)
        self.actiontts_api.triggered.connect(ttsapi.open)
        self.actionzhrecogn_api.triggered.connect(zh_recogn.open)
        self.actiondoubao_api.triggered.connect(doubao.open)
        self.actiontrans_api.triggered.connect(transapi.open)
        self.actiontts_gptsovits.triggered.connect(gptsovits.open)
        self.actiontts_cosyvoice.triggered.connect(cosyvoice.open)
        self.actiontts_fishtts.triggered.connect(fishtts.open)
        self.actionyoutube.triggered.connect(fn_youtube.open)
        self.actionwatermark.triggered.connect(fn_watermark.open)
        self.actionsepar.triggered.connect(fn_separate.open)
        self.actionsetini.triggered.connect(setini.open)
        self.actionvideoandaudio.triggered.connect(fn_videoandaudio.open)
        self.actionvideoandsrt.triggered.connect(fn_videoandsrt.open)
        self.action_hebingsrt.triggered.connect(fn_hebingsrt.open)
        self.action_yinshipinfenli.triggered.connect(fn_audiofromvideo.open)
        self.action_hun.triggered.connect(fn_hunliu.open)
        self.action_yingyinhebing.triggered.connect(fn_vas.open)
        self.action_fanyi.triggered.connect(fn_fanyisrt.open)
        self.action_yuyinshibie.triggered.connect(fn_recogn.open)
        self.action_yuyinhecheng.triggered.connect(fn_peiyin.open)
        if config.params['tts_type'] and not config.params['tts_type'] in ['edgeTTS', 'AzureTTS']:
            self.util.tts_type_change(config.params['tts_type'])

    def initUI(self):
        self.settings = QSettings("Jameson", "VideoTranslate")

        self.languagename = config.langnamelist

        self.splitter.setSizes([self.width - 400, 400])

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
        self.proxy.setText(config.params['proxy'])
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
        translate_name = config.params['translate_type'] if config.params['translate_type'] in TRANSNAMES else \
            TRANSNAMES[0]

        self.translate_type.setCurrentText(translate_name)

        #         model
        self.whisper_type.addItems([config.transobj['whisper_type_all'], config.transobj['whisper_type_avg']])
        self.whisper_type.setToolTip(config.transobj['fenge_tips'])
        if config.params['whisper_type']:
            d = {"all": 0, "avg": 1}
            self.whisper_type.setCurrentIndex(d[config.params['whisper_type']])
        self.whisper_model.addItems(config.model_list)
        if config.params['whisper_model'] in config.model_list:
            self.whisper_model.setCurrentText(config.params['whisper_model'])
        if config.params['model_type'] == 'openai':
            self.model_type.setCurrentIndex(1)
            self.whisper_type.setDisabled(True)
        elif config.params['model_type'] == 'GoogleSpeech':
            self.model_type.setCurrentIndex(2)
            self.whisper_model.setDisabled(True)
            self.whisper_type.setDisabled(True)
        elif config.params['model_type'] == 'zh_recogn':
            self.model_type.setCurrentIndex(3)
            self.whisper_model.setDisabled(True)
            self.whisper_type.setDisabled(True)
        elif config.params['model_type'] == 'doubao':
            self.model_type.setCurrentIndex(4)
            self.whisper_model.setDisabled(True)
            self.whisper_type.setDisabled(True)
        if config.params['only_video']:
            self.only_video.setChecked(True)
        try:
            self.voice_rate.setValue(int(config.params['voice_rate'].replace('%', '')))
        except Exception:
            self.voice_rate.setValue(0)

        self.voice_autorate.setChecked(config.params['voice_autorate'])
        self.video_autorate.setChecked(config.params['video_autorate'])
        self.append_video.setChecked(config.params['append_video'])

        if platform.system() == 'Darwin':
            self.enable_cuda.hide()

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
        # 底部状态栏
        self.statusLabel = QPushButton(config.transobj["Open Documents"])
        self.statusLabel.setCursor(QtCore.Qt.PointingHandCursor)
        self.statusBar.addWidget(self.statusLabel)

        self.rightbottom = QPushButton(config.transobj['juanzhu'])
        self.rightbottom.setCursor(QtCore.Qt.PointingHandCursor)

        self.container = QToolBar()
        self.container.addWidget(self.rightbottom)
        self.statusBar.addPermanentWidget(self.container)
        # 创建 Scroll Area
        self.scroll_area.setWidgetResizable(True)
        # 创建一个 QWidget 作为 Scroll Area 的 viewport
        viewport = QWidget(self.scroll_area)
        self.scroll_area.setWidget(viewport)
        # 创建一个垂直布局管理器，用于在 viewport 中放置按钮
        self.processlayout = QVBoxLayout(viewport)
        # 设置布局管理器的对齐方式为顶部对齐
        self.processlayout.setAlignment(Qt.AlignTop)
        # 设置QAction的大小
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # 设置QToolBar的大小，影响其中的QAction的大小
        self.toolBar.setIconSize(QSize(100, 45))  # 设置图标大小
        self.import_sub.setCursor(Qt.PointingHandCursor)
        self.import_sub.setToolTip(config.transobj['daoruzimutips'])

        self.export_sub.setText(config.transobj['Export srt'])
        self.export_sub.setCursor(Qt.PointingHandCursor)
        self.export_sub.setToolTip(
            config.transobj['When subtitles exist, the subtitle content can be saved to a local SRT file'])

        self.set_line_role.setCursor(Qt.PointingHandCursor)
        self.set_line_role.setToolTip(config.transobj['Set up separate dubbing roles for each subtitle to be used'])

        if config.params['subtitle_type'] and int(config.params['subtitle_type']) > 0:
            self.subtitle_type.setCurrentIndex(int(config.params['subtitle_type']))
        start_thread(self)

    def bind_action(self):
        from videotrans.mainwin.secwin import SecWindow
        self.util = SecWindow(self)

        if config.params['tts_type'] == 'clone-voice':
            self.voice_role.addItems(config.params["clone_voicelist"])
            threading.Thread(target=tools.get_clone_role).start()
        elif config.params['tts_type'] == 'ChatTTS':
            self.voice_role.addItems(['No'] + list(config.ChatTTS_voicelist))
        elif config.params['tts_type'] == 'TTS-API':
            self.voice_role.addItems(config.params['ttsapi_voice_role'].strip().split(','))
        elif config.params['tts_type'] == 'GPT-SoVITS':
            rolelist = tools.get_gptsovits_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
        elif config.params['tts_type'] == 'CosyVoice':
            rolelist = tools.get_cosyvoice_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['clone'])
        elif config.params['tts_type'] == 'FishTTS':
            rolelist = tools.get_fishtts_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['FishTTS'])

        if config.params['tts_type']:
            if config.params['tts_type'] not in ['edgeTTS', 'AzureTTS']:
                self.voice_role.addItems(['No'])

        if config.params['is_separate']:
            self.is_separate.setChecked(True)

        # 设置 tts_type
        self.tts_type.addItems(config.params['tts_type_list'])
        self.tts_type.setCurrentText(config.params['tts_type'])
        self.set_line_role.clicked.connect(self.util.set_line_role_fun)

        if config.params['target_language'] and config.params['target_language'] in self.languagename:
            self.target_language.setCurrentText(config.params['target_language'])
            # 根据目标语言更新角色列表
            self.util.set_voice_role(config.params['target_language'])
            # 设置默认角色列表
            print(config.params['voice_role'])
            if config.params['voice_role'] and config.params['voice_role'] != 'No' and self.current_rolelist and \
                    config.params['voice_role'] in self.current_rolelist:
                self.voice_role.setCurrentText(config.params['voice_role'])
                self.util.show_listen_btn(config.params['voice_role'])
                print('2222')

        self.proxy.textChanged.connect(self.util.change_proxy)

        # menubar
        self.import_sub.clicked.connect(self.util.import_sub_fun)

        self.export_sub.clicked.connect(self.util.export_sub_fun)

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
        self.video_autorate.stateChanged.connect(
            lambda: self.util.autorate_changed(self.video_autorate.isChecked(), "video"))
        self.append_video.stateChanged.connect(
            lambda: self.util.autorate_changed(self.video_autorate.isChecked(), "append_video"))

        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.util.tts_type_change)
        self.addbackbtn.clicked.connect(self.util.get_background)

        self.is_separate.toggled.connect(self.util.is_separate_fun)
        self.enable_cuda.toggled.connect(self.util.check_cuda)

        self.action_ffmpeg.triggered.connect(lambda: self.util.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.util.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.util.open_url('discord'))
        self.action_models.triggered.connect(lambda: self.util.open_url('models'))
        self.action_dll.triggered.connect(lambda: self.util.open_url('dll'))
        self.action_gtrans.triggered.connect(lambda: self.util.open_url('gtrans'))
        self.action_cuda.triggered.connect(lambda: self.util.open_url('cuda'))
        self.action_online.triggered.connect(lambda: self.util.open_url('online'))
        self.action_website.triggered.connect(lambda: self.util.open_url('website'))
        self.action_blog.triggered.connect(lambda: self.util.open_url('blog'))
        self.statusLabel.clicked.connect(lambda: self.util.open_url('help'))
        self.action_issue.triggered.connect(lambda: self.util.open_url('issue'))

        self.action_about.triggered.connect(self.util.about)

        self.action_xinshoujandan.triggered.connect(self.util.set_xinshoujandann)

        self.action_biaozhun.triggered.connect(self.util.set_biaozhun)

        self.action_tiquzimu.triggered.connect(self.util.set_tiquzimu)



        if self.app_mode == 'biaozhun_jd':
            self.util.set_xinshoujandann()
        elif self.app_mode == 'biaozhun':
            self.util.set_biaozhun()
        elif self.app_mode == 'tiqu':
            self.util.set_tiquzimu()

        self.moshis = {
            "biaozhun_jd": self.action_xinshoujandan,
            "biaozhun": self.action_biaozhun,
            "tiqu": self.action_tiquzimu
        }

        self.action_clearcache.triggered.connect(self.util.clearcache)

        # 禁止随意移动sp.exe
        if not Path(config.rootdir + '/videotrans').exists() or not Path(config.rootdir + '/models').exists():
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['sp.exeerror'])
            return False

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

        try:
            from videotrans.task.check_update import CheckUpdateWorker
            from videotrans.task.logs_worker import LogsWorker
            from videotrans.task.get_role_list import GetRoleWorker
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
        try:
            shutil.rmtree(config.rootdir + "/tmp", ignore_errors=True)
            shutil.rmtree(config.homedir + "/tmp", ignore_errors=True)
            for w in [config.separatew,
                      config.hebingw,
                      config.chatgptw,
                      config.azurew,
                      config.geminiw,
                      config.gptsovitsw,
                      config.fishttsw,
                      config.transapiw,
                      config.ttsapiw,
                      config.zijiew,
                      config.baiduw,
                      config.zhrecognw,
                      config.chatttsw,
                      config.clonew,
                      config.ottw,
                      config.elevenlabsw,
                      config.deeplxw,
                      config.azurettsw,
                      config.deeplw,
                      config.youw,
                      config.linerolew,
                      config.llmw,
                      config.tencentw, config.doubaow,
                      config.cosyvoicew,
                      config.ai302fyw,
                      config.ai302ttsw,
                      config.setiniw,
                      config.waterform,
                      config.audioform,
                      config.hunliuform,
                      config.vasform,
                      config.fanyiform,
                      config.recognform,
                      config.peiyinform,
                      config.vandaform,
                      config.vandsrtform]:
                if w and hasattr(w, 'close'):
                    w.close()


        except Exception:
            pass
        try:
            tools.kill_ffmpeg_processes()
        except Exception:
            pass
        print('等待所有进程退出...')
        time.sleep(2)
        event.accept()



    # 存储本地数据
    def save_setting(self):
        config.getset_params(config.params)
