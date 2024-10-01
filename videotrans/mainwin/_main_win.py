import platform
import shutil
import threading
import time

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QMessageBox, QLabel, QPushButton, QToolBar, QWidget, QVBoxLayout

from videotrans import VERSION
from videotrans.configure import config
from videotrans.translator import TRANSLASTE_NAME_LIST
from videotrans.tts import CLONE_VOICE_TTS, CHATTTS, TTS_API, GPTSOVITS_TTS, COSYVOICE_TTS, FISHTTS, OPENAI_TTS
from videotrans.ui.en import Ui_MainWindow

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None, width=1200, height=700):
        super(MainWindow, self).__init__(parent)
        self.width = int(width * 0.8)
        self.height = int(height * 0.8)
        self.resize(self.width, self.height)
        self.win_action = None
        self.moshis = None
        self.target_dir=None
        self.app_mode = "biaozhun" if not config.params['app_mode'] else config.params['app_mode']
        # 当前所有可用角色列表
        self.current_rolelist = []

        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.rawtitle = f"{config.transobj['softname']} {VERSION}  {'使用文档' if config.defaulelang == 'zh' else 'Documents'}  pyvideotrans.com "
        self.setWindowTitle(self.rawtitle)
        self.languagename = config.langnamelist
        self.setupUi(self)
        self.initUI()
        self.bind_action()
        self.show()

        QTimer.singleShot(100, self._set_cache_set)
        QTimer.singleShot(100, self.start_subform)
        QTimer.singleShot(100, self._bindsignal)


    def initUI(self):

        # 底部状态栏
        self.statusLabel = QPushButton(config.transobj["Open Documents"])
        self.statusBar.addWidget(self.statusLabel)
        self.rightbottom = QPushButton(config.transobj['juanzhu'])
        self.container = QToolBar()
        self.container.addWidget(self.rightbottom)
        self.statusBar.addPermanentWidget(self.container)
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.source_language.addItems(self.languagename)
        # 目标语言改变时，如果当前tts是 edgeTTS，则根据目标语言去修改显示的角色
        self.target_language.addItems(["-"] + self.languagename)
        #  translation type
        self.translate_type.addItems(TRANSLASTE_NAME_LIST)


    # 设置各种默认值和设置文字 提示等
    def _set_cache_set(self):
        from videotrans.component.controlobj import TextGetdir
        self.splitter.setSizes([self.width - 400, 400])
        self.scroll_area.setWidgetResizable(True)
        viewport = QWidget(self.scroll_area)
        self.scroll_area.setWidget(viewport)
        self.processlayout = QVBoxLayout(viewport)
        self.processlayout.setAlignment(Qt.AlignTop)
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
        self.import_sub.setVisible(True)
        self.export_sub.setVisible(True)
        self.set_line_role.setVisible(True)
        self.subtitle_layout.insertWidget(0, self.subtitle_tips)
        self.subtitle_layout.insertWidget(1, self.subtitle_area)

        if platform.system() == 'Darwin':
            self.enable_cuda.hide()
            config.params['cuda']=False
        self.statusLabel.setCursor(Qt.PointingHandCursor)
        self.rightbottom.setCursor(Qt.PointingHandCursor)
        self.source_mp4.setAcceptDrops(True)

        # 隐藏倒计时
        self.stop_djs.setStyleSheet("""background-color:#148CD2;color:#ffffff""")
        self.stop_djs.setToolTip(config.transobj['Click to pause and modify subtitles for more accurate processing'])

        self.continue_compos.setToolTip(config.transobj['Click to start the next step immediately'])
        self.stop_djs.setCursor(Qt.PointingHandCursor)
        self.continue_compos.setCursor(Qt.PointingHandCursor)
        self.startbtn.setCursor(Qt.PointingHandCursor)
        self.btn_get_video.setCursor(Qt.PointingHandCursor)
        self.btn_save_dir.setCursor(Qt.PointingHandCursor)

        self.proxy.setText(config.params['proxy'])
        # 目标语言改变
        self.listen_btn.setCursor(Qt.PointingHandCursor)

        #         model
        self.split_type.addItems([config.transobj['whisper_type_all'], config.transobj['whisper_type_avg']])
        self.split_type.setToolTip(config.transobj['fenge_tips'])

        self.model_name.addItems(config.WHISPER_MODEL_LIST)


        self.subtitle_tips.setToolTip(config.transobj['meitiaozimugeshi'])

        self.import_sub.setCursor(Qt.PointingHandCursor)
        self.import_sub.setToolTip(config.transobj['daoruzimutips'])

        self.export_sub.setText(config.transobj['Export srt'])
        self.export_sub.setCursor(Qt.PointingHandCursor)
        self.export_sub.setToolTip(
            config.transobj['When subtitles exist, the subtitle content can be saved to a local SRT file'])

        self.set_line_role.setCursor(Qt.PointingHandCursor)
        self.set_line_role.setToolTip(config.transobj['Set up separate dubbing roles for each subtitle to be used'])

        self.subtitle_type.addItems(
            [
                config.transobj['nosubtitle'],
                config.transobj['embedsubtitle'],
                config.transobj['softsubtitle'],
                config.transobj['embedsubtitle2'],
                config.transobj['softsubtitle2']
            ])
        self.subtitle_type.setCurrentIndex(config.params['subtitle_type'])

        try:
            config.params['recogn_type'] = int(config.params['recogn_type'])
        except Exception:
            config.params['recogn_type'] = 0
        print(f"{config.params['recogn_type']=}")
        self.recogn_type.setCurrentIndex(config.params['recogn_type'])
        if config.params['recogn_type'] > 1:
            self.model_name_help.setVisible(False)
        else:
            self.model_name_help.setCursor(Qt.PointingHandCursor)
            self.model_name_help.clicked.connect(self.win_action.show_model_help)


        try:
            config.params['tts_type'] = int(config.params['tts_type'])
        except Exception:
            config.params['tts_type'] = 0

        if config.params['split_type']:
            d = {"all": 0, "avg": 1}
            self.split_type.setCurrentIndex(d[config.params['split_type']])

        if config.params['subtitle_type'] and int(config.params['subtitle_type']) > 0:
            self.subtitle_type.setCurrentIndex(int(config.params['subtitle_type']))

        if config.params['model_name'] in config.WHISPER_MODEL_LIST:
            self.model_name.setCurrentText(config.params['model_name'])

        try:
            self.voice_rate.setValue(int(config.params['voice_rate'].replace('%', '')))
        except Exception:
            self.voice_rate.setValue(0)

        self.split_type.setDisabled(True if config.params['recogn_type'] > 0 else False)
        self.voice_autorate.setChecked(bool(config.params['voice_autorate']))
        self.video_autorate.setChecked(bool(config.params['video_autorate']))
        self.append_video.setChecked(bool(config.params['append_video']))
        self.clear_cache.setChecked(bool(config.params.get('clear_cache')))
        self.enable_cuda.setChecked(True if config.params['cuda'] else False)
        self.only_video.setChecked(True if config.params['only_video'] else False)
        self.is_separate.setChecked(True if config.params['is_separate'] else False)

    def bind_action(self):
        from videotrans.util import tools
        from videotrans.mainwin._actions import WinAction

        self.win_action = WinAction(self)
        self.win_action.tts_type_change(config.params['tts_type'])
        try:
            config.params['translate_type'] = int(config.params['translate_type'])
        except Exception:
            config.params['translate_type'] = 0
        self.translate_type.setCurrentIndex(config.params['translate_type'])

        if config.params['source_language'] and config.params['source_language'] in self.languagename:
            self.source_language.setCurrentText(config.params['source_language'])
        try:
            config.params['tts_type']=int(config.params['tts_type'])
        except:
            config.params['tts_type']=0
        
        self.tts_type.setCurrentIndex(config.params['tts_type'])
        if config.params['tts_type'] == CLONE_VOICE_TTS:
            self.voice_role.addItems(config.params["clone_voicelist"])
            threading.Thread(target=tools.get_clone_role).start()
        elif config.params['tts_type'] == CHATTTS:
            self.voice_role.addItems(['No'] + list(config.ChatTTS_voicelist))
        elif config.params['tts_type'] == TTS_API:
            self.voice_role.addItems(config.params['ttsapi_voice_role'].strip().split(','))
        elif config.params['tts_type'] == GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
        elif config.params['tts_type'] == COSYVOICE_TTS:
            rolelist = tools.get_cosyvoice_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['clone'])
        elif config.params['tts_type'] == FISHTTS:
            rolelist = tools.get_fishtts_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['FishTTS'])
        elif config.params['tts_type'] == OPENAI_TTS:
            rolelist = config.openaiTTS_rolelist
            self.voice_role.addItems(rolelist)
        elif self.win_action.change_by_lang(config.params['tts_type']):
            # 属于随语言变化的配音渠道
            self.voice_role.clear()



        # 设置 tts_type

        if config.params['target_language'] and config.params['target_language'] in self.languagename:
            self.target_language.setCurrentText(config.params['target_language'])
            # 根据目标语言更新角色列表
            self.win_action.set_voice_role(config.params['target_language'])
            # 设置默认角色列表
            if config.params['voice_role'] and config.params['voice_role'] != 'No' and self.current_rolelist and  config.params['voice_role'] in self.current_rolelist:
                self.voice_role.setCurrentText(config.params['voice_role'])
                self.win_action.show_listen_btn(config.params['voice_role'])

        # tts_type 改变时，重设角色
        self.tts_type.currentIndexChanged.connect(self.win_action.tts_type_change)
        self.translate_type.currentIndexChanged.connect(self.win_action.set_translate_type)
        self.voice_role.currentTextChanged.connect(self.win_action.show_listen_btn)
        self.target_language.currentTextChanged.connect(self.win_action.set_voice_role)

        self.set_line_role.clicked.connect(self.win_action.set_line_role_fun)
        self.proxy.textChanged.connect(self.win_action.change_proxy)
        self.import_sub.clicked.connect(self.win_action.import_sub_fun)
        self.export_sub.clicked.connect(self.win_action.export_sub_fun)
        self.startbtn.clicked.connect(self.win_action.check_start)
        self.btn_save_dir.clicked.connect(self.win_action.get_save_dir)
        self.btn_get_video.clicked.connect(self.win_action.get_mp4)
        self.stop_djs.clicked.connect(self.win_action.reset_timeid)
        self.continue_compos.clicked.connect(self.win_action.set_djs_timeout)
        self.listen_btn.clicked.connect(self.win_action.listen_voice_fun)
        self.split_type.currentIndexChanged.connect(self.win_action.check_split_type)
        self.model_name.currentTextChanged.connect(self.win_action.check_model_name)
        self.recogn_type.currentIndexChanged.connect(self.win_action.recogn_type_change)
        self.voice_rate.valueChanged.connect(self.win_action.voice_rate_changed)
        self.voice_autorate.stateChanged.connect(
            lambda: self.win_action.autorate_changed(self.voice_autorate.isChecked(), "voice"))
        self.video_autorate.stateChanged.connect(
            lambda: self.win_action.autorate_changed(self.video_autorate.isChecked(), "video"))
        self.append_video.stateChanged.connect(
            lambda: self.win_action.autorate_changed(self.video_autorate.isChecked(), "append_video"))
        self.addbackbtn.clicked.connect(self.win_action.get_background)
        self.enable_cuda.toggled.connect(self.win_action.check_cuda)
        self.action_ffmpeg.triggered.connect(lambda: self.win_action.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.win_action.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.win_action.open_url('discord'))
        self.action_models.triggered.connect(lambda: self.win_action.open_url('models'))
        self.action_dll.triggered.connect(lambda: self.win_action.open_url('dll'))
        self.action_gtrans.triggered.connect(lambda: self.win_action.open_url('gtrans'))
        self.action_cuda.triggered.connect(lambda: self.win_action.open_url('cuda'))
        self.action_online.triggered.connect(lambda: self.win_action.open_url('online'))
        self.action_website.triggered.connect(lambda: self.win_action.open_url('website'))
        self.action_blog.triggered.connect(lambda: self.win_action.open_url('blog'))
        self.statusLabel.clicked.connect(lambda: self.win_action.open_url('help'))
        self.action_issue.triggered.connect(lambda: self.win_action.open_url('issue'))
        self.action_about.triggered.connect(self.win_action.about)
        self.action_xinshoujandan.triggered.connect(self.win_action.set_xinshoujandann)
        self.action_biaozhun.triggered.connect(self.win_action.set_biaozhun)
        self.action_tiquzimu.triggered.connect(self.win_action.set_tiquzimu)

        self.moshis = {
            "biaozhun_jd": self.action_xinshoujandan,
            "biaozhun": self.action_biaozhun,
            "tiqu": self.action_tiquzimu
        }

        self.action_clearcache.triggered.connect(self.win_action.clearcache)
        self.rightbottom.clicked.connect(self.win_action.about)


    def start_subform(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['installffmpeg'])
            self.startbtn.setText(config.transobj['installffmpeg'])
            self.startbtn.setDisabled(True)
            self.startbtn.setStyleSheet("""color:#ff0000""")

        if self.app_mode == 'biaozhun_jd':
            self.win_action.set_xinshoujandann()
        elif self.app_mode == 'biaozhun':
            self.win_action.set_biaozhun()
        elif self.app_mode == 'tiqu':
            self.win_action.set_tiquzimu()

        from videotrans.winform import baidu, ai302, ai302tts, fn_audiofromvideo, azure, azuretts, chatgpt, chattts, \
            clone, \
            cosyvoice, deepL, deepLX, doubao, elevenlabs, fn_fanyisrt, fishtts, gemini, gptsovits, fn_hebingsrt, \
            fn_hunliu, \
            localllm, ott, fn_peiyin, fn_recogn, fn_separate, setini, tencent, transapi, ttsapi, fn_vas, fn_watermark, \
            fn_youtube, \
            zh_recogn, zijiehuoshan, fn_videoandaudio, fn_videoandsrt, fn_formatcover, openaitts, recognapi,sttapi, \
            openairecognapi, \
            fn_subtitlescover, fn_editer

        self.actionbaidu_key.triggered.connect(baidu.openwin)
        self.actionazure_key.triggered.connect(azure.openwin)
        self.actionazure_tts.triggered.connect(azuretts.openwin)
        self.actiongemini_key.triggered.connect(gemini.openwin)
        self.actiontencent_key.triggered.connect(tencent.openwin)
        self.actionchatgpt_key.triggered.connect(chatgpt.openwin)

        self.actionai302_key.triggered.connect(ai302.openwin)
        self.actionlocalllm_key.triggered.connect(localllm.openwin)
        self.actionzijiehuoshan_key.triggered.connect(zijiehuoshan.openwin)
        self.actiondeepL_key.triggered.connect(deepL.openwin)
        self.actionElevenlabs_key.triggered.connect(elevenlabs.openwin)
        self.actiondeepLX_address.triggered.connect(deepLX.openwin)
        self.actionott_address.triggered.connect(ott.openwin)
        self.actionclone_address.triggered.connect(clone.openwin)
        self.actionchattts_address.triggered.connect(chattts.openwin)
        self.actionai302tts_address.triggered.connect(ai302tts.openwin)
        self.actiontts_api.triggered.connect(ttsapi.openwin)
        self.actionzhrecogn_api.triggered.connect(zh_recogn.openwin)
        self.actionrecognapi.triggered.connect(recognapi.openwin)
        self.actionsttapi.triggered.connect(sttapi.openwin)
        self.actiondoubao_api.triggered.connect(doubao.openwin)
        self.actiontrans_api.triggered.connect(transapi.openwin)
        self.actiontts_gptsovits.triggered.connect(gptsovits.openwin)
        self.actiontts_cosyvoice.triggered.connect(cosyvoice.openwin)
        self.actionopenaitts_key.triggered.connect(openaitts.openwin)
        self.actionopenairecognapi_key.triggered.connect(openairecognapi.openwin)
        self.actiontts_fishtts.triggered.connect(fishtts.openwin)
        self.actionyoutube.triggered.connect(fn_youtube.openwin)
        self.actionwatermark.triggered.connect(fn_watermark.openwin)
        self.actionsepar.triggered.connect(fn_separate.openwin)
        self.actionsetini.triggered.connect(setini.openwin)
        self.actionvideoandaudio.triggered.connect(fn_videoandaudio.openwin)
        self.actionvideoandsrt.triggered.connect(fn_videoandsrt.openwin)
        self.actionformatcover.triggered.connect(fn_formatcover.openwin)
        self.actionsubtitlescover.triggered.connect(fn_subtitlescover.openwin)
        self.action_hebingsrt.triggered.connect(fn_hebingsrt.openwin)
        self.action_yinshipinfenli.triggered.connect(fn_audiofromvideo.openwin)
        self.action_hun.triggered.connect(fn_hunliu.openwin)
        self.action_yingyinhebing.triggered.connect(fn_vas.openwin)
        self.action_subtitleediter.triggered.connect(fn_editer.openwin)
        self.action_fanyi.triggered.connect(fn_fanyisrt.openwin)
        self.action_yuyinshibie.triggered.connect(fn_recogn.openwin)
        self.action_yuyinhecheng.triggered.connect(fn_peiyin.openwin)

    def _bindsignal(self):
        try:
            from videotrans.task.check_update import CheckUpdateWorker
            from videotrans.task.get_role_list import GetRoleWorker
            from videotrans.task.job import start_thread
            from videotrans.mainwin._signal import UUIDSignalThread
            update_role = GetRoleWorker(parent=self)
            update_role.start()
            self.check_update = CheckUpdateWorker(parent=self)
            self.check_update.start()

            uuid_signal = UUIDSignalThread(parent=self)
            uuid_signal.uito.connect(self.win_action.update_data)
            uuid_signal.start()
            start_thread(self)
        except Exception as e:
            print(e)

    def closeEvent(self, event):
        # 在关闭窗口前执行的操作
        config.exit_soft = True
        config.current_status='stop'
        self.hide()
        print('等待所有进程退出...')
        time.sleep(2)
        from videotrans.util import tools
        tools._unlink_tmp()
        try:
            for w in config.child_forms.values():
                if w and hasattr(w, 'close'):
                    w.close()
        except Exception:
            pass
        try:
            tools.kill_ffmpeg_processes()
        except Exception:
            pass

        time.sleep(3)
        tools._unlink_tmp()
        event.accept()
