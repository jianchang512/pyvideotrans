import os
import platform
import re
import shutil
import sys
import threading
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtCore import QTimer

from PySide6.QtWidgets import QMessageBox, QFileDialog, QPushButton

from videotrans import translator, tts,recognition
from videotrans.configure import config
from videotrans.util import tools


class WinActionSub:

    def show_model_help(self):
        
        msg="从 tiny 到 base -> small -> medium -> large-v3 模型，识别效果越来越好，但模型体积越来越大，识别速度越来越慢，需要更多CPU/内存/GPU资源。\n默认使用tiny模型，如果想要更好的效果，请使用更大模型\n\n .en 后缀模型和 distil 开头的模型只用于识别英文发音视频\n"
        if config.defaulelang!='zh':
            msg='From tiny model to base to small to medium to large-v3 model, the recognition effect is getting better and better, but the model size is getting bigger and bigger, the recognition speed is getting slower and slower, and it needs more CPU/memory/GPU resources. \n default is to use tiny model, if you want better result, please use bigger model \n\n.en suffix model and model starting with distil is only used to recognize English pronunciation video\n'

        # 创建 QMessageBox
        msg_box = QMessageBox(self.main)
        msg_box.setWindowTitle("Help")
        msg_box.setText(msg)

        # 添加 OK 按钮
        ok_button = msg_box.addButton(QMessageBox.Ok)
        ok_button.setText("知道了" if config.defaulelang=='zh' else 'OK')

        # 添加“模型选择教程”按钮
        tutorial_button = QPushButton("点击查看模型选择教程" if config.defaulelang=='zh' else "Model Selection Tutorial")
        msg_box.addButton(tutorial_button, QMessageBox.ActionRole)

        # 显示消息框
        msg_box.exec()

        # 检查哪个按钮被点击
        if msg_box.clickedButton() == tutorial_button:
            tools.open_url("https://pyvideotrans.com/selectmodel")  # 调用模型选择教程的函数

    def update_tips(self,text):
        if not self.update_btn:
            self.update_btn = QPushButton()
            self.update_btn.setStyleSheet('color:#ffff00;border:0')
            self.update_btn.setCursor(QtCore.Qt.PointingHandCursor)
            self.update_btn.clicked.connect(lambda: self.open_url('download'))
            self.main.container.addWidget(self.update_btn)
        self.update_btn.setText(text)
    # 关于页面
    def about(self):
        if config.INFO_WIN['win']:
            config.INFO_WIN['win'].show()
            return
        def open():
            from videotrans.component import InfoForm
            config.INFO_WIN['win'] = InfoForm()
            config.INFO_WIN['win'].show()
        QTimer.singleShot(50,open)

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
        self.cfg['cuda'] = res

    # 简单新手模式
    def set_xinshoujandann(self):

        self.main.splitter.setSizes([self.main.width, 0])
        self.main.action_xinshoujandan.setChecked(True)
        self.main.app_mode = 'biaozhun_jd'
        self.main.show_tips.setText(config.transobj['xinshoumoshitips'])
        self.main.startbtn.setText(config.transobj['kaishichuli'])
        self.main.action_biaozhun.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)

        # 仅保存视频行
        self.main.only_video.setChecked(False)
        self.main.only_video.hide()

        # 翻译
        self.main.translate_type.setCurrentIndex(1)
        self.main.label_9.hide()
        self.main.translate_type.hide()
        self.main.label_2.show()
        self.main.source_language.show()
        self.main.label_3.show()
        self.main.target_language.show()
        self.main.label.hide()
        self.main.proxy.hide()

        # 配音角色
        self.main.tts_text.show()
        self.main.tts_type.setCurrentIndex(0)
        self.main.tts_type.setDisabled(True)
        self.main.tts_type.show()
        self.main.label_4.show()
        self.main.voice_role.show()
        self.main.listen_btn.show()
        self.main.volume_rate.setDisabled(True)
        self.main.volume_rate.show()
        self.main.volume_label.show()
        self.main.pitch_label.show()
        self.main.pitch_rate.setDisabled(True)
        self.main.pitch_rate.show()


        # 语音识别行
        self.main.split_type.setCurrentIndex(0)
        self.main.model_name.setCurrentIndex(0)
        self.main.reglabel.hide()
        self.main.recogn_type.setCurrentIndex(0)
        self.main.recogn_type.hide()
        self.main.model_name_help.hide()
        self.main.model_name.hide()
        self.main.split_label.hide()
        self.main.split_type.hide()
        self.main.subtitle_type.setCurrentIndex(1)
        self.main.label_8.hide()
        self.main.subtitle_type.hide()




        # 字幕对齐行
        self.main.align_btn.hide()
        self.main.label_6.hide()
        self.main.voice_rate.hide()
        self.main.append_video.setChecked(True)
        self.main.append_video.hide()
        self.main.voice_autorate.setChecked(True)
        self.main.voice_autorate.hide()
        self.main.video_autorate.setChecked(True)
        self.main.video_autorate.hide()
        self.main.is_separate.setChecked(False)
        self.main.is_separate.hide()
        self.main.enable_cuda.setChecked(False)
        self.main.enable_cuda.hide()
        # 添加背景行
        self.main.addbackbtn.hide()
        self.main.back_audio.hide()


    # 启用标准模式
    def set_biaozhun(self):
        self.main.action_biaozhun.setChecked(True)
        self.main.splitter.setSizes([self.main.width-300, 300])
        self.main.app_mode = 'biaozhun'
        self.main.show_tips.setText("自定义各项配置，批量进行视频翻译。选择单个视频时，处理过程中可暂停编辑字幕" if config.defaulelang=='zh' else 'Customize each configuration to batch video translation. When selecting a single video, you can pause to edit subtitles during processing.')
        self.main.startbtn.setText(config.transobj['kaishichuli'])
        self.main.action_xinshoujandan.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)

        # 仅保存视频行
        self.main.only_video.setDisabled(False)
        self.main.only_video.show()

        # 翻译
        self.main.translate_type.setCurrentIndex(1)
        self.main.label_9.show()
        self.main.translate_type.show()
        self.main.label_2.show()
        self.main.source_language.show()
        self.main.label_3.show()
        self.main.target_language.show()
        self.main.label.show()
        self.main.proxy.show()

        # 配音角色
        self.main.tts_type.setCurrentIndex(tts.EDGE_TTS)
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
        self.main.split_type.setCurrentIndex(0)
        self.main.model_name.setCurrentIndex(0)
        self.main.reglabel.show()
        self.main.recogn_type.show()
        self.main.model_name_help.show()
        self.main.model_name.show()
        self.main.split_label.show()
        self.main.split_type.show()
        self.main.subtitle_type.setCurrentIndex(1)
        self.main.label_8.show()
        self.main.subtitle_type.show()

        # 字幕对齐行
        self.main.align_btn.show()
        self.main.voice_rate.show()
        self.main.label_6.show()
        self.main.append_video.setChecked(True)
        self.main.append_video.show()
        self.main.voice_autorate.setChecked(True)
        self.main.voice_autorate.show()
        self.main.video_autorate.setChecked(True)
        self.main.video_autorate.show()
        self.main.is_separate.setDisabled(False)
        self.main.is_separate.setChecked(False)
        self.main.is_separate.show()
        self.main.enable_cuda.setChecked(False)
        if platform.system() != 'Darwin':
            self.main.enable_cuda.show()
        # 添加背景行
        self.main.addbackbtn.show()
        self.main.back_audio.show()

    # 视频提取字幕并翻译，无需配音
    def set_tiquzimu(self):
        self.main.action_tiquzimu.setChecked(True)
        self.main.splitter.setSizes([self.main.width-300, 300])
        self.main.app_mode = 'tiqu'
        self.main.show_tips.setText(config.transobj['tiquzimu'])
        self.main.startbtn.setText(config.transobj['kaishitiquhefanyi'])
        self.main.action_xinshoujandan.setChecked(False)
        self.main.action_biaozhun.setChecked(False)

        # 仅保存视频行
        self.main.only_video.setChecked(False)
        self.main.only_video.hide()

        # 翻译
        self.main.translate_type.setCurrentIndex(1)
        self.main.label_9.show()
        self.main.translate_type.show()
        self.main.label_2.show()
        self.main.source_language.show()
        self.main.label_3.show()
        self.main.target_language.show()
        self.main.label.show()
        self.main.proxy.show()

        # 配音角色
        self.main.tts_type.setCurrentIndex(tts.EDGE_TTS)
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
        self.main.split_type.setCurrentIndex(0)
        self.main.model_name.setCurrentIndex(0)
        self.main.reglabel.show()
        self.main.recogn_type.show()
        self.main.model_name_help.show()
        self.main.model_name.show()
        self.main.split_label.show()
        self.main.split_type.show()
        self.main.subtitle_type.setCurrentIndex(1)
        self.main.label_8.hide()
        self.main.subtitle_type.hide()

        # 字幕对齐行
        self.main.align_btn.hide()
        self.main.label_6.hide()
        self.main.voice_rate.hide()
        self.main.append_video.setChecked(True)
        self.main.append_video.hide()
        self.main.voice_autorate.setChecked(True)
        self.main.voice_autorate.hide()
        self.main.video_autorate.setChecked(True)
        self.main.video_autorate.hide()

        self.main.is_separate.setChecked(False)
        self.main.is_separate.hide()
        self.main.enable_cuda.setChecked(False)
        if platform.system() != 'Darwin':
            self.main.enable_cuda.show()
        # 添加背景行
        self.main.addbackbtn.hide()
        self.main.back_audio.hide()

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
        if title == 'online':
            self.about()
        else:
            tools.open_url(title=title)

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



    def get_mp4(self):
        if self.main.app_mode == 'tiqu':
            allowed_exts = config.VIDEO_EXTS + config.AUDIO_EXITS
        else:
            allowed_exts = config.VIDEO_EXTS
        format_str = " ".join(['*.' + f for f in allowed_exts])
        mp4_list=[]
        if self.main.select_file_type.isChecked():
            """选择文件夹并添加到 selected_files 列表中"""
            folder_path = QFileDialog.getExistingDirectory(
                self.main,
                "选择文件夹" if config.defaulelang else 'Select folder',
                config.params['last_opendir']
                # QDir.currentPath()
            )

            if not folder_path:
                return
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if Path(file).suffix[1:].lower() in allowed_exts:
                        mp4_list.append(os.path.join(root, file).replace(os.sep, '/'))
            p=Path(folder_path)
            config.params['last_opendir'] = p.parent.as_posix()
            self.main.target_dir=config.params['last_opendir']+f'/{p.name}_video_out'
            self.main.btn_save_dir.setToolTip(self.main.target_dir)
        else:
            fnames, _ = QFileDialog.getOpenFileNames(self.main,
                                                     '选择一或多个文件' if config.defaulelang=='zh' else "Select one or more files",
                                                     config.params['last_opendir'],
                                                     f'Files({format_str})')
            if len(fnames) < 1:
                return
            for (i, it) in enumerate(fnames):
                mp4_list.append(Path(it).as_posix())
            config.params['last_opendir'] = Path(mp4_list[0]).parent.resolve().as_posix()
            self.main.target_dir=config.params['last_opendir']+f'/_video_out'
            self.main.btn_save_dir.setToolTip(self.main.target_dir)

        if len(mp4_list) > 0:
            self.main.source_mp4.setText(f'{len((mp4_list))} videos')
            self.queue_mp4 = mp4_list

    # 保存目录
    def get_save_dir(self):
        dirname = QFileDialog.getExistingDirectory(self.main, config.transobj['selectsavedir'],
                                                   config.params['last_opendir'])
        dirname = Path(dirname).as_posix()
        self.main.target_dir=dirname
        self.main.btn_save_dir.setToolTip(self.main.target_dir)

    # 设置或删除代理
    def change_proxy(self, p):
        config.proxy = p.strip()
        try:
            if not config.proxy:
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
        config.proxy = proxy
        try:
            if config.proxy:
                # 设置代理
                tools.set_proxy(config.proxy)
            else:
                # 删除代理
                tools.set_proxy('del')
        except Exception:
            pass
        return True

    # 核对字幕
    def check_txt(self, txt=''):
        if txt and not re.search(r'\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?\s*?-->\s*?\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?', txt):
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 '字幕格式不正确，请重新导入字幕或删除已导入字幕' if config.defaulelang == 'zh' else 'Subtitle format is not correct, please re-import the subtitle or delete the imported subtitle.')
            return False
        return True

    # 如果选中了cuda，判断是否可用
    def cuda_isok(self):
        if not self.main.enable_cuda.isChecked() or platform.system() == 'Darwin':
            self.cfg['cuda']=False
            return True

        import torch
        if not torch.cuda.is_available():
            self.cfg['cuda']=False
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocuda"])
            return False

        if self.main.recogn_type.currentIndex() == recognition.OPENAI_WHISPER:
            self.cfg['cuda']=True
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
                self.cfg['cuda']=False
                self.main.enable_cuda.setChecked(False)
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocudnn"])
                return False
        self.cfg['cuda']=True
        return True

    # 检测各个模式下参数是否设置正确
    def set_mode(self):
        subtitle_type=self.main.subtitle_type.currentIndex()
        voice_role=self.main.voice_role.currentText()
        if self.main.app_mode == 'tiqu' or (self.main.app_mode.startswith('biaozhun') and subtitle_type < 1 and voice_role in ('No',''," ")):
            self.main.app_mode = 'tiqu'
            # 提取字幕模式，必须有视频、有原始语言，语音模型
            self.cfg['is_separate'] = False
            self.cfg['subtitle_type'] = 0
            self.cfg['voice_role'] = 'No'
            self.cfg['voice_rate'] = '+0%'
            self.cfg['voice_autorate'] = False
            self.cfg['append_video'] = False
            self.cfg['back_audio'] = ''
        elif self.main.app_mode == 'biaozhun_jd':
            self.cfg['voice_autorate'] = True
            self.cfg['append_video'] = True
            self.cfg['is_separate'] = False
            self.cfg['back_audio'] = ''

    # 导入背景声音
    def get_background(self):
        format_str = " ".join(['*.' + f for f in config.AUDIO_EXITS])
        fname, _ = QFileDialog.getOpenFileName(self.main, 'Background music', config.params['last_opendir'],
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
        self.main.append_video.setDisabled(type)
        self.main.voice_role.setDisabled(type)
        self.main.voice_rate.setDisabled(type)
        self.main.only_video.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.is_separate.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.addbackbtn.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.back_audio.setReadOnly(True if self.main.app_mode in ['tiqu'] else type)

    # 0=整体识别模型
    # 1=均等分割模式
    def check_split_type(self, index):
        index = self.main.split_type.currentIndex()
        self.cfg['split_type'] = ['all','avg'][index]
        recogn_type = self.main.recogn_type.currentIndex()
        # 如果是均等分割，则阈值相关隐藏
        if recogn_type > 0:
            tools.hide_show_element(self.main.hfaster_layout, False)
            tools.hide_show_element(self.main.equal_split_layout, False)
        elif index == 1:
            tools.hide_show_element(self.main.equal_split_layout, True)
            tools.hide_show_element(self.main.hfaster_layout, False)
        else:
            tools.hide_show_element(self.main.equal_split_layout, False)

    # 试听配音
    def listen_voice_fun(self):
        import tempfile
        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if not lang:
            return QMessageBox.critical(self.main, config.transobj['anerror'],
                                        '请先选择目标语言' if config.defaulelang == 'zh' else 'Please select the target language first')
        text = config.params[f'listen_text_{lang}']
        role = self.main.voice_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['mustberole'])
        voice_dir = tempfile.gettempdir()+'/pyvideotrans'
        if not Path(voice_dir).exists():
            Path(voice_dir).mkdir(parents=True, exist_ok=True)
        lujing_role = role.replace('/', '-')
        rate = int(self.main.voice_rate.value())
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"

        volume = int(self.main.volume_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = int(self.main.pitch_rate.value())
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{volume}Hz'

        voice_file = f"{voice_dir}/{self.main.tts_type.currentIndex()}-{lang}-{lujing_role}-{volume}-{pitch}.mp3"

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
            QMessageBox.critical(self.main, config.transobj['anerror'],
                                 '原音色克隆不可试听' if config.defaulelang == 'zh' else 'The original sound clone cannot be auditioned')
            return
        threading.Thread(target=tts.run, kwargs={"queue_tts": [obj], "play": True, "is_test": True}).start()

    # 角色改变时 显示试听按钮
    def show_listen_btn(self, role):
        # config.params["voice_role"] = role
        tts_type=self.main.tts_type.currentIndex()
        voice_role = self.main.voice_role.currentText()
        if role == 'No' or (tts_type == tts.CLONE_VOICE_TTS and voice_role == 'clone'):
            self.main.listen_btn.hide()
            return
        if self.main.app_mode in ['biaozhun']:
            self.main.listen_btn.show()
            self.main.listen_btn.setDisabled(False)

    # 判断文件路径是否正确
    def url_right(self):
        if sys.platform != 'win32':
            return True
        for vurl in self.queue_mp4:
            if re.search(r'[:\?\*<>\|\"]', vurl[4:]):
                return QMessageBox.critical(self.main, config.transobj['anerror'],
                                            '视频所在路径和视频名字中不可含有  :  * ? < > | "  符号，请修正 ' if config.defaulelang == 'zh' else 'The path and name of the video must not contain the  : * ? < > | "  symbols, please revise. ')
            if len(vurl) > 255:
                return QMessageBox.critical(self.main, config.transobj['anerror'],
                                            f'视频路径总长度超过255个字符，处理中可能会出错，请改短视频文件名，并移动到浅层目录下url={vurl}' if config.defaulelang == 'zh' else f'The total length of the video path is more than 255 characters, there may be an error in processing, please change the short video file name and move it to a shallow directoryurl={vurl}')
        return True

    # 如果存在音频则设为提取
    # 如果有同名则停止
    def check_name(self):
        if self.main.app_mode != 'tiqu':
            for it in self.queue_mp4:
                if Path(it).suffix.lower() in config.AUDIO_EXITS:
                    self.main.app_mode = 'tiqu'
                    self.cfg['is_separate'] = False
                    break

        if len(self.queue_mp4) > 1:
            same_name = {}
            for it in self.queue_mp4:
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
