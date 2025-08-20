import os
import platform
import shutil
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSettings, QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QPushButton, QToolBar, QSizePolicy

from videotrans import VERSION, recognition, tts
from videotrans.configure import config
from videotrans.mainwin._actions import WinAction
from videotrans.ui.en import Ui_MainWindow
from videotrans.util import tools


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None, width=1200, height=650):

        super(MainWindow, self).__init__(parent)

        self.width = width
        self.height = height
        self.resize(width, height)
        # 实际行为实例
        self.win_action = None
        # 功能模式 dict{str,instance}
        self.moshis = None
        # 当前目标文件夹
        self.target_dir = None
        # 当前app模式
        self.app_mode = "biaozhun"
        # 当前所有可用角色列表
        self.current_rolelist = []
        self.languagename = config.langnamelist
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setupUi(self)

        self._replace_placeholders()
        self.initUI()

        self._retranslateUi_from_logic()
        self.show()
        QTimer.singleShot(50, self._set_cache_set)
        QTimer.singleShot(100, self._start_subform)
        QTimer.singleShot(400, self._bindsignal)
        QTimer.singleShot(800, self.is_writable)

    def _replace_placeholders(self):
        """
        用真正的自定义组件替换UI文件中的占位符
        """
        self.recogn_type.addItems(recognition.RECOGN_NAME_LIST)
        self.tts_type.addItems(tts.TTS_NAME_LIST)

        from videotrans.component.controlobj import TextGetdir
        self.subtitle_area = TextGetdir(self)
        self.subtitle_area.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.subtitle_area.setObjectName("subtitle_area")
        self.subtitle_area.setPlaceholderText(
            f"{config.transobj['zimubianjitishi']}\n\n{config.transobj['subtitle_tips']}\n\n{config.transobj['meitiaozimugeshi']}")
        # 替换占位符
        index = self.source_area_layout.indexOf(self.subtitle_area_placeholder)
        self.source_area_layout.insertWidget(index, self.subtitle_area)
        self.subtitle_area_placeholder.hide()
        self.subtitle_area_placeholder.deleteLater()

    def _retranslateUi_from_logic(self):
        """设置显示文字"""
        self.btn_get_video.setToolTip(
            config.uilanglist.get("Multiple MP4 videos can be selected and automatically queued for processing"))
        self.btn_get_video.setText('选择要处理的视频' if config.defaulelang == 'zh' else 'Select the video')
        self.btn_save_dir.setToolTip(config.uilanglist.get("Select where to save the processed output resources"))
        self.btn_save_dir.setText(config.uilanglist.get("Save to.."))

        self.label_9.setText(config.uilanglist.get("Translate channel") + "\u2193")
        self.label_9.setCursor(Qt.PointingHandCursor)
        self.translate_type.setToolTip(
            '翻译字幕文字时使用的翻译渠道' if config.defaulelang == 'zh' else 'Translation channels used in translating subtitle text')
        self.label.setText('网络代理\u2193' if config.defaulelang == 'zh' else 'Proxy')
        self.label.setToolTip(
            '点击查看网络代理填写教程' if config.defaulelang == 'zh' else 'Click to view the tutorial for filling in the network proxy')
        self.label.setCursor(Qt.PointingHandCursor)

        self.proxy.setPlaceholderText(config.uilanglist.get("proxy address"))
        self.listen_btn.setToolTip(config.uilanglist.get("shuoming01"))
        self.listen_btn.setText(config.uilanglist.get("Trial dubbing"))
        self.label_2.setText('发音语言 ' if config.defaulelang == 'zh' else "Speech language ")
        self.source_language.setToolTip(config.uilanglist.get("The language used for the original video pronunciation"))
        self.label_3.setText(config.uilanglist.get("Target lang"))
        self.target_language.setToolTip(config.uilanglist.get("What language do you want to translate into"))
        self.tts_text.setText("配音渠道\u2193" if config.defaulelang == 'zh' else "Dubbing channel\u2193")
        self.tts_text.setCursor(Qt.PointingHandCursor)
        self.label_4.setText(config.uilanglist.get("Dubbing role") + " ")
        self.voice_role.setToolTip(config.uilanglist.get("No is not dubbing"))

        self.model_name.setToolTip(config.uilanglist.get(
            "From base to large v3, the effect is getting better and better, but the speed is also getting slower and slower"))
        self.split_type.setToolTip(config.uilanglist.get(
            "Overall recognition is suitable for videos with or without background music and noticeable silence"))
        self.subtitle_type.setToolTip(config.uilanglist.get("shuoming02"))

        self.label_6.setText(config.uilanglist.get("Dubbing speed"))
        self.voice_rate.setToolTip(config.uilanglist.get("Overall acceleration or deceleration of voice over playback"))
        self.voice_autorate.setText('配音加速' if config.defaulelang == 'zh' else 'Dubbing acceler')
        self.voice_autorate.setToolTip(config.uilanglist.get("shuoming03"))
        self.video_autorate.setText('视频慢速' if config.defaulelang == 'zh' else 'Slow video')
        self.video_autorate.setToolTip('视频自动慢速处理' if config.defaulelang == 'zh' else 'Video Auto Slow')

        self.enable_cuda.setText(config.uilanglist.get("Enable CUDA?"))
        self.is_separate.setText('保留原始背景音' if config.defaulelang == 'zh' else 'Retain original background sound')
        self.is_separate.setToolTip(
            '若选中则分离人声和背景声，最终输出视频再将背景声嵌入' if config.defaulelang == 'zh' else 'If selected, separate human voice and background sound, \nand finally output video will embed background sound')
        self.startbtn.setText(config.uilanglist.get("Start"))
        self.addbackbtn.setText('添加额外背景音频' if config.defaulelang == 'zh' else 'Add background audio')
        self.addbackbtn.setToolTip(
            '为输出视频额外添加一个音频作为背景声音' if config.defaulelang == 'zh' else 'Add background audio for output video')
        self.back_audio.setPlaceholderText(config.uilanglist.get("back_audio_place"))
        self.back_audio.setToolTip(config.uilanglist.get("back_audio_place"))
        self.stop_djs.setText(config.uilanglist.get("Pause"))
        self.import_sub.setText(config.uilanglist.get("Import srt"))

        self.menu_Key.setTitle(config.uilanglist.get("&Setting"))
        self.menu_TTS.setTitle(config.uilanglist.get("&TTSsetting"))
        self.menu_RECOGN.setTitle(config.uilanglist.get("&RECOGNsetting"))
        self.menu.setTitle(config.uilanglist.get("&Tools"))
        self.menu_H.setTitle(config.uilanglist.get("&Help"))
        self.toolBar.setWindowTitle("toolBar")
        self.actionbaidu_key.setText("百度翻译" if config.defaulelang == 'zh' else "Baidu Key")
        self.actionali_key.setText("阿里机器翻译" if config.defaulelang == 'zh' else "Alibaba Translation")
        self.actionchatgpt_key.setText(
            "OpenAI API 及兼容AI" if config.defaulelang == 'zh' else "OpenAI API & Compatible AI")
        self.actionzhipuai_key.setText("智谱AI" if config.defaulelang == 'zh' else 'Zhipu AI')
        self.actionsiliconflow_key.setText('硅基流动' if config.defaulelang == 'zh' else "Siliconflow")
        self.actiondeepseek_key.setText('DeepSeek')
        self.actionopenrouter_key.setText('OpenRouter.ai')
        self.actionclaude_key.setText("Claude API")
        self.actionlibretranslate_key.setText("LibreTranslate API")
        self.actionopenaitts_key.setText("OpenAI TTS")
        self.actionqwentts_key.setText("Qwen TTS")
        self.actionopenairecognapi_key.setText(
            "OpenAI语音识别及兼容API" if config.defaulelang == 'zh' else 'OpenAI Speech to Text API')
        self.actionparakeet_key.setText('Nvidia parakeet-tdt')
        self.actionai302_key.setText("302.AI API Key" if config.defaulelang == 'zh' else "302.AI API KEY")
        self.actionlocalllm_key.setText("本地大模型(兼容OpenAI)" if config.defaulelang == 'zh' else "Local LLM API")
        self.actionzijiehuoshan_key.setText("字节火山大模型翻译" if config.defaulelang == 'zh' else 'ByteDance Ark')
        self.actiondeepL_key.setText("DeepL Key")

        self.action_ffmpeg.setText("FFmpeg")
        self.action_ffmpeg.setToolTip(config.uilanglist.get("Go FFmpeg website"))
        self.action_git.setText("Github Repository")
        self.action_issue.setText(config.uilanglist.get("Post issue"))
        self.actiondeepLX_address.setText("DeepLX Api")
        self.actionott_address.setText("OTT离线翻译Api" if config.defaulelang == 'zh' else "OTT Api")
        self.actionclone_address.setText("clone-voice" if config.defaulelang == 'zh' else "Clone-Voice TTS")
        self.actionkokoro_address.setText("Kokoro TTS")
        self.actionchattts_address.setText("ChatTTS")
        self.actiontts_api.setText("自定义TTS API" if config.defaulelang == 'zh' else "TTS API")
        self.actiontrans_api.setText("自定义翻译API" if config.defaulelang == 'zh' else "Transate API")
        self.actionrecognapi.setText("自定义语音识别API" if config.defaulelang == 'zh' else "Custom Speech Recognition API")
        self.actionsttapi.setText("STT语音识别API" if config.defaulelang == 'zh' else "STT Speech Recognition API")
        self.actiondeepgram.setText(
            "Deepgram.com语音识别" if config.defaulelang == 'zh' else "Deepgram Speech Recognition API")
        self.actiondoubao_api.setText("字节火山字幕生成" if config.defaulelang == 'zh' else "VolcEngine subtitles")
        self.actiontts_gptsovits.setText("GPT-SoVITS TTS")
        self.actiontts_chatterbox.setText("ChatterBox TTS")
        self.actiontts_cosyvoice.setText("CosyVoice TTS")
        self.actiontts_fishtts.setText("Fish TTS")
        self.actiontts_f5tts.setText("F5/index/SparK/Dia TTS")
        self.actiontts_volcengine.setText('字节火山语音合成' if config.defaulelang == 'zh' else 'VolcEngine TTS')
        self.action_website.setText(config.uilanglist.get("Documents"))
        self.action_discord.setText("Discord")
        self.action_blog.setText("bbs" if config.defaulelang == 'zh' else 'BBS')
        self.action_models.setText(config.uilanglist["Download Models"])
        self.action_gtrans.setText(
            '下载硬字幕提取软件' if config.defaulelang == 'zh' else 'Download Hard Subtitle Extraction Software')
        self.action_cuda.setText('CUDA & cuDNN')
        self.action_online.setText('免责声明' if config.defaulelang == 'zh' else 'Disclaimer')
        self.actiontencent_key.setText("腾讯翻译设置" if config.defaulelang == 'zh' else "Tencent Key")
        self.action_about.setText(config.uilanglist.get("Donating developers"))

        self.action_biaozhun.setText(config.uilanglist.get("Standard Function Mode"))
        self.action_biaozhun.setToolTip(
            '批量进行视频翻译，并可按照需求自定义所有配置选项' if config.defaulelang == 'zh' else 'Batch video translation with all configuration options customizable on demand')
        self.action_yuyinshibie.setText(config.uilanglist.get("Speech Recognition Text"))
        self.action_yuyinshibie.setToolTip(
            '批量将音频或视频中的语音识别为srt字幕' if config.defaulelang == 'zh' else 'Batch recognize speech in audio or video as srt subtitles')

        self.action_yuyinhecheng.setText(config.uilanglist.get("From  Text  Into  Speech"))
        self.action_yuyinhecheng.setToolTip(
            '根据srt字幕文件批量进行配音' if config.defaulelang == 'zh' else 'Batch dubbing based on srt subtitle files')

        self.action_tiquzimu.setText(config.uilanglist.get("Extract Srt And Translate"))
        self.action_tiquzimu.setToolTip(
            '批量将视频中的语音识别为字幕，并可选择是否同时翻译字幕' if config.defaulelang == 'zh' else 'Batch recognize speech in video as srt subtitles')

        self.action_yinshipinfenli.setText(config.uilanglist.get("Separate Video to audio"))
        self.action_yinshipinfenli.setToolTip(config.uilanglist.get("Separate audio and silent videos from videos"))

        self.action_yingyinhebing.setText(config.uilanglist.get("Video Subtitles Merging"))
        self.action_yingyinhebing.setToolTip(config.uilanglist.get("Merge audio, video, and subtitles into one file"))

        self.action_subtitleediter.setText('字幕编辑与翻译' if config.defaulelang == 'zh' else 'Subtitle Editing & Translate')
        self.action_subtitleediter.setToolTip(
            '导入字幕修改与翻译' if config.defaulelang == 'zh' else 'Importing subtitles and exporting them after modifying them or translation')

        self.action_hun.setText(config.uilanglist.get("Mixing 2 Audio Streams"))
        self.action_hun.setToolTip(config.uilanglist.get("Mix two audio files into one audio file"))

        self.action_fanyi.setText(config.uilanglist.get("Text  Or Srt  Translation"))
        self.action_fanyi.setToolTip(
            '将多个srt字幕文件批量进行翻译' if config.defaulelang == 'zh' else 'Batch translation of multiple srt subtitle files')

        self.action_hebingsrt.setText('合并两个字幕' if config.defaulelang == 'zh' else 'Combine Two Subtitles')
        self.action_hebingsrt.setToolTip(
            '将2个字幕文件合并为一个，组成双语字幕' if config.defaulelang == 'zh' else 'Combine 2 subtitle files into one to form bilingual subtitles')

        self.action_clearcache.setText("Clear Cache" if config.defaulelang != 'zh' else '清理缓存和配置')

        self.actionazure_key.setText("AzureGPT 翻译 " if config.defaulelang == 'zh' else 'AzureOpenAI Translation')
        self.actionazure_tts.setText("AzureAI 配音" if config.defaulelang == 'zh' else 'AzureAI TTS')
        self.actiongemini_key.setText("Gemini Pro")
        self.actionElevenlabs_key.setText("ElevenLabs.io")

        self.actionwatermark.setText('批量视频添加水印' if config.defaulelang == 'zh' else 'Add watermark to video')
        self.actionsepar.setText('人声/背景音分离' if config.defaulelang == 'zh' else 'Vocal & instrument Separate')
        self.actionsetini.setText('高级选项' if config.defaulelang == 'zh' else 'Options')

        self.actionvideoandaudio.setText('视频与音频合并' if config.defaulelang == 'zh' else 'Batch video/audio merger')
        self.actionvideoandaudio.setToolTip(
            '批量将视频和音频一一对应合并' if config.defaulelang == 'zh' else 'Batch merge video and audio one-to-one')

        self.actionvideoandsrt.setText('视频与字幕合并' if config.defaulelang == 'zh' else 'Batch Video Srt merger')
        self.actionvideoandsrt.setToolTip(
            '批量将视频和srt字幕一一对应合并' if config.defaulelang == 'zh' else 'Batch merge video and srt subtitles one by one.')

        self.actionformatcover.setText('音视频格式转换' if config.defaulelang == 'zh' else 'Batch Audio/Video conver')
        self.actionformatcover.setToolTip(
            '批量将音频和视频转换格式' if config.defaulelang == 'zh' else 'Batch convert audio and video formats')

        self.actionsubtitlescover.setText('批转换字幕格式' if config.defaulelang == 'zh' else 'Conversion Subtitle Format')
        self.actionsubtitlescover.setToolTip(
            '批量将字幕文件进行格式转换(srt/ass/vtt)' if config.defaulelang == 'zh' else 'Batch convert subtitle formats (srt/ass/vtt)')

        self.actionsrtmultirole.setText('字幕多角色配音' if config.defaulelang == 'zh' else 'Multi voice dubbing for SRT')
        self.actionsrtmultirole.setToolTip(
            '字幕多角色配音：为每条字幕分配一个声音' if config.defaulelang == 'zh' else 'Subtitle multi-role dubbing: assign a voice to each subtitle')

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
        except:
            config.params['translate_type'] = 0
        self.translate_type.setCurrentIndex(config.params['translate_type'])

        if config.params['source_language'] and config.params['source_language'] in self.languagename:
            self.source_language.setCurrentText(config.params['source_language'])
        try:
            config.params['tts_type'] = int(config.params['tts_type'])
        except:
            config.params['tts_type'] = 0

        self.tts_type.setCurrentIndex(config.params['tts_type'])
        self.voice_role.clear()

        if config.params['tts_type'] == tts.CLONE_VOICE_TTS:
            self.voice_role.addItems(config.params["clone_voicelist"])
            threading.Thread(target=tools.get_clone_role).start()
        elif config.params['tts_type'] == tts.CHATTTS:
            self.voice_role.addItems(['No'] + list(config.ChatTTS_voicelist))
        elif config.params['tts_type'] == tts.TTS_API:
            self.voice_role.addItems(config.params['ttsapi_voice_role'].strip().split(','))
        elif config.params['tts_type'] == tts.CHATTERBOX_TTS:
            rolelist = tools.get_chatterbox_role()
            self.voice_role.addItems(rolelist if rolelist else ['chatterbox'])
        elif config.params['tts_type'] == tts.GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
        elif config.params['tts_type'] == tts.COSYVOICE_TTS:
            rolelist = tools.get_cosyvoice_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['clone'])
        elif config.params['tts_type'] == tts.F5_TTS:
            rolelist = tools.get_f5tts_role()
            self.voice_role.addItems(['clone'] + list(rolelist.keys()) if rolelist else ['clone'])
        elif config.params['tts_type'] == tts.FISHTTS:
            rolelist = tools.get_fishtts_role()
            self.voice_role.addItems(list(rolelist.keys()) if rolelist else ['No'])
        elif config.params['tts_type'] == tts.ELEVENLABS_TTS:
            rolelist = tools.get_elevenlabs_role()
            self.voice_role.addItems(['No'] + rolelist)
        elif config.params['tts_type'] == tts.OPENAI_TTS:
            rolelist = config.params.get('openaitts_role', '')
            self.voice_role.addItems(['No'] + rolelist.split(','))
        elif config.params['tts_type'] == tts.QWEN_TTS:
            rolelist = config.params.get('qwentts_role', '')
            self.voice_role.addItems(['No'] + rolelist.split(','))
        elif config.params['tts_type'] == tts.GEMINI_TTS:
            rolelist = config.params.get('gemini_ttsrole', '')
            self.voice_role.addItems(['No'] + rolelist.split(','))
        elif self.win_action.change_by_lang(config.params['tts_type']):
            self.voice_role.clear()

        if config.params['target_language'] and config.params['target_language'] in self.languagename:
            self.target_language.setCurrentText(config.params['target_language'])
            self.win_action.set_voice_role(config.params['target_language'])
            if config.params['voice_role'] and config.params['voice_role'] != 'No' and self.current_rolelist and \
                    config.params['voice_role'] in self.current_rolelist:
                self.voice_role.setCurrentText(config.params['voice_role'])
                self.win_action.show_listen_btn(config.params['voice_role'])

        try:
            config.params['recogn_type'] = int(config.params['recogn_type'])
        except:
            config.params['recogn_type'] = 0
        self.recogn_type.setCurrentIndex(config.params['recogn_type'])
        self.model_name.clear()
        if config.params['recogn_type'] == recognition.Deepgram:
            self.model_name.addItems(config.DEEPGRAM_MODEL)
            curr = config.DEEPGRAM_MODEL
        elif config.params['recogn_type'] == recognition.FUNASR_CN:
            self.model_name.addItems(config.FUNASR_MODEL)
            curr = config.FUNASR_MODEL
        else:
            self.model_name.addItems(config.WHISPER_MODEL_LIST)
            curr = config.WHISPER_MODEL_LIST
        if config.params['model_name'] in curr:
            self.model_name.setCurrentText(config.params['model_name'])
        if config.params['recogn_type'] not in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL,
                                                recognition.OPENAI_WHISPER, recognition.FUNASR_CN,
                                                recognition.Deepgram]:
            self.model_name.setDisabled(True)
        else:
            self.model_name.setDisabled(False)
        self.moshis = {
            "biaozhun": self.action_biaozhun,
            "tiqu": self.action_tiquzimu
        }
        if config.params['model_name'] == 'paraformer-zh' or config.params['recogn_type'] == recognition.Deepgram or \
                config.params['recogn_type'] == recognition.GEMINI_SPEECH:
            self.show_spk.setVisible(True)

    def _bindsignal(self):
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

        print(f"\n####信号绑定结束:{time.time()}")

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
        except:
            config.params['tts_type'] = 0

        if config.params['split_type']:
            d = {"all": 0, "avg": 1}
            self.split_type.setCurrentIndex(d[config.params['split_type']])

        if config.params['subtitle_type'] and int(config.params['subtitle_type']) > 0:
            self.subtitle_type.setCurrentIndex(int(config.params['subtitle_type']))

        try:
            self.voice_rate.setValue(int(config.params['voice_rate'].replace('%', '')))
        except:
            self.voice_rate.setValue(0)
        try:
            self.pitch_rate.setValue(int(config.params['pitch'].replace('Hz', '')))
            self.volume_rate.setValue(int(config.params['volume']))
        except:
            self.pitch_rate.setValue(0)
            self.volume_rate.setValue(0)
        self.addbackbtn.clicked.connect(self.win_action.get_background)

        self.split_type.setDisabled(True if config.params['recogn_type'] > 0 else False)
        self.voice_autorate.setChecked(bool(config.params['voice_autorate']))
        self.video_autorate.setChecked(bool(config.params['video_autorate']))
        self.clear_cache.setChecked(bool(config.params.get('clear_cache')))
        self.enable_cuda.setChecked(True if config.params['cuda'] else False)
        self.only_video.setChecked(True if config.params['only_video'] else False)
        self.is_separate.setChecked(True if config.params['is_separate'] else False)
        self.rephrase.setChecked(config.settings.get('rephrase'))
        self.remove_noise.setChecked(config.params.get('remove_noise'))
        self.copysrt_rawvideo.setChecked(config.params.get('copysrt_rawvideo', False))

        self.bgmvolume.setText(str(config.settings.get('backaudio_volume', 0.8)))
        self.is_loop_bgm.setChecked(bool(config.settings.get('loop_backaudio', True)))

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

        self.label.clicked.connect(lambda: tools.open_url(url='https://pvt9.com/proxy'))
        self.hfaster_help.clicked.connect(lambda: tools.open_url(url='https://pvt9.com/vad'))
        self.split_label.clicked.connect(lambda: tools.open_url(url='https://pvt9.com/splitmode'))
        self.align_btn.clicked.connect(lambda: tools.open_url(url='https://pvt9.com/align'))
        self.glossary.clicked.connect(lambda: tools.show_glossary_editor(self))

        print(f"\n####缓存读取结束:{time.time()}")

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

        self.actionbaidu_key.triggered.connect(lambda: winform.get_win('baidu').openwin())
        self.actionali_key.triggered.connect(lambda: winform.get_win('ali').openwin())
        self.actionparakeet_key.triggered.connect(lambda: winform.get_win('parakeet').openwin())
        self.actionsrtmultirole.triggered.connect(lambda: winform.get_win('fn_peiyinrole').openwin())
        self.actionsubtitlescover.triggered.connect(lambda: winform.get_win('fn_subtitlescover').openwin())
        self.actionazure_key.triggered.connect(lambda: winform.get_win('azure').openwin())
        self.actionazure_tts.triggered.connect(lambda: winform.get_win('azuretts').openwin())
        self.actiongemini_key.triggered.connect(lambda: winform.get_win('gemini').openwin())
        self.actiontencent_key.triggered.connect(lambda: winform.get_win('tencent').openwin())
        self.actionchatgpt_key.triggered.connect(lambda: winform.get_win('chatgpt').openwin())
        self.actionclaude_key.triggered.connect(lambda: winform.get_win('claude').openwin())
        self.actionlibretranslate_key.triggered.connect(lambda: winform.get_win('libre').openwin())
        self.actionai302_key.triggered.connect(lambda: winform.get_win('ai302').openwin())
        self.actionlocalllm_key.triggered.connect(lambda: winform.get_win('localllm').openwin())
        self.actionzijiehuoshan_key.triggered.connect(lambda: winform.get_win('zijiehuoshan').openwin())
        self.actiondeepL_key.triggered.connect(lambda: winform.get_win('deepL').openwin())
        self.actionElevenlabs_key.triggered.connect(lambda: winform.get_win('elevenlabs').openwin())
        self.actiondeepLX_address.triggered.connect(lambda: winform.get_win('deepLX').openwin())
        self.actionott_address.triggered.connect(lambda: winform.get_win('ott').openwin())
        self.actionclone_address.triggered.connect(lambda: winform.get_win('clone').openwin())
        self.actionkokoro_address.triggered.connect(lambda: winform.get_win('kokoro').openwin())
        self.actionchattts_address.triggered.connect(lambda: winform.get_win('chattts').openwin())
        self.actiontts_api.triggered.connect(lambda: winform.get_win('ttsapi').openwin())
        self.actionrecognapi.triggered.connect(lambda: winform.get_win('recognapi').openwin())
        self.actionsttapi.triggered.connect(lambda: winform.get_win('sttapi').openwin())
        self.actiondeepgram.triggered.connect(lambda: winform.get_win('deepgram').openwin())
        self.actiondoubao_api.triggered.connect(lambda: winform.get_win('doubao').openwin())
        self.actiontrans_api.triggered.connect(lambda: winform.get_win('transapi').openwin())
        self.actiontts_gptsovits.triggered.connect(lambda: winform.get_win('gptsovits').openwin())
        self.actiontts_chatterbox.triggered.connect(lambda: winform.get_win('chatterbox').openwin())
        self.actiontts_cosyvoice.triggered.connect(lambda: winform.get_win('cosyvoice').openwin())
        self.actionopenaitts_key.triggered.connect(lambda: winform.get_win('openaitts').openwin())
        self.actionqwentts_key.triggered.connect(lambda: winform.get_win('qwentts').openwin())
        self.actionopenairecognapi_key.triggered.connect(lambda: winform.get_win('openairecognapi').openwin())
        self.actiontts_fishtts.triggered.connect(lambda: winform.get_win('fishtts').openwin())
        self.actiontts_f5tts.triggered.connect(lambda: winform.get_win('f5tts').openwin())
        self.actiontts_volcengine.triggered.connect(lambda: winform.get_win('volcenginetts').openwin())
        self.actionzhipuai_key.triggered.connect(lambda: winform.get_win('zhipuai').openwin())
        self.actiondeepseek_key.triggered.connect(lambda: winform.get_win('deepseek').openwin())
        self.actionopenrouter_key.triggered.connect(lambda: winform.get_win('openrouter').openwin())
        self.actionsiliconflow_key.triggered.connect(lambda: winform.get_win('siliconflow').openwin())
        self.actionwatermark.triggered.connect(lambda: winform.get_win('fn_watermark').openwin())
        self.actionsepar.triggered.connect(lambda: winform.get_win('fn_separate').openwin())
        self.actionsetini.triggered.connect(lambda: winform.get_win('setini').openwin())
        self.actionvideoandaudio.triggered.connect(lambda: winform.get_win('fn_videoandaudio').openwin())
        self.actionvideoandsrt.triggered.connect(lambda: winform.get_win('fn_videoandsrt').openwin())
        self.actionformatcover.triggered.connect(lambda: winform.get_win('fn_formatcover').openwin())
        self.actionsubtitlescover.triggered.connect(lambda: winform.get_win('fn_subtitlescover').openwin())
        self.action_hebingsrt.triggered.connect(lambda: winform.get_win('fn_hebingsrt').openwin())
        self.action_yinshipinfenli.triggered.connect(lambda: winform.get_win('fn_audiofromvideo').openwin())
        self.action_hun.triggered.connect(lambda: winform.get_win('fn_hunliu').openwin())
        self.action_yingyinhebing.triggered.connect(lambda: winform.get_win('fn_vas').openwin())
        self.action_subtitleediter.triggered.connect(lambda: winform.get_win('fn_editer').openwin())
        self.action_fanyi.triggered.connect(lambda: winform.get_win('fn_fanyisrt').openwin())
        self.action_yuyinshibie.triggered.connect(lambda: winform.get_win('fn_recogn').openwin())
        self.action_yuyinhecheng.triggered.connect(lambda: winform.get_win('fn_peiyin').openwin())
        self.action_ffmpeg.triggered.connect(lambda: self.win_action.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.win_action.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.win_action.open_url('discord'))
        self.action_models.triggered.connect(lambda: self.win_action.open_url('models'))

        self.action_gtrans.triggered.connect(lambda: self.win_action.open_url('gtrans'))
        self.action_cuda.triggered.connect(lambda: self.win_action.open_url('cuda'))
        self.action_online.triggered.connect(lambda: self.win_action.open_url('online'))
        self.action_website.triggered.connect(lambda: self.win_action.open_url('website'))
        self.action_blog.triggered.connect(lambda: self.win_action.open_url('bbs'))
        self.action_issue.triggered.connect(lambda: self.win_action.open_url('issue'))
        self.action_about.triggered.connect(self.win_action.about)
        self.action_clearcache.triggered.connect(self.win_action.clearcache)
        self.aisendsrt.toggled.connect(self.checkbox_state_changed)
        self.rightbottom.clicked.connect(self.win_action.about)
        self.statusLabel.clicked.connect(lambda: self.win_action.open_url('help'))
        Path(config.TEMP_DIR + '/stop_process.txt').unlink(missing_ok=True)

        print(f"\n####启动窗口结束:{time.time()}")

    def is_writable(self):
        import uuid
        temp_file_path = f"{config.ROOT_DIR}/.permission_test_{uuid.uuid4()}.tmp"
        try:
            with open(temp_file_path, 'w') as f:
                pass
        except OSError as e:
            tools.show_error(
                f"当前目录 {config.ROOT_DIR} 不可写，请将软件移动到非系统目录下或右键管理员权限打开。" if config.defaulelang == 'zh' else f"The current directory {config.ROOT_DIR}  is not writable, please try moving the software to a non-system directory or right-clicking with administrator privileges.")
        finally:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as e:
                    pass
        threading.Thread(target=tools.get_video_codec, args=(True,)).start()

    def checkbox_state_changed(self, state):
        """复选框状态发生变化时触发的函数"""
        if state:
            config.settings['aisendsrt'] = True
        else:
            config.settings['aisendsrt'] = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.aisendsrt.setChecked(config.settings.get('aisendsrt'))

    def kill_ffmpeg_processes(self):
        import platform
        import signal
        import getpass, subprocess
        try:
            system_platform = platform.system()
            current_user = getpass.getuser()

            if system_platform == "Windows":
                subprocess.call(f"taskkill /F /FI \"USERNAME eq {current_user}\" /IM ffmpeg.exe", shell=True)
            elif system_platform == "Linux" or system_platform == "Darwin":
                process = subprocess.Popen(['ps', '-U', current_user], stdout=subprocess.PIPE)
                out, err = process.communicate()

                for line in out.splitlines():
                    if b'ffmpeg' in line:
                        pid = int(line.split(None, 1)[0])
                        os.kill(pid, signal.SIGKILL)
        except:
            pass

    def closeEvent(self, event):
        config.exit_soft = True
        config.current_status = 'stop'
        try:
            with open(config.TEMP_DIR + '/stop_process.txt', 'w', encoding='utf-8') as f:
                f.write('stop')
        except:
            pass
        sets = QSettings("pyvideotrans", "settings")
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
        print('等待所有进程退出...')
        time.sleep(3)
        try:
            self.kill_ffmpeg_processes()
            time.sleep(3)
        except:
            pass
        os.chdir(config.ROOT_DIR)
        try:
            shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
        except:
            pass
        try:
            shutil.rmtree(config.TEMP_HOME, ignore_errors=True)
        except:
            pass
        event.accept()
