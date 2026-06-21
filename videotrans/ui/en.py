import platform

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal,QTimer
from PySide6.QtWidgets import QSizePolicy, QApplication

from videotrans.component.controlobj import TextGetdir
from videotrans.configure.config import tr, settings


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        # 语音识别渠道、翻译渠道、配音渠道 label和下拉框宽度
        _channel_label=80
        _channel_com=200       

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

        # 首行操作
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")

        self.btn_get_video = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_get_video.setMinimumSize(QtCore.QSize(120, 30))
        self.btn_get_video.setObjectName("btn_get_video")

        self.source_mp4 = QtWidgets.QLabel('')
        self.source_mp4.setMaximumWidth(100)
        self.source_mp4.setObjectName("source_mp4")

        self.clear_cache = QtWidgets.QCheckBox(self.layoutWidget)
        self.clear_cache.setMinimumSize(QtCore.QSize(50, 20))
        self.clear_cache.setObjectName("clear_cache")
        self.clear_cache.setToolTip(
            tr("Cleaning up files that have been processed in previous executions, such as recognized or translated subtitle files"))
        self.clear_cache.setText(tr("Del Generated"))
        self.clear_cache.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.select_file_type = QtWidgets.QCheckBox()
        self.select_file_type.setText(tr("Folder"))
        self.select_file_type.setToolTip(
            tr("Multiple files can be selected by default, check the box to select folders"))

        self.horizontalLayout_6.addWidget(self.btn_get_video)
        self.horizontalLayout_6.addWidget(self.select_file_type)

        self.horizontalLayout_6.addWidget(self.clear_cache)
        self.horizontalLayout_6.addWidget(self.source_mp4)

        self.btn_save_dir = QtWidgets.QPushButton()
        self.btn_save_dir.setMinimumSize(QtCore.QSize(120, 30))
        self.btn_save_dir.setObjectName("btn_save_dir")

        self.copysrt_rawvideo = QtWidgets.QCheckBox(self.layoutWidget)
        self.copysrt_rawvideo.setMinimumSize(QtCore.QSize(0, 30))
        self.copysrt_rawvideo.setObjectName("copysrt_rawvideo")
        self.copysrt_rawvideo.setVisible(False)
        self.copysrt_rawvideo.setText(tr("Moving subtitle"))
        self.copysrt_rawvideo.setToolTip(
            tr("When this item is checked, and the target language is different from the language of the pronunciation will move the translated srt file to the original video location and rename it to the same name as the video."))

        self.only_out_mp4 = QtWidgets.QCheckBox()
        self.only_out_mp4.setText(tr('Output only mp4'))
        self.only_out_mp4.setToolTip(tr('only_out_mp4'))

        self.shutdown = QtWidgets.QCheckBox()
        self.shutdown.setObjectName("shutdown")
        self.shutdown.setToolTip(
            tr("Automatic shutdown after completing all tasks"))
        self.shutdown.setText(tr("Automatic shutdown"))
        self.shutdown.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.horizontalLayout_6.addStretch()
        self.horizontalLayout_6.addWidget(self.btn_save_dir)
        self.horizontalLayout_6.addWidget(self.copysrt_rawvideo)
        self.horizontalLayout_6.addWidget(self.only_out_mp4)
        self.horizontalLayout_6.addWidget(self.shutdown)
        self.verticalLayout_3.addLayout(self.horizontalLayout_6)

        # 语音识别渠道行
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.reglabel = QtWidgets.QLabel(self.layoutWidget)
        self.reglabel.setStyleSheet("""background-color:transparent""")

        self.reglabel.setText(tr("Speech Recognit"))
        self.reglabel.setToolTip(
            tr("Click to set detailed recognition parameters when using faster-whisper"))
        #self.reglabel.setMinimumWidth(_channel_label)
        self.recogn_type = QtWidgets.QComboBox(self.layoutWidget)
        self.recogn_type.setMinimumSize(QtCore.QSize(_channel_com, 30))
        self.recogn_type.setObjectName("label_5")
        self.recogn_type.setToolTip(tr('model_type_tips'))

        self.model_name_help = QtWidgets.QLabel(self.layoutWidget)
        self.model_name_help.setText(tr("ASRModel"))
        #self.model_name_help.setMinimumWidth(_channel_label)

        self.model_name = QtWidgets.QComboBox(self.layoutWidget)
        self.model_name.setMinimumWidth(250)
        self.model_name.setObjectName("model_name")

        self.rephrase = QtWidgets.QComboBox()
        self.rephrase.addItems([tr("Default sentence"), tr("LLM Rephrase")])
        self.rephrase.setToolTip(tr("re-segment the sentence.the original segmentation will be used"))

        self.remove_noise = QtWidgets.QCheckBox()
        self.remove_noise.setText(tr("Noise reduction"))
        self.remove_noise.setToolTip(
            tr("Select to perform noise reduction processing from modelscope.cn, which takes a long time"))

        self.recogn2pass = QtWidgets.QCheckBox()
        self.recogn2pass.setToolTip(tr("Secondary speech recognition of dubbing files"))
        self.recogn2pass.setText(tr("STT again"))

        self.horizontalLayout_4.addWidget(self.reglabel)
        self.horizontalLayout_4.addWidget(self.recogn_type)
        self.horizontalLayout_4.addWidget(self.model_name_help)
        self.horizontalLayout_4.addWidget(self.model_name)

        self.horizontalLayout_4.addWidget(self.rephrase)
        self.horizontalLayout_4.addStretch()
        self.horizontalLayout_4.addWidget(self.recogn2pass)

        self.verticalLayout_3.addLayout(self.horizontalLayout_4)

        # 翻译渠道行
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")

        self.label_9 = QtWidgets.QLabel(self.layoutWidget)
        self.label_9.setObjectName("label_9")
        self.label_9.setStyleSheet("""background-color:transparent""")
        self.label_9.setToolTip(
            tr("Click to set the number of subtitles to be translated at the same time"))
        #self.label_9.setMinimumWidth(_channel_label)
        self.translate_type = QtWidgets.QComboBox(self.layoutWidget)
        self.translate_type.setMinimumSize(QtCore.QSize(_channel_com, 30))
        self.translate_type.setObjectName("translate_type")
        self.translate_type.setToolTip(
            tr("Select the channel used to translate text"))

        self.horizontalLayout_5.addWidget(self.label_9)
        self.horizontalLayout_5.addWidget(self.translate_type)

        self.label_2 = QtWidgets.QPushButton(self.layoutWidget)
        self.label_2.setStyleSheet("""background-color:transparent""")
        self.label_2.setObjectName("label_2")
        self.source_language = QtWidgets.QComboBox(self.layoutWidget)
        self.source_language.setObjectName("source_language")
        self.source_language.setMinimumWidth(130)

        self.label_3 = QtWidgets.QPushButton(self.layoutWidget)
        self.label_3.setObjectName("label_3")
        self.label_3.setStyleSheet("""background-color:transparent""")
        #self.label_3.setMinimumWidth(_channel_label)
        self.target_language = QtWidgets.QComboBox(self.layoutWidget)
        self.target_language.setObjectName("target_language")
        self.target_language.setMinimumWidth(130)

        self.aisendsrt = QtWidgets.QCheckBox()
        self.aisendsrt.setText(tr("Send SRT"))
        self.aisendsrt.setToolTip(
            tr("When using AI translation channel, you can translate in srt format, but there may be more empty lines"))
        self.aisendsrt.setChecked(settings.get('aisendsrt'))

        self.glossary = QtWidgets.QPushButton(self.layoutWidget)
        self.glossary.setObjectName("glossary")
        self.glossary.setText(tr("glossary"))
        self.glossary.setStyleSheet("""background-color:transparent;border:1px solid #455364""")
        self.glossary.setCursor(Qt.PointingHandCursor)
        self.glossary.setToolTip(tr("Click to set up and modify the glossary"))

        self.horizontalLayout_5.addWidget(self.label_2)
        self.horizontalLayout_5.addWidget(self.source_language)
        self.horizontalLayout_5.addWidget(self.label_3)
        self.horizontalLayout_5.addWidget(self.target_language)
        self.horizontalLayout_5.addStretch()
        self.horizontalLayout_5.addWidget(self.aisendsrt)
        

        self.verticalLayout_3.addLayout(self.horizontalLayout_5)

        # 配音渠道行
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.tts_text = QtWidgets.QLabel(self.layoutWidget)
        self.tts_text.setObjectName("tts_text")
        self.tts_text.setStyleSheet("""background-color:transparent""")
        self.tts_text.setToolTip(
            tr("Click to set the number of threads to be used for dubbing"))
        
        #self.tts_text.setMinimumWidth(_channel_label)
        self.tts_type = QtWidgets.QComboBox(self.layoutWidget)
        self.tts_type.setMinimumSize(QtCore.QSize(_channel_com, 30))
        self.tts_type.setObjectName("tts_type")

        self.tts_type.setToolTip(tr("Select the channel used to dub"))

        self.label_4 = QtWidgets.QPushButton(self.layoutWidget)
        self.label_4.setObjectName("label_4")
        self.label_4.setStyleSheet("background-color:transparent")
        #self.label_4.setMinimumWidth(_channel_label)
        self.voice_role = QtWidgets.QComboBox(self.layoutWidget)
        self.voice_role.setMinimumWidth(200)
        self.voice_role.setObjectName("voice_role")

        self.listen_btn = QtWidgets.QPushButton(self.layoutWidget)
        self.listen_btn.setEnabled(False)
        self.listen_btn.setStyleSheet("""background-color:transparent""")

        self.horizontalLayout.addWidget(self.tts_text)
        self.horizontalLayout.addWidget(self.tts_type)
        self.horizontalLayout.addWidget(self.label_4)
        self.horizontalLayout.addWidget(self.voice_role)
        self.horizontalLayout.addWidget(self.listen_btn)
        self.horizontalLayout.addStretch()
        self.horizontalLayout.addWidget(self.glossary)
        self.verticalLayout_3.addLayout(self.horizontalLayout)

        # 对齐行
        self.align_layout = QtWidgets.QHBoxLayout()
        self.align_btn = QtWidgets.QLabel()

        self.align_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        self.align_btn.setObjectName("align_btn")
        #self.align_btn.setMinimumWidth(_channel_label)
        self.align_btn.setText(tr("Alignment control"))
        self.align_btn.setToolTip(tr("View alignment tutorial"))

        self.voice_autorate = QtWidgets.QCheckBox(self.layoutWidget)
        self.voice_autorate.setObjectName("voice_autorate")

        self.video_autorate = QtWidgets.QCheckBox(self.layoutWidget)
        self.video_autorate.setObjectName("videoe_autorate")

        self.remove_silent_mid = QtWidgets.QCheckBox()
        self.remove_silent_mid.setObjectName("remove_silent_mid")
        self.remove_silent_mid.setVisible(False)
        self.align_sub_audio = QtWidgets.QCheckBox()
        self.align_sub_audio.setObjectName("align_sub_audio")
        self.align_sub_audio.setVisible(False)

        self.subtitle_type = QtWidgets.QComboBox(self.layoutWidget)
        self.subtitle_type.setMinimumSize(QtCore.QSize(150, 30))
        self.subtitle_type.setObjectName("subtitle_type")

        self.align_layout.addWidget(self.align_btn)
        self.align_layout.addWidget(self.voice_autorate)
        self.align_layout.addWidget(self.video_autorate)
        self.align_layout.addWidget(self.remove_silent_mid)
        self.align_layout.addWidget(self.align_sub_audio)
        self.align_layout.addWidget(self.subtitle_type)

        self.set_adv_status = QtWidgets.QPushButton()
        self.set_adv_status.setText(tr('More settings'))
        self.set_adv_status.setCursor(Qt.PointingHandCursor)

        self.label = QtWidgets.QPushButton(self.layoutWidget)
        self.label.setMinimumSize(QtCore.QSize(0, 30))
        self.label.setObjectName("label")
        self.label.setStyleSheet("""background-color:transparent""")

        self.proxy = QtWidgets.QLineEdit(self.layoutWidget)
        self.proxy.setMinimumSize(QtCore.QSize(200, 30))
        self.proxy.setObjectName("proxy")

        self.output_srt_label = QtWidgets.QLabel(tr('Output') + tr('Subtitles'))
        self.output_srt = QtWidgets.QComboBox()
        self.output_srt.addItems([
            tr('default'),
            tr('Target language under(Bilingual)'),
            tr('Target language up(Bilingual)'),
        ])
        self.output_srt.setVisible(False)
        self.output_srt_label.setVisible(False)

        self.align_layout.addWidget(self.output_srt_label)
        self.align_layout.addWidget(self.output_srt)
        self.align_layout.addStretch()
        self.align_layout.addWidget(self.label)
        self.align_layout.addWidget(self.proxy)
        self.align_layout.addWidget(self.set_adv_status)
        self.verticalLayout_3.addLayout(self.align_layout)

        # 背景行
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

        # 是否循环播放背景
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

        # 配音

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

        self.adv_layout_outer.addLayout(self.dubb_thread_layout)  # 配音      
        self.adv_layout_outer.addLayout(self.bgm_layout)  # 背景
        self.verticalLayout_3.addWidget(self.advcontainer)
        self.advcontainer.setVisible(False)

        # 简短提示行
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


        # 启动按钮行
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
        self.menuBar = QtWidgets.QMenuBar()

        self.menuBar.setObjectName("menuBar")
        self.menu_Key = QtWidgets.QMenu(self.menuBar)
        self.menu_Key.setObjectName("menu_Key")

        self.menu_TTS = QtWidgets.QMenu(self.menuBar)
        self.menu_TTS.setObjectName("menu_TTS")

        self.menu_RECOGN = QtWidgets.QMenu(self.menuBar)
        self.menu_RECOGN.setObjectName("menu_RECOGN")

        self.menu = QtWidgets.QMenu(self.menuBar)
        self.menu.setObjectName("menu")
        self.menu_H = QtWidgets.QMenu(self.menuBar)
        self.menu_H.setObjectName("menu_H")
        MainWindow.setMenuBar(self.menuBar)
        self.toolBar = QtWidgets.QToolBar()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.toolBar.sizePolicy().hasHeightForWidth())
        self.toolBar.setSizePolicy(sizePolicy)
        self.toolBar.setMinimumSize(QtCore.QSize(0, 0))
        self.toolBar.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.toolBar.setMovable(True)
        self.toolBar.setIconSize(QtCore.QSize(100, 40))
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolBar.setFloatable(True)
        self.toolBar.setObjectName("toolBar")
        self.toolBar.setStyleSheet("""
    QToolBar QToolButton {
        min-width: 130px; 
        text-align: center; 
    }
""")
        MainWindow.addToolBar(QtCore.Qt.LeftToolBarArea, self.toolBar)

        self.actionbaidu_key = QtGui.QAction()
        self.actionbaidu_key.setObjectName("actionbaidu_key")
        self.actionali_key = QtGui.QAction()
        self.actionali_key.setObjectName("actionali_key")

        self.actionchatgpt_key = QtGui.QAction()
        self.actionchatgpt_key.setObjectName("actionchatgpt_key")
        self.actionzhipuai_key = QtGui.QAction()
        self.actionzhipuai_key.setObjectName("actionzhipuai_key")
        self.actionsiliconflow_key = QtGui.QAction()
        self.actionsiliconflow_key.setObjectName("actionsiliconflow_key")
        self.actiondeepseek_key = QtGui.QAction()
        self.actiondeepseek_key.setObjectName("actiondeepseek_key")
        self.actionminimax_key = QtGui.QAction()
        self.actionminimax_key.setObjectName("actionminimax_key")
        self.actionqwenmt_key = QtGui.QAction()
        self.actionqwenmt_key.setObjectName("actionqwenmt_key")
        self.actionopenrouter_key = QtGui.QAction()
        self.actionopenrouter_key.setObjectName("actionopenrouter_key")

        self.actionlibretranslate_key = QtGui.QAction()
        self.actionlibretranslate_key.setObjectName("actionlibretranslate_key")
        self.actionopenaitts_key = QtGui.QAction()
        self.actionopenaitts_key.setObjectName("actionopenaitts_key")
        self.actionxaitts_key = QtGui.QAction()
        self.actionxaitts_key.setObjectName("actionxaitts_key")
        self.actionxiaomi_key = QtGui.QAction()
        self.actionxiaomi_key.setObjectName("actionxiaomi_key")
        self.actionqwentts_key = QtGui.QAction()
        self.actionqwentts_key.setObjectName("actionqwentts_key")
        self.actionopenairecognapi_key = QtGui.QAction()
        self.actionopenairecognapi_key.setObjectName("actionopenairecognapi_key")
        self.actionparakeet_key = QtGui.QAction()
        self.actionparakeet_key.setObjectName("actionparakeet_key")
        self.actionai302_key = QtGui.QAction()
        self.actionai302_key.setObjectName("actionai302_key")
        self.actionlocalllm_key = QtGui.QAction()
        self.actionlocalllm_key.setObjectName("actionlocalllm_key")
        self.actionzijiehuoshan_key = QtGui.QAction()
        self.actionzijiehuoshan_key.setObjectName("actionzijiehuoshan_key")
        self.actiondeepL_key = QtGui.QAction()
        self.actiondeepL_key.setObjectName("actiondeepL_key")

        self.actionazure_tts = QtGui.QAction()
        self.actionazure_tts.setObjectName("actionazure_tts")

        self.action_ffmpeg = QtGui.QAction()
        self.action_ffmpeg.setObjectName("action_ffmpeg")
        self.action_git = QtGui.QAction()
        self.action_git.setObjectName("action_git")
        self.action_issue = QtGui.QAction()
        self.action_issue.setObjectName("action_issue")
        self.actiondeepLX_address = QtGui.QAction()
        self.actiondeepLX_address.setObjectName("actiondeepLX_address")
        self.actionott_address = QtGui.QAction()
        self.actionott_address.setObjectName("actionott_address")

        self.actionclone_address = QtGui.QAction()
        self.actionclone_address.setObjectName("actionclone_address")
        self.actionkokoro_address = QtGui.QAction()
        self.actionkokoro_address.setObjectName("actionkokoro_address")
        self.actionchattts_address = QtGui.QAction()
        self.actionchattts_address.setObjectName("actionchattts_address")

        self.actiontts_api = QtGui.QAction()
        self.actiontts_api.setObjectName("actiontts_api")

        self.actionminimaxi_api = QtGui.QAction()
        self.actionminimaxi_api.setObjectName("actionminimaxi_api")

        self.actiontrans_api = QtGui.QAction()
        self.actiontrans_api.setObjectName("actiontrans_api")
        self.actionrecognapi = QtGui.QAction()
        self.actionrecognapi.setObjectName("actionrecognapi")
        self.actionsttapi = QtGui.QAction()
        self.actionsttapi.setObjectName("actionsttapi")
        self.actionwhisperx = QtGui.QAction()
        self.actionwhisperx.setObjectName("actionwhisperx")
        self.actiondeepgram = QtGui.QAction()
        self.actiondeepgram.setObjectName("actiondeepgram")
        self.actionxxl = QtGui.QAction()
        self.actionxxl.setObjectName("actionxxl")
        self.actioncpp = QtGui.QAction()
        self.actioncpp.setObjectName("actioncpp")

        self.actionzijierecognmodel_api = QtGui.QAction()
        self.actionzijierecognmodel_api.setObjectName("actionzijierecognmodel_api")

        self.actiontts_gptsovits = QtGui.QAction()
        self.actiontts_gptsovits.setObjectName("actiontts_gptsovits")

        self.actiontts_chatterbox = QtGui.QAction()
        self.actiontts_chatterbox.setObjectName("actiontts_chatterbox")

        self.actiontts_cosyvoice = QtGui.QAction()
        self.actiontts_cosyvoice.setObjectName("actiontts_cosyvoice")
        self.actiontts_omnivoice = QtGui.QAction()
        self.actiontts_omnivoice.setObjectName("actiontts_omnivoice")
        self.actiontts_qwenttslocal = QtGui.QAction()
        self.actiontts_qwenttslocal.setObjectName("actiontts_qwenttslocal")
        self.actiontts_fishtts = QtGui.QAction()
        self.actiontts_fishtts.setObjectName("actiontts_fishtts")
        self.actiontts_f5tts = QtGui.QAction()
        self.actiontts_f5tts.setObjectName("actiontts_f5tts")
        self.actiontts_refaudio = QtGui.QAction()
        self.actiontts_refaudio.setObjectName("actiontts_refaudio")
        self.actiontts_doubao2 = QtGui.QAction()
        self.actiontts_doubao2.setObjectName("actiontts_doubao2")

        self.action_website = QtGui.QAction()
        self.action_website.setObjectName("action_website")
        self.action_blog = QtGui.QAction()
        self.action_blog.setObjectName("action_blog")
        self.action_discord = QtGui.QAction()
        self.action_discord.setObjectName("action_discord")

        self.action_gtrans = QtGui.QAction()
        self.action_gtrans.setObjectName("action_gtrans")
        self.action_cuda = QtGui.QAction()
        self.action_cuda.setObjectName("action_cuda")

        self.action_online = QtGui.QAction()
        self.action_online.setObjectName("action_online")

        self.actiontencent_key = QtGui.QAction()
        self.actiontencent_key.setObjectName("actiontencent_key")
        self.action_about = QtGui.QAction()
        self.action_about.setObjectName("action_about")

        self.action_biaozhun = QtGui.QAction()
        self.action_biaozhun.setCheckable(True)
        self.action_biaozhun.setChecked(True)
        self.action_biaozhun.setObjectName("action_biaozhun")

        self.action_yuyinshibie = QtGui.QAction()

        self.action_yuyinshibie.setObjectName("action_yuyinshibie")
        self.action_yuyinhecheng = QtGui.QAction()

        self.action_yuyinhecheng.setObjectName("action_yuyinhecheng")
        self.action_tiquzimu = QtGui.QAction()
        self.action_tiquzimu.setCheckable(True)

        self.action_tiquzimu.setObjectName("action_tiquzimu")

        self.action_yingyinhebing = QtGui.QAction()
        self.action_yingyinhebing.setObjectName("action_yingyinhebing")
        self.action_clipvideo = QtGui.QAction()
        self.action_clipvideo.setObjectName("action_clipvideo")

        self.action_realtime_stt = QtGui.QAction()
        self.action_realtime_stt.setObjectName("action_realtime_stt")

        self.action_textmatching = QtGui.QAction()
        self.action_textmatching.setObjectName("action_textmatching")
        self.action_textmatching.setObjectName("action_textmatching")

        self.action_hun = QtGui.QAction()
        self.action_hun.setObjectName("action_hun")

        self.action_fanyi = QtGui.QAction()
        self.action_fanyi.setObjectName("action_fanyi")
        self.action_hebingsrt = QtGui.QAction()
        self.action_hebingsrt.setObjectName("action_hebingsrt")

        self.action_clearcache = QtGui.QAction()
        self.action_clearcache.setObjectName("action_clearcache")
        self.action_set_proxy = QtGui.QAction()
        self.action_set_proxy.setObjectName("action_set_proxy")

        self.actionazure_key = QtGui.QAction()
        self.actionazure_key.setObjectName("actionazure_key")
        self.actiongemini_key = QtGui.QAction()
        self.actiongemini_key.setObjectName("actiongemini_key")
        self.actioncamb_key = QtGui.QAction()
        self.actioncamb_key.setObjectName("actioncamb_key")
        self.actionElevenlabs_key = QtGui.QAction()
        self.actionElevenlabs_key.setObjectName("actionElevenlabs_key")
        self.actionwatermark = QtGui.QAction()
        self.actionwatermark.setObjectName("actionwatermark")
        self.actionsepar = QtGui.QAction()
        self.actionsepar.setObjectName("actionsepar")
        self.actionsetini = QtGui.QAction()
        self.actionsetini.setObjectName("setini")
        self.actionvideoandaudio = QtGui.QAction()
        self.actionvideoandaudio.setObjectName("videoandaudio")
        self.actionvideoandaudio = QtGui.QAction()
        self.actionvideoandaudio.setObjectName("videoandaudio")
        self.actionvideoandsrt = QtGui.QAction()
        self.actionvideoandsrt.setObjectName("videoandsrt")
        self.actionformatcover = QtGui.QAction()
        self.actionformatcover.setObjectName("formatcover")
        self.actionsubtitlescover = QtGui.QAction()
        self.actionsubtitlescover.setObjectName("subtitlescover")
        self.actionsrtmultirole = QtGui.QAction()
        self.actionsrtmultirole.setObjectName("actionsrtmultirole")

        self.action_yinshipinfenli = QtGui.QAction()
        self.action_yinshipinfenli.setObjectName("action_yinshipinfenli")

        self.menu_Key.addAction(self.actionbaidu_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionali_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiontencent_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionai302_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionchatgpt_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionlocalllm_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionzhipuai_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionsiliconflow_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiondeepseek_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionxiaomi_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionminimax_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionqwenmt_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionopenrouter_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionlibretranslate_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionzijiehuoshan_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionazure_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiongemini_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actioncamb_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiondeepL_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiondeepLX_address)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionott_address)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiontrans_api)

        self.menu_Key.addSeparator()

        self.menu_TTS.addAction(self.actiontts_refaudio)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionclone_address)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionkokoro_address)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionchattts_address)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_gptsovits)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_omnivoice)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_cosyvoice)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_qwenttslocal)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionqwentts_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_fishtts)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_f5tts)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionai302_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_doubao2)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionElevenlabs_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionazure_tts)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionxaitts_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionopenaitts_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionminimaxi_api)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_api)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_chatterbox)
        self.menu_TTS.addSeparator()

        self.menu_RECOGN.addAction(self.actionzijierecognmodel_api)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actionopenairecognapi_key)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actionparakeet_key)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actionrecognapi)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actionai302_key)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actionsttapi)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actionwhisperx)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actiondeepgram)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actionxxl)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actioncpp)

        self.menu.addAction(self.actionsetini)
        self.menu.addSeparator()
        self.menu.addAction(self.action_clipvideo)
        self.menu.addSeparator()
        self.menu.addAction(self.actionwatermark)
        self.menu.addSeparator()
        self.menu.addAction(self.action_realtime_stt)
        self.menu.addSeparator()
        self.menu.addAction(self.action_textmatching)
        self.menu.addSeparator()
        self.menu.addAction(self.action_yingyinhebing)
        self.menu.addSeparator()
        self.menu.addAction(self.actionvideoandaudio)
        self.menu.addSeparator()
        self.menu.addAction(self.actionvideoandsrt)
        self.menu.addSeparator()
        self.menu.addAction(self.actionformatcover)
        self.menu.addSeparator()
        self.menu.addAction(self.actionsubtitlescover)
        self.menu.addSeparator()
        self.menu.addAction(self.actionsrtmultirole)
        self.menu.addSeparator()
        self.menu.addAction(self.action_yinshipinfenli)
        self.menu.addSeparator()
        self.menu.addAction(self.action_hun)
        self.menu.addSeparator()
        self.menu.addAction(self.action_hebingsrt)
        self.menu.addSeparator()
        self.menu.addAction(self.actionsepar)
        self.menu.addSeparator()
        self.menu.addAction(self.action_set_proxy)
        self.menu.addSeparator()

        self.menu.addAction(self.action_clearcache)
        self.menu.addSeparator()

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_website)

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_blog)

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_discord)



        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_gtrans)

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_cuda)

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_git)

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_issue)

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_ffmpeg)

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_online)
        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_about)
        self.menu_H.addSeparator()

        self.menuBar.addAction(self.menu_Key.menuAction())
        self.menuBar.addAction(self.menu_TTS.menuAction())
        self.menuBar.addAction(self.menu_RECOGN.menuAction())
        self.menuBar.addAction(self.menu.menuAction())
        self.menuBar.addAction(self.menu_H.menuAction())

        self.toolBar.addAction(self.action_biaozhun)
        self.toolBar.addAction(self.action_tiquzimu)

        self.toolBar.addAction(self.action_yuyinshibie)
        self.toolBar.addAction(self.action_fanyi)
        self.toolBar.addAction(self.action_yuyinhecheng)
        self.toolBar.addAction(self.actionsrtmultirole)

        self.toolBar.addAction(self.action_yingyinhebing)



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

        # 底部状态条
        self.statusLabel = QtWidgets.QPushButton(tr("Open Documents"))
        self.statusLabel.setStyleSheet("""color:#ffff66""")
        self.statusBar.addWidget(self.statusLabel)

        self.rightbottom = QtWidgets.QPushButton(tr('juanzhu'))

        self.container = QtWidgets.QToolBar()
        self.container.addWidget(self.rightbottom)
        self.restart_btn = QtWidgets.QPushButton(tr("Restart"))
        self.container.addWidget(self.restart_btn)
        self.statusBar.addPermanentWidget(self.container)

        # 设置显示文字和样式
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

        # 菜单
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
        self.actionxiaomi_key.setText("XiaoMi AI")
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
        self.actionott_address.setText(tr("OTT Api"))
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
        self.actiontts_omnivoice.setText("OmniVoice TTS")
        self.actiontts_qwenttslocal.setText(f"Qwen3 TTS({tr('Local')})")
        self.actiontts_fishtts.setText("Fish TTS")
        self.actiontts_f5tts.setText("F5/Index/VoxCPM/SparK/Dia/Confucius")
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
