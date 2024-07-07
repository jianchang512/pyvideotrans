# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ttsapi.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QMetaObject, QRect, QSize, Qt
from PySide6.QtWidgets import   QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSizePolicy
from videotrans.configure import config

class Ui_fishttsform(object):
    def setupUi(self, fishttsform):
        if not fishttsform.objectName():
            fishttsform.setObjectName("fishttsform")
        fishttsform.setWindowModality(Qt.NonModal)
        fishttsform.resize(600, 500)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(fishttsform.sizePolicy().hasHeightForWidth())
        fishttsform.setSizePolicy(sizePolicy)
        fishttsform.setMaximumSize(QSize(600, 500))
        self.label_3 = QLabel(fishttsform)
        self.label_3.setObjectName("label_3")
        self.label_3.setGeometry(QRect(10, 60, 101, 16))


        self.label_4 = QLabel(fishttsform)
        self.label_4.setObjectName("label_4")
        self.label_4.setGeometry(QRect(10, 100, 301, 16))
        self.label_4.setText('参考音频#音频文字内容')

        self.role = QPlainTextEdit(fishttsform)
        self.role.setObjectName("role")
        self.role.setGeometry(QRect(10, 120, 571, 100))
        self.role.setReadOnly(False)

        self.label_5 = QLabel(fishttsform)
        self.label_5.setObjectName("label_5")
        self.label_5.setGeometry(QRect(10, 230, 301, 16))
        self.label_5.setText('API请求说明')

        self.tips = QPlainTextEdit(fishttsform)
        self.tips.setObjectName("tips")
        self.tips.setGeometry(QRect(10, 250, 571, 150))
        self.tips.setReadOnly(True)




        self.api_url = QLineEdit(fishttsform)
        self.api_url.setObjectName("api_url")
        self.api_url.setGeometry(QRect(130, 10, 441, 35))
        self.api_url.setMinimumSize(QSize(0, 35))
        self.label = QLabel(fishttsform)
        self.label.setObjectName("label")
        self.label.setGeometry(QRect(10, 10, 101, 35))
        self.label.setMinimumSize(QSize(0, 35))



        self.save = QPushButton(fishttsform)
        self.save.setObjectName("save")
        self.save.setGeometry(QRect(10, 450, 93, 35))
        self.save.setMinimumSize(QSize(0, 35))

        self.test = QPushButton(fishttsform)
        self.test.setObjectName("test")
        self.test.setGeometry(QRect(490, 450, 93, 35))
        self.test.setMinimumSize(QSize(0, 35))

        self.retranslateUi(fishttsform)

        QMetaObject.connectSlotsByName(fishttsform)
    # setupUi

    def retranslateUi(self, fishttsform):
        tips="""
FishTTS 开源地址 https://github.com/fishaudio/fish-speech

将以POST请求向填写的API地址发送application/json数据：

FishTTS自带 tools/api.py，可接受请求

text,reference_audio,reference_text

本工具将向填写的API地址发送以下3个参数

text:需要合成的文本/字符串
reference_audio:参考音频路径，相对于fishtts根目录，或填写绝对路径
reference_text:参考音频的文本


请求失败时返回json格式数据
      
请求成功时返回音频流
"""

        fishttsform.setWindowTitle("FishTTS API")
        self.role.setPlaceholderText("在此填写参考音频信息,格式如下\n例如：一行一组\n123.wav#你好啊我的朋友")
        self.tips.setPlainText(tips)
        self.save.setText("保存" if config.defaulelang=='zh' else "Save")
        self.api_url.setPlaceholderText("填写http开头的API地址,FishTTS默认 http://127.0.0.1:8000/v1/invoke")
        self.label.setText("FishTTS API")
        self.test.setText("测试Api" if config.defaulelang=='zh' else "Test API" )
    # retranslateUi

