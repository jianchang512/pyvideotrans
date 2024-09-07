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
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == 'error':
            winobj.has_done=True
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d['text'])
            winobj.fanyi_start.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            winobj.fanyi_start.setDisabled(False)
            winobj.fanyi_import.setDisabled(False)
        # 挨个从顶部添加已翻译后的文字
        elif d['type'] == 'subtitle':
            winobj.fanyi_targettext.moveCursor(QTextCursor.End)
            winobj.fanyi_targettext.setPlainText(d['text'])
        elif d['type'] == 'replace':
            winobj.fanyi_targettext.clear()
            winobj.fanyi_targettext.setPlainText(d['text'])
        # 开始时清理目标区域，填充原区域
        elif d['type'] == 'clear_target':
            winobj.fanyi_targettext.clear()
        elif d['type'] == 'set_source':
            winobj.fanyi_sourcetext.clear()
            winobj.fanyi_sourcetext.setPlainText(d['text'])
        elif d['type'] == 'logs':
            winobj.loglabel.setText(d["text"])
        else:
            winobj.has_done=True
            winobj.loglabel.setText(config.transobj['quanbuend'])
            winobj.fanyi_start.setText('执行完成/开始执行' if config.defaulelang == 'zh' else 'Ended/Start operate')
            winobj.fanyi_import.setDisabled(False)
            winobj.daochu.setDisabled(False)
            winobj.fanyi_start.setDisabled(False)

    def fanyi_import_fun():
        fnames, _ = QFileDialog.getOpenFileNames(winobj,
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
            winobj.files = fnames
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            winobj.fanyi_sourcetext.setPlainText(
                f'{config.transobj["yidaorujigewenjian"]}{len(fnames)}\n{",".join(namestr)}')

    def fanyi_save_fun():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    def fanyi_start_fun():
        winobj.has_done=False
        config.settings = config.parse_init()
        target_language = winobj.fanyi_target.currentText()
        translate_type = winobj.fanyi_translate_type.currentIndex()
        source_language,_=translator.get_source_target_code(show_source=winobj.fanyi_source.currentText(), translate_type=translate_type)
        if target_language == '-':
            return QMessageBox.critical(winobj, config.transobj['anerror'], config.transobj["fanyimoshi1"])
        proxy = winobj.fanyi_proxy.text()

        if proxy:
            tools.set_proxy(proxy)
            config.params['proxy'] = proxy

        rs = translator.is_allow_translate(translate_type=translate_type, show_target=target_language)
        if rs is not True:
            return False
        if len(winobj.files)<1:
            return QMessageBox.critical(winobj,config.transobj['anerror'],'必须导入srt字幕文件' if config.defaulelang=='zh' else 'Must import srt subtitle files')
        winobj.fanyi_sourcetext.clear()
        winobj.loglabel.setText('')

        fanyi_task = FanyiWorker(type=translate_type, target_language=target_language, files=winobj.files, parent=winobj,bilingual=winobj.out_format.currentIndex(),source_code=source_language if source_language and source_language!='-' else None)
        fanyi_task.uito.connect(feed)
        fanyi_task.start()

        winobj.fanyi_start.setDisabled(True)
        winobj.fanyi_start.setText(config.transobj["running"])
        winobj.fanyi_targettext.clear()
        winobj.daochu.setDisabled(True)

    # 翻译目标语言变化时
    def target_lang_change(t):
        if t in ['-', 'No']:
            return
        # 判断翻译渠道是否支持翻译到该目标语言
        if translator.is_allow_translate(translate_type=winobj.fanyi_translate_type.currentIndex(), show_target=t,
                                         win=winobj) is not True:
            return
    # 获取新增的google翻译语言代码
    def get_google_trans_newcode():
        new_langcode=[]
        if config.settings['google_trans_newadd']:
            new_langcode=config.settings['google_trans_newadd'].strip().split(',')
        return new_langcode

    # 更新目标语言列表
    def update_target_language(is_google=False):
        current_target=winobj.fanyi_target.currentText()
        config.settings = config.parse_init()
        language_namelist=["-"] + config.langnamelist
        if is_google or winobj.fanyi_translate_type.currentIndex() in [translator.GOOGLE_INDEX,translator.FREEGOOGLE_INDEX]:
            language_namelist+=get_google_trans_newcode()
        winobj.fanyi_target.clear()
        winobj.fanyi_target.addItems(language_namelist)
        if current_target and current_target!='-' and current_target in language_namelist:
            winobj.fanyi_target.setCurrentText(current_target)

   # 翻译渠道变化时重新设置目标语言
    def translate_type_change(idx):
        update_target_language(is_google=idx in [translator.GOOGLE_INDEX,translator.FREEGOOGLE_INDEX])
        target_lang_change(winobj.fanyi_target.currentText())

    from videotrans.component import Fanyisrt
    try:
        winobj = config.child_forms.get('fanyiform')
        if winobj is not None:
            winobj.show()
            update_target_language()
            winobj.raise_()
            winobj.activateWindow()
            return
        winobj = Fanyisrt()
        config.child_forms['fanyiform'] = winobj
        winobj.fanyi_translate_type.addItems(translator.TRANSLASTE_NAME_LIST)
        update_target_language(is_google=True)
        winobj.fanyi_target.currentTextChanged.connect(target_lang_change)
        winobj.fanyi_source.addItems(['-']+config.langnamelist)
        winobj.fanyi_import.clicked.connect(fanyi_import_fun)
        winobj.fanyi_start.clicked.connect(fanyi_start_fun)
        winobj.fanyi_translate_type.currentIndexChanged.connect(translate_type_change)

        winobj.fanyi_sourcetext = QPlainTextEdit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        winobj.fanyi_sourcetext.setSizePolicy(sizePolicy)
        winobj.fanyi_sourcetext.setMinimumSize(300, 0)
        winobj.fanyi_proxy.setText(config.params['proxy'])

        winobj.fanyi_sourcetext.setPlaceholderText(config.transobj['tuodongfanyi'])
        winobj.fanyi_sourcetext.setToolTip(config.transobj['tuodongfanyi'])
        winobj.fanyi_sourcetext.setReadOnly(True)

        winobj.fanyi_layout.insertWidget(0, winobj.fanyi_sourcetext)
        winobj.daochu.clicked.connect(fanyi_save_fun)

        winobj.show()
    except Exception as e:
        print(e)
