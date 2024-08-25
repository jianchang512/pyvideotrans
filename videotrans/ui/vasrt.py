# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'vasrt.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
                            QMetaObject, QObject, QPoint, QRect,
                            QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
                           QFont, QFontDatabase, QGradient, QIcon,
                           QImage, QKeySequence, QLinearGradient, QPainter,
                           QPalette, QPixmap, QRadialGradient, QTransform)

from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMenuBar, QPlainTextEdit, QPushButton,
                               QSizePolicy, QStatusBar, QVBoxLayout, QWidget)

from videotrans.configure import config


class Ui_vasrt(object):
    def setupUi(self, vasrt):
        if not vasrt.objectName():
            vasrt.setObjectName(u"vasrt")
        vasrt.resize(700, 500)
        vasrt.setWindowModality(QtCore.Qt.NonModal)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(vasrt.sizePolicy().hasHeightForWidth())
        vasrt.setSizePolicy(sizePolicy)
        # vasrt.setMaximumSize(QtCore.QSize(643, 500))

        self.horizontalLayout_3 = QHBoxLayout(vasrt)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")

        # start
        self.v3 = QtWidgets.QVBoxLayout()
        self.v3.setObjectName("v3")

        # h3
        self.h3 = QtWidgets.QHBoxLayout()
        self.h3.setObjectName("horizontalLayout_3")
        self.label_4 = QtWidgets.QLabel()
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setMinimumSize(QtCore.QSize(100, 40))
        self.label_4.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.label_4.setObjectName("label_4")
        self.h3.addWidget(self.label_4, 0, QtCore.Qt.AlignTop)



        self.ysphb_videoinput = QtWidgets.QLineEdit()
        self.ysphb_videoinput.setMinimumSize(QtCore.QSize(0, 40))
        self.ysphb_videoinput.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.ysphb_videoinput.setReadOnly(True)
        self.ysphb_videoinput.setObjectName("ysphb_videoinput")
        self.h3.addWidget(self.ysphb_videoinput, 0, QtCore.Qt.AlignTop)

        self.ysphb_selectvideo = QtWidgets.QPushButton()
        self.ysphb_selectvideo.setMinimumSize(QtCore.QSize(150, 40))
        self.ysphb_selectvideo.setObjectName("ysphb_selectvideo")
        self.h3.addWidget(self.ysphb_selectvideo, 0, QtCore.Qt.AlignTop)

        # v3 add h3
        self.v3.addLayout(self.h3)

        # h5
        self.h5 = QtWidgets.QHBoxLayout()
        self.h5.setObjectName("horizontalLayout_5")
        self.label_5 = QtWidgets.QLabel()
        self.label_5.setMinimumSize(QtCore.QSize(100, 40))
        self.label_5.setObjectName("label_5")
        self.h5.addWidget(self.label_5, 0, QtCore.Qt.AlignTop)

        self.ysphb_wavinput = QtWidgets.QLineEdit()
        self.ysphb_wavinput.setMinimumSize(QtCore.QSize(0, 40))
        # self.ysphb_wavinput.setReadOnly(True)
        self.ysphb_wavinput.setObjectName("ysphb_wavinput")
        self.h5.addWidget(self.ysphb_wavinput, 0, QtCore.Qt.AlignTop)

        self.ysphb_wavinput.textChanged.connect(self.remainraw)

        self.ysphb_selectwav = QtWidgets.QPushButton()
        self.ysphb_selectwav.setMinimumSize(QtCore.QSize(150, 40))
        self.ysphb_selectwav.setObjectName("ysphb_selectwav")
        self.h5.addWidget(self.ysphb_selectwav, 0, QtCore.Qt.AlignTop)
        self.v3.addLayout(self.h5)

        # h6
        self.h6 = QtWidgets.QHBoxLayout()
        self.h6.setObjectName("h6")

        self.label_6 = QtWidgets.QLabel()
        self.label_6.setMinimumSize(QtCore.QSize(100, 40))
        self.label_6.setObjectName("label_6")
        self.h6.addWidget(self.label_6, 0, QtCore.Qt.AlignTop)
        self.ysphb_srtinput = QtWidgets.QLineEdit()
        self.ysphb_srtinput.setMinimumSize(QtCore.QSize(0, 40))
        # self.ysphb_srtinput.setReadOnly(True)
        self.ysphb_srtinput.setObjectName("ysphb_srtinput")

        self.h6.addWidget(self.ysphb_srtinput, 0, QtCore.Qt.AlignTop)
        self.ysphb_selectsrt = QtWidgets.QPushButton()
        self.ysphb_selectsrt.setMinimumSize(QtCore.QSize(150, 40))
        self.ysphb_selectsrt.setObjectName("ysphb_selectsrt")
        self.h6.addWidget(self.ysphb_selectsrt, 0, QtCore.Qt.AlignTop)

        self.h7 = QtWidgets.QHBoxLayout()
        self.h7.setObjectName("h7")
        self.ysphb_replace = QtWidgets.QCheckBox()
        self.ysphb_replace.setObjectName("ysphb_replace")
        self.ysphb_replace.setDisabled(True)
        self.ysphb_replace.setText(config.transobj['Preserve the original sound in the video'])

        self.ysphb_maxlenlabel=QtWidgets.QLabel()
        self.ysphb_maxlenlabel.setText("硬字幕单行字符数")
        self.ysphb_maxlen=QtWidgets.QLineEdit()
        self.ysphb_maxlen.setText('30')

        self.layout_form0 = QtWidgets.QFormLayout()
        self.layout_form0.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.ysphb_maxlenlabel)
        self.layout_form0.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.ysphb_maxlen)

        self.ysphb_issoft = QtWidgets.QCheckBox()
        self.ysphb_issoft.setObjectName("ysphb_issoft")
        self.ysphb_issoft.setChecked(False)
        self.ysphb_issoft.setText('嵌入软字幕' if config.defaulelang=='zh' else 'Embedded Soft Subtitles')

        self.layout_form = QtWidgets.QFormLayout()

        self.languagelabel=QtWidgets.QLabel()
        self.languagelabel.setText('软字幕语言' if config.defaulelang=='zh' else 'soft subtitle language')
        self.languagelabel.setStyleSheet('color:#777')
        self.language = QtWidgets.QComboBox()
        self.language.setMinimumSize(QtCore.QSize(0, 30))
        self.language.setObjectName("language")
        self.language.addItems(config.langnamelist)
        self.language.setDisabled(True)
        self.ysphb_issoft.toggled.connect(self.update_language)

        self.layout_form.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.languagelabel)
        self.layout_form.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.language)





        self.h7.addWidget(self.ysphb_replace)
        self.h7.addLayout(self.layout_form0)
        self.h7.addStretch()
        self.h7.addWidget(self.ysphb_issoft)
        self.h7.addLayout(self.layout_form)

        self.v3.addLayout(self.h6)
        self.v3.addLayout(self.h7)

        self.ysphb_startbtn = QtWidgets.QPushButton()
        self.ysphb_startbtn.setMinimumSize(QtCore.QSize(250, 40))
        self.ysphb_startbtn.setObjectName("ysphb_startbtn")
        self.v3.addWidget(self.ysphb_startbtn)
        self.v3.addStretch()

        self.h8 = QtWidgets.QHBoxLayout()
        self.h8.setObjectName("horizontalLayout_20")
        self.ysphb_out = QtWidgets.QLineEdit()
        self.ysphb_out.setMinimumSize(QtCore.QSize(0, 30))
        self.ysphb_out.setReadOnly(True)
        self.ysphb_out.setObjectName("ysphb_out")
        self.h8.addWidget(self.ysphb_out)
        self.ysphb_opendir = QtWidgets.QPushButton()
        self.ysphb_opendir.setMinimumSize(QtCore.QSize(0, 30))
        self.ysphb_opendir.setObjectName("ysphb_opendir")
        self.h8.addWidget(self.ysphb_opendir)
        self.v3.addLayout(self.h8)

        # end
        self.horizontalLayout_3.addLayout(self.v3)

        self.retranslateUi(vasrt)

        QMetaObject.connectSlotsByName(vasrt)

    def remainraw(self,t):
        print(f'{t=}')
        if Path(t).is_file():
            self.ysphb_replace.setDisabled(False)
            self.ysphb_replace.setChecked(True)
        else:
            self.ysphb_replace.setChecked(False)
            self.ysphb_replace.setDisabled(True)


    def update_language(self,state):
        self.languagelabel.setStyleSheet(f"""color:#f1f1f1""" if state else 'color:#777777')
        self.language.setDisabled(False if state else True)

    def retranslateUi(self, vasrt):
        vasrt.setWindowTitle("视频、音频、字幕三者合并" if config.defaulelang == 'zh' else 'Video, audio, and subtitle merging')

        self.label_4.setText('视频文件' if config.defaulelang=='zh' else 'Video')
        self.label_5.setText('音频文件' if config.defaulelang=='zh' else 'Audio')
        self.label_6.setText('字幕文件/srt' if config.defaulelang=='zh' else 'Subtitles/srt')
        self.ysphb_selectvideo.setText('选择视频文件' if config.defaulelang=='zh' else 'Select a Video')
        self.ysphb_videoinput.setPlaceholderText('选择视频文件' if config.defaulelang=='zh' else 'Select a Video')
        self.ysphb_selectwav.setText('选择音频文件' if config.defaulelang=='zh' else 'Select a Audio')
        self.ysphb_wavinput.setPlaceholderText('选择音频文件' if config.defaulelang=='zh' else 'Select a Audio')
        self.ysphb_selectsrt.setText('选择srt字幕文件' if config.defaulelang=='zh' else 'Select a Srt file')
        self.ysphb_srtinput.setPlaceholderText('选择srt字幕文件' if config.defaulelang=='zh' else 'Select a Srt file')
        self.ysphb_startbtn.setText('开始执行' if config.defaulelang=='zh' else 'Start operating')
        self.ysphb_opendir.setText('打开结果目录' if config.defaulelang=='zh' else 'Open the results catalog')