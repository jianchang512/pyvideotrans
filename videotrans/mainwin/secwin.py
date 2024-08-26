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

warnings.filterwarnings('ignore')
from videotrans.winform import zh_recogn, doubao, clone, ttsapi, gptsovits, cosyvoice, fishtts, chattts, ai302tts, azuretts


from videotrans.util import tools
from videotrans import translator
from videotrans.configure import config
from pathlib import Path
from videotrans.task.main_worker import Worker


class SecWindow():
    def __init__(self, main=None):
        self.main = main
        self.usetype = None
        self.edit_subtitle_type = ''

    def is_separate_fun(self, state):
        config.params['is_separate'] = True if state else False

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
        if res:
            os.environ['CUDA_OK'] = "yes"
        elif os.environ.get('CUDA_OK'):
            os.environ.pop('CUDA_OK')

    # 配音速度改变时，更改全局
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
        self.main.translate_type.setCurrentText('FreeGoogle' if config.defaulelang == 'zh' else 'Google')
        self.hide_show_element(self.main.layout_translate_type, False)
        # 代理
        self.hide_show_element(self.main.layout_proxy, False)
        # 原始语言
        self.hide_show_element(self.main.layout_source_language, True)
        # 目标语言
        self.hide_show_element(self.main.layout_target_language, True)
        # 配音角色
        self.main.tts_type.setCurrentText('edgeTTS')
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

        # 隐藏音量 音调变化
        self.hide_show_element(self.main.edge_volume_layout, False)

        # 配音语速

        self.hide_show_element(self.main.layout_voice_rate, False)
        # 静音片段
        # 配音自动加速
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
        # 配音自动加速
        # 视频自动降速
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

        # 配音自动加速
        # 视频自动降速
        self.main.is_separate.setDisabled(True)
        self.main.addbackbtn.setDisabled(True)
        self.main.only_video.setDisabled(True)
        self.main.back_audio.setReadOnly(True)
        # self.main.auto_ajust.setDisabled(True)
        self.main.video_autorate.setDisabled(True)
        self.main.voice_autorate.setDisabled(True)
        self.main.append_video.setDisabled(True)

        self.main.append_video.hide()
        self.main.voice_autorate.hide()
        self.main.is_separate.hide()
        self.main.addbackbtn.hide()
        self.main.back_audio.hide()
        self.main.only_video.hide()
        # self.main.auto_ajust.hide()
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

    # 删除proce里的元素
    def delete_process(self):
        for i in range(self.main.processlayout.count()):
            item = self.main.processlayout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.main.processbtns = {}

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

    def export_sub_fun(self):
        srttxt = self.main.subtitle_area.toPlainText().strip()
        if not srttxt:
            return

        dialog = QFileDialog()
        dialog.setWindowTitle(config.transobj['savesrtto'])
        dialog.setNameFilters(["subtitle files (*.srt)"])
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.exec_()
        if not dialog.selectedFiles():  # If the user closed the choice window without selecting anything.
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
        import webbrowser
        if title == 'blog':
            webbrowser.open_new_tab("https://bbs.pyvideotrans.com/questions")
        elif title == 'ffmpeg':
            webbrowser.open_new_tab("https://www.ffmpeg.org/download.html")
        elif title == 'git':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans")
        elif title == 'issue':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/issues")
        elif title == 'discord':
            webbrowser.open_new_tab("https://discord.gg/7ZWbwKGMcx")
        elif title == 'models':
            webbrowser.open_new_tab("https://github.com/jianchang512/stt/releases/tag/0.0")
        elif title == 'dll':
            webbrowser.open_new_tab("https://github.com/jianchang512/stt/releases/tag/v0.0.1")
        elif title == 'gtrans':
            webbrowser.open_new_tab("https://pyvideotrans.com/15.html")
        elif title == 'cuda':
            webbrowser.open_new_tab("https://pyvideotrans.com/gpu.html")
        elif title in ('website', 'help'):
            webbrowser.open_new_tab("https://pyvideotrans.com")
        elif title == 'xinshou':
            webbrowser.open_new_tab("https://pyvideotrans.com/getstart")
        elif title == "about":
            webbrowser.open_new_tab("https://pyvideotrans.com/about")
        elif title == 'download':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/releases")
        elif title == 'openvoice':
            webbrowser.open_new_tab("https://github.com/kungful/openvoice-api")
        elif title == 'online':
            self.about()

    # 将倒计时设为立即超时
    def set_djs_timeout(self):
        config.task_countdown = 0
        self.main.continue_compos.setText(config.transobj['jixuzhong'])
        self.main.continue_compos.setDisabled(True)
        self.main.stop_djs.hide()
        if self.main.shitingobj:
            self.main.shitingobj.stop = True
        self.update_subtitle()

    # 手动点击停止自动合并倒计时
    def reset_timeid(self):
        self.main.stop_djs.hide()
        config.task_countdown = 86400
        self.main.continue_compos.setDisabled(False)
        self.main.continue_compos.setText(config.transobj['nextstep'])
        self.update_data('{"type":"allow_edit"}')

    # 翻译渠道变化时，检测条件
    def set_translate_type(self, name):
        try:
            rs = translator.is_allow_translate(translate_type=name, only_key=True,win=self.main)
            if rs is not True:
                return False
                # QMessageBox.critical(self.main, config.transobj['anerror'], rs)
                # if name == translator.TRANSAPI_NAME:
                #     transapi.open()
                # elif name == translator.CHATGPT_NAME:
                #     chatgpt.open()
                # elif name == translator.AI302_NAME:
                #     ai302.open()
                # elif name == translator.LOCALLLM_NAME:
                #     localllm.open()
                # elif name == translator.GEMINI_NAME:
                #     gemini.open()
                # elif name == translator.AZUREGPT_NAME:
                #     azure.open()
                # elif name == translator.BAIDU_NAME:
                #     baidu.open()
                # elif name == translator.TENCENT_NAME:
                #     tencent.open()
                # elif name == translator.DEEPL_NAME:
                #     deepL.open()
                # elif name == translator.DEEPLX_NAME:
                #     deepLX.open()
                # elif name == translator.OTT_NAME:
                #     ott.open()
                # elif name == translator.ZIJIE_NAME:
                #     zijiehuoshan.open()
                # return
            config.params['translate_type'] = name
        except Exception as e:
            QMessageBox.critical(self.main, config.transobj['anerror'], str(e))

    # 0=整体识别模型
    # 1=预先分割模式
    def check_whisper_type(self, index):
        if index == 0:
            config.params['whisper_type'] = 'all'
        else:
            config.params['whisper_type'] = 'avg'

    # 设定模型类型
    def model_type_change(self):
        if self.main.model_type.currentIndex() == 1:
            config.params['model_type'] = 'openai'
            self.main.whisper_model.setDisabled(False)
            self.main.whisper_type.setDisabled(True)
            self.check_whisper_model(self.main.whisper_model.currentText())
        elif self.main.model_type.currentIndex() == 2:
            config.params['model_type'] = 'GoogleSpeech'
            self.main.whisper_model.setDisabled(True)
            self.main.whisper_type.setDisabled(True)
        elif self.main.model_type.currentIndex() == 3:
            lang = self.main.source_language.currentText()
            if translator.get_code(show_text=lang) not in ['zh-cn', 'zh-tw']:
                self.main.model_type.setCurrentIndex(0)
                return QMessageBox.critical(self.main, config.transobj['anerror'],
                                            'zh_recogn 仅支持中文语音识别' if config.defaulelang == 'zh' else 'zh_recogn Supports Chinese speech recognition only')

            config.params['model_type'] = 'zh_recogn'
            self.main.whisper_model.setDisabled(True)
            self.main.whisper_type.setDisabled(True)
            if not config.params['zh_recogn_api']:
                zh_recogn.open()
        elif self.main.model_type.currentIndex() == 4:
            lang = self.main.source_language.currentText()
            langcode = translator.get_code(show_text=lang)
            if not langcode or langcode[:2] not in ["zh", "en", "ja", "ko", "fr", "es", "ru"]:
                self.main.model_type.setCurrentIndex(0)
                return QMessageBox.critical(self.main, config.transobj['anerror'], '豆包语音识别仅支持中英日韩法俄西班牙语言，其他不支持')
            config.params['model_type'] = 'doubao'
            self.main.whisper_model.setDisabled(True)
            self.main.whisper_type.setDisabled(True)
            if not config.params['doubao_appid']:
                doubao.open()
        else:
            self.main.whisper_type.setDisabled(False)
            self.main.whisper_model.setDisabled(False)
            config.params['model_type'] = 'faster'
            self.check_whisper_model(self.main.whisper_model.currentText())

    # 判断模型是否存在
    def check_whisper_model(self, name):
        if self.main.model_type.currentIndex() in [2, 3]:
            return True
        if name.find('/') > 0:
            return True
        slang = self.main.source_language.currentText()
        if name.endswith('.en') and translator.get_code(show_text=slang) != 'en':
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['enmodelerror'])
            return False
        if config.params['model_type'] == 'openai':
            if name.startswith('distil'):
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['openaimodelerror'])
                return False
            if not Path(config.rootdir + f"/models/{name}.pt").exists():
                QMessageBox.critical(self.main, config.transobj['anerror'],
                                     config.transobj['openaimodelnot'].replace('{name}', name))
                return False
            return True
        file = f'{config.rootdir}/models/models--Systran--faster-whisper-{name}/snapshots'
        if name.startswith('distil'):
            file = f'{config.rootdir}/models/models--Systran--faster-{name}/snapshots'

        if not Path(file).exists():
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 config.transobj['downloadmodel'].replace('{name}', name))
            return False

        return True

    def clearcache(self):
        if config.defaulelang == 'zh':
            question = tools.show_popup('确认进行清理？', '清理后需要重启软件并重新填写设置菜单中各项配置信息')

        else:
            question = tools.show_popup('Confirm cleanup?', 'The software needs to be restarted after cleaning')

        if question == QMessageBox.Yes:
            shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
            shutil.rmtree(config.homedir + "/tmp", ignore_errors=True)
            tools.remove_qsettings_data()
            QMessageBox.information(self.main, 'Please restart the software' if config.defaulelang != 'zh' else '请重启软件',
                                    'Please restart the software' if config.defaulelang != 'zh' else '软件将自动关闭，请重新启动，设置中各项配置信息需重新填写')
            self.main.close()

    # 是 edgeTTS AzureTTS 或 302.ai同时 ai302tts_model=azure
    def isMircosoft(self, type):
        if type in ['edgeTTS', 'AzureTTS']:
            return True
        if type == '302.ai' and config.params['ai302tts_model'] == 'azure':
            return True
        if type == '302.ai' and config.params['ai302tts_model'] == 'doubao':
            return True
        return False

    # tts类型改变
    def tts_type_change(self, type):

        self.hide_show_element(self.main.edge_volume_layout, self.isMircosoft(type))
        if  type == 'clone-voice' and config.params['voice_role'] == 'clone':
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj[
                'Clone voice cannot be used in subtitle dubbing mode as there are no replicable voices'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            clone.open()
            return
        if type == 'TTS-API' and not config.params['ttsapi_url']:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['ttsapi_nourl'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            ttsapi.open()
            return
        if type == 'GPT-SoVITS' and not config.params['gptsovits_url']:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['nogptsovitsurl'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            gptsovits.open()
            return
        if type == 'CosyVoice' and not config.params['cosyvoice_url']:
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 'You must deploy the CosyVoice-api project and start the api service, then fill in the api address' if config.defaulelang != 'zh' else '必须部署CosyVoice-api项目并启动api服务，然后填写api地址')
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            cosyvoice.open()
            return
        if type == 'FishTTS' and not config.params['fishtts_url']:
            QMessageBox.critical(self.main, config.transobj['anerror'], '必须填写FishTTS的api地址')
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            fishtts.open()
            return
        if type == 'ChatTTS' and not config.params['chattts_api']:
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            chattts.open()
            return
        if type == '302.ai' and not config.params['ai302tts_key']:
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            ai302tts.open()
            return

        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if lang and lang != '-':
            if type == 'GPT-SoVITS' and lang[:2] not in ['zh', 'ja', 'en']:
                self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['nogptsovitslanguage'])
                return
            if type == 'CosyVoice' and lang[:2] not in ['zh', 'ja', 'en', 'ko']:
                self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
                QMessageBox.critical(self.main, config.transobj['anerror'],
                                     'CosyVoice only supports Chinese, English, Japanese and Korean' if config.defaulelang == 'zh' else '')
                return
            if type == 'ChatTTS' and lang[:2] not in ['zh', 'en']:
                self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['onlycnanden'])
                return
            if type == 'FishTTS' and lang[:2] not in ['zh', 'ja', 'en']:
                self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['onlycnanden'])
                return
            if type == '302.ai' and config.params['ai302tts_model'] == 'doubao' and lang[:2] not in ['zh', 'ja', 'en']:
                self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
                QMessageBox.critical(self.main, config.transobj['anerror'], '302.ai选择doubao模型时仅支持中英日文字配音')
                return

        config.params['tts_type'] = type
        config.params['line_roles'] = {}
        if type == 'gtts':
            self.main.voice_role.clear()
            self.main.current_rolelist = ["gtts"]
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == "openaiTTS":
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['openaitts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)

        elif type == 'elevenlabsTTS':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['elevenlabstts_role']
            if len(self.main.current_rolelist) < 1:
                self.main.current_rolelist = tools.get_elevenlabs_role()
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif self.isMircosoft(type):
            if type == "AzureTTS" and (
                    not config.params['azure_speech_key'] or not config.params['azure_speech_region']):
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['azureinfo'])
                azuretts.open()
                return
            self.set_voice_role(self.main.target_language.currentText())
        elif type == "302.ai":
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['ai302tts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == 'clone-voice':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params["clone_voicelist"]
            self.main.voice_role.addItems(self.main.current_rolelist)
            threading.Thread(target=tools.get_clone_role).start()
        elif type == 'ChatTTS':
            self.main.voice_role.clear()
            self.main.current_rolelist = list(config.ChatTTS_voicelist)
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == 'TTS-API':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['ttsapi_voice_role'].strip().split(',')
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == 'GPT-SoVITS':
            rolelist = tools.get_gptsovits_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['GPT-SoVITS']
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == 'CosyVoice':
            rolelist = tools.get_cosyvoice_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['clone']
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == 'FishTTS':
            rolelist = tools.get_fishtts_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['FishTTS']
            self.main.voice_role.addItems(self.main.current_rolelist)

    # 试听配音
    def listen_voice_fun(self):
        lang = translator.get_code(show_text=self.main.target_language.currentText())
        text = config.params[f'listen_text_{lang}']
        role = self.main.voice_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['mustberole'])
        voice_dir = os.environ.get('APPDATA') or os.environ.get('appdata')
        if not voice_dir or not Path(voice_dir).exists():
            voice_dir = config.rootdir + "/tmp/voice_tmp"
        else:
            voice_dir = voice_dir.replace('\\', '/') + "/pyvideotrans"
        if not Path(voice_dir).exists():
            Path(voice_dir).mkdir(parents=True, exist_ok=True)
        lujing_role = role.replace('/', '-')
        volume = int(self.main.volume_rate.value())
        pitch = int(self.main.pitch_rate.value())
        voice_file = f"{voice_dir}/{config.params['tts_type']}-{lang}-{lujing_role}-{volume}-{pitch}.mp3"
        if config.params['tts_type'] in ['GPT-SoVITS', 'CosyVoice', 'ChatTTS', 'FishTTS']:
            voice_file += '.wav'

        obj = {
            "text": text,
            "rate": "+0%",
            "role": role,
            "voice_file": voice_file,
            "tts_type": config.params['tts_type'],
            "language": lang,
            "volume": f'+{volume}%' if volume > 0 else f'{volume}%',
            "pitch": f'+{pitch}Hz' if pitch > 0 else f'{pitch}Hz',
        }
        if role == 'clone':
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 '原音色克隆不可试听' if config.defaulelang == 'zh' else 'The original sound clone cannot be auditioned')
            return

        def feed(d):
            QMessageBox.critical(self.main, config.transobj['anerror'], d)

        from videotrans.task.play_audio import PlayMp3
        t = PlayMp3(obj, self.main)
        t.mp3_ui.connect(feed)
        t.start()

    # 角色改变时 显示试听按钮
    def show_listen_btn(self, role):
        config.params["voice_role"] = role
        if role == 'No' or (config.params['tts_type'] == 'clone-voice' and config.params['voice_role'] == 'clone'):
            self.main.listen_btn.hide()
            return
        if self.main.app_mode in ['biaozhun']:
            self.main.listen_btn.show()
            self.main.listen_btn.setDisabled(False)

    # 目标语言改变时设置配音角色
    def set_voice_role(self, t):
        role = self.main.voice_role.currentText()
        # 如果tts类型是 openaiTTS，则角色不变
        # 是edgeTTS时需要改变
        code = translator.get_code(show_text=t)
        if code and code != '-':
            if config.params['tts_type'] == 'GPT-SoVITS' and code[:2] not in ['zh', 'ja', 'en']:
                # 除此指望不支持
                config.params['tts_type'] = 'edgeTTS'
                self.main.tts_type.setCurrentText('edgeTTS')
                return QMessageBox.critical(self.main, config.transobj['anerror'],
                                            config.transobj['nogptsovitslanguage'])
            if config.params['tts_type'] == 'CosyVoice' and code[:2] not in ['zh', 'ja', 'en',
                                                                             'ko']:
                # 除此指望不支持
                config.params['tts_type'] = 'edgeTTS'
                self.main.tts_type.setCurrentText('edgeTTS')
                return QMessageBox.critical(self.main, config.transobj['anerror'],
                                            'CosyVoice仅支持中英日韩四种语言' if config.defaulelang == 'zh' else 'CosyVoice only supports Chinese, English, Japanese and Korean')
            if config.params['tts_type'] == 'FishTTS' and code[:2] not in ['zh', 'ja', 'en']:
                # 除此指望不支持
                config.params['tts_type'] = 'edgeTTS'
                self.main.tts_type.setCurrentText('edgeTTS')
                return QMessageBox.critical(self.main, config.transobj['anerror'], 'FishTTS仅可用于中日英配音')
            if config.params['tts_type'] == 'ChatTTS' and code[:2] not in ['zh', 'en']:
                # 除此指望不支持
                config.params['tts_type'] = 'edgeTTS'
                self.main.tts_type.setCurrentText('edgeTTS')
                return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['onlycnanden'])
            if config.params['tts_type'] == '302.ai' and config.params['ai302tts_model'] == 'doubao' and code[
                                                                                                         :2] not in [
                'zh', 'ja', 'en']:
                config.params['tts_type'] = 'edgeTTS'
                self.main.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(self.main, config.transobj['anerror'], '302.ai选择doubao模型时仅支持中英日文字配音')
                return

        # 除 edgeTTS外，其他的角色不会随语言变化
        if not self.isMircosoft(config.params['tts_type']):
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
        if config.params['tts_type'] == 'edgeTTS':
            show_rolelist = tools.get_edge_rolelist()
        elif config.params['tts_type'] == '302.ai' and config.params['ai302tts_model'] == 'doubao':
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

        file_types="Video files(*.mp4 *.avi *.mov *.mpg *.mkv)"
        if self.main.app_mode=='tiqu':
            file_types="Video files(*.mp4 *.avi *.mov *.mpg *.mkv *.wav *.mp3 *.m4a *.aac *.flac)"

        fnames, _ = QFileDialog.getOpenFileNames(self.main, config.transobj['selectmp4'], config.params['last_opendir'], file_types)
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/')

        if len(fnames) > 0:
            self.main.source_mp4.setText(f'{len((fnames))} videos')
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            config.queue_mp4 = fnames

    # 导入背景声音
    def get_background(self):
        fname, _ = QFileDialog.getOpenFileName(self.main, 'Background music', config.params['last_opendir'],  "Audio files(*.mp3 *.wav *.flac)")
        if not fname:
            return
        fname = fname.replace('\\', '/')
        self.main.back_audio.setText(fname)

    # 从本地导入字幕文件
    def import_sub_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self.main, config.transobj['selectmp4'], config.params['last_opendir'],   "Srt files(*.srt *.txt)")
        if fname:
            content = ""
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                with open(fname, 'r', encoding='gbk') as f:
                    content = f.read()
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
        dirname = dirname.replace('\\', '/')
        self.main.target_dir.setText(dirname)

    # 添加进度条
    def add_process_btn(self, target_dir=None):
        clickable_progress_bar = ClickableProgressBar(self)
        clickable_progress_bar.progress_bar.setValue(0)  # 设置当前进度值
        clickable_progress_bar.setText(config.transobj["waitforstart"])
        clickable_progress_bar.setMinimumSize(500, 50)
        # # 将按钮添加到布局中
        if target_dir:
            clickable_progress_bar.setTarget(target_dir)
            clickable_progress_bar.setCursor(Qt.PointingHandCursor)
        self.main.processlayout.addWidget(clickable_progress_bar)
        return clickable_progress_bar

    # 检测各个模式下参数是否设置正确
    def set_mode(self):
        if self.main.app_mode == 'tiqu' or (self.main.app_mode.startswith('biaozhun') and config.params['subtitle_type'] < 1 and config.params['voice_role'] == 'No' ):
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

    #
    # 判断是否需要翻译
    # 0 peiyin模式无需翻译，heibng模式无需翻译
    # 1. 不存在视频，则是字幕创建配音模式，无需翻译
    # 2. 不存在目标语言，无需翻译
    # 3. 原语言和目标语言相同，不需要翻译
    # 4. 存在字幕，不需要翻译
    # 是否无需翻译，返回True=无需翻译,False=需要翻译
    def shound_translate(self):
        if len(config.queue_mp4) < 1:
            return False
        if self.main.target_language.currentText() == '-' or self.main.source_language.currentText() == '-':
            return False
        if self.main.target_language.currentText() == self.main.source_language.currentText():
            return False

        return True

    def change_proxy(self, p):
        # 设置或删除代理
        config.params['proxy'] = p.strip()
        try:
            if not config.params['proxy']:
                # 删除代理
                tools.set_proxy('del')
        except Exception:
            pass

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

    def check_tts(self):
        if config.params['tts_type'] == 'openaiTTS' and not config.params["chatgpt_key"]:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['chatgptkeymust'])
            return False
        if config.params['tts_type'] == '302.ai' and not config.params["ai302tts_key"]:
            QMessageBox.critical(self.main, config.transobj['anerror'], '必须设置302.ai的API KEY')
            return False
        if config.params['tts_type'] == 'clone-voice' and not config.params["clone_api"]:
            config.logger.error(f"不存在clone-api:{config.params['tts_type']=},{config.params['clone_api']=}")
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['bixutianxiecloneapi'])
            return False
        if config.params['tts_type'] == 'elevenlabsTTS' and not config.params["elevenlabstts_key"]:
            QMessageBox.critical(self.main, config.transobj['anerror'], "no elevenlabs  key")
            return False
        # 如果没有选择目标语言，但是选择了配音角色，无法配音
        if config.params['target_language'] == '-' and config.params['voice_role'] != 'No':
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['wufapeiyin'])
            return False
        return True

    # 核对字幕
    def check_txt(self,txt=''):
        if txt and not re.search(r'\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?\s*?-->\s*?\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?', txt):
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 '字幕格式不正确，请重新导入字幕或删除已导入字幕' if config.defaulelang == 'zh' else 'Subtitle format is not correct, please re-import the subtitle or delete the imported subtitle.')
            return False
        return True

    # 检测开始状态并启动
    def check_start(self):
        self.edit_subtitle_type = ''
        if config.current_status == 'ing':
            # 停止
            question = tools.show_popup(config.transobj['exit'], config.transobj['confirmstop'])
            if question == QMessageBox.Yes:
                self.update_status('stop')
                return
        # 无视频选择 ，也无导入字幕，无法处理
        if len(config.queue_mp4) < 1:
            QMessageBox.critical(self.main, config.transobj['anerror'], '必须选择视频文件' if config.defaulelang=='zh' else 'Video file must be selected')
            return False

        if self.check_proxy() is not True:
            return

        config.task_countdown = int(config.settings['countdown_sec'])
        config.settings = config.parse_init()

        # 目标文件夹
        target_dir = self.main.target_dir.text().strip().replace('\\', '/')
        config.params['target_dir'] = target_dir if target_dir else ''

        # 原始语言
        config.params['source_language'] = self.main.source_language.currentText()
        langcode = translator.get_code(show_text=config.params['source_language'])
        if self.main.model_type.currentIndex == 3 and langcode[:2] != 'zh':
            self.update_status('stop')
            return QMessageBox.critical(
                self.main, config.transobj['anerror'],
                'zh_recogn 仅支持中文语音识别' if config.defaulelang == 'zh' else 'zh_recogn Supports Chinese speech recognition only')

        if self.main.model_type.currentIndex == 3 and not config.params['zh_recogn_api']:
            return QMessageBox.critical(self.main, config.transobj['anerror'],
                                        'zh_recogn 必须在设置-zh_recogn中填写http接口地址' if config.defaulelang == 'zh' else 'The http interface address must be filled in the settings-zh_recogn')

        if self.main.model_type.currentIndex == 4:
            if not config.params['doubao_appid']:
                return QMessageBox.critical(self.main, config.transobj['anerror'], '必须填写豆包应用APP ID')
            if langcode and langcode[:2] not in ["zh", "en", "ja", "ko", "es", "fr", "ru"]:
                return QMessageBox.critical(self.main, config.transobj['anerror'], '豆包语音识别仅支持中英日韩法俄西班牙语言，其他不支持')

        # 目标语言
        target_language = self.main.target_language.currentText()
        config.params['target_language'] = target_language

        # 配音角色
        config.params['voice_role'] = self.main.voice_role.currentText()
        if config.params['voice_role'] == 'No':
            config.params['is_separate'] = False

        # 配音自动加速
        config.params['voice_autorate'] = self.main.voice_autorate.isChecked()
        config.params['append_video'] = self.main.append_video.isChecked()

        # 语音模型
        config.params['whisper_model'] = self.main.whisper_model.currentText()
        model_index = self.main.model_type.currentIndex()
        if model_index == 1:
            config.params['model_type'] = 'openai'
        elif model_index == 2:
            config.params['model_type'] = 'GoogleSpeech'
        elif model_index == 3:
            config.params['model_type'] = 'zh_recogn'
        elif model_index == 4:
            config.params['model_type'] = 'doubao'
        else:
            config.params['model_type'] = 'faster'

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
        config.params['translate_type'] = self.main.translate_type.currentText()
        config.params['clear_cache'] = True if self.main.clear_cache.isChecked() else False
        config.params['only_video'] = self.main.only_video.isChecked()


        # 如果需要翻译，再判断是否符合翻译规则
        if self.shound_translate():
            rs = translator.is_allow_translate(
                translate_type=config.params['translate_type'],
                show_target=config.params['target_language'])
            if rs is not True:
                # 不是True，有错误
                # QMessageBox.critical(self.main, config.transobj['anerror'], rs)
                return False


        # 字幕区文字
        txt = self.main.subtitle_area.toPlainText().strip()
        if self.check_txt(txt) is not True:
            return
        # tts类型
        if self.check_tts() is not True:
            return
        # 检查模式是否正确
        self.set_mode()

        # 除了 peiyin  hebing模式，其他均需要检测模型是否存在
        if not txt and config.params['model_type'] in ['openai', 'faster'] and not self.check_whisper_model(config.params['whisper_model']):
            return False

        if self.cuda_isok() is not  True:
            return


        if self.url_right() is not True:
            return


        if self.check_name() is not True:
            return

        self.main.save_setting()
        self.update_status('ing')
        self.delete_process()

        config.settings = config.parse_init()
        if self.main.app_mode in ['biaozhun_jd', 'biaozhun', 'tiqu']:
            config.params['app_mode'] = self.main.app_mode
        config.getset_params(config.params)
        self.main.task = Worker(parent=self.main, app_mode=self.main.app_mode, txt=txt)
        self.main.task.start()

        for k, v in self.main.moshis.items():
            if k != self.main.app_mode:
                v.setDisabled(True)

    # 如果选中了cuda，判断是否可用
    def cuda_isok(self):
        if config.params["cuda"] and platform.system() != 'Darwin':
            import torch
            if not torch.cuda.is_available():
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocuda"])
                return False
            if config.params['model_type'] == 'faster':
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

    # 判断路径是否正确
    def url_right(self):
            for vurl in config.queue_mp4:
                if re.search(r'[:\?\*<>\|\"\']', vurl[4:]):
                    return QMessageBox.critical(self.main, config.transobj['anerror'],
                           '视频所在路径和视频名字中不可含有  :  * ? < > | " \' 符号，请修正 ' if config.defaulelang == 'zh' else 'The path and name of the video must not contain the  : * ? < > | " \' symbols, please revise. ')
                if len(vurl)>255 and sys.platform=='win32':
                    return QMessageBox.critical(self.main, config.transobj['anerror'],f'视频路径总长度超过255个字符，处理中可能会出错，请改短视频文件名，并移动到浅层目录下url={vurl}' if config.defaulelang=='zh' else f'The total length of the video path is more than 255 characters, there may be an error in processing, please change the short video file name and move it to a shallow directoryurl={vurl}')
            return True

    # 如果存在音频则设为提取
    # 如果有同名则停止
    def check_name(self):
        if self.main.app_mode !='tiqu':
            for it in  config.queue_mp4:
                if Path(it).suffix.lower() in ['.wav','.aac','.m4a','.flac','mp3']:
                    self.main.app_mode = 'tiqu'
                    config.params['is_separate'] = False
                    break

        if len(config.queue_mp4)>1:
            same_name={}
            for it in config.queue_mp4:
                p=Path(it)
                stem=p.stem
                if stem in same_name:
                    same_name[stem].append(p.name)
                else:
                    same_name[stem]=[p.name]
            msg=''
            for it in same_name.values():
                if len(it)>1:
                    msg+=",".join(it)
            if msg:
                 QMessageBox.critical(self.main, config.transobj['anerror'],
                          f'不可含有名字相同但后缀不同的文件，会导致混淆，请修改 {msg} ' if config.defaulelang == 'zh' else f'Do not include files with the same name but different extensions, this can lead to confusion, please modify {msg} ')
                 return False
        return True

    # 设置按钮上的日志信息
    def set_process_btn_text(self, text, btnkey="", type="logs"):
        if not btnkey or btnkey not in self.main.processbtns:
            return
        if not self.main.task:
            return
        precent = round(self.main.task.tasklist[
                            btnkey].precent if self.main.task.tasklist and btnkey in self.main.task.tasklist else 0, 1)
        if type == 'succeed' or precent >= 100.0:
            target = self.main.task.tasklist[btnkey].obj['output']
            basename = self.main.task.tasklist[btnkey].obj['raw_basename']

            self.main.processbtns[btnkey].setTarget(target)
            self.main.processbtns[btnkey].setCursor(Qt.PointingHandCursor)

            text = f'{config.transobj["endandopen"]} {basename}'
            self.main.processbtns[btnkey].setText(text)
            self.main.processbtns[btnkey].progress_bar.setValue(100)
            self.main.processbtns[btnkey].setToolTip(config.transobj['mubiao'])
        elif type == 'error' or type == 'stop':
            self.main.processbtns[btnkey].progress_bar.setStyleSheet('color:#ff0000')
            if type == 'error':
                self.main.processbtns[btnkey].setCursor(Qt.PointingHandCursor)
                self.main.processbtns[btnkey].setMsg(
                    text + f'\n\n{config.errorlist[btnkey] if btnkey in config.errorlist and config.errorlist[btnkey] != text else ""}'
                )
                self.main.processbtns[btnkey].setToolTip(
                    '点击查看详细报错' if config.defaulelang == 'zh' else 'Click to view the detailed error report')
                self.main.processbtns[btnkey].setText(text[:120])
            else:
                self.main.processbtns[btnkey].setToolTip('')
        elif btnkey in self.main.task.tasklist:
            jindu = f' {precent}% '
            self.main.processbtns[btnkey].progress_bar.setValue(int(self.main.task.tasklist[btnkey].precent))
            raw_name = self.main.task.tasklist[btnkey].obj['raw_basename']
            self.main.processbtns[btnkey].setToolTip(config.transobj["endopendir"])

            self.main.processbtns[btnkey].setText(
                f'{config.transobj["running"].replace("..", "")} [{jindu}] {raw_name} / {config.transobj["endopendir"]} {text}')

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
            # 启用
            self.disabled_widget(False)
            for k, v in self.main.moshis.items():
                v.setDisabled(False)
            if type == 'end':
                # 成功完成
                self.main.source_mp4.setText(config.transobj["No select videos"])
                # 关机
                if self.main.shutdown.isChecked():
                    try:
                        tools.shutdown_system()
                    except Exception as e:
                        QMessageBox.critical(self.main, config.transobj['anerror'],
                                             config.transobj['shutdownerror'] + str(e))
            else:
                # 停止
                self.main.continue_compos.hide()
                self.main.target_dir.clear()
                self.main.source_mp4.setText(config.transobj["No select videos"] if len(
                    config.queue_mp4) < 1 else f'{len(config.queue_mp4)} videos')
                # 清理输入
            self.main.source_mp4.setText(config.transobj["No select videos"])
            if self.main.task:
                self.main.task.requestInterruption()
                self.main.task.quit()
                self.main.task = None
            if self.main.app_mode == 'tiqu':
                self.set_tiquzimu()
        else:
            # 重设为开始状态
            self.disabled_widget(True)
            self.main.startbtn.setText(config.transobj["starting..."])

    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        if d['type'] == 'alert':
            QMessageBox.critical(self.main, config.transobj['anerror'], d['text'])
            return

        # 一行一行插入字幕到字幕编辑区
        elif d['type'] == 'set_start_btn':
            self.main.startbtn.setText(config.transobj["running"])
        elif d['type'] == "subtitle":
            self.main.subtitle_area.moveCursor(QTextCursor.End)
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'add_process':
            self.main.processbtns[d['btnkey']] = self.add_process_btn(d['text'])
        elif d['type'] == 'rename':
            self.main.show_tips.setText(d['text'])
        elif d['type'] == 'set_target_dir':
            self.main.target_dir.setText(d['text'])
        elif d['type'] == "logs":
            self.set_process_btn_text(d['text'], btnkey=d['btnkey'])
        elif d['type'] == 'stop' or d['type'] == 'end' or d['type'] == 'error':
            if d['type'] == 'error':
                self.set_process_btn_text(d['text'], btnkey=d['btnkey'], type=d['type'])
            elif d['type'] == 'stop':
                self.main.subtitle_area.clear()
            if d['type'] == 'stop' or d['type'] == 'end':
                self.update_status(d['type'])
                self.main.continue_compos.hide()
                self.main.target_dir.clear()
                self.main.stop_djs.hide()
                self.main.export_sub.setDisabled(False)
                self.main.set_line_role.setDisabled(False)
        elif d['type'] == 'succeed':
            # 本次任务结束
            self.set_process_btn_text(d['text'], btnkey=d['btnkey'], type='succeed')
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
            self.main.stop_djs.hide()
            self.main.continue_compos.setDisabled(True)
            self.main.subtitle_area.setReadOnly(True)
            self.update_subtitle()
        elif d['type'] == 'show_djs':
            self.set_process_btn_text(d['text'], btnkey=d['btnkey'])
        elif d['type'] == 'check_soft_update':
            if not self.usetype:
                self.usetype = QPushButton()
                self.usetype.setStyleSheet('color:#ffff00;border:0')
                self.usetype.setCursor(QtCore.Qt.PointingHandCursor)
                self.usetype.clicked.connect(lambda: self.open_url('download'))
                self.main.container.addWidget(self.usetype)
            self.usetype.setText(d['text'])
        elif d['type'] == 'set_clone_role' and config.params['tts_type'] == 'clone-voice':
            if config.current_status == 'ing':
                return
            current = self.main.voice_role.currentText()
            self.main.voice_role.clear()
            self.main.voice_role.addItems(config.params["clone_voicelist"])
            self.main.voice_role.setCurrentText(current)
        elif d['type'] == 'win':
            # 小窗口背景音分离
            if config.separatew is not None:
                config.separatew.set.setText(d['text'])

    # update subtitle 手动 点解了 立即合成按钮，或者倒计时结束超时自动执行
    def update_subtitle(self):
        self.main.stop_djs.hide()
        self.main.continue_compos.setDisabled(True)
        # 如果当前是等待翻译阶段，则更新原语言字幕,然后清空字幕区
        txt = self.main.subtitle_area.toPlainText().strip()
        txt = re.sub(r':\d+\.\d+', lambda m: m.group().replace('.', ','), txt, re.S | re.M)
        config.task_countdown = 0
        if not txt:
            return

        if not self.main.task.is_batch and self.main.task.tasklist:
            tk = list(self.main.task.tasklist.values())[0]
            if self.edit_subtitle_type == 'edit_subtitle_source':
                srtfile = tk.init['source_sub']
            else:
                srtfile = tk.init['target_sub']
            # 不是批量才允许更新字幕
            with open(srtfile, 'w', encoding='utf-8') as f:
                f.write(txt)
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
            checked_checkbox_names = get_checked_boxes(config.linerolew)

            if len(checked_checkbox_names) < 1:
                return QtWidgets.QMessageBox.critical(config.linerolew, config.transobj['anerror'],
                                                      config.transobj['zhishaoxuanzeyihang'])

            for n in checked_checkbox_names:
                _, line = n.split('_')
                # 设置labe为角色名
                ck = config.linerolew.findChild(QtWidgets.QCheckBox, n)
                ck.setText(config.transobj['default'] if role in ['No', 'no', '-'] else role)
                ck.setChecked(False)
                config.params['line_roles'][line] = config.params['voice_role'] if role in ['No', 'no', '-'] else role

        from videotrans.component import SetLineRole
        config.linerolew = SetLineRole()
        box = QtWidgets.QWidget()  # 创建新的 QWidget，它将承载你的 QHBoxLayouts
        box.setLayout(QtWidgets.QVBoxLayout())  # 设置 QVBoxLayout 为新的 QWidget 的layout
        if config.params['voice_role'] in ['No', '-', 'no']:
            return QtWidgets.QMessageBox.critical(config.linerolew, config.transobj['anerror'],
                                                  config.transobj['xianxuanjuese'])
        if not self.main.subtitle_area.toPlainText().strip():
            return QtWidgets.QMessageBox.critical(config.linerolew, config.transobj['anerror'],
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
        config.linerolew.select_role.addItems(self.main.current_rolelist)
        config.linerolew.set_role_label.setText(config.transobj['shezhijuese'])

        config.linerolew.select_role.currentTextChanged.connect(save)
        # 创建 QScrollArea 并将 box QWidget 设置为小部件
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(box)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 将 QScrollArea 添加到主窗口的 layout
        config.linerolew.layout.addWidget(scroll_area)

        config.linerolew.set_ok.clicked.connect(lambda: config.linerolew.close())
        config.linerolew.show()
