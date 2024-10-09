from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (QMetaObject)
from PySide6.QtWidgets import (QHBoxLayout, QVBoxLayout)

from videotrans.configure import config


class Ui_hunliu(object):
    def setupUi(self, hunliu):
        self.has_done = False
        if not hunliu.objectName():
            hunliu.setObjectName(u"hunliu")
        hunliu.resize(643, 400)
        hunliu.setWindowModality(QtCore.Qt.NonModal)
        self.horizontalLayout_3 = QHBoxLayout(hunliu)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")

        self.v1 = QVBoxLayout()
        self.v1.setObjectName(u"verticalLayout")

        # start
        self.h1 = QtWidgets.QHBoxLayout()
        self.h1.setObjectName("h1")

        self.l1 = QtWidgets.QLabel()
        self.l1.setMinimumSize(QtCore.QSize(100, 40))
        self.l1.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.l1.setObjectName("l1")
        self.h1.addWidget(self.l1, 0, QtCore.Qt.AlignTop)

        self.hun_file1 = QtWidgets.QLineEdit()
        self.hun_file1.setMinimumSize(QtCore.QSize(0, 40))
        self.hun_file1.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.hun_file1.setReadOnly(True)
        self.hun_file1.setObjectName("hun_file1")
        self.h1.addWidget(self.hun_file1, 0, QtCore.Qt.AlignTop)

        self.hun_file1btn = QtWidgets.QPushButton()
        self.hun_file1btn.setMinimumSize(QtCore.QSize(150, 40))
        self.hun_file1btn.setObjectName("hun_file1btn")
        self.h1.addWidget(self.hun_file1btn, 0, QtCore.Qt.AlignTop)
        self.v1.addLayout(self.h1)

        self.h2 = QtWidgets.QHBoxLayout()
        self.h2.setObjectName("horizontalLayout_16")
        self.l2 = QtWidgets.QLabel()
        self.l2.setMinimumSize(QtCore.QSize(100, 40))
        self.l2.setObjectName("l2")
        self.h2.addWidget(self.l2, 0, QtCore.Qt.AlignTop)
        self.hun_file2 = QtWidgets.QLineEdit()
        self.hun_file2.setMinimumSize(QtCore.QSize(0, 40))
        self.hun_file2.setReadOnly(True)
        self.hun_file2.setObjectName("hun_file2")
        self.h2.addWidget(self.hun_file2, 0, QtCore.Qt.AlignTop)
        self.hun_file2btn = QtWidgets.QPushButton()
        self.hun_file2btn.setMinimumSize(QtCore.QSize(150, 40))
        self.hun_file2btn.setObjectName("hun_file2btn")
        self.h2.addWidget(self.hun_file2btn, 0, QtCore.Qt.AlignTop)
        self.v1.addLayout(self.h2)

        self.hun_startbtn = QtWidgets.QPushButton()
        self.hun_startbtn.setMinimumSize(QtCore.QSize(250, 40))
        self.hun_startbtn.setObjectName("hun_startbtn")
        self.v1.addWidget(self.hun_startbtn)

        self.v1.addStretch()

        self.h3 = QtWidgets.QHBoxLayout()
        self.h3.setObjectName("horizontalLayout_21")
        self.hun_out = QtWidgets.QLineEdit()
        self.hun_out.setMinimumSize(QtCore.QSize(0, 30))
        self.hun_out.setReadOnly(False)
        self.hun_out.setObjectName("hun_out")
        self.h3.addWidget(self.hun_out)
        self.hun_opendir = QtWidgets.QPushButton()
        self.hun_opendir.setMinimumSize(QtCore.QSize(0, 30))
        self.hun_opendir.setObjectName("hun_opendir")
        self.h3.addWidget(self.hun_opendir)
        self.v1.addLayout(self.h3)
        self.v1.addStretch()
        self.horizontalLayout_3.addLayout(self.v1)
        self.retranslateUi(hunliu)
        QMetaObject.connectSlotsByName(hunliu)

    def retranslateUi(self, hunliu):
        hunliu.setWindowTitle("混合2个音频" if config.defaulelang == 'zh' else 'Mix 2 Audio')
        self.l1.setText('Audio 1')
        self.l2.setText('Audio 2')
        self.hun_file1.setPlaceholderText('Select an audio' if config.defaulelang != 'zh' else '选择第一个音频文件')
        self.hun_file1btn.setText('Select Audio' if config.defaulelang != 'zh' else '选择音频文件')
        self.hun_file2.setPlaceholderText('Select an audio' if config.defaulelang != 'zh' else '选择第二个音频文件')
        self.hun_file2btn.setText('Select Audio' if config.defaulelang != 'zh' else '选择音频文件')
        self.hun_out.setPlaceholderText('Output directory' if config.defaulelang != 'zh' else '输出目录')
        self.hun_opendir.setText('Open output directory' if config.defaulelang != 'zh' else '打开输出目录')
        self.hun_startbtn.setText('开始混合' if config.defaulelang == 'zh' else 'Start operate')
