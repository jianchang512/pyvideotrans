import json
import os
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.util import tools


# 从视频分离音频
def open():
    RESULT_DIR=config.homedir + "/audiofromvideo"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, videourls=None):
            super().__init__(parent=parent)
            self.videourls = videourls

        def post(self,type='logs',text=""):
            self.uito.emit(json.dumps({"type":type,"text":text}))

        def run(self):
            try:

                for i, v in enumerate(self.videourls):
                    tools.runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(v),
                        "-vn",
                        "-ac",
                        "2",
                        "-ar",
                        "44100",
                        "-c:a",
                        "pcm_s16le",
                        RESULT_DIR + f"/{Path(v).stem}.wav"
                    ])
                    jd = round((i + 1) * 100 / len(self.videourls), 2)
                    self.post(type='jd',text=f'{jd}%')
            except Exception as e:
                self.post(type='error',text=str(e))
            else:
                self.post(type="ok",text='Ended')

    def feed(d):
        d=json.loads(d)
        if d['type']=="error":
            QtWidgets.QMessageBox.critical(config.audioform, config.transobj['anerror'], d['text'])
            config.audioform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            config.audioform.startbtn.setDisabled(False)
            config.audioform.resultbtn.setDisabled(False)
        elif d['type']=='jd' or d['type']=='logs':
            config.audioform.startbtn.setText(d['text'])
        else:
            config.audioform.startbtn.setText('执行完成/开始执行' if config.defaulelang == 'zh' else 'Ended/Start operate')
            config.audioform.startbtn.setDisabled(False)
            config.audioform.resultbtn.setDisabled(False)
            config.audioform.videourls = []

    def get_file():
        fnames, _ = QFileDialog.getOpenFileNames(config.audioform, config.transobj['selectmp4'],
                                                 config.params['last_opendir'],
                                                 "Video files(*.mp4 *.avi *.mov *.mpg *.mkv)")
        if len(fnames) < 1:
            return
        config.audioform.videourls = []
        for it in fnames:
            config.audioform.videourls.append(it.replace('\\', '/'))

        if len(config.audioform.videourls) > 0:
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            config.audioform.videourl.setText(",".join(config.audioform.videourls))

    def start():
        if len(config.audioform.videourls) < 1:
            QMessageBox.critical(config.audioform, config.transobj['anerror'],
                                 '必须选择视频' if config.defaulelang == 'zh' else 'Must select video ')
            return

        config.audioform.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        config.audioform.startbtn.setDisabled(True)
        config.audioform.resultbtn.setDisabled(True)
        task = CompThread(parent=config.audioform, videourls=config.audioform.videourls)
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import GetaudioForm
    try:
        if config.audioform is not None:
            config.audioform.show()
            config.audioform.raise_()
            config.audioform.activateWindow()
            return
        config.audioform = GetaudioForm()
        config.audioform.videobtn.clicked.connect(lambda: get_file())
        config.audioform.resultbtn.clicked.connect(opendir)
        config.audioform.startbtn.clicked.connect(start)
        config.audioform.show()
    except Exception:
        pass
