import json
import re
from pathlib import Path

from PySide6 import QtWidgets

from videotrans.configure import config


# 下载
def open():
    def download():
        proxy = youw.proxy.text().strip()
        outdir = youw.outputdir.text()
        url = youw.url.text().strip()
        vid = youw.formatname.isChecked()
        thread_num = 8
        try:
            thread_num = int(youw.thread.text())
        except Exception:
            pass

        if not url or not re.match(r'^https://(www.)?(youtube.com/(watch|shorts)|youtu.be/\w)', url, re.I):
            QtWidgets.QMessageBox.critical(youw, config.transobj['anerror'],
                                           config.transobj[
                                               'You must fill in the YouTube video playback page address'])
            return
        if proxy:
            config.params['proxy'] = proxy
        from videotrans.task.download_youtube import Download
        down = Download(proxy=proxy, url=url, out=outdir, parent=youw, vid=vid, thread_num=thread_num)
        down.uito.connect(feed)
        down.start()
        youw.set.setText(config.transobj["downing..."])

    def feed(d):
        d = json.loads(d)
        if d['type'] == 'error':
            QtWidgets.QMessageBox.critical(youw, config.transobj['anerror'], d['text'])
        elif d['type'] == 'logs':
            youw.set.setText(d['text'])
        else:
            youw.set.setText(config.transobj['start download'])
            QtWidgets.QMessageBox.information(youw, "OK", d['text'])

    def selectdir():
        dirname = QtWidgets.QFileDialog.getExistingDirectory(youw, "Select Dir", outdir)
        youw.outputdir.setText(Path(dirname).as_posix())

    from videotrans.component import YoutubeForm
    youw = config.child_forms.get('youw')
    if youw is not None:
        youw.show()
        youw.raise_()
        youw.activateWindow()
        return
    youw = YoutubeForm()
    config.child_forms['youw'] = youw
    youw.set.setText(config.transobj['start download'])
    youw.selectdir.setText(config.transobj['Select Out Dir'])
    outdir = config.params['youtube_outdir'] if 'youtube_outdir' in config.params else Path(
        config.HOME_DIR + '/youtube').as_posix()
    Path(config.HOME_DIR + '/youtube').mkdir(parents=True, exist_ok=True)
    # 创建事件过滤器实例并将其安装到 lineEdit 上
    youw.outputdir.setText(outdir)
    if config.params['proxy']:
        youw.proxy.setText(config.params['proxy'])
    youw.selectdir.clicked.connect(selectdir)

    youw.set.clicked.connect(download)
    youw.show()
