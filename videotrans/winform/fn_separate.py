import os

from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.task.separate_worker import SeparateWorker


# 分离背景音
def open():
    def get_file():
        format_str=" ".join([ '*.'+f  for f in  config.VIDEO_EXTS+config.AUDIO_EXITS])
        fname, _ = QFileDialog.getOpenFileName(separatew, "Select audio or video",
                                               config.params['last_opendir'],
                                               f"files({format_str})")
        if fname:
            separatew.fromfile.setText(fname.replace('file:///', '').replace('\\', '/'))

    def update(d):
        # 更新
        if d == 'succeed':
            separatew.set.setText(config.transobj['Separate End/Restart'])
            separatew.fromfile.setText('')
        elif d == 'end':
            separatew.set.setText(config.transobj['Start Separate'])
        else:
            QMessageBox.critical(separatew, config.transobj['anerror'], d)

    def start():
        if config.separate_status == 'ing':
            config.separate_status = 'stop'
            separatew.set.setText(config.transobj['Start Separate'])
            return
        # 开始处理分离，判断是否选择了源文件
        file = separatew.fromfile.text()
        if not file or not os.path.exists(file):
            QMessageBox.critical(separatew, config.transobj['anerror'],
                                 config.transobj['must select audio or video file'])
            return
        separatew.set.setText(config.transobj['Start Separate...'])
        basename = os.path.basename(file)
        # 判断名称是否正常
        # 创建文件夹
        out = os.path.join(outdir, basename).replace('\\', '/')
        os.makedirs(out, exist_ok=True)
        separatew.url.setText(out)
        # 开始分离
        config.separate_status = 'ing'
        separatew.task = SeparateWorker(parent=separatew, out=out, file=file, basename=basename)
        separatew.task.finish_event.connect(update)
        separatew.task.start()

    from videotrans.component import SeparateForm
    try:
        separatew = config.child_forms.get('separatew')
        if separatew is not None:
            separatew.show()
            separatew.raise_()
            separatew.activateWindow()
            return
        separatew = SeparateForm()
        config.child_forms['separatew'] = separatew
        separatew.set.setText(config.transobj['Start Separate'])
        outdir = os.path.join(config.HOME_DIR, 'separate').replace('\\', '/')
        if not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        # 创建事件过滤器实例并将其安装到 lineEdit 上
        separatew.url.setText(outdir)

        separatew.selectfile.clicked.connect(get_file)

        separatew.set.clicked.connect(start)
        separatew.show()
    except Exception:
        pass
