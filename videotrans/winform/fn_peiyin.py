import json
import os
import os
import re
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans import translator
from videotrans.task.workertts import WorkerTTS
from videotrans.configure import config
from videotrans.util import tools
import builtins
# 使用内置的 open 函数
builtin_open = builtins.open


# 合成配音
def open():
    def feed(d):
        d=json.loads(d)
        if d['type']=='replace':
            config.peiyinform.hecheng_plaintext.clear()
            config.peiyinform.hecheng_plaintext.insertPlainText(d['text'])
        elif d['type']=='error':
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'], d['text'])
        elif d['type']=='logs':
            config.peiyinform.loglabel.setText(d['text'])
        elif d['type']=='jd':
            config.peiyinform.hecheng_startbtn.setText(d['text'])
        else:
            config.peiyinform.hecheng_startbtn.setText(config.transobj["zhixingwc"])
            config.peiyinform.hecheng_startbtn.setDisabled(False)


    # 试听配音
    def listen_voice_fun():
        lang = translator.get_code(show_text=config.peiyinform.hecheng_language.currentText())
        if not lang or lang == '-':
            return QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                        "选择字幕语言" if config.defaulelang == 'zh' else 'Please target language')
        text = config.params[f'listen_text_{lang}']
        role = config.peiyinform.hecheng_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['mustberole'])
        voice_dir = os.environ.get('APPDATA') or os.environ.get('appdata')
        if not voice_dir or not Path(voice_dir).exists():
            voice_dir = config.rootdir + "/tmp/voice_tmp"
        else:
            voice_dir = voice_dir.replace('\\', '/') + "/pyvideotrans"
        if not Path(voice_dir).exists():
            Path(voice_dir).mkdir(parents=True, exist_ok=True)
        lujing_role = role.replace('/', '-')

        rate = int(config.peiyinform.hecheng_rate.value())
        tts_type = config.peiyinform.tts_type.currentText()

        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        volume = int(config.peiyinform.volume_rate.value())
        pitch = int(config.peiyinform.pitch_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{volume}Hz'

        voice_file = f"{voice_dir}/{tts_type}-{lang}-{lujing_role}-{volume}-{pitch}.mp3"
        if tts_type in ['GPT-SoVITS', 'ChatTTS', 'FishTTS', 'CosyVoice']:
            voice_file += '.wav'

        obj = {
            "text": text,
            "rate": '+0%',
            "role": role,
            "voice_file": voice_file,
            "tts_type": tts_type,
            "language": lang,
            "volume": volume,
            "pitch": pitch,
        }

        if role == 'clone':
            return

        def feed(d):
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'], d)

        from videotrans.task.play_audio import PlayMp3
        t = PlayMp3(obj, config.peiyinform)
        t.mp3_ui.connect(feed)
        t.start()

    def isMircosoft(type):
        if type in ['edgeTTS', 'AzureTTS']:
            return True
        if type == '302.ai' and config.params['ai302tts_model'] == 'azure':
            return True
        if type == '302.ai' and config.params['ai302tts_model'] == 'doubao':
            return True
        return False

    # tab-4 语音合成
    def hecheng_start_fun():
        config.settings = config.parse_init()
        txt = config.peiyinform.hecheng_plaintext.toPlainText().strip()
        language = config.peiyinform.hecheng_language.currentText()
        role = config.peiyinform.hecheng_role.currentText()
        rate = int(config.peiyinform.hecheng_rate.value())
        tts_type = config.peiyinform.tts_type.currentText()
        langcode = translator.get_code(show_text=language)


        if language == '-' or role == 'No':
            return QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                        config.transobj['yuyanjuesebixuan'])
        if tts_type == 'openaiTTS' and not config.params['chatgpt_key']:
            return QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                        config.transobj['bixutianxie'] + "chatGPT key")
        if tts_type == '302.ai' and not config.params['ai302tts_key']:
            return QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                        config.transobj['bixutianxie'] + " 302.ai 的 API KEY")
        if tts_type == '302.ai' and config.params['ai302tts_model'] == 'doubao' and langcode[:2] not in ['zh', 'ja','en']:
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'], '302.ai选择doubao模型时仅支持中英日文字配音')
            return
        if tts_type == "AzureTTS" and (
                not config.params['azure_speech_key'] or not config.params['azure_speech_region']):
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['azureinfo'])
        if tts_type == 'GPT-SoVITS' and langcode[:2] not in ['zh', 'ja', 'en']:
            # 除此指望不支持
            tts_type = 'edgeTTS'
            config.peiyinform.tts_type.setCurrentText('edgeTTS')
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['nogptsovitslanguage'])
            return
        if tts_type == 'CosyVoice' and langcode[:2] not in ['zh', 'ja', 'en', 'ko']:
            # 除此指望不支持
            tts_type = 'edgeTTS'
            config.peiyinform.tts_type.setCurrentText('edgeTTS')
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                 'CosyVoice仅支持中英日韩四种语言' if config.defaulelang == 'zh' else 'CosyVoice only supports Chinese, English, Japanese and Korean')
            return
        if tts_type == 'FishTTS' and langcode[:2] not in ['zh', 'ja', 'en']:
            # 除此指望不支持
            tts_type = 'edgeTTS'
            config.peiyinform.tts_type.setCurrentText('edgeTTS')
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'], 'FishTTS仅可用于中日英配音')
            return
        if tts_type == 'ChatTTS' and langcode[:2] not in ['zh', 'en']:
            # 除此指望不支持
            tts_type = 'edgeTTS'
            config.peiyinform.tts_type.setCurrentText('edgeTTS')
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['onlycnanden'])
            return

        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        volume = int(config.peiyinform.volume_rate.value())
        pitch = int(config.peiyinform.pitch_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{volume}Hz'

        # 文件名称
        filename = config.peiyinform.hecheng_out.text()
        if os.path.exists(filename):
            filename = ''
        if filename and re.search(r'[\\/]+', filename):
            filename = ""
        if not filename:
            newrole = role.replace('/', '-').replace('\\', '-')
            filename = f"{newrole}-rate{rate.replace('%', '')}-volume{volume.replace('%', '')}-pitch{pitch}"
        else:
            filename = filename.replace('.wav', '')

        if not os.path.exists(f"{config.homedir}/tts"):
            os.makedirs(f"{config.homedir}/tts", exist_ok=True)

        wavname = f"{config.homedir}/tts/{filename}"

        if len(config.peiyinform.hecheng_files)<1 and not txt:
            return QMessageBox.critical(config.peiyinform,config.transobj['anerror'],'必须导入srt文件或在文本框中填写文字' if config.defaulelang=='zh' else 'Must import srt file or fill in text box with text')
        elif len(config.peiyinform.hecheng_files)<1:
            newsrtfile=config.TEMP_HOME+f"/peiyin{time.time()}.srt"
            tools.save_srt(tools.get_subtitle_from_srt(txt,is_file=False),newsrtfile)
            config.peiyinform.hecheng_files.append(newsrtfile)



        hecheng_task = WorkerTTS(
            files=config.peiyinform.hecheng_files,
            role=role,
            rate=rate,
            pitch=pitch,
            volume=volume,
            langcode=langcode,
            wavname=wavname,
            tts_type=config.peiyinform.tts_type.currentText(),
            voice_autorate=config.peiyinform.voice_autorate.isChecked(),
            parent=config.peiyinform)
        hecheng_task.uito.connect(feed)
        hecheng_task.start()
        config.peiyinform.hecheng_startbtn.setText(config.transobj["running"])
        config.peiyinform.hecheng_startbtn.setDisabled(True)
        config.peiyinform.hecheng_out.setText(wavname)
        config.peiyinform.hecheng_out.setDisabled(True)

    # tts类型改变
    def tts_type_change(type):
        if isMircosoft(type):
            config.peiyinform.volume_rate.setDisabled(False)
            config.peiyinform.pitch_rate.setDisabled(False)
        else:
            config.peiyinform.volume_rate.setDisabled(True)
            config.peiyinform.pitch_rate.setDisabled(True)

        code = translator.get_code(show_text=config.peiyinform.hecheng_language.currentText())
        if type == 'gtts':
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(['gtts'])
        elif type == 'ChatTTS':
            if code and code != '-' and code[:2] not in ['zh', 'en']:
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['onlycnanden'])
                return
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(['No'] + list(config.ChatTTS_voicelist))
        elif type == "openaiTTS":
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(config.params['openaitts_role'].split(","))

        elif type == 'elevenlabsTTS':
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(config.params['elevenlabstts_role'])
        elif isMircosoft(type):
            if type == "AzureTTS" and (
                    not config.params['azure_speech_key'] or not config.params['azure_speech_region']):
                return QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['azureinfo'])
            if type == '302.ai' and not config.params['ai302tts_key']:
                return QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                            '请在菜单--设置--302.ai接入配音中填写 API KEY')
            if type == '302.ai' and code[:2] not in ['zh', 'ja', 'en']:
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'], '302.ai选择doubao模型时仅支持中英日文字配音')
                return
            hecheng_language_fun(config.peiyinform.hecheng_language.currentText())
        elif type == "302.ai":
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(config.params['ai302tts_role'].split(","))
        elif type == 'clone-voice':
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems([it for it in config.params["clone_voicelist"] if it != 'clone'])
        elif type == 'TTS-API':
            if not config.params['ttsapi_url']:
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['ttsapi_nourl'])
                return
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(config.params['ttsapi_voice_role'].split(","))
        elif type == 'GPT-SoVITS':
            if code and code != '-' and code[:2] not in ['zh', 'ja', 'en']:
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                     config.transobj['nogptsovitslanguage'])
                return
            rolelist = tools.get_gptsovits_role()
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
        elif type == 'CosyVoice':
            if code and code != '-' and code[:2] not in ['zh', 'ja', 'en', 'ko']:
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                     'CosyVoice仅支持中英日韩四种语言' if config.defaulelang == 'zh' else 'CosyVoice only supports Chinese, English, Japanese and Korean')
                return
            rolelist = tools.get_cosyvoice_role()
            del rolelist["clone"]
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['-'])
        elif type == 'FishTTS':
            if code and code != '-' and code[:2] not in ['zh', 'ja', 'en']:
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'], 'FishTTS仅可用于中日英配音')
                return
            rolelist = tools.get_fishtts_role()
            config.peiyinform.hecheng_role.clear()
            config.peiyinform.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['FishTTS'])

    # 合成语言变化，需要获取到角色
    def hecheng_language_fun(t):
        code = translator.get_code(show_text=t)
        tts_type = config.peiyinform.tts_type.currentText()
        if code and code != '-':
            if tts_type == 'GPT-SoVITS' and code[:2] not in ['zh', 'ja', 'en']:
                # 除此指望不支持
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                     config.transobj['nogptsovitslanguage'])
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                return
            if tts_type == 'CosyVoice' and code[:2] not in ['zh', 'ja', 'en', 'ko']:
                # 除此指望不支持
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'],
                                     'CosyVoice仅支持中英日韩四种语言' if config.defaulelang == 'zh' else 'CosyVoice only supports Chinese, English, Japanese and Korean')
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                return
            if tts_type == 'ChatTTS' and code[:2] not in ['zh', 'en']:
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                # 除此指望不支持
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['onlycnanden'])
                return
            if tts_type == 'FishTTS' and code[:2] not in ['zh', 'ja', 'en']:
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                # 除此指望不支持
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'], 'FishTTS仅可用于中日英配音')
                return
            if tts_type == '302.ai' and config.params['ai302tts_model'] == 'doubao' and code[:2] not in ['zh', 'ja',
                                                                                                         'en']:
                config.peiyinform.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'], '302.ai选择doubao模型时仅支持中英日文字配音')
                return

        if not isMircosoft(tts_type):
            return
        config.peiyinform.hecheng_role.clear()
        if t == '-':
            config.peiyinform.hecheng_role.addItems(['No'])
            return

        show_rolelist = None

        if tts_type == 'edgeTTS':
            show_rolelist = tools.get_edge_rolelist()
        elif tts_type == '302.ai' and config.params['ai302tts_model'] == 'doubao':
            show_rolelist = tools.get_302ai_doubao()
        else:
            # AzureTTS或 302.ai选择doubao模型
            show_rolelist = tools.get_azure_rolelist()

        if not show_rolelist:
            config.peiyinform.hecheng_language.setCurrentText('-')
            QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['nojueselist'])
            return

        try:
            vt = code.split('-')[0]
            if vt not in show_rolelist:
                config.peiyinform.hecheng_role.addItems(['No'])
                return
            if len(show_rolelist[vt]) < 2:
                config.peiyinform.hecheng_language.setCurrentText('-')
                QMessageBox.critical(config.peiyinform, config.transobj['anerror'], config.transobj['waitrole'])
                return
            config.peiyinform.hecheng_role.addItems(show_rolelist[vt])
        except:
            config.peiyinform.hecheng_role.addItems(['No'])

    # 导入字幕
    def hecheng_import_fun():
        fnames, _ = QFileDialog.getOpenFileNames(config.peiyinform, "Select srt", config.params['last_opendir'],
                                                 "Text files(*.srt *.txt)")
        if len(fnames) < 1:
            return
        namestr=[]
        for (i, it) in enumerate(fnames):
            it = it.replace('\\', '/').replace('file:///', '')
            if it.endswith('.txt'):
                shutil.copy2(it, f'{it}.srt')
                # 使用 "r+" 模式打开文件：读取和写入
                with builtin_open(f'{it}.srt', 'r+', encoding='utf-8') as file:
                    # 读取原始文件内容
                    original_content = file.readlines()
                    # 将文件指针移动到文件开始位置
                    file.seek(0)
                    # 将新行内容与原始内容合并，并写入文件
                    file.writelines(["1\n", "00:00:00,000 --> 05:00:00,000\n"] + original_content)

                it += '.srt'
            fnames[i] = it
            namestr.append(os.path.basename(it))


        if len(fnames) > 0:
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            config.peiyinform.hecheng_files = fnames
            config.peiyinform.hecheng_importbtn.setText(
                f'导入{len(fnames)}个srt文件 \n{",".join(namestr)}' if config.defaulelang == 'zh' else f'Import {len(fnames)} Subtitles \n{",".join(namestr)}')
        config.peiyinform.hecheng_out.setDisabled(False)
        config.peiyinform.hecheng_out.setText('')

    def opendir_fn(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(config.homedir + "/tts"))

    from videotrans.component import Peiyinform
    try:
        if config.peiyinform is not None:
            config.peiyinform.show()
            config.peiyinform.raise_()
            config.peiyinform.activateWindow()
            return
        config.peiyinform = Peiyinform()
        config.peiyinform.hecheng_importbtn.clicked.connect(hecheng_import_fun)
        config.peiyinform.hecheng_language.currentTextChanged.connect(hecheng_language_fun)
        config.peiyinform.hecheng_startbtn.clicked.connect(hecheng_start_fun)
        config.peiyinform.listen_btn.clicked.connect(listen_voice_fun)
        config.peiyinform.hecheng_opendir.clicked.connect(opendir_fn)
        config.peiyinform.tts_type.currentTextChanged.connect(tts_type_change)

        config.peiyinform.show()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
