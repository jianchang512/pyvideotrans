import json
import os
import time
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QUrl, QThread, Signal
from PySide6.QtGui import QDesktopServices, QTextCursor, Qt
from PySide6.QtWidgets import QMessageBox, QFileDialog, QPlainTextEdit

from videotrans import translator
from videotrans.configure import config
from videotrans.task._translate_srt import TranslateSrt
from videotrans.util import tools


class SignThread(QThread):
    uito = Signal(str)

    def __init__(self, uuid_list=None, parent=None):
        super().__init__(parent=parent)
        self.uuid_list = uuid_list

    def post(self, jsondata):

        self.uito.emit(json.dumps(jsondata))

    def run(self):
        length = len(self.uuid_list)
        while 1:
            if len(self.uuid_list) == 0 or config.exit_soft:
                self.post({"type": "end"})
                time.sleep(1)
                return

            for uuid in self.uuid_list:
                if uuid in config.stoped_uuid_set:
                    try:
                        self.uuid_list.remove(uuid)
                    except:
                        pass
                    continue
                q = config.uuid_logs_queue.get(uuid)
                if not q:
                    continue
                try:
                    if q.empty():
                        time.sleep(0.5)
                        continue
                    data = q.get(block=False)
                    if not data:
                        continue
                    self.post(data)
                    if data['type'] in ['error', 'succeed']:
                        self.uuid_list.remove(uuid)
                        self.post({"type": "jindu", "text": f'{int((length - len(self.uuid_list)) * 100 / length)}%'})
                        config.stoped_uuid_set.add(uuid)
                        del config.uuid_logs_queue[uuid]
                except:
                    pass
SOURCE_DIR=""

