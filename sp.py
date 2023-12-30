# -*- coding: utf-8 -*-
import copy
import datetime
import json
import shutil
import sys
import os
import threading
import webbrowser
import torch

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QTextCursor, QIcon, QDesktopServices
from PyQt5.QtCore import QSettings, QUrl, Qt, QSize, pyqtSlot, QDir
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QLabel, QPushButton, QToolBar, \
    QTextBrowser, QWidget, QVBoxLayout, QSizePolicy
import warnings

from videotrans.component.set_form import InfoForm, AzureForm, GeminiForm
from videotrans.spwin import MainWindow
from videotrans.task.check_update import CheckUpdateWorker
from videotrans.task.logs_worker import LogsWorker
from videotrans.task.main_worker import Worker, Shiting

warnings.filterwarnings('ignore')

from videotrans import VERSION
from videotrans.component import DeepLForm, DeepLXForm, BaiduForm, TencentForm, ChatgptForm
from videotrans.component.controlobj import TextGetdir
from videotrans.configure.config import langlist, transobj, logger, homedir
from videotrans.configure.language import english_code_bygpt
from videotrans.util.tools import show_popup, set_proxy, set_process, get_edge_rolelist, is_vlc
from videotrans.configure import config



def pygameinit():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_allow_screensaver(True)


if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        if not os.path.exists(config.rootdir + "/models"):
            os.mkdir(config.rootdir + "/models")
        if not os.path.exists(config.rootdir + "/tmp"):
            os.makedirs(config.rootdir + "/tmp")
        if shutil.which('ffmpeg') is None:
            QMessageBox.critical(main, transobj['anerror'], transobj["installffmpeg"])
    except Exception as e:
        QMessageBox.critical(main, transobj['anerror'], transobj['createdirerror'])

    # or in new API
    try:
        with open(f'{config.rootdir}/videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
            main.setStyleSheet(f.read())
        import qdarkstyle

        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    except:
        pass

    main.show()
    try:
        import pygame
        threading.Thread(target=pygameinit).start()
        threading.Thread(target=get_edge_rolelist).start()
        threading.Thread(target=is_vlc).start()
    except:
        pass
    sys.exit(app.exec())
