from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from videotrans.configure.config import tr, ROOT_DIR
from videotrans.configure.constants import  CAMBAI_ASR_MODELS
from videotrans.util.help_misc import open_url


class Ui_camb(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setupUi(self)

    def setupUi(self, form):
        self.has_done = False
        form.setObjectName("form")
        form.resize(400, 260)

        self.verticalLayout = QtWidgets.QVBoxLayout(form)
        self.verticalLayout.setObjectName("verticalLayout")

        # API Key row
        self.formLayout_2 = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel()
        self.label.setMinimumSize(QtCore.QSize(100, 35))
        self.label.setObjectName("label")
        self.camb_api_key = QtWidgets.QLineEdit()
        self.camb_api_key.setMinimumSize(QtCore.QSize(210, 35))
        self.camb_api_key.setObjectName("camb_api_key")
        self.formLayout_2.addWidget(self.label)
        self.formLayout_2.addWidget(self.camb_api_key)

        self.verticalLayout.addLayout(self.formLayout_2)

        # Buttons
        self.set = QtWidgets.QPushButton()
        self.set.setMinimumSize(QtCore.QSize(0, 35))
        self.set.setObjectName("set")

        self.test = QtWidgets.QPushButton()
        self.test.setMinimumSize(QtCore.QSize(0, 35))
        self.test.setObjectName("test")

        help_btn = QtWidgets.QPushButton()
        help_btn.setMinimumSize(QtCore.QSize(0, 35))
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText(tr("Fill out the tutorial"))
        help_btn.clicked.connect(lambda: open_url(url='https://www.camb.ai'))

        hv = QtWidgets.QHBoxLayout()
        hv.addWidget(self.set)
        hv.addWidget(self.test)
        hv.addWidget(help_btn)

        self.verticalLayout.addLayout(hv)

        self.retranslateUi(form)
        QtCore.QMetaObject.connectSlotsByName(form)

    def retranslateUi(self, form):
        form.setWindowTitle("CAMB AI TTS")
        self.label.setText("API_KEY")
        self.set.setText(tr("Save"))
        self.test.setText(tr("Test & get roles"))
