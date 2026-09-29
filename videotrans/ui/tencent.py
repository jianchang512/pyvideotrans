from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from videotrans.configure.config import tr, ROOT_DIR
from videotrans.util.help_misc import open_url


class Ui_tencent(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setupUi(self)
    def setupUi(self, form):
        self.has_done = False
        form.setObjectName("form")
        form.resize(400, 300)

        self.verticalLayout = QtWidgets.QVBoxLayout(form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout_2 = QtWidgets.QFormLayout()
        self.formLayout_2.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.formLayout_2.setFormAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)
        self.formLayout_2.setObjectName("formLayout_2")
        self.label = QtWidgets.QLabel()
        self.label.setMinimumSize(QtCore.QSize(0, 35))
        self.label.setAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.tencent_SecretId = QtWidgets.QLineEdit()

        self.tencent_SecretId.setMinimumSize(QtCore.QSize(0, 35))
        self.tencent_SecretId.setObjectName("tencent_SecretId")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tencent_SecretId)
        self.verticalLayout.addLayout(self.formLayout_2)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.formLayout.setFormAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.formLayout.setObjectName("formLayout")
        self.label_2 = QtWidgets.QLabel()

        self.label_2.setMinimumSize(QtCore.QSize(0, 35))
        self.label_2.setSizeIncrement(QtCore.QSize(0, 35))
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.tencent_SecretKey = QtWidgets.QLineEdit()

        self.tencent_SecretKey.setMinimumSize(QtCore.QSize(0, 35))
        self.tencent_SecretKey.setObjectName("tencent_SecretKey")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tencent_SecretKey)

        self.verticalLayout.addLayout(self.formLayout)

        self.formLayout_term = QtWidgets.QFormLayout()
        self.label_term = QtWidgets.QLabel()
        self.label_term.setMinimumSize(QtCore.QSize(0, 35))
        self.tencent_term = QtWidgets.QLineEdit()
        self.tencent_term.setMinimumSize(QtCore.QSize(0, 35))
        self.formLayout_term.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_term)
        self.formLayout_term.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tencent_term)

        self.verticalLayout.addLayout(self.formLayout_term)


        h1 = QtWidgets.QHBoxLayout()

        self.set_tencent = QtWidgets.QPushButton()
        self.set_tencent.setMinimumSize(QtCore.QSize(0, 35))
        self.set_tencent.setObjectName("set_tencent")

        self.test = QtWidgets.QPushButton()
        self.test.setObjectName("test_tencent")

        help_btn = QtWidgets.QPushButton()
        help_btn.setMinimumSize(QtCore.QSize(0, 35))
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText(tr("Fill out the tutorial"))
        help_btn.clicked.connect(lambda: open_url(url='https://pyvideotrans.com/tencent'))

        h1.addWidget(self.set_tencent)
        h1.addWidget(self.test)
        h1.addWidget(help_btn)
        self.verticalLayout.addLayout(h1)
        self.retranslateUi(form)
        QtCore.QMetaObject.connectSlotsByName(form)

    def retranslateUi(self, form):
        form.setWindowTitle("腾讯翻译")
        self.label.setText("SecretId")
        self.label_term.setText("术语库id")
        self.tencent_term.setPlaceholderText("术语库id,多个以英文逗号隔开")
        self.label_2.setText("SecretKey")
        self.set_tencent.setText(tr("Save"))
        self.test.setText(tr("Test"))
