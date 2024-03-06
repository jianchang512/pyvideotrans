import json
import os
import re
import threading

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import QTextCursor, QDesktopServices
from PySide6.QtCore import QUrl, Qt, QDir, QThread, Signal
from PySide6.QtWidgets import QMessageBox, QFileDialog, QLabel, QPushButton, QTextBrowser, QWidget, QVBoxLayout, \
    QHBoxLayout, QLineEdit, QScrollArea, QCheckBox, QProgressBar
import warnings

from videotrans import configure

from videotrans.task.separate_worker import SeparateWorker
from videotrans.util import tools

warnings.filterwarnings('ignore')
from videotrans.translator import is_allow_translate, get_code
from videotrans.util.tools import show_popup, set_proxy, get_edge_rolelist, get_elevenlabs_role, get_subtitle_from_srt, \
    get_clone_role
from videotrans.configure import config



class ClickableProgressBar(QLabel):
    def __init__(self):
        super().__init__()
        self.target_dir = None


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
                background-color: #009688;
                width: 8px;
                border-radius:0;           
            }
        """)
        layout = QHBoxLayout(self)
        layout.addWidget(self.progress_bar)  # 将进度条添加到布局

    def setTarget(self, url):
        self.target_dir = url

    def setText(self, text):
        if self.progress_bar:
            self.progress_bar.setFormat(f' {text}')  # set text format

    def mousePressEvent(self, event):
        print(f"Progress bar clicked! {self.target_dir},{event.button()}")
        if self.target_dir and event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.target_dir))


class MyTextBrowser(QTextBrowser):
    def __init__(self):
        super(MyTextBrowser, self).__init__()

    def anchorClicked(self, url):
        # 拦截超链接点击事件
        if url.scheme() == "file":
            # 如果是本地文件链接
            file_path = url.toLocalFile()
            # 使用 QDir.toNativeSeparators 处理路径分隔符
            file_path = QDir.toNativeSeparators(file_path)
            # 打开系统目录
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


# primary ui
class SecWindow():
    def __init__(self, main=None):
        self.main = main
        self.usetype=None
        # QTimer.singleShot(100, self.open_toolbox)

    def openExternalLink(self, url):
        try:
            QDesktopServices.openUrl(url)
        except:
            pass
        return

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
        text = int(str(text).replace('+', '').replace('%', ''))
        text = f'+{text}%' if text >= 0 else f'-{text}%'
        config.params['voice_rate'] = text

    # 字幕下方试听配音
    def shiting_peiyin(self):
        if not self.main.task:
            return
        if self.main.voice_role.currentText() == 'No':
            return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['noselectrole'])
        if self.main.shitingobj:
            self.main.shitingobj.stop = True
            self.main.shitingobj = None
            self.main.listen_peiyin.setText(config.transobj['chongtingzhong'])
        else:
            self.main.listen_peiyin.setText(config.transobj['shitingzhong'])
        obj = {
            "sub_name": self.main.task.video.targetdir_target_sub,
            "noextname": self.main.task.video.noextname,
            "cache_folder": self.main.task.video.cache_folder,
            "source_wav": self.main.task.video.targetdir_source_sub
        }
        txt = self.main.subtitle_area.toPlainText().strip()
        if not txt:
            return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['bukeshiting'])
        with open(self.main.task.video.targetdir_target_sub, 'w', encoding='utf-8') as f:
            f.write(txt)
        from videotrans.task.main_worker import Shiting
        self.main.shitingobj = Shiting(obj, self.main)
        self.main.shitingobj.start()

    # 启用标准模式
    def set_biaozhun(self):
        self.main.app_mode = 'biaozhun'
        self.main.show_tips.setText("")
        self.main.startbtn.setText(config.transobj['kaishichuli'])
        self.main.action_tiquzimu_no.setChecked(False)
        self.main.action_biaozhun.setChecked(True)
        self.main.action_tiquzimu.setChecked(False)
        self.main.action_zimu_video.setChecked(False)
        self.main.action_zimu_peiyin.setChecked(False)

        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)
        self.main.open_targetdir.show()

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
        self.hide_show_element(self.main.listen_layout, False)
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, True)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, True)

        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, True)
        # 静音片段
        # self.hide_show_element(self.main.layout_voice_silence, True)
        # 配音自动加速
        self.main.voice_autorate.show()
        # 视频自动降速
        self.main.video_autorate.show()
        self.main.is_separate.setDisabled(False)
        self.main.addbackbtn.setDisabled(False)
        self.main.back_audio.setReadOnly(False)
        self.main.only_video.setDisabled(False)

        # cuda
        self.main.enable_cuda.show()

    # 视频提取字幕并翻译，无需配音
    def set_tiquzimu(self):
        self.main.app_mode = 'tiqu'
        self.main.show_tips.setText(config.transobj['tiquzimu'])
        self.main.startbtn.setText(config.transobj['kaishitiquhefanyi'])
        self.main.action_tiquzimu_no.setChecked(False)
        self.main.action_tiquzimu.setChecked(True)
        self.main.action_biaozhun.setChecked(False)
        self.main.action_zimu_video.setChecked(False)
        self.main.action_zimu_peiyin.setChecked(False)

        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)
        self.main.open_targetdir.show()

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
        # self.main.voice_role.setCurrentText('No')
        # 试听按钮
        self.hide_show_element(self.main.listen_layout, False)
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, True)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, False)
        # self.main.subtitle_type.setCurrentIndex(0)

        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, False)
        # self.main.voice_rate.setText('+0%')
        # 静音片段
        # self.hide_show_element(self.main.layout_voice_silence, False)
        # self.main.voice_silence.setText('500')
        # 配音自动加速
        self.main.voice_autorate.hide()
        self.main.voice_autorate.setChecked(False)
        # 视频自动降速
        self.main.video_autorate.hide()
        self.main.video_autorate.setChecked(False)
        self.main.is_separate.setDisabled(True)
        self.main.is_separate.setChecked(False)
        config.params['is_separate'] = False
        
        self.main.addbackbtn.setDisabled(True)
        self.main.back_audio.setReadOnly(True)
        self.main.only_video.setDisabled(True)
        self.main.only_video.setChecked(False)
        # cuda
        self.main.enable_cuda.show()

    # 从视频提取字幕，不翻译
    # 只显示 选择视频、保存目标、原始语言、语音模型，其他不需要
    def set_tiquzimu_no(self):
        self.main.app_mode = 'tiqu_no'
        self.main.show_tips.setText(config.transobj['tiquzimuno'])
        self.main.startbtn.setText(config.transobj['kaishitiquzimu'])
        self.main.action_tiquzimu.setChecked(False)
        self.main.action_tiquzimu_no.setChecked(True)
        self.main.action_biaozhun.setChecked(False)
        self.main.action_zimu_video.setChecked(False)
        self.main.action_zimu_peiyin.setChecked(False)

        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)
        self.main.open_targetdir.show()

        # 翻译渠道
        self.hide_show_element(self.main.layout_translate_type, False)
        # 代理
        self.hide_show_element(self.main.layout_proxy, False)
        # self.main.proxy.setText('')
        # 原始语言
        self.hide_show_element(self.main.layout_source_language, True)

        # 目标语言
        self.hide_show_element(self.main.layout_target_language, False)

        # tts类型
        self.hide_show_element(self.main.layout_tts_type, False)

        # 配音角色
        self.hide_show_element(self.main.layout_voice_role, False)
        # self.main.voice_role.setCurrentText('No')
        # 试听按钮
        self.hide_show_element(self.main.listen_layout, False)
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, True)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, False)
        # self.main.subtitle_type.setCurrentIndex(0)

        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, False)
        # self.main.voice_rate.setText('+0%')
        # 静音片段
        # self.hide_show_element(self.main.layout_voice_silence, False)
        # self.main.voice_silence.setText('500')
        # 配音自动加速
        self.main.voice_autorate.hide()
        self.main.voice_autorate.setChecked(False)
        # 视频自动降速
        self.main.video_autorate.hide()
        self.main.video_autorate.setChecked(False)
        self.main.is_separate.setDisabled(True)
        self.main.is_separate.setChecked(False)
        config.params['is_separate'] = False
        
        self.main.addbackbtn.setDisabled(True)
        self.main.back_audio.setReadOnly(True)
        self.main.only_video.setDisabled(True)
        self.main.only_video.setChecked(False)
        # cuda
        self.main.enable_cuda.show()

    # 启用字幕合并模式, 仅显示 选择视频、保存目录、字幕类型、自动视频降速 cuda
    # 不配音、不识别，
    def set_zimu_video(self):
        self.main.app_mode = 'hebing'
        self.main.show_tips.setText(config.transobj['zimu_video'])
        self.main.startbtn.setText(config.transobj['kaishihebing'])
        self.main.action_tiquzimu_no.setChecked(False)
        self.main.action_biaozhun.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)
        self.main.action_zimu_video.setChecked(True)
        self.main.action_zimu_peiyin.setChecked(False)

        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)
        self.main.open_targetdir.show()

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
        self.hide_show_element(self.main.listen_layout, False)
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, False)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, True)

        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, False)
        # 静音片段
        # self.hide_show_element(self.main.layout_voice_silence, False)

        # 配音自动加速
        self.main.voice_autorate.hide()
        self.main.voice_autorate.setChecked(False)
        # 视频自动降速
        self.main.video_autorate.show()
        self.main.video_autorate.setChecked(False)
        self.main.is_separate.setDisabled(True)
        self.main.is_separate.setChecked(False)
        config.params['is_separate'] = False
        self.main.addbackbtn.setDisabled(True)
        self.main.back_audio.setReadOnly(True)
        self.main.only_video.setDisabled(False)
        # cuda
        self.main.enable_cuda.show()

    # 仅仅对已有字幕配音，显示目标语言、tts相关，自动加速相关，
    # 不翻译不识别
    def set_zimu_peiyin(self):
        self.main.show_tips.setText(config.transobj['zimu_peiyin'])
        self.main.startbtn.setText(config.transobj['kaishipeiyin'])
        self.main.action_tiquzimu_no.setChecked(False)
        self.main.action_biaozhun.setChecked(False)
        self.main.action_tiquzimu.setChecked(False)
        self.main.action_zimu_video.setChecked(False)
        self.main.action_zimu_peiyin.setChecked(True)
        self.main.app_mode = 'peiyin'
        # 选择视频
        self.hide_show_element(self.main.layout_source_mp4, False)
        # 保存目标
        self.hide_show_element(self.main.layout_target_dir, True)
        self.main.open_targetdir.show()

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
        self.hide_show_element(self.main.listen_layout, True)
        # 语音模型
        self.hide_show_element(self.main.layout_whisper_model, False)
        # 字幕类型
        self.hide_show_element(self.main.layout_subtitle_type, False)

        # 配音语速
        self.hide_show_element(self.main.layout_voice_rate, True)
        # 静音片段
        # self.hide_show_element(self.main.layout_voice_silence, False)
        # 配音自动加速
        self.main.voice_autorate.show()
        # 视频自动降速
        self.main.video_autorate.hide()
        self.main.video_autorate.setChecked(False)
        self.main.is_separate.setDisabled(True)
        self.main.is_separate.setChecked(False)
        config.params['is_separate'] = False
        self.main.addbackbtn.setDisabled(False)
        self.main.back_audio.setReadOnly(False)
        self.main.only_video.setDisabled(True)
        self.main.only_video.setChecked(False)
        # cuda
        self.main.enable_cuda.show()

    # 关于页面
    def about(self):
        from videotrans.component import InfoForm
        self.main.infofrom = InfoForm()
        self.main.infofrom.show()

    # voice_autorate video_autorate 变化
    def autorate_changed(self, state, name):
        if name == 'voice':
            config.params['voice_autorate'] = state
        else:
            config.params['video_autorate'] = state

    def open_dir(self, dirname=None):
        if not dirname:
            return
        dirname=dirname.strip()
        if not os.path.isdir(dirname):
            dirname = os.path.dirname(dirname)
        if not dirname or not os.path.isdir(dirname):
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(dirname))

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

    # 开启执行后，禁用按钮，停止或结束后，启用按钮
    def disabled_widget(self, type):
        self.main.import_sub.setDisabled(type)
        # self.main.export_sub.setDisabled(type)
        self.main.btn_get_video.setDisabled(type)
        # self.main.source_mp4.setDisabled(type)
        self.main.btn_save_dir.setDisabled(type)
        # self.main.target_dir.setDisabled(type)
        self.main.translate_type.setDisabled(type)
        self.main.proxy.setDisabled(type)
        self.main.source_language.setDisabled(type)
        self.main.target_language.setDisabled(type)
        self.main.tts_type.setDisabled(type)
        self.main.whisper_model.setDisabled(type)
        self.main.whisper_type.setDisabled(type)
        self.main.subtitle_type.setDisabled(type)
        # self.main.voice_silence.setDisabled(type)
        self.main.video_autorate.setDisabled(type)
        self.main.enable_cuda.setDisabled(type)
        self.main.is_separate.setDisabled(type)
        self.main.model_type.setDisabled(type)
        self.main.only_video.setDisabled(True if self.main.app_mode in ['tiqu','tiqu_no','peiyin'] else type)
        self.main.addbackbtn.setDisabled(True if self.main.app_mode in ['tiqu','tiqu_no','hebing'] else type)
        self.main.back_audio.setReadOnly(True if self.main.app_mode in ['tiqu','tiqu_no','hebing'] else type)

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
        with open(path_to_file, "w",encoding='utf-8') as file:
            file.write(srttxt)


    def open_url(self, title):
        import webbrowser
        if title == 'vlc':
            webbrowser.open_new_tab("https://www.videolan.org/vlc/")
        elif title == 'ffmpeg':
            webbrowser.open_new_tab("https://www.ffmpeg.org/download.html")
        elif title == 'git':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans")
        elif title == 'issue':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/issues")
        elif title == 'discord':
            webbrowser.open_new_tab("https://discord.com/channels/1174626422044766258/1174626425702207562")
        elif title == 'models':
            webbrowser.open_new_tab("https://github.com/jianchang512/stt/releases/tag/0.0")
        elif title == 'dll':
            webbrowser.open_new_tab("https://github.com/jianchang512/stt/releases/tag/v0.0.1")
        elif title == 'gtrans':
            webbrowser.open_new_tab("https://juejin.cn/post/7339210740454719523")
        elif title == 'cuda':
            webbrowser.open_new_tab("https://juejin.cn/post/7318704408727519270")
        elif title == 'website':
            webbrowser.open_new_tab("https://pyvideotrans.com")
        elif title == 'xinshou':
            webbrowser.open_new_tab("https://pyvideotrans.com/guide.html" if config.defaulelang!='zh' else 'https://juejin.cn/post/7331558973657251840')
        elif title == "about":
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/blob/main/about.md")
        elif title == 'download':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/releases")

    # 工具箱
    def open_toolbox(self, index=0, is_hide=True):
        try:
            if configure.TOOLBOX is None:
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
            checked_checkbox_names = get_checked_boxes(self.main.w)

            if len(checked_checkbox_names) < 1:
                return QMessageBox.critical(self.main.w, config.transobj['anerror'],
                                            config.transobj['zhishaoxuanzeyihang'])

            for n in checked_checkbox_names:
                _, line = n.split('_')
                # 设置labe为角色名
                ck = self.main.w.findChild(QCheckBox, n)
                ck.setText(config.transobj['default'] if role in ['No', 'no', '-'] else role)
                ck.setChecked(False)
                config.params['line_roles'][line] = config.params['voice_role'] if role in ['No', 'no', '-'] else role

        from videotrans.component import SetLineRole
        self.main.w = SetLineRole()
        box = QWidget()  # 创建新的 QWidget，它将承载你的 QHBoxLayouts
        box.setLayout(QVBoxLayout())  # 设置 QVBoxLayout 为新的 QWidget 的layout
        if config.params['voice_role'] in ['No', '-', 'no']:
            return QMessageBox.critical(self.main.w, config.transobj['anerror'], config.transobj['xianxuanjuese'])
        if not self.main.subtitle_area.toPlainText().strip():
            return QMessageBox.critical(self.main.w, config.transobj['anerror'], config.transobj['youzimuyouset'])

        #  获取字幕
        srt_json = get_subtitle_from_srt(self.main.subtitle_area.toPlainText().strip(), is_file=False)
        for it in srt_json:
            # 创建新水平布局
            h_layout = QHBoxLayout()
            check = QCheckBox()
            check.setText(
                config.params['line_roles'][f'{it["line"]}'] if f'{it["line"]}' in config.params['line_roles'] else
                config.transobj['default'])
            check.setObjectName(f'check_{it["line"]}')
            # 创建并配置 QLineEdit
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(config.transobj['shezhijueseline'])

            line_edit.setText(f'[{it["line"]}] {it["text"]}')
            line_edit.setReadOnly(True)
            # 将标签和编辑线添加到水平布局
            h_layout.addWidget(check)
            h_layout.addWidget(line_edit)
            box.layout().addLayout(h_layout)
        box.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main.w.select_role.addItems(self.main.current_rolelist)
        self.main.w.set_role_label.setText(config.transobj['shezhijuese'])

        self.main.w.select_role.currentTextChanged.connect(save)
        # 创建 QScrollArea 并将 box QWidget 设置为小部件
        scroll_area = QScrollArea()
        scroll_area.setWidget(box)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignTop)

        # self.main.w.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # 将 QScrollArea 添加到主窗口的 layout
        self.main.w.layout.addWidget(scroll_area)

        self.main.w.set_ok.clicked.connect(lambda: self.main.w.close())
        self.main.w.show()

    def open_separate(self):
        def get_file():
            fname, _ = QFileDialog.getOpenFileName(self.main.sepw, "Select audio or video", config.last_opendir,
                                                   "files(*.wav *.mp3 *.aac *.m4a *.flac *.mp4 *.mov *.mkv)")
            if fname:
                self.main.sepw.fromfile.setText(fname.replace('file:///', '').replace('\\', '/'))

        def update(d):
            #更新
            if d=='succeed':
                self.main.sepw.set.setText(config.transobj['Separate End/Restart'])
                self.main.sepw.fromfile.setText('')
            elif d=='end':
                self.main.sepw.set.setText(config.transobj['Start Separate'])
            else:
                QMessageBox.critical(self.main.sepw,config.transobj['anerror'],d)


        def start():
            if config.separate_status=='ing':
                config.separate_status='stop'
                self.main.sepw.set.setText(config.transobj['Start Separate'])
                return
            #开始处理分离，判断是否选择了源文件
            file=self.main.sepw.fromfile.text()
            if not file or not os.path.exists(file):
                QMessageBox.critical(self.main.sepw, config.transobj['anerror'], config.transobj['must select audio or video file'])
                return
            self.main.sepw.set.setText(config.transobj['Start Separate...'])
            basename=os.path.basename(file)
            #判断名称是否正常
            rs,newfile,base=tools.rename_move(file,is_dir=False)
            if rs:
                file=newfile
                basename=base
            #创建文件夹
            out=os.path.join(outdir,basename).replace('\\','/')
            os.makedirs(out,exist_ok=True)
            self.main.sepw.url.setText(out)
            #开始分离
            config.separate_status='ing'
            self.main.sepw.task=SeparateWorker(parent=self.main.sepw,out=out,file=file,basename=basename)
            self.main.sepw.task.finish_event.connect(update)
            self.main.sepw.task.start()



        from videotrans.component import SeparateForm
        try:
            if self.main.sepw is not None:
                self.main.sepw.show()
                return
            self.main.sepw = SeparateForm()
            self.main.sepw.set.setText(config.transobj['Start Separate'])
            outdir = os.path.join(config.homedir,'separate').replace( '\\', '/')
            if not os.path.exists(outdir):
                os.makedirs(outdir, exist_ok=True)
            # 创建事件过滤器实例并将其安装到 lineEdit 上
            self.main.sepw.url.setText(outdir)

            self.main.sepw.selectfile.clicked.connect(get_file)

            self.main.sepw.set.clicked.connect(start)
            self.main.sepw.show()
        except:
            print('err')
            pass

    def open_youtube(self):
        def download():
            proxy = self.main.youw.proxy.text().strip()
            outdir = self.main.youw.outputdir.text()
            url = self.main.youw.url.text().strip()
            if not url or not re.match(r'^https://(www.)?(youtube.com/watch\?v=\w|youtu.be/\w)',url,re.I):
                QMessageBox.critical(self.main.youw, config.transobj['anerror'], config.transobj['You must fill in the YouTube video playback page address'])
                return
            self.main.settings.setValue("youtube_outdir", outdir)
            if proxy:
                config.proxy = proxy
                self.main.settings.setValue("proxy", proxy)
            from videotrans.task.download_youtube import Download
            down = Download(proxy=proxy,url=url,out=outdir, parent=self.main)
            down.start()
            self.main.youw.set.setDisabled(True)

        def selectdir():
            dirname = QFileDialog.getExistingDirectory(self.main, "Select Dir", outdir).replace('\\', '/')
            self.main.youw.outputdir.setText(dirname)

        from videotrans.component import YoutubeForm
        self.main.youw = YoutubeForm()
        self.main.youw.set.setText(config.transobj['start download'])
        self.main.youw.selectdir.setText(config.transobj['Select Out Dir'])
        outdir = config.params['youtube_outdir'] if 'youtube_outdir' in config.params else os.path.join(config.homedir,
                                                                                                        'youtube').replace(
            '\\', '/')
        if not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        # 创建事件过滤器实例并将其安装到 lineEdit 上

        self.main.youw.outputdir.setText(outdir)
        if config.proxy:
            self.main.youw.proxy.setText(config.proxy)
        self.main.youw.selectdir.clicked.connect(selectdir)

        self.main.youw.set.clicked.connect(download)
        self.main.youw.show()

    # set deepl key
    def set_deepL_key(self):
        def save():
            key = self.main.w.deepl_authkey.text()
            api = self.main.w.deepl_api.text().strip()
            self.main.settings.setValue("deepl_authkey", key)
            config.params['deepl_authkey'] = key
            if api:
                self.main.settings.setValue("deepl_api", api)
                config.params['deepl_api'] = api
            self.main.w.close()

        from videotrans.component import DeepLForm
        self.main.w = DeepLForm()
        if config.params['deepl_authkey']:
            self.main.w.deepl_authkey.setText(config.params['deepl_authkey'])
        if config.params['deepl_api']:
            self.main.w.deepl_api.setText(config.params['deepl_api'])
        self.main.w.set_deepl.clicked.connect(save)
        self.main.w.show()

    def set_elevenlabs_key(self):
        def save():
            key = self.main.w.elevenlabstts_key.text()
            self.main.settings.setValue("elevenlabstts_key", key)
            config.params['elevenlabstts_key'] = key
            self.main.w.close()

        from videotrans.component import ElevenlabsForm
        self.main.w = ElevenlabsForm()
        if config.params['elevenlabstts_key']:
            self.main.w.elevenlabstts_key.setText(config.params['elevenlabstts_key'])
        self.main.w.set.clicked.connect(save)
        self.main.w.show()

    def set_deepLX_address(self):
        def save():
            key = self.main.w.deeplx_address.text()
            self.main.settings.setValue("deeplx_address", key)
            config.params["deeplx_address"] = key
            self.main.w.close()

        from videotrans.component import DeepLXForm
        self.main.w = DeepLXForm()
        if config.params["deeplx_address"]:
            self.main.w.deeplx_address.setText(config.params["deeplx_address"])
        self.main.w.set_deeplx.clicked.connect(save)
        self.main.w.show()
    
    def set_ott_address(self):
        def save():
            key = self.main.w.ott_address.text()
            self.main.settings.setValue("ott_address", key)
            config.params["ott_address"] = key
            self.main.w.close()

        from videotrans.component import OttForm
        self.main.w = OttForm()
        if config.params["ott_address"]:
            self.main.w.ott_address.setText(config.params["ott_address"])
        self.main.w.set_ott.clicked.connect(save)
        self.main.w.show()

    def set_clone_address(self):
        class TestTTS(QThread):
            uito = Signal(str)
            def __init__(self, *,parent=None,text=None,language=None,role=None):
                super().__init__(parent=parent)
                self.text=text
                self.language=language
                self.role=role

            def run(self):
                from videotrans.tts.clone import get_voice
                try:
                    get_clone_role(True)
                    if len(config.clone_voicelist)<2:
                        raise Exception('没有可供测试的声音')
                    get_voice(text=self.text,language=self.language,role=config.clone_voicelist[1],set_p=False,filename=config.homedir+"/test.mp3")

                    self.uito.emit("ok")
                except Exception as e:
                    self.uito.emit(str(e))
        def feed(d):
            if d=="ok":
                tools.pygameaudio(config.homedir+"/test.mp3")
                QMessageBox.information(self.main.clonw,"ok","Test Ok")
            else:
                QMessageBox.critical(self.main.clonw,config.transobj['anerror'],d)
            self.main.clonw.test.setText('测试' if config.defaulelang=='zh' else 'Test')
        def test():
            if not self.main.clonw.clone_address.text().strip():
                QMessageBox.critical(self.main.clonw,config.transobj['anerror'],'必须填写http地址')
                return
            config.params['clone_api']=self.main.clonw.clone_address.text().strip()
            task=TestTTS(parent=self.main.clonw,
                    text="你好啊我的朋友" if config.defaulelang=='zh' else 'hello,my friend'
                    ,language="zh-cn" if config.defaulelang=='zh' else 'en')
            self.main.clonw.test.setText('测试中请稍等...' if config.defaulelang=='zh' else 'Testing...')
            task.uito.connect(feed)
            task.start()


        def save():
            key = self.main.clonw.clone_address.text().strip()
            key=key.rstrip('/')
            if key:
                key='http://'+key.replace('http://','')
            self.main.settings.setValue("clone_api", key)
            config.params["clone_api"] = key
            self.main.clonw.close()

        from videotrans.component import CloneForm
        self.main.clonw = CloneForm()
        if config.params["clone_api"]:
            self.main.clonw.clone_address.setText(config.params["clone_api"])
        self.main.clonw.set_clone.clicked.connect(save)
        self.main.clonw.test.clicked.connect(test)
        self.main.clonw.show()

    # set baidu
    def set_baidu_key(self):
        def save_baidu():
            appid = self.main.w.baidu_appid.text()
            miyue = self.main.w.baidu_miyue.text()
            self.main.settings.setValue("baidu_appid", appid)
            self.main.settings.setValue("baidu_miyue", miyue)
            config.params["baidu_appid"] = appid
            config.params["baidu_miyue"] = miyue
            self.main.w.close()

        from videotrans.component import BaiduForm
        self.main.w = BaiduForm()
        if config.params["baidu_appid"]:
            self.main.w.baidu_appid.setText(config.params["baidu_appid"])
        if config.params["baidu_miyue"]:
            self.main.w.baidu_miyue.setText(config.params["baidu_miyue"])
        self.main.w.set_badiu.clicked.connect(save_baidu)
        self.main.w.show()

    def set_tencent_key(self):
        def save():
            SecretId = self.main.w.tencent_SecretId.text()
            SecretKey = self.main.w.tencent_SecretKey.text()
            self.main.settings.setValue("tencent_SecretId", SecretId)
            self.main.settings.setValue("tencent_SecretKey", SecretKey)
            config.params["tencent_SecretId"] = SecretId
            config.params["tencent_SecretKey"] = SecretKey
            self.main.w.close()

        from videotrans.component import TencentForm
        self.main.w = TencentForm()
        if config.params["tencent_SecretId"]:
            self.main.w.tencent_SecretId.setText(config.params["tencent_SecretId"])
        if config.params["tencent_SecretKey"]:
            self.main.w.tencent_SecretKey.setText(config.params["tencent_SecretKey"])
        self.main.w.set_tencent.clicked.connect(save)
        self.main.w.show()

    # set chatgpt
    def set_chatgpt_key(self):
        class TestChatgpt(QThread):
            uito = Signal(str)
            def __init__(self, *,parent=None):
                super().__init__(parent=parent)

            def run(self):
                try:
                    from videotrans.translator.chatgpt import trans as trans_chatgpt
                    text = trans_chatgpt("测试正确" if config.defaulelang != 'zh' else "Test is ok",
                                         "English" if config.defaulelang != 'zh' else "Chinese", set_p=False, inst=None)
                    self.uito.emit("ok")
                except Exception as e:
                    self.uito.emit(str(e))
        def feed(d):
            if d!="ok":
                QMessageBox.critical(self.main.w,config.transobj['anerror'],d)
            else:
                QMessageBox.information(self.main.w,"OK","测试正常" if config.defaulelang=='zh' else "All right")
            self.main.w.test_chatgpt.setText('测试' if config.defaulelang=='zh' else 'Test')

        def test():
            config.box_trans='ing'
            task = TestChatgpt(parent=self.main.w)
            self.main.w.test_chatgpt.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
            task.uito.connect(feed)
            task.start()
            self.main.w.test_chatgpt.setText('测试中请稍等...' if config.defaulelang=='zh' else 'Testing...')


        def save_chatgpt():
            key = self.main.w.chatgpt_key.text()
            api = self.main.w.chatgpt_api.text()
            model = self.main.w.chatgpt_model.currentText()
            template = self.main.w.chatgpt_template.toPlainText()
            self.main.settings.setValue("chatgpt_key", key)
            self.main.settings.setValue("chatgpt_api", api)

            self.main.settings.setValue("chatgpt_model", model)
            self.main.settings.setValue("chatgpt_template", template)

            os.environ['OPENAI_API_KEY'] = key
            config.params["chatgpt_key"] = key
            config.params["chatgpt_api"] = api
            config.params["chatgpt_model"] = model
            config.params["chatgpt_template"] = template
            self.main.w.close()

        from videotrans.component import ChatgptForm
        self.main.w = ChatgptForm()
        if config.params["chatgpt_key"]:
            self.main.w.chatgpt_key.setText(config.params["chatgpt_key"])
        if config.params["chatgpt_api"]:
            self.main.w.chatgpt_api.setText(config.params["chatgpt_api"])
        if config.params["chatgpt_model"]:
            self.main.w.chatgpt_model.setCurrentText(config.params["chatgpt_model"])
        if config.params["chatgpt_template"]:
            self.main.w.chatgpt_template.setPlainText(config.params["chatgpt_template"])
        self.main.w.set_chatgpt.clicked.connect(save_chatgpt)
        self.main.w.test_chatgpt.clicked.connect(test)
        self.main.w.show()

    def set_ttsapi(self):
        class TestTTS(QThread):
            uito = Signal(str)
            def __init__(self, *,parent=None,text=None,language=None,rate="+0%",role=None):
                super().__init__(parent=parent)
                self.text=text
                self.language=language
                self.rate=rate
                self.role=role

            def run(self):

                from videotrans.tts.ttsapi import get_voice
                try:

                    get_voice(text=self.text,language=self.language,rate=self.rate,role=self.role,set_p=False,filename=config.homedir+"/test.mp3")

                    self.uito.emit("ok")
                except Exception as e:
                    self.uito.emit(str(e))
        def feed(d):
            if d=="ok":
                tools.pygameaudio(config.homedir+"/test.mp3")
                QMessageBox.information(self.main.ttsapiw,"ok","Test Ok")
            else:
                QMessageBox.critical(self.main.ttsapiw,config.transobj['anerror'],d)
            self.main.ttsapiw.test.setText('测试api' if config.defaulelang=='zh' else 'Test api')
        def test():
            url = self.main.ttsapiw.api_url.text()
            config.params["ttsapi_url"] = url
            task=TestTTS(parent=self.main.ttsapiw,
                    text="你好啊我的朋友" if config.defaulelang=='zh' else 'hello,my friend',
                    role=self.main.ttsapiw.voice_role.text().strip().split(',')[0],
                    language="zh-cn" if config.defaulelang=='zh' else 'en')
            self.main.ttsapiw.test.setText('测试中请稍等...' if config.defaulelang=='zh' else 'Testing...')
            task.uito.connect(feed)
            task.start()



        def save():
            url = self.main.ttsapiw.api_url.text()
            extra = self.main.ttsapiw.extra.text()
            role = self.main.ttsapiw.voice_role.text().strip()

            self.main.settings.setValue("ttsapi_url", url)
            self.main.settings.setValue("ttsapi_extra", extra if extra else "pyvideotrans")
            self.main.settings.setValue("ttsapi_voice_role", role)

            config.params["ttsapi_url"] = url
            config.params["ttsapi_extra"] = extra
            config.params["ttsapi_voice_role"] = role
            self.main.ttsapiw.close()

        from videotrans.component import TtsapiForm
        self.main.ttsapiw = TtsapiForm()
        if config.params["ttsapi_url"]:
            self.main.ttsapiw.api_url.setText(config.params["ttsapi_url"])
        if config.params["ttsapi_voice_role"]:
            self.main.ttsapiw.voice_role.setText(config.params["ttsapi_voice_role"])
        if config.params["ttsapi_extra"]:
            self.main.ttsapiw.extra.setText(config.params["ttsapi_extra"])

        self.main.ttsapiw.save.clicked.connect(save)
        self.main.ttsapiw.test.clicked.connect(test)
        self.main.ttsapiw.show()

    def set_gptsovits(self):
        class TestTTS(QThread):
            uito = Signal(str)
            def __init__(self, *,parent=None,text=None,language=None,role=None):
                super().__init__(parent=parent)
                self.text=text
                self.language=language
                self.role=role

            def run(self):
                from videotrans.tts.gptsovits import get_voice
                try:
                    get_voice(text=self.text,language=self.language,set_p=False,role=self.role,filename=config.homedir+"/test.wav")
                    self.uito.emit("ok")
                except Exception as e:
                    self.uito.emit(str(e))
        def feed(d):
            if d=="ok":
                tools.pygameaudio(config.homedir+"/test.wav")
                QMessageBox.information(self.main.gptsovitsw,"ok","Test Ok")
            else:
                QMessageBox.critical(self.main.gptsovitsw,config.transobj['anerror'],d)
            self.main.gptsovitsw.test.setText('测试api')
        def test():
            url = self.main.gptsovitsw.api_url.text()
            config.params["gptsovits_url"] = url
            task=TestTTS(parent=self.main.gptsovitsw,
                    text="你好啊我的朋友",
                    role=getrole(),
                    language="zh")
            self.main.gptsovitsw.test.setText('测试中请稍等...')
            task.uito.connect(feed)
            task.start()
        
        def getrole():
            tmp=self.main.gptsovitsw.role.toPlainText().strip()
            role=None
            if not tmp:
                return role
            
            for it in tmp.split("\n"):
                s=it.strip().split('#')
                if len(s)!=3:
                    QMessageBox.critical(self.main.gptsovitsw,config.transobj['anerror'],"每行都必须以#分割为三部分，格式为   音频名称.wav#音频文字内容#音频语言代码")
                    return
                if not s[0].endswith(".wav"):
                    QMessageBox.critical(self.main.gptsovitsw,config.transobj['anerror'],"每行都必须以#分割为三部分，格式为  音频名称.wav#音频文字内容#音频语言代码 ,并且第一部分为.wav结尾的音频名称")
                    return
                if s[2] not in ['zh','ja','en']:
                    QMessageBox.critical(self.main.gptsovitsw,config.transobj['anerror'],"每行必须以#分割为三部分，格式为 音频名称.wav#音频文字内容#音频语言代码 ,并且第三部分语言代码只能是 zh或en或ja")
                    return
                role=s[0]
            config.params['gptsovits_role']=tmp
            self.main.settings.setValue("gptsovits_rolel", tmp)
            return role


        def save():
            url = self.main.gptsovitsw.api_url.text()
            extra = self.main.gptsovitsw.extra.text()
            role=self.main.gptsovitsw.role.toPlainText().strip()

            self.main.settings.setValue("gptsovits_role", role)
            self.main.settings.setValue("gptsovits_url", url)
            self.main.settings.setValue("gptsovits_extra", extra if extra else "pyvideotrans")

            config.params["gptsovits_url"] = url
            config.params["gptsovits_extra"] = extra
            config.params["gptsovits_role"] = role
            
            self.main.gptsovitsw.close()

        from videotrans.component import GPTSoVITSForm
        self.main.gptsovitsw = GPTSoVITSForm()
        if config.params["gptsovits_url"]:
            self.main.gptsovitsw.api_url.setText(config.params["gptsovits_url"])
        if config.params["gptsovits_extra"]:
            self.main.gptsovitsw.extra.setText(config.params["gptsovits_extra"])
        if config.params["gptsovits_role"]:
            self.main.gptsovitsw.role.setPlainText(config.params["gptsovits_role"])

        self.main.gptsovitsw.save.clicked.connect(save)
        self.main.gptsovitsw.test.clicked.connect(test)
        self.main.gptsovitsw.show()



    def set_gemini_key(self):
        def save():
            key = self.main.w.gemini_key.text()
            template = self.main.w.gemini_template.toPlainText()
            self.main.settings.setValue("gemini_key", key)
            self.main.settings.setValue("gemini_template", template)

            os.environ['GOOGLE_API_KEY'] = key
            config.params["gemini_key"] = key
            config.params["gemini_template"] = template
            self.main.w.close()

        from videotrans.component import GeminiForm
        self.main.w = GeminiForm()
        if config.params["gemini_key"]:
            self.main.w.gemini_key.setText(config.params["gemini_key"])
        if config.params["gemini_template"]:
            self.main.w.gemini_template.setPlainText(config.params["gemini_template"])
        self.main.w.set_gemini.clicked.connect(save)
        self.main.w.show()

    def set_azure_key(self):
        def save():
            key = self.main.w.azure_key.text()
            api = self.main.w.azure_api.text()
            model = self.main.w.azure_model.currentText()
            template = self.main.w.azure_template.toPlainText()
            self.main.settings.setValue("azure_key", key)
            self.main.settings.setValue("azure_api", api)

            self.main.settings.setValue("azure_model", model)
            self.main.settings.setValue("azure_template", template)

            config.params["azure_key"] = key
            config.params["azure_api"] = api
            config.params["azure_model"] = model
            config.params["azure_template"] = template
            self.main.w.close()

        from videotrans.component import AzureForm
        self.main.w = AzureForm()
        if config.params["azure_key"]:
            self.main.w.azure_key.setText(config.params["azure_key"])
        if config.params["azure_api"]:
            self.main.w.azure_api.setText(config.params["azure_api"])
        if config.params["azure_model"]:
            self.main.w.azure_model.setCurrentText(config.params["azure_model"])
        if config.params["azure_template"]:
            self.main.w.azure_template.setPlainText(config.params["azure_template"])
        self.main.w.set_azure.clicked.connect(save)
        self.main.w.show()

    # 翻译渠道变化时，检测条件
    def set_translate_type(self, name):
        try:
            rs = is_allow_translate(translate_type=name, only_key=True)
            if rs is not True:
                QMessageBox.critical(self.main, config.transobj['anerror'], rs)
                return
            config.params['translate_type'] = name
        except Exception as e:
            QMessageBox.critical(self.main, config.transobj['anerror'], str(e))

    # 0=整体识别模型
    # 1=预先分割模式
    def check_whisper_type(self, index):
        if index == 0:
            config.params['whisper_type'] = 'all'
        elif index==1:
            config.params['whisper_type'] = 'split'
        else:
            config.params['whisper_type'] = 'avg'

    #设定模型类型
    def model_type_change(self):
        if self.main.model_type.currentIndex()==0:
            config.params['model_type']='faster'
        else:
            config.params['model_type']='openai'
        self.check_whisper_model(self.main.whisper_model.currentText())
    # 判断模型是否存在
    def check_whisper_model(self, name):
        if config.params['model_type']=='openai':
            if not os.path.exists(config.rootdir+f"/models/{name}.pt"):
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['openaimodelnot'].replace('{name}',name))
                return False
            return True
        file=f'{config.rootdir}/models/models--Systran--faster-whisper-{name}/snapshots'
        if not os.path.exists(file):
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['downloadmodel'].replace('{name}',name))
            return False
        return True



    # tts类型改变
    def tts_type_change(self, type):
        if self.main.app_mode=='peiyin' and type=='clone-voice' and config.params['voice_role']=='clone':
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['Clone voice cannot be used in subtitle dubbing mode as there are no replicable voices'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            self.set_clone_address()
            return
        if type=='TTS-API' and not config.params['ttsapi_url']:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['ttsapi_nourl'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            self.set_ttsapi()
            return
        if type=='GPT-SoVITS' and not config.params['gptsovits_url']:
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['nogptsovitsurl'])
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            self.set_gptsovits()
            return
        lang = get_code(show_text=self.main.target_language.currentText())
        if lang and lang !='-' and type=='GPT-SoVITS' and lang[:2] not in ['zh','ja','en']:
            self.main.tts_type.setCurrentText(config.params['tts_type_list'][0])
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['nogptsovitslanguage'])
            return

        config.params['tts_type'] = type
        config.params['line_roles'] = {}
        if type == "openaiTTS":
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['openaitts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == 'elevenlabsTTS':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['elevenlabstts_role']
            if len(self.main.current_rolelist) < 1:
                self.main.current_rolelist = get_elevenlabs_role()
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == 'edgeTTS':
            self.set_voice_role(self.main.target_language.currentText())
        elif type=='clone-voice':
            self.main.voice_role.clear()
            self.main.current_rolelist=config.clone_voicelist
            self.main.voice_role.addItems(self.main.current_rolelist)
            threading.Thread(target=get_clone_role).start()
            config.params['is_separate'] = True
            self.main.is_separate.setChecked(True)
        elif type=='TTS-API':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['ttsapi_voice_role'].strip().split(',')
            self.main.voice_role.addItems(self.main.current_rolelist)
        elif type=='GPT-SoVITS':
            rolelist=tools.get_gptsovits_role()
            self.main.voice_role.clear()
            self.main.current_rolelist = list(rolelist.keys()) if rolelist else ['GPT-SoVITS']
            self.main.voice_role.addItems(self.main.current_rolelist)


    # 试听配音
    def listen_voice_fun(self):
        lang = get_code(show_text=self.main.target_language.currentText())
        text = config.params[f'listen_text_{lang}']
        role = self.main.voice_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['mustberole'])
        voice_dir = os.environ.get('APPDATA') or os.environ.get('appdata')
        if not voice_dir or not os.path.exists(voice_dir):
            voice_dir = config.rootdir + "/tmp/voice_tmp"
        else:
            voice_dir = voice_dir.replace('\\', '/') + "/pyvideotrans"
        if not os.path.exists(voice_dir):
            os.makedirs(voice_dir)
        lujing_role=role.replace('/','-')
        voice_file = f"{voice_dir}/{config.params['tts_type']}-{lang}-{lujing_role}.mp3"
        if config.params['tts_type']=='GPT-SoVITS':
            voice_file+='.wav'
        obj = {
            "text": text,
            "rate": "+0%",
            "role": role,
            "voice_file": voice_file,
            "tts_type":config.params['tts_type'],
            "language":lang
        }
        print(f'{obj=}')
        if config.params['tts_type']=='clone-voice' and role=='clone':
            return
        # 测试能否连接clone
        if config.params['tts_type']=='clone-voice':
            try:
                get_clone_role(set_p=True)
            except:
                QMessageBox.critical(self.main,config.transobj['anerror'],config.transobj['You must deploy and start the clone-voice service'])
                return
        def feed(d):
            QMessageBox.critical(self.main,config.transobj['anerror'],d)
        from videotrans.task.play_audio import PlayMp3
        t = PlayMp3(obj, self.main)
        t.mp3_ui.connect(feed)
        t.start()

    # 角色改变时 显示试听按钮
    def show_listen_btn(self, role):
        config.params["voice_role"] = role
        if role == 'No' or (config.params['tts_type']=='clone-voice' and config.params['voice_role']=='clone'):
            self.main.listen_btn.setDisabled(True)
            return
        self.main.listen_btn.show()
        self.main.listen_btn.setDisabled(False)

    # 目标语言改变时设置配音角色
    def set_voice_role(self, t):
        role = self.main.voice_role.currentText()
        # 如果tts类型是 openaiTTS，则角色不变
        # 是edgeTTS时需要改变
        code = get_code(show_text=t)
        if code and code !='-' and config.params['tts_type']=='GPT-SoVITS' and code[:2] not in ['zh','ja','en']:
            #除此指望不支持
            config.params['tts_type']='edgeTTS'
            self.main.tts_type.setCurrentText('edgeTTS')
            QMessageBox.critical(self.main,config.transobj['anerror'],config.transobj['nogptsovitslanguage'])


        # 除 edgeTTS外，其他的角色不会随语言变化
        if config.params['tts_type'] != 'edgeTTS':
            if role != 'No':
                self.main.listen_btn.show()
                self.main.listen_btn.setDisabled(False)
            else:
                self.main.listen_btn.setDisabled(True)
            return

        self.main.listen_btn.hide()
        self.main.voice_role.clear()
        # 未设置目标语言，则清空 edgeTTS角色
        if t == '-':
            self.main.voice_role.addItems(['No'])
            return
        if not config.edgeTTS_rolelist:
            config.edgeTTS_rolelist = get_edge_rolelist()
        if not config.edgeTTS_rolelist:
            self.main.target_language.setCurrentText('-')
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['waitrole'])
            return
        try:
            vt = code.split('-')[0]
            if vt not in config.edgeTTS_rolelist:
                self.main.voice_role.addItems(['No'])
                return
            if len(config.edgeTTS_rolelist[vt]) < 2:
                self.main.target_language.setCurrentText('-')
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['waitrole'])
                return
            self.main.current_rolelist = config.edgeTTS_rolelist[vt]
            self.main.voice_role.addItems(config.edgeTTS_rolelist[vt])
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
            config.last_opendir=os.path.dirname(fnames[0])
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
            content=""
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    content=f.read()
            except:
                with open(fname, 'r', encoding='gbk') as f:
                    content=f.read()
            finally:
                if content:
                    self.main.subtitle_area.clear()
                    self.main.subtitle_area.insertPlainText(content.strip())
                else:
                    return QMessageBox.critical(self.main,config.transobj['anerror'],config.transobj['import src error'])

    # 保存目录
    def get_save_dir(self):
        dirname = QFileDialog.getExistingDirectory(self.main, config.transobj['selectsavedir'], config.last_opendir)
        dirname = dirname.replace('\\', '/')
        self.main.target_dir.setText(dirname)

    # 添加进度条
    def add_process_btn(self, txt):
        clickable_progress_bar = ClickableProgressBar()
        clickable_progress_bar.progress_bar.setValue(0)  # 设置当前进度值
        clickable_progress_bar.setText(
            f'{config.transobj["waitforstart"] if len(self.main.processbtns.keys()) > 0 else config.transobj["kaishiyuchuli"]}' + " " + txt)
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
            # config.params['voice_silence'] = '500'
            config.params['video_autorate'] = False
            config.params['whisper_model'] = 'base'
            config.params['whisper_type'] = 'all'
            config.params['is_separate']=False
            return True
        # 如果是 合并模式,必须有字幕，有视频，有字幕嵌入类型，允许设置视频减速
        # 不需要翻译
        if self.main.app_mode == 'hebing':
            if len(config.queue_mp4) < 1 or config.params['subtitle_type'] < 1 or not txt:
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['hebingmoshisrt'])
                return False
            config.params['is_separate']=False
            config.params['target_language'] = '-'
            config.params['source_language'] = '-'
            # config.params['voice_silence'] = '500'
            config.params['voice_role'] = 'No'
            config.params['voice_rate'] = '+0%'
            config.params['voice_autorate'] = False
            config.params['whisper_model'] = 'base'
            config.params['whisper_type'] = 'all'
            return True
        if self.main.app_mode == 'tiqu_no' or self.main.app_mode == 'tiqu':
            # 提取字幕模式，必须有视频、有原始语言，语音模型
            if len(config.queue_mp4) < 1:
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['selectvideodir'])
                return False

            if self.main.app_mode == 'tiqu' and config.params['target_language'] == '-':
                # 提取字幕并翻译，必须有视频，原始语言，语音模型, 目标语言
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['fanyimoshi1'])
                return False
            config.params['is_separate']=False
            config.params['subtitle_type'] = 0
            config.params['voice_role'] = 'No'
            # config.params['voice_silence'] = '500'
            config.params['voice_rate'] = '+0%'
            config.params['voice_autorate'] = False
            config.params['video_autorate'] = False
            if self.main.app_mode == 'tiqu_no':
                config.params['target_language'] = '-'
        return True

    #
    # 判断是否需要翻译
    # 0 peiyin模式无需翻译，heibng模式无需翻译，tiqu_no模式无需翻译
    # 1. 不存在视频，则是字幕创建配音模式，无需翻译
    # 2. 不存在目标语言，无需翻译
    # 3. 原语言和目标语言相同，不需要翻译
    # 4. 存在字幕，不需要翻译
    # 是否无需翻译，返回True=无需翻译,False=需要翻译
    def dont_translate(self):
        if self.main.app_mode in ['tiqu_no', 'peiyin', 'hebing']:
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

    # 检测开始状态并启动
    def check_start(self):
        if config.current_status == 'ing':
            # 停止
            question = show_popup(config.transobj['exit'], config.transobj['confirmstop'])
            if question == QMessageBox.Yes:
                self.update_status('stop')
                return
        config.settings=config.parse_init()
        # 清理日志
        self.delete_process()

        # 目标文件夹
        target_dir = self.main.target_dir.text().strip().replace('\\', '/')
        if target_dir:
            config.params['target_dir'] = target_dir

        # 设置或删除代理
        config.proxy = self.main.proxy.text().strip()
        try:
            if config.proxy:
                # 设置代理
                set_proxy(config.proxy)
            else:
                # 删除代理
                set_proxy('del')
        except:
            pass

        # 原始语言
        config.params['source_language'] = self.main.source_language.currentText()
        # 目标语言
        target_language = self.main.target_language.currentText()
        config.params['target_language'] = target_language

        # 配音角色
        config.params['voice_role'] = self.main.voice_role.currentText()

        # 配音自动加速
        config.params['voice_autorate'] = self.main.voice_autorate.isChecked()

        # 视频自动减速
        config.params['video_autorate'] = self.main.video_autorate.isChecked()
        # 语音模型
        config.params['whisper_model'] = self.main.whisper_model.currentText()

        # 字幕嵌入类型
        config.params['subtitle_type'] = int(self.main.subtitle_type.currentIndex())

        try:
            voice_rate = int(self.main.voice_rate.text().strip().replace('+', '').replace('%', ''))
            config.params['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"{voice_rate}%"
        except:
            config.params['voice_rate'] = '+0%'
        # try:
        #     voice_silence = int(self.main.voice_silence.text().strip())
        #     config.params['voice_silence'] = voice_silence
        # except:
        #     config.params['voice_silence'] = '500'

        # 字幕区文字
        txt = self.main.subtitle_area.toPlainText().strip()
        if txt and not re.search(r'\d{1,2}:\d{1,2}:\d{1,2}(,\d+)?\s*?-->\s*?\d{1,2}:\d{1,2}:\d{1,2}(,\d+)?',txt):
            txt=""
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
            QMessageBox.critical(self.main, config.transobj['anerror'], 'check-'+config.transobj['bixutianxiecloneapi'])
            return False
        if config.params['tts_type'] == 'elevenlabsTTS' and not config.params["elevenlabstts_key"]:
            QMessageBox.critical(self.main, config.transobj['anerror'], "no elevenlabs  key")
            return False
        # 如果没有选择目标语言，但是选择了配音角色，无法配音
        if config.params['target_language'] == '-' and config.params['voice_role'] != 'No':
            QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['wufapeiyin'])
            return False
        print(config.params['is_separate'])
        # 未主动选择模式，则判断设置情况应该属于什么模式
        if self.main.app_mode == 'biaozhun':
            if len(config.queue_mp4) > 0 and config.params['subtitle_type'] < 1 and config.params['voice_role'] == 'No':
                # tiqu 如果 存在视频但 无配音 无嵌入字幕，则视为提取
                self.main.app_mode = 'tiqu_no' if config.params['source_language'] == config.params[
                    'target_language'] or config.params['target_language'] == '-' else 'tiqu'
                config.params['is_separate']=False
            elif len(config.queue_mp4) > 0 and txt and config.params['subtitle_type'] > 0 and config.params[
                'voice_role'] == 'No':
                # hebing 存在视频，存在字幕，字幕嵌入，不配音
                self.main.app_mode = 'hebing'
                config.params['is_separate']=False
            elif len(config.queue_mp4) < 1 and txt:
                # peiyin
                self.main.app_mode = 'peiyin'
                config.params['is_separate']=False
        if not self.check_mode(txt=txt):
            return False
        # 除了 peiyin  hebing模式，其他均需要检测模型是否存在
        if self.main.app_mode not in ['hebing','peiyin'] and not self.check_whisper_model(config.params['whisper_model']):
            return False

        if config.params["cuda"]:
            import torch
            if not torch.cuda.is_available():
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocuda"])
                return
            if config.params['model_type']=='faster':
                allow=True
                try:
                    from torch.backends import cudnn
                    if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                        allow=False
                except:
                    allow=False
                finally:
                    if not allow:
                        self.main.enable_cuda.setChecked(False)
                        config.params['cuda']=False
                        return QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj["nocudnn"])

        # 如果需要翻译，再判断是否符合翻译规则
        if not self.dont_translate():
            rs = is_allow_translate(translate_type=config.params['translate_type'],
                                    show_target=config.params['target_language'])
            if rs is not True:
                # 不是True，有错误
                QMessageBox.critical(self.main, config.transobj['anerror'], rs)
                return False
        config.queue_task = []

        config.params['back_audio']=self.main.back_audio.text().strip()
        
        # 存在视频
        config.params['only_video']=False
        if len(config.queue_mp4) > 0:
            self.main.show_tips.setText("")
            if self.main.only_video.isChecked():
                config.params['only_video']=True
        elif txt:
            self.main.source_mp4.setText(config.transobj["No select videos"])
            self.main.app_mode='peiyin'
            config.params['is_separate']=False
            if config.params['tts_type']=='clone-voice' and config.params['voice_role']=='clone':
                QMessageBox.critical(self.main, config.transobj['anerror'], config.transobj['Clone voice cannot be used in subtitle dubbing mode as there are no replicable voices'])
                return
        if config.params['voice_role'] == 'No':
            config.params['is_separate'] = False
        # return
        self.main.save_setting()
        self.update_status("ing")
        from videotrans.task.main_worker import Worker
        self.main.task = Worker(parent=self.main,app_mode=self.main.app_mode,txt=txt)
        self.main.task.start()

    # 设置按钮上的日志信息
    def set_process_btn_text(self, text, btnkey="", type="logs"):
        #print(f'{type=}')
        if self.main.task and self.main.task.video:
            # 有视频
            if type != 'succeed':
                text = f'[{self.main.task.video.noextname[:10]}]: {text}'

        #print(f'==========={text=},{type=},{btnkey=}')
        if btnkey and btnkey in self.main.processbtns:
            if type == 'succeed':
                #print(f'succeed==={text},{btnkey=}')
                text, duration = text.split('##')
                self.main.processbtns[btnkey].setTarget(text)
                self.main.processbtns[btnkey].setCursor(Qt.PointingHandCursor)
                text = f'Time:[{duration}s] {config.transobj["endandopen"]}{text}'
                #print(f'{text=}')
                self.main.processbtns[btnkey].progress_bar.setValue(100)
            elif type == 'error' or type =='stop':
                self.main.processbtns[btnkey].setStyleSheet('color:#ff0000')
                self.main.processbtns[btnkey].progress_bar.setStyleSheet('color:#ff0000')
            elif self.main.task and self.main.task.video:
                jindu = f' {round(self.main.task.video.precent, 1)}% ' if self.main.task and self.main.task.video else ""
                self.main.processbtns[btnkey].progress_bar.setValue(int(self.main.task.video.precent))
                text = f'{config.transobj["running"]}{jindu} {text}'
            self.main.processbtns[btnkey].setText(text[:90])
            self.main.processbtns[btnkey].setToolTip(config.transobj['mubiao'])

    # 更新执行状态
    def update_status(self, type):
        config.current_status = type
        self.main.continue_compos.hide()
        self.main.stop_djs.hide()
        if type != 'ing':
            # 结束或停止
            self.main.subtitle_area.setReadOnly(False)
            self.main.startbtn.setText(config.transobj[type])
            # 启用
            self.disabled_widget(False)
            if type == 'end':
                # 成功完成
                self.main.subtitle_area.clear()
                self.main.source_mp4.setText(config.transobj["No select videos"])
            else:
                self.main.continue_compos.hide()
                self.main.target_dir.clear()
                #error or stop 出错
                self.main.source_mp4.setText(config.transobj["No select videos"] if len(config.queue_mp4)<1 else f'{len(config.queue_mp4)} videos')
                # 清理输入
            if self.main.task:
                if self.main.task.video and self.main.task.video.btnkey and type !='end':
                    self.set_process_btn_text("", self.main.task.video.btnkey, type)
                self.main.task.requestInterruption()
                self.main.task.quit()
                self.main.task = None
            if self.main.app_mode =='tiqu':
                self.set_tiquzimu()
            elif self.main.app_mode=='tiqu_no':
                self.set_tiquzimu_no()
            elif self.main.app_mode=='hebing':
                self.set_zimu_video()
            elif self.main.app_mode=='peiyin':
                self.set_zimu_peiyin()
        else:
            # 重设为开始状态
            self.disabled_widget(True)
            self.main.startbtn.setText(config.transobj['running'])

    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        # 一行一行插入字幕到字幕编辑区
        if d['type'] == "subtitle":
            self.main.subtitle_area.moveCursor(QTextCursor.End)
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'add_process':
            self.main.processbtns[d['text']] = self.add_process_btn(d['text'])
        elif d['type'] == 'rename':
            self.main.show_tips.setText(d['text'])
        elif d['type'] == 'set_target_dir':
            self.main.target_dir.setText(config.params['target_dir'])
            if self.main.task and self.main.task.video and self.main.task.video.source_mp4 and self.main.task.video.source_mp4 in self.main.processbtns:
                self.main.processbtns[self.main.task.video.source_mp4].setTarget(self.main.task.video.target_dir if not config.params['only_video'] else config.params['target_dir'])
        elif d['type'] == "logs":
            self.set_process_btn_text(d['text'], d['btnkey'])
        elif d['type'] == 'stop' or d['type'] == 'end' or d['type']=='error':
            self.update_status(d['type'])
            self.main.continue_compos.hide()
            self.main.target_dir.clear()
            print(f'{d=}')
            if d['type']=='error':
                self.set_process_btn_text(d['text'], d['btnkey'],d['type'])
                QMessageBox.critical(self.main,config.transobj['anerror'],d['text'])
            elif d['type']=='stop':
                self.set_process_btn_text(config.transobj['stop'], d['btnkey'],d['type'])
            #elif d['type']!='end':
            #    self.set_process_btn_text(d['text'], d['btnkey'], d['type'])
        elif d['type'] == 'succeed':
            # 本次任务结束
            self.set_process_btn_text(d['text'], d['btnkey'], 'succeed')
        elif d['type'] == 'edit_subtitle':
            # 显示出合成按钮,等待编辑字幕,允许修改字幕
            self.main.subtitle_area.setReadOnly(False)
            self.main.subtitle_area.setFocus()
            self.main.continue_compos.show()
            self.main.continue_compos.setDisabled(False)
            self.main.continue_compos.setText(d['text'])
            self.main.stop_djs.show()
            # 允许试听
            if self.main.task and self.main.task.video.step == 'dubbing_start':
                self.main.listen_peiyin.setDisabled(False)
        elif d['type']=='disabled_edit':
            #禁止修改字幕
            self.main.subtitle_area.setReadOnly(True)
        elif d['type']=='allow_edit':
            #允许修改字幕
            self.main.subtitle_area.setReadOnly(False)
        elif d['type'] == 'replace_subtitle':
            # 完全替换字幕区
            self.main.subtitle_area.clear()
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'timeout_djs':
            self.main.stop_djs.hide()
            self.update_subtitle()
            self.main.continue_compos.setDisabled(True)
            self.main.subtitle_area.setReadOnly(True)
            self.main.listen_peiyin.setDisabled(True)
            self.main.listen_peiyin.setText(config.transobj['shitingpeiyin'])
        elif d['type'] == 'show_djs':
            self.set_process_btn_text(d['text'], d['btnkey'])
        elif d['type'] == 'check_soft_update':
            if not self.usetype:
                self.usetype=QPushButton("")
                self.usetype.setStyleSheet('color:#ffff00;border:0')
                self.usetype.setCursor(QtCore.Qt.PointingHandCursor)
                self.usetype.clicked.connect(lambda: self.open_url('download'))
                self.main.container.addWidget(self.usetype)
            self.usetype.setText(d['text'])

        elif d['type'] == 'update_download' and self.main.youw is not None:
            if d['text']=='ok' or d['text'].find('[error]')>-1:
                self.main.youw.set.setDisabled(False)
            self.main.youw.logs.setText(config.transobj['Down done succeed'] if d['text'] == 'ok' else f"{d['text']}")
        elif d['type'] == 'open_toolbox':
            self.open_toolbox(0, True)
        elif d['type']=='set_clone_role' and config.params['tts_type']=='clone-voice':
            self.main.settings.setValue("clone_voicelist", ','.join(config.clone_voicelist) )
            if config.current_status=='ing':
                return
            current=self.main.voice_role.currentText()
            self.main.voice_role.clear()
            self.main.voice_role.addItems(config.clone_voicelist)
            self.main.voice_role.setCurrentText(current)
        elif d['type']=='win':
            #小窗口背景音分离
            print(f'{d["text"]=}')
            if self.main.sepw is not None:
                self.main.sepw.set.setText(d['text'])
            
            

    # update subtitle 手动 点解了 立即合成按钮，或者倒计时结束超时自动执行
    def update_subtitle(self):
        self.main.stop_djs.hide()
        self.main.continue_compos.setDisabled(True)
        # 如果当前是等待翻译阶段，则更新原语言字幕,然后清空字幕区
        txt = self.main.subtitle_area.toPlainText().strip()
        with open(
                self.main.task.video.targetdir_source_sub if self.main.task.video.step == 'translate_start' else self.main.task.video.targetdir_target_sub,
                'w', encoding='utf-8') as f:
            f.write(txt)
        if self.main.task.video.step == 'translate_start':
            self.main.subtitle_area.clear()
        config.task_countdown = 0
        return True
