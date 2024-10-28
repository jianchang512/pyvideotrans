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


# 水印
def openwin():
    RESULT_DIR = config.HOME_DIR + "/videoandaudio"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, remain=False, folder=None,audio_process=0):
            super().__init__(parent=parent)
            self.remain = remain
            self.folder = folder
            self.audio_process = audio_process

        # 取出具有相同名称的视频和音频文件，组装为dict待处理
        def get_list(self):
            videos = {}
            audios = {}
            for it in Path(self.folder).iterdir():
                if it.is_file():
                    suffix = it.suffix.lower()[1:]
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
                    video_time=tools.get_video_duration(info['video'])
                    audio_time=int(tools.get_audio_time(audio)*1000)
                    tmp_audio=config.TEMP_HOME + f"/{time.time()}-{Path(audio).name}"
                    if audio_time > video_time and self.audio_process==0:
                        tools.runffmpeg(['-y', '-i', audio, '-ss', '00:00:00.000', '-t', str(video_time/1000), tmp_audio])
                        audio = tmp_audio
                    elif audio_time>video_time and self.audio_process==1:
                        tools.precise_speed_up_audio(file_path=audio, out=tmp_audio, target_duration_ms=video_time)
                        audio=tmp_audio
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
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == "error":
            winobj.has_done = True
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d['text'])
            winobj.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            winobj.startbtn.setDisabled(False)
            winobj.loglabel.setText('')
        elif d['type'] == 'jd':
            winobj.startbtn.setText(d['text'])
        elif d['type'] == 'logs':
            winobj.loglabel.setText(d['text'])
        elif d['type']=='ok':
            winobj.has_done = True
            winobj.startbtn.setText(config.transobj['zhixingwc'])
            winobj.startbtn.setDisabled(False)
            winobj.loglabel.setText(config.transobj['quanbuend'])
            winobj.resultbtn.setDisabled(False)

    def get_file():
        dirname = QFileDialog.getExistingDirectory(winobj, config.transobj['selectsavedir'],
                                                   config.params['last_opendir'])
        winobj.folder.setText(dirname.replace('\\', '/'))

    def start():
        winobj.has_done = False
        folder = winobj.folder.text()
        if not folder or not Path(folder).exists() or not Path(folder).is_dir():
            QMessageBox.critical(winobj, config.transobj['anerror'],
                                 '必须选择存在同名视频和音频的文件夹' if config.defaulelang == 'zh' else 'You must select the folder where the video and audio with the same name exists.')
            return

        winobj.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        winobj.loglabel.setText('')
        winobj.startbtn.setDisabled(True)
        winobj.resultbtn.setDisabled(True)

        task = CompThread(parent=winobj, folder=folder, remain=winobj.remain.isChecked(),audio_process=winobj.audio_process.currentIndex())

        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import Videoandaudioform
    try:
        winobj = config.child_forms.get('vandaform')
        if winobj is not None:
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            return
        winobj = Videoandaudioform()
        config.child_forms['vandaform'] = winobj
        winobj.videobtn.clicked.connect(lambda: get_file())

        winobj.resultbtn.clicked.connect(opendir)
        winobj.startbtn.clicked.connect(start)
        winobj.show()
    except Exception:
        pass
