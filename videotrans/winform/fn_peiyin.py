import copy,re
import json
import json
import os
import shutil
import threading
import time
from pathlib import Path

from PySide6.QtCore import QUrl, QThread, Signal,Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans import translator, tts
from videotrans.configure import config
from videotrans.task._dubbing import DubbingSrt
from videotrans.tts import EDGE_TTS, AZURE_TTS, AI302_TTS, OPENAI_TTS, GPTSOVITS_TTS, COSYVOICE_TTS, FISHTTS, F5_TTS, CHATTTS, GOOGLE_TTS, ELEVENLABS_TTS, CLONE_VOICE_TTS, TTS_API, is_input_api, is_allow_lang, VOLCENGINE_TTS,KOKORO_TTS
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

langname_dict={
    "zh-cn": "中文简",
    "zh-tw": "中文繁",
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
	"bn":"孟加拉语",
	"fil":"菲律宾语",
    
    
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
if config.defaulelang !='zh':
    langname_dict={
    
    
    "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
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
	"bn":"Bengali",
	"fil":"Filipino",



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

# 合成配音
def openwin():
    RESULT_DIR = config.HOME_DIR + "/tts"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    def feed(d):
        if winobj.has_done or config.box_tts!='ing':
            return
        if isinstance(d, str):
            d = json.loads(d)
        if d['type']!='error':
            winobj.loglabel.setStyleSheet("""color:#148cd2;background-color:transparent""")
            winobj.error_msg = ""
            winobj.loglabel.setToolTip('')
        if d['type'] == 'replace':
            winobj.hecheng_plaintext.clear()
            winobj.hecheng_plaintext.insertPlainText(d['text'])
        elif d['type'] == 'error':
            winobj.error_msg = d['text']
            winobj.loglabel.setToolTip('点击查看详细出错信息' if config.defaulelang=='zh' else 'View  details error')
            winobj.has_done = True
            winobj.hecheng_startbtn.setText(config.transobj["zhixingwc"])
            winobj.hecheng_startbtn.setDisabled(False)
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
            winobj.hecheng_files = []
            winobj.hecheng_importbtn.setText(config.box_lang['Import text to be translated from a file..'])
            winobj.loglabel.setText(config.transobj['quanbuend'])
            winobj.hecheng_startbtn.setText(config.transobj["zhixingwc"])
            winobj.hecheng_startbtn.setDisabled(False)
            winobj.hecheng_stop.setDisabled(True)
            winobj.hecheng_plaintext.clear()

    # 试听配音
    def listen_voice_fun():
        lang = translator.get_code(show_text=winobj.hecheng_language.currentText())
        if not lang or lang == '-':
            return QMessageBox.critical(winobj, config.transobj['anerror'],
                                        f"该角色不支持试听" if config.defaulelang == 'zh' else 'The voice is not support listen')
        text = config.params[f'listen_text_{lang}']
        role = winobj.hecheng_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(winobj, config.transobj['anerror'], config.transobj['mustberole'])
        voice_dir = config.TEMP_DIR+'/listen_voice'
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
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{volume}Hz'

        voice_file = f"{voice_dir}/{tts_type}-{lang}-{lujing_role}-{volume}-{pitch}.mp3"

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
        threading.Thread(target=tts.run, kwargs={'language':lang,"queue_tts": [obj], "play": True, "is_test": True}).start()

    def change_by_lang(type):
        if type in [EDGE_TTS, AZURE_TTS,VOLCENGINE_TTS,AI302_TTS,KOKORO_TTS]:
            return True
        return False

    # tab-4 语音合成
    def hecheng_start_fun():
        nonlocal RESULT_DIR
        Path(config.TEMP_HOME).mkdir(parents=True, exist_ok=True)
        winobj.has_done = False
        txt = winobj.hecheng_plaintext.toPlainText().strip()
        language = winobj.hecheng_language.currentText()
        role = winobj.hecheng_role.currentText()
        rate = int(winobj.hecheng_rate.value())
        tts_type = winobj.tts_type.currentIndex()

        if language == '-' or role in ['No','-','']:
            return QMessageBox.critical(winobj, config.transobj['anerror'],config.transobj['yuyanjuesebixuan'])
                                        
        if is_input_api(tts_type=tts_type) is not True:
            return False

        # 语言是否支持
        if tts_type != EDGE_TTS:
            langcode = translator.get_code(show_text=language)
            is_allow_lang_res = is_allow_lang(langcode=langcode, tts_type=tts_type)
            if is_allow_lang_res is not True:
                return QMessageBox.critical(winobj, config.transobj['anerror'], is_allow_lang_res)
        else:
            code_list=[key for key, value in langname_dict.items() if value == language]
            if not code_list:
                return QMessageBox.critical(winobj, config.transobj['anerror'], f'{language} is not support -1')
            langcode=code_list[0]
        print(f'{langcode=}')
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        volume = int(winobj.volume_rate.value())
        pitch = int(winobj.pitch_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{volume}Hz'

        if len(winobj.hecheng_files) < 1 and not txt:
            return QMessageBox.critical(winobj, config.transobj['anerror'],
                                        '必须导入srt文件或在文本框中填写文字' if config.defaulelang == 'zh' else 'Must import srt file or fill in text box with text')
        if len(winobj.hecheng_files)>0 and winobj.save_to_srt.isChecked():
            RESULT_DIR=Path(winobj.hecheng_files[0]).parent.as_posix()
        if txt:
            newsrtfile = config.TEMP_HOME + f"/peiyin{time.time()}."
            if tts_type==tts.EDGE_TTS and not re.match(r'^1\s*[\r\n]+\s*\d{1,2}:\d{1,2}:\d{1,2}(\,\d{1,3})?\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2}(\,\d{1,3})?',txt.strip()):
                newsrtfile+='txt'
                Path(newsrtfile).write_text(txt.strip(),encoding='utf-8')
            else:
                newsrtfile+='srt'
                tools.save_srt(tools.get_subtitle_from_srt(tools.process_text_to_srt_str(txt), is_file=False), newsrtfile)
            winobj.hecheng_files.append(newsrtfile)

        config.box_tts = 'ing'
        video_list = [tools.format_video(it, None) for it in winobj.hecheng_files]
        uuid_list = [obj['uuid'] for obj in video_list]
        for it in video_list:
            trk = DubbingSrt({
                "voice_role": role,
                "cache_folder": config.TEMP_HOME + f'/{it["uuid"]}',
                "target_language_code": langcode,
                "target_dir": RESULT_DIR,
                "voice_rate": rate,
                "volume": volume,
                "inst": None,
                "rename":True,
                "uuid": it['uuid'],
                "pitch": pitch,
                "tts_type": tts_type,
                "out_ext": winobj.out_format.currentText(),
                "voice_autorate": winobj.voice_autorate.isChecked()
            }, it)
            config.dubb_queue.append(trk)

        th = SignThread(uuid_list=uuid_list, parent=winobj)
        th.uito.connect(feed)
        th.start()
        winobj.hecheng_startbtn.setText(config.transobj["running"])
        winobj.hecheng_startbtn.setDisabled(True)
        winobj.hecheng_stop.setDisabled(False)
        config.params["dubb_source_language"]=winobj.hecheng_language.currentIndex()
        config.params["dubb_tts_type"]=winobj.tts_type.currentIndex()
        config.params["dubb_role"]=winobj.hecheng_role.currentIndex()
        config.params["dubb_out_format"]=winobj.out_format.currentIndex()
        config.params["dubb_voice_autorate"]=winobj.voice_autorate.isChecked()
        config.params["dubb_save_to_srt"]=winobj.save_to_srt.isChecked()
        config.params["dubb_hecheng_rate"]=int(winobj.hecheng_rate.value())
        config.params["dubb_pitch_rate"]=int(winobj.pitch_rate.value())
        config.params["dubb_volume_rate"]=int(winobj.volume_rate.value())
        config.getset_params(config.params)

    def stop_tts():
        config.box_tts = 'stop'
        winobj.has_done = True
        winobj.hecheng_files = []
        winobj.hecheng_importbtn.setText(config.box_lang['Import text to be translated from a file..'])
        winobj.loglabel.setText('Stoped')
        winobj.hecheng_startbtn.setText(config.transobj["zhixingwc"])
        winobj.hecheng_startbtn.setDisabled(False)
        winobj.hecheng_stop.setDisabled(True)

    
    def getlangnamelist(tts_type=0):
        if tts_type !=EDGE_TTS:
            return ['-'] + config.langnamelist
        
        return ['-']+list(langname_dict.values())
    

    # tts类型改变
    def tts_type_change(type):
        if change_by_lang(type):
            winobj.volume_rate.setDisabled(False)
            winobj.pitch_rate.setDisabled(False)
        else:
            winobj.volume_rate.setDisabled(True)
            winobj.pitch_rate.setDisabled(True)
        
        current_text=winobj.hecheng_language.currentText()
        
        winobj.hecheng_language.clear()
        langnamelist=getlangnamelist(type)
        print(f'{langnamelist=}')
        winobj.hecheng_language.addItems(langnamelist)
        if current_text in langnamelist:
            winobj.hecheng_language.setCurrentText(current_text)

        if type != EDGE_TTS:
            code = translator.get_code(show_text=current_text)
            is_allow_lang_res = is_allow_lang(langcode=code, tts_type=type)
            if is_allow_lang_res is not True:
                winobj.tts_type.setCurrentIndex(0)
                return QMessageBox.critical(winobj, config.transobj['anerror'], is_allow_lang_res)
            if is_input_api(tts_type=type) is not True:
                winobj.tts_type.setCurrentIndex(0)
                return False
        

        if type == GOOGLE_TTS:
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems(['gtts'])
        elif type == CHATTTS:
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems(list(config.ChatTTS_voicelist))
        elif type == OPENAI_TTS:
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems(config.params['openaitts_role'].split(","))
        elif type == ELEVENLABS_TTS:
            winobj.hecheng_role.clear()
            rolelist=copy.deepcopy(config.params['elevenlabstts_role'])
            if "clone" in rolelist:
                rolelist.remove("clone")
            winobj.hecheng_role.addItems(rolelist)
        elif change_by_lang(type):
            hecheng_language_fun(winobj.hecheng_language.currentText())
        elif type == CLONE_VOICE_TTS:
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems([it for it in config.params["clone_voicelist"] if it != 'clone'])
        elif type == TTS_API:
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems(config.params['ttsapi_voice_role'].split(","))
        elif type == GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
        elif type == COSYVOICE_TTS:
            rolelist = tools.get_cosyvoice_role()
            del rolelist["clone"]
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['-'])
        elif type == FISHTTS:
            rolelist = tools.get_fishtts_role()
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['FishTTS'])
        elif type == F5_TTS:
            rolelist = tools.get_f5tts_role()
            winobj.hecheng_role.clear()
            winobj.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['-'])

    # 合成语言变化，需要获取到角色
    def hecheng_language_fun(t):
        tts_type = winobj.tts_type.currentIndex()
        if tts_type==EDGE_TTS:
            code_list=[key for key, value in langname_dict.items() if value == t]
            if not code_list:
                code='-'
            else:
                code=code_list[0]
        else:
            code = translator.get_code(show_text=t)
            if code and code != '-':
                is_allow_lang_reg = is_allow_lang(langcode=code, tts_type=tts_type)
                if is_allow_lang_reg is not True:
                    return QMessageBox.critical(winobj, config.transobj['anerror'], is_allow_lang_reg)
            print(f'==={code=}')
        # 不是跟随语言变化的配音渠道，无需继续处理
        if not change_by_lang(tts_type):
            return
        winobj.hecheng_role.clear()
        if t == '-':
            winobj.hecheng_role.addItems(['No'])
            return

        if tts_type == EDGE_TTS:
            show_rolelist = tools.get_edge_rolelist()
        elif tts_type == KOKORO_TTS:
            show_rolelist = tools.get_kokoro_rolelist()
        elif tts_type == AI302_TTS:
            show_rolelist = tools.get_302ai()
        elif tts_type==VOLCENGINE_TTS:
            show_rolelist = tools.get_volcenginetts_rolelist()
        else:
            # AzureTTS
            show_rolelist = tools.get_azure_rolelist()
        if not show_rolelist:
            winobj.hecheng_language.setCurrentText('-')
            QMessageBox.critical(winobj, config.transobj['anerror'], config.transobj['nojueselist'])
            return
        try:
            vt = code.split('-')[0]
            if vt not in show_rolelist:
                winobj.hecheng_role.addItems(['No'])
                return
            if len(show_rolelist[vt]) < 2:
                winobj.hecheng_language.setCurrentText('-')
                QMessageBox.critical(winobj, config.transobj['anerror'], config.transobj['waitrole'])
                return
            winobj.hecheng_role.addItems(show_rolelist[vt])
        except:
            winobj.hecheng_role.addItems(['No'])

    # 导入字幕
    def hecheng_import_fun():
        fnames, _ = QFileDialog.getOpenFileNames(winobj, "Select srt", config.params['last_opendir'],
                                                 "Text files(*.srt *.txt)")
        if len(fnames) < 1:
            return
        namestr = []
        for (i, it) in enumerate(fnames):
            it = it.replace('\\', '/').replace('file:///', '')
            fnames[i] = it
            namestr.append(os.path.basename(it))

        if len(fnames) > 0:
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            winobj.hecheng_files = fnames
            file_str= f'导入{len(fnames)}个srt文件 \n' if config.defaulelang == 'zh' else f'Import {len(fnames)} Subtitles \n'
            file_str+=("\n".join(namestr))
            winobj.hecheng_importbtn.setText(file_str)

    def opendir_fn():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    def show_detail_error():
        if winobj.error_msg:
            QMessageBox.critical(winobj,config.transobj['anerror'],winobj.error_msg)

    from videotrans.component import Peiyinform
    try:
        winobj = config.child_forms.get('peiyinform')
        if winobj is not None:
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            return
        winobj = Peiyinform()
        config.child_forms['peiyinform'] = winobj

        winobj.voice_autorate.setChecked(config.params.get('dubb_voice_autorate',False))
        winobj.save_to_srt.setChecked(config.params.get('dubb_save_to_srt',False))
        winobj.hecheng_rate.setValue(config.params.get('dubb_hecheng_rate', 0))
        winobj.pitch_rate.setValue(config.params.get('dubb_pitch_rate', 0))
        winobj.volume_rate.setValue(config.params.get('dubb_volume_rate', 0))

        winobj.hecheng_importbtn.clicked.connect(hecheng_import_fun)
        winobj.hecheng_startbtn.clicked.connect(hecheng_start_fun)
        winobj.hecheng_stop.clicked.connect(stop_tts)
        winobj.listen_btn.clicked.connect(listen_voice_fun)
        winobj.hecheng_opendir.clicked.connect(opendir_fn)
        
        last_tts_type=config.params.get("dubb_tts_type",0)
        langnamelist=getlangnamelist(last_tts_type)
        winobj.hecheng_language.addItems(langnamelist)
        #if last_tts_type!=EDGE_TTS:        
        winobj.hecheng_language.currentTextChanged.connect(hecheng_language_fun)
        winobj.hecheng_language.setCurrentIndex(config.params.get("dubb_source_language",0))
        winobj.tts_type.currentIndexChanged.connect(tts_type_change)
        winobj.tts_type.setCurrentIndex(last_tts_type)
        #else:
            

        winobj.hecheng_role.setCurrentIndex(config.params.get("dubb_role",0))
        winobj.out_format.setCurrentIndex(config.params.get("dubb_out_format",0))

        winobj.loglabel.clicked.connect(show_detail_error)

        winobj.show()
    except Exception as e:
        import traceback
        traceback.print_exc()
