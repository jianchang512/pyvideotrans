import json
import os
import re
import shutil
import threading
from PySide6 import QtCore
from PySide6.QtGui import QTextCursor, QDesktopServices
from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import QMessageBox, QFileDialog, QLabel, QPushButton, QHBoxLayout, QProgressBar
import warnings

warnings.filterwarnings('ignore')
from videotrans import configure
from videotrans.task.job import start_thread
from videotrans.util import tools
from videotrans import translator
from videotrans.configure import config
from pathlib import Path


class ClickableProgressBar(QLabel):
    def __init__(self,parent=None):
        super().__init__()
        self.target_dir = None
        self.msg=None
        self.parent=parent

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(35)
        self.progress_bar.setRange(0, 100)  # 设置进度范围
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: transparent;
                border:1px solid #32414B;
                color:#fff;
                height:35px;
                text-align:left;
                border-radius:3px;                
            }
            QProgressBar::chunk {
                width: 8px;
                border-radius:0;           
            }
        """)
        layout = QHBoxLayout(self)
        layout.addWidget(self.progress_bar)  # 将进度条添加到布局

    def setTarget(self, url):
        self.target_dir = url
    def setMsg(self, text):
        if text and config.defaulelang=='zh':
            text+='\n\n请尝试在文档站 pyvideotrans.com 搜索错误解决方案\n'
        self.msg = text
        

    def setText(self, text):
        if self.progress_bar:
            self.progress_bar.setFormat(f' {text}')  # set text format

    def mousePressEvent(self, event):
        if self.target_dir and event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.target_dir))
        elif not self.target_dir and self.msg:
            QMessageBox.critical(self,config.transobj['anerror'],self.msg)


# primary ui
class SecWindow():
    def __init__(self, main=None):
        self.main = main
        self.usetype = None

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
        # text = str(text).replace('+', '').replace('%', '').strip()
        # text = 0 if not text else int(text)
        # text = f'+{text}%' if text >= 0 else f'{text}%'
        config.params['voice_rate'] = f'+{text}%' if text>=0 else f'{text}%'

    # 简单新手模式
    def set_xinshoujandann(self):
        self.main.action_xinshoujandan.setChecked(True)
        self.main.app_mode = 'biaozhun_jd'
        self.main.show_tips.setText(config.transobj['xinshoumoshitips'])
        self.main.startbtn.setText(config.transobj['kaishichuli'])
        self.main.action_xinshoujandan.setChecked(True)
        self.main.action_biaozhun.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)
        self.main.action_zimu_video.setChecked(False)
        self.main.action_zimu_peiyin.setChecked(False)

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
        # self.main.auto_ajust.setDisabled(True)

        self.main.is_separate.hide()
        self.main.addbackbtn.hide()
        self.main.back_audio.hide()
        self.main.only_video.hide()
        # self.main.auto_ajust.hide()

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
        self.main.action_zimu_video.setChecked(False)
        self.main.action_zimu_peiyin.setChecked(False)

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
        # self.main.auto_ajust.setDisabled(False)
        # self.main.auto_ajust.show()

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
        self.main.action_zimu_video.setChecked(False)
        self.main.action_zimu_peiyin.setChecked(False)

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

    # 启用字幕合并模式, 仅显示 选择视频、保存目录、字幕类型、 cuda
    # 不配音、不识别，
    def set_zimu_video(self):
        self.main.action_zimu_video.setChecked(True)
        self.main.app_mode = 'hebing'
        self.main.show_tips.setText(config.transobj['zimu_video'])
        self.main.startbtn.setText(config.transobj['kaishihebing'])
        self.main.action_zimu_video.setChecked(True)
        self.main.action_xinshoujandan.setChecked(False)
        self.main.action_biaozhun.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)
        self.main.action_zimu_peiyin.setChecked(False)

        self.hide_show_element(self.main.subtitle_layout, True)
        self.main.splitter.setSizes([self.main.width - 400, 400])

        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)

        # 隐藏音量 音调变化
        self.hide_show_element(self.main.edge_volume_layout, False)

        # 翻译渠道
        self.hide_show_element(self.main.layout_translate_type, False)
        # 代理
        self.hide_show_element(self.main.layout_proxy, False)
        # 原始语言
        self.hide_show_element(self.main.layout_source_language, False)
        # 目标语言
        self.hide_show_element(self.main.layout_target_language, False)
        # tts类型
        self.hide_show_element(self.main.layout_tts_type, False)
        # 配音角色
        self.hide_show_element(self.main.layout_voice_role, False)
        # 试听按钮

        self.main.listen_btn.hide()
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, False)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, True)

        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, False)

        # 配音自动加速

        self.main.only_video.setDisabled(False)
        self.main.is_separate.setDisabled(True)
        self.main.addbackbtn.setDisabled(True)
        self.main.back_audio.setReadOnly(True)
        # self.main.auto_ajust.setDisabled(True)
        self.main.video_autorate.setDisabled(True)
        self.main.append_video.setDisabled(True)
        self.main.voice_autorate.setDisabled(True)

        self.main.only_video.show()
        self.main.voice_autorate.hide()
        self.main.is_separate.hide()
        self.main.addbackbtn.hide()
        self.main.back_audio.hide()
        # self.main.auto_ajust.hide()
        self.main.video_autorate.hide()
        self.main.append_video.hide()

        # cuda
        self.main.enable_cuda.show()

    # 仅仅对已有字幕配音，
    # 不翻译不识别
    def set_zimu_peiyin(self):
        self.main.action_zimu_peiyin.setChecked(True)
        self.main.show_tips.setText(config.transobj['zimu_peiyin'])
        self.main.startbtn.setText(config.transobj['kaishipeiyin'])
        self.main.action_zimu_peiyin.setChecked(True)
        self.main.action_xinshoujandan.setChecked(False)
        self.main.action_biaozhun.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)
        self.main.action_zimu_video.setChecked(False)
        self.main.app_mode = 'peiyin'

        self.hide_show_element(self.main.subtitle_layout, True)
        self.main.splitter.setSizes([self.main.width - 400, 400])
        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, False)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)

        # 显示音量 音调变化
        self.hide_show_element(self.main.edge_volume_layout, True)

        # 翻译渠道
        self.hide_show_element(self.main.layout_translate_type, False)
        # 代理 openaitts
        self.hide_show_element(self.main.layout_proxy, True)

        # 原始语言
        self.hide_show_element(self.main.layout_source_language, False)
        # 目标语言
        self.hide_show_element(self.main.layout_target_language, True)
        # tts类型
        self.hide_show_element(self.main.layout_tts_type, True)
        # 配音角色
        self.hide_show_element(self.main.layout_voice_role, True)
        # 试听按钮

        self.main.listen_btn.show()
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, False)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, False)

        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, True)
        # 静音片段

        # 配音自动加速
        # 视频自动降速
        self.main.is_separate.setDisabled(True)
        self.main.only_video.setDisabled(True)
        self.main.video_autorate.setDisabled(True)
        self.main.append_video.setDisabled(True)
        self.main.voice_autorate.setDisabled(False)
        # self.main.auto_ajust.setDisabled(False)
        self.main.back_audio.setReadOnly(False)
        self.main.addbackbtn.setDisabled(False)

        self.main.voice_autorate.show()
        self.main.is_separate.hide()
        self.main.video_autorate.hide()
        self.main.append_video.hide()
        self.main.only_video.hide()
        # self.main.auto_ajust.show()
        self.main.back_audio.show()
        self.main.addbackbtn.show()

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
        # elif name == 'auto_ajust':
        #     config.params['auto_ajust'] = state
        elif name == 'video':
            config.params['video_autorate'] = state
        elif name=='append_video':
            config.params['append_video']=state

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
        self.main.only_video.setDisabled(True if self.main.app_mode in ['tiqu', 'peiyin'] else type)
        self.main.is_separate.setDisabled(True if self.main.app_mode in ['tiqu', 'peiyin'] else type)
        self.main.addbackbtn.setDisabled(True if self.main.app_mode in ['tiqu', 'hebing'] else type)
        self.main.back_audio.setReadOnly(True if self.main.app_mode in ['tiqu', 'hebing'] else type)
        # self.main.auto_ajust.setDisabled(True if self.main.app_mode in ['tiqu', 'hebing'] else type)

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
            webbrowser.open_new_tab("https://juejin.cn/user/4441682704623992/columns")
        elif title == 'ffmpeg':
            webbrowser.open_new_tab("https://www.ffmpeg.org/download.html")
        elif title == 'git':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans")
        elif title == 'issue':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/issues")
        elif title == 'discord':
            webbrowser.open_new_tab("https://discord.gg/y9gUweVCCJ")
        elif title == 'models':
            webbrowser.open_new_tab("https://github.com/jianchang512/stt/releases/tag/0.0")
        elif title == 'dll':
            webbrowser.open_new_tab("https://github.com/jianchang512/stt/releases/tag/v0.0.1")
        elif title == 'gtrans':
            webbrowser.open_new_tab("https://www.pyvideotrans.com/15.html")
        elif title == 'cuda':
            webbrowser.open_new_tab("https://www.pyvideotrans.com/gpu.html")
        elif title in ('website', 'help'):
            webbrowser.open_new_tab("https://pyvideotrans.com")
        elif title == 'xinshou':
            webbrowser.open_new_tab("https://www.pyvideotrans.com/guide.html")
        elif title == "about":
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/blob/main/about.md")
        elif title == 'download':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/releases")
        elif title=='openvoice':
            webbrowser.open_new_tab("https://github.com/kungful/openvoice-api")
            
        elif title == 'online':
            QMessageBox.information(self.main,'免责声明',"""
