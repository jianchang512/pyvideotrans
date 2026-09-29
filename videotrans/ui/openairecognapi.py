from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from videotrans.configure.config import tr, params, settings, ROOT_DIR
from videotrans.util.help_misc import open_url


class Ui_openairecognapi(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setupUi(self)
    def setupUi(self, form):
        self.has_done = False
        form.setObjectName("form")
        form.resize(600, 500)

        v1 = QtWidgets.QVBoxLayout(form)
        h1 = QtWidgets.QHBoxLayout()
        h2 = QtWidgets.QHBoxLayout()
        h3 = QtWidgets.QHBoxLayout()
        h4 = QtWidgets.QHBoxLayout()
        h5 = QtWidgets.QHBoxLayout()


        self.label = QtWidgets.QLabel()
        self.label.setMinimumSize(QtCore.QSize(0, 35))
        self.label.setObjectName("label")
        self.openairecognapi_url = QtWidgets.QLineEdit()
        self.openairecognapi_url.setMinimumSize(QtCore.QSize(0, 35))
        self.openairecognapi_url.setObjectName("openairecognapi_url")
        h1.addWidget(self.label)
        h1.addWidget(self.openairecognapi_url)
        v1.addLayout(h1)

        self.label_2 = QtWidgets.QLabel()
        self.label_2.setMinimumSize(QtCore.QSize(0, 35))
        self.label_2.setSizeIncrement(QtCore.QSize(0, 35))
        self.label_2.setObjectName("label_2")
        self.openairecognapi_key = QtWidgets.QLineEdit()
        self.openairecognapi_key.setMinimumSize(QtCore.QSize(0, 35))
        self.openairecognapi_key.setObjectName("openairecognapi_key")
        h2.addWidget(self.label_2)
        h2.addWidget(self.openairecognapi_key)
        v1.addLayout(h2)

        self.label_prompt = QtWidgets.QLabel()
        self.label_prompt.setMinimumSize(QtCore.QSize(0, 35))
        self.label_prompt.setSizeIncrement(QtCore.QSize(0, 35))
        self.label_prompt.setObjectName("label_prompt")
        self.openairecognapi_prompt = QtWidgets.QLineEdit()
        self.openairecognapi_prompt.setMinimumSize(QtCore.QSize(0, 35))
        self.openairecognapi_prompt.setObjectName("openairecognapi_prompt")
        h3.addWidget(self.label_prompt)
        h3.addWidget(self.openairecognapi_prompt)
        v1.addLayout(h3)

        self.label_3 = QtWidgets.QLabel()
        self.label_3.setObjectName("label_3")
        self.openairecognapi_model = QtWidgets.QComboBox()
        self.openairecognapi_model.setMinimumSize(QtCore.QSize(0, 35))
        self.openairecognapi_model.setObjectName("openairecognapi_model")
        h4.addWidget(self.label_3)
        h4.addWidget(self.openairecognapi_model)
        v1.addLayout(h4)

        self.label_allmodels = QtWidgets.QLabel()
        self.label_allmodels.setObjectName("label_allmodels")
        self.label_allmodels.setText(
            tr("Fill in all available models, separated by commas. After filling in, you can select them above"))
        v1.addWidget(self.label_allmodels)

        self.edit_allmodels = QtWidgets.QPlainTextEdit()
        self.edit_allmodels.setObjectName("edit_allmodels")
        v1.addWidget(self.edit_allmodels)

        self.set_openairecognapi = QtWidgets.QPushButton()
        self.set_openairecognapi.setMinimumSize(QtCore.QSize(0, 35))
        self.set_openairecognapi.setObjectName("set_openairecognapi")
        h5.addWidget(self.set_openairecognapi)

        self.test_openairecognapi = QtWidgets.QPushButton()
        self.test_openairecognapi.setMinimumSize(QtCore.QSize(0, 30))
        self.test_openairecognapi.setObjectName("test_openairecognapi")
        h5.addWidget(self.test_openairecognapi)

        help_btn = QtWidgets.QPushButton()
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText(tr("Fill out the tutorial"))
        help_btn.clicked.connect(lambda: open_url(url='https://pyvideotrans.com/openairecogn'))
        h5.addWidget(help_btn)
        v1.addLayout(h5)

        self.retranslateUi(form)
        QtCore.QMetaObject.connectSlotsByName(form)

    def update_ui(self):
        allmodels_str = settings.get('openairecognapi_model','')
        allmodels = str(settings.get('openairecognapi_model','')).split(',')
        self.openairecognapi_model.clear()
        self.openairecognapi_model.addItems(allmodels)
        self.edit_allmodels.setPlainText(allmodels_str)

        self.openairecognapi_key.setText(str(params.get("openairecognapi_key",'')))
        self.openairecognapi_prompt.setText(str(params.get("openairecognapi_prompt",'')))
        self.openairecognapi_url.setText(str(params.get("openairecognapi_url",'')))
        if params.get('openairecognapi_model','') in allmodels:
            self.openairecognapi_model.setCurrentText(str(params.get("openairecognapi_model",'')))

    def retranslateUi(self, form):
        form.setWindowTitle(
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
