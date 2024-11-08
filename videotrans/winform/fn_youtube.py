import json
import re
from pathlib import Path

from PySide6 import QtWidgets

from videotrans.configure import config


# 下载
def openwin():
    def download():
        winobj.has_done = False
        proxy = winobj.proxy.text().strip()
        outdir = winobj.outputdir.text()
        url = winobj.url.text().strip()
        vid = winobj.formatname.isChecked()
        thread_num = 8
        try:
            thread_num = int(winobj.thread.text())
        except Exception:
            pass

        if not url or not re.match(r'^https://(www.)?(youtube.com/(watch|shorts)|youtu.be/\w)', url, re.I):
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'],
                                           config.transobj[
                                               'You must fill in the YouTube video playback page address'])
            return
        if proxy:
            config.proxy = proxy
        from videotrans.task.download_youtube import Download
        down = Download(proxy=proxy, url=url, out=outdir, parent=winobj, vid=vid, thread_num=thread_num)
        down.uito.connect(feed)
        down.start()
        winobj.set.setText(config.transobj["downing..."])

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == 'error':
            winobj.has_done = True
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d['text'])
            winobj.set.setText(config.transobj['start download'])
        elif d['type'] == 'logs':
            winobj.set.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.set.setText(config.transobj['start download'])
            QtWidgets.QMessageBox.information(winobj, "OK", d['text'])

    def selectdir():
        dirname = QtWidgets.QFileDialog.getExistingDirectory(winobj, "Select Dir", outdir)
        winobj.outputdir.setText(Path(dirname).as_posix())

    from videotrans.component import YoutubeForm
    winobj = config.child_forms.get('youw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = YoutubeForm()
    config.child_forms['youw'] = winobj
    winobj.set.setText(config.transobj['start download'])
    winobj.selectdir.setText(config.transobj['Select Out Dir'])
    outdir = config.params['youtube_outdir'] if 'youtube_outdir' in config.params else Path(
        config.HOME_DIR + '/youtube').as_posix()
    Path(config.HOME_DIR + '/youtube').mkdir(parents=True, exist_ok=True)
    # 创建事件过滤器实例并将其安装到 lineEdit 上
    winobj.outputdir.setText(outdir)
    if config.proxy:
        winobj.proxy.setText(config.proxy)
    winobj.selectdir.clicked.connect(selectdir)

    winobj.set.clicked.connect(download)
    winobj.show()
