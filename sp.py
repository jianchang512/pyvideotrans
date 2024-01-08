# -*- coding: utf-8 -*-
import sys
import os
import threading
from PyQt5.QtWidgets import QApplication
import warnings
from videotrans.spwin import MainWindow
warnings.filterwarnings('ignore')
from videotrans.util.tools import get_edge_rolelist, is_vlc, get_elevenlabs_role
from videotrans.configure import config
import qdarkstyle

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        with open(f'{config.rootdir}/videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
            main.setStyleSheet(f.read())

        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    except:
        pass
    main.show()
    try:
        threading.Thread(target=get_edge_rolelist).start()
        threading.Thread(target=get_elevenlabs_role, args=(True,)).start()
        threading.Thread(target=is_vlc).start()
        def init():
            try:
                os.makedirs(config.rootdir + "/models", exist_ok=True)
                os.makedirs(config.rootdir + "/tmp", exist_ok=True)
            except Exception as e:
                pass
        threading.Thread(target=init).start()
    except:
        pass
    sys.exit(app.exec())
