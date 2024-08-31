import json
import os
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtWidgets import QMessageBox, QFileDialog, QPlainTextEdit

from videotrans import translator
from videotrans.configure import config
from videotrans.task.fanyiwork import FanyiWorker
from videotrans.util import tools


# 字幕批量翻译
def open():
    RESULT_DIR = config.HOME_DIR + "/translate"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    def feed(d):
        d = json.loads(d)
        if d['type'] == 'error':
            QtWidgets.QMessageBox.critical(fanyiform, config.transobj['anerror'], d['text'])
            fanyiform.fanyi_start.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            fanyiform.fanyi_start.setDisabled(False)
            fanyiform.fanyi_import.setDisabled(False)
        # 挨个从顶部添加已翻译后的文字
        elif d['type'] == 'subtitle':
            fanyiform.fanyi_targettext.moveCursor(QTextCursor.End)
            fanyiform.fanyi_targettext.setPlainText(d['text'])
        elif d['type'] == 'replace':
            fanyiform.fanyi_targettext.clear()
            fanyiform.fanyi_targettext.setPlainText(d['text'])
        # 开始时清理目标区域，填充原区域
        elif d['type'] == 'clear_target':
            fanyiform.fanyi_targettext.clear()
        elif d['type'] == 'set_source':
            fanyiform.fanyi_sourcetext.clear()
            fanyiform.fanyi_sourcetext.setPlainText(d['text'])
        elif d['type'] == 'logs':
            fanyiform.loglabel.setText(d["text"])
        else:
            fanyiform.loglabel.setText(config.transobj['quanbuend'])
            fanyiform.fanyi_start.setText('执行完成/开始执行' if config.defaulelang == 'zh' else 'Ended/Start operate')
            fanyiform.fanyi_import.setDisabled(False)
            fanyiform.daochu.setDisabled(False)
            fanyiform.fanyi_start.setDisabled(False)

    def fanyi_import_fun():
        fnames, _ = QFileDialog.getOpenFileNames(fanyiform,
                                                 config.transobj['tuodongfanyi'],
                                                 config.params['last_opendir'],
                                                 "Subtitles files(*.srt)")
        if len(fnames) < 1:
            return
        namestr = []
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/').replace('file:///', '')
            namestr.append(os.path.basename(fnames[i]))
        if fnames:
            fanyiform.files = fnames
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            fanyiform.fanyi_sourcetext.setPlainText(
                f'{config.transobj["yidaorujigewenjian"]}{len(fnames)}\n{",".join(namestr)}')

    def fanyi_save_fun():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    def fanyi_start_fun():
        config.settings = config.parse_init()
        target_language = fanyiform.fanyi_target.currentText()
        translate_type = fanyiform.fanyi_translate_type.currentIndex()
        if target_language == '-':
            return QMessageBox.critical(fanyiform, config.transobj['anerror'], config.transobj["fanyimoshi1"])
        proxy = fanyiform.fanyi_proxy.text()

        if proxy:
            tools.set_proxy(proxy)
            config.params['proxy'] = proxy

        rs = translator.is_allow_translate(translate_type=translate_type, show_target=target_language)
        if rs is not True:
            return False
        fanyiform.fanyi_sourcetext.clear()
        fanyiform.loglabel.setText('')

        fanyi_task = FanyiWorker(translate_type, target_language, fanyiform.files, fanyiform)
        fanyi_task.uito.connect(feed)
        fanyi_task.start()

        fanyiform.fanyi_start.setDisabled(True)
        fanyiform.fanyi_start.setText(config.transobj["running"])
        fanyiform.fanyi_targettext.clear()
        fanyiform.daochu.setDisabled(True)

    # 翻译目标语言变化时
    def target_lang_change(t):
        if t in ['-', 'No']:
            return
        # 判断翻译渠道是否支持翻译到该目标语言
        if translator.is_allow_translate(translate_type=fanyiform.fanyi_translate_type.currentIndex(), show_target=t,
                                         win=fanyiform) is not True:
            return

    from videotrans.component import Fanyisrt
    try:
        fanyiform = config.child_forms.get('fanyiform')
        if fanyiform is not None:
            fanyiform.show()
            fanyiform.raise_()
            fanyiform.activateWindow()
            return
        fanyiform = Fanyisrt()
        config.child_forms['fanyiform'] = fanyiform
        fanyiform.fanyi_target.addItems(["-"] + config.langnamelist)
        fanyiform.fanyi_target.currentTextChanged.connect(target_lang_change)
        fanyiform.fanyi_import.clicked.connect(fanyi_import_fun)
        fanyiform.fanyi_start.clicked.connect(fanyi_start_fun)
        fanyiform.fanyi_translate_type.addItems(translator.TRANSLASTE_NAME_LIST)
        fanyiform.fanyi_translate_type.currentIndexChanged.connect(
            lambda: target_lang_change(fanyiform.fanyi_target.currentText()))

        fanyiform.fanyi_sourcetext = QPlainTextEdit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        fanyiform.fanyi_sourcetext.setSizePolicy(sizePolicy)
        fanyiform.fanyi_sourcetext.setMinimumSize(300, 0)
        fanyiform.fanyi_proxy.setText(config.params['proxy'])

        fanyiform.fanyi_sourcetext.setPlaceholderText(config.transobj['tuodongfanyi'])
        fanyiform.fanyi_sourcetext.setToolTip(config.transobj['tuodongfanyi'])
        fanyiform.fanyi_sourcetext.setReadOnly(True)

        fanyiform.fanyi_layout.insertWidget(0, fanyiform.fanyi_sourcetext)
        fanyiform.daochu.clicked.connect(fanyi_save_fun)

        fanyiform.show()
    except Exception as e:
        print(e)
