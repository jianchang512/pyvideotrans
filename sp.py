# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import threading
from PyQt5.QtWidgets import QApplication
from videotrans.spwin import MainWindow
import qdarkstyle

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        with open(os.path.join(os.getcwd(),'videotrans/styles/style.qss'), 'r', encoding='utf-8') as f:
            main.setStyleSheet(f.read())
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    except:
        pass
    main.show()
    try:
        def init():
            from videotrans.util import tools
            from videotrans.configure import config
            try:
                threading.Thread(target=tools.get_edge_rolelist).start()
                threading.Thread(target=tools.get_elevenlabs_role, args=(True,)).start()
                os.makedirs(config.rootdir + "/models", exist_ok=True)
                os.makedirs(config.rootdir + "/tmp", exist_ok=True)

            except Exception as e:
                pass
        threading.Thread(target=init).start()
    except:
        pass
    sys.exit(app.exec())
