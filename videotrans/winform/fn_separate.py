import os

from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.task.separate_worker import SeparateWorker


# 分离背景音
def open():
    def get_file():
        format_str=" ".join([ '*.'+f  for f in  config.VIDEO_EXTS+config.AUDIO_EXITS])
        fname, _ = QFileDialog.getOpenFileName(winobj, "Select audio or video",
                                               config.params['last_opendir'],
                                               f"files({format_str})")
        if fname:
            winobj.fromfile.setText(fname.replace('file:///', '').replace('\\', '/'))

    def update(d):
        # 更新
        if d == 'succeed':
            winobj.set.setText(config.transobj['Separate End/Restart'])
            winobj.fromfile.setText('')
        elif d == 'end':
            winobj.set.setText(config.transobj['Start Separate'])
        else:
            QMessageBox.critical(winobj, config.transobj['anerror'], d)

    def start():
        if config.separate_status == 'ing':
            config.separate_status = 'stop'
            winobj.set.setText(config.transobj['Start Separate'])
            return
        # 开始处理分离，判断是否选择了源文件
        file = winobj.fromfile.text()
        if not file or not os.path.exists(file):
            QMessageBox.critical(winobj, config.transobj['anerror'],
                                 config.transobj['must select audio or video file'])
            return
        winobj.set.setText(config.transobj['Start Separate...'])
        basename = os.path.basename(file)
        # 判断名称是否正常
        # 创建文件夹
        out = os.path.join(outdir, basename).replace('\\', '/')
        os.makedirs(out, exist_ok=True)
        winobj.url.setText(out)
        # 开始分离
        config.separate_status = 'ing'
        winobj.task = SeparateWorker(parent=winobj, out=out, file=file, basename=basename)
        winobj.task.finish_event.connect(update)
        winobj.task.start()

    from videotrans.component import SeparateForm
    try:
        winobj = config.child_forms.get('separatew')
        if winobj is not None:
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            return
        winobj = SeparateForm()
        config.child_forms['separatew'] = winobj
        winobj.set.setText(config.transobj['Start Separate'])
        outdir = os.path.join(config.HOME_DIR, 'separate').replace('\\', '/')
        if not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        # 创建事件过滤器实例并将其安装到 lineEdit 上
        winobj.url.setText(outdir)

        winobj.selectfile.clicked.connect(get_file)

        winobj.set.clicked.connect(start)
        winobj.show()
    except Exception:
        pass
