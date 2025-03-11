import platform

import threading
import time,os


from PySide6.QtCore import Qt, QTimer, QSettings, QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QPushButton, QToolBar


from videotrans.configure import config


from videotrans.ui.en import Ui_MainWindow
from videotrans.util import tools
from videotrans.mainwin._actions import WinAction
from videotrans import VERSION, recognition
from videotrans  import tts
from pathlib import Path



class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None, width=1200, height=650):
        super(MainWindow, self).__init__(parent)
        self.width = width
        self.height = height
        self.resize(width, height)
        self.win_action = None
        self.moshis = None
        self.target_dir=None
        self.app_mode = "biaozhun"
        # 当前所有可用角色列表
        self.current_rolelist = []

        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))

        self.languagename = config.langnamelist
        self.setupUi(self)
        self.initUI()
        self.show()
        QTimer.singleShot(50, self._set_cache_set)
        QTimer.singleShot(100, self._start_subform)
        QTimer.singleShot(500, self._bindsignal)

    def initUI(self):
        from videotrans.translator import TRANSLASTE_NAME_LIST
        self.statusLabel = QPushButton(config.transobj["Open Documents"])
        self.statusBar.addWidget(self.statusLabel)
        self.rightbottom = QPushButton(config.transobj['juanzhu'])
        self.container = QToolBar()
        self.container.addWidget(self.rightbottom)
        self.statusBar.addPermanentWidget(self.container)
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.source_language.addItems(self.languagename)
        self.target_language.addItems(["-"] + self.languagename[:-1])
        self.translate_type.addItems(TRANSLASTE_NAME_LIST)

        
        self.rawtitle = f"{config.transobj['softname']} {VERSION}  {'使用文档' if config.defaulelang == 'zh' else 'Documents'}  pyvideotrans.com "
        self.setWindowTitle(self.rawtitle)

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
        self.voice_role.clear()
        if config.params['tts_type'] == tts.CLONE_VOICE_TTS:
            self.voice_role.addItems(config.params["clone_voicelist"])
            threading.Thread(target=tools.get_clone_role).start()
        elif config.params['tts_type'] == tts.CHATTTS:
            self.voice_role.addItems(['No'] + list(config.ChatTTS_voicelist))
        elif config.params['tts_type'] == tts.TTS_API:
            self.voice_role.addItems(config.params['ttsapi_voice_role'].strip().split(','))
        elif config.params['tts_type'] == tts.GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
        elif config.params['tts_type'] == tts.COSYVOICE_TTS:
            rolelist = tools.get_cosyvoice_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['clone'])
        elif config.params['tts_type'] == tts.F5_TTS:
            rolelist = tools.get_f5tts_role()
            self.voice_role.addItems(['clone']+list(rolelist.keys()) if rolelist else ['clone'])
        elif config.params['tts_type'] == tts.FISHTTS:
            rolelist = tools.get_fishtts_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['No'])
        elif config.params['tts_type'] == tts.ELEVENLABS_TTS:
            rolelist = tools.get_elevenlabs_role()
            self.voice_role.addItems(['No']+rolelist)
        elif config.params['tts_type'] == tts.OPENAI_TTS:
            rolelist = config.params.get('openaitts_role','')
            self.voice_role.addItems(['No']+rolelist.split(','))
        elif self.win_action.change_by_lang(config.params['tts_type']):
            self.voice_role.clear()

        if config.params['target_language'] and config.params['target_language'] in self.languagename:
            self.target_language.setCurrentText(config.params['target_language'])
            self.win_action.set_voice_role(config.params['target_language'])
            if config.params['voice_role'] and config.params['voice_role'] != 'No' and self.current_rolelist and  config.params['voice_role'] in self.current_rolelist:
                self.voice_role.setCurrentText(config.params['voice_role'])
                self.win_action.show_listen_btn(config.params['voice_role'])



        try:
            config.params['recogn_type'] = int(config.params['recogn_type'])
        except Exception:
            config.params['recogn_type'] = 0
        #if config.params['recogn_type']>10:
        #    config.params['recogn_type']=10
        # 设置当前识别类型
        self.recogn_type.setCurrentIndex(config.params['recogn_type'])

        # 设置需要显示的模型
        self.model_name.clear()
        if config.params['recogn_type']==recognition.Deepgram:
            self.model_name.addItems(config.DEEPGRAM_MODEL)
            curr=config.DEEPGRAM_MODEL
        elif config.params['recogn_type']==recognition.FUNASR_CN:
            self.model_name.addItems(config.FUNASR_MODEL)
            curr=config.FUNASR_MODEL
        else:
            self.model_name.addItems(config.WHISPER_MODEL_LIST)
            curr=config.WHISPER_MODEL_LIST
        if config.params['model_name'] in curr:
            self.model_name.setCurrentText(config.params['model_name'])

        if config.params['recogn_type'] not in [recognition.FASTER_WHISPER,recognition.Faster_Whisper_XXL,recognition.OPENAI_WHISPER,recognition.FUNASR_CN,recognition.Deepgram]:
            self.model_name.setDisabled(True)
        else:
            self.model_name.setDisabled(False)

        self.moshis = {
            "biaozhun": self.action_biaozhun,
            "tiqu": self.action_tiquzimu
        }



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


    # 设置各种默认值和设置文字 提示等
    def _set_cache_set(self):
        if platform.system() == 'Darwin':
            self.enable_cuda.setChecked(False)
            self.enable_cuda.hide()
        self.source_mp4.setAcceptDrops(True)

        self.stop_djs.setStyleSheet("""background-color:#148CD2;color:#ffffff""")
        self.proxy.setText(config.proxy)
        self.continue_compos.setToolTip(config.transobj['Click to start the next step immediately'])
        self.split_type.addItems([config.transobj['whisper_type_all'], config.transobj['whisper_type_avg']])

        self.subtitle_type.addItems(
            [
                config.transobj['nosubtitle'],
                config.transobj['embedsubtitle'],
                config.transobj['softsubtitle'],
                config.transobj['embedsubtitle2'],
                config.transobj['softsubtitle2']
            ])
        self.subtitle_type.setCurrentIndex(config.params['subtitle_type'])

        if config.params['recogn_type'] > 1:
            self.model_name_help.setVisible(False)
        else:
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

        try:
            self.voice_rate.setValue(int(config.params['voice_rate'].replace('%', '')))
        except Exception:
            self.voice_rate.setValue(0)
        try:
            self.pitch_rate.setValue(int(config.params['pitch'].replace('Hz', '')))
            self.volume_rate.setValue(int(config.params['volume']))
        except Exception:
            self.pitch_rate.setValue(0)
            self.volume_rate.setValue(0)
        self.addbackbtn.clicked.connect(self.win_action.get_background)

        self.split_type.setDisabled(True if config.params['recogn_type'] > 0 else False)
        self.voice_autorate.setChecked(bool(config.params['voice_autorate']))
        self.video_autorate.setChecked(bool(config.params['video_autorate']))
        self.append_video.setChecked(bool(config.params['append_video']))
        self.clear_cache.setChecked(bool(config.params.get('clear_cache')))
        self.enable_cuda.setChecked(True if config.params['cuda'] else False)
        self.only_video.setChecked(True if config.params['only_video'] else False)
        self.is_separate.setChecked(True if config.params['is_separate'] else False)
        self.rephrase.setChecked(config.settings.get('rephrase'))
        self.remove_noise.setChecked(config.params.get('remove_noise'))
        self.copysrt_rawvideo.setChecked(config.params.get('copysrt_rawvideo',False))

        self.bgmvolume.setText(str(config.settings.get('backaudio_volume',0.8)))
        self.is_loop_bgm.setChecked(bool(config.settings.get('loop_backaudio',True)))

        self.enable_cuda.toggled.connect(self.win_action.check_cuda)
        self.tts_type.currentIndexChanged.connect(self.win_action.tts_type_change)
        self.translate_type.currentIndexChanged.connect(self.win_action.set_translate_type)
        self.voice_role.currentTextChanged.connect(self.win_action.show_listen_btn)
        self.target_language.currentTextChanged.connect(self.win_action.set_voice_role)
        self.source_language.currentTextChanged.connect(self.win_action.source_language_change)


        self.proxy.textChanged.connect(self.win_action.change_proxy)
        self.import_sub.clicked.connect(self.win_action.import_sub_fun)

        self.startbtn.clicked.connect(self.win_action.check_start)
        self.btn_save_dir.clicked.connect(self.win_action.get_save_dir)
        self.btn_get_video.clicked.connect(self.win_action.get_mp4)
        self.stop_djs.clicked.connect(self.win_action.reset_timeid)
        self.continue_compos.clicked.connect(self.win_action.set_djs_timeout)
        self.listen_btn.clicked.connect(self.win_action.listen_voice_fun)
        self.split_type.currentIndexChanged.connect(self.win_action.check_split_type)
        self.model_name.currentTextChanged.connect(self.win_action.check_model_name)
        self.recogn_type.currentIndexChanged.connect(self.win_action.recogn_type_change)
        self.reglabel.clicked.connect(self.win_action.click_reglabel)
        self.label_9.clicked.connect(self.win_action.click_translate_type)
        self.tts_text.clicked.connect(self.win_action.click_tts_type)
        from videotrans.util import tools
        self.label.clicked.connect(lambda :tools.open_url(url='https://pyvideotrans.com/proxy'))
        self.hfaster_help.clicked.connect(lambda :tools.open_url(url='https://pyvideotrans.com/vad'))
        self.split_label.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/splitmode'))
        self.align_btn.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/align'))
        self.glossary.clicked.connect(lambda:tools.show_glossary_editor(self))


    def _start_subform(self):
        self.import_sub.setCursor(Qt.PointingHandCursor)

        self.model_name_help.setCursor(Qt.PointingHandCursor)
        self.stop_djs.setCursor(Qt.PointingHandCursor)
        self.continue_compos.setCursor(Qt.PointingHandCursor)
        self.startbtn.setCursor(Qt.PointingHandCursor)
        self.btn_get_video.setCursor(Qt.PointingHandCursor)
        self.btn_save_dir.setCursor(Qt.PointingHandCursor)
        self.listen_btn.setCursor(Qt.PointingHandCursor)
        self.statusLabel.setCursor(Qt.PointingHandCursor)
        self.rightbottom.setCursor(Qt.PointingHandCursor)
    
        from videotrans import winform

        self.action_biaozhun.triggered.connect(self.win_action.set_biaozhun)
        self.action_tiquzimu.triggered.connect(self.win_action.set_tiquzimu)

        self.actionbaidu_key.triggered.connect(winform.baidu.openwin)
        self.actionali_key.triggered.connect(winform.ali.openwin)

        self.actionazure_key.triggered.connect(winform.azure.openwin)
        self.actionazure_tts.triggered.connect(winform.azuretts.openwin)
        self.actiongemini_key.triggered.connect(winform.gemini.openwin)
        self.actiontencent_key.triggered.connect(winform.tencent.openwin)
        self.actionchatgpt_key.triggered.connect(winform.chatgpt.openwin)
        self.actionclaude_key.triggered.connect(winform.claude.openwin)
        self.actionlibretranslate_key.triggered.connect(winform.libre.openwin)

        self.actionai302_key.triggered.connect(winform.ai302.openwin)
        self.actionlocalllm_key.triggered.connect(winform.localllm.openwin)
        self.actionzijiehuoshan_key.triggered.connect(winform.zijiehuoshan.openwin)
        self.actiondeepL_key.triggered.connect(winform.deepL.openwin)
        self.actionElevenlabs_key.triggered.connect(winform.elevenlabs.openwin)
        self.actiondeepLX_address.triggered.connect(winform.deepLX.openwin)
        self.actionott_address.triggered.connect(winform.ott.openwin)
        self.actionclone_address.triggered.connect(winform.clone.openwin)
        self.actionkokoro_address.triggered.connect(winform.kokoro.openwin)
        self.actionchattts_address.triggered.connect(winform.chattts.openwin)
        self.actiontts_api.triggered.connect(winform.ttsapi.openwin)
        self.actionrecognapi.triggered.connect(winform.recognapi.openwin)
        self.actionsttapi.triggered.connect(winform.sttapi.openwin)
        self.actiondeepgram.triggered.connect(winform.deepgram.openwin)
        self.actiondoubao_api.triggered.connect(winform.doubao.openwin)
        self.actiontrans_api.triggered.connect(winform.transapi.openwin)
        self.actiontts_gptsovits.triggered.connect(winform.gptsovits.openwin)
        self.actiontts_cosyvoice.triggered.connect(winform.cosyvoice.openwin)
        self.actionopenaitts_key.triggered.connect(winform.openaitts.openwin)
        self.actionopenairecognapi_key.triggered.connect(winform.openairecognapi.openwin)
        self.actiontts_fishtts.triggered.connect(winform.fishtts.openwin)
        self.actiontts_f5tts.triggered.connect(winform.f5tts.openwin)
        self.actiontts_volcengine.triggered.connect(winform.volcenginetts.openwin)
        self.actionfreeai_key.triggered.connect(winform.freeai.openwin)


        self.actionyoutube.triggered.connect(winform.fn_youtube.openwin)
        self.actionwatermark.triggered.connect(winform.fn_watermark.openwin)
        self.actionsepar.triggered.connect(winform.fn_separate.openwin)
        self.actionsetini.triggered.connect(winform.setini.openwin)

        self.actionvideoandaudio.triggered.connect(winform.fn_videoandaudio.openwin)

        self.actionvideoandsrt.triggered.connect(winform.fn_videoandsrt.openwin)

        self.actionformatcover.triggered.connect(winform.fn_formatcover.openwin)

        self.actionsubtitlescover.triggered.connect(winform.fn_subtitlescover.openwin)
        self.action_hebingsrt.triggered.connect(winform.fn_hebingsrt.openwin)
        self.action_yinshipinfenli.triggered.connect(winform.fn_audiofromvideo.openwin)
        self.action_hun.triggered.connect(winform.fn_hunliu.openwin)
        self.action_yingyinhebing.triggered.connect(winform.fn_vas.openwin)

        self.action_subtitleediter.triggered.connect(winform.fn_editer.openwin)

        self.action_fanyi.triggered.connect(winform.fn_fanyisrt.openwin)

        self.action_yuyinshibie.triggered.connect(winform.fn_recogn.openwin)

        self.action_yuyinhecheng.triggered.connect(winform.fn_peiyin.openwin)

        self.action_ffmpeg.triggered.connect(lambda: self.win_action.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.win_action.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.win_action.open_url('discord'))
        self.action_models.triggered.connect(lambda: self.win_action.open_url('models'))
        #self.action_dll.triggered.connect(lambda: self.win_action.open_url('dll'))
        self.action_gtrans.triggered.connect(lambda: self.win_action.open_url('gtrans'))
        self.action_cuda.triggered.connect(lambda: self.win_action.open_url('cuda'))
        self.action_online.triggered.connect(lambda: self.win_action.open_url('online'))
        self.action_website.triggered.connect(lambda: self.win_action.open_url('website'))
        self.action_blog.triggered.connect(lambda: self.win_action.open_url('blog'))
        self.statusLabel.clicked.connect(lambda: self.win_action.open_url('help'))
        self.action_issue.triggered.connect(lambda: self.win_action.open_url('issue'))
        self.action_about.triggered.connect(self.win_action.about)
        self.action_clearcache.triggered.connect(self.win_action.clearcache)
        self.aisendsrt.toggled.connect(self.checkbox_state_changed)
        self.rightbottom.clicked.connect(self.win_action.about)
        Path(config.TEMP_DIR+'/stop_process.txt').unlink(missing_ok=True)

    def checkbox_state_changed(self, state):
        """复选框状态发生变化时触发的函数"""
        print(f'{state=},{Qt.CheckState.Checked=}')
        if state:
            print("Checkbox is checked")
            config.settings['aisendsrt']=True
        else:
            print("Checkbox is unchecked")
            config.settings['aisendsrt']=False


    def changeEvent(self, event):

        super().changeEvent(event)  # 确保父类的事件处理被调用
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():  # 只有在窗口被激活时才执行
                # print("Window activated")
                self.aisendsrt.setChecked(config.settings.get('aisendsrt'))

    def closeEvent(self, event):
        config.exit_soft = True
        config.current_status='stop'
        try:
            with open(config.TEMP_DIR+'/stop_process.txt','w',encoding='utf-8') as f:
                f.write('stop')
        except:
            pass
        sets=QSettings("pyvideotrans", "settings")
        sets.setValue("windowSize", self.size())
        self.hide()
        try:
            for w in config.child_forms.values():
                if w and hasattr(w, 'close'):
                    w.hide()
                    w.close()
            if config.INFO_WIN['win']:
                config.INFO_WIN['win'].close()
        except Exception:
            pass
        time.sleep(3)
        from videotrans.util import tools
        print('等待所有进程退出...')
        try:
            tools.kill_ffmpeg_processes()
        except Exception:
            pass
        time.sleep(3)
        os.chdir(config.ROOT_DIR)
        tools._unlink_tmp()
        event.accept()
