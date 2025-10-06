from PySide6 import  QtWidgets
from PySide6.QtCore import (QMetaObject, QSize, Qt)
from PySide6.QtGui import (QCursor)
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit,
                               QPushButton,
                               QVBoxLayout, QCheckBox)

from videotrans.configure.config import tr


class Ui_videoandaudio(object):
    def setupUi(self, videoandaudio):
        self.has_done = False
        if not videoandaudio.objectName():
            videoandaudio.setObjectName(u"videoandaudio")
        videoandaudio.setMinimumSize(700, 300)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setHeightForWidth(videoandaudio.sizePolicy().hasHeightForWidth())
        videoandaudio.setSizePolicy(sizePolicy)


        self.horizontalLayout_3 = QHBoxLayout(videoandaudio)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")

        self.folder = QLineEdit()
        self.folder.setObjectName(u"folder")
        self.folder.setMinimumSize(QSize(0, 35))
        self.folder.setReadOnly(True)

        self.labeltips = QLabel()
        self.labeltips.setStyleSheet("color:#999999")

        self.horizontalLayout.addWidget(self.folder)

        self.videobtn = QPushButton()
        self.videobtn.setObjectName(u"videobtn")
        self.videobtn.setMinimumSize(QSize(180, 35))
        self.videobtn.setCursor(QCursor(Qt.PointingHandCursor))
        self.videobtn.setMouseTracking(False)
        self.horizontalLayout.addWidget(self.videobtn)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout.addWidget(self.labeltips)

        self.startbtn = QPushButton()
        self.startbtn.setObjectName(u"startbtn")
        self.startbtn.setMinimumSize(QSize(150, 35))
        self.startbtn.setCursor(QCursor(Qt.PointingHandCursor))

        self.remain = QCheckBox()
        self.remain.setChecked(False)

        label_audio = QtWidgets.QLabel()
        label_audio.setText(tr("Audio duration > video"))
        self.audio_process = QtWidgets.QComboBox()
        self.audio_process.addItems([
            tr("Truncate"),
            tr("Auto Accelerate")
        ])

        self.h2 = QHBoxLayout()
        self.h2.addWidget(self.remain)
        self.h2.addWidget(label_audio)
        self.h2.addWidget(self.audio_process)
        self.h2.addStretch()

        h3 = QHBoxLayout()
        h3.addStretch()
        h3.addWidget(self.startbtn)
        h3.addStretch()
        self.verticalLayout.addLayout(self.h2)
        self.verticalLayout.addLayout(h3)

        self.resultbtn = QPushButton()
        self.resultbtn.setObjectName(u"resultbtn")
        self.resultbtn.setStyleSheet("""background-color:transparent""")
        self.resultbtn.setMinimumSize(QSize(0, 30))
        self.resultbtn.setCursor(QCursor(Qt.PointingHandCursor))

        self.loglabel = QLabel()
        self.loglabel.setStyleSheet('''color:#148cd2''')
        self.verticalLayout.addWidget(self.loglabel)

        self.verticalLayout.addStretch()

        self.verticalLayout.addWidget(self.resultbtn)
        self.horizontalLayout_3.addLayout(self.verticalLayout)

        videoandaudio.setWindowTitle(tr("video/audio merger"))
        self.retranslateUi()

        QMetaObject.connectSlotsByName(videoandaudio)

    def retranslateUi(self):
        self.folder.setPlaceholderText(
            tr("Select the folder where you want to merge the video and audio"))
        self.videobtn.setText(tr("Select the folder"))
        self.startbtn.setText(tr("Start of execution"))
        self.resultbtn.setText(tr("Open the save results directory"))
        self.labeltips.setText(
            tr("Will merge video and audio with the same name in that folder, e.g. 1.mp4 and 1.wav"))
        self.remain.setText(tr("Preserve the original sound in the video"))
