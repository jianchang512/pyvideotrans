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

class Ui_cosyvoiceform(object):
    def setupUi(self, cosyvoiceform):
        if not cosyvoiceform.objectName():
            cosyvoiceform.setObjectName("cosyvoiceform")
        cosyvoiceform.setWindowModality(Qt.NonModal)
        cosyvoiceform.resize(600, 500)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(cosyvoiceform.sizePolicy().hasHeightForWidth())
        cosyvoiceform.setSizePolicy(sizePolicy)
        cosyvoiceform.setMaximumSize(QSize(600, 500))
        self.label_3 = QLabel(cosyvoiceform)
        self.label_3.setObjectName("label_3")
        self.label_3.setGeometry(QRect(10, 60, 580, 16))

        self.label_4 = QLabel(cosyvoiceform)
        self.label_4.setObjectName("label_4")
        self.label_4.setGeometry(QRect(10, 100, 301, 16))
        self.label_4.setText('参考音频#音频文字内容')

        self.role = QPlainTextEdit(cosyvoiceform)
        self.role.setObjectName("role")
        self.role.setGeometry(QRect(10, 120, 571, 100))
        self.role.setReadOnly(False)

        self.label_5 = QLabel(cosyvoiceform)
        self.label_5.setObjectName("label_5")
        self.label_5.setGeometry(QRect(10, 230, 301, 16))
        self.label_5.setText('API请求说明')

        self.tips = QPlainTextEdit(cosyvoiceform)
        self.tips.setObjectName("tips")
        self.tips.setGeometry(QRect(10, 250, 571, 150))
        self.tips.setReadOnly(True)




        self.api_url = QLineEdit(cosyvoiceform)
        self.api_url.setObjectName("api_url")
        self.api_url.setGeometry(QRect(130, 10, 441, 35))
        self.api_url.setMinimumSize(QSize(0, 35))
        self.label = QLabel(cosyvoiceform)
        self.label.setObjectName("label")
        self.label.setGeometry(QRect(10, 10, 101, 35))
        self.label.setMinimumSize(QSize(0, 35))



        self.save = QPushButton(cosyvoiceform)
        self.save.setObjectName("save")
        self.save.setGeometry(QRect(10, 450, 93, 35))
        self.save.setMinimumSize(QSize(0, 35))

        self.test = QPushButton(cosyvoiceform)
        self.test.setObjectName("test")
        self.test.setGeometry(QRect(490, 450, 93, 35))
        self.test.setMinimumSize(QSize(0, 35))

        self.retranslateUi(cosyvoiceform)

        QMetaObject.connectSlotsByName(cosyvoiceform)
    # setupUi

    def retranslateUi(self, cosyvoiceform):
        tips="""
# 需要预先部署CosyVoice项目，并放入了CosyVoice-api项目中的api.py
# CosyVoice项目地址 https://github.com/FunAudioLLM/CosyVoice
# CosyVoice-api项目地址 https://github.com/jianchang512/CosyVoice-api

将以POST请求向填写的API地址发送数据：
CosyVoice-api项目的api接口默认 http://127.0.0.1:9233

参考音频填写：
每行都由#符号分割为两部分，第一部分是wav音频路径，第二部分是该音频对应的文字内容，可填写多行。
wav音频最佳时长5-15s，如果音频放在了CosyVoice项目的根路径下，即webui.py同目录下，这里直接填写名称即可
如果放在了根目录下的wavs目录下，那么需要填写 wavs/音频名称.wav

参考音频填写示例：
1.wav#你好啊亲爱的朋友
wavs/2.wav#你好啊朋友们


# 本工具将向填写的API地址发送以下参数

##当角色为clone时：
text:需要合成的文本/字符串
lang:文字所属语言代码(zh|ja|en|ko)/字符串
reference_audio:原视频对应的语音片段

##当角色为预置7种语音时：
text:需要合成的文本/字符串
lang:文字所属语言代码(zh|ja|en|ko)/字符串
role:角色名称

##当角色为自定义的参考音频时
text:需要合成的文本/字符串
lang:文字所属语言代码(zh|ja|en|ko)/字符串
reference_audio:定义的参考音频


请求失败时返回：
{
    "code": 400, 错误数
    "msg": "错误信息"
}            
请求成功时返回音频流
"""

        cosyvoiceform.setWindowTitle("CosyVoice API")

        self.role.setPlaceholderText("在此填写参考音频信息,可以不填写，格式如下\n例如：一行一组\n123.wav#你好啊我的朋友")
        self.tips.setPlainText(tips)
        self.save.setText("保存" if config.defaulelang=='zh' else "Save")
        self.api_url.setPlaceholderText("填写http开头的完整地址,CosyVoice-api默认 http://127.0.0.1:9233")
        self.label.setText("CosyVoice API")
        self.label_3.setText("需部署并启动CosyVoice-api，项目地址 https://github.com/jianchang512/CosyVoice-api")
        self.test.setText("测试Api" if config.defaulelang=='zh' else "Test API" )


