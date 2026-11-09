from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from videotrans.configure.config import ROOT_DIR, params, settings, tr
from videotrans.configure.constants import WORLDROUTER_MODELS
from videotrans.util.help_misc import open_url


class Ui_worldrouter(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setWindowTitle("WorldRouter")
        self.resize(600, 520)
        layout = QtWidgets.QVBoxLayout(self)

        website = QtWidgets.QPushButton("WorldRouter")
        website.clicked.connect(lambda: open_url(url='https://router.worldclaw.ai'))
        layout.addWidget(website)

        endpoint = QtWidgets.QLabel('https://inference-api.worldrouter.ai/v1')
        endpoint.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(endpoint)

        fields = QtWidgets.QFormLayout()
        self.worldrouter_key = QtWidgets.QLineEdit()
        self.worldrouter_key.setEchoMode(QtWidgets.QLineEdit.Password)
        fields.addRow(tr("SK"), self.worldrouter_key)

        self.worldrouter_model = QtWidgets.QComboBox()
        self.worldrouter_model.setEditable(True)
        fields.addRow(tr("Model"), self.worldrouter_model)

        self.max_token = QtWidgets.QSpinBox()
        self.max_token.setRange(1, 1048576)
        fields.addRow(tr("Maximum output token"), self.max_token)
        layout.addLayout(fields)

        layout.addWidget(QtWidgets.QLabel(tr(
            "Fill in all available models, separated by commas. After filling in, you can select them above"
        )))
        self.edit_allmodels = QtWidgets.QPlainTextEdit()
        layout.addWidget(self.edit_allmodels)

        self.template = QtWidgets.QPlainTextEdit()
        self.template.setReadOnly(True)
        self.template.setPlainText(tr(
            "Prompt: Please open the {} file directly to modify it", 'worldrouter', 'worldrouter'
        ))
        layout.addWidget(self.template)

        buttons = QtWidgets.QHBoxLayout()
        self.set = QtWidgets.QPushButton(tr("Save"))
        self.test = QtWidgets.QPushButton(tr("Test"))
        help_btn = QtWidgets.QPushButton(tr("Fill out the tutorial"))
        help_btn.clicked.connect(lambda: open_url(url='https://router.worldclaw.ai/docs/quickstart'))
        for button in (self.set, self.test, help_btn):
            button.setMinimumHeight(35)
            buttons.addWidget(button)
        layout.addLayout(buttons)

    def update_ui(self):
        allmodels = str(settings.get('worldrouter_model', WORLDROUTER_MODELS))
        # Refreshing an existing dialog must not save settings or reset its selection.
        blocker = QtCore.QSignalBlocker(self.edit_allmodels)
        self.edit_allmodels.setPlainText(allmodels)
        del blocker
        self.worldrouter_model.clear()
        self.worldrouter_model.addItems([model.strip() for model in allmodels.split(',') if model.strip()])
        self.worldrouter_model.setCurrentText(params.get('worldrouter_model', WORLDROUTER_MODELS.split(',')[0]))
        self.worldrouter_key.setText(params.get('worldrouter_key', ''))
        try:
            max_tokens = int(params.get('worldrouter_max_token', 16384))
        except (TypeError, ValueError):
            max_tokens = 16384
        self.max_token.setValue(max_tokens)
