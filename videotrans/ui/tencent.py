from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from videotrans.configure import config
from videotrans.util import tools


class Ui_tencentform(object):
    def setupUi(self, tencentform):
        self.has_done = False
        tencentform.setObjectName("tencentform")
        tencentform.setWindowModality(QtCore.Qt.NonModal)
        tencentform.resize(400, 300)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(tencentform.sizePolicy().hasHeightForWidth())
        tencentform.setSizePolicy(sizePolicy)
        tencentform.setMaximumSize(QtCore.QSize(400, 300))

        self.verticalLayout_2 = QtWidgets.QVBoxLayout(tencentform)
        self.verticalLayout_2.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout_2 = QtWidgets.QFormLayout()
        self.formLayout_2.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.formLayout_2.setFormAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)
        self.formLayout_2.setObjectName("formLayout_2")
        self.label = QtWidgets.QLabel(tencentform)
        self.label.setMinimumSize(QtCore.QSize(100, 35))
        self.label.setAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.tencent_SecretId = QtWidgets.QLineEdit(tencentform)

        self.tencent_SecretId.setMinimumSize(QtCore.QSize(0, 35))
        self.tencent_SecretId.setObjectName("tencent_SecretId")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tencent_SecretId)
        self.verticalLayout.addLayout(self.formLayout_2)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.formLayout.setFormAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.formLayout.setObjectName("formLayout")
        self.label_2 = QtWidgets.QLabel(tencentform)

        self.label_2.setMinimumSize(QtCore.QSize(100, 35))
        self.label_2.setSizeIncrement(QtCore.QSize(0, 35))
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.tencent_SecretKey = QtWidgets.QLineEdit(tencentform)

        self.tencent_SecretKey.setMinimumSize(QtCore.QSize(0, 35))
        self.tencent_SecretKey.setObjectName("tencent_SecretKey")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tencent_SecretKey)

        self.verticalLayout.addLayout(self.formLayout)

        self.formLayout_term = QtWidgets.QFormLayout()
        self.label_term = QtWidgets.QLabel(tencentform)
        self.label_term.setMinimumSize(QtCore.QSize(100, 35))
        self.tencent_term = QtWidgets.QLineEdit(tencentform)
        self.tencent_term.setMinimumSize(QtCore.QSize(0, 35))
        self.formLayout_term.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_term)
        self.formLayout_term.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tencent_term)

        self.verticalLayout.addLayout(self.formLayout_term)

        self.verticalLayout_2.addLayout(self.verticalLayout)

        h1=QtWidgets.QHBoxLayout()

        self.set_tencent = QtWidgets.QPushButton(tencentform)
        self.set_tencent.setMinimumSize(QtCore.QSize(0, 35))
        self.set_tencent.setObjectName("set_tencent")

        self.test = QtWidgets.QPushButton(tencentform)
        self.test.setObjectName("test_tencent")


        help_btn = QtWidgets.QPushButton()
        help_btn.setMinimumSize(QtCore.QSize(0, 35))
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText("查看填写教程" if config.defaulelang == 'zh' else "Fill out the tutorial")
        help_btn.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/tencent'))


        h1.addWidget(self.set_tencent)
        h1.addWidget(self.test)
        h1.addWidget(help_btn)
        self.verticalLayout_2.addLayout(h1)
        self.retranslateUi(tencentform)
        QtCore.QMetaObject.connectSlotsByName(tencentform)

    def retranslateUi(self, tencentform):
        tencentform.setWindowTitle("腾讯翻译")
        self.label.setText("SecretId")
        self.label_term.setText("术语库id")
        self.tencent_term.setPlaceholderText("术语库id,多个以英文逗号隔开")
        self.label_2.setText("SecretKey")
        self.set_tencent.setText('保存' if config.defaulelang == 'zh' else "Save")
        self.test.setText('测试' if config.defaulelang == 'zh' else "Test")
