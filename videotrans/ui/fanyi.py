# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fanyisrt.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (QMetaObject)

from videotrans.configure import config
from videotrans.configure.config import box_lang


class Ui_fanyisrt(object):
    def setupUi(self, fanyisrt):
        if not fanyisrt.objectName():
            fanyisrt.setObjectName(u"fanyisrt")
        fanyisrt.resize(760, 535)
        fanyisrt.setWindowModality(QtCore.Qt.NonModal)

        self.files=[]

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(fanyisrt.sizePolicy().hasHeightForWidth())
        fanyisrt.setSizePolicy(sizePolicy)


        # start
        self.horizontalLayout_23 = QtWidgets.QHBoxLayout(fanyisrt)
        self.horizontalLayout_23.setObjectName("horizontalLayout_23")

        self.verticalLayout_13 = QtWidgets.QVBoxLayout()
        self.verticalLayout_13.setObjectName("verticalLayout_13")

        self.horizontalLayout_18 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_18.setObjectName("horizontalLayout_18")

        self.label_13 = QtWidgets.QLabel()
        self.label_13.setObjectName("label_13")
        self.horizontalLayout_18.addWidget(self.label_13)

        self.fanyi_translate_type = QtWidgets.QComboBox()
        self.fanyi_translate_type.setMinimumSize(QtCore.QSize(100, 30))
        self.fanyi_translate_type.setObjectName("fanyi_translate_type")
        self.horizontalLayout_18.addWidget(self.fanyi_translate_type)

        self.label_613 = QtWidgets.QLabel()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_613.sizePolicy().hasHeightForWidth())
        self.label_613.setSizePolicy(sizePolicy)
        self.label_613.setMinimumSize(QtCore.QSize(0, 30))
        self.label_613.setObjectName("label_613")
        self.horizontalLayout_18.addWidget(self.label_613)


        self.fanyi_target = QtWidgets.QComboBox()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fanyi_target.sizePolicy().hasHeightForWidth())
        self.fanyi_target.setSizePolicy(sizePolicy)
        self.fanyi_target.setMinimumSize(QtCore.QSize(120, 30))
        self.fanyi_target.setObjectName("fanyi_target")
        self.horizontalLayout_18.addWidget(self.fanyi_target)
        self.label_614 = QtWidgets.QLabel()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_614.sizePolicy().hasHeightForWidth())
        self.label_614.setSizePolicy(sizePolicy)
        self.label_614.setMinimumSize(QtCore.QSize(0, 30))
        self.label_614.setObjectName("label_614")
        self.horizontalLayout_18.addWidget(self.label_614)


        self.fanyi_proxy = QtWidgets.QLineEdit()
        self.fanyi_proxy.setMinimumSize(QtCore.QSize(0, 30))
        self.fanyi_proxy.setObjectName("fanyi_proxy")
        self.horizontalLayout_18.addWidget(self.fanyi_proxy)


        self.verticalLayout_13.addLayout(self.horizontalLayout_18)

        self.loglabel=QtWidgets.QLabel()
        self.loglabel.setStyleSheet('''color:#148cd2''')
        self.verticalLayout_13.addWidget(self.loglabel)


        self.horizontalLayout_19 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_19.setContentsMargins(-1, 20, -1, -1)
        self.horizontalLayout_19.setObjectName("horizontalLayout_19")
        self.fanyi_import = QtWidgets.QPushButton()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fanyi_import.sizePolicy().hasHeightForWidth())
        self.fanyi_import.setSizePolicy(sizePolicy)
        self.fanyi_import.setMinimumSize(QtCore.QSize(200, 30))
        self.fanyi_import.setObjectName("fanyi_import")

        self.horizontalLayout_19.addWidget(self.fanyi_import)
        self.daochu = QtWidgets.QToolButton()
        self.daochu.setMinimumSize(QtCore.QSize(0, 28))
        self.daochu.setObjectName("daochu")
        self.horizontalLayout_19.addStretch()
        self.horizontalLayout_19.addWidget(self.daochu)
        self.verticalLayout_13.addLayout(self.horizontalLayout_19)



        self.fanyi_layout = QtWidgets.QHBoxLayout()
        self.fanyi_layout.setObjectName("fanyi_layout")
        self.fanyi_start = QtWidgets.QPushButton()
        self.fanyi_start.setMinimumSize(QtCore.QSize(120, 30))
        self.fanyi_start.setObjectName("fanyi_start")
        self.fanyi_layout.addWidget(self.fanyi_start)
        self.fanyi_targettext = QtWidgets.QPlainTextEdit()
        self.fanyi_targettext.setObjectName("fanyi_targettext")
        self.fanyi_layout.addWidget(self.fanyi_targettext)
        self.verticalLayout_13.addLayout(self.fanyi_layout)
        self.reslabel=QtWidgets.QLabel()

        self.verticalLayout_13.addWidget(self.reslabel)

        self.horizontalLayout_23.addLayout(self.verticalLayout_13)



        # end

        self.retranslateUi(fanyisrt)

        QMetaObject.connectSlotsByName(fanyisrt)

    # setupUi

    def retranslateUi(self, fanyisrt):
        fanyisrt.setWindowTitle("批量字幕翻译" if config.defaulelang == 'zh' else 'Translation Subtitles')
        self.label_13.setText(box_lang.get("Translation channels"))
        self.label_613.setText(box_lang.get("Target lang"))
        self.label_614.setText(box_lang.get("Proxy"))
        self.fanyi_proxy.setPlaceholderText(
            box_lang.get("Failed to access Google services. Please set up the proxy correctly"))
        self.fanyi_import.setText(box_lang.get("Import text to be translated from a file.."))
        self.daochu.setText(config.transobj['dakaizimubaocunmulu'])
        self.fanyi_start.setText(box_lang.get("Start>"))
        self.fanyi_targettext.setPlaceholderText(box_lang.get("The translation result is displayed here"))

