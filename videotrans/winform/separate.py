import os

from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.task.separate_worker import SeparateWorker
from videotrans.util import tools


# 分离背景音
def open():
    def get_file():
        fname, _ = QFileDialog.getOpenFileName(config.separatew, "Select audio or video",
                                               config.params['last_opendir'],
                                               "files(*.wav *.mp3 *.aac *.m4a *.flac *.mp4 *.mov *.mkv)")
        if fname:
            config.separatew.fromfile.setText(fname.replace('file:///', '').replace('\\', '/'))

    def update(d):
        # 更新
        if d == 'succeed':
            config.separatew.set.setText(config.transobj['Separate End/Restart'])
            config.separatew.fromfile.setText('')
        elif d == 'end':
            config.separatew.set.setText(config.transobj['Start Separate'])
        else:
            QMessageBox.critical(config.separatew, config.transobj['anerror'], d)

    def start():
        if config.separate_status == 'ing':
            config.separate_status = 'stop'
            config.separatew.set.setText(config.transobj['Start Separate'])
            return
        # 开始处理分离，判断是否选择了源文件
        file = config.separatew.fromfile.text()
        if not file or not os.path.exists(file):
            QMessageBox.critical(config.separatew, config.transobj['anerror'],
                                 config.transobj['must select audio or video file'])
            return
        config.separatew.set.setText(config.transobj['Start Separate...'])
        basename = os.path.basename(file)
        # 判断名称是否正常
        rs, newfile, base = tools.rename_move(file, is_dir=False)
        if rs:
            file = newfile
            basename = base
        # 创建文件夹
        out = os.path.join(outdir, basename).replace('\\', '/')
        os.makedirs(out, exist_ok=True)
        config.separatew.url.setText(out)
        # 开始分离
        config.separate_status = 'ing'
        config.separatew.task = SeparateWorker(parent=config.separatew, out=out, file=file, basename=basename)
        config.separatew.task.finish_event.connect(update)
        config.separatew.task.start()

    from videotrans.component import SeparateForm
    try:
        if config.separatew is not None:
            config.separatew.show()
            config.separatew.raise_()
            config.separatew.activateWindow()
            return
        config.separatew = SeparateForm()
        config.separatew.set.setText(config.transobj['Start Separate'])
        outdir = os.path.join(config.homedir, 'separate').replace('\\', '/')
        if not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        # 创建事件过滤器实例并将其安装到 lineEdit 上
        config.separatew.url.setText(outdir)

        config.separatew.selectfile.clicked.connect(get_file)

        config.separatew.set.clicked.connect(start)
        config.separatew.show()
    except Exception:
        pass
