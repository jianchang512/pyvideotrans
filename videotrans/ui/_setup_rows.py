from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy

from videotrans.configure.config import tr, settings

_channel_com = 200


def _create_file_row(ui, parent):
    layout = QtWidgets.QHBoxLayout()
    layout.setObjectName("horizontalLayout_6")

    ui.btn_get_video = QtWidgets.QPushButton(parent)
    ui.btn_get_video.setMinimumSize(QtCore.QSize(120, 30))
    ui.btn_get_video.setObjectName("btn_get_video")

    ui.source_mp4 = QtWidgets.QLabel('')
    ui.source_mp4.setMaximumWidth(100)
    ui.source_mp4.setObjectName("source_mp4")

    ui.clear_cache = QtWidgets.QCheckBox(parent)
    ui.clear_cache.setMinimumSize(QtCore.QSize(50, 20))
    ui.clear_cache.setObjectName("clear_cache")
    ui.clear_cache.setToolTip(
        tr("Cleaning up files that have been processed in previous executions, such as recognized or translated subtitle files"))
    ui.clear_cache.setText(tr("Del Generated"))
    ui.clear_cache.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

    ui.select_file_type = QtWidgets.QCheckBox()
    ui.select_file_type.setText(tr("Folder"))
    ui.select_file_type.setToolTip(
        tr("Multiple files can be selected by default, check the box to select folders"))

    layout.addWidget(ui.btn_get_video)
    layout.addWidget(ui.select_file_type)
    layout.addWidget(ui.clear_cache)
    layout.addWidget(ui.source_mp4)

    ui.btn_save_dir = QtWidgets.QPushButton()
    ui.btn_save_dir.setMinimumSize(QtCore.QSize(120, 30))
    ui.btn_save_dir.setObjectName("btn_save_dir")

    ui.copysrt_rawvideo = QtWidgets.QCheckBox(parent)
    ui.copysrt_rawvideo.setMinimumSize(QtCore.QSize(0, 30))
    ui.copysrt_rawvideo.setObjectName("copysrt_rawvideo")
    ui.copysrt_rawvideo.setVisible(False)
    ui.copysrt_rawvideo.setText(tr("Moving subtitle"))
    ui.copysrt_rawvideo.setToolTip(
        tr("When this item is checked, and the target language is different from the language of the pronunciation will move the translated srt file to the original video location and rename it to the same name as the video."))

    ui.only_out_mp4 = QtWidgets.QCheckBox()
    ui.only_out_mp4.setText(tr('Output only mp4'))
    ui.only_out_mp4.setToolTip(tr('only_out_mp4'))

    ui.shutdown = QtWidgets.QCheckBox()
    ui.shutdown.setObjectName("shutdown")
    ui.shutdown.setToolTip(
        tr("Automatic shutdown after completing all tasks"))
    ui.shutdown.setText(tr("Automatic shutdown"))
    ui.shutdown.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    layout.addStretch()
    layout.addWidget(ui.btn_save_dir)
    layout.addWidget(ui.copysrt_rawvideo)
    layout.addWidget(ui.only_out_mp4)
    layout.addWidget(ui.shutdown)
    return layout


