import json
import os
import platform
import re
import shutil
import sys
import threading
import warnings

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMessageBox, QFileDialog, QPushButton

from videotrans.component.progressbar import ClickableProgressBar
from videotrans.recognition import OPENAI_WHISPER, FASTER_WHISPER, is_allow_lang as recogn_is_allow_lang, \
    is_input_api as recogn_is_input_api
from videotrans.task.logs_worker import LogsWorker
from videotrans.tts import EDGE_TTS, AZURE_TTS, AI302_TTS, CLONE_VOICE_TTS, TTS_API, GPTSOVITS_TTS, COSYVOICE_TTS, \
    FISHTTS, CHATTTS, GOOGLE_TTS, OPENAI_TTS, ELEVENLABS_TTS, is_allow_lang as tts_is_allow_lang, \
    is_input_api as tts_is_input_api

warnings.filterwarnings('ignore')
from videotrans.winform import fn_downmodel

from videotrans.util import tools
from videotrans import translator, tts
from videotrans.configure import config
from pathlib import Path
from videotrans.task.main_worker import Worker


class SecWindow():
    def __init__(self, main=None):
        self.main = main
        # 更新按钮
        self.update_btn = None
        # 单个执行时，当前字幕所处阶段：识别后编辑或翻译后编辑
        self.edit_subtitle_type = ''
        # 进度按钮
        self.processbtns = {}
        # 任务对象
        self.task: Worker = None
        # 进度记录
        self.task_log = None
        # 试听对象
        self.shitingobj = None
        # 单个任务时，修改字幕后需要保存到的位置，原始语言字幕或者目标语音字幕
        self.wait_subtitle = None

    def is_separate_fun(self, state):
        config.params['is_separate'] = True if state else False

    # 选中按钮时判断当前cuda是否可用
    def check_cuda(self, state):
        import torch
        res = state
        # 选中如果无效，则取消
        if state and not torch.cuda.is_available():
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['nocuda'])
            self.main.enable_cuda.setChecked(False)
            self.main.enable_cuda.setDisabled(True)
            res = False
        config.params['cuda'] = res

    # 配音速度改变时
    def voice_rate_changed(self, text):
        config.params['voice_rate'] = f'+{text}%' if text >= 0 else f'{text}%'

    # 简单新手模式
    def set_xinshoujandann(self):
        self.main.action_xinshoujandan.setChecked(True)
        self.main.app_mode = 'biaozhun_jd'
        self.main.show_tips.setText(config.transobj['xinshoumoshitips'])
        self.main.startbtn.setText(config.transobj['kaishichuli'])
        self.main.action_xinshoujandan.setChecked(True)
        self.main.action_biaozhun.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)
        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, False)
        # 翻译渠道
        self.main.translate_type.setCurrentIndex(1)
        self.hide_show_element(self.main.layout_translate_type, False)
        # 代理
        self.hide_show_element(self.main.layout_proxy, False)
        # 原始语言
        self.hide_show_element(self.main.layout_source_language, True)
        # 目标语言
        self.hide_show_element(self.main.layout_target_language, True)
        # 配音角色
        self.main.tts_type.setCurrentIndex(EDGE_TTS)
        self.hide_show_element(self.main.layout_voice_role, True)
        # tts类型
        self.hide_show_element(self.main.layout_tts_type, False)
        # 试听按钮
        self.main.listen_btn.hide()
        # 语音模型
        self.main.whisper_type.setCurrentIndex(0)
        self.main.whisper_model.setCurrentIndex(0)
        self.main.subtitle_type.setCurrentIndex(1)
        self.hide_show_element(self.main.layout_whisper_model, False)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, False)
        self.hide_show_element(self.main.edge_volume_layout, False)
        self.hide_show_element(self.main.layout_voice_rate, False)
        self.main.voice_autorate.setChecked(True)
        self.main.voice_autorate.hide()
        self.main.video_autorate.setChecked(True)
        self.main.video_autorate.hide()
        self.main.append_video.setChecked(True)
        self.main.append_video.hide()
        self.main.splitter.setSizes([self.main.width, 0])
        self.hide_show_element(self.main.subtitle_layout, False)
        # 视频自动降速
        self.main.is_separate.setDisabled(True)
        self.main.addbackbtn.setDisabled(True)
        self.main.only_video.setDisabled(True)
        self.main.back_audio.setReadOnly(True)
        self.main.is_separate.hide()
        self.main.addbackbtn.hide()
        self.main.back_audio.hide()
        self.main.only_video.hide()
        # cuda
        self.main.enable_cuda.setChecked(False)
        self.main.enable_cuda.hide()

    # 启用标准模式
    def set_biaozhun(self):
        self.main.action_biaozhun.setChecked(True)
        self.main.app_mode = 'biaozhun'
        self.main.show_tips.setText("")
        self.main.startbtn.setText(config.transobj['kaishichuli'])
        self.main.action_biaozhun.setChecked(True)
        self.main.action_xinshoujandan.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)
        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)
        # 翻译渠道
        self.hide_show_element(self.main.layout_translate_type, True)
        # 代理
        self.hide_show_element(self.main.layout_proxy, True)
        # 原始语言
        self.hide_show_element(self.main.layout_source_language, True)
        # 目标语言
        self.hide_show_element(self.main.layout_target_language, True)
        # tts类型
        self.hide_show_element(self.main.layout_tts_type, True)
        # 配音角色
        self.hide_show_element(self.main.layout_voice_role, True)
        # 试听按钮
        # 显示音量 音调变化
        self.hide_show_element(self.main.edge_volume_layout, True)
        self.main.listen_btn.show()
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, True)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, True)
        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, True)
        self.main.is_separate.setDisabled(False)
        self.main.is_separate.show()
        self.main.addbackbtn.setDisabled(False)
        self.main.only_video.setDisabled(False)
        self.main.back_audio.setReadOnly(False)
        self.main.video_autorate.setDisabled(False)
        self.main.voice_autorate.setDisabled(False)
        self.main.voice_autorate.show()
        self.main.append_video.setDisabled(False)
        self.main.append_video.setDisabled(False)
        self.hide_show_element(self.main.subtitle_layout, True)
        self.main.splitter.setSizes([self.main.width - 400, 400])
        self.main.addbackbtn.show()
        self.main.back_audio.show()
        self.main.only_video.show()
        self.main.video_autorate.show()
        self.main.append_video.show()
        # cuda
        self.main.enable_cuda.show()

    # 视频提取字幕并翻译，无需配音
    def set_tiquzimu(self):
        self.main.action_tiquzimu.setChecked(True)
        self.main.app_mode = 'tiqu'
        self.main.show_tips.setText(config.transobj['tiquzimu'])
        self.main.startbtn.setText(config.transobj['kaishitiquhefanyi'])
        self.main.action_tiquzimu.setChecked(True)
        self.main.action_xinshoujandan.setChecked(False)
        self.main.action_biaozhun.setChecked(False)

        self.hide_show_element(self.main.subtitle_layout, True)
        self.main.splitter.setSizes([self.main.width - 400, 400])
        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)
        # 隐藏音量 音调变化
        self.hide_show_element(self.main.edge_volume_layout, False)
        # 翻译渠道
        self.hide_show_element(self.main.layout_translate_type, True)
        # 代理
        self.hide_show_element(self.main.layout_proxy, True)
        # 原始语言
        self.hide_show_element(self.main.layout_source_language, True)
        # 目标语言
        self.hide_show_element(self.main.layout_target_language, True)
        # tts类型
        self.hide_show_element(self.main.layout_tts_type, False)
        # 配音角色
        self.hide_show_element(self.main.layout_voice_role, False)
        # 试听按钮
        self.main.listen_btn.hide()
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, True)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, False)
        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, False)
        self.main.is_separate.setDisabled(True)
        self.main.addbackbtn.setDisabled(True)
        self.main.only_video.setDisabled(True)
        self.main.back_audio.setReadOnly(True)
        self.main.video_autorate.setDisabled(True)
        self.main.voice_autorate.setDisabled(True)
        self.main.append_video.setDisabled(True)

        self.main.append_video.hide()
        self.main.voice_autorate.hide()
        self.main.is_separate.hide()
        self.main.addbackbtn.hide()
        self.main.back_audio.hide()
        self.main.only_video.hide()
        self.main.video_autorate.hide()
        # cuda
        self.main.enable_cuda.show()

    # 关于页面
    def about(self):
        from videotrans.component import InfoForm
        self.main.infofrom = InfoForm()
        self.main.infofrom.show()

    # voice_autorate  变化
    def autorate_changed(self, state, name):
        if name == 'voice':
            config.params['voice_autorate'] = state
        elif name == 'video':
            config.params['video_autorate'] = state
        elif name == 'append_video':
            config.params['append_video'] = state

    # 隐藏布局及其元素
    def hide_show_element(self, wrap_layout, show_status):
        def hide_recursive(layout, show_status):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    if not show_status:
                        item.widget().hide()
                    else:
                        item.widget().show()
                elif item.layout():
                    hide_recursive(item.layout(), show_status)

        hide_recursive(wrap_layout, show_status)

    # 删除进度按钮
    def delete_process(self):
        for i in range(self.main.processlayout.count()):
            item = self.main.processlayout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.processbtns = {}

    # 开启执行后，禁用按钮，停止或结束后，启用按钮
    def disabled_widget(self, type):
        self.main.clear_cache.setDisabled(type)
        self.main.volume_rate.setDisabled(type)
        self.main.pitch_rate.setDisabled(type)
        self.main.import_sub.setDisabled(type)
        self.main.btn_get_video.setDisabled(type)
        self.main.btn_save_dir.setDisabled(type)
        self.main.translate_type.setDisabled(type)
        self.main.proxy.setDisabled(type)
        self.main.source_language.setDisabled(type)
        self.main.target_language.setDisabled(type)
        self.main.tts_type.setDisabled(type)
        self.main.whisper_model.setDisabled(type)
        self.main.whisper_type.setDisabled(type)
        self.main.subtitle_type.setDisabled(type)
        self.main.enable_cuda.setDisabled(type)
        self.main.model_type.setDisabled(type)
        self.main.voice_autorate.setDisabled(type)
        self.main.video_autorate.setDisabled(type)
        self.main.append_video.setDisabled(type)
        self.main.voice_role.setDisabled(type)
        self.main.voice_rate.setDisabled(type)
        self.main.only_video.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.is_separate.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.addbackbtn.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.back_audio.setReadOnly(True if self.main.app_mode in ['tiqu'] else type)

    # 右侧字幕区导出
    def export_sub_fun(self):
        srttxt = self.main.subtitle_area.toPlainText().strip()
        if not srttxt:
            return
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
            file.write(srttxt)

    def open_url(self, title):
        if title == 'online':
            self.about()
        else:
            tools.open_url(title=title)

    # 将倒计时设为立即超时
    def set_djs_timeout(self):
        config.task_countdown = 0
        self.main.continue_compos.setText(config.transobj['jixuzhong'])
        self.main.continue_compos.setDisabled(True)
        self.main.stop_djs.hide()
        if self.shitingobj:
            self.shitingobj.stop = True
        self.update_subtitle()

    # 手动点击暂停按钮
    def reset_timeid(self):
        self.main.stop_djs.hide()
        config.task_countdown = 86400
        self.main.continue_compos.setDisabled(False)
        self.main.continue_compos.setText(config.transobj['nextstep'])
        self.update_data('{"type":"allow_edit"}')

    # 翻译渠道变化时，检测条件
    def set_translate_type(self, idx):
        try:
            t = self.main.target_language.currentText()
            if t not in ['-']:
                rs = translator.is_allow_translate(translate_type=idx, show_target=t, win=self.main)
                if rs is not True:
                    return False
            config.params['translate_type'] = idx
        except Exception as e:
            QMessageBox.critical(self.main, config.transobj['anerror'], str(e))

    # 0=整体识别模型
    # 1=均等分割模式
    def check_whisper_type(self, index):
        if index == 0:
            config.params['whisper_type'] = 'all'
        else:
            config.params['whisper_type'] = 'avg'

    # 语音识别方式改变时
    def model_type_change(self):
        config.params['model_type'] = self.main.model_type.currentIndex()
        if config.params['model_type'] > 0:
            self.main.whisper_type.setDisabled(True)
        else:
            self.main.whisper_type.setDisabled(False)

        if config.params['model_type'] > 1:
            self.main.whisper_model.setDisabled(True)
        else:
            self.main.whisper_model.setDisabled(False)
            self.check_whisper_model(self.main.whisper_model.currentText())
        lang = translator.get_code(show_text=self.main.source_language.currentText())
        is_allow_lang = recogn_is_allow_lang(langcode=lang, model_type=config.params['model_type'])
        if is_allow_lang is not True:
            QMessageBox.critical(self.main, config.transobj['anerror'], is_allow_lang)

    # 判断 openai whisper和 faster whisper 模型是否存在
    def check_whisper_model(self, name):
        if self.main.model_type.currentIndex() in [2, 3, 4, 5, 6]:
            return True
        if name.find('/') > 0:
            return True

        slang = self.main.source_language.currentText()
        if name.endswith('.en') and translator.get_code(show_text=slang) != 'en':
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['enmodelerror'])
            return False

        if config.params['model_type'] == OPENAI_WHISPER:
            if name.startswith('distil'):
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['openaimodelerror'])
                return False
            # 不存在，需下载

            if not Path(config.ROOT_DIR + f"/models/{name}.pt").exists():
                fn_downmodel.open(model_name=name, model_type=OPENAI_WHISPER)
                return False
            return True

        file = f'{config.ROOT_DIR}/models/models--Systran--faster-whisper-{name}/snapshots'
        if name.startswith('distil'):
            file = f'{config.ROOT_DIR}/models/models--Systran--faster-{name}/snapshots'

        if not Path(file).exists():
            fn_downmodel.open(model_name=name, model_type=FASTER_WHISPER)
            return False

        return True

    def clearcache(self):
        if config.defaulelang == 'zh':
            question = tools.show_popup('确认进行清理？', '清理后需要重启软件并重新填写设置菜单中各项配置信息')

        else:
            question = tools.show_popup('Confirm cleanup?', 'The software needs to be restarted after cleaning')

        if question == QMessageBox.Yes:
            shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
            shutil.rmtree(config.TEMP_HOME, ignore_errors=True)
            tools.remove_qsettings_data()
            QMessageBox.information(self.main, 'Please restart the software' if config.defaulelang != 'zh' else '请重启软件',
                                    'Please restart the software' if config.defaulelang != 'zh' else '软件将自动关闭，请重新启动，设置中各项配置信息需重新填写')
            self.main.close()

    # 是否属于 配音角色 随所选目标语言变化的配音渠道 是 edgeTTS AzureTTS 或 302.ai同时 ai302tts_model=azure
    def change_by_lang(self, type):
        if type in [EDGE_TTS, AZURE_TTS]:
            return True
        if type == AI302_TTS and config.params['ai302tts_model'] == 'azure':
            return True
        if type == AI302_TTS and config.params['ai302tts_model'] == 'doubao':
            return True
        return False

    # tts类型改变
    def tts_type_change(self, type):
        self.hide_show_element(self.main.edge_volume_layout, self.change_by_lang(type))
        if tts_is_input_api(tts_type=type) is not True:
            return

        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if lang and lang != '-':
            is_allow_lang = tts_is_allow_lang(langcode=lang, tts_type=type)
            if is_allow_lang is not True:
                QMessageBox.critical(self.main, config.transobj['anerror'], is_allow_lang)
                return False

        config.params['tts_type'] = type
        config.params['line_roles'] = {}
        if type == GOOGLE_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = ["gtts"]
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == OPENAI_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['openaitts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == ELEVENLABS_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['elevenlabstts_role']
            if len(self.main.current_rolelist) < 1:
                self.main.current_rolelist = tools.get_elevenlabs_role()
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif self.change_by_lang(type):
            self.set_voice_role(self.main.target_language.currentText())
        elif type == AI302_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['ai302tts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == CLONE_VOICE_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params["clone_voicelist"]
            self.main.voice_role.addItems(self.main.current_rolelist)
            threading.Thread(target=tools.get_clone_role).start()
        elif type == CHATTTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = list(config.ChatTTS_voicelist)
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == TTS_API:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['ttsapi_voice_role'].strip().split(',')
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['GPT-SoVITS']
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == COSYVOICE_TTS:
            rolelist = tools.get_cosyvoice_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['clone']
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == FISHTTS:
            rolelist = tools.get_fishtts_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['FishTTS']
            self.main.voice_role.addItems(self.main.current_rolelist)

    # 试听配音
    def listen_voice_fun(self):
        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if not lang:
            return QMessageBox.critical(self.main, config.transobj['anerror'],
                                        '请先选择目标语言' if config.defaulelang == 'zh' else 'Please select the target language first')
        text = config.params[f'listen_text_{lang}']
        role = self.main.voice_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['mustberole'])
        voice_dir = os.environ.get('APPDATA') or os.environ.get('appdata')
        if not voice_dir or not Path(voice_dir).exists():
            voice_dir = config.TEMP_DIR + "/voice_tmp"
        else:
            voice_dir = Path(voice_dir + "/pyvideotrans").as_posix()
        if not Path(voice_dir).exists():
            Path(voice_dir).mkdir(parents=True, exist_ok=True)
        lujing_role = role.replace('/', '-')
        rate=int(self.main.voice_rate.value())
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"

        volume = int(self.main.volume_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = int(self.main.pitch_rate.value())
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{volume}Hz'


        voice_file = f"{voice_dir}/{config.params['tts_type']}-{lang}-{lujing_role}-{volume}-{pitch}.mp3"

        obj = {
            "text": text,
            "rate": rate,
            "role": role,
            "filename": voice_file,
            "tts_type": self.main.tts_type.currentIndex(),
            "language": lang,
            "volume":volume,
            "pitch": pitch,
        }
        if role == 'clone':
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 '原音色克隆不可试听' if config.defaulelang == 'zh' else 'The original sound clone cannot be auditioned')
            return
        threading.Thread(target=tts.run,kwargs={"queue_tts":[obj],"play":True,"is_test":True}).start()


    # 角色改变时 显示试听按钮
    def show_listen_btn(self, role):
        config.params["voice_role"] = role
        if role == 'No' or (config.params['tts_type'] == CLONE_VOICE_TTS and config.params['voice_role'] == 'clone'):
            self.main.listen_btn.hide()
            return
        if self.main.app_mode in ['biaozhun']:
            self.main.listen_btn.show()
            self.main.listen_btn.setDisabled(False)

    # 目标语言改变时设置配音角色
    # t 语言显示文字
    def set_voice_role(self, t):
        role = self.main.voice_role.currentText()
        code = translator.get_code(show_text=t)
        if code and code != '-':
            is_allow_lang = tts_is_allow_lang(langcode=code, tts_type=config.params['tts_type'])
            if is_allow_lang is not True:
                return QMessageBox.critical(self.main, config.transobj['anerror'], is_allow_lang)
            # 判断翻译渠道是否支持翻译到该目标语言
            if translator.is_allow_translate(translate_type=self.main.translate_type.currentIndex(), show_target=t,
                                             win=self.main) is not True:
                return

        if not self.change_by_lang(config.params['tts_type']):
            if role != 'No' and self.main.app_mode in ['biaozhun']:
                self.main.listen_btn.show()
                self.main.listen_btn.setDisabled(False)
            else:
                self.main.listen_btn.hide()
            return

        self.main.listen_btn.hide()
        self.main.voice_role.clear()
        # 未设置目标语言，则清空 edgeTTS角色
        if t == '-':
            self.main.voice_role.addItems(['No'])
            return
        show_rolelist = None
        if config.params['tts_type'] == EDGE_TTS:
            show_rolelist = tools.get_edge_rolelist()
        elif config.params['tts_type'] == AI302_TTS and config.params['ai302tts_model'] == 'doubao':
            show_rolelist = tools.get_302ai_doubao()
        else:
            # AzureTTS或 302.ai选择doubao模型
            show_rolelist = tools.get_azure_rolelist()

        if not show_rolelist:
            self.main.target_language.setCurrentText('-')
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['waitrole'])
            return
        try:
            vt = code.split('-')[0]
            if vt not in show_rolelist:
                self.main.voice_role.addItems(['No'])
                return
            if len(show_rolelist[vt]) < 2:
                self.main.target_language.setCurrentText('-')
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['waitrole'])
                return
            self.main.current_rolelist = show_rolelist[vt]
            self.main.voice_role.addItems(show_rolelist[vt])
        except:
            self.main.voice_role.addItems(['No'])

    # get video filter mp4
    def get_mp4(self):
        format_str=" ".join([ '*.'+f  for f in  config.VIDEO_EXTS])
        if self.main.app_mode == 'tiqu':
            format_str=" ".join([ '*.'+f  for f in  config.VIDEO_EXTS+config.AUDIO_EXITS])
        fnames, _ = QFileDialog.getOpenFileNames(self.main, config.transobj['selectmp4'], config.params['last_opendir'],
                                                 f'Files({format_str})')
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = Path(it).as_posix()

        if len(fnames) > 0:
            self.main.source_mp4.setText(f'{len((fnames))} videos')
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            config.queue_mp4 = fnames

    # 导入背景声音
    def get_background(self):
        format_str=" ".join([ '*.'+f  for f in  config.AUDIO_EXITS])
        fname, _ = QFileDialog.getOpenFileName(self.main, 'Background music', config.params['last_opendir'],
                                               f"Audio files({format_str})")
        if not fname:
            return
        fname = Path(fname).as_posix()
        self.main.back_audio.setText(fname)

    # 从本地导入字幕文件
    def import_sub_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self.main, config.transobj['selectmp4'], config.params['last_opendir'],
                                               "Srt files(*.srt *.txt)")
        if fname:
            content = ""
            try:
                content = Path(fname).read_text(encoding='utf-8')
            except:
                content = Path(fname).read_text(encoding='gbk')
            finally:
                if content:
                    self.main.subtitle_area.clear()
                    self.main.subtitle_area.insertPlainText(content.strip())
                else:
                    return QMessageBox.critical(self.main, config.transobj['anerror'],
                                                config.transobj['import src error'])

    # 保存目录
    def get_save_dir(self):
        dirname = QFileDialog.getExistingDirectory(self.main, config.transobj['selectsavedir'],
                                                   config.params['last_opendir'])
        dirname = Path(dirname).as_posix()
        self.main.target_dir.setText(dirname)

    # 检测各个模式下参数是否设置正确
    def set_mode(self):
        if self.main.app_mode == 'tiqu' or (
                self.main.app_mode.startswith('biaozhun') and config.params['subtitle_type'] < 1 and config.params[
            'voice_role'] == 'No'):
            self.main.app_mode = 'tiqu'
            # 提取字幕模式，必须有视频、有原始语言，语音模型
            config.params['is_separate'] = False
            config.params['subtitle_type'] = 0
            config.params['voice_role'] = 'No'
            config.params['voice_rate'] = '+0%'
            config.params['voice_autorate'] = False
            config.params['append_video'] = False
            config.params['back_audio'] = ''
        elif self.main.app_mode == 'biaozhun_jd':
            config.params['voice_autorate'] = True
            config.params['append_video'] = True
            config.params['is_separate'] = False
            config.params['back_audio'] = ''

    # 判断是否需要翻译
    def shound_translate(self):
        if self.main.target_language.currentText() == '-' or self.main.source_language.currentText() == '-':
            return False
        if self.main.target_language.currentText() == self.main.source_language.currentText():
            return False
        return True

    # 设置或删除代理
    def change_proxy(self, p):
        config.params['proxy'] = p.strip()
        try:
            if not config.params['proxy']:
                # 删除代理
                tools.set_proxy('del')
        except Exception:
            pass

    # 核对代理填写
    def check_proxy(self):
        proxy = self.main.proxy.text().strip().replace('：', ':')
        if proxy:
            if not re.match(r'^(http|sock)', proxy, re.I):
                proxy = f'http://{proxy}'
            if not re.match(r'^(http|sock)(s|5)?://(\d+\.){3}\d+:\d+', proxy, re.I):
                question = tools.show_popup(
                    '请确认代理地址是否正确？' if config.defaulelang == 'zh' else 'Please make sure the proxy address is correct', """你填写的网络代理地址似乎不正确
        一般代理/vpn格式为 http://127.0.0.1:数字端口号 
        如果不知道什么是代理请勿随意填写
        ChatGPT等api地址请填写在菜单-设置-对应配置内。
        如果确认代理地址无误，请点击 Yes 继续执行""" if config.defaulelang == 'zh' else 'The network proxy address you fill in seems to be incorrect, the general proxy/vpn format is http://127.0.0.1:port, if you do not know what is the proxy please do not fill in arbitrarily, ChatGPT and other api address please fill in the menu - settings - corresponding configuration. If you confirm that the proxy address is correct, please click Yes to continue.')
                if question != QMessageBox.Yes:
                    self.update_status('stop')
                    return False
        # 设置或删除代理
        config.params['proxy'] = proxy
        try:
            if config.params['proxy']:
                # 设置代理
                tools.set_proxy(config.params['proxy'])
            else:
                # 删除代理
                tools.set_proxy('del')
        except Exception:
            pass
        return True

    # 核对tts选择是否正确
    def check_tts(self):
        if tts_is_input_api(tts_type=config.params['tts_type']) is not True:
            return False
        # 如果没有选择目标语言，但是选择了配音角色，无法配音
        if config.params['target_language'] == '-' and config.params['voice_role'] != 'No':
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['wufapeiyin'])
            return False
        return True

    # 核对字幕
    def check_txt(self, txt=''):
        if txt and not re.search(r'\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?\s*?-->\s*?\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?', txt):
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 '字幕格式不正确，请重新导入字幕或删除已导入字幕' if config.defaulelang == 'zh' else 'Subtitle format is not correct, please re-import the subtitle or delete the imported subtitle.')
            return False
        return True

    # 核对所选语音识别模式是否正确
    def check_reccogn(self):
        langcode = translator.get_code(show_text=config.params['source_language'])

        is_allow_lang = recogn_is_allow_lang(langcode=langcode, model_type=self.main.model_type.currentIndex())
        if is_allow_lang is not True:
            QMessageBox.critical(self.main, config.transobj['anerror'], is_allow_lang)
            return False
        # 判断是否填写自定义识别api openai-api识别、zh_recogn识别信息
        return recogn_is_input_api(model_type=self.main.model_type.currentIndex())

    # 格式化视频信息
    def format_video(self, name):

        raw_pathlib = Path(name)
        raw_basename = raw_pathlib.name
        raw_noextname = raw_pathlib.stem
        ext_path = raw_noextname.split('/')
        if len(ext_path) > 1:
            raw_noextname = ext_path[-1]
        ext = raw_pathlib.suffix
        raw_dirname = raw_pathlib.parent.resolve().as_posix()

        output_path = Path(f'{config.params["target_dir"]}/{raw_noextname}' if config.params[
            "target_dir"] else f'{raw_dirname}/_video_out/{raw_noextname}')
        output_path.mkdir(parents=True, exist_ok=True)

        obj = {
            "name": name,
            # 处理后 移动后符合规范的目录名
            "dirname": raw_dirname,
            # 符合规范的基本名带后缀
            "basename": raw_basename,
            # 符合规范的不带后缀
            "noextname": raw_noextname,
            # 扩展名
            "ext": ext[1:],
            # 最终存放目标位置，直接存到这里
            "target_dir": output_path.as_posix(),
            "uuid": tools.get_md5(name),
        }
        return obj

    # 检测开始状态并启动
    def check_start(self):
        self.edit_subtitle_type = ''
        if config.current_status == 'ing':
            # 已在执行中，则停止
            question = tools.show_popup(config.transobj['exit'], config.transobj['confirmstop'])
            if question == QMessageBox.Yes:
                self.update_status('stop')
                return

        # 无视频选择 ，也无导入字幕，无法处理
        if len(config.queue_mp4) < 1:
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 '必须选择视频文件' if config.defaulelang == 'zh' else 'Video file must be selected')
            return False

        if self.check_proxy() is not True:
            return

        config.task_countdown = int(config.settings['countdown_sec'])
        config.settings = config.parse_init()

        # 目标文件夹
        target_dir = self.main.target_dir.text().strip()
        config.params['target_dir'] = Path(target_dir).as_posix() if target_dir else ''
        config.params['source_language'] = self.main.source_language.currentText()
        config.params['target_language'] = self.main.target_language.currentText()

        # 核对识别是否正确
        if self.check_reccogn() is not True:
            return
        # 配音角色
        config.params['voice_role'] = self.main.voice_role.currentText()
        if config.params['voice_role'] == 'No':
            config.params['is_separate'] = False

        # 配音自动加速
        config.params['voice_autorate'] = self.main.voice_autorate.isChecked()
        config.params['append_video'] = self.main.append_video.isChecked()

        # 语音模型
        config.params['whisper_model'] = self.main.whisper_model.currentText()
        # 识别模式，从faster--openai--googlespeech ...
        config.params['model_type'] = self.main.model_type.currentIndex()
        # 字幕嵌入类型
        config.params['subtitle_type'] = int(self.main.subtitle_type.currentIndex())
        try:
            voice_rate = int(self.main.voice_rate.value())
            config.params['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"{voice_rate}%"
        except Exception:
            config.params['voice_rate'] = '+0%'
        try:
            volume = int(self.main.volume_rate.value())
            pitch = int(self.main.pitch_rate.value())
            config.params['volume'] = f'+{volume}%' if volume > 0 else f'{volume}%'
            config.params['pitch'] = f'+{pitch}Hz' if pitch > 0 else f'{pitch}Hz'
        except Exception:
            config.params['volume'] = '+0%'
            config.params['pitch'] = '+0Hz'
        config.params['back_audio'] = self.main.back_audio.text().strip()
        config.params['translate_type'] = self.main.translate_type.currentIndex()
        config.params['clear_cache'] = True if self.main.clear_cache.isChecked() else False
        config.params['only_video'] = self.main.only_video.isChecked()

        # 如果需要翻译，再判断是否符合翻译规则
        if self.shound_translate() and translator.is_allow_translate(
                translate_type=config.params['translate_type'],
                show_target=config.params['target_language']) is not True:
            return False

        # 字幕区文字
        txt = self.main.subtitle_area.toPlainText().strip()
        if self.check_txt(txt) is not True:
            return

        # tts类型
        if self.check_tts() is not True:
            return
        # 设置各项模式参数
        self.set_mode()

        # 检测模型是否存在
        if not txt and config.params['model_type'] in [OPENAI_WHISPER, FASTER_WHISPER] and not self.check_whisper_model(
                config.params['whisper_model']):
            return False
        # 判断CUDA
        if self.cuda_isok() is not True:
            return
        # 核对文件路径是否符合规范，防止ffmpeg处理中出错
        if self.url_right() is not True:
            return
        # 核对是否存在名字相同后缀不同的文件，以及若存在音频则强制为tiqu模式
        if self.check_name() is not True:
            return
        self.main.save_setting()
        self.delete_process()
        # 设为开始
        self.update_status('ing')
        config.settings = config.parse_init()
        if self.main.app_mode in ['biaozhun_jd', 'biaozhun', 'tiqu']:
            config.params['app_mode'] = self.main.app_mode
        config.getset_params(config.params)

        # 启动进度日志任务
        self.task_logs = LogsWorker(parent=self.main)
        self.task_logs.post_logs.connect(self.update_data)
        self.task_logs.start()

        videolist = []
        for video_path in config.queue_mp4:
            obj = self.format_video(video_path)
            videolist.append(obj)
            self.add_process_btn(target_dir=Path(obj['target_dir']).parent.resolve().as_posix() if config.params['only_video'] else obj['target_dir'], name=obj['name'], uuid=obj['uuid'])

        # 启动任务
        self.task = Worker(
            parent=self.main,
            app_mode=self.main.app_mode,
            videolist=videolist,
            txt=txt,
            task_logs=self.task_logs
        )
        self.task.start()

        for k, v in self.main.moshis.items():
            if k != self.main.app_mode:
                v.setDisabled(True)

    # 如果选中了cuda，判断是否可用
    def cuda_isok(self):
        if not config.params["cuda"] or platform.system() == 'Darwin':
            return True

        import torch
        if not torch.cuda.is_available():
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocuda"])
            return False

        if config.params['model_type'] == OPENAI_WHISPER:
            return True
        allow = True
        try:
            from torch.backends import cudnn
            if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                allow = False
        except:
            allow = False
        finally:
            if not allow:
                self.main.enable_cuda.setChecked(False)
                config.params['cuda'] = False
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocudnn"])
                return False
        return True

    # 判断文件路径是否正确
    def url_right(self):
        for vurl in config.queue_mp4:
            if re.search(r'[:\?\*<>\|\"\']', vurl[4:]):
                return QMessageBox.critical(self.main, config.transobj['anerror'],
                                            '视频所在路径和视频名字中不可含有  :  * ? < > | " \' 符号，请修正 ' if config.defaulelang == 'zh' else 'The path and name of the video must not contain the  : * ? < > | " \' symbols, please revise. ')
            if len(vurl) > 255 and sys.platform == 'win32':
                return QMessageBox.critical(self.main, config.transobj['anerror'],
                                            f'视频路径总长度超过255个字符，处理中可能会出错，请改短视频文件名，并移动到浅层目录下url={vurl}' if config.defaulelang == 'zh' else f'The total length of the video path is more than 255 characters, there may be an error in processing, please change the short video file name and move it to a shallow directoryurl={vurl}')
        return True

    # 如果存在音频则设为提取
    # 如果有同名则停止
    def check_name(self):
        if self.main.app_mode != 'tiqu':
            for it in config.queue_mp4:
                if Path(it).suffix.lower() in config.AUDIO_EXITS:
                    self.main.app_mode = 'tiqu'
                    config.params['is_separate'] = False
                    break

        if len(config.queue_mp4) > 1:
            same_name = {}
            for it in config.queue_mp4:
                p = Path(it)
                stem = p.stem
                if stem in same_name:
                    same_name[stem].append(p.name)
                else:
                    same_name[stem] = [p.name]
            msg = ''
            for it in same_name.values():
                if len(it) > 1:
                    msg += ",".join(it)
            if msg:
                QMessageBox.critical(self.main, config.transobj['anerror'],
                                     f'不可含有名字相同但后缀不同的文件，会导致混淆，请修改 {msg} ' if config.defaulelang == 'zh' else f'Do not include files with the same name but different extensions, this can lead to confusion, please modify {msg} ')
                return False
        return True

    # 添加进度条
    def add_process_btn(self, *, target_dir: str = None, name: str = None, uuid=None):
        clickable_progress_bar = ClickableProgressBar(self)
        clickable_progress_bar.progress_bar.setValue(0)  # 设置当前进度值
        clickable_progress_bar.setText(config.transobj["waitforstart"])
        clickable_progress_bar.setMinimumSize(500, 50)
        clickable_progress_bar.setToolTip(config.transobj['mubiao'])
        # # 将按钮添加到布局中

        clickable_progress_bar.setTarget(target_dir=target_dir, name=name)
        clickable_progress_bar.setCursor(Qt.PointingHandCursor)
        self.main.processlayout.addWidget(clickable_progress_bar)
        if uuid:
            self.processbtns[uuid] = clickable_progress_bar

    # 设置按钮上的日志信息
    def set_process_btn_text(self, text, uuid="", type="logs"):
        if not uuid or uuid not in self.processbtns:
            return
        if not self.task:
            return
        if type == 'set_precent' and self.processbtns[uuid].precent < 100:
            t, precent = text.split('???')
            precent = int(float(precent))
            self.processbtns[uuid].setPrecent(precent)
            self.processbtns[uuid].setText(f'{config.transobj["running"].replace("..", "")} {t}')
            self.processbtns[uuid].progress_bar.setValue(precent)
        elif type == 'logs' and self.processbtns[uuid].precent < 100:
            self.processbtns[uuid].setText(text)
        elif type == 'succeed':
            self.processbtns[uuid].setEnd()
            if self.processbtns[uuid].name in config.queue_mp4:
                config.queue_mp4.remove(self.processbtns[uuid].name)
        elif type == 'error':
            self.processbtns[uuid].setError(text)
            self.processbtns[uuid].progress_bar.setStyleSheet('color:#ff0000')
            self.processbtns[uuid].setCursor(Qt.PointingHandCursor)

    # 更新执行状态
    def update_status(self, type):
        config.current_status = type
        self.main.continue_compos.hide()
        self.main.stop_djs.hide()
        if type != 'ing':
            # 结束或停止
            self.main.subtitle_area.setReadOnly(False)
            self.main.subtitle_area.clear()
            self.main.startbtn.setText(config.transobj[type])
            self.main.export_sub.setDisabled(False)
            self.main.set_line_role.setDisabled(False)
            # 启用
            self.disabled_widget(False)
            for k, v in self.main.moshis.items():
                v.setDisabled(False)
            if type == 'end':
                for prb in self.processbtns.values():
                    prb.setEnd()
                # 成功完成
                self.main.source_mp4.setText(config.transobj["No select videos"])
                # 关机
                if self.main.shutdown.isChecked():
                    try:
                        tools.shutdown_system()
                    except Exception as e:
                        QMessageBox.critical(self.main, config.transobj['anerror'],
                                             config.transobj['shutdownerror'] + str(e))
                self.main.source_mp4.setText(config.transobj["No select videos"])
                self.main.target_dir.clear()
            else:
                # 停止
                self.main.source_mp4.setText(config.transobj["No select videos"] if len(
                    config.queue_mp4) < 1 else f'{len(config.queue_mp4)} videos')
                # 清理输入
            if self.main.app_mode == 'tiqu':
                self.set_tiquzimu()
            try:
                self.task = None
                self.tasklog = None
            except Exception:
                pass
        else:
            # 重设为开始状态
            self.disabled_widget(True)
            self.main.startbtn.setText(config.transobj["starting..."])

    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        # 一行一行插入字幕到字幕编辑区
        if d['type'] == "subtitle":
            self.main.subtitle_area.moveCursor(QTextCursor.End)
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] in ["logs", 'set_precent', 'error', 'succeed', 'show_djs']:
            self.set_process_btn_text(d['text'], uuid=d['uuid'], type=d['type'])
        elif d['type'] in ['stop', 'end']:
            self.update_status(d['type'])
            if "linerolew" in config.child_forms and hasattr(config.child_forms['linerolew'], 'close'):
                config.child_forms['linerolew'].close()
                config.child_forms.pop('linerolew', None)
        elif d['type'] == 'set_source_sub':
            # 单个任务时，设置 self.wait_subtitle 为原始语言文件，以便界面中修改字幕后保存
            self.wait_subtitle = d['text']
        elif d['type'] == 'set_target_sub':
            # 单个任务时，设置 self.wait_subtitle 为原始语言文件，以便界面中修改字幕后保存
            self.wait_subtitle = d['text']
        elif d['type'] == 'edit_subtitle_source' or d['type'] == 'edit_subtitle_target':
            # 显示出合成按钮,等待编辑字幕,允许修改字幕
            self.main.subtitle_area.setReadOnly(False)
            self.main.subtitle_area.setFocus()
            self.main.continue_compos.show()
            self.main.continue_compos.setDisabled(False)
            self.main.continue_compos.setText(d['text'])
            self.main.stop_djs.show()
            self.edit_subtitle_type = d['type']
        elif d['type'] == 'disabled_edit':
            # 禁止修改字幕
            self.main.subtitle_area.setReadOnly(True)
            self.main.export_sub.setDisabled(True)
            self.main.set_line_role.setDisabled(True)
        elif d['type'] == 'allow_edit':
            # 允许修改字幕
            self.main.subtitle_area.setReadOnly(False)
            self.main.subtitle_area.setFocus()
            self.main.export_sub.setDisabled(False)
            self.main.set_line_role.setDisabled(False)
        elif d['type'] == 'replace_subtitle':
            # 完全替换字幕区
            self.main.subtitle_area.clear()
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'timeout_djs':
            # 倒计时结束或者手动点击继续，保存字幕区字幕到 self.wait_subtitle
            self.main.stop_djs.hide()
            self.main.continue_compos.setDisabled(True)
            self.main.subtitle_area.setReadOnly(True)
            self.update_subtitle()

        elif d['type'] == 'check_soft_update':
            if not self.update_btn:
                self.update_btn = QPushButton()
                self.update_btn.setStyleSheet('color:#ffff00;border:0')
                self.update_btn.setCursor(QtCore.Qt.PointingHandCursor)
                self.update_btn.clicked.connect(lambda: self.open_url('download'))
                self.main.container.addWidget(self.update_btn)
            self.update_btn.setText(d['text'])
        elif d['type'] == 'set_clone_role' and self.main.tts_type.currentText() == 'clone-voice':
            if config.current_status == 'ing':
                return
            current = self.main.voice_role.currentText()
            self.main.voice_role.clear()
            self.main.voice_role.addItems(config.params["clone_voicelist"])
            self.main.voice_role.setCurrentText(current)

    # update subtitle 手动 点解了 立即合成按钮，或者倒计时结束超时自动执行
    def update_subtitle(self):
        self.main.stop_djs.hide()
        self.main.continue_compos.setDisabled(True)
        txt = self.main.subtitle_area.toPlainText().strip()
        txt = re.sub(r':\d+\.\d+', lambda m: m.group().replace('.', ','), txt, re.S | re.M)
        config.task_countdown = 0
        if not txt:
            return

        # 是单个视频执行时
        if not self.task.is_batch and self.wait_subtitle:
            # 不是批量才允许更新字幕
            Path(self.wait_subtitle).write_text(txt, encoding='utf-8')
        if self.edit_subtitle_type == 'edit_subtitle_source':
            self.main.subtitle_area.clear()
        return True

    # 设置每行角色
    def set_line_role_fun(self):
        def get_checked_boxes(widget):
            checked_boxes = []
            for child in widget.children():
                if isinstance(child, QtWidgets.QCheckBox) and child.isChecked():
                    checked_boxes.append(child.objectName())
                else:
                    checked_boxes.extend(get_checked_boxes(child))
            return checked_boxes

        def save(role):
            # 初始化一个列表，用于存放所有选中 checkbox 的名字
            checked_checkbox_names = get_checked_boxes(linerolew)

            if len(checked_checkbox_names) < 1:
                return QtWidgets.QMessageBox.critical(linerolew, config.transobj['anerror'],
                                                      config.transobj['zhishaoxuanzeyihang'])

            for n in checked_checkbox_names:
                _, line = n.split('_')
                # 设置labe为角色名
                ck = linerolew.findChild(QtWidgets.QCheckBox, n)
                ck.setText(config.transobj['default'] if role in ['No', 'no', '-'] else role)
                ck.setChecked(False)
                config.params['line_roles'][line] = config.params['voice_role'] if role in ['No', 'no', '-'] else role
            linerolew.close()

        from videotrans.component import SetLineRole
        linerolew = config.child_forms.get('linerolew')
        if linerolew is not None:
            linerolew.show()
            linerolew.raise_()
            linerolew.activateWindow()
            return
        linerolew = SetLineRole()
        config.child_forms['linerolew'] = linerolew
        box = QtWidgets.QWidget()
        box.setLayout(QtWidgets.QVBoxLayout())
        if config.params['voice_role'].lower() in ['-', 'no']:
            return QtWidgets.QMessageBox.critical(linerolew, config.transobj['anerror'],
                                                  config.transobj['xianxuanjuese'])
        if not self.main.subtitle_area.toPlainText().strip():
            return QtWidgets.QMessageBox.critical(linerolew, config.transobj['anerror'],
                                                  config.transobj['youzimuyouset'])

        #  获取字幕
        srt_json = tools.get_subtitle_from_srt(self.main.subtitle_area.toPlainText().strip(), is_file=False)
        for it in srt_json:
            # 创建新水平布局
            h_layout = QtWidgets.QHBoxLayout()
            check = QtWidgets.QCheckBox()
            check.setText(
                config.params['line_roles'][f'{it["line"]}'] if f'{it["line"]}' in config.params['line_roles'] else
                config.transobj['default'])
            check.setObjectName(f'check_{it["line"]}')
            # 创建并配置 QLineEdit
            line_edit = QtWidgets.QLineEdit()
            line_edit.setPlaceholderText(config.transobj['shezhijueseline'])

            line_edit.setText(f'[{it["line"]}] {it["text"]}')
            line_edit.setReadOnly(True)
            # 将标签和编辑线添加到水平布局
            h_layout.addWidget(check)
            h_layout.addWidget(line_edit)
            box.layout().addLayout(h_layout)
        box.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        linerolew.select_role.addItems(self.main.current_rolelist)
        linerolew.set_role_label.setText(config.transobj['shezhijuese'])

        linerolew.select_role.currentTextChanged.connect(save)
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(box)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 将 QScrollArea 添加到主窗口的 layout
        linerolew.layout.addWidget(scroll_area)
        linerolew.set_ok.clicked.connect(lambda: linerolew.close())
        linerolew.show()
