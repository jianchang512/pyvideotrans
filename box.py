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
        
        import qdarkstyle
        main.setStyleSheet("""QToolBar QToolButton {
                  background-color: #32414B;
                  height:35px;
                  margin-bottom:0px;
                  margin-top:8px;
                  margin-left:2px;
                  margin-right:0px;
                  text-align: left;
                }
                QToolBar QToolButton:hover {
                  border: 1px solid #148CD2;
                }
                QToolBar QToolButton:checked {
                  background-color: #19232D;
                  border: 1px solid #148CD2;
                }
                QToolBar QToolButton:checked:hover {
                border: 1px solid #339933;
                }
                QLabel{
                    color: #bbbbbb;
                }
                QLabel#show_tips{
                    color:#bbbbbb
                }
                QLineEdit:hover,QComboBox:hover{
                    border-color: #148cd2;
                }
                QLineEdit[readOnly="true"],QLineEdit[readOnly="true"]:hover {
                    background-color: transparent;  /* 灰色背景 */
                    border-color: transparent;  /* 灰色背景 */
                }
                QLineEdit,QComboBox{
                    background-color: #161E26;
                    border-color: #32414B;
                }
                QLineEdit:disabled {
                    background-color: transparent;  /* 灰色背景 */
                    border-color: transparent;  /* 灰色背景 */
                }
                QComboBox:disabled{
                    background-color: transparent;  /* 灰色背景 */
                    border-color: #273442;  /* 灰色背景 */
                }
                QScrollArea QPushButton{
                    background-color: rgba(50, 65, 75, 0.5);
                    border-radius: 0;
                    opacity: 0.1;
                    text-align:left;
                    padding-left:5px;
                }
                QScrollArea QPushButton:hover{
                    background-color: #19232D;
                }
            """)
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    except:
        pass
    main.show()
    sys.exit(app.exec())
