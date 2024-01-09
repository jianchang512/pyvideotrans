# -*- coding: utf-8 -*-
import os
import sys
from PyQt5.QtWidgets import QApplication
from videotrans.box.win import MainWindow
from videotrans.configure import  config
from videotrans.configure.config import  homedir


if __name__ == "__main__":
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
    sys.exit(app.exec())
