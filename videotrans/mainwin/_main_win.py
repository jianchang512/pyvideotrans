from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSettings, QEvent, QThreadPool, QCoreApplication, Signal
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMessageBox, QMainWindow, QPushButton, QToolBar, QSizePolicy, QApplication
import asyncio, sys
import os

from videotrans.util import contants, tools

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# 将这个工厂函数注册给 huggingface_hub
import shutil
import time
import platform
import getpass
import subprocess

from videotrans.util.req_fac import custom_session_factory
import huggingface_hub

huggingface_hub.configure_http_backend(backend_factory=custom_session_factory)

from videotrans.configure import config

config.init_run()
from videotrans.configure.config import tr, params, settings, app_cfg, logger, ROOT_DIR, IS_FROZEN, TEMP_DIR, TEMP_ROOT

from videotrans import VERSION
from videotrans.task.job import start_thread
from videotrans.util.checkgpu import AiLoaderThread
from videotrans.ui.en import Ui_MainWindow
from videotrans.translator import TRANSLASTE_NAME_LIST, LANGNAME_DICT
from videotrans.component.downmodels import DownmodelsWindow
from videotrans.task.simple_runnable_qt import run_in_threadpool
from videotrans import winform

system_platform = platform.system()

class MainWindow(QMainWindow, Ui_MainWindow):
    uito = Signal(str)

    def __init__(self, parent=None, width=1200, height=650):
        super(MainWindow, self).__init__(parent)
        QApplication.processEvents()
        self.uito.emit('loading GUI...')
        self.resize(width, height)
        self.setupUi(self)
        QApplication.processEvents()
        self.uito.emit('checking GPU...')

        s = AiLoaderThread(self)
        s.gpu_io.connect(self._start_workers)
        s.start()

        self.worker_threads = []
        self.width = width
        self.height = height
        self.is_restarting = False
        # 实际行为实例
        self.win_action = None

        self.moshi = None
        # 当前目标文件夹
        self.target_dir = None
        # 当前app模式
        self.app_mode = "biaozhun"
        # 当前所有可用角色列表
        self.current_rolelist = []

        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.languagename = list(LANGNAME_DICT.values())
        self.source_language.addItems(self.languagename)
        self.target_language.addItems(["-"] + self.languagename)
        self.translate_type.addItems(TRANSLASTE_NAME_LIST)

        self.rawtitle = f"{tr('softname')} {VERSION} {tr('Documents')} pyvideotrans.com"
        self.setWindowTitle(self.rawtitle)
        self.show()

        self.moshi = {
            "biaozhun": self.action_biaozhun,
            "tiqu": self.action_tiquzimu
        }
        self.subtitle_type.addItems(
            [
                tr('nosubtitle'),
                tr('embedsubtitle'),
                tr('softsubtitle'),
                tr('embedsubtitle2'),
                tr('softsubtitle2')
            ])

        QTimer.singleShot(200, self._set_default)

    def _set_default(self):

        params['translate_type'] = int(params.get('translate_type', 0))
        params['tts_type'] = int(params.get('tts_type', 0))
        params['recogn_type'] = int(params.get('recogn_type', 0))
        params['fix_punc'] = bool(params.get('fix_punc', False))

        from videotrans import tts
        self.tts_type.addItems(tts.TTS_NAME_LIST)
        self.translate_type.setCurrentIndex(params.get('translate_type', 0))
        self.tts_type.setCurrentIndex(params.get('tts_type'))
        self.voice_role.clear()
        if params['output_dir'].strip():
            Path(params['output_dir']).mkdir(parents=True,exist_ok=True)
            self.output_dir.setText(tr('Translation results saved to:')+params['output_dir'])
            self.target_dir=params['output_dir']

        if params.get('source_language', '') and params.get('source_language', '') in self.languagename:
            self.source_language.setCurrentText(params.get('source_language', ''))

        # 字幕双语类型
        _subtitle_type = int(params.get('subtitle_type', 0))
        self.subtitle_type.setCurrentIndex(_subtitle_type)
        _output_srt = int(params.get('output_srt', 0))
        if _subtitle_type > 2:
            self.output_srt.setVisible(True)
            self.output_srt.setCurrentIndex(_output_srt if _output_srt > 0 else 2)

        self.select_file_type.setChecked(bool(params.get('select_file_type', False)))
        self.voice_rate.setValue(int(params.get('voice_rate', '0').replace('%', '')))
        self.volume_rate.setValue(int(params.get('volume', '0').replace('%', '')))
        self.pitch_rate.setValue(int(params.get('pitch', '0').replace('Hz', '')))
        self.voice_autorate.setChecked(bool(params.get('voice_autorate', False)))
        self.video_autorate.setChecked(bool(params.get('video_autorate', False)))
        self.fix_punc.setChecked(bool(params.get('fix_punc', False)))
        self.recogn2pass.setChecked(bool(params.get('recogn2pass', False)))
        self.only_out_mp4.setChecked(bool(params.get('only_out_mp4', False)))
        if not params.get('voice_autorate', False) and not params.get('video_autorate', False):
            self.remove_silent_mid.setVisible(True)
            self.align_sub_audio.setVisible(True)
        self.remove_silent_mid.setChecked(params.get('remove_silent_mid', False))
        self.align_sub_audio.setChecked(params.get('align_sub_audio', False))
        self.clear_cache.setChecked(bool(params.get('clear_cache', False)))
        self.enable_cuda.setChecked(bool(params.get('is_cuda', False)))
        self.enable_diariz.setChecked(bool(params.get('enable_diariz', False)))
        self.nums_diariz.setCurrentIndex(int(params.get('nums_diariz', 0)))
        self.is_separate.setChecked(bool(params.get('is_separate', False)))
        self.embed_bgm.setChecked(bool(params.get('embed_bgm', True)))

        self.rephrase.setCurrentIndex(int(params.get('rephrase', 0)))

        self.remove_noise.setChecked(bool(params.get('remove_noise')))
        self.copysrt_rawvideo.setChecked(bool(params.get('copysrt_rawvideo', False)))

        self.bgmvolume.setText(str(settings.get('backaudio_volume', 0.8)))
        self.is_loop_bgm.setCurrentIndex(int(settings.get('loop_backaudio', 0)))

        if system_platform == 'Darwin':
            self.enable_cuda.setChecked(False)
            self.enable_cuda.hide()

        QApplication.processEvents()
        self.uito.emit('set cursor...')

        self.import_sub.setCursor(Qt.PointingHandCursor)
        self.model_name_help.setCursor(Qt.PointingHandCursor)
        self.startbtn.setCursor(Qt.PointingHandCursor)
        self.btn_get_video.setCursor(Qt.PointingHandCursor)
        self.btn_save_dir.setCursor(Qt.PointingHandCursor)
        self.listen_btn.setCursor(Qt.PointingHandCursor)
        self.statusLabel.setCursor(Qt.PointingHandCursor)
        self.rightbottom.setCursor(Qt.PointingHandCursor)
        self.restart_btn.setCursor(Qt.PointingHandCursor)

        QApplication.processEvents()
        self.uito.emit('import action')

        from videotrans.mainwin._actions import WinAction
        from videotrans.util import tools
        self.win_action = WinAction(self)
        self.win_action.tts_type_change(params.get('tts_type', ''))

        if not app_cfg.proxy:
            app_cfg.proxy = tools.set_proxy() or ''
        self.proxy.setText(app_cfg.proxy)

        tts_type = int(params.get('tts_type', 0))
        self.voice_role.clear()
        if tts_type == tts.CLONE_VOICE_TTS:
            self.voice_role.addItems(params.get("clone_voicelist", ''))
            run_in_threadpool(tools.get_clone_role)
        elif tts_type == tts.CHATTTS:
            self.voice_role.addItems(['No'] + list(settings.ChatTTS_voicelist))
        elif tts_type == tts.TTS_API:
            self.voice_role.addItems(params.get('ttsapi_voice_role', '').strip().split(','))
        elif tts_type == tts.GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
        elif tts_type in [tts.F5_TTS, tts.INDEX_TTS, tts.SPARK_TTS, tts.VOXCPM_TTS,
                          tts.DIA_TTS, tts.OMNIVOICE_TTS, tts.COSYVOICE_TTS, tts.CHATTERBOX_TTS, tts.FISHTTS,
                          tts.MOSS_TTS, tts.QWEN3LOCAL_TTS]:
            rolelist = tools.get_f5tts_role()
            self.voice_role.addItems(['clone'] + list(rolelist.keys()) if rolelist else ['clone'])
        elif tts_type == tts.ELEVENLABS_TTS:
            rolelist = tools.get_elevenlabs_role()
            self.voice_role.addItems(['No'] + rolelist)
        elif tts_type == tts.CAMB_TTS:
            rolelist = tools.get_camb_role()
            self.voice_role.addItems(rolelist)
        elif tts_type == tts.OPENAI_TTS:
            rolelist = params.get('openaitts_role', '')
            self.voice_role.addItems(['No'] + rolelist.split(','))
        elif tts_type == tts.XAI_TTS:
            self.voice_role.addItems(['No'] + contants.XAITTS_ROLES.split(','))
        elif tts_type == tts.XIAOMI_TTS:
            self.voice_role.addItems(['No'] + contants.MITTS_ROLES.split(','))
        elif tts_type == tts.QWEN_TTS:
            rolelist = list(tools.get_qwen3tts_rolelist().keys())
            self.voice_role.addItems(rolelist)
        elif tts_type == tts.GLM_TTS:
            rolelist = list(tools.get_glmtts_rolelist().keys())
            self.voice_role.addItems(rolelist)
        elif tts_type == tts.GEMINI_TTS:
            rolelist = params.get('gemini_ttsrole', '')
            self.voice_role.addItems(['No'] + rolelist.split(','))
        elif self.win_action.change_by_lang(tts_type):
            self.voice_role.clear()

        if params.get('target_language', '') and params.get('target_language', '') in self.languagename:
            self.target_language.setCurrentText(params.get('target_language', ''))
            self.win_action.set_voice_role(params.get('target_language', ''))
            default_role = params.get('voice_role', '')
            if default_role != 'No' and self.current_rolelist and default_role in self.current_rolelist:
                self.voice_role.setCurrentText(default_role)
                self.win_action.show_listen_btn(default_role)

        QApplication.processEvents()
        self.uito.emit('Bind signal...')
        run_in_threadpool(tools.check_hw_on_start)
        self._bind_signal()

    def _bind_signal(self):
        from videotrans.util import tools
        from videotrans.configure.signal_hub import SignalHub
        from videotrans import recognition
        self.restart_btn.clicked.connect(self.restart_app)

        recogn_type = int(params.get('recogn_type', 0))
        self.model_name.clear()
        self.recogn_type.addItems(recognition.RECOGN_NAME_LIST)
        self.recogn_type.setCurrentIndex(recogn_type)

        if recogn_type == recognition.Deepgram:
            curr = contants.DEEPGRAM_MODEL
            self.model_name.addItems(curr)
        elif recogn_type == recognition.Whisper_CPP:
            curr = settings.Whisper_CPP_MODEL_LIST
            self.model_name.addItems(curr)
        elif recogn_type == recognition.WHISPER_NET:
            curr = settings.Whisper_NET_MODEL_LIST
            self.model_name.addItems(curr)
        elif recogn_type == recognition.QWENASR:
            curr = ['1.7B', '0.6B']
            self.model_name.addItems(curr)
        elif recogn_type == recognition.FUNASR_CN:
            curr = contants.FUNASR_MODEL
            self.model_name.addItems(curr)
        elif recogn_type == recognition.HUGGINGFACE_ASR:
            curr = list(recognition.HUGGINGFACE_ASR_MODELS.keys())
            self.model_name.addItems(curr)
        elif recogn_type == recognition.OPENAI_WHISPER:
            self.model_name.addItems(contants.Openai_Whisper_Models)
            curr = contants.Openai_Whisper_Models
        else:
            self.model_name.addItems(settings.WHISPER_MODEL_LIST)
            curr = settings.WHISPER_MODEL_LIST
        if params.get('model_name', '') in curr:
            self.model_name.setCurrentText(params.get('model_name', ''))
        if recogn_type not in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL, recognition.Whisper_CPP,
                               recognition.OPENAI_WHISPER, recognition.FUNASR_CN, recognition.Deepgram,
                               recognition.WHISPERX_API, recognition.HUGGINGFACE_ASR, recognition.QWENASR,
                               recognition.WHISPER_NET]:
            self.model_name.setDisabled(True)
        else:
            self.model_name.setDisabled(False)

        if recogn_type > 1:
            self.model_name_help.setVisible(False)
        else:
            self.model_name_help.clicked.connect(self.win_action.show_model_help)

        # 绑定行为
        self.addbackbtn.clicked.connect(self.win_action.get_background)
        self.voice_autorate.toggled.connect(self.win_action.check_voice_autorate)
        self.video_autorate.toggled.connect(self.win_action.check_video_autorate)
        self.enable_cuda.toggled.connect(self.win_action.check_cuda)
        self.tts_type.currentIndexChanged.connect(self.win_action.tts_type_change)
        self.translate_type.currentIndexChanged.connect(self.win_action.set_translate_type)
        self.subtitle_type.currentIndexChanged.connect(self.win_action.set_subtitle_type)
        self.voice_role.currentTextChanged.connect(self.win_action.show_listen_btn)
        self.target_language.currentTextChanged.connect(self.win_action.set_voice_role)

        self.proxy.textChanged.connect(self.win_action.change_proxy)
        self.import_sub.clicked.connect(self.win_action.import_sub_fun)

        self.startbtn.clicked.connect(self.win_action.check_start)
        self.retrybtn.clicked.connect(self.win_action.retry)
        self.btn_save_dir.clicked.connect(self.win_action.get_save_dir)
        self.set_adv_status.clicked.connect(self.win_action.toggle_adv)
        self.btn_get_video.clicked.connect(self.win_action.get_mp4)
        self.listen_btn.clicked.connect(self.win_action.listen_voice_fun)
        self.recogn_type.currentIndexChanged.connect(self.win_action.recogn_type_change)
        self.model_name.currentIndexChanged.connect(self.win_action.model_type_change)

        self.label.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/proxy'))

        self.glossary.clicked.connect(lambda: tools.show_glossary_editor(self))
        self.action_biaozhun.triggered.connect(self.win_action.set_biaozhun)
        self.action_tiquzimu.triggered.connect(self.win_action.set_tiquzimu)

        self.actionbaidu_key.triggered.connect(lambda: self._open_winform('baidu'))
        self.actionali_key.triggered.connect(lambda: self._open_winform('ali'))
        self.set_ass.clicked.connect(lambda: self._open_winform('set_ass'))
        self.actionparakeet_key.triggered.connect(lambda: self._open_winform('parakeet'))
        self.actionsrtmultirole.triggered.connect(lambda: self._open_winform('fn_peiyinrole'))
        self.actionazure_key.triggered.connect(lambda: self._open_winform('azure'))
        self.actionazure_tts.triggered.connect(lambda: self._open_winform('azuretts'))
        self.actiongemini_key.triggered.connect(lambda: self._open_winform('gemini'))
        self.actioncamb_key.triggered.connect(lambda: self._open_winform('cambtts'))
        self.actiontencent_key.triggered.connect(lambda: self._open_winform('tencent'))
        self.actionchatgpt_key.triggered.connect(lambda: self._open_winform('chatgpt'))
        self.actionlibretranslate_key.triggered.connect(lambda: self._open_winform('libre'))
        self.actionai302_key.triggered.connect(lambda: self._open_winform('ai302'))
        self.actionlocalllm_key.triggered.connect(lambda: self._open_winform('localllm'))
        self.actionzijiehuoshan_key.triggered.connect(lambda: self._open_winform('zijiehuoshan'))
        self.actiondeepL_key.triggered.connect(lambda: self._open_winform('deepL'))
        self.actionElevenlabs_key.triggered.connect(lambda: self._open_winform('elevenlabs'))
        self.actiondeepLX_address.triggered.connect(lambda: self._open_winform('deepLX'))
        self.actionott_address.triggered.connect(lambda: self._open_winform('ott'))
        self.actionclone_address.triggered.connect(lambda: self._open_winform('clone'))
        self.actionmosstts.triggered.connect(lambda: self._open_winform('mosstts'))
        self.actionkokoro_address.triggered.connect(lambda: self._open_winform('kokoro'))
        self.actionchattts_address.triggered.connect(lambda: self._open_winform('chattts'))
        self.actiontts_api.triggered.connect(lambda: self._open_winform('ttsapi'))
        self.actionminimaxi_api.triggered.connect(lambda: self._open_winform('minimaxi'))
        self.actionrecognapi.triggered.connect(lambda: self._open_winform('recognapi'))
        self.actionsttapi.triggered.connect(lambda: self._open_winform('sttapi'))
        self.actionwhisperx.triggered.connect(lambda: self._open_winform('whisperxapi'))
        self.actiondeepgram.triggered.connect(lambda: self._open_winform('deepgram'))
        self.actionxxl.triggered.connect(lambda: self._open_winform('xxl'))
        self.actioncpp.triggered.connect(lambda: self._open_winform('cpp'))
        self.actionzijierecognmodel_api.triggered.connect(lambda: self._open_winform('zijierecognmodel'))
        self.actiontrans_api.triggered.connect(lambda: self._open_winform('transapi'))
        self.actiontts_gptsovits.triggered.connect(lambda: self._open_winform('gptsovits'))
        self.actiontts_chatterbox.triggered.connect(lambda: self._open_winform('chatterbox'))
        self.actiontts_cosyvoice.triggered.connect(lambda: self._open_winform('cosyvoice'))
        self.actiontts_omnivoice.triggered.connect(lambda: self._open_winform('omnivoice'))
        self.actiontts_qwenttslocal.triggered.connect(lambda: self._open_winform('qwenttslocal'))
        self.actionopenaitts_key.triggered.connect(lambda: self._open_winform('openaitts'))
        self.actionxaitts_key.triggered.connect(lambda: self._open_winform('xaitts'))
        self.actionxiaomi_key.triggered.connect(lambda: self._open_winform('xiaomi'))
        self.actionqwentts_key.triggered.connect(lambda: self._open_winform('qwentts'))
        self.actionopenairecognapi_key.triggered.connect(lambda: self._open_winform('openairecognapi'))
        self.actiontts_fishtts.triggered.connect(lambda: self._open_winform('fishtts'))
        self.actiontts_f5tts.triggered.connect(lambda: self._open_winform('f5tts'))
        self.actiontts_refaudio.triggered.connect(lambda: self._open_winform('refaudio'))
        self.actiontts_doubao2.triggered.connect(lambda: self._open_winform('doubao2'))
        self.actionzhipuai_key.triggered.connect(lambda: self._open_winform('zhipuai'))
        self.actiondeepseek_key.triggered.connect(lambda: self._open_winform('deepseek'))
        self.actionminimax_key.triggered.connect(lambda: self._open_winform('minimax'))
        self.actionqwenmt_key.triggered.connect(lambda: self._open_winform('qwenmt'))
        self.actionopenrouter_key.triggered.connect(lambda: self._open_winform('openrouter'))
        self.actionsiliconflow_key.triggered.connect(lambda: self._open_winform('siliconflow'))
        self.actionwatermark.triggered.connect(lambda: self._open_winform('fn_watermark'))
        self.actionsepar.triggered.connect(lambda: self._open_winform('fn_separate'))
        self.actionsetini.triggered.connect(lambda: self._open_winform('setini'))
        self.actionvideoandaudio.triggered.connect(lambda: self._open_winform('fn_videoandaudio'))
        self.actionvideoandsrt.triggered.connect(lambda: self._open_winform('fn_videoandsrt'))
        self.actionformatcover.triggered.connect(lambda: self._open_winform('fn_formatcover'))
        self.actionsubtitlescover.triggered.connect(lambda: self._open_winform('fn_subtitlescover'))
        self.action_hebingsrt.triggered.connect(lambda: self._open_winform('fn_hebingsrt'))
        self.action_yinshipinfenli.triggered.connect(lambda: self._open_winform('fn_audiofromvideo'))
        self.action_hun.triggered.connect(lambda: self._open_winform('fn_hunliu'))
        self.action_yingyinhebing.triggered.connect(lambda: self._open_winform('fn_vas'))
        self.action_clipvideo.triggered.connect(lambda: self._open_winform('clipvideo'))
        self.action_textmatching.triggered.connect(lambda: self._open_winform('textmatching'))
        self.action_realtime_stt.triggered.connect(lambda: self._open_winform('realtime_stt'))
        self.action_fanyi.triggered.connect(lambda: self._open_winform('fn_fanyisrt'))
        self.action_yuyinshibie.triggered.connect(lambda: self._open_winform('fn_recogn'))

        self.action_yuyinhecheng.triggered.connect(lambda: self._open_winform('fn_peiyin'))
        self.action_ffmpeg.triggered.connect(lambda: self.win_action.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.win_action.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.win_action.open_url('hfmirrorcom'))

        self.action_gtrans.triggered.connect(lambda: self.win_action.open_url('gtrans'))
        self.action_cuda.triggered.connect(lambda: self.win_action.open_url('cuda'))
        self.action_online.triggered.connect(self.win_action.lawalert)
        self.action_website.triggered.connect(lambda: self.win_action.open_url('website'))
        self.action_blog.triggered.connect(lambda: self.win_action.open_url('bbs'))
        self.action_issue.triggered.connect(lambda: self.win_action.open_url('issue'))
        self.action_about.triggered.connect(self.win_action.about)
        self.action_clearcache.triggered.connect(self.win_action.clearcache)
        self.action_set_proxy.triggered.connect(self.win_action.proxy_alert)
        self.aisendsrt.toggled.connect(self.checkbox_state_changed)
        self.rightbottom.clicked.connect(self.win_action.about)
        self.statusLabel.clicked.connect(lambda: self.win_action.open_url('help'))

        SignalHub.instance().new_message.connect(self.win_action.update_data)

        if settings.get('show_more_settings'):
            self.win_action.toggle_adv()

        # 预先加载 配音/语音转录/字幕翻译窗口 等常用功能面板，
        self._open_winform('fn_peiyin')
        self._open_winform('fn_recogn')
        self._open_winform('fn_fanyisrt')
        QApplication.processEvents()
        self.uito.emit('end')

    def _start_workers(self, status):
        if status == 'end':
            self.worker_threads = start_thread()
        else:
            from videotrans.util import tools
            tools.show_error(status)

    # 打开缓慢
    def _open_winform(self, name, extra_name=None):

        if name == 'set_ass':
            from videotrans.component.set_ass import ASSStyleDialog
            dialog = ASSStyleDialog()
            dialog.exec()
            return
        if name == 'refaudio':
            tools.show_refaudio_win()
            return
        if name == 'xxl':
            from videotrans.component.set_xxl import SetFasterXXL
            dialog = SetFasterXXL()
            dialog.exec()
            return

        if name == 'cpp':
            from videotrans.component.set_cpp import SetWhisperCPP
            dialog = SetWhisperCPP()
            dialog.exec()
            return

        winobj = app_cfg.child_forms.get(name)
        if winobj:
            if hasattr(winobj, 'update_ui'):
                winobj.update_ui()

            winobj.show()
            winobj.activateWindow()
            if name == 'downmodels' and extra_name:
                winobj.auto_start(extra_name)
            return

        if name == 'downmodels':
            window = DownmodelsWindow()
            app_cfg.child_forms[name] = window
            window.show()
            if extra_name:
                window.auto_start(extra_name)
            return
        if name == 'clipvideo':
            from videotrans.component.clip_video import ClipVideoWindow
            window = ClipVideoWindow()
            app_cfg.child_forms[name] = window
            window.show()
            return
        if name == 'textmatching':
            from videotrans.component.textmatching import TextmatchingWindow
            window = TextmatchingWindow()
            app_cfg.child_forms[name] = window
            window.show()
            return
        if name == 'realtime_stt':
            from videotrans.component.realtime_stt import RealTimeWindow
            window = RealTimeWindow()
            app_cfg.child_forms[name] = window
            window.show()
            return

        return winform.get_win(name).openwin()

    def restart_app(self):
        # 创建确认对话框

        reply = QMessageBox.question(
            self,
            tr("Restart"),
            tr("Are you sure you want to restart the application?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.is_restarting = True
            self.close()  # 触发 closeEvent，进行清理，然后在 closeEvent 中重启

    def checkbox_state_changed(self, state):
        """复选框状态发生变化时触发的函数"""
        if state:
            settings['aisendsrt'] = True
        else:
            settings['aisendsrt'] = False
        settings.save()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.aisendsrt.setChecked(settings.get('aisendsrt'))

    def kill_ffmpeg_processes(self):
        """ffmpeg进程终止函数"""


        current_user = getpass.getuser()

        if system_platform == "Windows":
            # Windows平台 - 使用taskkill
            try:
                result = subprocess.run(
                    f'taskkill /F /FI "USERNAME eq {current_user}" /IM ffmpeg.exe',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.warning(f"taskkill returned: {result.returncode}, output: {result.stdout}")
            except Exception as e:
                logger.exception(f"Error using taskkill: {e}",exc_info=True)

            return

        try:
            result = subprocess.run(
                ['pkill', '-9', '-u', current_user, 'ffmpeg'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning(f"pkill returned: {result.returncode}",exc_info=True)
        except Exception as e:
            logger.exception(f"Error using pkill: {e}",exc_info=True)

    def closeEvent(self, event):
        app_cfg.exit_soft = True
        app_cfg.current_status = 'stop'
        self.hide()
        os.chdir(ROOT_DIR)
        self.cleanup_and_accept()

        # 暂停等待可能的 faster-whisper 独立进程退出
        time.sleep(4)
        try:
            shutil.rmtree(TEMP_ROOT, ignore_errors=True)
        except OSError:
            pass
        if not self.is_restarting:
            event.accept()
            return

        # 清理后启动新进程，然后立即退出旧进程
        import subprocess
        if getattr(sys, 'frozen', False):  # PyInstaller 打包模式
            subprocess.Popen([sys.executable] + sys.argv[1:])
        else:  # 源代码模式
            subprocess.Popen([sys.executable, sys.argv[0]] + sys.argv[1:])

        event.accept()
        os._exit(0)  # 立即退出进程，避免 Qt 清理错误

    def cleanup_and_accept(self):
        QCoreApplication.processEvents()
        sets = QSettings("pyvideotrans", "settings")
        sets.setValue("windowSize", self.size())
        try:
            for w in app_cfg.child_forms.values():
                if w and hasattr(w, 'hide'):
                    w.hide()
            if app_cfg.INFO_WIN['win']:
                app_cfg.INFO_WIN['win'].hide()
        except Exception as e:
            logger.exception(f'子窗口隐藏中出错 {e}',exc_info=True)


        # 遍历所有工作线程，等待结束
        for thread in self.worker_threads:
            if thread and thread.isRunning():
                thread.terminate()
                thread.wait(5000)

        try:
            for w in app_cfg.child_forms.values():
                if w and hasattr(w, 'close'):
                    w.close()
            if app_cfg.INFO_WIN['win']:
                app_cfg.INFO_WIN['win'].close()
        except Exception as e:
            logger.exception(f'子窗口关闭中出错',exc_info=True)
        QThreadPool.globalInstance().waitForDone(5000)
        # 最后再kill ffmpeg，避免占用
        self.kill_ffmpeg_processes()
