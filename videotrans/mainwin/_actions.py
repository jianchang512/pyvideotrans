import copy
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFileDialog

from videotrans import translator, recognition, tts
from videotrans.configure import config
from videotrans.configure.config import tr,logs
from videotrans.mainwin._actions_sub import WinActionSub
from videotrans.task.simple_runnable_qt import run_in_threadpool
from videotrans.util import tools
from videotrans.component.onlyone_set_editdubb import EditDubbingResultDialog
from videotrans.component.onlyone_set_recogn import EditRecognResultDialog
from videotrans.component.onlyone_set_role import SpeakerAssignmentDialog
from videotrans.task.trans_create import TransCreate


@dataclass
class WinAction(WinActionSub):

    def _reset(self):
        # 存放需要处理的视频dict信息，包括uuid
        self.obj_list = []
        self.main.source_mp4.setText(tr("No select videos"))


    # 删除进度按钮
    def delete_process(self):
        for i in range(self.main.processlayout.count()):
            item = self.main.processlayout.itemAt(i)
            if item.widget():
                try:
                    item.widget().deleteLater()
                except Exception:
                    pass
        self.processbtns = {}

    # 将倒计时设为立即超时
    def set_djs_timeout(self):
        config.task_countdown = -1
        if self.had_click_btn:
            return
        self.had_click_btn=True
        self.main.subtitle_area.setReadOnly(True)
        self.had_click_btn=False



    # 翻译渠道变化时，检测条件
    def set_translate_type(self, idx):
        try:
            t = self.main.target_language.currentText()
            if t not in ['-']:
                rs = translator.is_allow_translate(translate_type=idx, show_target=t)
                if rs is not True:
                    return False
        except Exception as e:
            tools.show_error(str(e))

    def show_xxl_select(self):
        import sys
        if sys.platform != 'win32':
            tools.show_error(
                tr("faster-whisper-xxl.exe is only available on Windows"))
            return False
        xxl_path=config.settings.get('Faster_Whisper_XXL', '')  
        if not xxl_path or not Path(xxl_path).exists():
            from videotrans.component.set_xxl import SetFasterXXL
            dialog = SetFasterXXL()
            if dialog.exec():  # OK 按钮被点击时 exec 返回 True
                xxl_path = dialog.get_values()
                if xxl_path and Path(xxl_path).is_file():
                    return True
            tools.show_error(
                tr("Must be selected, otherwise it cannot be used"))
            return False
        return True
    def show_cpp_select(self):
        import sys
        cpp_path=config.settings.get('Whisper.cpp', '')
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


    # 语音识别方式改变时
    def recogn_type_change(self):
        recogn_type = self.main.recogn_type.currentIndex()
        if recogn_type == recognition.Faster_Whisper_XXL and not self.show_xxl_select():
            return
        if recogn_type == recognition.Whisper_CPP and not self.show_cpp_select():
            return
        if recogn_type != recognition.FASTER_WHISPER:
            self.main.split_type.setDisabled(True)
            self.main.split_type.setCurrentIndex(0)
        else:
            # 是 faster，启用 分割模式，根据需要显示均等分割
            self.main.split_type.setDisabled(False)

        if recogn_type not in [recognition.FASTER_WHISPER, recognition.OPENAI_WHISPER, recognition.Faster_Whisper_XXL,recognition.FUNASR_CN,recognition.Deepgram,recognition.Whisper_CPP,recognition.WHISPERX_API]:
            # 禁止模块选择
            self.main.model_name.setDisabled(True)
            self.main.model_name_help.setDisabled(True)
        else:
            # 允许模块选择
            self.main.model_name_help.setDisabled(False)
            self.main.model_name.setDisabled(False)
            self.main.model_name.clear()
            if recogn_type in [recognition.FASTER_WHISPER, recognition.OPENAI_WHISPER, recognition.Faster_Whisper_XXL,recognition.WHISPERX_API]:
                self.main.model_name.addItems(config.WHISPER_MODEL_LIST)
            elif recogn_type == recognition.Deepgram:
                self.main.model_name.addItems(config.DEEPGRAM_MODEL)
            elif recogn_type == recognition.Whisper_CPP:
                self.main.model_name.addItems(config.Whisper_CPP_MODEL_LIST)
            else:
                self.main.model_name.addItems(config.FUNASR_MODEL)
        

        lang = translator.get_code(show_text=self.main.source_language.currentText())


        is_allow_lang = recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type,
                                                  model_name=self.main.model_name.currentText())
        if is_allow_lang is not True:
            self.main.show_tips.setText(is_allow_lang)
        else:
            self.main.show_tips.setText('')

        if recognition.is_input_api(recogn_type=recogn_type) is not True:
            return

    def check_model_name(self):
        recogn_type = self.main.recogn_type.currentIndex()
        model = self.main.model_name.currentText()
        res = recognition.check_model_name(
            recogn_type=recogn_type,
            name=model,
            source_language_isLast=self.main.source_language.currentIndex() == self.main.source_language.count() - 1,
            source_language_currentText=self.main.source_language.currentText()
        )

        if res is not True:
            return tools.show_error(res)
        return True



    # 是否属于 配音角色 随所选目标语言变化的配音渠道 是 edgeTTS AzureTTS 或 302.ai同时 ai302tts_model=azure
    def change_by_lang(self, type):
        if type in [tts.EDGE_TTS, tts.MINIMAXI_TTS,tts.AZURE_TTS, tts.DOUBAO_TTS,tts.DOUBAO2_TTS, tts.AI302_TTS, tts.KOKORO_TTS]:
            return True
        return False

    # tts类型改变
    def tts_type_change(self, type):
        if tts.is_input_api(tts_type=type) is not True:
            self.main.tts_type.setCurrentIndex(0)
            return

        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if lang and lang != '-':
            is_allow_lang = tts.is_allow_lang(langcode=lang, tts_type=type)
            if is_allow_lang is not True:
                self.main.show_tips.setText(is_allow_lang)
            else:
                self.main.show_tips.setText('')

        config.line_roles = {}
        if type == tts.GOOGLE_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = ['No',"gtts"]
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.OPENAI_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.OPENAITTS_ROLES.split(',')
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.QWEN_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = list(tools.get_qwen3tts_rolelist().keys())
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.GEMINI_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.GEMINITTS_ROLES.split(',')
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.ELEVENLABS_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = tools.get_elevenlabs_role()
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif self.change_by_lang(type):
            self.set_voice_role(self.main.target_language.currentText())
        elif type == tts.CLONE_VOICE_TTS:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params.get("clone_voicelist",'')
            if self.main.current_rolelist[0]!='No':
                self.main.current_rolelist.insert(0,'No')
            self.main.voice_role.addItems(self.main.current_rolelist)
            run_in_threadpool(tools.get_clone_role)
        elif type == tts.CHATTTS:
            self.main.voice_role.clear()
            config.ChatTTS_voicelist = re.split(r'[,，]', config.settings.get('chattts_voice',''))
            self.main.current_rolelist = list(config.ChatTTS_voicelist)
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == tts.TTS_API:
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params.get('ttsapi_voice_role','').strip().split(',')
            self.main.voice_role.addItems(['No']+self.main.current_rolelist)
        elif type == tts.GPTSOVITS_TTS:
            rolelist = tools.get_gptsovits_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys())
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.CHATTERBOX_TTS:
            rolelist = tools.get_chatterbox_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = rolelist
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.COSYVOICE_TTS:
            rolelist = tools.get_cosyvoice_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys())
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == tts.FISHTTS:
            rolelist = tools.get_fishtts_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys())
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type in [tts.F5_TTS,tts.VOXCPM_TTS,tts.SPARK_TTS,tts.INDEX_TTS,tts.DIA_TTS]:
            rolelist = tools.get_f5tts_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys())
            self.main.voice_role.addItems(self.main.current_rolelist)

    # 目标语言改变时设置配音角色
    # t 语言显示文字
    def set_voice_role(self, t):

        role = self.main.voice_role.currentText()
        code = translator.get_code(show_text=t)

        if code and code != '-':
            is_allow_lang = tts.is_allow_lang(langcode=code, tts_type=self.main.tts_type.currentIndex())
            if is_allow_lang is not True:
                self.main.show_tips.setText(is_allow_lang)
            else:
                self.main.show_tips.setText('')
            # 判断翻译渠道是否支持翻译到该目标语言
            if translator.is_allow_translate(translate_type=self.main.translate_type.currentIndex(), show_target=t) is not True:
                return

        if not self.change_by_lang(self.main.tts_type.currentIndex()):
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


        if not code:
            self.main.voice_role.addItems(['No'])
        vt = code.split('-')[0] #if code != 'yue' else "zh"
        tts_type = self.main.tts_type.currentIndex()


        if tts_type == tts.EDGE_TTS:
            show_rolelist = tools.get_edge_rolelist()
            
        elif tts_type == tts.KOKORO_TTS:
            show_rolelist = tools.get_kokoro_rolelist()
        elif tts_type == tts.AI302_TTS:
            show_rolelist = tools.get_302ai()
        elif tts_type == tts.DOUBAO2_TTS:
            show_rolelist = tools.get_doubao2_rolelist()
        elif tts_type == tts.DOUBAO_TTS:
            show_rolelist = tools.get_doubao_rolelist()
        elif tts_type == tts.MINIMAXI_TTS:
            show_rolelist = tools.get_minimaxi_rolelist()

        else:
            # AzureTTS
            show_rolelist = tools.get_azure_rolelist()

        if not show_rolelist:
            self.main.target_language.setCurrentText('-')
            tools.show_error(tr('waitrole'))
            return

        if vt not in show_rolelist:
            self.main.voice_role.addItems(['No'])
            return
        if tts_type == tts.MINIMAXI_TTS:
            show_rolelist=list(show_rolelist[vt].keys())
            self.main.current_rolelist = show_rolelist
            self.main.voice_role.addItems(show_rolelist)
            return
        if len(show_rolelist[vt]) < 1:
            self.main.target_language.setCurrentText('-')
            tools.show_error(tr('waitrole'))
            return
        if isinstance(show_rolelist[vt],list):
            self.main.current_rolelist = show_rolelist[vt]
            self.main.voice_role.addItems(show_rolelist[vt])
        else:
            self.main.current_rolelist = list(show_rolelist[vt].keys())
            self.main.voice_role.addItems(self.main.current_rolelist)

    # 从本地导入字幕文件
    def import_sub_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self.main,tr('selectmp4'), config.params.get('last_opendir',''),
                                               "Srt files(*.srt *.txt)")
        if fname:
            content = ""
            try:
                content = Path(fname).read_text(encoding='utf-8')
            except UnicodeError:
                content = Path(fname).read_text(encoding='gbk')
            finally:
                if content:
                    self.main.subtitle_area.clear()
                    self.main.subtitle_area.insertPlainText(content.strip())
                else:
                    return tools.show_error(tr('import src error'))

    # 判断是否需要翻译
    def shound_translate(self):
        if self.main.target_language.currentText() == '-' or self.main.source_language.currentText() == '-':
            return False
        if self.main.target_language.currentText() == self.main.source_language.currentText():
            return False
        return True

    # 核对tts选择是否正确
    def check_tts(self):
        if tts.is_input_api(tts_type=self.main.tts_type.currentIndex()) is not True:
            return False
        # 如果没有选择目标语言，但是选择了配音角色，无法配音
        if self.main.target_language.currentText() == '-' and self.main.voice_role.currentText() not in ['No', '', ' ']:
            tools.show_error(tr('wufapeiyin'))
            return False
        return True

    # 核对所选语音识别模式是否正确
    def check_reccogn(self):
        langcode = translator.get_code(show_text=self.main.source_language.currentText())
        recogn_type = self.main.recogn_type.currentIndex()
        model_name = self.main.model_name.currentText()
        res = recognition.is_allow_lang(langcode=langcode, recogn_type=recogn_type, model_name=model_name)
        self.main.show_tips.setText(res if res is not True else '')

        # 原始语言是最后一个，即auto自动检查
        source_code = translator.get_code(show_text=self.main.source_language.currentText())

        if self.main.subtitle_area.toPlainText().strip() and source_code=='auto':
            tools.show_error(
                tr("The detection function cannot be used when subtitles have already been imported."))
            return False

        # 判断是否填写自定义识别 api openai-api识别
        return recognition.is_input_api(recogn_type=recogn_type)

    
    def check_output(self):
        from PySide6.QtWidgets import QMessageBox
        input_folder=Path(self.queue_mp4[0]).parent
        if not self.main.target_dir:
            self.main.target_dir= (input_folder / '_video_out').as_posix()
        output_folder=Path(self.main.target_dir)
        # 输出文件夹尚不存在
        if not output_folder.exists():
            return True

        
        # 输入输出是同个文件夹，
        if input_folder.samefile(output_folder):
            tools.show_error(tr("The output directory is not allowed to point to the input directory. Please use the default or create an empty folder as the output"))
            return False
        
        # 输出目录是空的
        if not self.main.clear_cache.isChecked():
            return True
        for it in self.queue_mp4:
            p=Path(it)
            folder=output_folder / f'{p.stem}-{p.suffix.lower()[1:]}'
            if  folder.exists():
                reply = QMessageBox.question(
                    self.main,
                    tr("Are you sure the cleanup has been output?"),
                    tr("If you confirm to clean up, all files in the output directory will be deleted. If you manually specify the output directory, please make sure there are no important files in the directory and back it up in advance to avoid data loss.",folder.as_posix()),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply != QMessageBox.StandardButton.Yes:
                    return False
                return True
        return True

    # 检测开始状态并启动
    def check_start(self):
        # 已在执行中，则停止
        if config.current_status == 'ing':
            self.update_status('stop')
            return
        self.main.startbtn.setDisabled(True)
        # 存储所有音视频文件都需要用到信息，例如原始语言 目标语言、 渠道、角色等
        self.cfg = {}
        # 重置字幕行角色
        config.line_roles = {}
        self.is_render = False
        config.settings = config.parse_init()
        # 倒计时
        config.task_countdown = int(float(config.settings.get('countdown_sec', 1)))


        # 无视频选择 ，也无导入字幕，无法处理
        if len(self.queue_mp4) < 1:
            tools.show_error(tr("Video file must be selected"))
            self.main.startbtn.setDisabled(False)
            return
        # 核对代理
        if self.check_proxy() is not True:
            self.main.startbtn.setDisabled(False)
            return


        # 先确定原始和目标语言
        self.cfg['translate_type'] = self.main.translate_type.currentIndex()
        # 存储 原始语言 目标语言显示文字，非语言代码
        self.cfg['source_language'] = self.main.source_language.currentText()
        self.cfg['target_language'] = self.main.target_language.currentText()
        # 存储语言代码
        self.cfg['source_language_code'] = translator.get_code(show_text=self.cfg['source_language'])
        self.cfg['target_language_code'] = translator.get_code(show_text=self.cfg['target_language'])

        # 清理缓存
        self.cfg['clear_cache'] = self.main.clear_cache.isChecked()
        self.cfg['only_out_mp4'] = self.main.only_out_mp4.isChecked()

        # 配音设置
        self.cfg['tts_type'] = self.main.tts_type.currentIndex()
        self.cfg['voice_role'] = self.main.voice_role.currentText()
        try:
            volume = int(self.main.volume_rate.value())
            pitch = int(self.main.pitch_rate.value())
        except ValueError:
            volume=0
            pitch=0
        self.cfg['volume'] = f'+{volume}%' if volume >= 0 else f'{volume}%'
        self.cfg['pitch'] = f'+{pitch}Hz' if pitch >= 0 else f'{pitch}Hz'

        # 语音识别设置
        self.cfg['recogn_type'] = self.main.recogn_type.currentIndex()
        if self.cfg['recogn_type'] == recognition.Faster_Whisper_XXL and not self.show_xxl_select():
            self.main.startbtn.setDisabled(False)
            return
        self.cfg['model_name'] = self.main.model_name.currentText()
        self.cfg['split_type'] = self.main.split_type.currentIndex()
        # 降噪
        self.cfg['remove_noise'] = self.main.remove_noise.isChecked()

        # 字幕嵌入类型
        self.cfg['subtitle_type'] = self.main.subtitle_type.currentIndex()

        # 对齐控制 配音加速 视频慢速
        self.cfg['voice_rate'] = self.main.voice_rate.value()
        try:
            voice_rate = int(self.main.voice_rate.value())
        except ValueError:
            voice_rate=0
        self.cfg['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"{voice_rate}%"
        self.cfg['voice_autorate'] = self.main.voice_autorate.isChecked()
        self.cfg['video_autorate'] = self.main.video_autorate.isChecked()

        # 人声背景音分离 添加背景音频
        self.cfg['is_separate'] = self.main.is_separate.isChecked()
        if self.cfg['voice_role'] == 'No':
            self.cfg['is_separate'] = False
        self.cfg['back_audio'] = self.main.back_audio.text().strip()
        self.cfg['enable_diariz'] = self.main.enable_diariz.isChecked()
        self.cfg['nums_diariz'] = self.main.nums_diariz.currentIndex()
        
        if self.cfg['is_separate'] and not Path(f'{config.ROOT_DIR}/models/onnx/UVR-MDX-NET-Inst_HQ_4.onnx').exists():
            self.main.startbtn.setDisabled(False)
            tools.show_download_tips(self.main,tr('Retain original background sound'))
            return

        if self.cfg['enable_diariz'] and not Path(f'{config.ROOT_DIR}/models/onnx/3dspeaker_speech_eres2net_large_sv_zh-cn_3dspeaker_16k.onnx').exists():
            self.main.startbtn.setDisabled(False)
            tools.show_download_tips(self.main,tr('Speaker'))
            return



        # 检查输入 输出目录
        if self.check_output() is not True:
            self.main.startbtn.setDisabled(False)
            return


        # 核对识别是否正确
        if self.check_reccogn() is not True:
            self.main.startbtn.setDisabled(False)
            return

        # 如果需要翻译，再判断是否符合翻译规则
        if self.shound_translate() and translator.is_allow_translate(
                translate_type=self.cfg['translate_type'],
                show_target=self.cfg['target_language_code']) is not True:
            self.main.startbtn.setDisabled(False)
            return

        # 字幕区文字
        txt = self.main.subtitle_area.toPlainText().strip()
        if self.check_txt(txt) is not True:
            self.main.startbtn.setDisabled(False)
            return

        # tts类型
        if self.check_tts() is not True:
            self.main.tts_type.setCurrentIndex(0)
            self.main.startbtn.setDisabled(False)
            return

        # LLM重新断句
        self.cfg['rephrase'] = self.main.rephrase.currentIndex()
        # 判断CUDA
        self.cfg['cuda'] = self.main.enable_cuda.isChecked()
        self.cfg['remove_silent_mid'] = False
        self.cfg['align_sub_audio'] = True
        # 只有未启用 音频加速 视频慢速时才起作用
        if not self.cfg['voice_autorate'] and not self.cfg['video_autorate']:
            self.cfg['remove_silent_mid']=self.main.remove_silent_mid.isChecked()
            self.cfg['align_sub_audio']=self.main.align_sub_audio.isChecked()
        if self.cuda_isok() is not True:
            self.main.startbtn.setDisabled(False)
            return

        # 未设置目标语言，不允许嵌入字幕
        if not self.cfg.get('target_language_code') and self.cfg['subtitle_type'] > 0:
            self.main.startbtn.setDisabled(False)
            return tools.show_error(
                tr("Target language must be selected to embed subtitles"))
        
        # 核对是否存在名字相同后缀不同的文件，以及若存在音频则强制为tiqu模式
        if self.check_name() is not True:
            self.main.startbtn.setDisabled(False)
            return

        # LLM 重新断句时，需判断 deepseek或openai chatgpt填写了信息
        if self.main.rephrase.currentIndex()==1:
            ai_type = config.settings.get('llm_ai_type', 'openai')
            if ai_type == 'openai' and not config.params.get('chatgpt_key'):
                self.main.startbtn.setDisabled(False)
                tools.show_error(tr('llmduanju'))
                from videotrans.winform import chatgpt
                chatgpt.openwin()
                return
            if ai_type == 'deepseek' and not config.params.get('deepseek_key'):
                self.main.startbtn.setDisabled(False)
                tools.show_error(tr('llmduanjudp'))
                from videotrans.winform import deepseek
                deepseek.openwin()
                return

        # 设置各项模式参数
        self.set_mode()
        if self.main.app_mode in ['biaozhun', 'tiqu']:
            self.cfg['app_mode'] = self.main.app_mode


        config.params.update(self.cfg)
        config.getset_params(config.params)

        self.delete_process()
        # 设为开始
        self.update_status('ing')
        try:
            Path(config.TEMP_DIR + '/stop_porcess.txt').unlink(missing_ok=True)
        except:
            pass

        if self.main.recogn_type.currentIndex() == recognition.FASTER_WHISPER or self.main.app_mode == 'biaozhun':
            # 背景音量
            config.settings['loop_backaudio'] = self.main.is_loop_bgm.isChecked()
            try:
                config.settings['backaudio_volume'] = float(self.main.bgmvolume.text())
            except ValueError:
                pass

            # VAD参数
            config.settings["threshold"] = min(
                0.9,
                max(float(self.main.threshold.text().strip()), 0.1)
            )
            config.settings["min_speech_duration_ms"] = int(self.main.min_speech_duration_ms.text())
            config.settings["min_silence_duration_ms"] = int(self.main.min_silence_duration_ms.text())
            config.settings["max_speech_duration_s"] = int(self.main.max_speech_duration_s.text())
        
        config.settings['dubbing_wait'] = self.main.dubbing_wait.text()
        config.settings['trans_thread'] = self.main.trans_thread.text()
        config.settings['aitrans_thread'] = self.main.aitrans_thread.text()
        config.settings['translation_wait'] = self.main.translation_wait.text()

        # 中日韩硬字幕单行字符
        config.settings['cjk_len'] = self.main.cjklinenums.value()
        # 其他语言硬字幕单行字符
        config.settings['other_len'] = self.main.othlinenums.value()
        # AI翻译发送完整字幕
        config.settings['aisendsrt']=self.main.aisendsrt.isChecked()
        config.parse_init(config.settings)

        self._disabled_button(True)
        self.main.subtitle_area.setReadOnly(True)
        tools.set_process(text='start', type='create_btns')
        self.main.startbtn.setDisabled(False)
        self.retry_queue_mp4=[]
        self.uuid_queue_mp4={}


    def retry(self):
        if not self.retry_queue_mp4:
            self.main.retrybtn.setVisible(False)
            return

        self._disabled_button(True)
        self.main.retrybtn.setVisible(False)
        self.main.subtitle_area.setReadOnly(True)
        self.delete_process()
        # 设为开始
        self.update_status('ing')
        # 待翻译的文件列表
        self.obj_list = []

        cfg = copy.deepcopy(self.cfg)
        for v in self.retry_queue_mp4:
            obj = tools.format_video(v.get('file'), v.get('target_dir'))
            self.obj_list.append(obj)
            self.add_process_btn(
                target_dir=Path(obj['target_dir']).as_posix() if cfg.get('app_mode')=='tiqu' or not cfg.get('only_out_mp4') else v.get('target_dir'),
                name=obj['name'],
                uuid=obj['uuid'])

        cfg['clear_cache']=False

        # 启动任务
        tools.set_process(text=tr('kaishichuli'), uuid=self.obj_list[0]['uuid'])

        from videotrans.task._mult_video import MultVideo
        task = MultVideo(parent=self.main, cfg=cfg, obj_list=self.obj_list)
        # 单个顺序执行
        if config.settings.get('batch_single'):
            task.uito.connect(self.update_data)
        task.start()
        self.main.startbtn.setDisabled(False)
        # 不再重试
        self.retry_queue_mp4=[]


    # 创建进度按钮
    def create_btns(self):
        # 输出目录，此时该目录是 视频名子文件夹的父级
        target_dir = self.main.target_dir
        self.main.btn_save_dir.setToolTip(target_dir)
        # 待翻译的文件列表
        self.obj_list = []

        # new_name = []
        txt = self.main.subtitle_area.toPlainText().strip()
        self.cfg.update(
            {'subtitles': txt, 'app_mode': self.main.app_mode}
        )
        cfg=copy.deepcopy(self.cfg)

        for video_path in self.queue_mp4:
            obj = tools.format_video(video_path, target_dir)
            self.obj_list.append(obj)
            self.add_process_btn(
                target_dir=Path(obj['target_dir']).as_posix() if cfg.get('app_mode')=='tiqu' or not cfg.get('only_out_mp4') else target_dir,
                name=obj['name'],
                uuid=obj['uuid'])
            self.uuid_queue_mp4[obj['uuid']]=(video_path,target_dir)


        # 启动任务
        tools.set_process(text=tr('kaishichuli'), uuid=self.obj_list[0]['uuid'])
        # 单个视频处理模式
        if self.main.app_mode not in ['tiqu'] and len(self.obj_list) == 1:
            from videotrans.task._only_one import Worker
            task = Worker(
                parent=self.main,
                obj_list=self.obj_list,
                cfg=cfg
            )
            task.uito.connect(self.update_data)
            task.start()
            return

        from videotrans.task._mult_video import MultVideo
        task=MultVideo(parent=self.main, cfg=cfg, obj_list=self.obj_list)
        # 单个顺序执行
        if config.settings.get('batch_single'):
            task.uito.connect(self.update_data)
        task.start()

    # 启动时禁用相关模式按钮，停止时重新启用
    def _disabled_button(self, disabled=True):
        for k, v in self.main.moshi.items():
            if k != self.main.app_mode:
                # 非当前模式
                v.setDisabled(disabled)
                v.setChecked(False)
            else:
                v.setDisabled(False)
                v.setChecked(True)

    # 任务end结束或暂停时，清空队列
    # 先不清空 stoped_uuid_set 标志，用于背景分离任务稍后结束
    def _clear_task(self):
        for v in self.obj_list:
            try:
                if v['uuid'] in config.uuid_logs_queue:
                    del config.uuid_logs_queue[v['uuid']]
            except ValueError:
                pass

    # 添加进度条
    def add_process_btn(self, *, target_dir: str = None, name: str = None, uuid=None):
        from videotrans.component.progressbar import ClickableProgressBar
        clickable_progress_bar = ClickableProgressBar(self)
        clickable_progress_bar.progress_bar.setValue(0)  # 设置当前进度值
        clickable_progress_bar.setText(tr("waitforstart"))
        clickable_progress_bar.setMinimumSize(500, 50)
        clickable_progress_bar.setToolTip(tr('mubiao'))
        # # 将按钮添加到布局中
        if self.cfg.get('app_mode') == 'tiqu' and self.cfg.get('copysrt_rawvideo'):
            target_dir = Path(name).parent.as_posix()

        clickable_progress_bar.setTarget(
            target_dir=target_dir,
            name=name
        )
        clickable_progress_bar.setCursor(Qt.PointingHandCursor)
        self.main.processlayout.addWidget(clickable_progress_bar)
        if uuid:
            self.processbtns[uuid] = clickable_progress_bar

    # 设置按钮上的日志信息
    def set_process_btn_text(self, d):
        if isinstance(d, str):
            d = json.loads(d)
        text, uuid, _type = d['text'], d.get('uuid', ''), d.get('type', 'logs')
        if not uuid or uuid not in self.processbtns:
            return
        if _type == 'set_precent' and self.processbtns[uuid].precent < 100:
            t, precent = text.split('???')
            precent = int(float(precent) * 100) / 100
            self.processbtns[uuid].setPrecent(precent)
            self.processbtns[uuid].setText(f'{t}')
        elif _type == 'logs' and self.processbtns[uuid].precent < 100:
            self.processbtns[uuid].setText(text)
        elif _type == 'succeed':
            self.processbtns[uuid].setEnd()
            if self.processbtns[uuid].name in self.queue_mp4:
                self.queue_mp4.remove(self.processbtns[uuid].name)
        elif _type == 'error':
            self.processbtns[uuid].setError(text)
            self.processbtns[uuid].progress_bar.setStyleSheet('color:#ff0000')
            self.processbtns[uuid].setCursor(Qt.PointingHandCursor)

    # 更新执行状态
    def update_status(self, type):
        if self.had_click_btn:
            return
        self.had_click_btn=True
        config.current_status = type
        if type == 'ing':
            # 重设为开始状态
            self.disabled_widget(True)
            self.main.startbtn.setText(tr("starting..."))
            self.had_click_btn=False
            return
        try:
            Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
            with open(config.TEMP_DIR + '/stop_porcess.txt', 'w', encoding='utf-8') as f:
                f.write('stop')
        except Exception:
            pass
        # stop 停止，end=结束
        self.main.subtitle_area.clear()
        self.main.startbtn.setText(tr(type))

        # 删除本次任务的所有进度队列
        self._clear_task()
        # 启用
        self.disabled_widget(False)
        # 启用相关模式
        self._disabled_button(False)
        for it in self.obj_list:
            if it['uuid'] in config.uuid_logs_queue:
                config.uuid_logs_queue.pop(it['uuid'],None)
        if type == 'end':
            self.main.subtitle_area.clear()

            for prb in self.processbtns.values():
                prb.setEnd()
            # 成功完成
            # 关机
            if self.main.shutdown.isChecked():
                try:
                    tools.shutdown_system()
                except Exception as e:
                    tools.show_error(tr('shutdownerror') + str(e))
            self.main.target_dir = None
            self.main.btn_save_dir.setToolTip('')
        else:
            config.task_countdown = -1
            self.set_djs_timeout()
            # 任务队列中设为停止并删除队列，防止后续到来的日志继续显示
            for it in self.obj_list:
                # 按钮设为暂停
                if it['uuid'] in self.processbtns:
                    self.processbtns[it['uuid']].setPause()
        
        if self.main.app_mode == 'tiqu':
            self.set_tiquzimu()
        self._reset()
        self.had_click_btn=False

    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data) if isinstance(json_data, str) else json_data
        if config.current_status !='ing' and d['type'] not in [ 'error', 'succeed']:
            return

        if d['type'] in ['logs', 'error', 'succeed', 'set_precent']:
            self.set_process_btn_text(d)
            if d['type'] in ['error', 'succeed'] and d.get('uuid'):
                config.stoped_uuid_set.add(d['uuid'])
            if d['type']!='error' or not d.get('uuid'):
                return
            uuid=d.get('uuid')
            vdata=self.uuid_queue_mp4.get(uuid)
            if not vdata:
                return
            self.retry_queue_mp4.append({"file":vdata[0],"target_dir":vdata[1]})
        elif d['type'] == 'create_btns':
            self.create_btns()
        # 任务开始执行，初始化按钮等
        elif d['type'] == 'shitingerror':
            tools.show_error(d['text'])
        elif d['type'] in ['end']:
            # 任务全部完成时出现 end
            self.update_status(d['type'])
            self.main.retrybtn.setVisible(True if self.retry_queue_mp4 else False)
        # 一行一行插入字幕到字幕编辑区
        elif d['type'] == "subtitle" and config.current_status == 'ing':
            self.main.subtitle_area.moveCursor(QTextCursor.End)
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'edit_dubbing':
            # 显示编辑翻译框
            cache_folder,language=d['text'].split('<|>')
            dialog=EditDubbingResultDialog(
                cache_folder=cache_folder,
                language=language,
                parent=self.main
            )
            
            if dialog.exec():
                self.set_djs_timeout()
            else:
                self.update_status('stop')
        elif d['type'] == 'edit_subtitle_source':
            # 显示编辑翻译框

            
            dialog=EditRecognResultDialog(
                source_sub=config.onlyone_source_sub,
                parent=self.main
            )
            
            if dialog.exec():
                self.set_djs_timeout()
            else:
                self.update_status('stop')
        elif d['type'] == 'edit_subtitle_target':
            # 弹出编辑配音字幕

            cache_folder,target_language,tts_type=d['text'].split('<|>')
            dialog=SpeakerAssignmentDialog(
                source_sub=None if not config.onlyone_trans else config.onlyone_source_sub,
                target_sub=config.onlyone_target_sub,
                all_voices=self.main.current_rolelist,
                cache_folder=cache_folder,
                target_language=target_language,
                tts_type=int(tts_type),
                parent=self.main
                
            )
            if dialog.exec():
                self.set_djs_timeout()                
            else:
                self.update_status('stop')
        elif d['type'] == 'replace_subtitle':
            # 完全替换字幕区
            self.main.subtitle_area.clear()
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'check_soft_update':
            self.update_tips(d['text'])
        elif d['type'] == 'set_clone_role' and self.main.tts_type.currentText() == 'clone-voice':
            if config.current_status == 'ing':
                return
            current = self.main.voice_role.currentText()
            self.main.voice_role.clear()
            self.main.voice_role.addItems(config.params.get("clone_voicelist",''))
            self.main.voice_role.setCurrentText(current)
        elif d['type'] == 'ffmpeg':
            self.main.startbtn.setText(d['text'])
            self.main.startbtn.setDisabled(True)
            self.main.startbtn.setStyleSheet("""color:#ff0000""")
        elif d['type'] == 'refreshtts':
            currentIndex = self.main.tts_type.currentIndex()
            if currentIndex >0:
                self.main.tts_type.setCurrentIndex(0)
                QTimer.singleShot(100,lambda: self.main.tts_type.setCurrentIndex(currentIndex))
        elif d['type'] == 'refreshmodel_list':
            config.WHISPER_MODEL_LIST = re.split(r'[,，]', config.settings.get('model_list',''))
            config.Whisper_CPP_MODEL_LIST = re.split(r'[,，]', config.settings.get('Whisper.cpp.models',''))
            if self.main.recogn_type.currentIndex() in [recognition.FASTER_WHISPER, recognition.OPENAI_WHISPER,recognition.Faster_Whisper_XXL,recognition.Whisper_CPP]:
                current_model_name = self.main.model_name.currentText()
                self.main.model_name.clear()
                self.main.model_name.addItems(config.Whisper_CPP_MODEL_LIST if self.main.recogn_type.currentIndex()==recognition.Whisper_CPP else config.WHISPER_MODEL_LIST)
                self.main.model_name.setCurrentText(current_model_name)


