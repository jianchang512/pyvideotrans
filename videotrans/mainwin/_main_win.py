from PySide6.QtCore import Qt, QTimer, QSettings, QEvent, QThreadPool, QCoreApplication,  Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox, QMainWindow, QPushButton, QToolBar, QSizePolicy, QApplication
import asyncio, sys
import os
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import shutil
import time
import platform
import getpass
import subprocess

from videotrans.configure import config
from videotrans import VERSION
from videotrans.ui.en import Ui_MainWindow
from videotrans.translator import TRANSLASTE_NAME_LIST, LANGNAME_DICT
from videotrans.component.downmodels import MainWindow as downwin
from videotrans.task.simple_runnable_qt import run_in_threadpool

import huggingface_hub
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


# 1. 定义一个工厂函数，返回配置好的 Session
def _custom_session_factory():
    sess = requests.Session()
    # 配置重试策略
    retries = Retry(
        total=3,  # 总重试次数 (改为3)
        connect=2,  # 连接重试次数
        read=2,  # 读取重试次数
        backoff_factor=1,  # 重试间隔时间 (秒)，避免瞬间频繁请求
        status_forcelist=[500, 502, 503, 504]  # 遇到这些状态码才重试
    )

    # 将重试策略挂载到 http 和 https 协议上
    adapter = HTTPAdapter(max_retries=retries)
    sess.mount('http://', adapter)
    sess.mount('https://', adapter)
    return sess


# 2. 将这个工厂函数注册给 huggingface_hub
huggingface_hub.configure_http_backend(backend_factory=_custom_session_factory)