def _create_asr_row(ui, parent):
    layout = QtWidgets.QHBoxLayout()
    layout.setObjectName("horizontalLayout_4")
    ui.reglabel = QtWidgets.QLabel(parent)
    ui.reglabel.setStyleSheet("""background-color:transparent""")

    ui.reglabel.setText(tr("Speech Recognit"))
    ui.reglabel.setToolTip(
        tr("Click to set detailed recognition parameters when using faster-whisper"))
    ui.recogn_type = QtWidgets.QComboBox(parent)
    ui.recogn_type.setMinimumSize(QtCore.QSize(_channel_com, 30))
    ui.recogn_type.setObjectName("label_5")
    ui.recogn_type.setToolTip(tr('model_type_tips'))

    ui.model_name_help = QtWidgets.QLabel(parent)
    ui.model_name_help.setText(tr("ASRModel"))

    ui.model_name = QtWidgets.QComboBox(parent)
    ui.model_name.setMinimumWidth(250)
    ui.model_name.setObjectName("model_name")

    ui.rephrase = QtWidgets.QComboBox()
    ui.rephrase.addItems([tr("Default sentence"), tr("LLM Rephrase")])
    ui.rephrase.setToolTip(tr("re-segment the sentence.the original segmentation will be used"))

    ui.remove_noise = QtWidgets.QCheckBox()
    ui.remove_noise.setText(tr("Noise reduction"))
    ui.remove_noise.setToolTip(
        tr("Select to perform noise reduction processing from modelscope.cn, which takes a long time"))

    ui.recogn2pass = QtWidgets.QCheckBox()
    ui.recogn2pass.setToolTip(tr("Secondary speech recognition of dubbing files"))
    ui.recogn2pass.setText(tr("STT again"))

    layout.addWidget(ui.reglabel)
    layout.addWidget(ui.recogn_type)
    layout.addWidget(ui.model_name_help)
    layout.addWidget(ui.model_name)
    layout.addWidget(ui.rephrase)
    layout.addStretch()
    layout.addWidget(ui.recogn2pass)
    return layout


def _create_translation_row(ui, parent):
    layout = QtWidgets.QHBoxLayout()
    layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
    layout.setObjectName("horizontalLayout_5")

    ui.label_9 = QtWidgets.QLabel(parent)
    ui.label_9.setObjectName("label_9")
    ui.label_9.setStyleSheet("""background-color:transparent""")
    ui.label_9.setToolTip(
        tr("Click to set the number of subtitles to be translated at the same time"))
    ui.translate_type = QtWidgets.QComboBox(parent)
    ui.translate_type.setMinimumSize(QtCore.QSize(_channel_com, 30))
    ui.translate_type.setObjectName("translate_type")
    ui.translate_type.setToolTip(
        tr("Select the channel used to translate text"))

    layout.addWidget(ui.label_9)
    layout.addWidget(ui.translate_type)

    ui.label_2 = QtWidgets.QPushButton(parent)
    ui.label_2.setStyleSheet("""background-color:transparent""")
    ui.label_2.setObjectName("label_2")
    ui.source_language = QtWidgets.QComboBox(parent)
    ui.source_language.setObjectName("source_language")
    ui.source_language.setMinimumWidth(130)

    ui.label_3 = QtWidgets.QPushButton(parent)
    ui.label_3.setObjectName("label_3")
    ui.label_3.setStyleSheet("""background-color:transparent""")
    ui.target_language = QtWidgets.QComboBox(parent)
    ui.target_language.setObjectName("target_language")
    ui.target_language.setMinimumWidth(130)

    ui.aisendsrt = QtWidgets.QCheckBox()
    ui.aisendsrt.setText(tr("Send SRT"))
    ui.aisendsrt.setToolTip(
        tr("When using AI translation channel, you can translate in srt format, but there may be more empty lines"))
    ui.aisendsrt.setChecked(settings.get('aisendsrt'))

    ui.glossary = QtWidgets.QPushButton(parent)
    ui.glossary.setObjectName("glossary")
    ui.glossary.setText(tr("glossary"))
    ui.glossary.setStyleSheet("""background-color:transparent;border:1px solid #455364""")
    ui.glossary.setCursor(Qt.PointingHandCursor)
    ui.glossary.setToolTip(tr("Click to set up and modify the glossary"))

    layout.addWidget(ui.label_2)
    layout.addWidget(ui.source_language)
    layout.addWidget(ui.label_3)
    layout.addWidget(ui.target_language)
    layout.addStretch()
    layout.addWidget(ui.aisendsrt)
    return layout


