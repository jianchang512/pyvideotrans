import json
import os
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip

from videotrans.configure import config
import builtins
# 使用内置的 open 函数
from videotrans.util import tools

builtin_open = builtins.open

# 水印
def open():
    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, video=None, png=None, x=10, y=10, width=50, height=50, pos=0):
            super().__init__(parent=parent)
            self.video = video
            self.png = png
            self.x = int(x)
            self.y = int(y)
            self.width = int(width)
            self.height = int(height)
            self.pos = int(pos)
            self.result_dir = config.homedir + "/watermark"
            os.makedirs(self.result_dir, exist_ok=True)
            name = os.path.splitext(os.path.basename(video))[0]
            self.result_file = self.result_dir + f"/{name}-{int(time.time())}.mp4"

        def hebing_pro(self, protxt, video_time):
            percent = 0
            while 1:
                if percent >= 100:
                    return
                if not os.path.exists(protxt):
                    time.sleep(1)
                    continue
                content = Path(protxt).read_text(encoding='utf-8').strip().split("\n")
                if content[-1] == 'progress=end':
                    return
                idx = len(content) - 1
                end_time = "00:00:00"
                while idx > 0:
                    if content[idx].startswith('out_time='):
                        end_time = content[idx].split('=')[1].strip()
                        break
                    idx -= 1
                try:
                    h, m, s = end_time.split(':')
                except Exception:
                    time.sleep(1)
                    continue
                else:
                    h, m, s = end_time.split(':')
                    tmp1 = round((int(h) * 3600000 + int(m) * 60000 + int(s[:2]) * 1000) / video_time, 2)
                    if percent + tmp1 < 99.9:
                        percent += tmp1
                    self.uito.emit(f'jd:{percent}%')
                    time.sleep(1)



        def run(self) -> None:
            os.chdir(config.homedir + "/watermark")
            # 确保临时目录存在
            temp_dir = config.TEMP_HOME
            os.makedirs(temp_dir, exist_ok=True)

            # 计算水印位置
            duration=tools.get_video_duration(self.video)
            positions = [
                f"{self.x}:{self.y}",  # 左上角
                f"(w-overlay_w-{self.x}):{self.y}",  # 右上角
                f"(w-overlay_w-{self.x}):(h-overlay_h-{self.y})",  # 右下角
                f"{self.x}:(h-overlay_h-{self.y})",  # 左下角
                f"(w-overlay_w)/2:(h-overlay_h)/2"  # 中心
            ]

            position = positions[self.pos]
            protxt = config.TEMP_HOME + f'/jd{time.time()}.txt'
            threading.Thread(target=self.hebing_pro, args=(protxt, duration,)).start()

            # 构建 FFmpeg 命令
            ffmpeg_command = [
                "-y",
                "-progress",
                protxt,
                "-i", self.video,
                "-i", self.png,
                "-filter_complex",
                f"[1:v]scale={self.width}:{self.height}[overlay];[0:v][overlay]overlay={position}:enable='between(t,0,999999)'",
                "-c:v", "libx264",
                "-crf", f"{config.settings['crf']}",
                "-preset", f"{config.settings['preset']}",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                self.result_file
            ]
            try:
                tools.runffmpeg(ffmpeg_command)
            except Exception as e:
                self.uito.emit(f'error:{str(e)}')
            else:
                self.uito.emit('ok')


    def feed(d):
        if d.startswith("error:"):
            QtWidgets.QMessageBox.critical(config.waterform, config.transobj['anerror'], d)
            config.waterform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            config.waterform.startbtn.setDisabled(False)
            config.waterform.resultlabel.setText('')
        elif d.startswith('jd:'):
            config.waterform.startbtn.setText(d[3:])
        else:
            config.waterform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            config.waterform.startbtn.setDisabled(False)
            config.waterform.resultlabel.setText(d)
            config.waterform.resultbtn.setDisabled(False)

    def get_file(type):
        if type == 1:
            fname, _ = QFileDialog.getOpenFileName(config.waterform, "Select Video",
                                                   config.params['last_opendir'],
                                                   "files(*.mp4 *.mov *.mkv *.avi *.mpeg)")
            if fname:
                config.waterform.videourl.setText(fname.replace('file:///', '').replace('\\', '/'))
        else:
            fname, _ = QFileDialog.getOpenFileName(config.waterform, "Select Image",
                                                   config.params['last_opendir'],
                                                   "files(*.png *.jpg *.jpeg *.gif)")
            if fname:
                config.waterform.pngurl.setText(fname.replace('file:///', '').replace('\\', '/'))

    def start():
        # 开始处理分离，判断是否选择了源文件
        video = config.waterform.videourl.text()
        png = config.waterform.pngurl.text()
        if not video or not png:
            QMessageBox.critical(config.waterform, config.transobj['anerror'],
                                 '必须选择视频和水印图片' if config.defaulelang == 'zh' else 'Must select video and watermark image')
            return

        config.waterform.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        config.waterform.startbtn.setDisabled(True)
        config.waterform.resultbtn.setDisabled(True)

        x, y = 10, 10
        try:
            x = int(config.waterform.linex.text())
        except Exception:
            pass
        try:
            y = int(config.waterform.liney.text())
        except Exception:
            pass
        w, h = 50, 50
        try:
            tmp_w = config.waterform.linew.text().strip().split('x')
            w, h = int(tmp_w[0]), int(tmp_w[1])
        except Exception:
            pass

        task = CompThread(parent=config.waterform, video=video, png=png, x=max(x, 0), y=max(y, 0),
                          width=max(w, 1), height=max(h, 1), pos=int(config.waterform.compos.currentIndex()))

        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(config.homedir+"/watermark"))

    from videotrans.component import WatermarkForm
    try:
        if config.waterform is not None:
            config.waterform.show()
            config.waterform.raise_()
            config.waterform.activateWindow()
            return
        config.waterform = WatermarkForm()
        config.waterform.videobtn.clicked.connect(lambda: get_file(1))
        config.waterform.pngbtn.clicked.connect(lambda: get_file(2))

        config.waterform.resultbtn.clicked.connect(opendir)
        config.waterform.startbtn.clicked.connect(start)
        config.waterform.show()
    except Exception:
        pass
