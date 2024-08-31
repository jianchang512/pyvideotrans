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
    RESULT_DIR = config.HOME_DIR + "/audiofromvideo"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, videourls=None):
            super().__init__(parent=parent)
            self.videourls = videourls

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

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
                    self.post(type='jd', text=f'{jd}%')
            except Exception as e:
                self.post(type='error', text=str(e))
            else:
                self.post(type="ok", text='Ended')

    def feed(d):
        d = json.loads(d)
        if d['type'] == "error":
            QtWidgets.QMessageBox.critical(audioform, config.transobj['anerror'], d['text'])
            audioform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            audioform.startbtn.setDisabled(False)
            audioform.resultbtn.setDisabled(False)
        elif d['type'] == 'jd' or d['type'] == 'logs':
            audioform.startbtn.setText(d['text'])
        else:
            audioform.startbtn.setText(config.transobj['zhixingwc'])
            audioform.startbtn.setDisabled(False)
            audioform.resultbtn.setDisabled(False)
            audioform.videourls = []

    def get_file():
        format_str=" ".join([ '*.'+f  for f in  config.VIDEO_EXTS])
        fnames, _ = QFileDialog.getOpenFileNames(audioform, config.transobj['selectmp4'],
                                                 config.params['last_opendir'],
                                                 f"Video files({format_str})")
        if len(fnames) < 1:
            return
        audioform.videourls = []
        for it in fnames:
            audioform.videourls.append(it.replace('\\', '/'))

        if len(audioform.videourls) > 0:
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            audioform.videourl.setText(",".join(audioform.videourls))

    def start():
        if len(audioform.videourls) < 1:
            QMessageBox.critical(audioform, config.transobj['anerror'],
                                 '必须选择视频' if config.defaulelang == 'zh' else 'Must select video ')
            return

        audioform.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        audioform.startbtn.setDisabled(True)
        audioform.resultbtn.setDisabled(True)
        task = CompThread(parent=audioform, videourls=audioform.videourls)
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import GetaudioForm
    try:
        audioform = config.child_forms.get('audioform')
        if audioform is not None:
            audioform.show()
            audioform.raise_()
            audioform.activateWindow()
            return
        audioform = GetaudioForm()
        config.child_forms['audioform'] = audioform
        audioform.videobtn.clicked.connect(lambda: get_file())
        audioform.resultbtn.clicked.connect(opendir)
        audioform.startbtn.clicked.connect(start)
        audioform.show()
    except Exception:
        pass
