'''
import requests
from PySide6.QtCore import QSettings

from videotrans.configure import config

url=QSettings("Jameson", "VideoTranslate").value("clone_api", "")
print(f'{url=}')
if not url:
    print(config.transobj['bixutianxiecloneapi'])
else:
    try:
        url = url.strip().rstrip('/') + "/init"
        res = requests.get('http://' + url.replace('http://', ''))
        if res.status_code == 200:
            print(res.json)
            print("\nOK\n")
        else:
            raise Exception(f"code={res.status_code},{config.transobj['You must deploy and start the clone-voice service']}")
    except Exception as e:
        print(f'[error]:clone-voice:{str(e)}')


input("Press Enter for quit")
'''

# from videotrans.separate import st
# try:
#     gr = st.uvr(model_name="HP2", save_root="./", inp_path=r'C:/Users/c1/Videos/240.wav')
#     print(next(gr))
#     print(next(gr))
# except Exception as e:
#     msg=f"separate vocal and background music:{str(e)}"
#     #set_process(msg)
#     print(msg)
import sys

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QApplication

def ceshi():
    from you_get.extractors import youtube

    try:
        youtube.download('https://www.youtube.com/watch?v=n4mF5xo5khM',
                         output_dir='.',
                         merge=True,
                         extractor_proxy='http://127.0.0.1:10809'
                         )
    except Exception as e:
        print(e)

class StartWindow(QWidget):
    def __init__(self):
        super(StartWindow, self).__init__()
        # 设置窗口无边框和标题
        # 设置窗口的背景图片
        # 窗口大小
        self.resize(560, 350)
        self.center()
        self.show()
        # 使用QTimer延时显示窗口B
        ceshi()


    def center(self):
        screen=QGuiApplication.primaryScreen()
        qtRect = self.frameGeometry()
        qtRect.moveCenter(screen.availableGeometry().center())
        reso=screen.geometry()
        self.width, self.height=reso.width(), reso.height()
        self.move(qtRect.topLeft())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        startwin = StartWindow()
    except Exception as e:
        print(f"error:{str(e)}")
    sys.exit(app.exec())

