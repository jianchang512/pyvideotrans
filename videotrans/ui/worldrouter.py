from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QIntValidator
from PySide6.QtWidgets import QDialog

from videotrans.configure.config import tr, settings, params, ROOT_DIR
from videotrans.configure.constants import WORLDROUTER_MODELS
from videotrans.util.help_misc import open_url


class Ui_worldrouter(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setupUi(self)
    def setupUi(self, form):
        self.has_done = False
        form.setObjectName("form")
        form.resize(600, 600)

        v1 = QtWidgets.QVBoxLayout(form)

        h3 = QtWidgets.QHBoxLayout()
        h4 = QtWidgets.QHBoxLayout()

        self.label_0 = QtWidgets.QPushButton()
        self.label_0.setGeometry(QtCore.QRect(10, 10, 580, 35))
        self.label_0.setStyleSheet("background-color: rgba(255, 255, 255,0);text-align:left")
        self.label_0.setCursor(Qt.PointingHandCursor)
        self.label_0.setText('WorldRouter')
        self.label_0.clicked.connect(lambda: open_url(url='https://router.worldclaw.ai'))
        v1.addWidget(self.label_0)

        self.label_3 = QtWidgets.QLabel()
        self.label_3.setObjectName("label_3")
        self.worldrouter_key = QtWidgets.QLineEdit()
        self.worldrouter_key.setMinimumSize(QtCore.QSize(0, 35))
        self.worldrouter_key.setObjectName("worldrouter_key")
        self.worldrouter_key.setEchoMode(QtWidgets.QLineEdit.Password)
        h3.addWidget(self.label_3)
        h3.addWidget(self.worldrouter_key)
        v1.addLayout(h3)

        h_token = QtWidgets.QHBoxLayout()

        label_token = QtWidgets.QLabel()
        label_token.setObjectName("label_token")
        label_token.setText(tr("Maximum output token"))
        self.max_token = QtWidgets.QLineEdit()
        self.max_token.setMinimumSize(QtCore.QSize(0, 35))
        self.max_token.setObjectName("max_token")
        self.max_token.setValidator(QIntValidator(1, 1048576, self.max_token))

        h_token.addWidget(label_token)
        h_token.addWidget(self.max_token)
        v1.addLayout(h_token)

        h_model = QtWidgets.QHBoxLayout()
        self.label_selectmodel = QtWidgets.QLabel()
        self.label_selectmodel.setObjectName("label_selectmodel")
        self.label_selectmodel.setText(tr('Text  Or Srt  Translation')+tr("Model"))
        self.worldrouter_model = QtWidgets.QComboBox()
        self.worldrouter_model.setMinimumSize(QtCore.QSize(0, 35))
        self.worldrouter_model.setObjectName("worldrouter_model")
        h_model.addWidget(self.label_selectmodel)
        h_model.addWidget(self.worldrouter_model)
        v1.addLayout(h_model)

        self.label_allmodels = QtWidgets.QLabel()
        self.label_allmodels.setObjectName("label_allmodels")
        self.label_allmodels.setText(
            tr("Fill in all available models, separated by commas. After filling in, you can select them above"))
        v1.addWidget(self.label_allmodels)

        self.edit_allmodels = QtWidgets.QPlainTextEdit()
        self.edit_allmodels.setObjectName("edit_allmodels")
        v1.addWidget(self.edit_allmodels)

        self.label_4 = QtWidgets.QLabel()
        self.label_4.setObjectName("label_4")

        self.template = QtWidgets.QPlainTextEdit()
        self.template.setObjectName("template")
        self.template.setReadOnly(True)
        v1.addWidget(self.label_4)
        v1.addWidget(self.template)

        self.set = QtWidgets.QPushButton()
        self.set.setMinimumSize(QtCore.QSize(0, 35))
        self.set.setObjectName("set")

        self.test = QtWidgets.QPushButton()
        self.test.setMinimumSize(QtCore.QSize(0, 30))
        self.test.setObjectName("test")
        self.test.setText(tr("Test"))

        help_btn = QtWidgets.QPushButton()
        help_btn.setMinimumSize(QtCore.QSize(0, 35))
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText(tr("Fill out the tutorial"))
        help_btn.clicked.connect(lambda: open_url(url='https://router.worldclaw.ai/docs/quickstart'))

        h4.addWidget(self.set)
        h4.addWidget(self.test)
        h4.addWidget(help_btn)
        v1.addLayout(h4)
        self.template.setPlainText(tr("Prompt: Please open the {} file directly to modify it", 'worldrouter', 'worldrouter'))

        self.retranslateUi(form)
        QtCore.QMetaObject.connectSlotsByName(form)

    def update_ui(self):
        allmodels_str = str(settings.get('worldrouter_model', WORLDROUTER_MODELS))
        allmodels = [model.strip() for model in allmodels_str.split(',') if model.strip()]
        current_model = str(params.get('worldrouter_model', WORLDROUTER_MODELS.split(',')[0]))
        # Preserve a previously saved custom model when upgrading the settings UI.
        if current_model and current_model not in allmodels:
            allmodels.append(current_model)
        self.worldrouter_model.clear()
        self.worldrouter_model.addItems(allmodels)
        blocker = QtCore.QSignalBlocker(self.edit_allmodels)
        self.edit_allmodels.setPlainText(','.join(allmodels))
        del blocker
        self.worldrouter_key.setText(str(params.get('worldrouter_key', '')))
        self.worldrouter_model.setCurrentText(current_model)
        self.max_token.setText(str(params.get('worldrouter_max_token', 16384)))

    def retranslateUi(self, form):
        form.setWindowTitle("WorldRouter")
        self.label_3.setText(tr("SK"))
        self.label_4.setText(tr("{lang} represents the target language name, do not delete it."))
        self.set.setText(tr('Save'))