class MainWindow(QMainWindow, Ui_MainWindow):
    uito = Signal(str)

    def __init__(self, parent=None, width=1200, height=650):

        super(MainWindow, self).__init__(parent)

        self.resize(width, height)
        self.setupUi(self)

        self.worker_threads = []
        self.uuid_signal = None
        self.width = width
        self.height = height
        self.is_restarting = False
        # 实际行为实例
        self.win_action = None

        # 功能模式 dict{str,instance}
        self.moshi = None
        # 当前目标文件夹
        self.target_dir = None
        # 当前app模式
        self.app_mode = "biaozhun"
        # 当前所有可用角色列表
        self.current_rolelist = []

        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.languagename = list(LANGNAME_DICT.values())
        self.source_language.addItems(self.languagename)
        self.target_language.addItems(["-"] + self.languagename)
        self.translate_type.addItems(TRANSLASTE_NAME_LIST)

        self.rawtitle = f"{config.tr('softname')} {VERSION} {config.tr('Documents')} pyvideotrans.com"
        self.setWindowTitle(self.rawtitle)
        self.show()

        self.moshi = {
            "biaozhun": self.action_biaozhun,
            "tiqu": self.action_tiquzimu
        }
        self.subtitle_type.addItems(
            [
                config.tr('nosubtitle'),
                config.tr('embedsubtitle'),
                config.tr('softsubtitle'),
                config.tr('embedsubtitle2'),
                config.tr('softsubtitle2')
            ])
        self.uito.emit('load subtitles area...')
        QTimer.singleShot(200, self._set_Ui_Text)

    def _set_Ui_Text(self):
        # 字幕显示区域
        # set text start
        from videotrans.component.controlobj import TextGetdir
        self.subtitle_area = TextGetdir(self)
        self.subtitle_area.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.subtitle_area.setObjectName("subtitle_area")
        self.subtitle_area.setPlaceholderText(
            f"{config.tr('zimubianjitishi')}\n\n{config.tr('subtitle_tips')}\n\n{config.tr('meitiaozimugeshi')}")
        self.source_area_layout.insertWidget(self.source_area_layout.indexOf(self.subtitle_area_placeholder),
                                             self.subtitle_area)
        self.subtitle_area_placeholder.hide()
        self.subtitle_area_placeholder.deleteLater()

        # 底部状态条
        self.statusLabel = QPushButton(config.tr("Open Documents"))
        self.statusLabel.setStyleSheet("""color:#ffffbb""")
        self.statusBar.addWidget(self.statusLabel)

        self.rightbottom = QPushButton(config.tr('juanzhu'))

        self.container = QToolBar()
        self.container.addWidget(self.rightbottom)
        self.restart_btn = QPushButton(config.tr("Restart"))
        self.container.addWidget(self.restart_btn)
        self.statusBar.addPermanentWidget(self.container)

        QApplication.processEvents()
        self.uito.emit('Set controls style...')

        # 设置显示文字和样式
        self.rightbottom.setStyleSheet("""color:#ffffbb""")
        self.restart_btn.setStyleSheet("""color:#ffffbb""")
        self.restart_btn.setToolTip(
            config.tr("Click to end all tasks immediately and restart"))
        self.restart_btn.clicked.connect(self.restart_app)

        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.btn_get_video.setToolTip(
            config.tr("Multiple MP4 videos can be selected and automatically queued for processing"))
        self.btn_get_video.setText(config.tr("Select audio & video"))
        self.btn_save_dir.setToolTip(config.tr("Select where to save the processed output resources"))
        self.btn_save_dir.setText(config.tr("Save to.."))

        self.label_9.setText(config.tr("Translate channel"))
        self.label_9.setCursor(Qt.PointingHandCursor)
        self.translate_type.setToolTip(
            config.tr("Translation channels used in translating subtitle text"))
        self.label.setText(config.tr("Proxy"))
        self.label.setToolTip(
            config.tr("Click to view the tutorial for filling in the network proxy"))
        self.label.setCursor(Qt.PointingHandCursor)

        self.proxy.setPlaceholderText(config.tr("proxy address"))
        self.listen_btn.setToolTip(config.tr("shuoming01"))
        self.listen_btn.setText(config.tr("Trial dubbing"))
        self.label_2.setText(config.tr("Speech language"))
        self.source_language.setToolTip(config.tr("The language used for the original video pronunciation"))
        self.label_3.setText(config.tr("Target lang"))
        self.target_language.setToolTip(config.tr("What language do you want to translate into"))
        self.tts_text.setText(config.tr("Dubbing channel"))
        self.tts_text.setCursor(Qt.PointingHandCursor)
        self.label_4.setText(config.tr("Dubbing role") + " ")
        self.voice_role.setToolTip(config.tr("No is not dubbing"))

        self.model_name.setToolTip(config.tr(
            "From base to large v3, the effect is getting better and better, but the speed is also getting slower and slower"))
        self.subtitle_type.setToolTip(config.tr("shuoming02"))

        self.label_6.setText(config.tr("Dubbing speed"))
        self.voice_rate.setToolTip(config.tr("Overall acceleration or deceleration of voice over playback"))
        self.voice_autorate.setText(config.tr("Dubbing acceler"))
        self.voice_autorate.setToolTip(config.tr("shuoming03"))
        self.video_autorate.setText(config.tr("Slow video"))
        self.video_autorate.setToolTip(config.tr("Video Auto Slow"))

        self.remove_silent_mid.setText(config.tr("Del inline mute?"))
        self.remove_silent_mid.setToolTip(
            config.tr("Selecting this option will delete the silent intervals between subtitles"))

        self.align_sub_audio.setText(config.tr("Align subtitles and audio"))
        self.align_sub_audio.setToolTip(config.tr("If selected, it will force the subtitles and audio to align."))

        self.enable_cuda.setText(config.tr("Enable CUDA?"))
        self.is_separate.setText(config.tr("Retain original background sound"))
        self.is_separate.setToolTip(
            config.tr(
                "If selected, separate human voice and background sound, and finally output video will embed background sound"))
        self.startbtn.setText(config.tr("Start"))
        self.addbackbtn.setText(config.tr("Add background audio"))
        self.addbackbtn.setToolTip(
            config.tr("Add background audio for output video"))
        self.back_audio.setPlaceholderText(config.tr("back_audio_place"))
        self.back_audio.setToolTip(config.tr("back_audio_place"))

        self.import_sub.setText(config.tr("Import original language SRT"))
        self.uito.emit('Set menu...')
        QApplication.processEvents()
        # 菜单
        self.menu_Key.setTitle(config.tr("&Setting"))
        self.menu_TTS.setTitle(config.tr("&TTSsetting"))
        self.menu_RECOGN.setTitle(config.tr("&RECOGNsetting"))
        self.menu.setTitle(config.tr("&Tools"))
        self.menu_H.setTitle(config.tr("&Help"))
        self.toolBar.setWindowTitle("toolBar")
        self.actionbaidu_key.setText(config.tr("Baidu Key"))
        self.actionali_key.setText(config.tr("Alibaba Translation"))
        self.actionchatgpt_key.setText(
            config.tr("OpenAI API & Compatible AI"))
        self.actionzhipuai_key.setText(config.tr("Zhipu AI"))
        self.actionsiliconflow_key.setText(config.tr("SiliconFlow"))
        self.actiondeepseek_key.setText('DeepSeek')
        self.actionqwenmt_key.setText(config.tr('Ali Qwen3-ASR'))
        self.actionopenrouter_key.setText('OpenRouter.ai')
        self.actionlibretranslate_key.setText("LibreTranslate API")
        self.actionopenaitts_key.setText("OpenAI TTS")
        self.actionqwentts_key.setText("Qwen3 TTS")
        self.actionopenairecognapi_key.setText(
            config.tr("OpenAI Speech to Text API"))
        self.actionparakeet_key.setText('Nvidia parakeet-tdt')
        self.actionai302_key.setText(config.tr("302.AI API KEY"))
        self.actionlocalllm_key.setText(config.tr("Local LLM API"))
        self.actionzijiehuoshan_key.setText(config.tr("ByteDance Ark"))
        self.actiondeepL_key.setText("DeepL Key")

        self.action_ffmpeg.setText("FFmpeg")
        self.action_ffmpeg.setToolTip(config.tr("Go FFmpeg website"))
        self.action_git.setText("Github Repository")
        self.action_issue.setText(config.tr("Post issue"))
        self.actiondeepLX_address.setText("DeepLX Api")
        self.actionott_address.setText(config.tr("OTT Api"))
        self.actionclone_address.setText(config.tr("Clone-Voice TTS"))
        self.actionkokoro_address.setText("Kokoro TTS")
        self.actionchattts_address.setText("ChatTTS")
        self.actiontts_api.setText(config.tr("TTS API"))
        self.actionminimaxi_api.setText("Minimaxi TTS API")
        self.actiontrans_api.setText(config.tr("Transate API"))
        self.actionrecognapi.setText(config.tr("Custom Speech Recognition API"))
        self.actionsttapi.setText(config.tr("STT Speech Recognition API"))
        self.actionwhisperx.setText('WhisperX-API')
        self.actiondeepgram.setText(
            config.tr("Deepgram Speech Recognition API"))
        self.actionxxl.setText('Faster_Whisper_XXL.exe')
        self.actioncpp.setText('Whisper.cpp')
        self.actiondoubao_api.setText(config.tr("VolcEngine subtitles"))
        self.actionzijierecognmodel_api.setText(config.tr("VolcEngine STT"))
        self.actiontts_gptsovits.setText("GPT-SoVITS TTS")
        self.actiontts_chatterbox.setText("ChatterBox TTS")
        self.actiontts_cosyvoice.setText("CosyVoice TTS")
        self.actiontts_fishtts.setText("Fish TTS")
        self.actiontts_f5tts.setText("F5-TTS/Index-TTS/VoxCPM/SparK-TTS/Dia-TTS")
        self.actiontts_volcengine.setText(config.tr("VolcEngine TTS"))
        self.actiontts_doubao2.setText(config.tr("DouBao2"))
        self.action_website.setText(config.tr("Documents"))
        self.action_discord.setText(config.tr("Solution to model download failure"))
        self.action_blog.setText(config.tr("Having problems? Ask"))
        self.action_gtrans.setText(
            config.tr("Download Hard Subtitle Extraction Software"))
        self.action_cuda.setText('CUDA & cuDNN')
        self.action_online.setText(config.tr("Disclaimer"))
        self.actiontencent_key.setText(config.tr("Tencent Key"))
        self.action_about.setText(config.tr("Donating developers"))

        self.action_biaozhun.setText(config.tr("Standard Function Mode"))
        self.action_biaozhun.setToolTip(
            config.tr("Batch audio or video translation with all configuration options customizable on demand"))
        self.action_yuyinshibie.setText(config.tr("Speech Recognition Text"))
        self.action_yuyinshibie.setToolTip(
            config.tr("Batch recognize speech in audio or video as srt subtitles"))

        self.action_yuyinhecheng.setText(config.tr("From  Text  Into  Speech"))
        self.action_yuyinhecheng.setToolTip(
            config.tr("Batch dubbing based on srt subtitle files"))

        self.action_tiquzimu.setText(config.tr("Extract Srt And Translate"))
        self.action_tiquzimu.setToolTip(
            config.tr("Batch recognize speech in video as srt subtitles"))

        self.action_yinshipinfenli.setText(config.tr("Separate Video to audio"))
        self.action_yinshipinfenli.setToolTip(config.tr("Separate audio and silent videos from videos"))

        self.action_yingyinhebing.setText(config.tr("Video Subtitles Merging"))
        self.action_yingyinhebing.setToolTip(config.tr("Merge audio, video, and subtitles into one file"))
        self.action_clipvideo.setText(config.tr("Edit video on subtitles"))
        self.action_clipvideo.setToolTip(config.tr("Edit video on subtitles"))
        self.action_realtime_stt.setText(config.tr("Real-time speech-to-text"))
        self.action_realtime_stt.setToolTip(config.tr("Real-time speech-to-text"))

        self.action_hun.setText(config.tr("Mixing 2 Audio Streams"))
        self.action_hun.setToolTip(config.tr("Mix two audio files into one audio file"))

        self.action_fanyi.setText(config.tr("Text  Or Srt  Translation"))
        self.action_fanyi.setToolTip(
            config.tr("Batch translation of multiple srt subtitle files"))

        self.action_hebingsrt.setText(config.tr("Combine Two Subtitles"))
        self.action_hebingsrt.setToolTip(
            config.tr("Combine 2 subtitle files into one to form bilingual subtitles"))

        self.action_clearcache.setText(config.tr("Clear Cache"))
        self.action_downmodels.setText(config.tr("Download Models"))
        self.action_set_proxy.setText(config.tr("Setting up a network proxy"))

        self.actionazure_key.setText(config.tr("AzureOpenAI Translation"))
        self.actionazure_tts.setText(config.tr("AzureAI TTS"))
        self.actiongemini_key.setText("Gemini AI")
        self.actionElevenlabs_key.setText("ElevenLabs.io")

        self.actionwatermark.setText(config.tr("Add watermark to video"))
        self.actionsepar.setText(config.tr("Vocal & instrument Separate"))
        self.actionsetini.setText(config.tr("Options"))

        self.actionvideoandaudio.setText(config.tr("Batch video/audio merger"))
        self.actionvideoandaudio.setToolTip(
            config.tr("Batch merge video and audio one-to-one"))

        self.actionvideoandsrt.setText(config.tr("Batch Video Srt merger"))
        self.actionvideoandsrt.setToolTip(
            config.tr("Batch merge video and srt subtitles one by one."))

        self.actionformatcover.setText(config.tr("Batch Audio/Video conver"))
        self.actionformatcover.setToolTip(
            config.tr("Batch convert audio and video formats"))

        self.actionsubtitlescover.setText(config.tr("Conversion Subtitle Format"))
        self.actionsubtitlescover.setToolTip(
            config.tr("Batch convert subtitle formats (srt/ass/vtt)"))

        self.actionsrtmultirole.setText(config.tr("Multi voice dubbing for SRT"))
        self.actionsrtmultirole.setToolTip(
            config.tr("Subtitle multi-role dubbing: assign a voice to each subtitle"))
        # set text end
        QApplication.processEvents()
        self.uito.emit('Set default params')
        QTimer.singleShot(200, self._set_default)

    def _set_default(self):
        config.params['translate_type'] = int(config.params.get('translate_type', 0))
        config.params['tts_type'] = int(config.params.get('tts_type', 0))
        config.params['recogn_type'] = int(config.params.get('recogn_type', 0))
        config.params['fix_punc'] = bool(config.params.get('fix_punc', False))

        from videotrans import tts
        self.tts_type.addItems(tts.TTS_NAME_LIST)
        self.translate_type.setCurrentIndex(config.params.get('translate_type', 0))
        self.tts_type.setCurrentIndex(config.params.get('tts_type'))
        self.voice_role.clear()

        if config.params.get('source_language', '') and config.params.get('source_language', '') in self.languagename:
            self.source_language.setCurrentText(config.params.get('source_language', ''))

        self.subtitle_type.setCurrentIndex(int(config.params.get('subtitle_type', 0)))
        self.voice_rate.setValue(int(config.params.get('voice_rate', '0').replace('%', '')))
        self.volume_rate.setValue(int(config.params.get('volume', '0').replace('%', '')))
        self.pitch_rate.setValue(int(config.params.get('pitch', '0').replace('Hz', '')))
        self.voice_autorate.setChecked(bool(config.params.get('voice_autorate', False)))
        self.video_autorate.setChecked(bool(config.params.get('video_autorate', False)))
        self.fix_punc.setChecked(bool(config.params.get('fix_punc', False)))
        self.recogn2pass.setChecked(bool(config.params.get('recogn2pass', False)))
        self.only_out_mp4.setChecked(bool(config.params.get('only_out_mp4', False)))
        if not config.params.get('voice_autorate', False) and not config.params.get('video_autorate', False):
            self.remove_silent_mid.setVisible(True)
            self.align_sub_audio.setVisible(True)
        self.remove_silent_mid.setChecked(config.params.get('remove_silent_mid', False))
        self.align_sub_audio.setChecked(config.params.get('align_sub_audio', False))
        self.clear_cache.setChecked(bool(config.params.get('clear_cache', False)))
        self.enable_cuda.setChecked(bool(config.params.get('cuda', False)))
        self.enable_diariz.setChecked(bool(config.params.get('enable_diariz', False)))
        self.nums_diariz.setCurrentIndex(int(config.params.get('nums_diariz', 0)))
        self.is_separate.setChecked(bool(config.params.get('is_separate', False)))

        self.rephrase.setCurrentIndex(int(config.params.get('rephrase', 0)))
        self.remove_noise.setChecked(bool(config.params.get('remove_noise')))
        self.copysrt_rawvideo.setChecked(bool(config.params.get('copysrt_rawvideo', False)))

        self.bgmvolume.setText(str(config.settings.get('backaudio_volume', 0.8)))
        self.is_loop_bgm.setChecked(bool(config.settings.get('loop_backaudio', True)))

        if platform.system() == 'Darwin':
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
        self.win_action.tts_type_change(config.params.get('tts_type', ''))

        if not config.proxy:
            config.proxy = tools.set_proxy() or ''
        self.proxy.setText(config.proxy)

        tts_type = int(config.params.get('tts_type', 0))
        if tts_type == tts.CLONE_VOICE_TTS:
            self.voice_role.addItems(config.params.get("clone_voicelist", ''))
            run_in_threadpool(tools.get_clone_role)
        elif tts_type == tts.CHATTTS:
            self.voice_role.addItems(['No'] + list(config.ChatTTS_voicelist))
        elif tts_type == tts.TTS_API:
            self.voice_role.addItems(config.params.get('ttsapi_voice_role', '').strip().split(','))
        elif tts_type == tts.CHATTERBOX_TTS:
            rolelist = tools.get_chatterbox_role()
            self.voice_role.addItems(rolelist if rolelist else ['chatterbox'])
        elif tts_type == tts.GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
        elif tts_type == tts.COSYVOICE_TTS:
            rolelist = tools.get_cosyvoice_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['clone'])
        elif tts_type in [tts.F5_TTS, tts.INDEX_TTS, tts.SPARK_TTS, tts.VOXCPM_TTS,
                          tts.DIA_TTS]:
            rolelist = tools.get_f5tts_role()
            self.voice_role.addItems(['clone'] + list(rolelist.keys()) if rolelist else ['clone'])
        elif tts_type == tts.FISHTTS:
            rolelist = tools.get_fishtts_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['No'])
        elif tts_type == tts.ELEVENLABS_TTS:
            rolelist = tools.get_elevenlabs_role()
            self.voice_role.addItems(['No'] + rolelist)
        elif tts_type == tts.OPENAI_TTS:
            rolelist = config.params.get('openaitts_role', '')
            self.voice_role.addItems(['No'] + rolelist.split(','))
        elif tts_type == tts.QWEN_TTS:
            rolelist = list(tools.get_qwen3tts_rolelist().keys())
            self.voice_role.addItems(rolelist)
        elif tts_type == tts.GLM_TTS:
            rolelist = list(tools.get_glmtts_rolelist().keys())
            self.voice_role.addItems(rolelist)
        elif tts_type == tts.GEMINI_TTS:
            rolelist = config.params.get('gemini_ttsrole', '')
            self.voice_role.addItems(['No'] + rolelist.split(','))
        elif self.win_action.change_by_lang(tts_type):
            self.voice_role.clear()

        if config.params.get('target_language', '') and config.params.get('target_language', '') in self.languagename:
            self.target_language.setCurrentText(config.params.get('target_language', ''))
            self.win_action.set_voice_role(config.params.get('target_language', ''))
            default_role = config.params.get('voice_role', '')
            if default_role != 'No' and self.current_rolelist and default_role in self.current_rolelist:
                self.voice_role.setCurrentText(default_role)
                self.win_action.show_listen_btn(default_role)

        QApplication.processEvents()
        self.uito.emit('Bind signal...')
        run_in_threadpool(tools.check_hw_on_start)
        self._bind_signal()

    def _bind_signal(self):
        from videotrans.util import tools
        from videotrans.task.check_update import CheckUpdateWorker
        from videotrans.task.job import start_thread
        from videotrans.mainwin._signal import UUIDSignalThread
        from videotrans import recognition

        recogn_type = int(config.params.get('recogn_type', 0))
        self.model_name.clear()
        self.recogn_type.addItems(recognition.RECOGN_NAME_LIST)
        self.recogn_type.setCurrentIndex(recogn_type)

        if recogn_type == recognition.Deepgram:
            self.model_name.addItems(config.DEEPGRAM_MODEL)
            curr = config.DEEPGRAM_MODEL
        elif recogn_type == recognition.Whisper_CPP:
            curr = config.Whisper_CPP_MODEL_LIST
            self.model_name.addItems(config.Whisper_CPP_MODEL_LIST)
        elif recogn_type == recognition.FUNASR_CN:
            self.model_name.addItems(config.FUNASR_MODEL)
            curr = config.FUNASR_MODEL
        elif recogn_type == recognition.HUGGINGFACE_ASR:
            curr = list(recognition.HUGGINGFACE_ASR_MODELS.keys())
            self.model_name.addItems(curr)
        else:
            self.model_name.addItems(config.WHISPER_MODEL_LIST)
            curr = config.WHISPER_MODEL_LIST
        if config.params.get('model_name', '') in curr:
            self.model_name.setCurrentText(config.params.get('model_name', ''))
        if recogn_type not in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL, recognition.Whisper_CPP,
                               recognition.OPENAI_WHISPER, recognition.FUNASR_CN, recognition.Deepgram,
                               recognition.WHISPERX_API, recognition.HUGGINGFACE_ASR]:
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
        self.actiondoubao_api.triggered.connect(lambda: self._open_winform('doubao'))
        self.actionzijierecognmodel_api.triggered.connect(lambda: self._open_winform('zijierecognmodel'))
        self.actiontrans_api.triggered.connect(lambda: self._open_winform('transapi'))
        self.actiontts_gptsovits.triggered.connect(lambda: self._open_winform('gptsovits'))
        self.actiontts_chatterbox.triggered.connect(lambda: self._open_winform('chatterbox'))
        self.actiontts_cosyvoice.triggered.connect(lambda: self._open_winform('cosyvoice'))
        self.actionopenaitts_key.triggered.connect(lambda: self._open_winform('openaitts'))
        self.actionqwentts_key.triggered.connect(lambda: self._open_winform('qwentts'))
        self.actionopenairecognapi_key.triggered.connect(lambda: self._open_winform('openairecognapi'))
        self.actiontts_fishtts.triggered.connect(lambda: self._open_winform('fishtts'))
        self.actiontts_f5tts.triggered.connect(lambda: self._open_winform('f5tts'))
        self.actiontts_volcengine.triggered.connect(lambda: self._open_winform('volcenginetts'))
        self.actiontts_doubao2.triggered.connect(lambda: self._open_winform('doubao2'))
        self.actionzhipuai_key.triggered.connect(lambda: self._open_winform('zhipuai'))
        self.actiondeepseek_key.triggered.connect(lambda: self._open_winform('deepseek'))
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
        self.action_downmodels.triggered.connect(lambda: self._open_winform('downmodels'))
        self.action_set_proxy.triggered.connect(self.win_action.proxy_alert)
        self.aisendsrt.toggled.connect(self.checkbox_state_changed)
        self.rightbottom.clicked.connect(self.win_action.about)
        self.statusLabel.clicked.connect(lambda: self.win_action.open_url('help'))

        self.check_update = CheckUpdateWorker(parent=self)
        self.uuid_signal = UUIDSignalThread(parent=self)
        self.uuid_signal.uito.connect(self.win_action.update_data)
        self.uuid_signal.setObjectName("UUIDSignalThread")
        self.check_update.setObjectName("CheckUpdateThread")

        self.check_update.start()
        self.uuid_signal.start()
        self.worker_threads = start_thread()
        if not config.IS_FROZEN and not shutil.which("rubberband"):
            print(
                f'For Windows systems, please download the file, extract it, and place it in the ffmpeg folder in the current directory. Use a better audio acceleration algorithm\nhttps://breakfastquay.com/files/releases/rubberband-4.0.0-gpl-executable-windows.zip')
            print(
                f'MacOS: `brew install rubberband`  and  `uv add pyrubberband` Use a better audio acceleration algorithm')
            print(
                f'Ubuntu: `sudo apt install rubberband-cli libsndfile1-dev` and `uv add pyrubberband`  Use a better audio acceleration algorithm')

        QApplication.processEvents()
        self.uito.emit('preload model window')
        config.child_forms['downmodels'] = downwin()
        self.uito.emit('end')
        if config.settings.get('show_more_settings'):
            self.win_action.toggle_adv()

    # 打开缓慢
    def _open_winform(self, name, extra_name=None):

        if name == 'set_ass':
            from videotrans.component.set_ass import ASSStyleDialog
            dialog = ASSStyleDialog()
            dialog.exec()
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

        winobj = config.child_forms.get(name)
        if winobj:
            if hasattr(winobj, 'update_ui'):
                winobj.update_ui()

            winobj.show()
            winobj.activateWindow()
            if name == 'downmodels' and extra_name:
                winobj.auto_start(extra_name)
            return

        if name == 'downmodels':
            window = downwin()
            config.child_forms[name] = window
            window.show()
            if extra_name:
                window.auto_start(extra_name)
            return
        if name == 'clipvideo':
            from videotrans.component.clip_video import ClipVideoWindow
            window = ClipVideoWindow()
            config.child_forms[name] = window
            window.show()
            return
        if name == 'realtime_stt':
            from videotrans.component.realtime_stt import RealTimeWindow
            window = RealTimeWindow()
            config.child_forms[name] = window
            window.show()
            return

        from videotrans import winform
        QTimer.singleShot(0, winform.get_win(name).openwin)

    def restart_app(self):
        # 创建确认对话框

        reply = QMessageBox.question(
            self,
            config.tr("Restart"),
            config.tr("Are you sure you want to restart the application?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.is_restarting = True
            self.close()  # 触发 closeEvent，进行清理，然后在 closeEvent 中重启

    def checkbox_state_changed(self, state):
        """复选框状态发生变化时触发的函数"""
        if state:
            config.settings['aisendsrt'] = True
        else:
            config.settings['aisendsrt'] = False
        config.settings = config.parse_init(config.settings)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.aisendsrt.setChecked(config.settings.get('aisendsrt'))

    def kill_ffmpeg_processes(self):
        """ffmpeg进程终止函数"""

        system_platform = platform.system()
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
                if result.returncode == 0:
                    print("Successfully killed ffmpeg processes using taskkill")
                else:
                    print(f"taskkill returned: {result.returncode}, output: {result.stdout}")
            except Exception as e:
                print(f"Error using taskkill: {e}")

            return

        try:
            result = subprocess.run(
                ['pkill', '-9', '-u', current_user, 'ffmpeg'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("Successfully killed ffmpeg processes using pkill")
            else:
                print(f"pkill returned: {result.returncode}")
        except Exception as e:
            print(f"Error using pkill: {e}")

    def closeEvent(self, event):
        config.exit_soft = True
        config.current_status = 'stop'
        self.hide()
        os.chdir(config.ROOT_DIR)
        self.cleanup_and_accept()

        # 暂停等待可能的 faster-whisper 独立进程退出
        time.sleep(4)
        try:
            shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
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
            for w in config.child_forms.values():
                if w and hasattr(w, 'hide'):
                    w.hide()
            if config.INFO_WIN['win']:
                config.INFO_WIN['win'].hide()
        except Exception as e:
            print(f'子窗口隐藏中出错 {e}')

        if hasattr(self, 'check_update') and self.check_update and self.check_update.isRunning():
            print('等待 check_update 线程退出')
            self.check_update.quit()
            self.check_update.wait(1000)

        if hasattr(self, 'uuid_signal') and self.uuid_signal and self.uuid_signal.isRunning():
            print('等待 uuid_signal 线程退出')
            self.uuid_signal.quit()
            self.uuid_signal.wait(3000)

        # 遍历所有工作线程，等待结束
        for thread in self.worker_threads:
            if thread and thread.isRunning():
                print(f"正在等待线程 {thread.name} 结束...")
                thread.quit()
                thread.wait(5000)

        try:
            for w in config.child_forms.values():
                if w and hasattr(w, 'close'):
                    w.close()
            if config.INFO_WIN['win']:
                config.INFO_WIN['win'].close()
        except Exception as e:
            print(f'子窗口关闭中出错')
        QThreadPool.globalInstance().waitForDone(5000)
        # 最后再kill ffmpeg，避免占用
        self.kill_ffmpeg_processes()
