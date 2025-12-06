import json
import os
import platform
import re
import shutil,time

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer, Qt

from videotrans.configure import config
from videotrans.configure.config import tr,logs
from videotrans.util import tools
from videotrans.util.ListenVoice import ListenVoice


@dataclass
class WinActionSub:
    main: Optional[Any]=None
    law:Optional[Any]=None

    update_btn: Optional[Any] = field(default=None, init=False)

    is_render: bool = field(default=False, init=False)
    is_batch: bool = field(default=True, init=False)
    had_click_btn: bool = field(default=False, init=False)
    removing_layout: bool = field(default=False, init=False)

    # -- UI 对象实例 --
    scroll_area: Optional[Any] = field(default=None, init=False)
    scroll_area_after: Optional[Any] = field(default=None, init=False)
    scroll_area_search: Optional[Any] = field(default=None, init=False)

    # -- 数据容器 (使用 default_factory 处理可变类型) --
    processbtns: Dict = field(default_factory=dict, init=False)
    obj_list: List[Dict] = field(default_factory=list, init=False)
    cfg: Dict = field(default_factory=dict, init=False)
    queue_mp4: List[str] = field(default_factory=list, init=False)
    show_adv_status:bool=False # 高级选项当前显示状态，默认不显示
    # 存储失败重试的信息
    retry_queue_mp4: List[Dict] = field(default_factory=list, init=False)
    # 保存原始的 uuid:mp4 信息，用于出错重试
    uuid_queue_mp4: Dict = field(default_factory=dict, init=False)




    def show_model_help(self):

        msg = tr('From tiny model to base to small to medium to large-v3 model, the recognition effect is getting better and better, but the model size is getting bigger and bigger, the recognition speed is getting slower and slower, and it needs more CPU/memory/GPU resources. default is to use tiny model, if you want better result, please use bigger model .en suffix model and model starting with distil is only used to recognize English pronunciation video')

        # 创建 QMessageBox
        msg_box = QtWidgets.QMessageBox(self.main)
        msg_box.setWindowTitle("Help")
        msg_box.setText(msg)

        # 添加 OK 按钮
        ok_button = msg_box.addButton(QtWidgets.QMessageBox.Ok)
        ok_button.setText(tr("OK"))

        # 添加“模型选择教程”按钮
        tutorial_button = QtWidgets.QPushButton(
            tr("Model Selection Tutorial"))
        msg_box.addButton(tutorial_button, QtWidgets.QMessageBox.ActionRole)

        # 显示消息框
        msg_box.exec()

        # 检查哪个按钮被点击
        if msg_box.clickedButton() == tutorial_button:
            tools.open_url("https://pyvideotrans.com/selectmodel")  # 调用模型选择教程的函数

    def update_tips(self, text):
        if not self.update_btn:
            self.update_btn = QtWidgets.QPushButton()
            self.update_btn.setStyleSheet('color:#ffff00;border:0')
            self.update_btn.setCursor(Qt.PointingHandCursor)
            self.update_btn.clicked.connect(lambda: self.open_url('download'))
            self.main.container.addWidget(self.update_btn)
        self.update_btn.setText(text)

    # 关于页面
    def about(self):
        if config.INFO_WIN['win']:
            config.INFO_WIN['win'].show()
            return

        def open():
            from videotrans.component.set_form import InfoForm
            config.INFO_WIN['win'] = InfoForm()
            config.INFO_WIN['win'].show()

        QTimer.singleShot(50, open)


    # 选中按钮时判断当前cuda是否可用
    def check_cuda(self, state):
        import torch
        res = state
        # 选中如果无效，则取消
        if state and not torch.cuda.is_available():
            tools.show_error(tr('nocuda'))
            self.main.enable_cuda.setChecked(False)
            self.main.enable_cuda.setDisabled(True)
            res = False
        self.cfg['cuda'] = res

    def check_voice_autorate(self,state):
        if state:
            self.main.remove_silent_mid.setVisible(False)
            self.main.align_sub_audio.setVisible(False)
        elif not self.main.video_autorate.isChecked():
            self.main.remove_silent_mid.setVisible(True)
            self.main.align_sub_audio.setVisible(True)
    def check_video_autorate(self,state):
        if state:
            self.main.remove_silent_mid.setVisible(False)
            self.main.align_sub_audio.setVisible(False)
        elif not self.main.voice_autorate.isChecked():
            self.main.remove_silent_mid.setVisible(True)
            self.main.align_sub_audio.setVisible(True)


    # 启用标准模式
    def set_biaozhun(self):
        self.main.action_biaozhun.setChecked(True)
        self.main.splitter.setSizes([self.main.width - 300, 300])
        self.main.app_mode = 'biaozhun'
        self.main.show_tips.setText(
            tr("Customize each configuration to batch video translation. When selecting a single video, you can pause to edit subtitles during processing."))
        self.main.startbtn.setText(tr('kaishichuli'))
        self.main.action_tiquzimu.setChecked(False)

        # 仅保存视频行
        self.main.copysrt_rawvideo.hide()

        # 翻译
        self.main.label_9.show()
        self.main.translate_type.show()
        self.main.label_2.show()
        self.main.source_language.show()
        self.main.label_3.show()
        self.main.target_language.show()
        self.main.label.show()
        if config.defaulelang=='zh':
            self.main.proxy.show()

        # 配音角色
        self.main.tts_text.show()
        self.main.tts_type.show()
        self.main.tts_type.setDisabled(False)
        self.main.label_4.show()
        self.main.voice_role.show()
        self.main.listen_btn.show()
        self.main.volume_label.show()
        self.main.volume_rate.show()
        self.main.volume_rate.setDisabled(False)
        self.main.pitch_label.show()
        self.main.pitch_rate.show()
        self.main.pitch_rate.setDisabled(False)

        # 语音识别行
        self.main.reglabel.show()
        self.main.recogn_type.show()
        self.main.model_name_help.show()
        self.main.model_name.show()
        self.main.split_type.show()
        self.main.subtitle_type.setCurrentIndex(1)
        self.main.subtitle_type.show()
        self.main.rephrase.show()
        self.main.remove_noise.show()

        # 字幕对齐行
        self.main.align_btn.show()
        self.main.voice_rate.show()
        self.main.label_6.show()
        self.main.voice_autorate.show()
        self.main.video_autorate.show()
        self.main.label_cjklinenums.show()
        self.main.cjklinenums.show()
        self.main.set_ass.show()
        self.main.label_othlinenums.show()
        self.main.othlinenums.show()
        if platform.system() != 'Darwin':
            self.main.enable_cuda.show()

        if not self.main.voice_autorate.isChecked() and not self.main.video_autorate.isChecked():
            self.main.remove_silent_mid.setVisible(True)
            self.main.align_sub_audio.setVisible(True)
        else:
            self.main.remove_silent_mid.setVisible(False)
            self.main.align_sub_audio.setVisible(False)
        
        # 高级        
        #self.main.set_adv_status.show()
        self.show_adv_status=True
        self.toggle_adv()

    # 视频提取字幕并翻译，无需配音
    def set_tiquzimu(self):
        self.main.action_tiquzimu.setChecked(True)
        self.main.splitter.setSizes([self.main.width - 300, 300])
        self.main.app_mode = 'tiqu'
        self.main.show_tips.setText(tr('tiquzimu'))
        self.main.startbtn.setText(tr('kaishitiquhefanyi'))
        self.main.action_biaozhun.setChecked(False)

        # 仅保存视频行
        self.main.copysrt_rawvideo.show()

        # 翻译
        self.main.label_9.show()
        self.main.translate_type.show()
        self.main.label_2.show()
        self.main.source_language.show()
        self.main.label_3.show()
        self.main.target_language.show()
        self.main.label.show()
        if config.defaulelang=='zh':
            self.main.proxy.show()

        # 配音角色
        self.main.tts_text.hide()
        self.main.tts_type.hide()
        self.main.label_4.hide()
        self.main.voice_role.hide()
        self.main.listen_btn.hide()
        self.main.volume_label.hide()
        self.main.volume_rate.hide()
        self.main.pitch_label.hide()
        self.main.pitch_rate.hide()

        # 语音识别行
        self.main.reglabel.show()
        self.main.recogn_type.show()
        self.main.model_name_help.show()
        self.main.model_name.show()
        self.main.split_type.show()
        self.main.subtitle_type.setCurrentIndex(1)
        self.main.subtitle_type.hide()
        self.main.rephrase.show()
        self.main.remove_noise.show()

        # 字幕对齐行
        self.main.align_btn.hide()
        self.main.label_6.hide()
        self.main.voice_rate.hide()
        self.main.voice_autorate.hide()
        self.main.video_autorate.hide()

        self.main.set_ass.hide()
        self.main.remove_silent_mid.hide()
        self.main.align_sub_audio.hide()
        if platform.system() != 'Darwin':
            self.main.enable_cuda.show()
        
        #self.main.set_adv_status.hide()
        self.show_adv_status=True
        self.toggle_adv()


    # 显示或隐藏高级选项
    def toggle_adv(self):
        self.show_adv_status=not self.show_adv_status
        self.hide_show_element(self.main.hfaster_layout,self.show_adv_status)
        self.hide_show_element(self.main.adv_layout,self.show_adv_status)
        self.hide_show_element(self.main.bgm_layout,self.show_adv_status)
        self.hide_show_element(self.main.trans_thread_layout,self.show_adv_status)
        self.hide_show_element(self.main.dubb_thread_layout,self.show_adv_status)
        self.main.advcontainer.setVisible(self.show_adv_status)

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

    def open_url(self, title):
        tools.open_url(title)


    def clearcache(self):
        question = tools.show_popup(tr('Confirm cleanup?'), tr('After cleaning, you need to restart the software. Only cache and temporary files are cleaned. For configuration information, please directly delete the .json in the videotrans folder.'))

        if question == QtWidgets.QMessageBox.Yes:
            os.chdir(config.ROOT_DIR)
            config.exit_soft=True
            QTimer.singleShot(1000,self._clean_dir)

    def _clean_dir(self):
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
        Path(config.ROOT_DIR+"/videotrans/codec.json").unlink(missing_ok=True)
        Path(config.ROOT_DIR+"/videotrans/ass.json").unlink(missing_ok=True)
        self.main.restart_app()


    def get_mp4(self):
        allowed_exts = config.VIDEO_EXTS + config.AUDIO_EXITS
        format_str = " ".join(['*.' + f for f in allowed_exts])
        mp4_list = []
        if self.main.select_file_type.isChecked():
            """选择文件夹并添加到 selected_files 列表中"""
            folder_path = QtWidgets.QFileDialog.getExistingDirectory(
                self.main,
                tr('Select folder'),
                config.params.get('last_opendir','')
            )

            if not folder_path:
                return
            p = Path(folder_path)

            # 使用列表推导式一行完成
            mp4_list = [
                file.as_posix()
                for file in p.rglob('*')
                if file.is_file() and file.suffix[1:].lower() in allowed_exts
            ]

            config.params['last_opendir'] = p.as_posix()
            self.main.target_dir = p.parent.as_posix()+"/_video_out"
            print(f'{self.main.target_dir=}')
            self.main.btn_save_dir.setToolTip(self.main.target_dir)
        else:
            fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(self.main,
                                                               tr("Select one or more files"),
                                                               config.params.get('last_opendir',''),
                                                               f'Files({format_str})')
            if len(fnames) < 1:
                return
            for (i, it) in enumerate(fnames):
                mp4_list.append(Path(it).as_posix())
            config.params['last_opendir'] = Path(mp4_list[0]).parent.resolve().as_posix()

        if len(mp4_list) > 0:
            self.main.source_mp4.setText(f'{len(mp4_list)} videos')
            self.queue_mp4 = mp4_list

    # 保存目录
    def get_save_dir(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self.main, tr('selectsavedir'),
                                                             config.params.get('last_opendir',''))
        dirname = Path(dirname).as_posix()
        self.main.target_dir = dirname
        self.main.btn_save_dir.setToolTip(self.main.target_dir)

    # 设置或删除代理
    def change_proxy(self, p):
        config.proxy = p.strip()
        if not config.proxy:
            # 删除代理
            tools.set_proxy('del')
            config.settings['proxy'] = ''
        elif re.match(r'https?://(\d+\.){3}\d+:\d+', config.proxy):
            config.settings['proxy'] = config.proxy
        config.parse_init(config.settings)

    
    # 弹出代理设置框
    def proxy_alert(self):        
        from videotrans.component.set_proxy import SetThreadProxy
        dialog = SetThreadProxy()
        if dialog.exec():  # OK 按钮被点击时 exec 返回 True
            proxy = dialog.get_values()
            self.main.proxy.setText(proxy)
    

    # 核对代理填写
    def check_proxy(self):
        proxy = self.main.proxy.text().strip().replace('：', ':')
        if proxy:
            if not re.match(r'^(http|sock)', proxy, re.I):
                proxy = f'http://{proxy}'
            if not re.match(r'^(http|sock)(s|5)?://(\d+\.){3}\d+:\d+', proxy, re.I):
                question = tools.show_popup(
                    tr("Please make sure the proxy address is correct"), tr('The network proxy address you fill in seems to be incorrect, the general proxy/vpn format is http://127.0.0.1:port, if you do not know what is the proxy please do not fill in arbitrarily, ChatGPT and other api address please fill in the menu - settings - corresponding configuration. If you confirm that the proxy address is correct, please click Yes to continue.'))
                if question != QtWidgets.QMessageBox.Yes:
                    self.update_status('stop')
                    return False
        # 设置或删除代理
        config.proxy = proxy
        if config.proxy:
            # 设置代理
            tools.set_proxy(config.proxy)
            config.settings['proxy'] = config.proxy
        else:
            # 删除代理
            config.settings['proxy'] = ''
            tools.set_proxy('del')
        config.parse_init(config.settings)

        return True

    # 核对字幕
    def check_txt(self, txt=''):
        if txt and not re.search(r'\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?\s*?-->\s*?\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?', txt):
            tools.show_error(
                tr("Subtitle format is not correct, please re-import the subtitle or delete the imported subtitle."))
            return False
        return True

    # 如果选中了cuda，判断是否可用
    def cuda_isok(self):
        if not self.main.enable_cuda.isChecked() or platform.system() == 'Darwin':
            self.cfg['cuda'] = False
            return True

        import torch
        from videotrans import recognition
        if not torch.cuda.is_available():
            self.cfg['cuda'] = False
            tools.show_error(tr("nocuda"))
            return False

        if self.main.recogn_type.currentIndex() == recognition.OPENAI_WHISPER:
            self.cfg['cuda'] = True
            return True
        allow = True
        try:
            from torch.backends import cudnn
            if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                allow = False
        except Exception:
            allow = False
        finally:
            if not allow:
                self.cfg['cuda'] = False
                self.main.enable_cuda.setChecked(False)
                tools.show_error(tr("nocudnn"))
                return False
        self.cfg['cuda'] = True
        return True

    # 检测各个模式下参数是否设置正确
    def set_mode(self):
        subtitle_type = self.main.subtitle_type.currentIndex()
        voice_role = self.main.voice_role.currentText()
        self.cfg['copysrt_rawvideo'] = False
        if self.main.app_mode == 'tiqu' or (subtitle_type < 1 and voice_role in ('No', '', " ")):
            self.main.app_mode = 'tiqu'
            # 提取字幕模式，必须有视频、有原始语言，语音模型
            self.cfg['subtitle_type'] = 0
            self.cfg['voice_role'] = 'No'
            self.cfg['voice_rate'] = '+0%'
            self.cfg['voice_autorate'] = False
            self.cfg['back_audio'] = ''
            self.cfg['copysrt_rawvideo'] = self.main.copysrt_rawvideo.isChecked()

    # 导入背景声音
    def get_background(self):
        format_str = " ".join(['*.' + f for f in config.AUDIO_EXITS])
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self.main, 'Background music', config.params.get('last_opendir',''),
                                                         f"Audio files({format_str})")
        if not fname:
            return
        fname = Path(fname).as_posix()
        self.main.back_audio.setText(fname)

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
        self.main.model_name.setDisabled(type)
        self.main.split_type.setDisabled(type)
        self.main.subtitle_type.setDisabled(type)
        self.main.enable_cuda.setDisabled(type)
        self.main.recogn_type.setDisabled(type)
        self.main.voice_autorate.setDisabled(type)
        self.main.video_autorate.setDisabled(type)
        self.main.voice_role.setDisabled(type)
        self.main.voice_rate.setDisabled(type)
        self.main.is_loop_bgm.setDisabled(type)
        self.main.aisendsrt.setDisabled(type)
        self.main.rephrase.setDisabled(type)
        self.main.remove_silent_mid.setDisabled(type)
        self.main.align_sub_audio.setDisabled(type)
        self.main.remove_noise.setDisabled(type)
        self.main.cjklinenums.setDisabled(type)
        self.main.othlinenums.setDisabled(type)
        self.main.bgmvolume.setDisabled(type)
        self.main.set_adv_status.setDisabled(type)
        self.main.select_file_type.setDisabled(type)
        self.main.is_separate.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.addbackbtn.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.back_audio.setReadOnly(True if self.main.app_mode in ['tiqu'] else type)




    def lawalert(self):
        from videotrans.ui.lawalert import Ui_lawalert
        self.law = Ui_lawalert(self.main)
        self.law.show()
        self.law.raise_()
        self.law.activateWindow()

    # 试听配音
    def listen_voice_fun(self):
        import tempfile
        from videotrans import translator
        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if not lang:
            return tools.show_error(
                tr("Please select the target language first"))

        text = config.params.get(f'listen_text_{lang}')
        if not text:
            return tools.show_error(tr("The voice is not support listen"))
        role = self.main.voice_role.currentText()
        if not role or role == 'No':
            return tools.show_error(tr('mustberole'))
        voice_dir = tempfile.gettempdir() + '/pyvideotrans'
        if not Path(voice_dir).exists():
            Path(voice_dir).mkdir(parents=True, exist_ok=True)
        rate = int(self.main.voice_rate.value())
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"

        volume = int(self.main.volume_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = int(self.main.pitch_rate.value())
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{volume}Hz'

        voice_file = f"{voice_dir}/{time.time()}.wav"
        obj = {
            "text": text,
            "rate": rate,
            "role": role,
            "filename": voice_file,
            "tts_type": self.main.tts_type.currentIndex(),
            "language": lang,
            "volume": volume,
            "pitch": pitch,
        }
        if role == 'clone':
            tools.show_error(
                tr("The original sound clone cannot be auditioned"))
            return

        def feed(d):
            if d != "ok":
                tools.show_error(d)

        wk = ListenVoice(parent=self.main, queue_tts=[obj], language=lang, tts_type=obj['tts_type'])
        wk.uito.connect(feed)
        wk.start()

    # 角色改变时 显示试听按钮
    def show_listen_btn(self, role):
        voice_role = self.main.voice_role.currentText()
        if role == 'No' or voice_role == 'clone':
            self.main.listen_btn.hide()
            return
        if self.main.app_mode in ['biaozhun']:
            self.main.listen_btn.show()
            self.main.listen_btn.setDisabled(False)


    # 如果存在音频则设为提取
    def check_name(self):
        if self.main.app_mode != 'tiqu':
            for it in self.queue_mp4:
                if Path(it).suffix.lower() in config.AUDIO_EXITS:
                    self.main.app_mode = 'tiqu'
                    self.cfg['is_separate'] = False
                    break
        return True


