# 从视频分离音频

def openwin():
    import json
    import os
    from pathlib import Path
    from videotrans.configure.config import tr
    from PySide6.QtCore import QThread, Signal, QUrl,QTimer
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog

    from videotrans.configure import config
    from videotrans.util import tools
    RESULT_DIR = config.HOME_DIR + "/audiofromvideo"


    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, videourls=None, export_video):
            super().__init__(parent=parent)
            self.videourls = videourls
            self.export_video = export_video

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
                    if self.export_video:
                        tools.runffmpeg([
                            "-y",
                            "-i",
                            os.path.normpath(v),
                            "-an",
                            "-c:v",
                            "copy",
                            RESULT_DIR + f"/{Path(v).stem}-novoice.mp4"
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
            winobj.resultbtn.setDisabled(False)
        elif d['type'] == 'jd' or d['type'] == 'logs':
            winobj.startbtn.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.startbtn.setText(tr('zhixingwc'))
            winobj.startbtn.setDisabled(False)
            winobj.resultbtn.setDisabled(False)
            winobj.videourls = []

    def get_file():
        format_str = " ".join(['*.' + f for f in config.VIDEO_EXTS])
        fnames, _ = QFileDialog.getOpenFileNames(winobj, tr('selectmp4'),
                                                 config.params['last_opendir'],
                                                 f"Video files({format_str})")
        if len(fnames) < 1:
            return
        winobj.videourls = []
        for it in fnames:
            winobj.videourls.append(it.replace('\\', '/'))

        if len(winobj.videourls) > 0:
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            winobj.videourl.setText(",".join(winobj.videourls))

    def start():
        if len(winobj.videourls) < 1:
            tools.show_error(tr("Must select video"))
            return
        winobj.has_done = False

        winobj.startbtn.setText(
            tr("under implementation in progress..."))
        winobj.startbtn.setDisabled(True)
        winobj.resultbtn.setDisabled(True)
        task = CompThread(parent=winobj, videourls=winobj.videourls, export_video=winobj.getvideo.isChecked())
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component.set_form import GetaudioForm
    winobj = GetaudioForm()
    config.child_forms['fn_audiofromvideo'] = winobj
    winobj.show()
    def _bind():
        Path(RESULT_DIR).mkdir(exist_ok=True)
        winobj.videobtn.clicked.connect(lambda: get_file())
        winobj.resultbtn.clicked.connect(opendir)
        winobj.startbtn.clicked.connect(start)
    QTimer.singleShot(10,_bind)