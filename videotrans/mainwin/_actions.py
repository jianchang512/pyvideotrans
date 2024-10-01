import copy
import json
import re
import shutil
import threading
from pathlib import Path

from PySide6 import  QtWidgets
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans import translator, recognition
from videotrans.component.progressbar import ClickableProgressBar
from videotrans.configure import config
from videotrans.mainwin._actions_sub import WinActionSub
from videotrans.recognition import OPENAI_WHISPER, FASTER_WHISPER, is_allow_lang as recogn_is_allow_lang, \
    is_input_api as recogn_is_input_api
from videotrans.task._only_one import Worker
from videotrans.task.trans_create import TransCreate
from videotrans.tts import EDGE_TTS, AZURE_TTS, AI302_TTS, CLONE_VOICE_TTS, TTS_API, GPTSOVITS_TTS, COSYVOICE_TTS, \
    FISHTTS, CHATTTS, GOOGLE_TTS, OPENAI_TTS, ELEVENLABS_TTS, is_allow_lang as tts_is_allow_lang, \
    is_input_api as tts_is_input_api
from videotrans.util import tools
from videotrans.winform import fn_downmodel


class WinAction(WinActionSub):
    def __init__(self, main=None):
        super().__init__()
        self.main = main
        # 更新按钮
        self.update_btn = None
        # 单个执行时，当前字幕所处阶段：识别后编辑或翻译后编辑
        self.edit_subtitle_type = ''
        # 进度按钮
        self.processbtns = {}
        # 单个任务时，修改字幕后需要保存到的位置，原始语言字幕或者目标语音字幕
        self.wait_subtitle = None
        # 存放需要处理的视频dict信息，包括uuid
        self.obj_list = []
        self.is_batch=True

    def _reset(self):
        # 单个执行时，当前字幕所处阶段：识别后编辑或翻译后编辑
        self.edit_subtitle_type = ''
        # 单个任务时，修改字幕后需要保存到的位置，原始语言字幕或者目标语音字幕
        self.wait_subtitle = None
        # 存放需要处理的视频dict信息，包括uuid
        self.obj_list = []
        self.main.source_mp4.setText(config.transobj["No select videos"])
        config.queue_mp4=[]
    # 配音速度改变时
    def voice_rate_changed(self, text):
        config.params['voice_rate'] = f'+{text}%' if text >= 0 else f'{text}%'

    # voice_autorate  变化
    def autorate_changed(self, state, name):
        if name == 'voice':
            config.params['voice_autorate'] = state
        elif name == 'video':
            config.params['video_autorate'] = state
        elif name == 'append_video':
            config.params['append_video'] = state

    # 删除进度按钮
    def delete_process(self):
        for i in range(self.main.processlayout.count()):
            item = self.main.processlayout.itemAt(i)
            if item.widget():
                try:
                    item.widget().deleteLater()
                except Exception as e:
                    pass
        self.processbtns = {}

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

    # 将倒计时设为立即超时
    def set_djs_timeout(self):
        config.task_countdown = -1
        self.main.stop_djs.hide()
        self.main.continue_compos.hide()
        self.main.timeout_tips.setText('')
        self.main.continue_compos.setText('')
        self.main.continue_compos.setDisabled(True)
        self.main.subtitle_area.setReadOnly(True)
        self.update_subtitle()

    # 手动点击暂停按钮
    def reset_timeid(self):
        config.task_countdown = 86400
        self.main.stop_djs.hide()
        self.main.timeout_tips.setText('')
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

    # 语音识别方式改变时
    def recogn_type_change(self):
        config.params['recogn_type'] = self.main.recogn_type.currentIndex()
        self.main.split_type.setDisabled(True if config.params['recogn_type'] > 0 else False)

        if config.params['recogn_type'] > 1:
            self.main.model_name.setDisabled(True)
            self.main.model_name_help.setDisabled(True)
        else:
            self.main.model_name_help.setDisabled(False)
            self.main.model_name.setDisabled(False)
            self.check_model_name()
        if config.params['recogn_type']>1:
            # >1 禁用 auto 自动检测
            # 禁用最后一项
            if self.main.source_language.currentIndex()==self.main.source_language.count() - 1:
                self.main.source_language.setCurrentIndex(0)

        lang = translator.get_code(show_text=self.main.source_language.currentText())
        is_allow_lang = recogn_is_allow_lang(langcode=lang, recogn_type=config.params['recogn_type'])
        if is_allow_lang is not True:
            QMessageBox.critical(self.main, config.transobj['anerror'], is_allow_lang)

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
        self.hide_show_element(self.main.horizontalLayout, self.change_by_lang(type))
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

    # 判断是否需要翻译
    def shound_translate(self):
        if self.main.target_language.currentText() == '-' or self.main.source_language.currentText() == '-':
            return False
        if self.main.target_language.currentText() == self.main.source_language.currentText():
            return False
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

    # 核对所选语音识别模式是否正确
    def check_reccogn(self):
        if self.main.recogn_type.currentIndex()>1 and self.main.source_language.currentIndex()==self.main.source_language.count() - 1:
            QMessageBox.critical(self.main, config.transobj['anerror'], '仅faster-whisper和open-whisper模式下可使用检测语言' if config.defaulelang=='zh' else 'Detection language available only in fast-whisper and open-whisper modes.')
            return False
        if self.main.subtitle_area.toPlainText().strip() and self.main.source_language.currentIndex()==self.main.source_language.count() - 1:
            QMessageBox.critical(self.main, config.transobj['anerror'], '已导入字幕情况下，不可再使用检测功能' if config.defaulelang=='zh' else 'The detection function cannot be used when subtitles have already been imported.')
            return False
        langcode = translator.get_code(show_text=config.params['source_language'])

        is_allow_lang = recogn_is_allow_lang(langcode=langcode, recogn_type=self.main.recogn_type.currentIndex())
        if is_allow_lang is not True:
            QMessageBox.critical(self.main, config.transobj['anerror'], is_allow_lang)
            return False
        # 判断是否填写自定义识别api openai-api识别、zh_recogn识别信息
        return recogn_is_input_api(recogn_type=self.main.recogn_type.currentIndex())

    def check_model_name(self):
        res = recognition.check_model_name(
            recogn_type=self.main.recogn_type.currentIndex(),
            name=self.main.model_name.currentText(),
            source_language_isLast=self.main.source_language.currentIndex() == self.main.source_language.count() - 1,
            source_language_currentText=self.main.source_language.currentText()
        )
        if res == 'download':
            return fn_downmodel.openwin(model_name=self.main.model_name.currentText(), recogn_type=self.main.recogn_type.currentIndex())
        if res is not True:
            return QMessageBox.critical(self.main, config.transobj['anerror'], res)
        return True
    # 检测开始状态并启动
    def check_start(self):
        self.edit_subtitle_type = ''
        if config.current_status == 'ing':
            # 已在执行中，则停止
            question = tools.show_popup(config.transobj['exit'], config.transobj['confirmstop'])
            if question == QMessageBox.Yes:
                self.update_status('stop')
                return
        self.main.startbtn.setDisabled(True)
        # 无视频选择 ，也无导入字幕，无法处理
        if len(config.queue_mp4) < 1:
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 '必须选择视频文件' if config.defaulelang == 'zh' else 'Video file must be selected')
            self.main.startbtn.setDisabled(False)
            return

        if self.check_proxy() is not True:
            self.main.startbtn.setDisabled(False)
            return

        config.task_countdown = int(config.settings['countdown_sec'])
        config.settings = config.parse_init()

        # 目标文件夹
        config.params['source_language'] = self.main.source_language.currentText()
        config.params['target_language'] = self.main.target_language.currentText()

        # 核对识别是否正确
        if self.check_reccogn() is not True:
            self.main.startbtn.setDisabled(False)
            return
        # 配音角色
        config.params['voice_role'] = self.main.voice_role.currentText()
        config.params['is_separate'] = self.main.is_separate.isChecked()
        if config.params['voice_role'] == 'No':
            config.params['is_separate'] = False

        # 配音自动加速
        config.params['voice_autorate'] = self.main.voice_autorate.isChecked()
        config.params['append_video'] = self.main.append_video.isChecked()

        # 语音模型
        config.params['model_name'] = self.main.model_name.currentText()
        # 识别模式，从faster--openai--googlespeech ...
        config.params['recogn_type'] = self.main.recogn_type.currentIndex()
        # 字幕嵌入类型
        config.params['subtitle_type'] = int(self.main.subtitle_type.currentIndex())
        try:
            voice_rate = int(self.main.voice_rate.value())
            config.params['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"{voice_rate}%"
        except:
            config.params['voice_rate'] = '+0%'
        try:
            volume = int(self.main.volume_rate.value())
            pitch = int(self.main.pitch_rate.value())
            config.params['volume'] = f'+{volume}%' if volume > 0 else f'{volume}%'
            config.params['pitch'] = f'+{pitch}Hz' if pitch > 0 else f'{pitch}Hz'
        except:
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
            self.main.startbtn.setDisabled(False)
            return

        # 字幕区文字
        txt = self.main.subtitle_area.toPlainText().strip()
        if self.check_txt(txt) is not True:
            self.main.startbtn.setDisabled(False)
            return

        # tts类型
        if self.check_tts() is not True:
            self.main.startbtn.setDisabled(False)
            return
        # 设置各项模式参数
        self.set_mode()

        # 检测模型是否存在
        if not txt and self.main.recogn_type.currentIndex() in [OPENAI_WHISPER, FASTER_WHISPER] and  self.check_model_name() is not True:
            self.main.startbtn.setDisabled(False)
            return
        # 判断CUDA
        if self.cuda_isok() is not True:
            self.main.startbtn.setDisabled(False)
            return
        # 核对文件路径是否符合规范，防止ffmpeg处理中出错
        if self.url_right() is not True:
            self.main.startbtn.setDisabled(False)
            return
        if self.main.recogn_type.currentIndex()>1 and self.main.source_language.currentIndex()==self.main.source_language.count() - 1:
            QMessageBox.critical(self.main, config.transobj['anerror'], '仅faster-whisper和open-whisper模式下可使用检测语言' if config.defaulelang=='zh' else 'Detection language available only in fast-whisper and open-whisper modes.')
            return
        # 核对是否存在名字相同后缀不同的文件，以及若存在音频则强制为tiqu模式
        if self.check_name() is not True:
            self.main.startbtn.setDisabled(False)
            return
        config.params['line_roles']={}
        config.params['split_type']='avg' if self.main.split_type.currentIndex()>0 else 'all'
        if self.main.app_mode in ['biaozhun_jd', 'biaozhun', 'tiqu']:
            config.params['app_mode'] = self.main.app_mode
        config.getset_params(config.params)
        self.delete_process()
        # 设为开始
        self.update_status('ing')
        config.settings = config.parse_init()
        
        self._disabled_button(True)
        self.main.startbtn.setDisabled(False)
        QTimer.singleShot(50, self.create_btns)

    def create_btns(self):
        target_dir = Path(self.main.target_dir if self.main.target_dir else Path(
            config.queue_mp4[0]).parent.as_posix() + "/_video_out").resolve().as_posix()
        config.params["target_dir"]=target_dir
        self.main.btn_save_dir.setToolTip(target_dir)
        self.obj_list = []
        # queue_mp4中的名字可能已修改为规范
        new_name=[]
        for video_path in config.queue_mp4:
            obj=tools.format_video(video_path, target_dir)
            new_name.append(obj['name'])
            self.obj_list.append(obj)
            self.add_process_btn(target_dir=Path(obj['target_dir']).as_posix(), name=obj['name'], uuid=obj['uuid'])
        config.queue_mp4=new_name
        txt=self.main.subtitle_area.toPlainText().strip()

        if len(self.obj_list)==1 and self.main.app_mode not in ['biaozhun_jd','tiqu']:
            self.is_batch=False
            # 启动任务
            tools.set_process(text=config.transobj['kaishichuli'],uuid=self.obj_list[0]['uuid'])
            task = Worker(
                parent=self.main,
                app_mode=self.main.app_mode,
                obj=self.obj_list[0],
                txt=txt
            )
            task.uito.connect(self.update_data)
            task.start()
            return
        self.is_batch=True
        config.params.update(
            {'subtitles': txt, 'app_mode': self.main.app_mode}
        )
        # 保存任务实例
        for it in self.obj_list:
            if config.params['clear_cache'] and Path(it['target_dir']).is_dir():
                shutil.rmtree(it['target_dir'], ignore_errors=True)
            Path(it['target_dir']).mkdir(parents=True, exist_ok=True)
            trk = TransCreate(copy.deepcopy(config.params), it)
            self.update_data({"text":config.transobj['kaishichuli'],"uuid":it['uuid'],"type":"logs"})
            # 压入识别队列开始执行
            config.prepare_queue.append(trk)


    # 启动时禁用相关模式按钮，停止时重新启用
    def _disabled_button(self, disabled=True):
        for k, v in self.main.moshis.items():
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
            except:
                pass

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
    def set_process_btn_text(self, d):
        if isinstance(d, str):
            d = json.loads(d)
        text, uuid, _type = d['text'], d['uuid'], d['type']
        if not uuid or uuid not in self.processbtns:
            return
        if _type == 'set_precent' and self.processbtns[uuid].precent < 100:
            t, precent = text.split('???')
            precent = int(float(precent))
            self.processbtns[uuid].setPrecent(precent)
            self.processbtns[uuid].setText(f'{config.transobj["running"].replace("..", "")} {t}')
        elif _type == 'logs' and self.processbtns[uuid].precent < 100:
            self.processbtns[uuid].setText(text)
        elif _type == 'succeed':
            self.processbtns[uuid].setEnd()
            if self.processbtns[uuid].name in config.queue_mp4:
                config.queue_mp4.remove(self.processbtns[uuid].name)
        elif _type == 'error':
            self.processbtns[uuid].setError(text)
            self.processbtns[uuid].progress_bar.setStyleSheet('color:#ff0000')
            self.processbtns[uuid].setCursor(Qt.PointingHandCursor)

    # 更新执行状态
    def update_status(self, type):
        config.current_status = type
        self.main.continue_compos.hide()
        self.main.stop_djs.hide()
        if type == 'ing':
            # 重设为开始状态
            self.disabled_widget(True)
            self.main.startbtn.setText(config.transobj["starting..."])
            return
        # stop 停止，end=结束
        self.main.subtitle_area.setReadOnly(False)
        self.main.subtitle_area.clear()
        self.main.startbtn.setText(config.transobj[type])
        self.main.export_sub.setDisabled(False)
        self.main.set_line_role.setDisabled(False)
        # 删除本次任务的所有进度队列
        self._clear_task()
        # 启用
        self.disabled_widget(False)
        # 启用相关模式
        self._disabled_button(False)
        if type == 'end':
            for prb in self.processbtns.values():
                prb.setEnd()
            # 成功完成

            # 关机
            if self.main.shutdown.isChecked():
                try:
                    tools.shutdown_system()
                except Exception as e:
                    QMessageBox.critical(self.main, config.transobj['anerror'],
                                         config.transobj['shutdownerror'] + str(e))
            self.main.target_dir=None
            self.main.btn_save_dir.setToolTip('')
        else:
            # 任务队列中设为停止并删除队列，防止后续到来的日志继续显示
            for it in self.obj_list:
                # 按钮设为暂停
                if it['uuid'] in self.processbtns:
                    self.processbtns[it['uuid']].setPause()
            self.set_djs_timeout()
            self.main.stop_djs.hide()
            self.main.continue_compos.hide()
        for it in self.obj_list:
            if it['uuid'] in config.uuid_logs_queue:
                del config.uuid_logs_queue[it['uuid']]
        if self.main.app_mode == 'tiqu':
            self.set_tiquzimu()
        self._reset()


    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data) if isinstance(json_data, str) else json_data
        if d['type'] in ['logs', 'error', 'succeed', 'set_precent']:
            self.set_process_btn_text(d)
            if d['type'] in ['error', 'succeed']:
                config.stoped_uuid_set.add(d['uuid'])
        # 任务开始执行，初始化按钮等
        elif d['type'] in ['end']:
            # 任务全部完成时出现 end
            try:
                self.update_status(d['type'])
                if "linerolew" in config.child_forms and hasattr(config.child_forms['linerolew'], 'close'):
                    config.child_forms['linerolew'].close()
                    config.child_forms.pop('linerolew', None)
            except Exception as e:
                print(f'#########{e}')
        # 一行一行插入字幕到字幕编辑区
        elif d['type'] == "subtitle" and config.current_status=='ing' and (self.is_batch or config.task_countdown<=0):
            self.main.subtitle_area.moveCursor(QTextCursor.End)
            self.main.subtitle_area.insertPlainText(d['text'])
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
            self.set_djs_timeout()
        elif d['type'] == 'show_djs':
            self.main.timeout_tips.setText(d['text'])
            self.main.stop_djs.show()
            self.main.continue_compos.show()
            self.main.continue_compos.setDisabled(False)
            self.main.subtitle_area.setReadOnly(False)
        elif d['type'] == 'check_soft_update':
            self.update_tips(d['text'])
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
        # txt = re.sub(r':\d+[\.\,]\d+', lambda m: m.group().replace('.', ','), txt, re.S | re.M)
        config.task_countdown = 0
        if not txt:
            return

        # 是单个视频执行时
        if not self.is_batch and self.wait_subtitle:
            # 不是批量才允许更新字幕
            with Path(self.wait_subtitle).open('w', encoding='utf-8') as f:
                f.write(txt)
                f.flush()
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
