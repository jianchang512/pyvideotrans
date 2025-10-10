

def openwin():
    from videotrans.configure.config import tr
    import json
    from pathlib import Path
    from PySide6 import QtWidgets
    from PySide6.QtCore import QUrl,QTimer
    from PySide6.QtGui import QDesktopServices, QTextCursor, Qt
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.task._speech2text import SpeechToText
    from videotrans.task.taskcfg import TaskCfg
    from videotrans import translator, recognition
    RESULT_DIR = config.HOME_DIR + f"/recogn"
    COPYSRT_TO_RAWDIR = RESULT_DIR

    def feed(d):
        if winobj.has_done or config.box_recogn != 'ing':
            return
        if isinstance(d, str):
            d = json.loads(d)

        if d['type'] != 'error':
            winobj.loglabel.setStyleSheet("""color:#148cd2;background-color:transparent""")
            winobj.error_msg = ""
            winobj.loglabel.setToolTip('')
        
        if d['type'] in ['replace', 'replace_subtitle']:
            winobj.shibie_text.clear()
            winobj.shibie_text.insertPlainText(d["text"])
        elif d['type'] == 'subtitle':
            winobj.shibie_text.moveCursor(QTextCursor.End)
            winobj.shibie_text.insertPlainText(d['text'])
        elif d['type'] == 'error':
            toggle_state(False)
            winobj.loglabel.setToolTip(tr("View  details error"))
            winobj.error_msg = d['text']
            winobj.has_done = True
            winobj.loglabel.setText(d['text'][:150])
            winobj.loglabel.setCursor(Qt.PointingHandCursor)
            winobj.loglabel.setStyleSheet("""color:#ff0000;background-color:transparent""")
            winobj.shibie_startbtn.setText(tr("Start"))
        elif d['type'] == 'logs' and d['text']:
            winobj.loglabel.setText(d['text'] + ' ... ')
        elif d['type'] in ['jindu', 'succeed']:
            winobj.shibie_startbtn.setText(d['text'])
        elif d['type'] in ['end']:
            config.box_recogn = 'stop'
            winobj.has_done = True
            toggle_state(False)
            winobj.loglabel.setText(tr('quanbuend'))
            winobj.shibie_startbtn.setText(tr("zhixingwc"))
            winobj.shibie_dropbtn.setText(tr('quanbuend') + ". " + tr('xuanzeyinshipin'))

    def opendir_fn():
        QDesktopServices.openUrl(QUrl.fromLocalFile(COPYSRT_TO_RAWDIR))

    def check_model_name(recogn_type, model):
        res = recognition.check_model_name(
            recogn_type=recogn_type,
            name=model,
            source_language_isLast=winobj.shibie_language.currentIndex() == winobj.shibie_language.count() - 1,
            source_language_currentText=winobj.shibie_language.currentText()
        )

        if res is not True:
            return tools.show_error(res)
        if (
                model == 'paraformer-zh' and recogn_type == recognition.FUNASR_CN) or recogn_type == recognition.Deepgram or recogn_type == recognition.GEMINI_SPEECH:
            winobj.show_spk.setVisible(True)
        else:
            winobj.show_spk.setVisible(False)
        return True

    def toggle_state(state):
        winobj.shibie_language.setDisabled(state)
        winobj.is_cuda.setDisabled(state)
        winobj.shibie_recogn_type.setDisabled(state)
        winobj.shibie_model.setDisabled(state)
        winobj.show_spk.setDisabled(state)
        winobj.shibie_split_type.setDisabled(state)
        winobj.equal_split_time.setDisabled(state)
        winobj.out_format.setDisabled(state)
        winobj.shibie_opendir.setDisabled(state)
        winobj.shibie_startbtn.setDisabled(state)
        winobj.shibie_dropbtn.setDisabled(state)
        winobj.rephrase.setDisabled(state)
        winobj.rephrase_local.setDisabled(state)
        winobj.remove_noise.setDisabled(state)
        winobj.copysrt_rawvideo.setDisabled(state)
        winobj.shibie_stop.setDisabled(not state)

    def shibie_start_fun():
        nonlocal COPYSRT_TO_RAWDIR
        Path(config.TEMP_HOME).mkdir(parents=True, exist_ok=True)
        winobj.has_done = False
        model = winobj.shibie_model.currentText()
        split_type_index = winobj.shibie_split_type.currentIndex()
        recogn_type = winobj.shibie_recogn_type.currentIndex()
        if recogn_type == recognition.Faster_Whisper_XXL and not show_xxl_select():
            return

        if check_model_name(recogn_type, model) is not True:
            return
        langcode = translator.get_audio_code(show_source=winobj.shibie_language.currentText())
        is_cuda = winobj.is_cuda.isChecked()
        if check_cuda(is_cuda) is not True:
            return tools.show_error(tr("nocudnn"))
        # 待识别音视频文件列表
        files = winobj.shibie_dropbtn.filelist
        if not files or len(files) < 1:
            return tools.show_error(tr('bixuyinshipin'))

        is_allow_lang_res = recognition.is_allow_lang(langcode=langcode, recogn_type=recogn_type, model_name=model)
        if is_allow_lang_res is not True:
            winobj.loglabel.setText(is_allow_lang_res)
        else:
            winobj.loglabel.setText('')
        # 判断是否填写自定义识别api openai-api识别、zh_recogn识别信息
        if recognition.is_input_api(recogn_type=recogn_type) is not True:
            return

        if winobj.rephrase.isChecked():
            ai_type = config.settings.get('llm_ai_type', 'openai')
            if ai_type == 'openai' and not config.params.get('chatgpt_key'):
                tools.show_error(tr('llmduanju'))
                from videotrans.winform import chatgpt
                chatgpt.openwin()
                return
            if ai_type == 'deepseek' and not config.params.get('deepseek_key'):
                tools.show_error(tr('llmduanjudp'))
                from videotrans.winform import deepseek
                deepseek.openwin()
                return
        toggle_state(True)
        winobj.shibie_startbtn.setText(tr("running"))
        winobj.label_shibie10.setText('')
        winobj.shibie_text.clear()
        if recogn_type == recognition.FASTER_WHISPER and split_type_index == 1:
            try:
                config.settings['interval_split'] = int(winobj.equal_split_time.text().strip())
            except ValueError:
                config.settings['interval_split'] = 10
        config.settings['rephrase'] = winobj.rephrase.isChecked()
        config.settings['rephrase_local'] = winobj.rephrase_local.isChecked()
        with open(config.ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))

        try:
            COPYSRT_TO_RAWDIR = RESULT_DIR if not winobj.copysrt_rawvideo.isChecked() else RESULT_DIR
            winobj.loglabel.setText('')
            config.box_recogn = 'ing'
            video_list = [tools.format_video(it, None) for it in files]
            uuid_list = [obj['uuid'] for obj in video_list]
            for it in video_list:
                cfg={
                    "recogn_type": recogn_type,
                    "split_type": ["all", "avg"][split_type_index],
                    "model_name": model,
                    "cuda": is_cuda,
                    "target_dir": RESULT_DIR,
                    "detect_language": langcode,
                    "remove_noise": winobj.remove_noise.isChecked(),
                }
                try:
                    trk = SpeechToText(cfg=TaskCfg(**cfg|it),out_format=winobj.out_format.currentText(),copysrt_rawvideo=winobj.copysrt_rawvideo.isChecked())
                    config.prepare_queue.append(trk)
                except Exception as e:
                    print(e)
            from videotrans.task.child_win_sign import SignThread
            th = SignThread(uuid_list=uuid_list, parent=winobj)
            th.uito.connect(feed)
            config.params["stt_source_language"] = winobj.shibie_language.currentIndex()
            config.params["stt_recogn_type"] = winobj.shibie_recogn_type.currentIndex()
            config.params["stt_model_name"] = winobj.shibie_model.currentText()
            config.params["stt_out_format"] = winobj.out_format.currentText()
            config.params["stt_remove_noise"] = winobj.remove_noise.isChecked()
            config.params["stt_copysrt_rawvideo"] = winobj.copysrt_rawvideo.isChecked()
            config.params["paraformer_spk"] = winobj.show_spk.isChecked()
            config.getset_params(config.params)
            th.start()

        except Exception as e:
            from videotrans.configure._except import get_msg_from_except
            tools.show_error(get_msg_from_except(e))

    def check_cuda(state):
        # 选中如果无效，则取消
        if state:
            import torch
            if not torch.cuda.is_available():
                tools.show_error(tr('nocuda'))
                winobj.is_cuda.setChecked(False)
                winobj.is_cuda.setDisabled(True)
                return False
            if winobj.shibie_recogn_type.currentIndex() == recognition.OPENAI_WHISPER:
                return True

            if winobj.shibie_recogn_type.currentIndex() == recognition.FASTER_WHISPER:
                from torch.backends import cudnn
                if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                    tools.show_error(tr("nocudnn"))
                    winobj.is_cuda.setChecked(False)
                    winobj.is_cuda.setDisabled(True)
                    return False
        return True

    def show_xxl_select():
        import sys
        if sys.platform != 'win32':
            tools.show_error(
                tr("faster-whisper-xxl.exe is only available on Windows"))
            return False
        if not config.settings.get('Faster_Whisper_XXL') or not Path(
                config.settings.get('Faster_Whisper_XXL', '')).exists():
            from PySide6.QtWidgets import QFileDialog
            exe, _ = QFileDialog.getOpenFileName(winobj,
                                                 tr("Select faster-whisper-xxl.exe"),
                                                 'C:/', f'Files(*.exe)')
            if exe:
                config.settings['Faster_Whisper_XXL'] = Path(exe).as_posix()
                return True
            return False
        return True

    # 识别类型改变时
    def recogn_type_change():
        recogn_type = winobj.shibie_recogn_type.currentIndex()
        if recogn_type == recognition.Faster_Whisper_XXL and not show_xxl_select():
            return
        # 仅在faster模式下，才涉及 均等分割和阈值等，其他均隐藏
        if recogn_type != recognition.FASTER_WHISPER:  # openai-whisper
            winobj.shibie_split_type.setDisabled(True)
            winobj.shibie_split_type.setCurrentIndex(0)
            tools.hide_show_element(winobj.equal_split_layout, False)
            tools.hide_show_element(winobj.hfaster_layout, False)
        else:
            winobj.shibie_split_type.setDisabled(False)
            # faster
            tools.hide_show_element(winobj.equal_split_layout,
                                    True if winobj.shibie_split_type.currentIndex() == 1 else False)

        if recogn_type not in [recognition.FASTER_WHISPER,
                               recognition.Faster_Whisper_XXL,
                               recognition.OPENAI_WHISPER,
                               recognition.FUNASR_CN,
                               recognition.Deepgram
                               ]:  # 可选模型，whisper funasr deepram
            winobj.shibie_model.setDisabled(True)
            winobj.rephrase.setDisabled(True)
            winobj.rephrase_local.setDisabled(True)
        else:
            winobj.rephrase_local.setDisabled(False)
            winobj.rephrase.setDisabled(False)
            winobj.shibie_model.setDisabled(False)
            winobj.shibie_model.clear()
            if recogn_type in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL, recognition.OPENAI_WHISPER]:
                winobj.shibie_model.addItems(config.WHISPER_MODEL_LIST)
            elif recogn_type == recognition.Deepgram:
                winobj.shibie_model.addItems(config.DEEPGRAM_MODEL)
            else:
                winobj.shibie_model.addItems(config.FUNASR_MODEL)
        if check_model_name(recogn_type, winobj.shibie_model.currentText()) is not True:
            return
        if recognition.is_input_api(recogn_type=recogn_type) is not True:
            return

        if recogn_type == recognition.Deepgram or recogn_type == recognition.GEMINI_SPEECH or (
                winobj.shibie_model.currentText() == 'paraformer-zh' and recogn_type == recognition.FUNASR_CN):
            winobj.show_spk.setVisible(True)
        else:
            winobj.show_spk.setVisible(False)
        lang = translator.get_code(show_text=winobj.shibie_language.currentText())
        is_allow_lang_res = recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type,
                                                      model_name=winobj.shibie_model.currentText())
        if is_allow_lang_res is not True:
            winobj.loglabel.setText(is_allow_lang_res)
        else:
            winobj.loglabel.setText('')

    def stop_recogn():
        config.box_recogn = 'stop'
        winobj.has_done = True
        winobj.loglabel.setText('Stoped')
        winobj.shibie_startbtn.setText(tr("zhixingwc"))
        winobj.shibie_dropbtn.setText(tr('xuanzeyinshipin'))
        toggle_state(False)

    def show_detail_error():
        if winobj.error_msg:
            tools.show_error(winobj.error_msg)

    # 点击语音识别，显示隐藏faster时的详情设置
    def click_reglabel():
        if winobj.shibie_recogn_type.currentIndex() == recognition.FASTER_WHISPER and winobj.shibie_split_type.currentIndex() == 0:
            tools.hide_show_element(winobj.hfaster_layout, not winobj.threshold.isVisible())
        else:
            tools.hide_show_element(winobj.hfaster_layout, False)

    # 整体识别和均等分割变化
    def shibie_split_type_change():
        split_type_index = winobj.shibie_split_type.currentIndex()
        recogn_type = winobj.shibie_recogn_type.currentIndex()
        # 如果是均等分割，则阈值相关隐藏
        if recogn_type != recognition.FASTER_WHISPER:
            tools.hide_show_element(winobj.hfaster_layout, False)
            tools.hide_show_element(winobj.equal_split_layout, False)
            winobj.shibie_split_type.setCurrentIndex(0)
            winobj.shibie_split_type.setDisabled(True)
        elif split_type_index == 1:
            tools.hide_show_element(winobj.hfaster_layout, False)
            tools.hide_show_element(winobj.equal_split_layout, True)
        else:
            tools.hide_show_element(winobj.equal_split_layout, False)


    def rephrase_fun(s,name):
        if s and name=='llm':
            winobj.rephrase_local.setChecked(False)
        elif s and name=='local':
            winobj.rephrase.setChecked(False)
            

    from videotrans.component import Recognform


    winobj = Recognform()
    config.child_forms['fn_recogn'] = winobj
    winobj.show()
    def _bind():
        Path(RESULT_DIR).mkdir(exist_ok=True,parents=True)
        from videotrans.component.component import DropButton
        winobj.shibie_dropbtn = DropButton(tr('xuanzeyinshipin'))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(winobj.shibie_dropbtn.sizePolicy().hasHeightForWidth())
        winobj.shibie_dropbtn.setSizePolicy(sizePolicy)
        winobj.shibie_dropbtn.setMinimumSize(0, 150)
        winobj.shibie_widget.insertWidget(0, winobj.shibie_dropbtn)
        winobj.shibie_language.addItems(list(translator.LANGNAME_DICT.values())+['auto'])
        winobj.shibie_label.clicked.connect(click_reglabel)

        winobj.shibie_startbtn.clicked.connect(shibie_start_fun)
        winobj.shibie_stop.clicked.connect(stop_recogn)
        winobj.shibie_opendir.clicked.connect(opendir_fn)
        winobj.is_cuda.toggled.connect(check_cuda)
        local_rephrase=config.settings.get('rephrase_local',False)
        winobj.rephrase_local.setChecked(local_rephrase)
        winobj.rephrase.setChecked(config.settings.get('rephrase',False) if not local_rephrase else False)
        winobj.remove_noise.setChecked(config.params.get('stt_remove_noise'))
        winobj.copysrt_rawvideo.setChecked(config.params.get('stt_copysrt_rawvideo', False))
        winobj.out_format.setCurrentText(config.params.get('stt_out_format', 'srt'))

        default_lang = int(config.params.get('stt_source_language', 0))
        winobj.shibie_language.setCurrentIndex(default_lang)
        try:
            default_type = int(config.params.get('stt_recogn_type', 0))
        except ValueError:
            default_type = 0
        winobj.shibie_recogn_type.clear()
        winobj.shibie_recogn_type.addItems(recognition.RECOGN_NAME_LIST)
        winobj.shibie_recogn_type.setCurrentIndex(default_type)
        winobj.shibie_recogn_type.currentIndexChanged.connect(recogn_type_change)

        winobj.shibie_model.clear()
        if default_type == recognition.Deepgram:
            curr = config.DEEPGRAM_MODEL
            winobj.shibie_model.addItems(config.DEEPGRAM_MODEL)
        elif default_type == recognition.FUNASR_CN:
            curr = config.FUNASR_MODEL
            winobj.shibie_model.addItems(config.FUNASR_MODEL)
        else:
            curr = config.WHISPER_MODEL_LIST
            winobj.shibie_model.addItems(config.WHISPER_MODEL_LIST)
        if config.params.get('stt_model_name') in curr:
            current_model = config.params.get('stt_model_name')
            winobj.shibie_model.setCurrentText(current_model)
            if current_model == 'paraformer-zh' or default_type == recognition.Deepgram or default_type == recognition.GEMINI_SPEECH:
                winobj.show_spk.setVisible(True)

        if default_type not in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL, recognition.OPENAI_WHISPER,recognition.FUNASR_CN, recognition.Deepgram]:
            winobj.shibie_model.setDisabled(True)
        else:
            winobj.shibie_model.setDisabled(False)

        winobj.loglabel.clicked.connect(show_detail_error)
        winobj.shibie_split_type.currentIndexChanged.connect(shibie_split_type_change)
        winobj.shibie_model.currentTextChanged.connect(
            lambda: check_model_name(winobj.shibie_recogn_type.currentIndex(), winobj.shibie_model.currentText()))

        winobj.rephrase.toggled.connect(lambda checked:rephrase_fun(checked,'llm'))
        winobj.rephrase_local.toggled.connect(lambda checked:rephrase_fun(checked,'local'))
    QTimer.singleShot(10,_bind)
