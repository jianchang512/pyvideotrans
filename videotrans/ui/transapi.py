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

class Ui_transapiform(object):
    def setupUi(self, transapiform):
        if not transapiform.objectName():
            transapiform.setObjectName("transapiform")
        transapiform.setWindowModality(Qt.NonModal)
        transapiform.resize(600, 400)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(transapiform.sizePolicy().hasHeightForWidth())
        transapiform.setSizePolicy(sizePolicy)
        transapiform.setMaximumSize(QSize(600, 400))

        self.label = QLabel(transapiform)
        self.label.setObjectName("label")
        self.label.setGeometry(QRect(10, 10, 101, 35))
        self.label.setMinimumSize(QSize(0, 35))
        self.api_url = QLineEdit(transapiform)
        self.api_url.setObjectName("api_url")
        self.api_url.setGeometry(QRect(130, 10, 441, 35))
        self.api_url.setMinimumSize(QSize(0, 35))


        self.label_3 = QLabel(transapiform)
        self.label_3.setObjectName("miyue")
        self.label_3.setGeometry(QRect(10, 50, 101, 35))


        self.miyue = QLineEdit(transapiform)
        self.miyue.setObjectName("miyue")
        self.miyue.setGeometry(QRect(130, 50, 441, 35))

        self.tips = QLabel(transapiform)
        self.tips.setObjectName("tips")
        self.tips.setGeometry(QRect(10, 100, 570, 200))




        self.save = QPushButton(transapiform)
        self.save.setObjectName("save")
        self.save.setGeometry(QRect(10, 350, 93, 35))
        self.save.setMinimumSize(QSize(0, 35))





        self.test = QPushButton(transapiform)
        self.test.setObjectName("test")
        self.test.setGeometry(QRect(490, 350, 93, 35))
        self.test.setMinimumSize(QSize(0, 35))

        self.retranslateUi(transapiform)

        QMetaObject.connectSlotsByName(transapiform)
    # setupUi

    def retranslateUi(self, transapiform):
        if config.defaulelang=='zh':
            tips="""
将以GET请求向填写的API地址发送application/www-urlencode数据：
text:需要翻译的文本/字符串
source_language:原始文字语言代码zh,en,ja,ko,ru,de,fr,tr,th,vi,ar,hi,hu,es,pt,it/字符串
target_language:目标文字语言代码zh,en,ja,ko,ru,de,fr,tr,th,vi,ar,hi,hu,es,pt,it/字符串
期待从接口返回json格式数据：
{
    code:0=成功时，>0的数字代表失败 , msg:ok=成功时，其他为失败原因, text:翻译后的文本
}
基于cloudflare和m2m100实现的免费翻译API见: github.com/jianchang512/translate-api
"""
        else:
            tips="""
The application/www-urlencode data will be sent as a GET request to the filled API address:
text:text/string to be translated
source_language:original text language code zh,en,ja,ko,ru,de,fr,tr,th,vi,ar,hi,hu,es,pt,it/string
target_language:target_language code zh,en,ja,ko,ru,de,fr,tr,th,vi,ar,hi,hu,es,pt,it/string
Expect data to be returned from the interface in json format:
{
    code:0=on success  numbers >0 represent failures, msg:ok=success  others are failure reasons,text:Translated text
}
Usage: github.com/jianchang512/translate-api
"""
        transapiform.setWindowTitle("自定义翻译API/无编码能力勿使用该功能" if config.defaulelang=='zh' else "Customizing the Translate API")
        self.label_3.setText("密钥" if config.defaulelang=='zh' else "Secret")
        self.miyue.setPlaceholderText("填写密钥")

        self.tips.setText(tips)

        self.save.setText("保存" if config.defaulelang=='zh' else "Save")
        self.api_url.setPlaceholderText("填写http开头的翻译api地址" if config.defaulelang=='zh' else "Fill in the full address starting with http")
        self.label.setText("自定义翻译API" if config.defaulelang=='zh' else "Translate API")
        self.test.setText("测试Api" if config.defaulelang=='zh' else "Test API" )
    # retranslateUi

