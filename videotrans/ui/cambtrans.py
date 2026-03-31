from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from videotrans.configure.config import tr, app_cfg, params, settings, logger
from videotrans.util import tools


class Ui_cambtransform(object):
    def setupUi(self, cambtransform):
        self.has_done = False
        cambtransform.setObjectName("cambtransform")
        cambtransform.setWindowModality(QtCore.Qt.NonModal)
        cambtransform.resize(400, 160)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(cambtransform.sizePolicy().hasHeightForWidth())
        cambtransform.setSizePolicy(sizePolicy)
        cambtransform.setMaximumSize(QtCore.QSize(400, 200))

        self.verticalLayout = QtWidgets.QVBoxLayout(cambtransform)
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

        help_btn = QtWidgets.QPushButton()
        help_btn.setMinimumSize(QtCore.QSize(0, 35))
        help_btn.setStyleSheet("background-color: rgba(255, 255, 255,0)")
        help_btn.setObjectName("help_btn")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setText(tr("Fill out the tutorial"))
        help_btn.clicked.connect(lambda: tools.open_url(url='https://www.camb.ai'))

        hv = QtWidgets.QHBoxLayout()
        hv.addWidget(self.set)
        hv.addWidget(help_btn)

        self.verticalLayout.addLayout(hv)

        self.retranslateUi(cambtransform)
        QtCore.QMetaObject.connectSlotsByName(cambtransform)

    def retranslateUi(self, cambtransform):
        cambtransform.setWindowTitle("CAMB AI Translation")
        self.label.setText("API_KEY")
        self.set.setText(tr("Save"))