# 字幕批量翻译
def openwin():
    global SOURCE_DIR
    RESULT_DIR = config.HOME_DIR + "/translate"
    Path(RESULT_DIR).mkdir(exist_ok=True)
    SOURCE_DIR=RESULT_DIR

    def feed(d):
        if winobj.has_done or config.box_trans!='ing':
            return
        d = json.loads(d)
        if d['type']!='error':
            winobj.loglabel.setStyleSheet("""color:#148cd2;background-color:transparent""")
            winobj.error_msg = ""
            winobj.loglabel.setToolTip('')

        if d['type'] == 'error':
            winobj.error_msg = d['text']
            winobj.has_done = True
            winobj.loglabel.setToolTip('点击查看详细出错信息' if config.defaulelang=='zh' else 'View  details error')
            winobj.loglabel.setStyleSheet("""color:#ff0000;background-color:transparent""")
            winobj.loglabel.setText(d['text'][:150])
            winobj.loglabel.setCursor(Qt.PointingHandCursor)
            winobj.fanyi_start.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            winobj.fanyi_start.setDisabled(False)
            winobj.fanyi_import.setDisabled(False)
        # 挨个从顶部添加已翻译后的文字
        elif d['type'] == 'subtitle':
            winobj.fanyi_targettext.moveCursor(QTextCursor.End)
            winobj.fanyi_targettext.insertPlainText(d['text'])
        elif d['type'] == 'replace':
            winobj.fanyi_targettext.clear()
            winobj.fanyi_targettext.setPlainText(d['text'])
        # 开始时清理目标区域，填充原区域
        elif d['type'] == 'clear_target':
            winobj.fanyi_targettext.clear()
        elif d['type'] == 'set_source':
            winobj.fanyi_sourcetext.clear()
            winobj.fanyi_sourcetext.setPlainText(d['text'])
        elif d['type'] in ['logs', 'succeed']:
            if d['text']:
                winobj.loglabel.setText(d["text"])
        elif d['type'] in ['stop', 'end']:
            winobj.has_done = True
            winobj.loglabel.setText(config.transobj['quanbuend'])
            winobj.fanyi_start.setText('执行完成/开始执行' if config.defaulelang == 'zh' else 'Ended/Start operate')
            winobj.fanyi_start.setDisabled(False)
            winobj.fanyi_import.setDisabled(False)
            winobj.daochu.setDisabled(False)
            config.box_trans = 'stop'
            winobj.fanyi_stop.setDisabled(True)

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
        global SOURCE_DIR
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR if not SOURCE_DIR else SOURCE_DIR))

    def fanyi_start_fun():
        global SOURCE_DIR
        
        Path(config.TEMP_HOME).mkdir(parents=True, exist_ok=True)
        
        winobj.has_done = False
        target_language = winobj.fanyi_target.currentText()
        translate_type = winobj.fanyi_translate_type.currentIndex()
        source_code,target_code = translator.get_source_target_code(show_source=winobj.fanyi_source.currentText(),show_target=target_language,translate_type=translate_type)
        if target_language == '-':
            return QMessageBox.critical(winobj, config.transobj['anerror'], config.transobj["fanyimoshi1"])
        proxy = winobj.fanyi_proxy.text()

        if proxy:
            tools.set_proxy(proxy)
            config.proxy = proxy
            config.settings['proxy'] = proxy

        rs = translator.is_allow_translate(translate_type=translate_type, show_target=target_code)
        if rs is not True:
            return False
        if len(winobj.files) < 1:
            return QMessageBox.critical(winobj, config.transobj['anerror'],
                                        '必须导入srt字幕文件' if config.defaulelang == 'zh' else 'Must import srt subtitle files')
        winobj.fanyi_sourcetext.clear()
        winobj.fanyi_targettext.clear()
        winobj.loglabel.setText('')

        config.box_trans = 'ing'
        config.settings['aisendsrt']=winobj.aisendsrt.isChecked()
        config.settings['refine3']=winobj.refine3.isChecked()
        with open(config.ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))


        video_list = [tools.format_video(it, None) for it in winobj.files]
        uuid_list = [obj['uuid'] for obj in video_list]
        if winobj.save_source.isChecked():
            SOURCE_DIR=Path(video_list[0]['name']).parent.as_posix()
        for it in video_list:
            trk = TranslateSrt({
                "out_format":winobj.out_format.currentIndex(),
                "translate_type": translate_type,
                "text_list": tools.get_subtitle_from_srt(it['name']),
                "target_dir": SOURCE_DIR if SOURCE_DIR else RESULT_DIR,
                "inst": None,
                "rename":True,
                "uuid": it['uuid'],
                "source_code": source_code,
                "target_code": target_code
            }, it)
            config.trans_queue.append(trk)

        th = SignThread(uuid_list=uuid_list, parent=winobj)
        th.uito.connect(feed)
        th.start()
        if len(video_list)==1:
            winobj.fanyi_sourcetext.setPlainText(Path(video_list[0]['name']).read_text(encoding='utf-8'))
            winobj.exportsrt.setVisible(True)
            winobj.fanyi_targettext.setReadOnly(False)
        else:
            winobj.fanyi_targettext.setReadOnly(True)
            winobj.exportsrt.setVisible(False)

        config.params["trans_translate_type"]=winobj.fanyi_translate_type.currentIndex()
        config.params["trans_source_language"]=winobj.fanyi_source.currentIndex()
        config.params["trans_target_language"]=winobj.fanyi_target.currentIndex()
        config.params["trans_out_format"]=winobj.out_format.currentIndex()
        config.getset_params(config.params)

        winobj.fanyi_start.setDisabled(True)
        winobj.fanyi_stop.setDisabled(False)
        winobj.fanyi_start.setText(config.transobj["running"])
        winobj.daochu.setDisabled(True)

    # 翻译目标语言变化时
    def target_lang_change(t):
        if t in ['-', 'No']:
            return
        # 判断翻译渠道是否支持翻译到该目标语言
        if translator.is_allow_translate(translate_type=winobj.fanyi_translate_type.currentIndex(), show_target=t,win=winobj) is not True:
            return

    # 获取新增的google翻译语言代码
    def get_google_trans_newcode():
        new_langcode = []
        if config.settings['google_trans_newadd']:
            new_langcode = config.settings['google_trans_newadd'].strip().split(',')
        return new_langcode

    # 更新目标语言列表
    def update_target_language():
        current_target = winobj.fanyi_target.currentText()
        language_namelist = ["-"] + [ it for it in config.langnamelist if config.rev_langlist[it]!='auto']
        if winobj.fanyi_translate_type.currentIndex() in [translator.GOOGLE_INDEX,translator.FREEGOOGLE_INDEX]:
            language_namelist += get_google_trans_newcode()
        winobj.fanyi_target.clear()
        winobj.fanyi_target.addItems(language_namelist)
        if current_target and current_target != '-' and current_target in language_namelist:
            winobj.fanyi_target.setCurrentText(current_target)
        winobj.aisendsrt.setChecked(config.settings.get('aisendsrt'))
        winobj.refine3.setChecked(config.settings.get('refine3'))



    # 翻译渠道变化时重新设置目标语言
    def translate_type_change(idx):
        update_target_language()
        target_lang_change(winobj.fanyi_target.currentText())
        show_model_list()

    # 显示模型列表
    def show_model_list():
        idx=winobj.fanyi_translate_type.currentIndex()
        if idx==translator.LOCALLLM_INDEX:
            model_list = config.settings['localllm_model'].strip().split(',')
            current_model=config.params["localllm_model"]
        elif idx==translator.GEMINI_INDEX:
            model_list = config.settings['gemini_model'].strip().split(',')
            current_model=config.params["gemini_model"]
        elif idx==translator.CHATGPT_INDEX:
            model_list = config.settings['chatgpt_model'].strip().split(',')
            current_model=config.params["chatgpt_model"]
        elif idx==translator.AZUREGPT_INDEX:
            model_list = config.settings['azure_model'].strip().split(',')
            current_model=config.params["azure_model"]
        elif idx==translator.ZIJIE_INDEX:
            model_list = config.settings['zijiehuoshan_model'].strip().split(',')
            current_model=config.params["zijiehuoshan_model"]

        else:
            winobj.fanyi_model_list.setVisible(False)
            return

        winobj.fanyi_model_list.clear()
        winobj.fanyi_model_list.addItems(model_list)
        if current_model in model_list:
            winobj.fanyi_model_list.setCurrentText(current_model)
        winobj.fanyi_model_list.setVisible(True)

    # 模型变化
    def model_change():
        idx=winobj.fanyi_translate_type.currentIndex()
        model_name=winobj.fanyi_model_list.currentText()
        if idx == translator.LOCALLLM_INDEX:
            config.params["localllm_model"]=model_name
        elif idx == translator.GEMINI_INDEX:
            config.params["gemini_model"]=model_name
        elif idx == translator.CHATGPT_INDEX:
            config.params["chatgpt_model"]=model_name
        elif idx == translator.AZUREGPT_INDEX:
            config.params["azure_model"]=model_name
        elif idx == translator.ZIJIE_INDEX:
            config.params["zijiehuoshan_model"]=model_name

        config.getset_params(config.params)

    def pause_trans():
        config.box_trans='stop'
        winobj.has_done = True
        winobj.loglabel.setText('Stoped')
        winobj.fanyi_start.setText('开始执行' if config.defaulelang == 'zh' else 'Start operate')
        winobj.fanyi_import.setDisabled(False)
        winobj.daochu.setDisabled(False)
        winobj.fanyi_start.setDisabled(False)
        winobj.fanyi_stop.setDisabled(True)

    def show_detail_error():
        if winobj.error_msg:
            QMessageBox.critical(winobj,config.transobj['anerror'],winobj.error_msg)

    def export_srt():
        srt_string=winobj.fanyi_targettext.toPlainText().strip()
        if not srt_string:
            return QMessageBox.critical(winobj,config.transobj['anerror'],'没有翻译结果，无需保存' if config.defaulelang == 'zh' else 'No result, no need to save')
        dialog = QFileDialog()
        dialog.setWindowTitle(config.transobj['savesrtto'])
        dialog.setNameFilters(["subtitle files (*.srt)"])
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.exec_()
        if not dialog.selectedFiles():
            return
        else:
            path_to_file = dialog.selectedFiles()[0]
        ext = ".srt"
        if path_to_file.endswith('.srt') or path_to_file.endswith('.txt'):
            path_to_file = path_to_file[:-4] + ext
        else:
            path_to_file += ext
        with open(path_to_file, "w", encoding='utf-8') as file:
            file.write(srt_string)


    def checkbox_state_changed(state):
        """复选框状态发生变化时触发的函数"""
        if state:
            config.settings['aisendsrt']=True
        else:
            config.settings['aisendsrt']=False

    from videotrans.component import Fanyisrt
    try:
        winobj = config.child_forms.get('fanyiform')

        if winobj is not None:
            print("show")
            winobj.show()
            update_target_language()
            winobj.raise_()
            winobj.activateWindow()
            return

        winobj = Fanyisrt()
        config.child_forms['fanyiform'] = winobj
        winobj.fanyi_translate_type.addItems(translator.TRANSLASTE_NAME_LIST)
        winobj.fanyi_translate_type.setCurrentIndex(int(config.params.get('trans_translate_type',0)))

        update_target_language()
        winobj.fanyi_source.addItems(['-'] + config.langnamelist)
        winobj.fanyi_import.clicked.connect(fanyi_import_fun)
        winobj.fanyi_start.clicked.connect(fanyi_start_fun)
        winobj.fanyi_stop.clicked.connect(pause_trans)

        winobj.fanyi_source.setCurrentIndex(config.params.get("trans_source_language",0))
        winobj.fanyi_target.setCurrentIndex(config.params.get("trans_target_language",0))
        winobj.out_format.setCurrentIndex(config.params.get("trans_out_format",0))

        winobj.fanyi_target.currentTextChanged.connect(target_lang_change)

        show_model_list()
        winobj.fanyi_translate_type.currentIndexChanged.connect(translate_type_change)

        winobj.fanyi_sourcetext = QPlainTextEdit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        winobj.fanyi_sourcetext.setSizePolicy(sizePolicy)
        winobj.fanyi_sourcetext.setMinimumSize(300, 0)
        winobj.fanyi_proxy.setText(config.proxy)

        winobj.fanyi_sourcetext.setPlaceholderText(config.transobj['tuodongfanyi'])
        winobj.fanyi_sourcetext.setToolTip(config.transobj['tuodongfanyi'])
        winobj.fanyi_sourcetext.setReadOnly(True)

        winobj.fanyi_layout.insertWidget(0, winobj.fanyi_sourcetext)
        winobj.daochu.clicked.connect(fanyi_save_fun)
        winobj.fanyi_model_list.currentTextChanged.connect(model_change)
        winobj.loglabel.clicked.connect(show_detail_error)
        winobj.exportsrt.clicked.connect(export_srt)
        winobj.glossary.clicked.connect(lambda:tools.show_glossary_editor(winobj))
        winobj.aisendsrt.toggled.connect(checkbox_state_changed)


        winobj.show()
    except Exception as e:
        print(e)
