# 水印


def openwin():
    from videotrans.winform import get_cls
    from videotrans.util._ffmpeg_runner import runffmpeg
    from videotrans.util._ffprobe import get_video_duration
    from videotrans.util.help_misc import show_error, read_last_n_lines
    import json
    import os
    import time,threading
    from pathlib import Path
    from PySide6.QtCore import QThread, Signal, QUrl,QTimer
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog
    from videotrans.configure import constants
    from videotrans.configure.config import tr,app_cfg,settings,params
    from videotrans.configure import config
    # 使用内置的 open 函数

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, png=None, x=10, y=10, width=50, height=50, pos=0):
            super().__init__(parent=parent)
            self.png = png
            self.x = int(x)
            self.y = int(y)
            self.width = int(width)
            self.height = int(height)
            self.pos = int(pos)
            self.every_percent = 1 / len(winobj.videourls)
            self.percent = 0
            self.end = False

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

        def hebing_pro(self, protxt, video_time=0):
            percent = 0
            while 1:
                if app_cfg.exit_soft:return
                if self.end or percent >= 100:
                    return
                content = read_last_n_lines(protxt)    
                if not content:
                    time.sleep(1)
                    continue
                
                
                if content[-1] == 'progress=end':
                    return
                idx = len(content) - 1
                end_time = "00:00:00"
                while idx > 0:
                    if content[idx].startswith('out_time='):
                        end_time = content[idx].split('=')[1].strip()
                        break
                    idx -= 1
                if video_time==0:                
                    self.post(type='jd', text=f'{end_time}')
                    time.sleep(1)
                    continue
                try:
                    h, m, s = end_time.split(':')
                except ValueError:
                    continue
                tmp1 = round((int(h) * 3600000 + int(m) * 60000 + int(s[:2]) * 1000) / video_time, 2)
                if percent + tmp1 < 99.9:
                    percent += tmp1
                self.percent += percent * self.every_percent / 100
                self.post(type='jd', text=f'{self.percent * 100}%')
                time.sleep(1)


        def run(self) -> None:
            # 不切换工作目录：所用路径都是绝对路径。os.chdir 会改变整个软件的工作目录，输出目录不存在时还会在发出任何消息前出错，按钮一直显示“执行中”
            target=winobj.output_data.text()
            # 确保临时目录存在

            for video in winobj.videourls:
                result_file = target + f'/{Path(video).stem}.mp4'

                # 计算水印位置
                duration = get_video_duration(video)
                # overlay 滤镜中 main_w/main_h 是视频的宽高，w/h 与 overlay_w/overlay_h 相同，是水印的宽高：用 w/h 计算时，右侧、底部和居中的水印都会落在左上角
                positions = [
                    f"{self.x}:{self.y}",  # 左上角
                    f"(main_w-overlay_w-{self.x}):{self.y}",  # 右上角
                    f"(main_w-overlay_w-{self.x}):(main_h-overlay_h-{self.y})",  # 右下角
                    f"{self.x}:(main_h-overlay_h-{self.y})",  # 左下角
                    "(main_w-overlay_w)/2:(main_h-overlay_h)/2"  # 中心
                ]

                position = positions[self.pos]
                protxt = config.TEMP_DIR + f'/jd{time.time()}.txt'
                threading.Thread(target=self.hebing_pro,args=(protxt,duration),daemon=True).start()

                # 构建 FFmpeg 命令
                ffmpeg_command = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i", os.path.normpath(video),
                    "-i", os.path.normpath(self.png),
                    "-filter_complex",
                    f"[1:v]scale={self.width}:{self.height}[overlay];[0:v][overlay]overlay={position}:enable='between(t,0,999999)'",
                    "-c:v", "libx265",
                    "-crf", f"{settings.get('crf',26)}",
                    "-preset", f"{settings.get('preset','fast')}",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    os.path.normpath(result_file)
                ]
                try:
                    runffmpeg(ffmpeg_command,force_cpu=False)
                except Exception as e:
                    from videotrans.configure.excepts import get_msg_from_except
                    self.post(type='error', text=get_msg_from_except(e))
                finally:
                    self.percent += self.every_percent
                self.post(type='jd', text=f'{self.percent * 100}%')
            self.post(type='ok', text='Ended')
            self.end = True

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == "error":
            winobj.has_done = True
            show_error(d['text'])
            winobj.startbtn.setText(tr("start operate"))
            winobj.startbtn.setDisabled(False)
            winobj.resultlabel.setText('')
        elif d['type'] == 'jd':
            winobj.startbtn.setText(d['text'])
        elif d['type'] == 'logs':
            winobj.resultlabel.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.startbtn.setText(tr('zhixingwc'))
            winobj.startbtn.setDisabled(False)
            winobj.resultlabel.setText(tr('quanbuend'))

    def get_file(type):
        if type == 1:
            format_str = " ".join(['*.' + f for f in constants.VIDEO_EXTS])
            fname, _ = QFileDialog.getOpenFileNames(winobj, "Select Video",
                                                    params.get('last_opendir'),
                                                    f"Video files({format_str})")
            if len(fname) > 0:
                winobj.videourls = fname.copy()
                winobj.videourl.setText(",".join(winobj.videourls))
        else:
            fname, _ = QFileDialog.getOpenFileName(winobj, "Select Image",
                                                   params.get('last_opendir'),
                                                   "files(*.png *.jpg *.jpeg *.gif)")
            if fname:
                winobj.pngurl.setText(fname)


    def start():
        winobj.has_done = False
        png = winobj.pngurl.text()
        if len(winobj.videourls) < 1 or not png:
            show_error(tr("Must select video and watermark image"))
            return

        winobj.startbtn.setText(
            tr("under implementation in progress..."))
        winobj.startbtn.setDisabled(True)

        x, y = 10, 10
        try:
            x = int(winobj.linex.text())
        except (TypeError,ValueError):
            pass
        try:
            y = int(winobj.liney.text())
        except (TypeError,ValueError):
            pass
        w, h = 50, 50
        try:
            tmp_w = winobj.linew.text().strip().split('x')
            w, h = int(tmp_w[0]), int(tmp_w[1])
        except (ValueError,AttributeError,IndexError,TypeError):
            pass

        task = CompThread(parent=winobj, png=png, x=max(x, 0), y=max(y, 0),
                          width=max(w, 1), height=max(h, 1), pos=int(winobj.compos.currentIndex()))

        task.uito.connect(feed)
        task.start()


    winobj = get_cls(Path(__file__).stem)()
    def _bind():
        winobj.videobtn.clicked.connect(lambda: get_file(1))
        winobj.pngbtn.clicked.connect(lambda: get_file(2))

        winobj.startbtn.clicked.connect(start)
    _bind()
    return winobj