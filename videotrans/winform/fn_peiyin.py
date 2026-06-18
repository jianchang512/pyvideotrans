# 合成配音


def openwin():

    from videotrans.util.help_misc import show_error
    from videotrans.util.help_role import role_menu
    from typing import List
    from videotrans.task.taskcfg import InputFile
    from datetime import datetime
    from videotrans.configure.contants import LISTEN_TEXT
    import re
    import json
    from pathlib import Path
    from PySide6.QtCore import QUrl, Qt
    from PySide6.QtGui import QDesktopServices
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr, app_cfg, params, defaulelang,   HOME_DIR
    from videotrans.configure import config
    from videotrans.task.taskcfg import TaskCfgTTS
    from videotrans import translator, tts
    from videotrans.component.set_form import Peiyinform


    langname_dict = {
        "zh-cn": "简体中文",
        "zh-tw": "繁体中文",
        "yue": "粤语",
        "en": "英语",
        "fr": "法语",
        "de": "德语",
        "ja": "日语",
        "ko": "韩语",
        "ru": "俄语",
        "es": "西班牙语",
        "th": "泰国语",
        "it": "意大利语",
        "pt": "葡萄牙语",
        "vi": "越南语",
        "ar": "阿拉伯语",
        "tr": "土耳其语",
        "hi": "印度语",
        "hu": "匈牙利语",
        "uk": "乌克兰语",
        "id": "印度尼西亚",
        "ms": "马来语",
        "kk": "哈萨克语",
        "cs": "捷克语",
        "pl": "波兰语",
        "nl": "荷兰语",
        "sv": "瑞典语",
        "he": "希伯来语",
        "bn": "孟加拉语",
        "fil": "菲律宾语",

        "af": "南非荷兰语",
        "sq": "阿尔巴尼亚语",
        "am": "阿姆哈拉语",
        "az": "阿塞拜疆语",
        "bs": "波斯尼亚语",
        "bg": "保加利亚语",
        "my": "缅甸语",
        "ca": "加泰罗尼亚语",
        "hr": "克罗地亚语",
        "da": "丹麦语",
        "et": "爱沙尼亚语",
        "fi": "芬兰语",
        "gl": "加利西亚语",
        "ka": "格鲁吉亚语",
        "el": "希腊语",
        "gu": "古吉拉特语",
        "is": "冰岛语",
        "iu": "因纽特语",
        "ga": "爱尔兰语",
        "jv": "爪哇语",
        "kn": "卡纳达语",
        "km": "高棉语",
        "lo": "老挝语",
        "lv": "拉脱维亚语",
        "lt": "立陶宛语",
        "mk": "马其顿语",
        "ml": "马拉雅拉姆语",
        "mt": "马耳他语",
        "mr": "马拉地语",
        "mn": "蒙古语",
        "ne": "尼泊尔语",
        "nb": "挪威语(书面挪威语)",
        "ps": "普什图语",
        "fa": "波斯语",

        "ro": "罗马尼亚语",
        "sr": "塞尔维亚语",
        "si": "僧伽罗语",
        "sk": "斯洛伐克语",
        "sl": "斯洛文尼亚语",
        "so": "索马里语",
        "su": "巽他语",
        "sw": "斯瓦希里语",
        "ta": "泰米尔语",
        "te": "泰卢固语",
        "ur": "乌尔都语",
        "uz": "乌兹别克语",
        "cy": "威尔士语",
        "zu": "祖鲁语"
    }
    if defaulelang != 'zh':
        langname_dict = {
            "zh-cn": "Simplified Chinese",
            "zh-tw": "Traditional Chinese",
            "yue": "Cantonese",
            "en": "English",
            "fr": "French",
            "de": "German",
            "ja": "Japanese",
            "ko": "Korean",
            "ru": "Russian",
            "es": "Spanish",
            "th": "Thai",
            "it": "Italian",
            "pt": "Portuguese",
            "vi": "Vietnamese",
            "ar": "Arabic",
            "tr": "Turkish",
            "hi": "Hindi",
            "hu": "Hungarian",
            "uk": "Ukrainian",
            "id": "Indonesian",
            "ms": "Malay",
            "kk": "Kazakh",
            "cs": "Czech",
            "pl": "Polish",
            "nl": "Dutch",
            "sv": "Swedish",
            "he": "Hebrew",
            "bn": "Bengali",
            "fil": "Filipino",

            "af": "Afrikaans",
            "sq": "Albanian",
            "am": "Amharic",
            "az": "Azerbaijani",
            "bs": "Bosnian",
            "bg": "Bulgarian",
            "my": "Burmese",
            "ca": "Catalan",
            "hr": "Croatian",
            "da": "Danish",
            "et": "Estonian",
            "fi": "Finnish",
            "gl": "Galician",
            "ka": "Georgian",
            "el": "Greek",
            "gu": "Gujarati",
            "is": "Icelandic",
            "iu": "Inuktitut",
            "ga": "Irish",
            "jv": "Javanese",
            "kn": "Kannada",
            "km": "Khmer",
            "lo": "Lao",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "mk": "Macedonian",
            "ml": "Malayalam",
            "mt": "Maltese",
            "mr": "Marathi",
            "mn": "Mongolian",
            "ne": "Nepali",
            "nb": "Norwegian Bokmål",
            "ps": "Pashto",
            "fa": "Persian",

            "ro": "Romanian",
            "sr": "Serbian",
            "si": "Sinhala",
            "sk": "Slovak",
            "sl": "Slovenian",
            "so": "Somali",
            "su": "Sundanese",
            "sw": "Swahili",
            "ta": "Tamil",
            "te": "Telugu",
            "ur": "Urdu",
            "uz": "Uzbek",
            "cy": "Welsh",
            "zu": "Zulu"
        }
    RESULT_DIR = HOME_DIR + "/tts"
    Path(RESULT_DIR).mkdir(parents=True, exist_ok=True)
    uuid_list = list()
    percent = ""


    def toggle_state(state):
        winobj.hecheng_plaintext.setDisabled(state)
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
        winobj.hecheng_stop.setDisabled(not state)

    def feed(d):
        nonlocal percent
        if winobj.has_done:
            return
        if isinstance(d, str):
            d = json.loads(d)
        if d['type'] != 'error':
            winobj.loglabel.setStyleSheet("""color:#148cd2;background-color:transparent""")
            winobj.error_msg = ""
            winobj.loglabel.setToolTip('')

        if d['type'] == 'error':
            winobj.error_msg = d['text']
            winobj.loglabel.setToolTip(tr("View  details error"))
            winobj.has_done = True
            winobj.hecheng_startbtn.setText(tr("zhixingwc"))
            toggle_state(False)
            winobj.loglabel.setText(d['text'][:150])
            winobj.loglabel.setStyleSheet("""color:#ff0000;background-color:transparent""")
            winobj.loglabel.setCursor(Qt.PointingHandCursor)
            if len(winobj.hecheng_importbtn.filelist) > 0:
                winobj.hecheng_plaintext.clear()
        elif d['type'] in ['logs']:
            winobj.loglabel.setText(f"{percent} {d['text']}")
        elif d['type'] == 'jindu':
            percent = d['text']
        elif d['type'] == 'end':
            percent = ''
            winobj.has_done = True
            winobj.hecheng_importbtn.filelist = []
            winobj.hecheng_importbtn.setText(tr('Import text to be translated from a file..'))
            winobj.loglabel.setText(tr('quanbuend'))
            winobj.hecheng_startbtn.setText(tr("zhixingwc"))
            toggle_state(False)
            winobj.hecheng_plaintext.clear()
            winobj.hecheng_importbtn.filelist = []

    # 试听配音
    def listen_voice_fun():
        lang = translator.get_code(show_text=winobj.hecheng_language.currentText())
        if not lang or lang == '-':
            return show_error(tr("The voice is not support listen"))
        text = LISTEN_TEXT.get(f'{lang}')
        if not text:
            return show_error(tr('The current language does not support audition'))
        role = winobj.hecheng_role.currentText()
        if not role or role == 'No':
            return show_error(tr('mustberole'))
        voice_dir = config.TEMP_DIR + '/listen_voice'
        Path(voice_dir).mkdir(parents=True, exist_ok=True)
        lujing_role = role.replace('/', '-')
        tts_type = winobj.tts_type.currentIndex()

        rate = int(winobj.hecheng_rate.value())
        rate = f"+{rate}%" if rate >= 0 else f"{rate}%"
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
        raw_text = winobj.listen_btn.text()

        def feed(d):
            winobj.listen_btn.setDisabled(False)
            winobj.listen_btn.setText(raw_text)
            if d != "ok":
                show_error(d)

        winobj.listen_btn.setDisabled(True)
        winobj.listen_btn.setText('load...')

        from videotrans.util.ListenVoice import ListenVoice
        wk = ListenVoice(parent=winobj, queue_tts=[obj], language=lang, tts_type=tts_type)
        wk.uito.connect(feed)
        wk.start()

    # tab-4 语音合成
    def hecheng_start_fun():
        nonlocal RESULT_DIR, uuid_list

        Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        winobj.has_done = False
        txt = winobj.hecheng_plaintext.toPlainText().strip()
        language = winobj.hecheng_language.currentText()
        role = winobj.hecheng_role.currentText()
        rate = int(winobj.hecheng_rate.value())
        tts_type = winobj.tts_type.currentIndex()

        if language == '-' or role in ['No', '-', '']:
            return show_error(tr('yuyanjuesebixuan'))

        if tts.is_input_api(tts_type=tts_type) is not True:
            return False

        # 语言是否支持
        if tts_type not in  [tts.EDGE_TTS,tts.OMNIVOICE_TTS,tts.G_TTS]:
            langcode = translator.get_code(show_text=language)
            is_allow_lang_res = tts.is_allow_lang(langcode=langcode, tts_type=tts_type)
            if is_allow_lang_res is not True:
                winobj.loglabel.setText(is_allow_lang_res)
            else:
                winobj.loglabel.setText('')
        else:
            code_list = [key for key, value in langname_dict.items() if value == language]
            if not code_list:
                return show_error(f'{language} is not support -1')
            langcode = code_list[0]


        rate = f"+{rate}%" if rate >= 0 else f"{rate}%"
        volume = int(winobj.volume_rate.value())
        pitch = int(winobj.pitch_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{pitch}Hz'

        if len(winobj.hecheng_importbtn.filelist) < 1 and not txt:
            return show_error(
                tr("Must import srt file or fill in text box with text"))
        toggle_state(True)
        if len(winobj.hecheng_importbtn.filelist) > 0 and winobj.save_to_srt.isChecked():
            RESULT_DIR = Path(winobj.hecheng_importbtn.filelist[0]).parent.as_posix()
        else:
            RESULT_DIR = HOME_DIR + "/tts"

        if txt:
            newsrtfile = config.TEMP_DIR + f"/{datetime.now().strftime('%Y%m%d-%H%M%S')}."
            is_srt = re.match(
                r'^1\s*[\r\n]+\s*\d{1,2}:\d{1,2}:\d{1,2}(,\d{1,3})?\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2}(,\d{1,3})?', txt)
            if not is_srt:
                newsrtfile += 'txt'
                Path(newsrtfile).write_text(txt, encoding='utf-8')
            else:
                newsrtfile += 'srt'
                with open(newsrtfile, "w", encoding="utf-8") as f:
                    f.write(txt)
            winobj.hecheng_importbtn.filelist.append(newsrtfile)
        from videotrans.util.help_ffmpeg import format_video
        video_list:List[InputFile] = [format_video(it, None) for it in winobj.hecheng_importbtn.filelist]
        uuid_list = [obj['uuid'] for obj in video_list]
        for it in video_list:
            app_cfg.rm_uuid(it['uuid'])
            it['target_dir']=RESULT_DIR
            cfg = {
                "voice_role": role,
                "cache_folder": config.TEMP_DIR + f'/{it["uuid"]}',
                "target_language_code": langcode,
                "voice_rate": rate,
                "volume": volume,
                "uuid": it['uuid'],
                "pitch": pitch,
                "tts_type": tts_type,
                "voice_autorate": winobj.voice_autorate.isChecked(),
                "remove_silent_mid": winobj.remove_silent_mid.isChecked(),
                "align_sub_audio": False,
                "is_cuda": winobj.is_cuda.isChecked()
            }
            from videotrans.task.dubbing import DubbingSrt
            trk = DubbingSrt(cfg=TaskCfgTTS(**cfg | it), out_ext=winobj.out_format.currentText())
            app_cfg.dubb_queue.put_nowait(trk)
            winobj.hecheng_plaintext.clear()
            winobj.hecheng_plaintext.insertPlainText(Path(it['name']).read_text(encoding='utf-8-sig',errors="ingore"))
        from videotrans.task.child_win_sign import SignThread
        th = SignThread(uuid_list=uuid_list, parent=winobj)
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
            params['dubb_remove_silent_mid'] = winobj.remove_silent_mid.isChecked()
        params.save()

    def stop_tts():
        nonlocal uuid_list
        winobj.has_done = True
        winobj.hecheng_importbtn.filelist = []
        winobj.hecheng_importbtn.setText(tr('Import text to be translated from a file..'))
        winobj.loglabel.setText('Stoped')
        winobj.hecheng_startbtn.setText(tr("zhixingwc"))
        toggle_state(False)
        if uuid_list:
            for uuid in uuid_list:
                app_cfg.stoped_uuid_set.add(uuid)
        uuid_list = list()

    def getlangnamelist(tts_type=0):
        if tts_type not in [tts.EDGE_TTS,tts.OMNIVOICE_TTS,tts.G_TTS]:
            return ['-'] + list(translator.LANGNAME_DICT.values())

        return ['-'] + list(langname_dict.values())

    # tts类型改变
    def tts_type_change(type):
        winobj.is_cuda.setVisible(type  in [tts.QWEN3LOCAL_TTS,tts.CHATTERBOX_TTS])
        current_text = winobj.hecheng_language.currentText()

        winobj.hecheng_language.clear()
        langnamelist = getlangnamelist(type)

        winobj.hecheng_language.addItems(langnamelist)
        code = translator.get_code(show_text=current_text)
        if current_text in langnamelist:
            winobj.hecheng_language.setCurrentText(current_text)

        if type != tts.EDGE_TTS:
            is_allow_lang_res = tts.is_allow_lang(langcode=code, tts_type=type)
            if is_allow_lang_res is not True:
                winobj.loglabel.setText(is_allow_lang_res)
            else:
                winobj.loglabel.setText('')
            if tts.is_input_api(tts_type=type) is not True:
                return False
        role_list = role_menu(type, code)
        winobj.hecheng_role.clear()
        if "clone" in role_list:
            role_list.remove('clone')
        winobj.hecheng_role.addItems(role_list)

    # 合成语言变化，需要获取到角色
    def hecheng_language_fun(t):
        tts_type = winobj.tts_type.currentIndex()
        if tts_type in [tts.EDGE_TTS,tts.OMNIVOICE_TTS,tts.G_TTS]:
            code_list = [key for key, value in langname_dict.items() if value == t]
            if not code_list:
                code = None
            else:
                code = code_list[0]
        else:
            code = translator.get_code(show_text=t)
            if code and code != '-':
                is_allow_lang_reg = tts.is_allow_lang(langcode=code, tts_type=tts_type)
                if is_allow_lang_reg is not True:
                    winobj.loglabel.setText(is_allow_lang_reg)
                else:
                    winobj.loglabel.setText('')

        # 不是跟随语言变化的配音渠道，无需继续处理
        if tts_type not in tts.CHANGE_BY_LANGUAGE:
            return
        winobj.hecheng_role.clear()
        if t == '-' or not code:
            winobj.hecheng_role.addItems(['No'])
            return
        role_list = role_menu(tts_type, code)
        if 'clone' in role_list:
            role_list.remove('clone')
        winobj.hecheng_role.addItems(role_list)

    def opendir_fn():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    def show_detail_error():
        if winobj.error_msg:
            show_error(winobj.error_msg)

    def check_voice_autorate(state):
        winobj.remove_silent_mid.setVisible(not state)

    def check_cuda(state):
        # 选中如果无效，则取消
        if state:
            import torch
            if not torch.cuda.is_available():
                show_error(tr('nocuda'))
                winobj.is_cuda.setChecked(False)
                winobj.is_cuda.setDisabled(True)
                return False
        return True


    winobj = Peiyinform()
    app_cfg.child_forms['fn_peiyin'] = winobj

    def _bind():
        from videotrans.component.component import PeiyinDropButton
        winobj.hecheng_importbtn = PeiyinDropButton(tr('Import text to be translated from a file..'))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(winobj.hecheng_importbtn.sizePolicy().hasHeightForWidth())
        winobj.hecheng_importbtn.setSizePolicy(sizePolicy)
        winobj.hecheng_importbtn.setMinimumSize(0, 150)
        winobj.hecheng_layout.insertWidget(0, winobj.hecheng_importbtn)


        if not params.get('dubb_voice_autorate', False):
            winobj.remove_silent_mid.setVisible(True)
            winobj.remove_silent_mid.setChecked(bool(params.get('dubb_remove_silent_mid', False)))

        winobj.voice_autorate.setChecked(bool(params.get('dubb_voice_autorate', False)))
        winobj.save_to_srt.setChecked(bool(params.get('dubb_save_to_srt', False)))
        winobj.is_cuda.setChecked(bool(params.get('dubb_is_cuda', False)))
        winobj.hecheng_rate.setValue(int(params.get('dubb_hecheng_rate', 0)))
        winobj.pitch_rate.setValue(int(params.get('dubb_pitch_rate', 0)))
        winobj.volume_rate.setValue(int(params.get('dubb_volume_rate', 0)))

        last_tts_type = int(params.get("dubb_tts_type", 0))
        winobj.hecheng_language.addItems(getlangnamelist(last_tts_type))
        winobj.hecheng_language.setCurrentIndex(int(params.get("dubb_source_language", 0)))
        winobj.tts_type.setCurrentIndex(last_tts_type)

        winobj.out_format.setCurrentIndex(int(params.get("dubb_out_format", 0)))

        winobj.hecheng_startbtn.clicked.connect(hecheng_start_fun)
        winobj.hecheng_stop.clicked.connect(stop_tts)
        winobj.listen_btn.clicked.connect(listen_voice_fun)
        winobj.hecheng_opendir.clicked.connect(opendir_fn)
        winobj.hecheng_language.currentTextChanged.connect(hecheng_language_fun)
        winobj.tts_type.currentIndexChanged.connect(tts_type_change)
        winobj.voice_autorate.toggled.connect(check_voice_autorate)
        winobj.loglabel.clicked.connect(show_detail_error)
        winobj.is_cuda.toggled.connect(check_cuda)
        tts_type_change(last_tts_type)
        winobj.hecheng_role.setCurrentIndex(int(params.get("dubb_role", 0)))
    _bind()
    return winobj
