import builtins
import json
import os
import time
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
# 使用内置的 open 函数
from videotrans.util import tools

builtin_open = builtins.open


# 水印
def open():
    RESULT_DIR = config.HOME_DIR + "/videoandaudio"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, remain=False, folder=None):
            super().__init__(parent=parent)
            self.remain = remain
            self.folder = folder

        # 取出具有相同名称的视频和音频文件，组装为dict待处理
        def get_list(self):
            videos = {}
            audios = {}
            for it in Path(self.folder).iterdir():
                if it.is_file():
                    suffix = it.suffix.lower()
                    if suffix in config.VIDEO_EXTS:
                        videos[it.stem] = it.resolve().as_posix()
                    elif suffix in config.AUDIO_EXITS:
                        audios[it.stem] = it.resolve().as_posix()

            vailfiles = {}
            for key, val in videos.items():
                if key in audios:
                    vailfiles[key] = {"video": val, "audio": audios[key]}
            length = len(vailfiles.keys())
            if length < 1:
                return None, 0
            return vailfiles, length

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

        def run(self) -> None:
            os.chdir(RESULT_DIR)
            # 确保临时目录存在
            os.makedirs(config.TEMP_HOME, exist_ok=True)

            vailfiles, length = self.get_list()
            if not vailfiles:
                self.post(type='error',
                          text='不存在同名视频和音频，无法合并' if config.defaulelang == 'zh' else 'Video and audio of the same name do not exist and cannot be merged')
                return

            percent = 0
            self.post(
                f'有{length}组同名视频和音频需合并' if config.defaulelang == 'zh' else f'There are {length} sets of videos with the same name and audio that need to be merged.')
            for name, info in vailfiles.items():
                result_file = RESULT_DIR + f'/{name}.mp4'
                audio = info['audio']
                try:
                    self.post(f'{Path(audio).name} --> {Path(info["video"]).name} ')
                    if self.remain:
                        # 需要保留原声
                        video_info = tools.get_video_info(info['video'])
                        if video_info['streams_audio']:
                            tmp_mp4 = config.TEMP_HOME + f"/{name}-{time.time()}.m4a"
                            # 存在声音，则需要混合
                            tools.runffmpeg([
                                '-y',
                                '-i',
                                info['video'],
                                "-vn",
                                '-i',
                                audio,
                                '-filter_complex',
                                "[1:a]apad[a1];[0:a][a1]amerge=inputs=2[aout]",
                                '-map',
                                '[aout]',
                                '-ac',
                                '2', tmp_mp4])
                            audio = tmp_mp4

                    tools.runffmpeg([
                        '-y',
                        '-i',
                        info['video'],
                        '-i',
                        os.path.normpath(audio),
                        '-c:v',
                        'copy' if Path(info['video']).suffix.lower() == '.mp4' else 'libx264',
                        "-c:a",
                        "aac",
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-shortest",
                        result_file
                    ])
                except Exception as e:
                    self.post(type='error', text=str(e))
                finally:
                    percent += round(100 / length, 2)
                    self.post(type='jd', text=f'{percent if percent <= 100 else 99}%')
            self.post(type='ok', text="执行结束" if config.defaulelang == 'zh' else 'Ended')

    def feed(d):
        d = json.loads(d)
        if d['type'] == "error":
            QtWidgets.QMessageBox.critical(vandaform, config.transobj['anerror'], d['text'])
            vandaform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            vandaform.startbtn.setDisabled(False)
            vandaform.loglabel.setText('')
        elif d['type'] == 'jd':
            vandaform.startbtn.setText(d['text'])
        elif d['type'] == 'logs':
            vandaform.loglabel.setText(d['text'])
        else:
            vandaform.startbtn.setText(config.transobj['zhixingwc'])
            vandaform.startbtn.setDisabled(False)
            vandaform.loglabel.setText(config.transobj['quanbuend'])
            vandaform.resultbtn.setDisabled(False)

    def get_file():
        dirname = QFileDialog.getExistingDirectory(vandaform, config.transobj['selectsavedir'],
                                                   config.params['last_opendir'])
        vandaform.folder.setText(dirname.replace('\\', '/'))

    def start():
        folder = vandaform.folder.text()
        if not folder or not Path(folder).exists() or not Path(folder).is_dir():
            QMessageBox.critical(vandaform, config.transobj['anerror'],
                                 '必须选择存在同名视频和音频的文件夹' if config.defaulelang == 'zh' else 'You must select the folder where the video and audio with the same name exists.')
            return

        vandaform.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        vandaform.startbtn.setDisabled(True)
        vandaform.resultbtn.setDisabled(True)

        task = CompThread(parent=vandaform, folder=folder, remain=vandaform.remain.isChecked())

        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import Videoandaudioform
    try:
        vandaform = config.child_forms.get('vandaform')
        if vandaform is not None:
            vandaform.show()
            vandaform.raise_()
            vandaform.activateWindow()
            return
        vandaform = Videoandaudioform()
        config.child_forms['vandaform'] = vandaform
        vandaform.videobtn.clicked.connect(lambda: get_file())

        vandaform.resultbtn.clicked.connect(opendir)
        vandaform.startbtn.clicked.connect(start)
        vandaform.show()
    except Exception:
        pass
