import platform

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QSizePolicy, QApplication

from videotrans.component.controlobj import TextGetdir
from videotrans.configure.config import tr, settings
from videotrans.ui._setup_menus import _setup_actions_and_menus
from videotrans.ui._setup_rows import (
    _create_file_row,
    _create_asr_row,
    _create_translation_row,
    _create_tts_row,
    _create_alignment_row,
)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        _channel_label = 80
        _channel_com = 200

        self.centralwidget = QtWidgets.QWidget()
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.splitter.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.splitter.setLineWidth(1)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.splitter.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        self.splitter.setMinimumWidth(500)

        self.layoutWidget = QtWidgets.QWidget(self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_3.setContentsMargins(0, 0, 3, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setSpacing(8)

        self.verticalLayout_3.addLayout(_create_file_row(self, self.layoutWidget))
        self.verticalLayout_3.addLayout(_create_asr_row(self, self.layoutWidget))
        self.verticalLayout_3.addLayout(_create_translation_row(self, self.layoutWidget))
        self.verticalLayout_3.addLayout(_create_tts_row(self, self.layoutWidget))
        self.verticalLayout_3.addLayout(_create_alignment_row(self, self.layoutWidget))

        self.bgm_layout = QtWidgets.QHBoxLayout()
        self.bgm_layout.setObjectName("bgm_layout")

        self.is_separate = QtWidgets.QCheckBox(self.layoutWidget)
        self.is_separate.setMinimumSize(QtCore.QSize(0, 30))
        self.is_separate.setObjectName("is_separate")
        self.is_separate.setVisible(False)
        self.embed_bgm = QtWidgets.QCheckBox(self.layoutWidget)
        self.embed_bgm.setMinimumSize(QtCore.QSize(0, 30))
        self.embed_bgm.setObjectName("embed_bgm")
        self.embed_bgm.setChecked(True)
        self.embed_bgm.setVisible(False)

        self.addbackbtn = QtWidgets.QPushButton(self.layoutWidget)
        self.addbackbtn.setObjectName("addbackbtn")
        self.addbackbtn.setVisible(False)
        self.addbackbtn.setCursor(Qt.PointingHandCursor)

        self.back_audio = QtWidgets.QLineEdit(self.layoutWidget)
        self.back_audio.setObjectName("back_audio")
        self.back_audio.setVisible(False)

        self.is_loop_bgm = QtWidgets.QComboBox(self.layoutWidget)
        self.is_loop_bgm.addItems([tr('The bgm briefly lengthens'), tr('loop the BGM')])
        self.is_loop_bgm.setVisible(False)

        self.bgmvolume_label = QtWidgets.QLabel()
        self.bgmvolume_label.setText(tr("Volume BGM"))
        self.bgmvolume_label.setVisible(False)
        self.bgmvolume = QtWidgets.QLineEdit()
        self.bgmvolume.setText('0.8')
        self.bgmvolume.setMaximumWidth(80)
        self.bgmvolume.setVisible(False)
        self.bgmvolume.setToolTip(
            tr("BGM volume is a multiple of the original volume, greater than 1 increases, less than decreases"))

        self.set_ass = QtWidgets.QPushButton()
        self.set_ass.setText(tr('Modify hard subtitle style'))
        self.set_ass.setCursor(Qt.PointingHandCursor)
        self.set_ass.setVisible(False)

        self.bgm_layout.addWidget(self.is_separate)
        self.bgm_layout.addWidget(self.embed_bgm)
        self.bgm_layout.addWidget(self.is_loop_bgm)
        self.bgm_layout.addWidget(self.bgmvolume_label)
        self.bgm_layout.addWidget(self.bgmvolume)

        self.bgm_layout.addWidget(self.addbackbtn)
        self.bgm_layout.addWidget(self.back_audio)
        self.bgm_layout.addWidget(self.set_ass)

        self.enable_diariz = QtWidgets.QCheckBox()
        self.enable_diariz.setToolTip(tr("Speaker classification language"))
        self.enable_diariz.setText(tr("Speaker classification"))

        self.fix_punc = QtWidgets.QComboBox()
        self.fix_punc.setToolTip(tr("Restoring punctuation marks when Chinese & English"))
        self.fix_punc.addItems([
            tr("Default punctuation"),
            tr("Restore punctuation"),
            tr("Delete punctuation")
        ])

        self.nums_diariz = QtWidgets.QComboBox()
        self.nums_diariz.setToolTip(tr("Specifying the number of speakers"))
        self.nums_diariz.addItems([tr("No limit"), "2", "3", "4", "5", "6", "7", "8", "9", "10"])

        self.label_6 = QtWidgets.QLabel(self.layoutWidget)
        self.label_6.setObjectName("label_6")
        self.label_6.setVisible(False)

        self.voice_rate = QtWidgets.QSpinBox(self.layoutWidget)
        self.voice_rate.setMinimum(-50)
        self.voice_rate.setMaximum(50)
        self.voice_rate.setMinimumWidth(80)
        self.voice_rate.setObjectName("voice_rate")
        self.voice_rate.setVisible(False)

        self.volume_label = QtWidgets.QLabel(self.layoutWidget)
        self.volume_label.setText(tr("Volume+"))
        self.volume_label.setVisible(False)
        self.volume_rate = QtWidgets.QSpinBox(self.layoutWidget)
        self.volume_rate.setMinimum(-95)
        self.volume_rate.setToolTip(tr("Percentage of volume adjustment"))
        self.volume_rate.setMaximum(100)
        self.volume_rate.setMinimumWidth(80)
        self.volume_rate.setObjectName("volume_rate")
        self.volume_rate.setVisible(False)

        self.pitch_label = QtWidgets.QLabel(self.layoutWidget)
        self.pitch_label.setText(tr("Pitch+"))
        self.pitch_label.setVisible(False)
        self.pitch_rate = QtWidgets.QSpinBox(self.layoutWidget)
        self.pitch_rate.setVisible(False)
        self.pitch_rate.setMinimum(-100)
        self.pitch_rate.setMaximum(100)
        self.pitch_rate.setMinimumWidth(80)
        self.pitch_rate.setObjectName("pitch_rate")

        self.dubb_thread_layout = QtWidgets.QHBoxLayout()
        self.dubb_thread_layout.addWidget(self.label_6)
        self.dubb_thread_layout.addWidget(self.voice_rate)
        self.dubb_thread_layout.addWidget(self.volume_label)
        self.dubb_thread_layout.addWidget(self.volume_rate)
        self.dubb_thread_layout.addWidget(self.pitch_label)
        self.dubb_thread_layout.addWidget(self.pitch_rate)
        self.dubb_thread_layout.addStretch()

        self.dubb_thread_layout.addWidget(self.remove_noise)
        self.dubb_thread_layout.addWidget(self.fix_punc)
        self.dubb_thread_layout.addWidget(self.enable_diariz)
        self.dubb_thread_layout.addWidget(self.nums_diariz)

        self.adv_layout_outer = QtWidgets.QVBoxLayout()
        self.advcontainer = QtWidgets.QWidget()
        self.advcontainer.setLayout(self.adv_layout_outer)
        self.advcontainer.setObjectName("advContainer")
        self.advcontainer.setStyleSheet("""#advContainer {
        border: 1px solid #455364;
        border-radius: 5px;         
        padding: 10px; 
    }""")

        self.adv_layout_outer.addLayout(self.dubb_thread_layout)
        self.adv_layout_outer.addLayout(self.bgm_layout)
        self.verticalLayout_3.addWidget(self.advcontainer)
        self.advcontainer.setVisible(False)

        self.show_tips = QtWidgets.QLabel(self.layoutWidget)
        self.show_tips.setWordWrap(True)
        self.show_tips.setStyleSheet(
            """background-color:transparent;border-color:transparent;color:#aaaaaa;text-align:left""")
        self.show_tips.setObjectName("show_tips")
        self.output_dir = QtWidgets.QLabel(self.layoutWidget)
        self.output_dir.setWordWrap(True)
        self.output_dir.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_dir.setStyleSheet(
            """background-color:transparent;border-color:transparent;color:#929ca7;text-align:center""")
        self.output_dir.setObjectName("output_dir")
        self.verticalLayout_3.addWidget(self.show_tips)

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")

        self.enable_cuda = QtWidgets.QCheckBox(self.layoutWidget)
        self.enable_cuda.setMinimumSize(QtCore.QSize(50, 20))
        self.enable_cuda.setObjectName("enable_cuda")
        self.enable_cuda.setToolTip(tr('cudatips'))

        self.startbtn = QtWidgets.QPushButton(self.layoutWidget)
        self.startbtn.setMinimumSize(QtCore.QSize(160, 40))
        self.startbtn.setObjectName("startbtn")

        self.retrybtn = QtWidgets.QPushButton(self.layoutWidget)
        self.retrybtn.setObjectName("retrybtn")
        self.retrybtn.setVisible(False)
        self.retrybtn.setText(tr('Retry failed'))

        self.horizontalLayout_3.addStretch(1)
        self.horizontalLayout_3.addWidget(self.enable_cuda)
        self.horizontalLayout_3.addWidget(self.startbtn)
        self.horizontalLayout_3.addWidget(self.retrybtn)
        self.horizontalLayout_3.addStretch(1)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)
        self.verticalLayout_3.addWidget(self.output_dir)

        self.scroll_area = QtWidgets.QScrollArea(self.layoutWidget)
        self.scroll_area.setStyleSheet("border-color:#32414B")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("scroll_area")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()

        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.scroll_area.setWidgetResizable(True)
        viewport = QtWidgets.QWidget(self.scroll_area)
        self.scroll_area.setWidget(viewport)
        self.processlayout = QtWidgets.QVBoxLayout(viewport)
        self.processlayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.verticalLayout_3.addWidget(self.scroll_area)
        self.verticalLayoutWidget = QtWidgets.QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")

        self.subtitle_layout = QtWidgets.QHBoxLayout(self.verticalLayoutWidget)
        self.subtitle_layout.setContentsMargins(3, 0, 0, 0)
        self.subtitle_layout.setObjectName("subtitle_layout")

        self.source_area_layout = QtWidgets.QVBoxLayout()

        self.subtitle_area_placeholder = QtWidgets.QWidget(self)
        self.subtitle_area_placeholder.setObjectName("subtitle_area_placeholder")

        self.import_sub = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.import_sub.setObjectName("import_sub")
        self.source_area_layout.addWidget(self.subtitle_area_placeholder)
        self.source_area_layout.addWidget(self.import_sub)
        self.target_subtitle_area = QtWidgets.QVBoxLayout()

        self.subtitle_layout.addLayout(self.source_area_layout)
        self.subtitle_layout.addLayout(self.target_subtitle_area)

        self.horizontalLayout_7.addWidget(self.splitter)
        MainWindow.setCentralWidget(self.centralwidget)

        self.statusBar = QtWidgets.QStatusBar()
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)

        _setup_actions_and_menus(self, MainWindow)

        if platform.system() == 'Darwin':
            self.enable_cuda.setChecked(False)
            self.enable_cuda.hide()

        self._set_Ui_Text()

    def _set_Ui_Text(self):
        self.subtitle_area = TextGetdir(self)
        self.subtitle_area.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.subtitle_area.setObjectName("subtitle_area")
        self.subtitle_area.setPlaceholderText(
            f"{tr('zimubianjitishi')}\n\n{tr('subtitle_tips')}\n\n{tr('meitiaozimugeshi')}")
        self.source_area_layout.insertWidget(self.source_area_layout.indexOf(self.subtitle_area_placeholder),
                                             self.subtitle_area)
        self.subtitle_area_placeholder.hide()
        self.subtitle_area_placeholder.deleteLater()

        self.statusLabel = QtWidgets.QPushButton(tr("Open Documents"))
        self.statusLabel.setStyleSheet("""color:#ffff66""")
        self.statusBar.addWidget(self.statusLabel)

        self.rightbottom = QtWidgets.QPushButton(tr('juanzhu'))

        self.container = QtWidgets.QToolBar()
        self.container.addWidget(self.rightbottom)
        self.restart_btn = QtWidgets.QPushButton(tr("Restart"))
        self.container.addWidget(self.restart_btn)
        self.statusBar.addPermanentWidget(self.container)

        self.rightbottom.setStyleSheet("""color:#ffff66""")
        self.restart_btn.setStyleSheet("""color:#ffffbb""")
        self.restart_btn.setToolTip(
            tr("Click to end all tasks immediately and restart"))

        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.btn_get_video.setToolTip(
            tr("Multiple MP4 videos can be selected and automatically queued for processing"))
        self.btn_get_video.setText(tr("Select audio & video"))
        self.btn_save_dir.setToolTip(tr("Select where to save the processed output resources"))
        self.btn_save_dir.setText(tr("Save to.."))

        self.label_9.setText(tr("Translate channel"))
        self.translate_type.setToolTip(
            tr("Translation channels used in translating subtitle text"))
        self.label.setText(tr("Proxy"))
        self.label.setToolTip(
            tr("Click to view the tutorial for filling in the network proxy"))
        self.label.setCursor(Qt.PointingHandCursor)

        self.proxy.setPlaceholderText(tr("proxy address"))
        self.listen_btn.setToolTip(tr("shuoming01"))
        self.listen_btn.setText(tr("Trial dubbing"))
        self.label_2.setText(tr("Speech language"))
        self.source_language.setToolTip(tr("The language used for the original video pronunciation"))
        self.label_3.setText(tr("Target lang"))
        self.target_language.setToolTip(tr("What language do you want to translate into"))
        self.tts_text.setText(tr("Dubbing channel"))
        self.label_4.setText(tr("Dubbing role") + " ")
        self.voice_role.setToolTip(tr("No is not dubbing"))

        self.model_name.setToolTip(tr(
            "From base to large v3, the effect is getting better and better, but the speed is also getting slower and slower"))
        self.subtitle_type.setToolTip(tr("shuoming02"))

        self.label_6.setText(tr("Dubbing speed"))
        self.voice_rate.setToolTip(tr("Overall acceleration or deceleration of voice over playback"))
        self.voice_autorate.setText(tr("Dubbing acceler"))
        self.voice_autorate.setToolTip(tr("shuoming03"))
        self.video_autorate.setText(tr("Slow video"))
        self.video_autorate.setToolTip(tr("Video Auto Slow"))

        self.remove_silent_mid.setText(tr("Del inline mute?"))
        self.remove_silent_mid.setToolTip(
            tr("Selecting this option will delete the silent intervals between subtitles"))

        self.align_sub_audio.setText(tr("Align subtitles and audio"))
        self.align_sub_audio.setToolTip(tr("If selected, it will force the subtitles and audio to align."))

        self.enable_cuda.setText(tr("Enable CUDA?"))
        self.embed_bgm.setText(tr("embed_bgm"))
        self.is_separate.setText(tr("Retain original background sound"))
        self.is_separate.setToolTip(tr(
            "If selected, separate human voice and background sound, and finally output video will embed background sound"))
        self.startbtn.setText(tr("Start"))
        self.addbackbtn.setText(tr("Add background audio"))
        self.addbackbtn.setToolTip(
            tr("Add background audio for output video"))
        self.back_audio.setPlaceholderText(tr("back_audio_place"))
        self.back_audio.setToolTip(tr("back_audio_place"))

        self.import_sub.setText(tr("Import original language SRT"))

        self.menu_Key.setTitle(tr("&Setting"))
        self.menu_TTS.setTitle(tr("&TTSsetting"))
        self.menu_RECOGN.setTitle(tr("&RECOGNsetting"))
        self.menu.setTitle(tr("&Tools"))
        self.menu_H.setTitle(tr("&Help"))
        self.toolBar.setWindowTitle("toolBar")
        self.actionbaidu_key.setText(tr("Baidu Key"))
        self.actionali_key.setText(tr("Alibaba Translation"))
        self.actionchatgpt_key.setText(
            tr("OpenAI API & Compatible AI"))
        self.actionzhipuai_key.setText(tr("Zhipu AI"))
        self.actionsiliconflow_key.setText(tr("SiliconFlow"))
        self.actiondeepseek_key.setText('DeepSeek')
        self.actionminimax_key.setText('MiniMax AI')
        self.actionqwenmt_key.setText(tr('Ali Qwen3-ASR'))
        self.actionopenrouter_key.setText('OpenRouter.ai')
        self.actionlibretranslate_key.setText("LibreTranslate API")
        self.actionopenaitts_key.setText("OpenAI TTS")
        self.actionxaitts_key.setText("X.AI TTS")
        self.actionxiaomi_key.setText(tr("XiaoMi")+ "AI")
        self.actionqwentts_key.setText("Qwen3 TTS(Bailian)")
        self.actionopenairecognapi_key.setText(
            tr("OpenAI Speech to Text API"))
        self.actionparakeet_key.setText('Nvidia parakeet-tdt')
        self.actionai302_key.setText(tr("302.AI API KEY"))
        self.actionlocalllm_key.setText(tr("Local LLM API"))
        self.actionzijiehuoshan_key.setText(tr("ByteDance Ark"))
        self.actiondeepL_key.setText("DeepL Key")

        self.action_ffmpeg.setText("FFmpeg")
        self.action_ffmpeg.setToolTip(tr("Go FFmpeg website"))
        self.action_git.setText("Github Repository")
        self.action_issue.setText(tr("Post issue"))
        self.actiondeepLX_address.setText("DeepLX Api")
        self.actionclone_address.setText(tr("Clone-Voice TTS"))
        self.actionkokoro_address.setText("Kokoro TTS")
        self.actionchattts_address.setText("ChatTTS")
        self.actiontts_api.setText(tr("TTS API"))
        self.actionminimaxi_api.setText("Minimaxi TTS API")
        self.actiontrans_api.setText(tr("Transate API"))
        self.actionrecognapi.setText(tr("Custom Speech Recognition API"))
        self.actionsttapi.setText(tr("STT Speech Recognition API"))
        self.actionwhisperx.setText('WhisperX-API')
        self.actiondeepgram.setText(
            tr("Deepgram Speech Recognition API"))
        self.actionxxl.setText('Faster_Whisper_XXL.exe')
        self.actioncpp.setText('Whisper.cpp')
        self.actionzijierecognmodel_api.setText(tr("VolcEngine STT"))
        self.actiontts_gptsovits.setText("GPT-SoVITS TTS")
        self.actiontts_chatterbox.setText("ChatterBox TTS")
        self.actiontts_cosyvoice.setText("CosyVoice TTS")
        self.actiontts_qwenttslocal.setText(f"Qwen3 TTS({tr('Local')})")
        self.actiontts_fishtts.setText("Fish TTS")
        self.actiontts_gradiowin.setText("Index/VoxCPM/SparK/Confucius")
        self.actiontts_refaudio.setText(tr("Set reference audio"))
        self.actiontts_doubao2.setText(tr("DouBao2"))
        self.action_website.setText(tr("Documents"))
        self.action_discord.setText(tr("Solution to model download failure"))
        self.action_blog.setText(tr("Having problems? Ask"))
        self.action_gtrans.setText(
            tr("Download Hard Subtitle Extraction Software"))
        self.action_cuda.setText('CUDA & cuDNN')
        self.action_online.setText(tr("Disclaimer"))
        self.actiontencent_key.setText(tr("Tencent Key"))
        self.action_about.setText(tr("Donating developers"))

        self.action_biaozhun.setText(tr("Standard Function Mode"))
        self.action_biaozhun.setToolTip(
            tr("Batch audio or video translation with all configuration options customizable on demand"))
        self.action_yuyinshibie.setText(tr("Speech Recognition Text"))
        self.action_yuyinshibie.setToolTip(
            tr("Batch recognize speech in audio or video as srt subtitles"))

        self.action_yuyinhecheng.setText(tr("From  Text  Into  Speech"))
        self.action_yuyinhecheng.setToolTip(
            tr("Batch dubbing based on srt subtitle files"))

        self.action_tiquzimu.setText(tr("Extract Srt And Translate"))
        self.action_tiquzimu.setToolTip(
            tr("Batch recognize speech in video as srt subtitles"))

        self.action_yinshipinfenli.setText(tr("Separate Video to audio"))
        self.action_yinshipinfenli.setToolTip(tr("Separate audio and silent videos from videos"))

        self.action_yingyinhebing.setText(tr("Video Subtitles Merging"))
        self.action_yingyinhebing.setToolTip(tr("Merge audio, video, and subtitles into one file"))
        self.action_clipvideo.setText(tr("Edit video on subtitles"))
        self.action_clipvideo.setToolTip(tr("Edit video on subtitles"))
        self.action_realtime_stt.setText(tr("Real-time speech-to-text"))
        self.action_textmatching.setText(tr("Text matching and timing"))
        self.action_textmatching.setToolTip(tr("Text matching and timing"))

        self.action_hun.setText(tr("Mixing 2 Audio Streams"))
        self.action_hun.setToolTip(tr("Mix two audio files into one audio file"))

        self.action_fanyi.setText(tr("Text  Or Srt  Translation"))
        self.action_fanyi.setToolTip(
            tr("Batch translation of multiple srt subtitle files"))

        self.action_hebingsrt.setText(tr("Combine Two Subtitles"))
        self.action_hebingsrt.setToolTip(
            tr("Combine 2 subtitle files into one to form bilingual subtitles"))

        self.action_clearcache.setText(tr("Clear Cache"))
        self.action_set_proxy.setText(tr("Setting up a network proxy"))

        self.actionazure_key.setText(tr("AzureOpenAI Translation"))
        self.actionazure_tts.setText(tr("AzureAI TTS"))
        self.actiongemini_key.setText("Gemini AI")
        self.actioncamb_key.setText("CAMB AI")
        self.actionElevenlabs_key.setText("ElevenLabs.io")

        self.actionwatermark.setText(tr("Add watermark to video"))
        self.actionsepar.setText(tr("Vocal & instrument Separate"))
        self.actionsetini.setText(tr("Options"))

        self.actionvideoandaudio.setText(tr("Batch video/audio merger"))
        self.actionvideoandaudio.setToolTip(
            tr("Batch merge video and audio one-to-one"))

        self.actionvideoandsrt.setText(tr("Batch Video Srt merger"))
        self.actionvideoandsrt.setToolTip(
            tr("Batch merge video and srt subtitles one by one."))

        self.actionformatcover.setText(tr("Batch Audio/Video conver"))
        self.actionformatcover.setToolTip(
            tr("Batch convert audio and video formats"))

        self.actionsubtitlescover.setText(tr("Conversion Subtitle Format"))
        self.actionsubtitlescover.setToolTip(
            tr("Batch convert subtitle formats (srt/ass/vtt)"))

        self.actionsrtmultirole.setText(tr("Multi voice dubbing for SRT"))
        self.actionsrtmultirole.setToolTip(
            tr("Subtitle multi-role dubbing: assign a voice to each subtitle"))
