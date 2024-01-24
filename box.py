# -*- coding: utf-8 -*-
import os
import sys
from PyQt5.QtWidgets import QApplication
from videotrans.box.win import MainWindow
from videotrans.configure import config


if __name__ == "__main__":
    if not os.path.exists(config.homedir):
        os.makedirs(config.homedir, exist_ok=True)
    if not os.path.exists(config.homedir + "/tmp"):
        os.makedirs(config.homedir + "/tmp", exist_ok=True)

    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        with open(os.path.join(os.getcwd(), 'videotrans/styles/style.qss'), 'r', encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except:
        pass
    main.show()
    sys.exit(app.exec())
