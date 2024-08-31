import json
import os
import shutil
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.util import tools


# 音视频格式转换
def open():
    RESULT_DIR = config.HOME_DIR + "/formatcover"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, videourls=None, target_format=""):
            super().__init__(parent=parent)
            self.videourls = videourls
            self.target_format = target_format.lower()

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

        def run(self):
            try:
                for i, v in enumerate(self.videourls):
                    raw_path = Path(v)
                    # 格式不变直接复制
                    if raw_path.suffix.lower() == self.target_format:
                        shutil.copy2(self.videourls, RESULT_DIR + f'/{raw_path.name}')
                        continue
                    tools.runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(v),
                        RESULT_DIR + f"/{Path(v).stem}.{self.target_format}"
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
            QtWidgets.QMessageBox.critical(formatcoverform, config.transobj['anerror'], d['text'])
            formatcoverform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            formatcoverform.startbtn.setDisabled(False)
            formatcoverform.opendir.setDisabled(False)
        elif d['type'] == 'jd' or d['type'] == 'logs':
            formatcoverform.startbtn.setText(d['text'])
        else:
            formatcoverform.startbtn.setText(config.transobj['zhixingwc'])
            formatcoverform.startbtn.setDisabled(False)
            formatcoverform.opendir.setDisabled(False)
            formatcoverform.videourls = []

    def get_file():
        format_str=" ".join([ '*.'+f  for f in  config.VIDEO_EXTS+config.AUDIO_EXITS])
        fnames, _ = QFileDialog.getOpenFileNames(formatcoverform, config.transobj['selectmp4'],
                                                 config.params['last_opendir'],
                                                 f"Video files({format_str})")
        if len(fnames) < 1:
            return
        formatcoverform.videourls = []
        for it in fnames:
            formatcoverform.videourls.append(it.replace('\\', '/'))

        if len(formatcoverform.videourls) > 0:
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            formatcoverform.pathdir.setText(",".join(formatcoverform.videourls))

    def start():
        if len(formatcoverform.videourls) < 1:
            QMessageBox.critical(formatcoverform, config.transobj['anerror'],
                                 '必须选择音频视频文件' if config.defaulelang == 'zh' else 'Must select videos or audios ')
            return

        formatcoverform.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        formatcoverform.startbtn.setDisabled(True)
        formatcoverform.opendir.setDisabled(True)
        target_format = formatcoverform.formatlist.currentText()
        task = CompThread(parent=formatcoverform, videourls=formatcoverform.videourls, target_format=target_format)
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import FormatcoverForm
    try:
        formatcoverform = config.child_forms.get('formatcoverform')
        if formatcoverform is not None:
            formatcoverform.show()
            formatcoverform.raise_()
            formatcoverform.activateWindow()
            return
        formatcoverform = FormatcoverForm()
        config.child_forms['formatcoverform'] = formatcoverform
        formatcoverform.selectbtn.clicked.connect(lambda: get_file())
        formatcoverform.opendir.clicked.connect(opendir)
        formatcoverform.startbtn.clicked.connect(start)
        formatcoverform.show()
    except Exception:
        pass
