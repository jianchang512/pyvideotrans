from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from videotrans.configure import config
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
            'OpenAI官方接口无需填写' if config.defaulelang == 'zh' else 'AIs compatible with the ChatGPT also used here')

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
            '填写所有可用模型，以英文逗号分隔，填写后可在上方选择' if config.defaulelang == 'zh' else 'Fill in all available models, separated by commas. After filling in, you can select them above')

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
        help_btn.setText("查看填写教程" if config.defaulelang == 'zh' else "Fill out the tutorial")
        help_btn.clicked.connect(lambda: tools.open_url(url='https://pyvideotrans.com/openairecogn'))

        self.retranslateUi(openairecognapiform)
        QtCore.QMetaObject.connectSlotsByName(openairecognapiform)

    def retranslateUi(self, openairecognapiform):
        openairecognapiform.setWindowTitle(
            "OpenAI API Speech to text" if config.defaulelang != 'zh' else 'OpenAI 在线api语音识别')
        self.label_3.setText('选择模型' if config.defaulelang == 'zh' else "Model")
        self.set_openairecognapi.setText('保存' if config.defaulelang == 'zh' else "Save")
        self.test_openairecognapi.setText('测试' if config.defaulelang == 'zh' else "Test")
        self.openairecognapi_url.setPlaceholderText(
            '若使用OpenAI官方接口，无需填写;第三方api在此填写' if config.defaulelang == 'zh' else 'If using the official OpenAI interface, there is no need to fill it out; Fill in the third-party API here')
        self.openairecognapi_url.setToolTip(
            '若使用OpenAI官方接口，无需填写;第三方api在此填写' if config.defaulelang == 'zh' else 'If using the official OpenAI interface, there is no need to fill it out; Fill in the third-party API here')
        self.openairecognapi_key.setPlaceholderText("Secret key")
        self.openairecognapi_prompt.setPlaceholderText(
            "An optional text to guide the model's style or continue a previous audio segment" if config.defaulelang != 'zh' else '提示词，不懂无需填写')
        self.openairecognapi_key.setToolTip(
            "必须是付费账号，免费账号频率受限无法使用" if config.defaulelang == 'zh' else 'Must be a paid account, free account frequency is limited and cannot be used')
        self.label.setText("API URL")
        self.label_2.setText("SK")
        self.label_prompt.setText("Prompt" if config.defaulelang != 'zh' else '提示词')
