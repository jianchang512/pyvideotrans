from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from videotrans.configure import config
from videotrans.util import tools


class Ui_googlecloudform(object):
    def setupUi(self, googlecloudform):
        self.has_done = False
        googlecloudform.setObjectName("googlecloudform")
        googlecloudform.setWindowModality(QtCore.Qt.NonModal)
        googlecloudform.resize(500, 300)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(googlecloudform.sizePolicy().hasHeightForWidth())
        googlecloudform.setSizePolicy(sizePolicy)
        googlecloudform.setMaximumSize(QtCore.QSize(500, 300))

        self.verticalLayout = QtWidgets.QVBoxLayout(googlecloudform)
        self.verticalLayout.setObjectName("verticalLayout")

        # Credential JSON file
        self.formLayout_1 = QtWidgets.QFormLayout()
        self.formLayout_1.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.formLayout_1.setFormAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)
        self.formLayout_1.setObjectName("formLayout_1")

        self.label_cred = QtWidgets.QLabel(googlecloudform)
        self.label_cred.setMinimumSize(QtCore.QSize(100, 35))
        self.label_cred.setObjectName("label_cred")
        self.formLayout_1.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_cred)

        self.credential_path = QtWidgets.QLineEdit(googlecloudform)
        self.credential_path.setMinimumSize(QtCore.QSize(0, 35))
        self.credential_path.setObjectName("credential_path")
        self.formLayout_1.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.credential_path)

        self.browse_btn = QtWidgets.QPushButton(googlecloudform)
        self.browse_btn.setMinimumSize(QtCore.QSize(80, 35))
        self.browse_btn.setObjectName("browse_btn")
        self.formLayout_1.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.browse_btn)

        self.verticalLayout.addLayout(self.formLayout_1)

        # Language code
        self.formLayout_2 = QtWidgets.QFormLayout()
        self.formLayout_2.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.formLayout_2.setFormAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)
        self.formLayout_2.setObjectName("formLayout_2")

        self.label_lang = QtWidgets.QLabel(googlecloudform)
        self.label_lang.setMinimumSize(QtCore.QSize(100, 35))
        self.label_lang.setObjectName("label_lang")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_lang)

        self.language_code = QtWidgets.QComboBox(googlecloudform)
        self.language_code.setMinimumSize(QtCore.QSize(0, 35))
        self.language_code.setObjectName("language_code")
        self.language_code.addItems([
            "pt-BR", "en-US", "en-GB", "es-ES", "fr-FR", "de-DE",
            "it-IT", "ja-JP", "ko-KR", "zh-CN", "ru-RU", "hi-IN",
            "ar-XA", "tr-TR", "th-TH", "vi-VN", "id-ID"
        ])
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.language_code)

        self.verticalLayout.addLayout(self.formLayout_2)

        # Voice name
        self.formLayout_3 = QtWidgets.QFormLayout()
        self.formLayout_3.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.formLayout_3.setFormAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)
        self.formLayout_3.setObjectName("formLayout_3")

        self.label_voice = QtWidgets.QLabel(googlecloudform)
        self.label_voice.setMinimumSize(QtCore.QSize(100, 35))
        self.label_voice.setObjectName("label_voice")
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_voice)

        self.voice_name = QtWidgets.QComboBox(googlecloudform)
        self.voice_name.setMinimumSize(QtCore.QSize(0, 35))
        self.voice_name.setObjectName("voice_name")
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.voice_name)

        self.verticalLayout.addLayout(self.formLayout_3)

        # Audio encoding
        self.formLayout_4 = QtWidgets.QFormLayout()
        self.formLayout_4.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.formLayout_4.setFormAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)
        self.formLayout_4.setObjectName("formLayout_4")

        self.label_encoding = QtWidgets.QLabel(googlecloudform)
        self.label_encoding.setMinimumSize(QtCore.QSize(100, 35))
        self.label_encoding.setObjectName("label_encoding")
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_encoding)

        self.audio_encoding = QtWidgets.QComboBox(googlecloudform)
        self.audio_encoding.setMinimumSize(QtCore.QSize(0, 35))
        self.audio_encoding.setObjectName("audio_encoding")
        self.audio_encoding.addItems(["MP3", "LINEAR16", "OGG_OPUS"])
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.audio_encoding)

        self.verticalLayout.addLayout(self.formLayout_4)

        # Buttons
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.save = QtWidgets.QPushButton(googlecloudform)
        self.save.setMinimumSize(QtCore.QSize(0, 35))
        self.save.setObjectName("save")
        self.horizontalLayout.addWidget(self.save)

        self.test = QtWidgets.QPushButton(googlecloudform)
        self.test.setMinimumSize(QtCore.QSize(0, 35))
        self.test.setObjectName("test")
        self.horizontalLayout.addWidget(self.test)

        help_btn = QtWidgets.QPushButton(googlecloudform)
        help_btn.setMinimumSize(QtCore.QSize(0, 35))
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText("查看填写教程" if config.defaulelang == 'zh' else "Fill out the tutorial")
        help_btn.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/googlecloudtts'))
        self.horizontalLayout.addWidget(help_btn)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(googlecloudform)
        QtCore.QMetaObject.connectSlotsByName(googlecloudform)

    def retranslateUi(self, googlecloudform):
        googlecloudform.setWindowTitle("Google Cloud TTS Settings")
        self.label_cred.setText("Credential JSON" if config.defaulelang == 'zh' else "Credential JSON")
        self.label_lang.setText("Language" if config.defaulelang == 'zh' else "Language")
        self.label_voice.setText("Voice" if config.defaulelang == 'zh' else "Voice")
        self.label_encoding.setText("Audio Encoding" if config.defaulelang == 'zh' else "Audio Encoding")
        self.browse_btn.setText("Browse" if config.defaulelang == 'zh' else "Browse")
        self.save.setText("Save" if config.defaulelang == 'zh' else "Save")
        self.test.setText("Test" if config.defaulelang == 'zh' else "Test")
        self.credential_path.setPlaceholderText(
            "Path to Google Cloud credentials JSON file" if config.defaulelang == 'zh'
            else "Path to Google Cloud credentials JSON file"
        )
