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

class Ui_ttsapiform(object):
    def setupUi(self, ttsapiform):
        if not ttsapiform.objectName():
            ttsapiform.setObjectName("ttsapiform")
        ttsapiform.setWindowModality(Qt.NonModal)
        ttsapiform.resize(600, 500)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ttsapiform.sizePolicy().hasHeightForWidth())
        ttsapiform.setSizePolicy(sizePolicy)
        ttsapiform.setMaximumSize(QSize(600, 500))
        self.label_3 = QLabel(ttsapiform)
        self.label_3.setObjectName("label_3")
        self.label_3.setGeometry(QRect(10, 120, 101, 16))
        self.tips = QPlainTextEdit(ttsapiform)
        self.tips.setObjectName("tips")
        self.tips.setGeometry(QRect(10, 180, 571, 151))
        self.tips.setReadOnly(True)
        self.save = QPushButton(ttsapiform)
        self.save.setObjectName("save")
        self.save.setGeometry(QRect(10, 350, 93, 35))
        self.save.setMinimumSize(QSize(0, 35))
        self.api_url = QLineEdit(ttsapiform)
        self.api_url.setObjectName("api_url")
        self.api_url.setGeometry(QRect(130, 10, 441, 35))
        self.api_url.setMinimumSize(QSize(0, 35))
        self.label = QLabel(ttsapiform)
        self.label.setObjectName("label")
        self.label.setGeometry(QRect(10, 10, 101, 35))
        self.label.setMinimumSize(QSize(0, 35))
        self.voice_role = QLineEdit(ttsapiform)
        self.voice_role.setObjectName("voice_role")
        self.voice_role.setGeometry(QRect(130, 60, 441, 35))
        self.voice_role.setMinimumSize(QSize(0, 35))
        self.label_2 = QLabel(ttsapiform)
        self.label_2.setObjectName("label_2")
        self.label_2.setGeometry(QRect(10, 60, 101, 35))
        self.label_2.setMinimumSize(QSize(0, 35))
        self.label_2.setSizeIncrement(QSize(0, 35))
        self.extra = QLineEdit(ttsapiform)
        self.extra.setObjectName("extra")
        self.extra.setGeometry(QRect(130, 110, 441, 35))
        self.extra.setMinimumSize(QSize(0, 35))
        self.test = QPushButton(ttsapiform)
        self.test.setObjectName("test")
        self.test.setGeometry(QRect(490, 350, 93, 35))
        self.test.setMinimumSize(QSize(0, 35))

        self.otherlink=QPushButton(ttsapiform)
        self.otherlink.setStyleSheet("""background-color:transparent;border:0;""")
        self.otherlink.setText("第三方实现OpenVoice接口 https://github.com/kungful/openvoice-api")
        self.otherlink.setGeometry(QRect(10,400,400,35))

        self.retranslateUi(ttsapiform)

        QMetaObject.connectSlotsByName(ttsapiform)
    # setupUi

    def retranslateUi(self, ttsapiform):
        if config.defaulelang=='zh':
            tips="""
将以POST请求向填写的API地址发送application/www-urlencode数据：

text:需要合成的文本/字符串
language:文字所属语言代码(zh-cn,zh-tw,en,ja,ko,ru,de,fr,tr,th,vi,ar,hi,hu,es,pt,it)/字符串
voice:配音角色名称/字符串
rate:加减速值，0或者 '+数字%' '-数字%'，代表在正常速度基础上进行加减速的百分比/字符串
ostype:win32或mac或linux操作系统类型/字符串
extra:额外参数/字符串

期待从接口返回json格式数据：
{
    code:0=合成成功时，>0的数字代表失败
    msg:ok=合成成功时，其他为失败原因
    data:在合成成功时，返回mp3文件的完整url地址，用于在软件内下载。失败时为空
}       

----
OpenVoice-v2第三方实现自定义api
https://github.com/kungful/openvoice-api
     
"""
        else:
            tips="""
            
The application/www-urlencode data will be sent in a POST request to the filled API address:

text:text/string
language:language code(zh-cn,zh-tw,en,ja,ko,ru,de,fr,tr,th,vi,ar,hi,hu,es,pt,it) / string
voice:voice character name/string
rate:acceleration/deceleration value, 0 or '+numeric%' '-numeric%', represents the percentage of acceleration/deceleration on top of the normal speed /string
ostype:win32 or mac or linux OS type/string
extra:extra parameters/string

Expect data to be returned from the interface in json format:
{
    code:0=when synthesis is successful, a number >0 means failure
    msg:ok=when the synthesis was successful, other is the reason for failure
    data:On successful synthesis, return the full url of the mp3 file for downloading within the software. When it fails, the url will be empty.
}            
"""
        ttsapiform.setWindowTitle("自定义TTS-API/无编码能力勿使用该功能" if config.defaulelang=='zh' else "Customizing the TTS-API")
        self.label_3.setText("额外参数" if config.defaulelang=='zh' else "additional parameter")
        self.tips.setPlainText(tips)
        self.tips.setPlaceholderText("")
        self.save.setText("保存" if config.defaulelang=='zh' else "Save")
        self.api_url.setPlaceholderText("填写http开头的完整地址" if config.defaulelang=='zh' else "Fill in the full address starting with http")
        self.label.setText("自定义TTS API" if config.defaulelang=='zh' else "Customizing TTS-API")
        self.voice_role.setPlaceholderText("填写可用的配音角色名称，以英文逗号分隔多个"  if config.defaulelang=='zh' else "")
        self.label_2.setText("配音角色名称" if config.defaulelang=='zh' else "Fill in the names of the available voiceover characters, separating multiple ones with English commas")
        self.extra.setPlaceholderText("填写通过extra键向api传递的额外参数，为空则传递pyvideotrans" if config.defaulelang=='zh' else "Fill in the extra parameters passed to the api via the extra key, null to pass pyvideotrans")
        self.test.setText("测试Api" if config.defaulelang=='zh' else "Test API" )
    # retranslateUi

