# 字幕批量翻译

def openwin():
    import json
    import os
    from pathlib import Path
    from PySide6.QtCore import QUrl,QTimer
    from PySide6.QtGui import QDesktopServices, QTextCursor, Qt
    from PySide6 import QtWidgets
    from PySide6.QtWidgets import QFileDialog, QPlainTextEdit
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.task.taskcfg import TaskCfgSTS

    from videotrans.util import tools
    from videotrans import translator
    from videotrans.task._translate_srt import TranslateSrt
    RESULT_DIR = HOME_DIR + "/translate"
    SOURCE_DIR = RESULT_DIR
    uuid_list=[]

    def toggle_state(state):
        winobj.fanyi_translate_type.setDisabled(state)
        winobj.fanyi_model_list.setDisabled(state)
        winobj.fanyi_source.setDisabled(state)
        winobj.fanyi_target.setDisabled(state)
        winobj.out_format.setDisabled(state)
        winobj.aisendsrt.setDisabled(state)
        winobj.fanyi_proxy.setDisabled(state)
        winobj.fanyi_import.setDisabled(state)
        winobj.save_source.setDisabled(state)
        winobj.exportsrt.setDisabled(state)
        winobj.fanyi_start.setDisabled(state)
        winobj.fanyi_stop.setDisabled(not state)
        winobj.fanyi_targettext.setDisabled(state)

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] != 'error':
            winobj.loglabel.setStyleSheet("""color:#148cd2;background-color:transparent""")
            winobj.error_msg = ""
            winobj.loglabel.setToolTip('')

        if d['type'] == 'error':
            winobj.error_msg = d['text']
            winobj.has_done = True
            winobj.loglabel.setToolTip(tr("View  details error"))
            winobj.loglabel.setStyleSheet("""color:#ff0000;background-color:transparent""")
            winobj.loglabel.setText(d['text'][:150])
            winobj.loglabel.setCursor(Qt.PointingHandCursor)
            winobj.fanyi_start.setText(tr("start operate"))
            toggle_state(False)
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
            winobj.loglabel.setText(tr('quanbuend'))
            winobj.fanyi_start.setText(tr("Ended/Start operate"))
            toggle_state(False)

    def fanyi_import_fun():
        fnames, _ = QFileDialog.getOpenFileNames(winobj,
                                                 tr('tuodongfanyi'),
                                                 params['last_opendir'],
                                                 "Subtitles files(*.srt)")
        if len(fnames) < 1:
            return
        namestr = []
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/').replace('file:///', '')
            namestr.append(os.path.basename(fnames[i]))
        if fnames:
            winobj.files = fnames
            params['last_opendir'] = os.path.dirname(fnames[0])
            winobj.fanyi_sourcetext.setPlainText(
                f'{tr("yidaorujigewenjian")}{len(fnames)}\n{",".join(namestr)}')

    def fanyi_save_fun():
        nonlocal SOURCE_DIR
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR if not SOURCE_DIR else SOURCE_DIR))

    def fanyi_start_fun():
        nonlocal SOURCE_DIR,uuid_list
        uuid_list=[]
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        winobj.has_done = False
        target_language = winobj.fanyi_target.currentText()
        translate_type = winobj.fanyi_translate_type.currentIndex()
        source_code, target_code = translator.get_source_target_code(show_source=winobj.fanyi_source.currentText(),
                                                                     show_target=target_language,
                                                                     translate_type=translate_type)
       
        if target_language == '-':
            return tools.show_error(tr("fanyimoshi1"))
        

        proxy = winobj.fanyi_proxy.text()

        if proxy:
            app_cfg.proxy = proxy
            tools.set_proxy(proxy)
            settings['proxy'] = proxy

        rs = translator.is_allow_translate(translate_type=translate_type, show_target=target_code)
        if rs is not True:
            return False
        if len(winobj.files) < 1:
            return tools.show_error(tr("Must import srt subtitle files"))
        winobj.fanyi_sourcetext.clear()
        winobj.fanyi_targettext.clear()
        winobj.loglabel.setText('')

        settings['aisendsrt'] = winobj.aisendsrt.isChecked()

        settings.save()

        video_list = [tools.format_video(it, None) for it in winobj.files]
        uuid_list = [obj['uuid'] for obj in video_list]
        if winobj.save_source.isChecked():
            SOURCE_DIR = Path(video_list[0]['name']).parent.as_posix()
        for it in video_list:
            uuid_list.append(it['uuid'])
            cfg={
                "translate_type": translate_type,
                "target_dir": SOURCE_DIR if SOURCE_DIR else RESULT_DIR,
                "uuid": it['uuid'],
                "source_language_code": source_code,
                "target_language_code": target_code
            }
            trk = TranslateSrt(cfg=TaskCfgSTS(**cfg|it),out_format=winobj.out_format.currentIndex())
            app_cfg.trans_queue.put_nowait(trk)
        from videotrans.task.child_win_sign import SignThread
        th = SignThread(uuid_list=uuid_list, parent=winobj)
        th.uito.connect(feed)
        th.start()
        if len(video_list) == 1:
            winobj.fanyi_sourcetext.setPlainText(Path(video_list[0]['name']).read_text(encoding='utf-8'))
            winobj.exportsrt.setVisible(True)
            winobj.fanyi_targettext.setReadOnly(False)
        else:
            winobj.fanyi_sourcetext.setPlainText(tr("Please wait patiently while the translation is in progress.."))
            winobj.fanyi_targettext.setReadOnly(True)
            winobj.exportsrt.setVisible(False)

        params["trans_translate_type"] = winobj.fanyi_translate_type.currentIndex()
        params["trans_source_language"] = winobj.fanyi_source.currentIndex()
        params["trans_target_language"] = winobj.fanyi_target.currentIndex()
        params["trans_out_format"] = winobj.out_format.currentIndex()
        params["trans_save_source"] = winobj.save_source.isChecked()
        params.save()

        toggle_state(True)
        winobj.fanyi_start.setText(tr("running"))

    # 翻译目标语言变化时
    def target_lang_change(t):
        if t in ['-', 'No']:
            return
        # 判断翻译渠道是否支持翻译到该目标语言
        if translator.is_allow_translate(translate_type=winobj.fanyi_translate_type.currentIndex(), show_target=t) is not True:
            return


    # 更新目标语言列表
    def update_target_language():
        current_target = winobj.fanyi_target.currentText()
        language_namelist = ["-"] + list(translator.LANGNAME_DICT.values())
        winobj.fanyi_target.clear()
        winobj.fanyi_target.addItems(language_namelist)
        if current_target and current_target != '-' and current_target in language_namelist:
            winobj.fanyi_target.setCurrentText(current_target)
        winobj.aisendsrt.setChecked(settings.get('aisendsrt'))

    # 翻译渠道变化时重新设置目标语言
    def translate_type_change(idx):
        update_target_language()
        target_lang_change(winobj.fanyi_target.currentText())
        show_model_list()

    # 显示模型列表
    def show_model_list():
        idx = winobj.fanyi_translate_type.currentIndex()
        if idx == translator.LOCALLLM_INDEX:
            model_list = settings.get('localllm_model','').strip().split(',')
            current_model = params["localllm_model"]
        elif idx == translator.GEMINI_INDEX:
            model_list = settings.get('gemini_model','').strip().split(',')
            current_model = params["gemini_model"]
        elif idx == translator.CHATGPT_INDEX:
            model_list = settings.get('chatgpt_model','').strip().split(',')
            current_model = params["chatgpt_model"]
        elif idx == translator.AZUREGPT_INDEX:
            model_list = settings.get('azure_model','').strip().split(',')
            current_model = params["azure_model"]
        elif idx == translator.ZIJIE_INDEX:
            model_list = settings.get('zijiehuoshan_model','').strip().split(',')
            current_model = params["zijiehuoshan_model"]

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
        idx = winobj.fanyi_translate_type.currentIndex()
        model_name = winobj.fanyi_model_list.currentText()
        if idx == translator.LOCALLLM_INDEX:
            params["localllm_model"] = model_name
        elif idx == translator.GEMINI_INDEX:
            params["gemini_model"] = model_name
        elif idx == translator.CHATGPT_INDEX:
            params["chatgpt_model"] = model_name
        elif idx == translator.AZUREGPT_INDEX:
            params["azure_model"] = model_name
        elif idx == translator.ZIJIE_INDEX:
            params["zijiehuoshan_model"] = model_name

        params.save()

    def pause_trans():
        winobj.has_done = True
        winobj.loglabel.setText('Stoped')
        winobj.fanyi_start.setText(tr("Start operate"))
        for it in uuid_list:
            app_cfg.stoped_uuid_set.add(it)
        toggle_state(False)

    def show_detail_error():
        if winobj.error_msg:
            tools.show_error(winobj.error_msg)

    def export_srt():
        srt_string = winobj.fanyi_targettext.toPlainText().strip()
        if not srt_string:
            return tools.show_error(tr("No result, no need to save"))
        dialog = QFileDialog()
        dialog.setWindowTitle(tr('savesrtto'))
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
            settings['aisendsrt'] = True
        else:
            settings['aisendsrt'] = False

    from videotrans.component.set_form import Fanyisrt

    winobj = Fanyisrt()
    app_cfg.child_forms['fn_fanyisrt'] = winobj
    winobj.show()
    def _bind():
        Path(RESULT_DIR).mkdir(parents=True,exist_ok=True)
        winobj.fanyi_translate_type.addItems(translator.TRANSLASTE_NAME_LIST)
        winobj.fanyi_translate_type.setCurrentIndex(int(params.get('trans_translate_type', 0)))

        update_target_language()
        winobj.fanyi_source.addItems(['-'] + list(translator.LANGNAME_DICT.values()))
        winobj.fanyi_import.clicked.connect(fanyi_import_fun)
        winobj.fanyi_start.clicked.connect(fanyi_start_fun)
        winobj.fanyi_stop.clicked.connect(pause_trans)

        winobj.fanyi_source.setCurrentIndex(params.get("trans_source_language", 0))
        winobj.fanyi_target.setCurrentIndex(params.get("trans_target_language", 0))
        winobj.out_format.setCurrentIndex(params.get("trans_out_format", 0))

        winobj.fanyi_target.currentTextChanged.connect(target_lang_change)

        show_model_list()
        winobj.fanyi_translate_type.currentIndexChanged.connect(translate_type_change)

        winobj.fanyi_sourcetext = QPlainTextEdit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        winobj.fanyi_sourcetext.setSizePolicy(sizePolicy)
        winobj.fanyi_sourcetext.setMinimumSize(300, 0)
        winobj.fanyi_proxy.setText(app_cfg.proxy)

        winobj.fanyi_sourcetext.setPlaceholderText(tr('tuodongfanyi'))
        winobj.fanyi_sourcetext.setToolTip(tr('tuodongfanyi'))
        winobj.fanyi_sourcetext.setReadOnly(True)

        winobj.fanyi_layout.insertWidget(0, winobj.fanyi_sourcetext)
        winobj.daochu.clicked.connect(fanyi_save_fun)
        winobj.fanyi_model_list.currentTextChanged.connect(model_change)
        winobj.loglabel.clicked.connect(show_detail_error)
        winobj.exportsrt.clicked.connect(export_srt)
        winobj.glossary.clicked.connect(lambda: tools.show_glossary_editor(winobj))
        winobj.aisendsrt.toggled.connect(checkbox_state_changed)
        winobj.save_source.setChecked(params.get("trans_save_source",False))

    QTimer.singleShot(10,_bind)

