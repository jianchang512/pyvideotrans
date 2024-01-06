# -*- coding: utf-8 -*-
import os
import shutil
import sys
import threading
from PyQt5.QtWidgets import QApplication, QMessageBox

from videotrans.box.win import MainWindow
from videotrans.configure import  config
from videotrans.configure.config import  homedir
from videotrans.util.tools import  set_proxy,  get_edge_rolelist
from videotrans.configure.config import transobj

if config.is_vlc:
    try:
        import vlc
    except:
        config.is_vlc = False
        class vlc():
            pass




if __name__ == "__main__":
    threading.Thread(target=get_edge_rolelist)

    if not os.path.exists(homedir):
        os.makedirs(homedir, exist_ok=True)
    if not os.path.exists(homedir + "/tmp"):
        os.makedirs(homedir + "/tmp", exist_ok=True)

    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        with open(f'{config.rootdir}/videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
            main.setStyleSheet(f.read())
        import qdarkstyle

        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    except:
        pass

    main.show()
    threading.Thread(target=set_proxy).start()
    if shutil.which('ffmpeg') is None:
        QMessageBox.critical(main, transobj['anerror'], transobj['ffmpegno'])

    sys.exit(app.exec())
