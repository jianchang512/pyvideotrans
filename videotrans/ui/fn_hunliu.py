from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (QMetaObject)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QHBoxLayout, QVBoxLayout)

from videotrans.configure.config import tr, ROOT_DIR
from videotrans.ui._bottom_btn import _Bottom_btn_layout


class Ui_fn_hunliu(QtWidgets.QWidget,_Bottom_btn_layout):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.has_done = False
        self.output_key="hunliu_output_data"
        self.setupUi(self)
    def setupUi(self, hunliu):
        if not hunliu.objectName():
            hunliu.setObjectName(u"hunliu")
        hunliu.setMinimumSize(643, 400)

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

        self.v1.addLayout(self.get_bottom_btn_layout())
        self.v1.addStretch()
        self.horizontalLayout_3.addLayout(self.v1)
        hunliu.setWindowTitle(tr("Mix 2 Audio"))
        self.retranslateUi()
        QMetaObject.connectSlotsByName(hunliu)

    def retranslateUi(self):
        self.l1.setText(tr('Audio')+" 1")
        self.l2.setText(tr('Audio')+" 2")
        self.hun_file1.setPlaceholderText(tr("Select an audio"))
        self.hun_file1btn.setText(tr("Select Audio"))
        self.hun_file2.setPlaceholderText(tr("Select an audio"))
        self.hun_file2btn.setText(tr("Select Audio"))
        self.hun_startbtn.setText(tr("Start operate"))
