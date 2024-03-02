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

class Ui_gptsovitsform(object):
    def setupUi(self, gptsovitsform):
        if not gptsovitsform.objectName():
            gptsovitsform.setObjectName("gptsovitsform")
        gptsovitsform.setWindowModality(Qt.NonModal)
        gptsovitsform.resize(600, 500)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(gptsovitsform.sizePolicy().hasHeightForWidth())
        gptsovitsform.setSizePolicy(sizePolicy)
        gptsovitsform.setMaximumSize(QSize(600, 500))
        self.label_3 = QLabel(gptsovitsform)
        self.label_3.setObjectName("label_3")
        self.label_3.setGeometry(QRect(10, 60, 101, 16))
        
        self.extra = QLineEdit(gptsovitsform)
        self.extra.setObjectName("extra")
        self.extra.setGeometry(QRect(130, 50, 441, 35))
        self.extra.setMinimumSize(QSize(0, 35))
        
        self.label_4 = QLabel(gptsovitsform)
        self.label_4.setObjectName("label_4")
        self.label_4.setGeometry(QRect(10, 100, 301, 16))
        self.label_4.setText('参考音频#音频文字内容#语言代码')        

        self.role = QPlainTextEdit(gptsovitsform)
        self.role.setObjectName("role")
        self.role.setGeometry(QRect(10, 120, 571, 100))
        self.role.setReadOnly(False)
        
        self.label_5 = QLabel(gptsovitsform)
        self.label_5.setObjectName("label_5")
        self.label_5.setGeometry(QRect(10, 230, 301, 16))
        self.label_5.setText('API请求说明')       
        
        self.tips = QPlainTextEdit(gptsovitsform)
        self.tips.setObjectName("tips")
        self.tips.setGeometry(QRect(10, 250, 571, 150))
        self.tips.setReadOnly(True)
        
        

        
        self.api_url = QLineEdit(gptsovitsform)
        self.api_url.setObjectName("api_url")
        self.api_url.setGeometry(QRect(130, 10, 441, 35))
        self.api_url.setMinimumSize(QSize(0, 35))
        self.label = QLabel(gptsovitsform)
        self.label.setObjectName("label")
        self.label.setGeometry(QRect(10, 10, 101, 35))
        self.label.setMinimumSize(QSize(0, 35))


        
        self.save = QPushButton(gptsovitsform)
        self.save.setObjectName("save")
        self.save.setGeometry(QRect(10, 450, 93, 35))
        self.save.setMinimumSize(QSize(0, 35))
        
        self.test = QPushButton(gptsovitsform)
        self.test.setObjectName("test")
        self.test.setGeometry(QRect(490, 450, 93, 35))
        self.test.setMinimumSize(QSize(0, 35))

        self.retranslateUi(gptsovitsform)

        QMetaObject.connectSlotsByName(gptsovitsform)
    # setupUi

    def retranslateUi(self, gptsovitsform):
        tips="""
将以POST请求向填写的API地址发送application/json数据：

GPT-SoVITS自带api.py，可接受请求共包含5个参数

text,text_language,refer_wav_path,prompt_text,prompt_language

因该api.py不可动态切换模型，因此后3个参数可在启动api.py时指定，在此请求时不发送
GPT-SoVITS启动时指定命令`python api.py -dr "参考音频路径"  -dt "参考音频文本" -dl "参考音频语言代码" `

本工具将向填写的API地址发送以下4个参数，后2个为冗余暂未使用

text:需要合成的文本/字符串
text_language:文字所属语言代码(zh|ja|en)/字符串


ostype:win32或mac或linux操作系统类型/字符串
extra:额外参数/字符串

请求失败时返回：
{
    "code": 400, 错误数
    "message": "错误信息"
}            
请求成功时返回音频流
"""

        gptsovitsform.setWindowTitle("GPT-SoVITS API")
        self.label_3.setText("额外参数")
        self.role.setPlaceholderText("在此填写参考音频信息,可以不填写，格式如下\n例如：一行一组\n123.wav#你好啊我的朋友#zh")
        self.tips.setPlainText(tips)
        self.save.setText("保存" if config.defaulelang=='zh' else "Save")
        self.api_url.setPlaceholderText("填写http开头的完整地址,GPT-SoVITS自带api默认 http://127.0.0.1:9880")
        self.label.setText("GPT-SoVITS API")
        self.extra.setPlaceholderText("填写通过extra键向api传递的额外参数，为空则传递pyvideotrans")
        self.test.setText("测试Api" if config.defaulelang=='zh' else "Test API" )
    # retranslateUi

