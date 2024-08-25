import os
import re

from PySide6 import QtWidgets
import json
from videotrans.configure import config


# 下载
def open():
    def download():
        proxy = config.youw.proxy.text().strip()
        outdir = config.youw.outputdir.text()
        url = config.youw.url.text().strip()
        vid = config.youw.formatname.isChecked()
        thread_num=8
        try:
            thread_num=int(config.youw.thread.text())
        except Exception:
            pass
        print(f'{thread_num=}')
        if not url or not re.match(r'^https://(www.)?(youtube.com/(watch|shorts)|youtu.be/\w)', url, re.I):
            QtWidgets.QMessageBox.critical(config.youw, config.transobj['anerror'],
                                           config.transobj[
                                               'You must fill in the YouTube video playback page address'])
            return
        if proxy:
            config.params['proxy'] = proxy
        from videotrans.task.download_youtube import Download
        down = Download(proxy=proxy, url=url, out=outdir, parent=config.youw, vid=vid,thread_num=thread_num)
        down.uito.connect(feed)
        down.start()
        config.youw.set.setText(config.transobj["downing..."])
    def feed(d):
        d=json.loads(d)
        if d['type']=='error':
            QtWidgets.QMessageBox.critical(config.youw,config.transobj['anerror'],d['text'])
        elif d['type']=='logs':
            config.youw.set.setText(d['text'])
        else:
            config.youw.set.setText(config.transobj['start download'])
            QtWidgets.QMessageBox.information(config.youw, "OK", d['text'])

    def selectdir():
        dirname = QtWidgets.QFileDialog.getExistingDirectory(config.youw, "Select Dir", outdir).replace('\\', '/')
        config.youw.outputdir.setText(dirname)

    from videotrans.component import YoutubeForm
    if config.youw is not None:
        config.youw.show()
        config.youw.raise_()
        config.youw.activateWindow()
        return
    config.youw = YoutubeForm()
    config.youw.set.setText(config.transobj['start download'])
    config.youw.selectdir.setText(config.transobj['Select Out Dir'])
    outdir = config.params['youtube_outdir'] if 'youtube_outdir' in config.params else os.path.join(config.homedir,
                                                                                                    'youtube').replace(
        '\\', '/')
    if not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)
    # 创建事件过滤器实例并将其安装到 lineEdit 上

    config.youw.outputdir.setText(outdir)
    if config.params['proxy']:
        config.youw.proxy.setText(config.params['proxy'])
    config.youw.selectdir.clicked.connect(selectdir)

    config.youw.set.clicked.connect(download)
    config.youw.show()