免责声明：

在您下载或使用 "pyVideoTrans视频翻译配音" 软件（以下简称"本软件"）前，请仔细阅读并充分理解本免责声明中的各项条款。

您的下载、安装或使用行为将被视为对本免责声明的接受，并同意按照本声明内容约束自己的行为。如果您不同意本声明的任何条款，请不要下载、安装或使用本软件。

本软件所有源码均在 https://github.com/jianchang512/pyvideotrans 上开放。

1. 本软件是由独立开发者使用开源语音识别模型并结合第三方翻译API和第三方配音API开发的免费工具，旨在提供视频翻译和配音功能。开发者保证在软件运行过程中不会获取或存储用户数据。

2. 本软件中集成的语音识别功能（openai和faster模式）完全在本地环境下运行，不涉及将任何数据发送到开发者的服务器。当使用第三方翻译API和配音API时，相关数据将由用户的计算机直接传输至第三方服务器，未经开发者服务器处理。本软件无需用户注册或登录，不收集或存储任何个人信息。

3. 本软件纯属个人爱好项目，开发者无营利目的，未制定任何盈利计划，并不提供付费技术支持或其他付费服务。

4. 本软件不提供视频内容转移的功能，也不鼓励或支持任何形式的视频内容搬运行为。本软件仅旨在降低观赏外语视频时的语言障碍。

