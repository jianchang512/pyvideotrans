from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from videotrans.configure.config import tr,app_cfg,params,settings,logger
from videotrans.util import tools


class Ui_openairecognapiform(object):
    def setupUi(self, openairecognapiform):
        self.has_done = False
        openairecognapiform.setObjectName("openairecognapiform")
        openairecognapiform.setWindowModality(QtCore.Qt.NonModal)
        openairecognapiform.resize(600, 500)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(openairecognapiform.sizePolicy().hasHeightForWidth())
        openairecognapiform.setSizePolicy(sizePolicy)
        openairecognapiform.setMaximumSize(QtCore.QSize(600, 600))

        self.label_0 = QtWidgets.QLabel(openairecognapiform)
        self.label_0.setGeometry(QtCore.QRect(10, 10, 580, 35))
        self.label_0.setText(
            tr("AIs compatible with the ChatGPT also used here"))

        self.label = QtWidgets.QLabel(openairecognapiform)
        self.label.setGeometry(QtCore.QRect(10, 45, 130, 35))
        self.label.setMinimumSize(QtCore.QSize(0, 35))
        self.label.setObjectName("label")
        self.openairecognapi_url = QtWidgets.QLineEdit(openairecognapiform)
        self.openairecognapi_url.setGeometry(QtCore.QRect(150, 45, 431, 35))
        self.openairecognapi_url.setMinimumSize(QtCore.QSize(0, 35))
        self.openairecognapi_url.setObjectName("openairecognapi_url")

        self.label_2 = QtWidgets.QLabel(openairecognapiform)
        self.label_2.setGeometry(QtCore.QRect(10, 95, 130, 35))
        self.label_2.setMinimumSize(QtCore.QSize(0, 35))
        self.label_2.setSizeIncrement(QtCore.QSize(0, 35))
        self.label_2.setObjectName("label_2")
        self.openairecognapi_key = QtWidgets.QLineEdit(openairecognapiform)
        self.openairecognapi_key.setGeometry(QtCore.QRect(150, 95, 431, 35))
        self.openairecognapi_key.setMinimumSize(QtCore.QSize(0, 35))
        self.openairecognapi_key.setObjectName("openairecognapi_key")

        self.label_prompt = QtWidgets.QLabel(openairecognapiform)
        self.label_prompt.setGeometry(QtCore.QRect(10, 140, 130, 35))
        self.label_prompt.setMinimumSize(QtCore.QSize(0, 35))
        self.label_prompt.setSizeIncrement(QtCore.QSize(0, 35))
        self.label_prompt.setObjectName("label_prompt")
        self.openairecognapi_prompt = QtWidgets.QLineEdit(openairecognapiform)
        self.openairecognapi_prompt.setGeometry(QtCore.QRect(150, 140, 431, 35))
        self.openairecognapi_prompt.setMinimumSize(QtCore.QSize(0, 35))
        self.openairecognapi_prompt.setObjectName("openairecognapi_prompt")

        self.label_3 = QtWidgets.QLabel(openairecognapiform)
        self.label_3.setGeometry(QtCore.QRect(10, 190, 121, 16))
        self.label_3.setObjectName("label_3")
        self.openairecognapi_model = QtWidgets.QComboBox(openairecognapiform)
        self.openairecognapi_model.setGeometry(QtCore.QRect(150, 185, 431, 35))
        self.openairecognapi_model.setMinimumSize(QtCore.QSize(0, 35))
        self.openairecognapi_model.setObjectName("openairecognapi_model")

        self.label_allmodels = QtWidgets.QLabel(openairecognapiform)
        self.label_allmodels.setGeometry(QtCore.QRect(10, 220, 571, 21))
        self.label_allmodels.setObjectName("label_allmodels")
        self.label_allmodels.setText(
            tr("Fill in all available models, separated by commas. After filling in, you can select them above"))

        self.edit_allmodels = QtWidgets.QPlainTextEdit(openairecognapiform)
        self.edit_allmodels.setGeometry(QtCore.QRect(10, 250, 571, 100))
        self.edit_allmodels.setObjectName("edit_allmodels")

        self.set_openairecognapi = QtWidgets.QPushButton(openairecognapiform)
        self.set_openairecognapi.setGeometry(QtCore.QRect(10, 410, 93, 35))
        self.set_openairecognapi.setMinimumSize(QtCore.QSize(0, 35))
        self.set_openairecognapi.setObjectName("set_openairecognapi")

        self.test_openairecognapi = QtWidgets.QPushButton(openairecognapiform)
        self.test_openairecognapi.setGeometry(QtCore.QRect(130, 415, 93, 30))
        self.test_openairecognapi.setMinimumSize(QtCore.QSize(0, 30))
        self.test_openairecognapi.setObjectName("test_openairecognapi")

        help_btn = QtWidgets.QPushButton(openairecognapiform)
        help_btn.setGeometry(QtCore.QRect(250, 415, 120, 30))
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText(tr("Fill out the tutorial"))
        help_btn.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/openairecogn'))

        self.retranslateUi(openairecognapiform)
        QtCore.QMetaObject.connectSlotsByName(openairecognapiform)

    def update_ui(self):
        allmodels_str = settings.get('openairecognapi_model','')
        allmodels = str(settings.get('openairecognapi_model','')).split(',')
        self.openairecognapi_model.clear()
        self.openairecognapi_model.addItems(allmodels)
        self.edit_allmodels.setPlainText(allmodels_str)

        self.openairecognapi_key.setText(params.get("openairecognapi_key",''))
        self.openairecognapi_prompt.setText(params.get("openairecognapi_prompt",''))
        self.openairecognapi_url.setText(params.get("openairecognapi_url",''))
        if params.get('openairecognapi_model','') in allmodels:
            self.openairecognapi_model.setCurrentText(params.get("openairecognapi_model",''))

    def retranslateUi(self, openairecognapiform):
        openairecognapiform.setWindowTitle(
            tr("OpenAI API Speech to text"))
        self.label_3.setText(tr("Model"))
        self.set_openairecognapi.setText(tr("Save"))
        self.test_openairecognapi.setText(tr("Test"))
        self.openairecognapi_url.setPlaceholderText(
            tr("If using the official OpenAI interface, there is no need to fill it out; Fill in the third-party API here"))
        self.openairecognapi_url.setToolTip(
            tr("If using the official OpenAI interface, there is no need to fill it out; Fill in the third-party API here"))
        self.openairecognapi_key.setPlaceholderText("Secret key")
        self.openairecognapi_key.setToolTip(
            tr("Must be a paid account, free account frequency is limited and cannot be used"))
        self.label.setText(tr("API URL"))
        self.label_2.setText(tr("SK"))
        self.label_prompt.setText(tr("Prompt"))