def _create_tts_row(ui, parent):
    layout = QtWidgets.QHBoxLayout()
    layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
    layout.setObjectName("horizontalLayout")
    ui.tts_text = QtWidgets.QLabel(parent)
    ui.tts_text.setObjectName("tts_text")
    ui.tts_text.setStyleSheet("""background-color:transparent""")
    ui.tts_text.setToolTip(
        tr("Click to set the number of threads to be used for dubbing"))

    ui.tts_type = QtWidgets.QComboBox(parent)
    ui.tts_type.setMinimumSize(QtCore.QSize(_channel_com, 30))
    ui.tts_type.setObjectName("tts_type")
    ui.tts_type.setToolTip(tr("Select the channel used to dub"))

    ui.label_4 = QtWidgets.QPushButton(parent)
    ui.label_4.setObjectName("label_4")
    ui.label_4.setStyleSheet("background-color:transparent")
    ui.voice_role = QtWidgets.QComboBox(parent)
    ui.voice_role.setMinimumWidth(200)
    ui.voice_role.setObjectName("voice_role")

    ui.listen_btn = QtWidgets.QPushButton(parent)
    ui.listen_btn.setEnabled(False)
    ui.listen_btn.setStyleSheet("""background-color:transparent""")

    layout.addWidget(ui.tts_text)
    layout.addWidget(ui.tts_type)
    layout.addWidget(ui.label_4)
    layout.addWidget(ui.voice_role)
    layout.addWidget(ui.listen_btn)
    layout.addStretch()
    layout.addWidget(ui.glossary)
    return layout


def _create_alignment_row(ui, parent):
    layout = QtWidgets.QHBoxLayout()
    ui.align_btn = QtWidgets.QLabel()

    ui.align_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
    ui.align_btn.setObjectName("align_btn")
    ui.align_btn.setText(tr("Alignment control"))
    ui.align_btn.setToolTip(tr("View alignment tutorial"))

    ui.voice_autorate = QtWidgets.QCheckBox(parent)
    ui.voice_autorate.setObjectName("voice_autorate")

    ui.video_autorate = QtWidgets.QCheckBox(parent)
    ui.video_autorate.setObjectName("videoe_autorate")

    ui.remove_silent_mid = QtWidgets.QCheckBox()
    ui.remove_silent_mid.setObjectName("remove_silent_mid")
    ui.remove_silent_mid.setVisible(False)
    ui.align_sub_audio = QtWidgets.QCheckBox()
    ui.align_sub_audio.setObjectName("align_sub_audio")
    ui.align_sub_audio.setVisible(False)

    ui.subtitle_type = QtWidgets.QComboBox(parent)
    ui.subtitle_type.setMinimumSize(QtCore.QSize(150, 30))
    ui.subtitle_type.setObjectName("subtitle_type")

    layout.addWidget(ui.align_btn)
    layout.addWidget(ui.voice_autorate)
    layout.addWidget(ui.video_autorate)
    layout.addWidget(ui.remove_silent_mid)
    layout.addWidget(ui.align_sub_audio)
    layout.addWidget(ui.subtitle_type)

    ui.set_adv_status = QtWidgets.QPushButton()
    ui.set_adv_status.setText(tr('More settings'))
    ui.set_adv_status.setCursor(Qt.PointingHandCursor)

    ui.label = QtWidgets.QPushButton(parent)
    ui.label.setMinimumSize(QtCore.QSize(0, 30))
    ui.label.setObjectName("label")
    ui.label.setStyleSheet("""background-color:transparent""")

    ui.proxy = QtWidgets.QLineEdit(parent)
    ui.proxy.setMinimumSize(QtCore.QSize(200, 30))
    ui.proxy.setObjectName("proxy")

    ui.output_srt_label = QtWidgets.QLabel(tr('Output') + tr('Subtitles'))
    ui.output_srt = QtWidgets.QComboBox()
    ui.output_srt.addItems([
        tr('default'),
        tr('Target language under(Bilingual)'),
        tr('Target language up(Bilingual)'),
    ])
    ui.output_srt.setVisible(False)
    ui.output_srt_label.setVisible(False)

    layout.addWidget(ui.output_srt_label)
    layout.addWidget(ui.output_srt)
    layout.addStretch()
    layout.addWidget(ui.label)
    layout.addWidget(ui.proxy)
    layout.addWidget(ui.set_adv_status)
    return layout
