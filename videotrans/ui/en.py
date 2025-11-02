from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy

from videotrans.configure import config
from videotrans.configure.config import tr,logs


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
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
        self.horizontalLayout_6.addWidget(self.btn_save_dir)


        self.copysrt_rawvideo = QtWidgets.QCheckBox(self.layoutWidget)
        self.copysrt_rawvideo.setMinimumSize(QtCore.QSize(0, 30))
        self.copysrt_rawvideo.setObjectName("copysrt_rawvideo")
        self.copysrt_rawvideo.setVisible(False)
        self.copysrt_rawvideo.setText(tr("Moving subtitle"))
        self.copysrt_rawvideo.setToolTip(
            tr("When this item is checked, and the target language is different from the language of the pronunciation will move the translated srt file to the original video location and rename it to the same name as the video."))

        self.shutdown = QtWidgets.QCheckBox(self.layoutWidget)
        self.shutdown.setMinimumSize(QtCore.QSize(50, 20))
        self.shutdown.setObjectName("shutdown")
        self.shutdown.setToolTip(
            tr("Automatic shutdown after completing all tasks"))
        self.shutdown.setText(tr("Automatic shutdown"))
        self.shutdown.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addWidget(self.copysrt_rawvideo)
        self.horizontalLayout_6.addWidget(self.shutdown)
        
        self.horizontalLayout_6.addStretch()
        # proxy
        proxy_layout=QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QPushButton(self.layoutWidget)
        self.label.setMinimumSize(QtCore.QSize(0, 30))
        self.label.setObjectName("label")
        self.label.setStyleSheet("""background-color:transparent""")

        self.proxy = QtWidgets.QLineEdit(self.layoutWidget)
        self.proxy.setMinimumSize(QtCore.QSize(0, 30))
        self.proxy.setObjectName("proxy")
        if config.defaulelang!='zh':
            self.label.hide()
            self.proxy.hide()
        
        proxy_layout.addWidget(self.label)
        proxy_layout.addWidget(self.proxy)        
        
        
        self.horizontalLayout_6.addLayout(proxy_layout)
        
        # proxy
        

        self.verticalLayout_3.addLayout(self.horizontalLayout_6)


        
        # 语音识别渠道行
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.reglabel = QtWidgets.QPushButton(self.layoutWidget)
        self.reglabel.setStyleSheet("""background-color:transparent""")

        self.reglabel.setText(tr("Speech Recognit"))
        self.reglabel.setCursor(Qt.PointingHandCursor)
        self.reglabel.setToolTip(
            tr("Click to set detailed recognition parameters when using faster-whisper"))
        self.recogn_type = QtWidgets.QComboBox(self.layoutWidget)
        self.recogn_type.setMinimumSize(QtCore.QSize(160, 30))
        self.recogn_type.setObjectName("label_5")

        self.recogn_type.setToolTip(tr('model_type_tips'))

        self.model_name_help = QtWidgets.QPushButton(self.layoutWidget)
        self.model_name_help.setStyleSheet("""background-color:transparent""")
        self.model_name_help.setText(tr("Model"))
        self.model_name_help.setToolTip(tr("Click for model description"))
        self.model_name_help.setMinimumSize(QtCore.QSize(0, 30))

        self.model_name = QtWidgets.QComboBox(self.layoutWidget)
        self.model_name.setMinimumSize(QtCore.QSize(160, 30))
        self.model_name.setMaximumWidth(160)
        self.model_name.setObjectName("model_name")



        self.split_label = QtWidgets.QPushButton()
        self.split_label.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        self.split_label.setObjectName("split_label")
        self.split_label.setCursor(Qt.PointingHandCursor)
        self.split_label.setToolTip(
            tr("Click for detailed description"))
        self.split_label.setText(tr("Speech Split"))

        self.split_type = QtWidgets.QComboBox(self.layoutWidget)
        self.split_type.setMinimumSize(QtCore.QSize(80, 30))
        self.split_type.setObjectName("split_type")

        self.equal_split_time = QtWidgets.QLineEdit()
        self.equal_split_time.setToolTip(
            tr("Duration of each segment/second"))
        self.equal_split_time.setText(str(config.settings.get('interval_split', 10)))
        self.equal_split_time_label = QtWidgets.QLabel()
        self.equal_split_time_label.setText(tr("Sec"))
        self.equal_split_time.setVisible(False)
        self.equal_split_time_label.setVisible(False)

        self.equal_split_layout = QtWidgets.QHBoxLayout()
        self.equal_split_layout.addWidget(self.equal_split_time)
        self.equal_split_layout.addWidget(self.equal_split_time_label)

        self.rephrase = QtWidgets.QCheckBox()
        self.rephrase.setText(tr("LLM Rephrase"))
        self.rephrase.setToolTip(
            tr("When selecting the faster/openai-whisper channel, the large model will be used to re-segment the sentence. If it fails, the original segmentation will be used."))
        
        self.rephrase_local = QtWidgets.QCheckBox()
        self.rephrase_local.setText(tr("Rephrase Local"))
        self.rephrase_local.setToolTip(
            tr("When selecting the faster/openai-whisper channel, the local algorithm will be used to re-segment the sentence"))
        
        
        self.remove_noise = QtWidgets.QCheckBox()
        self.remove_noise.setText(tr("Noise reduction"))
        self.remove_noise.setToolTip(
            tr("Select to perform noise reduction processing from modelscope.cn, which takes a long time"))

        self.horizontalLayout_4.addWidget(self.reglabel)
        self.horizontalLayout_4.addWidget(self.recogn_type)
        self.horizontalLayout_4.addWidget(self.model_name_help)
        self.horizontalLayout_4.addWidget(self.model_name)
        
        self.horizontalLayout_4.addWidget(self.split_label)
        self.horizontalLayout_4.addWidget(self.split_type)
        self.horizontalLayout_4.addLayout(self.equal_split_layout)
        self.horizontalLayout_4.addStretch()
        self.horizontalLayout_4.addWidget(self.rephrase)
        self.horizontalLayout_4.addWidget(self.rephrase_local)
        self.horizontalLayout_4.addWidget(self.remove_noise)
        self.verticalLayout_3.addLayout(self.horizontalLayout_4)

        
        # 语音识别精细调整行
        self.hfaster_layout = QtWidgets.QHBoxLayout()
        self.hfaster_help = QtWidgets.QPushButton()
        self.hfaster_help.setText(tr("Help"))
        self.hfaster_help.setToolTip(tr("Click to open help page"))
        self.hfaster_help.setStyleSheet("background-color:transparent;color:#999999")
        self.hfaster_help.setCursor(Qt.PointingHandCursor)
        self.hfaster_help.setVisible(False)

        self.threshold_label = QtWidgets.QLabel()
        self.threshold_label.setText(tr("threshold"))
        self.threshold_label.setVisible(False)
        self.threshold = QtWidgets.QLineEdit()
        self.threshold.setPlaceholderText('200ms')
        self.threshold.setMaximumWidth(80)
        self.threshold.setVisible(False)
        self.threshold.setToolTip(
            tr("Threshold for speech detection"))
        self.threshold.setText(str(config.settings.get('threshold', 0.5)))
        self.hfaster_layout.addWidget(self.hfaster_help)
        self.hfaster_layout.addWidget(self.threshold_label)
        self.hfaster_layout.addWidget(self.threshold)

        self.min_speech_duration_ms_label = QtWidgets.QLabel()
        self.min_speech_duration_ms_label.setText(
            tr("min_speech_duration_ms"))
        self.min_speech_duration_ms_label.setVisible(False)
        self.min_speech_duration_ms = QtWidgets.QLineEdit()
        self.min_speech_duration_ms.setPlaceholderText('200ms')
        self.min_speech_duration_ms.setMaximumWidth(80)
        self.min_speech_duration_ms.setVisible(False)
        self.min_speech_duration_ms.setText(str(config.settings.get('min_speech_duration_ms', 1000)))
        self.min_speech_duration_ms.setToolTip(
            tr("Minimum speech duration (ms)"))
        self.hfaster_layout.addWidget(self.min_speech_duration_ms_label)
        self.hfaster_layout.addWidget(self.min_speech_duration_ms)

        self.min_silence_duration_ms_label = QtWidgets.QLabel()
        self.min_silence_duration_ms_label.setText(
            tr("min_silence_duration_ms"))
        self.min_silence_duration_ms_label.setVisible(False)
        self.min_silence_duration_ms = QtWidgets.QLineEdit()
        self.min_silence_duration_ms.setPlaceholderText('250ms')
        self.min_silence_duration_ms.setMaximumWidth(80)
        self.min_silence_duration_ms.setVisible(False)
        self.min_silence_duration_ms.setText(str(config.settings.get('min_silence_duration_ms', 250)))
        self.min_silence_duration_ms.setToolTip(
            tr("Minimum silence duration (ms)"))
        self.hfaster_layout.addWidget(self.min_silence_duration_ms_label)
        self.hfaster_layout.addWidget(self.min_silence_duration_ms)

        self.max_speech_duration_s_label = QtWidgets.QLabel()
        self.max_speech_duration_s_label.setText(tr("max_speech_duration_s"))
        self.max_speech_duration_s_label.setVisible(False)
        self.max_speech_duration_s = QtWidgets.QLineEdit()
        self.max_speech_duration_s.setMaximumWidth(80)
        self.max_speech_duration_s.setVisible(False)
        self.max_speech_duration_s.setText(str(config.settings.get('max_speech_duration_s', 8)))
        self.max_speech_duration_s.setToolTip(
            tr("max speech duration (s)"))
        self.hfaster_layout.addWidget(self.max_speech_duration_s_label)
        self.hfaster_layout.addWidget(self.max_speech_duration_s)

        self.speech_pad_ms_label = QtWidgets.QLabel()
        self.speech_pad_ms_label.setText(tr("speech_pad_ms"))
        self.speech_pad_ms_label.setVisible(False)
        self.speech_pad_ms = QtWidgets.QLineEdit()
        self.speech_pad_ms.setPlaceholderText('200ms')
        self.speech_pad_ms.setMaximumWidth(80)
        self.speech_pad_ms.setVisible(False)
        self.speech_pad_ms.setToolTip(
            tr("Speech padding (ms)"))
        self.speech_pad_ms.setText(str(config.settings.get('speech_pad_ms', 400)))
        self.hfaster_layout.addWidget(self.speech_pad_ms_label)
        self.hfaster_layout.addWidget(self.speech_pad_ms)

        self.verticalLayout_3.addLayout(self.hfaster_layout)
        
        
        
        # 翻译渠道行
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")

        self.label_9 = QtWidgets.QPushButton(self.layoutWidget)
        self.label_9.setMinimumSize(QtCore.QSize(0, 30))
        self.label_9.setObjectName("label_9")
        self.label_9.setStyleSheet("""background-color:transparent""")
        self.label_9.setToolTip(
            tr("Click to set the number of subtitles to be translated at the same time"))

        self.translate_type = QtWidgets.QComboBox(self.layoutWidget)
        self.translate_type.setMinimumSize(QtCore.QSize(160, 30))
        self.translate_type.setObjectName("translate_type")
        self.translate_type.setToolTip(
            tr("Select the channel used to translate text"))

        self.horizontalLayout_5.addWidget(self.label_9)
        self.horizontalLayout_5.addWidget(self.translate_type)

        # 原始语言 目标语言 start
        self.label_2 = QtWidgets.QPushButton(self.layoutWidget)
        self.label_2.setMinimumSize(QtCore.QSize(0, 30))
        self.label_2.setStyleSheet("""background-color:transparent""")
        self.label_2.setObjectName("label_2")
        self.source_language = QtWidgets.QComboBox(self.layoutWidget)
        self.source_language.setMinimumSize(QtCore.QSize(160, 30))
        self.source_language.setObjectName("source_language")

        self.label_3 = QtWidgets.QPushButton(self.layoutWidget)
        self.label_3.setMinimumSize(QtCore.QSize(0, 30))
        self.label_3.setObjectName("label_3")
        self.label_3.setStyleSheet("""background-color:transparent""")
        self.target_language = QtWidgets.QComboBox(self.layoutWidget)
        #self.target_language.setMinimumSize(QtCore.QSize(100, 30))
        self.target_language.setObjectName("target_language")

        self.horizontalLayout_5.addWidget(self.label_2)
        self.horizontalLayout_5.addWidget(self.source_language)
        self.horizontalLayout_5.addWidget(self.label_3)
        self.horizontalLayout_5.addWidget(self.target_language)
        self.horizontalLayout_5.addStretch()

        self.glossary = QtWidgets.QPushButton(self.layoutWidget)
        self.glossary.setMinimumSize(QtCore.QSize(0, 30))
        self.glossary.setObjectName("glossary")
        self.glossary.setText(tr("glossary"))
        self.glossary.setStyleSheet("""background-color:transparent""")
        self.glossary.setCursor(Qt.PointingHandCursor)
        self.glossary.setToolTip(
            tr("Click to set up and modify the glossary"))
        
        

        
        self.aisendsrt = QtWidgets.QCheckBox()
        self.aisendsrt.setText(tr("Send SRT"))
        self.aisendsrt.setToolTip(
            tr("When using AI translation channel, you can translate in srt format, but there may be more empty lines"))
        self.aisendsrt.setChecked(config.settings.get('aisendsrt'))

        self.horizontalLayout_5.addWidget(self.glossary)
        self.horizontalLayout_5.addWidget(self.aisendsrt)
        

        self.listen_btn = QtWidgets.QPushButton(self.layoutWidget)
        self.listen_btn.setEnabled(False)
        self.listen_btn.setStyleSheet("""background-color:transparent""")
        self.verticalLayout_3.addLayout(self.horizontalLayout_5)

        # 配音渠道行
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.tts_text = QtWidgets.QPushButton(self.layoutWidget)
        self.tts_text.setObjectName("tts_text")
        self.tts_text.setMinimumSize(QtCore.QSize(0, 30))
        self.tts_text.setStyleSheet("""background-color:transparent""")
        self.tts_text.setToolTip(
            tr("Click to set the number of threads to be used for dubbing"))
        self.tts_type = QtWidgets.QComboBox(self.layoutWidget)
        self.tts_type.setMinimumSize(QtCore.QSize(160, 30))
        self.tts_type.setObjectName("tts_type")

        self.tts_type.setToolTip(tr("Select the channel used to dub"))
        self.horizontalLayout.addWidget(self.tts_text)
        self.horizontalLayout.addWidget(self.tts_type)

        self.label_4 = QtWidgets.QPushButton(self.layoutWidget)
        self.label_4.setMinimumSize(QtCore.QSize(0, 30))
        self.label_4.setObjectName("label_4")
        self.label_4.setStyleSheet("background-color:transparent")
        self.voice_role = QtWidgets.QComboBox(self.layoutWidget)
        self.voice_role.setMinimumSize(QtCore.QSize(160, 30))
        self.voice_role.setMaximumWidth(160)
        self.voice_role.setObjectName("voice_role")

        self.horizontalLayout.addWidget(self.label_4)
        self.horizontalLayout.addWidget(self.voice_role)
        self.horizontalLayout.addWidget(self.listen_btn)
        self.horizontalLayout.addStretch()

        self.label_6 = QtWidgets.QLabel(self.layoutWidget)

        self.label_6.setObjectName("label_6")

        self.voice_rate = QtWidgets.QSpinBox(self.layoutWidget)
        self.voice_rate.setMinimum(-50)
        self.voice_rate.setMaximum(50)
        self.voice_rate.setMinimumWidth(80)
        self.voice_rate.setObjectName("voice_rate")

        self.volume_label = QtWidgets.QLabel(self.layoutWidget)
        self.volume_label.setText(tr("Volume+"))
        self.volume_rate = QtWidgets.QSpinBox(self.layoutWidget)
        self.volume_rate.setMinimum(-95)
        self.volume_rate.setToolTip(tr("Percentage of volume adjustment"))
        self.volume_rate.setMaximum(100)
        self.volume_rate.setMinimumWidth(80)
        self.volume_rate.setObjectName("volume_rate")


        self.pitch_label = QtWidgets.QLabel(self.layoutWidget)
        self.pitch_label.setText(tr("Pitch+"))
        self.pitch_rate = QtWidgets.QSpinBox(self.layoutWidget)
        self.pitch_rate.setMinimum(-100)
        self.pitch_rate.setMaximum(100)
        self.pitch_rate.setMinimumWidth(80)
        self.pitch_rate.setObjectName("pitch_rate")


        self.horizontalLayout.addWidget(self.label_6)
        self.horizontalLayout.addWidget(self.voice_rate)
        self.horizontalLayout.addWidget(self.volume_label)
        self.horizontalLayout.addWidget(self.volume_rate)
        self.horizontalLayout.addWidget(self.pitch_label)
        self.horizontalLayout.addWidget(self.pitch_rate)

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        
        # 对齐行
        self.gaoji_layout_inner = QtWidgets.QHBoxLayout()
        self.gaoji_layout_inner.setObjectName("gaoji_layout_inner")

        self.align_btn = QtWidgets.QPushButton()

        self.align_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        self.align_btn.setObjectName("align_btn")
        self.align_btn.setCursor(Qt.PointingHandCursor)
        self.align_btn.setText(tr("Alignment control"))
        self.align_btn.setToolTip(tr("View alignment tutorial"))
        self.gaoji_layout_inner.addWidget(self.align_btn)

        self.voice_autorate = QtWidgets.QCheckBox(self.layoutWidget)
        self.voice_autorate.setObjectName("voice_autorate")

        self.video_autorate = QtWidgets.QCheckBox(self.layoutWidget)
        self.video_autorate.setObjectName("videoe_autorate")

        self.subtitle_type = QtWidgets.QComboBox(self.layoutWidget)
        self.subtitle_type.setMinimumSize(QtCore.QSize(100, 30))
        self.subtitle_type.setObjectName("subtitle_type")

        self.label_cjklinenums = QtWidgets.QLabel(self.layoutWidget)
        self.label_cjklinenums.setObjectName("label_cjklinenums")
        self.label_cjklinenums.setText(
            tr("Line length"))

        self.cjklinenums = QtWidgets.QSpinBox(self.layoutWidget)

        self.cjklinenums.setMinimum(5)
        self.cjklinenums.setMaximum(100)
        self.cjklinenums.setMinimumWidth(90)
        self.cjklinenums.setToolTip(
            tr("Chinese/Japanese/Korean line length"))
        self.cjklinenums.setObjectName("cjklinenums")
        self.cjklinenums.setValue(int(config.settings.get('cjk_len', 20)))

        self.label_othlinenums = QtWidgets.QLabel(self.layoutWidget)
        self.label_othlinenums.setObjectName("label_othlinenums")
        self.label_othlinenums.setText(
            tr("Ohter Line length"))

        self.othlinenums = QtWidgets.QSpinBox(self.layoutWidget)
        self.othlinenums.setMinimum(5)
        self.othlinenums.setMinimumWidth(90)
        self.othlinenums.setMaximum(100)
        self.othlinenums.setToolTip(
            tr("Number of characters per line for subtitles in other languages"))
        self.othlinenums.setObjectName("othlinenums")
        self.othlinenums.setValue(int(config.settings.get('other_len', 60)))

        self.gaoji_layout_inner.addWidget(self.voice_autorate)
        self.gaoji_layout_inner.addWidget(self.video_autorate)
        
        self.subtitle_label=QtWidgets.QLabel(tr('How embed subtitles'))
        self.gaoji_layout_inner.addWidget(self.subtitle_label)
        self.gaoji_layout_inner.addWidget(self.subtitle_type)
        
        self.set_ass=QtWidgets.QPushButton()
        self.set_ass.setStyleSheet("background-color:transparent;border:0")
        self.set_ass.setText(tr('Modify hard subtitle style'))
        self.set_ass.setCursor(Qt.PointingHandCursor)
        self.gaoji_layout_inner.addWidget(self.set_ass)
        
        self.gaoji_layout_inner.addStretch()
        
        self.gaoji_layout_inner.addWidget(self.label_cjklinenums)
        self.gaoji_layout_inner.addWidget(self.cjklinenums)
        self.gaoji_layout_inner.addWidget(self.label_othlinenums)
        self.gaoji_layout_inner.addWidget(self.othlinenums)
        self.verticalLayout_3.addLayout(self.gaoji_layout_inner)
        
        # 背景行
        self.gaoji_layout_inner2 = QtWidgets.QHBoxLayout()
        self.gaoji_layout_inner2.setObjectName("gaoji_layout_inner2")

        self.is_separate = QtWidgets.QCheckBox(self.layoutWidget)
        self.is_separate.setMinimumSize(QtCore.QSize(0, 30))
        self.is_separate.setObjectName("is_separate")

        self.addbackbtn = QtWidgets.QPushButton(self.layoutWidget)
        self.addbackbtn.setObjectName("addbackbtn")

        self.back_audio = QtWidgets.QLineEdit(self.layoutWidget)
        self.back_audio.setObjectName("back_audio")

        # 是否循环播放背景
        self.is_loop_bgm = QtWidgets.QCheckBox(self.layoutWidget)
        self.is_loop_bgm.setChecked(True)
        self.is_loop_bgm.setText(tr("loop the BGM"))
        self.is_loop_bgm.setToolTip(
            tr("Whether to loop the background music when the duration is insufficient"))

        self.bgmvolume_label = QtWidgets.QLabel()
        self.bgmvolume_label.setText(tr("Volume BGM"))
        self.bgmvolume = QtWidgets.QLineEdit()
        self.bgmvolume.setText('0.8')
        self.bgmvolume.setMaximumWidth(80)
        self.bgmvolume.setToolTip(
            tr("BGM volume is a multiple of the original volume, greater than 1 increases, less than decreases"))

        self.gaoji_layout_inner2.addWidget(self.is_separate)
        self.gaoji_layout_inner2.addWidget(self.is_loop_bgm)
        self.gaoji_layout_inner2.addWidget(self.bgmvolume_label)
        self.gaoji_layout_inner2.addWidget(self.bgmvolume)
        self.gaoji_layout_inner2.addStretch()
        
        self.gaoji_layout_inner2.addWidget(self.addbackbtn)
        self.gaoji_layout_inner2.addWidget(self.back_audio)
        self.verticalLayout_3.addLayout(self.gaoji_layout_inner2)
        
        
        
        # 简短提示行
        self.show_tips = QtWidgets.QPushButton(self.layoutWidget)
        self.show_tips.setStyleSheet(
            """background-color:transparent;border-color:transparent;color:#aaaaaa;text-align:left""")
        self.show_tips.setObjectName("show_tips")
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


        self.horizontalLayout_3.addStretch(1)
        self.horizontalLayout_3.addWidget(self.enable_cuda)
        self.horizontalLayout_3.addWidget(self.startbtn)
        self.horizontalLayout_3.addStretch(1)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)


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

        self.statusBar = QtWidgets.QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)
        self.menuBar = QtWidgets.QMenuBar(MainWindow)

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
        self.toolBar = QtWidgets.QToolBar(MainWindow)
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
        #if config.defaulelang == 'zh':
        MainWindow.addToolBar(QtCore.Qt.LeftToolBarArea, self.toolBar)
        #else:
        #    # 工具条放在顶部
        #    MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.actionbaidu_key = QtGui.QAction(MainWindow)
        self.actionbaidu_key.setObjectName("actionbaidu_key")
        self.actionali_key = QtGui.QAction(MainWindow)
        self.actionali_key.setObjectName("actionali_key")

        self.actionchatgpt_key = QtGui.QAction(MainWindow)
        self.actionchatgpt_key.setObjectName("actionchatgpt_key")
        self.actionzhipuai_key = QtGui.QAction(MainWindow)
        self.actionzhipuai_key.setObjectName("actionzhipuai_key")
        self.actionsiliconflow_key = QtGui.QAction(MainWindow)
        self.actionsiliconflow_key.setObjectName("actionsiliconflow_key")
        self.actiondeepseek_key = QtGui.QAction(MainWindow)
        self.actiondeepseek_key.setObjectName("actiondeepseek_key")
        self.actionqwenmt_key = QtGui.QAction(MainWindow)
        self.actionqwenmt_key.setObjectName("actionqwenmt_key")
        self.actionopenrouter_key = QtGui.QAction(MainWindow)
        self.actionopenrouter_key.setObjectName("actionopenrouter_key")

        self.actionclaude_key = QtGui.QAction(MainWindow)
        self.actionclaude_key.setObjectName("actionclaude_key")
        self.actionlibretranslate_key = QtGui.QAction(MainWindow)
        self.actionlibretranslate_key.setObjectName("actionlibretranslate_key")
        self.actionopenaitts_key = QtGui.QAction(MainWindow)
        self.actionopenaitts_key.setObjectName("actionopenaitts_key")
        self.actionqwentts_key = QtGui.QAction(MainWindow)
        self.actionqwentts_key.setObjectName("actionqwentts_key")
        self.actionopenairecognapi_key = QtGui.QAction(MainWindow)
        self.actionopenairecognapi_key.setObjectName("actionopenairecognapi_key")
        self.actionparakeet_key = QtGui.QAction(MainWindow)
        self.actionparakeet_key.setObjectName("actionparakeet_key")
        self.actionai302_key = QtGui.QAction(MainWindow)
        self.actionai302_key.setObjectName("actionai302_key")
        self.actionlocalllm_key = QtGui.QAction(MainWindow)
        self.actionlocalllm_key.setObjectName("actionlocalllm_key")
        self.actionzijiehuoshan_key = QtGui.QAction(MainWindow)
        self.actionzijiehuoshan_key.setObjectName("actionzijiehuoshan_key")
        self.actiondeepL_key = QtGui.QAction(MainWindow)
        self.actiondeepL_key.setObjectName("actiondeepL_key")

        self.actionazure_tts = QtGui.QAction(MainWindow)
        self.actionazure_tts.setObjectName("actionazure_tts")

        self.action_ffmpeg = QtGui.QAction(MainWindow)
        self.action_ffmpeg.setObjectName("action_ffmpeg")
        self.action_git = QtGui.QAction(MainWindow)
        self.action_git.setObjectName("action_git")
        self.action_issue = QtGui.QAction(MainWindow)
        self.action_issue.setObjectName("action_issue")
        self.actiondeepLX_address = QtGui.QAction(MainWindow)
        self.actiondeepLX_address.setObjectName("actiondeepLX_address")
        self.actionott_address = QtGui.QAction(MainWindow)
        self.actionott_address.setObjectName("actionott_address")

        self.actionclone_address = QtGui.QAction(MainWindow)
        self.actionclone_address.setObjectName("actionclone_address")
        self.actionkokoro_address = QtGui.QAction(MainWindow)
        self.actionkokoro_address.setObjectName("actionkokoro_address")
        self.actionchattts_address = QtGui.QAction(MainWindow)
        self.actionchattts_address.setObjectName("actionchattts_address")

        self.actiontts_api = QtGui.QAction(MainWindow)
        self.actiontts_api.setObjectName("actiontts_api")

        self.actionminimaxi_api = QtGui.QAction(MainWindow)
        self.actionminimaxi_api.setObjectName("actionminimaxi_api")

        self.actiontrans_api = QtGui.QAction(MainWindow)
        self.actiontrans_api.setObjectName("actiontrans_api")
        self.actionrecognapi = QtGui.QAction(MainWindow)
        self.actionrecognapi.setObjectName("actionrecognapi")
        self.actionsttapi = QtGui.QAction(MainWindow)
        self.actionsttapi.setObjectName("actionsttapi")
        self.actiondeepgram = QtGui.QAction(MainWindow)
        self.actiondeepgram.setObjectName("actiondeepgram")
        self.actionxxl = QtGui.QAction(MainWindow)
        self.actionxxl.setObjectName("actionxxl")
        self.actioncpp = QtGui.QAction(MainWindow)
        self.actioncpp.setObjectName("actioncpp")

        self.actiondoubao_api = QtGui.QAction(MainWindow)
        self.actiondoubao_api.setObjectName("actiondoubao_api")

        self.actionzijierecognmodel_api = QtGui.QAction(MainWindow)
        self.actionzijierecognmodel_api.setObjectName("actionzijierecognmodel_api")

        self.actiontts_gptsovits = QtGui.QAction(MainWindow)
        self.actiontts_gptsovits.setObjectName("actiontts_gptsovits")

        self.actiontts_chatterbox = QtGui.QAction(MainWindow)
        self.actiontts_chatterbox.setObjectName("actiontts_chatterbox")

        self.actiontts_cosyvoice = QtGui.QAction(MainWindow)
        self.actiontts_cosyvoice.setObjectName("actiontts_cosyvoice")
        self.actiontts_fishtts = QtGui.QAction(MainWindow)
        self.actiontts_fishtts.setObjectName("actiontts_fishtts")
        self.actiontts_f5tts = QtGui.QAction(MainWindow)
        self.actiontts_f5tts.setObjectName("actiontts_f5tts")
        self.actiontts_volcengine = QtGui.QAction(MainWindow)
        self.actiontts_volcengine.setObjectName("actiontts_volcengine")
        self.actiontts_doubao2 = QtGui.QAction(MainWindow)
        self.actiontts_doubao2.setObjectName("actiontts_doubao2")

        self.action_website = QtGui.QAction(MainWindow)
        self.action_website.setObjectName("action_website")
        self.action_blog = QtGui.QAction(MainWindow)
        self.action_blog.setObjectName("action_blog")
        self.action_discord = QtGui.QAction(MainWindow)
        self.action_discord.setObjectName("action_discord")
        self.action_models = QtGui.QAction(MainWindow)
        self.action_models.setObjectName("action_models")

        self.action_gtrans = QtGui.QAction(MainWindow)
        self.action_gtrans.setObjectName("action_gtrans")
        self.action_cuda = QtGui.QAction(MainWindow)
        self.action_cuda.setObjectName("action_cuda")

        self.action_online = QtGui.QAction(MainWindow)
        self.action_online.setObjectName("action_online")

        self.actiontencent_key = QtGui.QAction(MainWindow)
        self.actiontencent_key.setObjectName("actiontencent_key")
        self.action_about = QtGui.QAction(MainWindow)
        self.action_about.setObjectName("action_about")

        self.action_biaozhun = QtGui.QAction(MainWindow)
        self.action_biaozhun.setCheckable(True)
        self.action_biaozhun.setChecked(True)
        self.action_biaozhun.setObjectName("action_biaozhun")

        self.action_yuyinshibie = QtGui.QAction(MainWindow)

        self.action_yuyinshibie.setObjectName("action_yuyinshibie")
        self.action_yuyinhecheng = QtGui.QAction(MainWindow)

        self.action_yuyinhecheng.setObjectName("action_yuyinhecheng")
        self.action_tiquzimu = QtGui.QAction(MainWindow)
        self.action_tiquzimu.setCheckable(True)

        self.action_tiquzimu.setObjectName("action_tiquzimu")

        self.action_yingyinhebing = QtGui.QAction(MainWindow)
        self.action_yingyinhebing.setObjectName("action_yingyinhebing")
        self.action_clipvideo = QtGui.QAction(MainWindow)
        self.action_clipvideo.setObjectName("action_clipvideo")


        self.action_hun = QtGui.QAction(MainWindow)
        self.action_hun.setObjectName("action_hun")

        self.action_fanyi = QtGui.QAction(MainWindow)
        self.action_fanyi.setObjectName("action_fanyi")
        self.action_hebingsrt = QtGui.QAction(MainWindow)
        self.action_hebingsrt.setObjectName("action_hebingsrt")

        self.action_clearcache = QtGui.QAction(MainWindow)
        self.action_clearcache.setObjectName("action_clearcache")
        self.action_set_proxy = QtGui.QAction(MainWindow)
        self.action_set_proxy.setObjectName("action_set_proxy")

        self.actionazure_key = QtGui.QAction(MainWindow)
        self.actionazure_key.setObjectName("actionazure_key")
        self.actiongemini_key = QtGui.QAction(MainWindow)
        self.actiongemini_key.setObjectName("actiongemini_key")
        self.actionElevenlabs_key = QtGui.QAction(MainWindow)
        self.actionElevenlabs_key.setObjectName("actionElevenlabs_key")
        self.actionwatermark = QtGui.QAction(MainWindow)
        self.actionwatermark.setObjectName("actionwatermark")
        self.actionsepar = QtGui.QAction(MainWindow)
        self.actionsepar.setObjectName("actionsepar")
        self.actionsetini = QtGui.QAction(MainWindow)
        self.actionsetini.setObjectName("setini")
        self.actionvideoandaudio = QtGui.QAction(MainWindow)
        self.actionvideoandaudio.setObjectName("videoandaudio")
        self.actionvideoandaudio = QtGui.QAction(MainWindow)
        self.actionvideoandaudio.setObjectName("videoandaudio")
        self.actionvideoandsrt = QtGui.QAction(MainWindow)
        self.actionvideoandsrt.setObjectName("videoandsrt")
        self.actionformatcover = QtGui.QAction(MainWindow)
        self.actionformatcover.setObjectName("formatcover")
        self.actionsubtitlescover = QtGui.QAction(MainWindow)
        self.actionsubtitlescover.setObjectName("subtitlescover")
        self.actionsrtmultirole = QtGui.QAction(MainWindow)
        self.actionsrtmultirole.setObjectName("actionsrtmultirole")

        self.action_yinshipinfenli = QtGui.QAction(MainWindow)
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
        self.menu_Key.addAction(self.actionqwenmt_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionopenrouter_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionclaude_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionlibretranslate_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionzijiehuoshan_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionazure_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiongemini_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiondeepL_key)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiondeepLX_address)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actionott_address)
        self.menu_Key.addSeparator()
        self.menu_Key.addAction(self.actiontrans_api)

        self.menu_Key.addSeparator()

        self.menu_TTS.addAction(self.actionclone_address)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionkokoro_address)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionchattts_address)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_gptsovits)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_cosyvoice)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_fishtts)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_f5tts)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionai302_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_doubao2)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_volcengine)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionElevenlabs_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionazure_tts)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionopenaitts_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionqwentts_key)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actionminimaxi_api)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_api)
        self.menu_TTS.addSeparator()
        self.menu_TTS.addAction(self.actiontts_chatterbox)
        self.menu_TTS.addSeparator()

        self.menu_RECOGN.addAction(self.actiondoubao_api)
        self.menu_RECOGN.addSeparator()
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
        self.menu_RECOGN.addAction(self.actiondeepgram)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actionxxl)
        self.menu_RECOGN.addSeparator()
        self.menu_RECOGN.addAction(self.actioncpp)

        self.menu.addAction(self.actionsetini)
        self.menu.addSeparator()
        self.menu.addAction(self.actionwatermark)
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
        self.menu_H.addAction(self.action_about)

        self.menu_H.addSeparator()
        self.menu_H.addAction(self.action_models)

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
        self.toolBar.addAction(self.actionsubtitlescover)

        self.toolBar.addAction(self.action_yingyinhebing)
        self.toolBar.addAction(self.action_clipvideo)
