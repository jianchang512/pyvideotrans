

def openwin():
    import os
    from videotrans.util import contants
    from pathlib import Path
    from PySide6.QtCore import QTimer

    from PySide6.QtWidgets import QFileDialog

    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    # 分离背景音
    from videotrans.util import tools


    outdir = HOME_DIR +'/separate'
    def get_file():
        format_str = " ".join(['*.' + f for f in contants.VIDEO_EXTS + contants.AUDIO_EXITS])
        fname, _ = QFileDialog.getOpenFileName(winobj, "Select audio or video",
                                               params.get('last_opendir',''),
                                               f"files({format_str})")
        if fname:
            winobj.fromfile.setText(fname.replace('file:///', '').replace('\\', '/'))

    def update(d):
        # 更新
        if d == 'succeed':
            winobj.set.setText(tr('Separate End/Restart'))
            winobj.fromfile.setText('')
        elif d == 'end':
            winobj.set.setText(tr('Start Separate'))
            winobj.logs.setText('')
        elif d.startswith('logs:'):
            if len(d) > 5:
                winobj.set.setText(d[5:])
        elif d.startswith('error:'):
            tools.show_error(d[6:])
        
        if not d.startswith('logs:'):
            winobj.has_done = False
            winobj.set.setText(tr('Start Separate'))

    def start():
        # 开始处理分离，判断是否选择了源文件
        file = winobj.fromfile.text()
        if not file or not os.path.exists(file):
            tools.show_error(tr('must select audio or video file'))
            return

        uuid = tools.get_md5(file)
        # 已在执行，在此点击停止
        if winobj.has_done:
            winobj.has_done = False
            del app_cfg.uuid_logs_queue[uuid]
            winobj.set.setText(tr('Start Separate'))
            return
        winobj.has_done = True
        if uuid in app_cfg.uuid_logs_queue:
            del app_cfg.uuid_logs_queue[uuid]

        winobj.set.setText(tr('Start Separate...'))
        basename = Path(file).stem
        # 判断名称是否正常
        # 创建文件夹
        Path(outdir).mkdir(parents=True,exist_ok=True)
        winobj.url.setText(outdir)
        # 开始分离
        from videotrans.task.separate_worker import SeparateWorker
        winobj.task = SeparateWorker(parent=winobj, file=file, out=outdir, uuid=uuid)
        winobj.task.finish_event.connect(update)
        winobj.task.start()

    from videotrans.component.set_form import SeparateForm

    winobj = SeparateForm()
    app_cfg.child_forms['fn_separate'] = winobj
    winobj.show()
    def _bind():

        Path(outdir).mkdir(exist_ok=True,parents=True)
        # 创建事件过滤器实例并将其安装到 lineEdit 上
        winobj.url.setText(outdir)

        winobj.selectfile.clicked.connect(get_file)

        winobj.set.clicked.connect(start)
    QTimer.singleShot(10,_bind)
