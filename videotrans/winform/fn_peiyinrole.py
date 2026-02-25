

def openwin():
    from videotrans.util import contants
    from videotrans.task.taskcfg import TaskCfgTTS
    from videotrans.util.contants import LISTEN_TEXT
    import json
    import os
    from pathlib import Path
    from PySide6.QtCore import QUrl, Qt,QTimer
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR

    from videotrans.util import tools


    # ==================== 语言字典 (完整版) ====================
    langname_dict = {
        "zh-cn": "简体中文", "zh-tw": "繁体中文", "yue": "粤语", "en": "英语", "fr": "法语", "de": "德语", "ja": "日语", "ko": "韩语",
        "ru": "俄语", "es": "西班牙语",
        "th": "泰国语", "it": "意大利语", "pt": "葡萄牙语", "vi": "越南语", "ar": "阿拉伯语", "tr": "土耳其语", "hi": "印度语", "hu": "匈牙利语",
        "uk": "乌克兰语", "id": "印度尼西亚", "ms": "马来语", "kk": "哈萨克语", "cs": "捷克语", "pl": "波兰语", "nl": "荷兰语", "sv": "瑞典语",
        "he": "希伯来语", "bn": "孟加拉语", "fil": "菲律宾语", "af": "南非荷兰语", "sq": "阿尔巴尼亚语", "am": "阿姆哈拉语", "az": "阿塞拜疆语",
        "bs": "波斯尼亚语", "bg": "保加利亚语", "my": "缅甸语", "ca": "加泰罗尼亚语", "hr": "克罗地亚语", "da": "丹麦语", "et": "爱沙尼亚语",
        "fi": "芬兰语", "gl": "加利西亚语", "ka": "格鲁吉亚语", "el": "希腊语", "gu": "古吉拉特语", "is": "冰岛语", "iu": "因纽特语", "ga": "爱尔兰语",
        "jv": "爪哇语", "kn": "卡纳达语", "km": "高棉语", "lo": "老挝语", "lv": "拉脱维亚语", "lt": "立陶宛语", "mk": "马其顿语", "ml": "马拉雅拉姆语",
        "mt": "马耳他语", "mr": "马拉地语", "mn": "蒙古语", "ne": "尼泊尔语", "nb": "挪威语(书面挪威语)", "ps": "普什图语", "fa": "波斯语",
        "ro": "罗马尼亚语",
        "sr": "塞尔维亚语", "si": "僧伽罗语", "sk": "斯洛伐克语", "sl": "斯洛文尼亚语", "so": "索马里语", "su": "巽他语", "sw": "斯瓦希里语",
        "ta": "泰米尔语", "te": "泰卢固语", "ur": "乌尔都语", "uz": "乌兹别克语", "cy": "威尔士语", "zu": "祖鲁语"
    }
    if defaulelang != 'zh':
        langname_dict = {
            "zh-cn": "Simplified Chinese", "zh-tw": "Traditional Chinese", "yue": "Cantonese", "en": "English",
            "fr": "French", "de": "German", "ja": "Japanese",
            "ko": "Korean", "ru": "Russian", "es": "Spanish", "th": "Thai", "it": "Italian", "pt": "Portuguese",
            "vi": "Vietnamese",
            "ar": "Arabic", "tr": "Turkish", "hi": "Hindi", "hu": "Hungarian", "uk": "Ukrainian", "id": "Indonesian",
            "ms": "Malay",
            "kk": "Kazakh", "cs": "Czech", "pl": "Polish", "nl": "Dutch", "sv": "Swedish", "he": "Hebrew",
            "bn": "Bengali", "fil": "Filipino",
            "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "az": "Azerbaijani", "bs": "Bosnian",
            "bg": "Bulgarian", "my": "Burmese",
            "ca": "Catalan", "hr": "Croatian", "da": "Danish", "et": "Estonian", "fi": "Finnish", "gl": "Galician",
            "ka": "Georgian",
            "el": "Greek", "gu": "Gujarati", "is": "Icelandic", "iu": "Inuktitut", "ga": "Irish", "jv": "Javanese",
            "kn": "Kannada",
            "km": "Khmer", "lo": "Lao", "lv": "Latvian", "lt": "Lithuanian", "mk": "Macedonian", "ml": "Malayalam",
            "mt": "Maltese",
            "mr": "Marathi", "mn": "Mongolian", "ne": "Nepali", "nb": "Norwegian Bokmål", "ps": "Pashto",
            "fa": "Persian", "ro": "Romanian",
            "sr": "Serbian", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "so": "Somali", "su": "Sundanese",
            "sw": "Swahili",
            "ta": "Tamil", "te": "Telugu", "ur": "Urdu", "uz": "Uzbek", "cy": "Welsh", "zu": "Zulu"
        }

    RESULT_DIR = HOME_DIR + "/tts"
    uuid=None

    from videotrans.task._dubbing import DubbingSrt
    from videotrans import translator, tts

    def toggle_state(state):
        winobj.hecheng_importbtn.setDisabled(state)
        winobj.hecheng_language.setDisabled(state)
        winobj.tts_type.setDisabled(state)
        winobj.hecheng_role.setDisabled(state)
        winobj.listen_btn.setDisabled(state)
        winobj.hecheng_rate.setDisabled(state)
        winobj.voice_autorate.setDisabled(state)
        winobj.volume_rate.setDisabled(state)
        winobj.pitch_rate.setDisabled(state)
        winobj.out_format.setDisabled(state)
        winobj.save_to_srt.setDisabled(state)
        winobj.hecheng_startbtn.setDisabled(state)
        winobj.hecheng_importbtn.setDisabled(state)
        winobj.clear_button.setDisabled(state)
        winobj.tmp_rolelist.setDisabled(state)
        winobj.assign_role_button.setDisabled(state)
        winobj.hecheng_stop.setDisabled(not state)

    def feed(d):
        if winobj.has_done:
            return
        if isinstance(d, str):
            d = json.loads(d)
        if d['type'] != 'error':
            winobj.loglabel.setStyleSheet("""color:#148cd2;background-color:transparent""")
            winobj.error_msg = ""
            winobj.loglabel.setToolTip('')
        if d['type'] == 'replace':
            # This logic is no longer used as we don't have the hecheng_plaintext
            pass
        elif d['type'] == 'error':
            winobj.error_msg = d['text']
            winobj.loglabel.setToolTip(tr("View details error"))
            winobj.has_done = True
            winobj.hecheng_startbtn.setText(tr("zhixingwc"))
            toggle_state(False)
            winobj.loglabel.setText(d['text'][:150])
            winobj.loglabel.setStyleSheet("""color:#ff0000;background-color:transparent""")
            winobj.loglabel.setCursor(Qt.PointingHandCursor)
        elif d['type'] in ['logs', 'succeed']:
            if d['text']:
                winobj.loglabel.setText(d['text'])
        elif d['type'] == 'jindu':
            winobj.hecheng_startbtn.setText(d['text'])
        elif d['type'] == 'end':
            winobj.has_done = True
            winobj.loglabel.setText(tr('quanbuend'))
            winobj.hecheng_startbtn.setText(tr("zhixingwc"))
            toggle_state(False)

    def listen_voice_fun():
        lang = translator.get_code(show_text=winobj.hecheng_language.currentText())
        if not lang or lang == '-':
            return tools.show_error(tr("The voice is not support listen"))
        text = LISTEN_TEXT.get(f'{lang}')
        if not text:
            return tools.show_error(tr('The current language does not support audition'))
        role = winobj.hecheng_role.currentText()
        if not role or role == 'No':
            return tools.show_error(tr('mustberole'))
        voice_dir = TEMP_DIR + '/listen_voice'
        Path(voice_dir).mkdir(parents=True, exist_ok=True)
        lujing_role = role.replace('/', '-')

        rate = int(winobj.hecheng_rate.value())
        tts_type = winobj.tts_type.currentIndex()

        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        volume = int(winobj.volume_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = int(winobj.pitch_rate.value())
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{pitch}Hz'

        voice_file = f"{voice_dir}/{tts_type}-{lang}-{lujing_role}-{volume}-{pitch}.wav"

        obj = {
            "text": text, 
            "rate": rate, 
            "role": role, 
            "filename": voice_file, 
            "tts_type": tts_type,
            "language": lang, 
            "volume": volume, 
            "pitch": pitch,
        }

        if role == 'clone':
            return

        raw_text=winobj.listen_btn.text()
        def feed(d):
            winobj.listen_btn.setDisabled(False)
            winobj.listen_btn.setText(raw_text)
            if d != "ok":
                tools.show_error(d)
        winobj.listen_btn.setDisabled(True)
        winobj.listen_btn.setText('load...')
        from videotrans.util.ListenVoice import ListenVoice
        wk = ListenVoice(parent=winobj, queue_tts=[obj], language=lang, tts_type=tts_type)
        wk.uito.connect(feed)
        wk.start()
        
        

    def change_by_lang(type):
        return type in [tts.EDGE_TTS, tts.MINIMAXI_TTS,tts.AZURE_TTS, tts.DOUBAO_TTS,tts.DOUBAO2_TTS,tts.AI302_TTS, tts.KOKORO_TTS,tts.PIPER_TTS,tts.VITSCNEN_TTS,tts.FreeAzure]

    def hecheng_start_fun():
        nonlocal RESULT_DIR,uuid

        if not winobj.srt_path:
            return tools.show_error(
                tr("Please import an SRT subtitle file first."))

        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        winobj.has_done = False
        language = winobj.hecheng_language.currentText()
        role = winobj.hecheng_role.currentText()  # Default role
        rate = int(winobj.hecheng_rate.value())
        tts_type = winobj.tts_type.currentIndex()

        if language == '-' or role in ['No', '-', '']:
            return tools.show_error(tr("A default role must be selected"))

        if tts.is_input_api(tts_type=tts_type) is not True:
            return False

        if tts_type != tts.EDGE_TTS:
            langcode = translator.get_code(show_text=language)
            is_allow_lang_res = tts.is_allow_lang(langcode=langcode, tts_type=tts_type)
            if is_allow_lang_res is not True:
                winobj.loglabel.setText(is_allow_lang_res)
            else:
                winobj.loglabel.setText('')
        else:
            code_list = [key for key, value in langname_dict.items() if value == language]
            if not code_list:
                return tools.show_error(f'{language} is not support -1')
            langcode = code_list[0]
        toggle_state(True)
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        volume = int(winobj.volume_rate.value())
        pitch = int(winobj.pitch_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{pitch}Hz'

        if winobj.save_to_srt.isChecked():
            RESULT_DIR = Path(winobj.srt_path).parent.as_posix()

        video_obj = tools.format_video(winobj.srt_path, None)
        uuid = video_obj['uuid']
        cfg={
            "voice_role": role,  # Default role
            "cache_folder": TEMP_DIR + f'/{uuid}',
            "target_language_code": langcode,
            "target_dir": RESULT_DIR,
            "voice_rate": rate,
            "volume": volume,
            "uuid": uuid,
            "pitch": pitch,
            "tts_type": tts_type,
            "voice_autorate": winobj.voice_autorate.isChecked(),
            "remove_silent_mid": winobj.remove_silent_mid.isChecked(),
            "align_sub_audio":False,
            "is_cuda":winobj.is_cuda.isChecked()
        }


        trk = DubbingSrt(cfg=TaskCfgTTS(**cfg | video_obj),subs=winobj.subtitles,is_multi_role=True,out_ext=winobj.out_format.currentText())
        app_cfg.dubb_queue.put_nowait(trk)
        from videotrans.task.child_win_sign import SignThread
        th = SignThread(uuid_list=[uuid], parent=winobj)
        th.uito.connect(feed)
        th.start()

        winobj.hecheng_startbtn.setText(tr("running"))
        params["dubb_source_language"] = winobj.hecheng_language.currentIndex()
        params["dubb_tts_type"] = winobj.tts_type.currentIndex()
        params["dubb_role"] = winobj.hecheng_role.currentIndex()
        params["dubb_out_format"] = winobj.out_format.currentIndex()
        params["dubb_voice_autorate"] = winobj.voice_autorate.isChecked()
        params["dubb_save_to_srt"] = winobj.save_to_srt.isChecked()
        params["dubb_is_cuda"] = winobj.is_cuda.isChecked()
        params["dubb_hecheng_rate"] = int(winobj.hecheng_rate.value())
        params["dubb_pitch_rate"] = int(winobj.pitch_rate.value())
        params["dubb_volume_rate"] = int(winobj.volume_rate.value())
        if not params["dubb_voice_autorate"]:
            params['dubb_remove_silent_mid']=winobj.remove_silent_mid.isChecked()
        params.save()

    def stop_tts():
        nonlocal uuid
        winobj.has_done = True
        winobj.loglabel.setText('Stoped')
        winobj.hecheng_startbtn.setText(tr("zhixingwc"))
        toggle_state(False)
        if uuid:
            app_cfg.stoped_uuid_set.add(uuid)
        uuid = None
    def getlangnamelist(tts_type=0):
        if tts_type != tts.EDGE_TTS:
            return ['-'] + list(translator.LANGNAME_DICT.values())
        return ['-'] + list(langname_dict.values())

    def tts_type_change(type):
        app_cfg.dubbing_role={}
        if change_by_lang(type):
            winobj.volume_rate.setDisabled(False)
            winobj.pitch_rate.setDisabled(False)
        else:
            winobj.volume_rate.setDisabled(True)
            winobj.pitch_rate.setDisabled(True)

        if type == tts.QWEN3LOCAL_TTS:
            winobj.is_cuda.show()
        else:
            winobj.is_cuda.hide()

        current_text = winobj.hecheng_language.currentText()

        winobj.hecheng_language.clear()
        langnamelist = getlangnamelist(type)

        winobj.hecheng_language.addItems(langnamelist)
        if current_text in langnamelist:
            winobj.hecheng_language.setCurrentText(current_text)

        if type != tts.EDGE_TTS:
            code = translator.get_code(show_text=current_text)
            is_allow_lang_res = tts.is_allow_lang(langcode=code, tts_type=type)
            if is_allow_lang_res is not True:
                winobj.loglabel.setText(is_allow_lang_res)
            else:
                winobj.loglabel.setText('')
            if tts.is_input_api(tts_type=type) is not True:
                winobj.tts_type.setCurrentIndex(0)
                return False

        role_list=['No']
        winobj.hecheng_role.clear()
        if change_by_lang(type):
            return hecheng_language_fun(winobj.hecheng_language.currentText())
        if type == tts.GOOGLE_TTS:
            role_list=['No','gtts']
        elif type == tts.CHATTTS:
            role_list.extend(list(settings.ChatTTS_voicelist))
        elif type == tts.OPENAI_TTS:
            role_list=contants.OPENAITTS_ROLES.split(',')
        elif type == tts.QWEN_TTS:
            role_list=list(tools.get_qwen3tts_rolelist().keys())
        elif type == tts.QWEN3LOCAL_TTS:
            role_list=list(tools.get_qwenttslocal_rolelist().keys())
        elif type == tts.Supertonic_TTS:
            role_list=list(tools.get_supertonic_rolelist().keys())
        elif type == tts.GLM_TTS:
            role_list=list(tools.get_glmtts_rolelist().keys())
        elif type == tts.GEMINI_TTS:
            role_list.extend(contants.GEMINITTS_ROLES.split(','))
        elif type == tts.ELEVENLABS_TTS:
            role_list =  tools.get_elevenlabs_role()
        elif type == tts.CLONE_VOICE_TTS:
            role_list.extend([it for it in params["clone_voicelist"] if it != 'clone'])
        elif type == tts.TTS_API:
            role_list=params['ttsapi_voice_role'].split(",")
        elif type == tts.GPTSOVITS_TTS:
            role_list = list(tools.get_gptsovits_role().keys())
        elif type == tts.CHATTERBOX_TTS:
            role_list = tools.get_chatterbox_role()
        elif type == tts.COSYVOICE_TTS:
            role_list = list(tools.get_cosyvoice_role().keys())
        elif type == tts.FISHTTS:
            role_list = list(tools.get_fishtts_role().keys())
        elif type in [tts.F5_TTS,tts.INDEX_TTS,tts.SPARK_TTS,tts.VOXCPM_TTS,tts.DIA_TTS]:
            role_list = list(tools.get_f5tts_role().keys())
        if 'clone' in role_list:
            role_list.remove('clone')
        winobj.hecheng_role.addItems(role_list)


    def hecheng_language_fun(t):
        tts_type = winobj.tts_type.currentIndex()
        if tts_type == tts.EDGE_TTS:
            code_list = [key for key, value in langname_dict.items() if value == t]
            code = code_list[0] if code_list else '-'
        else:
            code = translator.get_code(show_text=t)
            if code and code != '-':
                is_allow_lang_reg = tts.is_allow_lang(langcode=code, tts_type=tts_type)
                if is_allow_lang_reg is not True:
                    winobj.loglabel.setText(is_allow_lang_reg)
                else:
                    winobj.loglabel.setText('')

        if not change_by_lang(tts_type):
            return

        winobj.hecheng_role.clear()
        if t == '-':
            winobj.hecheng_role.addItems(['No'])
            return
        if not code:
            winobj.hecheng_role.addItems(['No'])
            return
        vt = code.split('-')[0] #if code != 'yue' else "zh"

        show_rolelist = {}
        if tts_type == tts.EDGE_TTS:
            show_rolelist = tools.get_edge_rolelist()
        elif tts_type == tts.KOKORO_TTS:
            show_rolelist = tools.get_kokoro_rolelist()
        elif tts_type == tts.PIPER_TTS:
            show_rolelist = tools.get_piper_role()
        elif tts_type == tts.VITSCNEN_TTS:
            show_rolelist = tools.get_vits_role()
        elif tts_type == tts.AI302_TTS:
            show_rolelist = tools.get_302ai()
        elif tts_type == tts.DOUBAO2_TTS:
            show_rolelist = tools.get_doubao2_rolelist()
        elif tts_type == tts.DOUBAO_TTS:
            show_rolelist = tools.get_doubao_rolelist()
        elif tts_type == tts.MINIMAXI_TTS:
            show_rolelist = tools.get_minimaxi_rolelist()
        else:  # AzureTTS
            show_rolelist = tools.get_azure_rolelist()

        if not show_rolelist:
            winobj.hecheng_language.setCurrentText('-')
            tools.show_error(tr('nojueselist'))
            return
        if vt not in show_rolelist:
            winobj.hecheng_role.addItems(['No'])
            return
        if tts_type == tts.MINIMAXI_TTS:
            winobj.hecheng_role.addItems(list(show_rolelist[vt].keys()))
            return
        if len(show_rolelist[vt]) < 1:
            winobj.hecheng_language.setCurrentText('-')
            tools.show_error(tr('waitrole'))
            return
        if isinstance(show_rolelist[vt],list):
            role_list=show_rolelist[vt]
        else:
            role_list=list(show_rolelist[vt].keys())
        if 'clone' in role_list:
            role_list.remove('clone')
        winobj.hecheng_role.addItems(role_list)


    def hecheng_import_fun():
        fname, _ = QFileDialog.getOpenFileName(winobj, "SRT", params.get('last_opendir', '.'),
                                               "SRT files (*.srt)")
        if not fname:
            return

        fname = fname.replace('\\', '/')
        params['last_opendir'] = os.path.dirname(fname)
        params.save()

        winobj.parse_and_display_srt(fname)

    def opendir_fn():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    def show_detail_error():
        if winobj.error_msg:
            tools.show_error(winobj.error_msg)
    def check_voice_autorate(state):
        winobj.remove_silent_mid.setVisible(not state)
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
    
    from videotrans.component.set_form import Peiyinformrole


    winobj = Peiyinformrole()
    app_cfg.child_forms['fn_peiyinrole'] = winobj
    winobj.show()
    def _bind():
        Path(RESULT_DIR).mkdir(parents=True,exist_ok=True)
        winobj.voice_autorate.setChecked(params.get('dubb_voice_autorate', False))
        winobj.save_to_srt.setChecked(params.get('dubb_save_to_srt', False))
        winobj.hecheng_rate.setValue(params.get('dubb_hecheng_rate', 0))
        winobj.pitch_rate.setValue(params.get('dubb_pitch_rate', 0))
        winobj.volume_rate.setValue(params.get('dubb_volume_rate', 0))
        winobj.is_cuda.setChecked(params.get('dubb_is_cuda', False))
        winobj.is_cuda.toggled.connect(check_cuda)
        
        if not params.get('dubb_voice_autorate', False):
            winobj.remove_silent_mid.setVisible(True)
            winobj.remove_silent_mid.setChecked(params.get('dubb_remove_silent_mid', False))

        winobj.hecheng_importbtn.clicked.connect(hecheng_import_fun)
        winobj.hecheng_startbtn.clicked.connect(hecheng_start_fun)
        winobj.hecheng_stop.clicked.connect(stop_tts)
        winobj.listen_btn.clicked.connect(listen_voice_fun)
        winobj.hecheng_opendir.clicked.connect(opendir_fn)
        winobj.loglabel.clicked.connect(show_detail_error)

        winobj.hecheng_language.currentTextChanged.connect(hecheng_language_fun)
        winobj.tts_type.currentIndexChanged.connect(tts_type_change)

        last_tts_type = params.get("dubb_tts_type", 0)
        winobj.tts_type.setCurrentIndex(last_tts_type)
        tts_type_change(last_tts_type)
        
        winobj.voice_autorate.toggled.connect(check_voice_autorate)
        winobj.hecheng_language.setCurrentIndex(params.get("dubb_source_language", 0))
        winobj.hecheng_role.setCurrentIndex(params.get("dubb_role", 0))
        winobj.out_format.setCurrentIndex(params.get("dubb_out_format", 0))

    QTimer.singleShot(10,_bind)