5. 用户在使用本软件时，须自觉遵守当地法律以及中华人民共和国的法律法规，敬重并维护他人版权和知识产权。

6. 用户因违反法律法规或侵犯他人权利而造成的任何后果，由用户本人承担，本软件开发者不承担任何连带责任。

7. 鉴于开发者从本软件中未获利，对于本软件的使用引发的任何问题或损失，开发者不负责任。

8. 本软件采用GPL-v3开源协议。任何基于本软件的二次开发或分支版本，需遵循GPL-v3协议规定，遵守相应义务和约束。

本软件的所有解释权均属于开发者。谨请用户在理解、同意、遵守本免责声明的前提下使用本软件。                
            """)

    # 工具箱
    def open_toolbox(self, index=0, is_hide=True):
        try:
            if configure.TOOLBOX is None:
                QMessageBox.information(self.main, "pyVideoTrans",
                                        "尚未完成初始化，请稍等重试" if config.defaulelang == 'zh' else "Retry hold on a monment!")
                return
            if is_hide:
                configure.TOOLBOX.hide()
                return
            configure.TOOLBOX.show()
            configure.TOOLBOX.tabWidget.setCurrentIndex(index)
            configure.TOOLBOX.raise_()
        except Exception as e:
            configure.TOOLBOX = None
            QMessageBox.critical(self.main, config.transobj['anerror'], str(e))
            config.logger.error("box" + str(e))

    # 将倒计时设为立即超时
    def set_djs_timeout(self):
        config.task_countdown = 0
        self.main.continue_compos.setText(config.transobj['jixuzhong'])
        self.main.continue_compos.setDisabled(True)
        self.main.stop_djs.hide()
        if self.main.shitingobj:
            self.main.shitingobj.stop = True

    # 手动点击停止自动合并倒计时
    def reset_timeid(self):
        self.main.stop_djs.hide()
        config.task_countdown = 86400
        self.main.continue_compos.setDisabled(False)
        self.main.continue_compos.setText(config.transobj['nextstep'])

    # 翻译渠道变化时，检测条件
    def set_translate_type(self, name):
        try:
            rs = translator.is_allow_translate(translate_type=name, only_key=True)
            if rs is not True:
                QMessageBox.critical(self.main, config.transobj['anerror'], rs)
                if name == translator.TRANSAPI_NAME:
                    self.main.subform.set_transapi()
                elif name == translator.CHATGPT_NAME:
                    self.main.subform.set_chatgpt_key()
                elif name == translator.LOCALLLM_NAME:
                    self.main.subform.set_localllm_key()
                elif name == translator.GEMINI_NAME:
                    self.main.subform.set_gemini_key()
                elif name == translator.AZUREGPT_NAME:
                    self.main.subform.set_azure_key()
                elif name == translator.BAIDU_NAME:
                    self.main.subform.set_transapi()
                elif name == translator.TENCENT_NAME:
                    self.main.subform.set_transapi()
                elif name == translator.DEEPL_NAME:
                    self.main.subform.set_transapi()
                elif name == translator.DEEPLX_NAME:
                    self.main.subform.set_transapi()
                elif name == translator.OTT_NAME:
                    self.main.subform.set_transapi()
                elif name == translator.ZIJIE_NAME:
                    self.main.subform.set_zijiehuoshan_key()
                return
            config.params['translate_type'] = name
        except Exception as e:
            QMessageBox.critical(self.main, config.transobj['anerror'], str(e))

    # 0=整体识别模型
    # 1=预先分割模式
    def check_whisper_type(self, index):
        if index == 0:
            config.params['whisper_type'] = 'all'
        elif index == 1:
            config.params['whisper_type'] = 'split'
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
            lang=self.main.source_language.currentText()
            if translator.get_code(show_text=lang) not in ['zh-cn','zh-tw']:
                self.main.model_type.setCurrentIndex(0)
                return QMessageBox.critical(self.main,config.transobj['anerror'],'zh_recogn 仅支持中文语音识别' if config.defaulelang=='zh' else 'zh_recogn Supports Chinese speech recognition only')

            config.params['model_type'] = 'zh_recogn'
            self.main.whisper_model.setDisabled(True)
            self.main.whisper_type.setDisabled(True)
            if not config.params['zh_recogn_api']:
                self.main.subform.set_zh_recogn()
        elif self.main.model_type.currentIndex() == 4:
            lang=self.main.source_language.currentText()
            langcode=translator.get_code(show_text=lang)
            if not langcode or langcode[:2] not in ["zh","en","ja","ko","fr","es","ru"]:
                self.main.model_type.setCurrentIndex(0)
                return QMessageBox.critical(self.main,config.transobj['anerror'],'豆包语音识别仅支持中英日韩法俄西班牙语言，其他不支持')
            config.params['model_type'] = 'doubao'
            self.main.whisper_model.setDisabled(True)
            self.main.whisper_type.setDisabled(True)
            if not config.params['doubao_appid']:
                self.main.subform.set_doubao()
        else:
            self.main.whisper_type.setDisabled(False)
            self.main.whisper_model.setDisabled(False)
            config.params['model_type'] = 'faster'
            self.check_whisper_model(self.main.whisper_model.currentText())

    # 判断模型是否存在
    def check_whisper_model(self, name):
        if self.main.model_type.currentIndex() in [2,3]:
            return True
        if name.find('/')>0:
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
            question = tools.show_popup('清理后需要重启软件', '确认进行清理？')

        else:
            question = tools.show_popup('The software needs to be restarted after cleaning', 'Confirm cleanup?')

        if question == QMessageBox.Yes:
            shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
            shutil.rmtree(config.homedir + "/tmp", ignore_errors=True)
            tools.remove_qsettings_data()
            QMessageBox.information(self.main, 'Please restart the software' if config.defaulelang != 'zh' else '请重启软件',
                                    'Please restart the software' if config.defaulelang != 'zh' else '软件将自动关闭，请重新启动')
            self.main.close()

    # tts类型改变
    def tts_type_change(self, type):
        self.hide_show_element(self.main.edge_volume_layout,True if type in ['edgeTTS','AzureTTS'] else False)
        if self.main.app_mode == 'peiyin' and type == 'clone-voice' and config.params['voice_role'] == 'clone':
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj[
                'Clone voice cannot be used in subtitle dubbing mode as there are no replicable voices'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            self.main.subform.set_clone_address()
            return
        if type == 'TTS-API' and not config.params['ttsapi_url']:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['ttsapi_nourl'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            self.main.subform.set_ttsapi()
            return
        if type == 'GPT-SoVITS' and not config.params['gptsovits_url']:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['nogptsovitsurl'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            self.main.subform.set_gptsovits()
            return
        if type == 'ChatTTS' and not config.params['chattts_api']:
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            self.main.subform.set_chattts_address()
            return

        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if lang and lang != '-' and type == 'GPT-SoVITS' and lang[:2] not in ['zh', 'ja', 'en']:
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['nogptsovitslanguage'])
            return
        if lang and lang != '-' and type == 'ChatTTS' and lang[:2] not in ['zh', 'en']:
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['onlycnanden'])
            return

        config.params['tts_type'] = type
        config.params['line_roles'] = {}
        if type=='gtts':
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
        elif type in ['edgeTTS', 'AzureTTS']:
            if type == "AzureTTS" and (not config.params['azure_speech_key'] or not config.params['azure_speech_region']):
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['azureinfo'])
                self.main.subform.set_auzuretts_key()
                return
            self.set_voice_role(self.main.target_language.currentText())
        elif type == 'clone-voice':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.clone_voicelist
            self.main.voice_role.addItems(self.main.current_rolelist)
            threading.Thread(target=tools.get_clone_role).start()
        elif type =='ChatTTS':
            self.main.voice_role.clear()
            self.main.current_rolelist = list(config.ChatTTS_voicelist)
            self.main.voice_role.addItems(['No']+self.main.current_rolelist)
        elif type == 'TTS-API':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['ttsapi_voice_role'].strip().split(',')
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type == 'GPT-SoVITS':
            rolelist = tools.get_gptsovits_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['GPT-SoVITS']
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
            Path(voice_dir).mkdir(parents=True,exist_ok=True)
        lujing_role = role.replace('/', '-')
        volume=int(self.main.volume_rate.value())
        pitch=int(self.main.pitch_rate.value())
        voice_file = f"{voice_dir}/{config.params['tts_type']}-{lang}-{lujing_role}-{volume}-{pitch}.mp3"
        if config.params['tts_type'] in ['GPT-SoVITS','ChatTTS']:
            voice_file += '.wav'

        obj = {
            "text": text,
            "rate": "+0%",
            "role": role,
            "voice_file": voice_file,
            "tts_type": config.params['tts_type'],
            "language": lang,
            "volume":f'+{volume}%' if volume>0 else f'{volume}%',
            "pitch":f'+{pitch}Hz' if pitch>0 else f'{pitch}Hz',
        }
        if config.params['tts_type'] == 'clone-voice' and role == 'clone':
            return
        # 测试能否连接clone
        if config.params['tts_type'] == 'clone-voice':
            try:
                tools.get_clone_role(set_p=True)
            except:
                QMessageBox.critical(self.main, config.transobj['anerror'],
                                     config.transobj['You must deploy and start the clone-voice service'])
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
        if self.main.app_mode in ['biaozhun','peiyin']:
            self.main.listen_btn.show()
            self.main.listen_btn.setDisabled(False)

    # 目标语言改变时设置配音角色
    def set_voice_role(self, t):
        role = self.main.voice_role.currentText()
        # 如果tts类型是 openaiTTS，则角色不变
        # 是edgeTTS时需要改变
        code = translator.get_code(show_text=t)
        if code and code != '-' and config.params['tts_type'] == 'GPT-SoVITS' and code[:2] not in ['zh', 'ja', 'en']:
            # 除此指望不支持
            config.params['tts_type'] = 'edgeTTS'
            self.main.tts_type.setCurrentText('edgeTTS')
            return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['nogptsovitslanguage'])
        if code and code != '-' and config.params['tts_type'] == 'ChatTTS' and code[:2] not in ['zh','en']:
            # 除此指望不支持
            config.params['tts_type'] = 'edgeTTS'
            self.main.tts_type.setCurrentText('edgeTTS')
            return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['onlycnanden'])

        # 除 edgeTTS外，其他的角色不会随语言变化
        if config.params['tts_type'] not in ['edgeTTS', 'AzureTTS']:
            if role != 'No' and self.main.app_mode in ['biaozhun','peiyin']:
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
        show_rolelist = tools.get_edge_rolelist() if config.params['tts_type'] == 'edgeTTS' else tools.get_azure_rolelist()

        if not show_rolelist:
            show_rolelist = tools.get_edge_rolelist()
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
        fnames, _ = QFileDialog.getOpenFileNames(self.main, config.transobj['selectmp4'], config.last_opendir,
                                                 "Video files(*.mp4 *.avi *.mov *.mpg *.mkv)")
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/')

        if len(fnames) > 0:
            self.main.source_mp4.setText(f'{len((fnames))} videos')
            config.last_opendir = os.path.dirname(fnames[0])
            self.main.settings.setValue("last_dir", config.last_opendir)
            config.queue_mp4 = fnames

    # 导入背景声音
    def get_background(self):
        fname, _ = QFileDialog.getOpenFileName(self.main, 'Background music', config.last_opendir,
                                               "Audio files(*.mp3 *.wav *.flac)")
        if not fname:
            return
        fname = fname.replace('\\', '/')
        self.main.back_audio.setText(fname)

    # 从本地导入字幕文件
    def import_sub_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self.main, config.transobj['selectmp4'], config.last_opendir,
                                               "Srt files(*.srt *.txt)")
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
        dirname = QFileDialog.getExistingDirectory(self.main, config.transobj['selectsavedir'], config.last_opendir)
        dirname = dirname.replace('\\', '/')
        self.main.target_dir.setText(dirname)

    # 添加进度条
    def add_process_btn(self):
        clickable_progress_bar = ClickableProgressBar(self)
        clickable_progress_bar.progress_bar.setValue(0)  # 设置当前进度值
        clickable_progress_bar.setText(config.transobj["waitforstart"])
        clickable_progress_bar.setMinimumSize(500, 50)
        # # 将按钮添加到布局中
        self.main.processlayout.addWidget(clickable_progress_bar)
        return clickable_progress_bar

    # 检测各个模式下参数是否设置正确
    def check_mode(self, *, txt=None):
        # 如果是 从字幕配音模式, 只需要字幕和目标语言，不需要翻译和视频
        if self.main.app_mode == 'peiyin':
            if not txt or config.params['voice_role'] == 'No' or config.params['target_language'] == '-':
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['peiyinmoshisrt'])
                return False
            # 去掉选择视频，去掉原始语言
            config.params['source_mp4'] = ''
            config.params['source_language'] = '-'
            config.params['subtitle_type'] = 0
            config.params['whisper_model'] = 'tiny'
            config.params['whisper_type'] = 'all'
            config.params['is_separate'] = False
            config.params['video_autorate'] = False
            config.params['append_video'] = False
            return True
        # 如果是 合并模式,必须有字幕，有视频，有字幕嵌入类型，允许设置视频减速
        # 不需要翻译
        if self.main.app_mode == 'hebing':
            if len(config.queue_mp4) < 1 or config.params['subtitle_type'] < 1 or not txt:
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['hebingmoshisrt'])
                return False
            config.params['is_separate'] = False
            config.params['target_language'] = '-'
            config.params['source_language'] = '-'
            config.params['voice_role'] = 'No'
            config.params['voice_rate'] = '+0%'
            config.params['voice_autorate'] = False
            config.params['video_autorate'] = False
            config.params['append_video'] = False
            config.params['whisper_model'] = 'tiny'
            config.params['whisper_type'] = 'all'
            config.params['back_audio'] = ''
            return True
        if self.main.app_mode == 'tiqu':
            # 提取字幕模式，必须有视频、有原始语言，语音模型
            if len(config.queue_mp4) < 1:
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['selectvideodir'])
                return False

            config.params['is_separate'] = False
            config.params['subtitle_type'] = 0
            config.params['voice_role'] = 'No'
            config.params['voice_rate'] = '+0%'
            config.params['voice_autorate'] = False
            config.params['video_autorate'] = False
            config.params['append_video'] = False
            config.params['back_audio'] = ''
        if self.main.app_mode == 'biaozhun_jd':
            config.params['voice_autorate'] = True
            config.params['video_autorate'] = True
            config.params['append_video'] = True
            # config.params['auto_ajust'] = True
            config.params['is_separate'] = False
            config.params['back_audio'] = ''

        return True

    #
    # 判断是否需要翻译
    # 0 peiyin模式无需翻译，heibng模式无需翻译
    # 1. 不存在视频，则是字幕创建配音模式，无需翻译
    # 2. 不存在目标语言，无需翻译
    # 3. 原语言和目标语言相同，不需要翻译
    # 4. 存在字幕，不需要翻译
    # 是否无需翻译，返回True=无需翻译,False=需要翻译
    def dont_translate(self):
        if self.main.app_mode in ['peiyin', 'hebing']:
            return True
        if len(config.queue_mp4) < 1:
            return True
        if self.main.target_language.currentText() == '-' or self.main.source_language.currentText() == '-':
            return True
        if self.main.target_language.currentText() == self.main.source_language.currentText():
            return True
        if self.main.subtitle_area.toPlainText().strip():
            return True
        return False

    def change_proxy(self, p):
        # 设置或删除代理
        config.proxy = p.strip()
        try:
            if not config.proxy:
                # 删除代理
                tools.set_proxy('del')
            self.main.settings.setValue('proxy', config.proxy)
        except Exception:
            pass

    # 检测开始状态并启动
    def check_start(self):
        if config.current_status == 'ing':
            # 停止
            question = tools.show_popup(config.transobj['exit'], config.transobj['confirmstop'])
            if question == QMessageBox.Yes:
                self.update_status('stop')
                return
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
                    return

        config.task_countdown = config.settings['countdown_sec']
        config.settings = config.parse_init()
        # 清理日志

        # 目标文件夹
        target_dir = self.main.target_dir.text().strip().replace('\\', '/')
        if target_dir:
            config.params['target_dir'] = target_dir
        else:
            config.params['target_dir'] = ''

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

        # 原始语言
        config.params['source_language'] = self.main.source_language.currentText()
        langcode=translator.get_code(show_text=config.params['source_language'])
        if self.main.model_type.currentIndex==3 and langcode not in ['zh-cn','zh-tw']:
            self.update_status('stop')
            return QMessageBox.critical(self.main,config.transobj['anerror'],'zh_recogn 仅支持中文语音识别' if config.defaulelang=='zh' else 'zh_recogn Supports Chinese speech recognition only')
            
        if self.main.model_type.currentIndex==3 and not config.params['zh_recogn_api']:
            return QMessageBox.critical(self.main,config.transobj['anerror'],'zh_recogn 必须在设置-zh_recogn中填写http接口地址' if config.defaulelang=='zh' else 'The http interface address must be filled in the settings-zh_recogn')
        
        if self.main.model_type.currentIndex==4:
            if not config.params['doubao_appid']:
                return QMessageBox.critical(self.main,config.transobj['anerror'],'必须填写豆包应用APP ID')
            if langcode and langcode[:2] not in ["zh","en","ja","ko","es","fr","ru"]:
                return QMessageBox.critical(self.main,config.transobj['anerror'],'豆包语音识别仅支持中英日韩法俄西班牙语言，其他不支持')
            

        # 目标语言
        target_language = self.main.target_language.currentText()
        config.params['target_language'] = target_language

        # 配音角色
        config.params['voice_role'] = self.main.voice_role.currentText()

        # 配音自动加速
        config.params['voice_autorate'] = self.main.voice_autorate.isChecked()
        config.params['video_autorate'] = self.main.video_autorate.isChecked()
        config.params['append_video'] = self.main.append_video.isChecked()

        # 视频自动减速
        # 语音模型
        config.params['whisper_model'] = self.main.whisper_model.currentText()
        model_index=self.main.model_type.currentIndex()
        if model_index==1:
            config.params['model_type']='openai'
        elif model_index==2:
            config.params['model_type']='GoogleSpeech'
        elif model_index==3:
            config.params['model_type']='zh_recogn'
        elif model_index==4:
            config.params['model_type']='doubao'
        else:
            config.params['model_type']='faster'
            
        print(f"{config.params['model_type']}")

        # 字幕嵌入类型
        config.params['subtitle_type'] = int(self.main.subtitle_type.currentIndex())

        try:
            voice_rate = int(self.main.voice_rate.value())
            config.params['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"{voice_rate}%"
        except Exception:
            config.params['voice_rate'] = '+0%'

        try:
            volume=int(self.main.volume_rate.value())
            pitch=int(self.main.pitch_rate.value())
            config.params['volume']=f'+{volume}%' if volume>0 else f'{volume}%'
            config.params['pitch']=f'+{pitch}Hz' if pitch>0 else f'{pitch}Hz'
        except Exception:
            config.params['volume']='+0%'
            config.params['pitch']='+0Hz'
        config.params['back_audio'] = self.main.back_audio.text().strip()
        # 字幕区文字
        txt = self.main.subtitle_area.toPlainText().strip()
        if txt and not re.search(r'\d{1,2}:\d{1,2}:\d{1,2}(,\d+)?\s*?-->\s*?\d{1,2}:\d{1,2}:\d{1,2}(,\d+)?', txt):
            txt = ""
            self.main.subtitle_area.clear()

        # 综合判断
        if len(config.queue_mp4) < 1 and not txt:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['bukedoubucunzai'])
            return False

        # tts类型
        if config.params['tts_type'] == 'openaiTTS' and not config.params["chatgpt_key"]:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['chatgptkeymust'])
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

        # 未主动选择模式，则判断设置情况应该属于什么模式
        if self.main.app_mode.startswith('biaozhun'):
            # tiqu 如果 存在视频但 无配音 无嵌入字幕，则视为提取
            if len(config.queue_mp4) > 0 and config.params['subtitle_type'] < 1 and config.params['voice_role'] == 'No':
                self.main.app_mode = 'tiqu'
                config.params['is_separate'] = False
            elif len(config.queue_mp4) > 0 and txt and config.params['subtitle_type'] > 0 and config.params[
                'voice_role'] == 'No':
                # hebing 存在视频，存在字幕，字幕嵌入，不配音
                self.main.app_mode = 'hebing'
                config.params['is_separate'] = False
            elif len(config.queue_mp4) < 1 and txt:
                # peiyin
                self.main.app_mode = 'peiyin'
                config.params['is_separate'] = False

        if not self.check_mode(txt=txt):
            return False
        # 除了 peiyin  hebing模式，其他均需要检测模型是否存在
        if self.main.app_mode not in ['hebing', 'peiyin'] and not self.check_whisper_model(
                config.params['whisper_model']):
            return False

        if config.params["cuda"]:
            import torch
            if not torch.cuda.is_available():
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocuda"])
                return
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
                        return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocudnn"])

        config.params['translate_type'] = self.main.translate_type.currentText()
        # 如果需要翻译，再判断是否符合翻译规则
        if not self.dont_translate():
            rs = translator.is_allow_translate(translate_type=config.params['translate_type'],
                                    show_target=config.params['target_language'])
            if rs is not True:
                # 不是True，有错误
                QMessageBox.critical(self.main, config.transobj['anerror'], rs)
                return False

        if self.main.app_mode !='hebing' and config.params['target_language']!='-':
            code=translator.get_code(show_text=config.params['target_language'])
            if code not in ['zh-cn','zh-tw','en'] and config.params['tts_type']=='ChatTTS' and config.params['voice_role']!='No':
                return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['onlycnanden'])


        # 存在视频
        config.params['only_video'] = False
        if config.params['voice_role'] == 'No':
            config.params['is_separate'] = False
        config.params['clear_cache']=False
        if self.main.clear_cache.isChecked():
            config.params['clear_cache']=True
        if len(config.queue_mp4) > 0:
            self.main.show_tips.setText("")
            if self.main.app_mode not in ['tiqu', 'peiyin',
                                          'biaozhun_jd'] and self.main.only_video.isChecked():
                config.params['only_video'] = True
            start_thread(self.main)
        elif txt:
            self.main.source_mp4.setText(config.transobj["No select videos"])
            self.main.app_mode = 'peiyin'
            config.params['is_separate'] = False
            if config.params['tts_type'] == 'clone-voice' and config.params['voice_role'] == 'clone':
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj[
                    'Clone voice cannot be used in subtitle dubbing mode as there are no replicable voices'])
                return


        self.main.save_setting()
        self.update_status('ing')
        self.delete_process()
        # return
        config.settings=config.parse_init()
        from videotrans.task.main_worker import Worker

        self.main.task = Worker(parent=self.main, app_mode=self.main.app_mode, txt=txt)
        self.main.task.start()


        for k,v in self.main.moshis.items():
            if k != self.main.app_mode:
                v.setDisabled(True)


    # 设置按钮上的日志信息
    def set_process_btn_text(self, text, btnkey="", type="logs"):
        if not btnkey or btnkey not in self.main.processbtns:
            return
        if not self.main.task:
            return
        if btnkey=='srt2wav':
            if not self.main.task or not self.main.task.video:
                return
            if type=='succeed':
                text, basename = text.split('##')
                self.main.processbtns[btnkey].setTarget(text)
                self.main.processbtns[btnkey].setCursor(Qt.PointingHandCursor)
                precent=100
                text=f'{config.transobj["endandopen"].replace("..", "")} {text}'
            else:
                precent=self.main.task.video.precent
                text=f'{config.transobj["running"].replace("..", "")} [{round(precent, 1)}%] /  {config.transobj["endopendir"]} {text}'
            self.main.processbtns[btnkey].progress_bar.setValue(precent)
            self.main.processbtns[btnkey].setText(text)
            return
        precent=round( self.main.task.tasklist[btnkey].precent if self.main.task.tasklist and btnkey in self.main.task.tasklist else 0, 1)
        if type == 'succeed' or precent>=100.0:        
            
            target=self.main.task.tasklist[btnkey].obj['output']            
            basename=self.main.task.tasklist[btnkey].obj['raw_basename']
            
            self.main.processbtns[btnkey].setTarget(target)
            self.main.processbtns[btnkey].setCursor(Qt.PointingHandCursor)
            
            text = f'{config.transobj["endandopen"]} {basename}'
            self.main.processbtns[btnkey].setText(text)
            self.main.processbtns[btnkey].progress_bar.setValue(100)
            self.main.processbtns[btnkey].setToolTip(config.transobj['mubiao'])
        elif type == 'error' or type == 'stop':
            self.main.processbtns[btnkey].progress_bar.setStyleSheet('color:#ff0000')
            if type=='error':
                self.main.processbtns[btnkey].setCursor(Qt.PointingHandCursor)
                self.main.processbtns[btnkey].setMsg(
                    text+f'\n\n{config.errorlist[btnkey] if btnkey in config.errorlist and config.errorlist[btnkey]!=text else "" }'
                )
                self.main.processbtns[btnkey].setToolTip('点击查看详细报错' if config.defaulelang=='zh' else 'Click to view the detailed error report')
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
            else:
                # 停止
                self.main.continue_compos.hide()
                self.main.target_dir.clear()
                self.main.source_mp4.setText(config.transobj["No select videos"] if len(
                    config.queue_mp4) < 1 else f'{len(config.queue_mp4)} videos')
                # 清理输入
            if self.main.task:
                self.main.task.requestInterruption()
                self.main.task.quit()
                self.main.task = None
            if self.main.app_mode == 'tiqu':
                self.set_tiquzimu()
            elif self.main.app_mode == 'hebing':
                self.set_zimu_video()
            elif self.main.app_mode == 'peiyin':
                self.set_zimu_peiyin()
        else:
            # 重设为开始状态
            self.disabled_widget(True)
            self.main.startbtn.setText(config.transobj["starting..."])
            

    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        if d['type']=='alert':
            QMessageBox.critical(self.main, config.transobj['anerror'], d['text'])
            return
            
        # 一行一行插入字幕到字幕编辑区
        elif d['type'] == 'set_start_btn':
            self.main.startbtn.setText(config.transobj["running"])
        elif d['type'] == "subtitle":
            self.main.subtitle_area.moveCursor(QTextCursor.End)
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'add_process':
            self.main.processbtns[d['btnkey']] = self.add_process_btn()
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
                #self.set_process_btn_text(config.transobj['stop'], d['btnkey'], d['type'])
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
        elif d['type'] == 'edit_subtitle':
            # 显示出合成按钮,等待编辑字幕,允许修改字幕
            self.main.subtitle_area.setReadOnly(False)
            self.main.subtitle_area.setFocus()
            self.main.continue_compos.show()
            self.main.continue_compos.setDisabled(False)
            self.main.continue_compos.setText(d['text'])
            self.main.stop_djs.show()
        elif d['type'] == 'disabled_edit':
            # 禁止修改字幕
            self.main.subtitle_area.setReadOnly(True)
            self.main.export_sub.setDisabled(True)
            self.main.set_line_role.setDisabled(True)
        elif d['type'] == 'allow_edit':
            # 允许修改字幕
            self.main.subtitle_area.setReadOnly(False)
            self.main.export_sub.setDisabled(False)
            self.main.set_line_role.setDisabled(False)
        elif d['type'] == 'replace_subtitle':
            # 完全替换字幕区
            self.main.subtitle_area.clear()
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'timeout_djs':
            self.main.stop_djs.hide()
            self.update_subtitle(step=d['text'], btnkey=d['btnkey'])
            self.main.continue_compos.setDisabled(True)
            self.main.subtitle_area.setReadOnly(True)
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

        elif d['type'] == 'update_download' and self.main.youw is not None:
            self.main.youw.logs.setText(config.transobj['youtubehasdown'])
        elif d['type'] == 'youtube_error':
            self.main.youw.set.setText(config.transobj['start download'])
            QMessageBox.critical(self.main.youw, config.transobj['anerror'], d['text'][:900])

        elif d['type'] == 'youtube_ok':
            self.main.youw.set.setText(config.transobj['start download'])
            QMessageBox.information(self.main.youw, "OK", d['text'])
        elif d['type'] == 'open_toolbox':
            self.open_toolbox(0, True)
        elif d['type'] == 'set_clone_role' and config.params['tts_type'] == 'clone-voice':
            self.main.settings.setValue("clone_voicelist", ','.join(config.clone_voicelist))
            if config.current_status == 'ing':
                return
            current = self.main.voice_role.currentText()
            self.main.voice_role.clear()
            self.main.voice_role.addItems(config.clone_voicelist)
            self.main.voice_role.setCurrentText(current)
        elif d['type'] == 'win':
            # 小窗口背景音分离
            if self.main.sepw is not None:
                self.main.sepw.set.setText(d['text'])

    # update subtitle 手动 点解了 立即合成按钮，或者倒计时结束超时自动执行
    def update_subtitle(self, step="translate_start", btnkey=""):
        self.main.stop_djs.hide()
        self.main.continue_compos.setDisabled(True)
        # 如果当前是等待翻译阶段，则更新原语言字幕,然后清空字幕区
        txt = self.main.subtitle_area.toPlainText().strip()
        config.task_countdown = 0
        if not btnkey or not txt:
            return
        if btnkey == 'srt2wav':
            srtfile = self.main.task.video.init['target_sub']
            with open(srtfile, 'w', encoding='utf-8') as f:
                f.write(txt)
            return

        if not self.main.task.is_batch and btnkey in self.main.task.tasklist:
            if step == 'translate_start':
                srtfile = self.main.task.tasklist[btnkey].init['source_sub']
            else:
                srtfile = self.main.task.tasklist[btnkey].init['target_sub']
            # 不是批量才允许更新字幕
            with open(srtfile, 'w', encoding='utf-8') as f:
                f.write(txt)
        if step == 'translate_start':
            self.main.subtitle_area.clear()
        return True
