# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'downmodel.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (QMetaObject, QSize, Qt)
from PySide6.QtGui import (QCursor)
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit,
                               QPushButton,
                               QVBoxLayout)

from videotrans.configure import config
from videotrans.util import tools


class Ui_downmodel(object):
    def setupUi(self, downmodel):
        self.has_done=False
        if not downmodel.objectName():
            downmodel.setObjectName(u"downmodel")
        downmodel.resize(643, 400)
        downmodel.setWindowModality(QtCore.Qt.NonModal)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setHeightForWidth(downmodel.sizePolicy().hasHeightForWidth())
        downmodel.setSizePolicy(sizePolicy)


        self.verticalLayout = QVBoxLayout(downmodel)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.hlayout_name = QHBoxLayout()
        self.hlayout_name.setObjectName(u"hlayout_name")
        self.label_name = QLabel()
        self.hlayout_name.addWidget(self.label_name)

        self.hlayout_url = QHBoxLayout()
        self.hlayout_url.setObjectName(u"hlayout_url")
        self.url = QLineEdit()
        self.url.setObjectName(u"url")
        self.url.setMinimumSize(QSize(0, 35))
        self.url.setReadOnly(True)
        self.hlayout_url.addWidget(self.url)
        self.verticalLayout.addLayout(self.hlayout_name)
        self.verticalLayout.addLayout(self.hlayout_url)

        self.hlayout_btn = QHBoxLayout()
        self.hlayout_btn.setObjectName(u"hlayout_btn")

        self.down_btn = QPushButton()
        self.down_btn.setObjectName(u"down_btn")
        self.down_btn.setMinimumSize(QSize(200, 35))
        self.down_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.down_btn.setMouseTracking(False)
        self.hlayout_btn.addWidget(self.down_btn)
        self.verticalLayout.addLayout(self.hlayout_btn)

        self.hlayout_page = QHBoxLayout()
        self.hlayout_page.setObjectName(u"hlayout_page")
        self.down_page = QPushButton()
        self.down_page.setObjectName(u"down_page")
        self.down_page.setMinimumSize(QSize(0, 35))
        self.down_page.setCursor(Qt.PointingHandCursor)
        self.down_page.setStyleSheet("""background-color:transparent""")
        self.down_page.setText(
            f'打开所有模型下载网页 https://pyvideotrans.com/model' if config.defaulelang == 'zh' else f'Click to open all models download page https://pyvideotrans.com/model')
        self.down_page.clicked.connect(lambda: tools.open_url('https://pyvideotrans.com/model'))
        self.hlayout_page.addWidget(self.down_page)
        self.verticalLayout.addLayout(self.hlayout_page)

        self.text_help = QtWidgets.QPlainTextEdit( )
        self.text_help.setReadOnly(True)
        self.text_help.setMinimumSize(QSize(0, 150))
        self.verticalLayout.addWidget(self.text_help)

        self.retranslateUi(downmodel)

        QMetaObject.connectSlotsByName(downmodel)

    def retranslateUi(self, downmodel):
        downmodel.setWindowTitle("下载模型" if config.defaulelang == 'zh' else 'Download Models')
        self.down_btn.setText("点击打开浏览器下载" if config.defaulelang == 'zh' else 'Click to open browser to download')
