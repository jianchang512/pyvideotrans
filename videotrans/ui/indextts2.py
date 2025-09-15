# videotrans/ui/indextts2.py
from PySide6 import QtWidgets
from PySide6.QtCore import QMetaObject, QSize, Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QPlainTextEdit
from videotrans.configure import config

class Ui_indextts2form(object):
    def setupUi(self, indextts2form):
        indextts2form.setObjectName("indextts2form")
        indextts2form.setWindowModality(Qt.NonModal)
        indextts2form.resize(600, 400)

        self.wrap_h = QHBoxLayout(indextts2form)
        self.inner_v = QVBoxLayout()

        h1 = QHBoxLayout()
        self.label = QLabel("Index-TTS2 URL:")
        self.label.setMinimumSize(QSize(120, 35))
        self.api_url = QLineEdit()
        self.api_url.setMinimumSize(QSize(0, 35))
        h1.addWidget(self.label)
        h1.addWidget(self.api_url)
        self.inner_v.addLayout(h1)

        self.role_label = QLabel("参考音频#音频文字内容 (音频文件存放在根目录 f5-tts 文件夹)")
        self.inner_v.addWidget(self.role_label)
        self.rolelist = QPlainTextEdit()
        self.rolelist.setPlaceholderText("例如:\nUnrealmagic.wav#你好啊，我的朋友，希望你的每一天都是美好的")
        self.inner_v.addWidget(self.rolelist)

        h4 = QHBoxLayout()
        self.save = QPushButton()
        self.save.setMinimumSize(QSize(0, 35))
        self.test = QPushButton()
        self.test.setMinimumSize(QSize(0, 35))
        h4.addWidget(self.save)
        h4.addWidget(self.test)
        self.inner_v.addLayout(h4)

        self.wrap_h.addLayout(self.inner_v)
        self.retranslateUi(indextts2form)
        QMetaObject.connectSlotsByName(indextts2form)

    def retranslateUi(self, indextts2form):
        indextts2form.setWindowTitle("Index-TTS2 Config")
        self.save.setText("保存" if config.defaulelang == 'zh' else "Save")
        self.api_url.setPlaceholderText("填写http开头的完整地址, 例如 http://127.0.0.1:9880")
        self.test.setText("测试Api" if config.defaulelang == 'zh' else "Test API")