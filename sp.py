# -*- coding: utf-8 -*-
import shutil
import sys
import os
import threading
from PyQt5.QtWidgets import  QApplication, QMessageBox
import warnings
from videotrans.spwin import MainWindow

warnings.filterwarnings('ignore')
from videotrans.configure.config import  transobj
from videotrans.util.tools import get_edge_rolelist, is_vlc, get_elevenlabs_role
from videotrans.configure import config


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
        threading.Thread(target=get_edge_rolelist).start()
        threading.Thread(target=get_elevenlabs_role,args=(True,)).start()
        threading.Thread(target=is_vlc).start()
    except:
        pass
    sys.exit(app.exec())
