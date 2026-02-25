# 音视频格式转换


def openwin():
    import json
    import os
    import shutil
    from pathlib import Path
    from PySide6.QtCore import QThread, Signal, QUrl,QTimer
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog

    from videotrans.util import contants
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools

    RESULT_DIR = HOME_DIR + "/formatcover"


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
                from videotrans.configure._except import get_msg_from_except
                self.post(type='error', text=get_msg_from_except(e))
            else:
                self.post(type="ok", text='Ended')

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == "error":
            winobj.has_done = True
            tools.show_error(d['text'])
            winobj.startbtn.setText(tr("start operate"))
            winobj.startbtn.setDisabled(False)
            winobj.opendir.setDisabled(False)
        elif d['type'] == 'jd' or d['type'] == 'logs':
            winobj.startbtn.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.startbtn.setText(tr('zhixingwc'))
            winobj.startbtn.setDisabled(False)
            winobj.opendir.setDisabled(False)
            winobj.videourls = []

    def get_file():
        format_str = " ".join(['*.' + f for f in contants.VIDEO_EXTS + contants.AUDIO_EXITS])
        fnames, _ = QFileDialog.getOpenFileNames(winobj, tr('selectmp4'),
                                                 params['last_opendir'],
                                                 f"Video files({format_str})")
        if len(fnames) < 1:
            return
        winobj.videourls = []
        for it in fnames:
            winobj.videourls.append(it.replace('\\', '/'))

        if len(winobj.videourls) > 0:
            params['last_opendir'] = os.path.dirname(fnames[0])
            winobj.pathdir.setText(",".join(winobj.videourls))

    def start():
        winobj.has_done = False
        if len(winobj.videourls) < 1:
            tools.show_error(tr("Must select videos or audio"))
            return

        winobj.startbtn.setText(
            tr("under implementation in progress..."))
        winobj.startbtn.setDisabled(True)
        winobj.opendir.setDisabled(True)
        target_format = winobj.formatlist.currentText()
        task = CompThread(parent=winobj, videourls=winobj.videourls, target_format=target_format)
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component.set_form import FormatcoverForm
    winobj = FormatcoverForm()
    app_cfg.child_forms['fn_formatcover'] = winobj
    winobj.show()
    def _bind():
        Path(RESULT_DIR).mkdir(parents=True,exist_ok=True)
        winobj.selectbtn.clicked.connect(lambda: get_file())
        winobj.opendir.clicked.connect(opendir)
        winobj.startbtn.clicked.connect(start)
    QTimer.singleShot(10,_bind)
