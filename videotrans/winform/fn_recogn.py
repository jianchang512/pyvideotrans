

def openwin():
    import json
    from pathlib import Path
    from PySide6 import QtWidgets
    from PySide6.QtCore import QUrl,QTimer
    from PySide6.QtGui import QDesktopServices, QTextCursor, Qt
    from videotrans.util import contants
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from videotrans.task._speech2text import SpeechToText
    from videotrans.task.taskcfg import TaskCfgSTT
    from videotrans import translator, recognition
    RESULT_DIR = HOME_DIR + f"/recogn"
    COPYSRT_TO_RAWDIR = RESULT_DIR
    uuid_list=[]

    def feed(d):
        if winobj.has_done:
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
            winobj.has_done = True
            toggle_state(False)
            winobj.loglabel.setText(tr('quanbuend'))
            winobj.shibie_startbtn.setText(tr("zhixingwc"))
            winobj.shibie_dropbtn.setText(tr('quanbuend') + ". " + tr('xuanzeyinshipin'))

    def opendir_fn():
        QDesktopServices.openUrl(QUrl.fromLocalFile(COPYSRT_TO_RAWDIR))


    def toggle_state(state):
        winobj.shibie_language.setDisabled(state)
        winobj.is_cuda.setDisabled(state)
        winobj.shibie_recogn_type.setDisabled(state)
        winobj.shibie_model.setDisabled(state)
        winobj.out_format.setDisabled(state)
        winobj.shibie_opendir.setDisabled(state)
        winobj.shibie_startbtn.setDisabled(state)
        winobj.shibie_dropbtn.setDisabled(state)
        winobj.rephrase.setDisabled(state)
        winobj.remove_noise.setDisabled(state)
        winobj.fix_punc.setDisabled(state)
        winobj.copysrt_rawvideo.setDisabled(state)
        winobj.shibie_stop.setDisabled(not state)


    def shibie_start_fun():
        nonlocal COPYSRT_TO_RAWDIR,uuid_list
        uuid_list=[]
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        winobj.has_done = False
        model = winobj.shibie_model.currentText()
        recogn_type = winobj.shibie_recogn_type.currentIndex()
        if recogn_type == recognition.Faster_Whisper_XXL and not show_xxl_select():
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

        if winobj.rephrase.currentIndex()==1:
            ai_type = settings.get('llm_ai_type', 'openai')
            if ai_type == 'openai' and not params.get('chatgpt_key'):
                tools.show_error(tr('llmduanju'))
                from videotrans.winform import chatgpt
                chatgpt.openwin()
                return
            if ai_type == 'deepseek' and not params.get('deepseek_key'):
                tools.show_error(tr('llmduanjudp'))
                from videotrans.winform import deepseek
                deepseek.openwin()
                return
        enable_diariz_is=winobj.enable_diariz.isChecked()

        toggle_state(True)
        winobj.shibie_startbtn.setText(tr("running"))
        winobj.label_shibie10.setText('')
        winobj.shibie_text.clear()
        stt_rephrase= int(winobj.rephrase.currentIndex())
        settings.save()

        try:
            COPYSRT_TO_RAWDIR = RESULT_DIR if not winobj.copysrt_rawvideo.isChecked() else RESULT_DIR
            winobj.loglabel.setText('')
            video_list = [tools.format_video(it, None) for it in files]
            uuid_list = [obj['uuid'] for obj in video_list]
            remove_noise_is=winobj.remove_noise.isChecked()
            fix_punc=winobj.fix_punc.isChecked()
            nums_diariz=winobj.nums_diariz.currentIndex()
            for it in video_list:
                uuid_list.append(it['uuid'])
                cfg={
                    "recogn_type": recogn_type,
                    "model_name": model,
                    "is_cuda": is_cuda,
                    "target_dir": RESULT_DIR,
                    "detect_language": langcode,
                    "remove_noise": remove_noise_is,
                    "enable_diariz": enable_diariz_is,
                    "nums_diariz":nums_diariz,
                    "rephrase":stt_rephrase,
                    "fix_punc":fix_punc
                }
                try:
                    trk = SpeechToText(cfg=TaskCfgSTT(**cfg|it),out_format=winobj.out_format.currentText(),copysrt_rawvideo=winobj.copysrt_rawvideo.isChecked())
                    app_cfg.prepare_queue.put_nowait(trk)
                except Exception as e:
                    print(e)
            from videotrans.task.child_win_sign import SignThread
            th = SignThread(uuid_list=uuid_list, parent=winobj)
            th.uito.connect(feed)
            params["stt_source_language"] = winobj.shibie_language.currentIndex()
            params["stt_recogn_type"] = winobj.shibie_recogn_type.currentIndex()
            params["stt_model_name"] = winobj.shibie_model.currentText()
            params["stt_out_format"] = winobj.out_format.currentText()
            params["stt_remove_noise"] = remove_noise_is
            params["stt_copysrt_rawvideo"] = winobj.copysrt_rawvideo.isChecked()
            params["stt_enable_diariz"] = enable_diariz_is
            params["stt_nums_diariz"] = nums_diariz
            params["stt_spk_insert"] = winobj.spk_insert.isChecked()
            params["stt_rephrase"] = stt_rephrase
            params["stt_fix_punc"] = fix_punc
            params["stt_cuda"] = is_cuda
            params.save()
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
        return True

    def show_xxl_select():
        import sys
        if sys.platform != 'win32':
            tools.show_error(
                tr("faster-whisper-xxl.exe is only available on Windows"))
            return False
        if not settings.get('Faster_Whisper_XXL') or not Path(
                settings.get('Faster_Whisper_XXL', '')).exists():
            from PySide6.QtWidgets import QFileDialog
            exe, _ = QFileDialog.getOpenFileName(winobj,
                                                 tr("Select faster-whisper-xxl.exe"),
                                                 'C:/', f'Files(*.exe)')
            if exe:
                settings['Faster_Whisper_XXL'] = Path(exe).as_posix()
                return True
            return False
        return True
    
    def show_cpp_select():
        import sys
        cpp_path=settings.get('Whisper_cpp', '')
        if not cpp_path or not Path(cpp_path).exists():
            from videotrans.component.set_cpp import SetWhisperCPP
            dialog = SetWhisperCPP()
            if dialog.exec():  # OK 按钮被点击时 exec 返回 True
                cpp_path = dialog.get_values()
                if cpp_path and Path(cpp_path).is_file():
                    return True
            tools.show_error(
                tr("Must be selected, otherwise it cannot be used"))
            return False
        return True    

    # 识别类型改变时
    def model_type_change():
        lang = translator.get_code(show_text=winobj.shibie_language.currentText())
        recogn_type = winobj.shibie_recogn_type.currentIndex()
        is_allow_lang=recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type, model_name=winobj.shibie_model.currentText())
        if is_allow_lang is not True:
            winobj.loglabel.setText(is_allow_lang)
        else:
            winobj.loglabel.setText('')
    
    def recogn_type_change():
        recogn_type = winobj.shibie_recogn_type.currentIndex()
        if recogn_type == recognition.Faster_Whisper_XXL and not show_xxl_select():
            return
        if recogn_type == recognition.Whisper_CPP and not show_cpp_select():
            return
        # 仅在faster模式下，才涉及 均等分割和阈值等，其他均隐藏
        if recogn_type not in [recognition.FASTER_WHISPER,recognition.OPENAI_WHISPER]:  # openai-whisper
            tools.hide_show_element(winobj.hfaster_layout, False)

        if recogn_type not in [recognition.FASTER_WHISPER,
                               recognition.Faster_Whisper_XXL,
                               recognition.Whisper_CPP,
                               recognition.OPENAI_WHISPER,
                               recognition.FUNASR_CN,
                               recognition.Deepgram,
                               recognition.WHISPERX_API,
                               recognition.HUGGINGFACE_ASR,
                               recognition.QWENASR
                               ]:  # 可选模型，whisper funasr deepram
            winobj.shibie_model.setDisabled(True)
        else:
            winobj.shibie_model.setDisabled(False)
            winobj.shibie_model.clear()
            if recogn_type in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL, recognition.OPENAI_WHISPER,recognition.WHISPERX_API]:
                winobj.shibie_model.addItems(settings.WHISPER_MODEL_LIST)
            elif recogn_type == recognition.Deepgram:
                winobj.shibie_model.addItems(contants.DEEPGRAM_MODEL)
            elif recogn_type == recognition.Whisper_CPP:
                winobj.shibie_model.addItems(settings.Whisper_CPP_MODEL_LIST)
            elif recogn_type == recognition.QWENASR:
                winobj.shibie_model.addItems(['1.7B','0.6B'])
            elif recogn_type == recognition.HUGGINGFACE_ASR:
                winobj.shibie_model.addItems(list(recognition.HUGGINGFACE_ASR_MODELS.keys()))
            else:
                winobj.shibie_model.addItems(contants.FUNASR_MODEL)
        

            
        if recognition.is_input_api(recogn_type=recogn_type) is not True:
            return

        lang = translator.get_code(show_text=winobj.shibie_language.currentText())
        is_allow_lang_res = recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type,
                                                      model_name=winobj.shibie_model.currentText())
        if is_allow_lang_res is not True:
            winobj.loglabel.setText(is_allow_lang_res)
        else:
            winobj.loglabel.setText('')

    def stop_recogn():
        winobj.has_done = True
        winobj.loglabel.setText('Stoped')
        winobj.shibie_startbtn.setText(tr("zhixingwc"))
        winobj.shibie_dropbtn.setText(tr('xuanzeyinshipin'))
        for it in uuid_list:
            app_cfg.stoped_uuid_set.add(it)
        toggle_state(False)

    def show_detail_error():
        if winobj.error_msg:
            tools.show_error(winobj.error_msg)

    # 点击语音识别，显示隐藏faster时的详情设置
    def click_reglabel():
        if winobj.shibie_recogn_type.currentIndex() in [recognition.FASTER_WHISPER,recognition.OPENAI_WHISPER]:
            tools.hide_show_element(winobj.hfaster_layout, not winobj.threshold.isVisible())
        else:
            tools.hide_show_element(winobj.hfaster_layout, False)


    from videotrans.component.set_form import Recognform


    winobj = Recognform()
    app_cfg.child_forms['fn_recogn'] = winobj
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
        winobj.is_cuda.setChecked(params.get("stt_cuda",False))
        winobj.is_cuda.toggled.connect(check_cuda)
        winobj.rephrase.setCurrentIndex(int(params.get('stt_rephrase',2)))
        winobj.remove_noise.setChecked(bool(params.get('stt_remove_noise')))
        winobj.copysrt_rawvideo.setChecked(params.get('stt_copysrt_rawvideo', False))
        winobj.spk_insert.setChecked(bool(params.get('stt_spk_insert', False)))
        winobj.enable_diariz.setChecked(bool(params.get('stt_enable_diariz', False)))
        winobj.fix_punc.setChecked(bool(params.get('stt_fix_punc', False)))

        winobj.nums_diariz.setCurrentIndex(int(params.get("stt_nums_diariz",0)))
        winobj.out_format.setCurrentText(params.get('stt_out_format', 'srt'))

        default_lang = int(params.get('stt_source_language', 0))
        winobj.shibie_language.setCurrentIndex(default_lang)
        try:
            default_type = int(params.get('stt_recogn_type', 0))
        except ValueError:
            default_type = 0
        winobj.shibie_recogn_type.clear()
        winobj.shibie_recogn_type.addItems(recognition.RECOGN_NAME_LIST)
        winobj.shibie_recogn_type.setCurrentIndex(default_type)
        winobj.shibie_recogn_type.currentIndexChanged.connect(recogn_type_change)

        winobj.shibie_model.clear()
        if default_type == recognition.Deepgram:
            curr = contants.DEEPGRAM_MODEL
            winobj.shibie_model.addItems(curr)
        elif default_type == recognition.Whisper_CPP:
            curr = settings.Whisper_CPP_MODEL_LIST
            winobj.shibie_model.addItems(curr)
        elif default_type == recognition.FUNASR_CN:
            curr = contants.FUNASR_MODEL
            winobj.shibie_model.addItems(curr)
        elif default_type == recognition.QWENASR:
            curr=['1.7B','0.6B']
            winobj.shibie_model.addItems(curr)
        elif default_type == recognition.HUGGINGFACE_ASR:
            curr=list(recognition.HUGGINGFACE_ASR_MODELS.keys())
            winobj.shibie_model.addItems(curr)            
        else:
            curr = settings.WHISPER_MODEL_LIST
            winobj.shibie_model.addItems(settings.WHISPER_MODEL_LIST)
        if params.get('stt_model_name') in curr:
            current_model = params.get('stt_model_name')
            winobj.shibie_model.setCurrentText(current_model)
        
        
        if default_type not in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL, recognition.OPENAI_WHISPER,recognition.FUNASR_CN, recognition.Deepgram,recognition.Whisper_CPP,recognition.WHISPERX_API,recognition.HUGGINGFACE_ASR,recognition.QWENASR]:
            winobj.shibie_model.setDisabled(True)
        else:
            winobj.shibie_model.setDisabled(False)

        winobj.loglabel.clicked.connect(show_detail_error)
        winobj.shibie_model.currentIndexChanged.connect(model_type_change)


    QTimer.singleShot(10,_bind)
