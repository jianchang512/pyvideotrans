import json
import re
import os
import webbrowser
import torch
from PyQt5 import QtWidgets
from PyQt5.QtGui import QTextCursor, QDesktopServices
from PyQt5.QtCore import QUrl, Qt, QDir
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QLabel, QPushButton, QTextBrowser, QWidget, QVBoxLayout, \
    QHBoxLayout, QLineEdit, QScrollArea, QCheckBox, QProgressBar
import warnings

from videotrans.component.set_form import InfoForm, AzureForm, GeminiForm, SetLineRole, ElevenlabsForm, YoutubeForm
from videotrans.task.download_youtube import Download
from videotrans.task.main_worker import Worker, Shiting

warnings.filterwarnings('ignore')

from videotrans.component import DeepLForm, DeepLXForm, BaiduForm, TencentForm, ChatgptForm
from videotrans.configure.config import langlist, transobj, logger
from videotrans.configure.config import english_code_bygpt
from videotrans.util.tools import show_popup, set_proxy, get_edge_rolelist, get_elevenlabs_role, get_subtitle_from_srt
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
        self.open_toolbox(0, True)

    def openExternalLink(self, url):
        try:
            QDesktopServices.openUrl(url)
        except:
            pass
        return

    def check_cuda(self, state):
        res = state
        # 选中如果无效，则取消
        if state and not torch.cuda.is_available():
            QMessageBox.critical(self.main, transobj['anerror'], transobj['nocuda'])
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
            return QMessageBox.critical(self.main, transobj['anerror'], transobj['noselectrole'])
        if self.main.shitingobj:
            self.main.shitingobj.stop = True
            self.main.shitingobj = None
            self.main.listen_peiyin.setText(transobj['chongtingzhong'])
        else:
            self.main.listen_peiyin.setText(transobj['shitingzhong'])
        obj = {
            "sub_name": self.main.task.video.targetdir_target_sub,
            "noextname": self.main.task.video.noextname,
            "cache_folder": self.main.task.video.cache_folder,
            "source_wav": self.main.task.video.targetdir_source_sub
        }
        txt = self.main.subtitle_area.toPlainText().strip()
        if not txt:
            return QMessageBox.critical(self.main, transobj['anerror'], transobj['bukeshiting'])
        with open(self.main.task.video.targetdir_target_sub, 'w', encoding='utf-8') as f:
            f.write(txt)
        self.main.shitingobj = Shiting(obj, self.main)
        self.main.shitingobj.start()

    # 启用标准模式
    def set_biaozhun(self):
        self.main.app_mode = 'biaozhun'
        self.main.show_tips.setText("")
        self.main.startbtn.setText(transobj['kaishichuli'])
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
        self.hide_show_element(self.main.layout_voice_silence, True)
        # 配音自动加速
        self.main.voice_autorate.show()
        # 视频自动降速
        self.main.video_autorate.show()
        # cuda
        self.main.enable_cuda.show()

    # 视频提取字幕并翻译，无需配音
    def set_tiquzimu(self):
        self.main.app_mode = 'tiqu'
        self.main.show_tips.setText(transobj['tiquzimu'])
        self.main.startbtn.setText(transobj['kaishitiquhefanyi'])
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
        self.hide_show_element(self.main.layout_voice_silence, False)
        # self.main.voice_silence.setText('500')
        # 配音自动加速
        self.main.voice_autorate.hide()
        self.main.voice_autorate.setChecked(False)
        # 视频自动降速
        self.main.video_autorate.hide()
        self.main.video_autorate.setChecked(False)
        # cuda
        self.main.enable_cuda.show()

    # 从视频提取字幕，不翻译
    # 只显示 选择视频、保存目标、原始语言、语音模型，其他不需要
    def set_tiquzimu_no(self):
        self.main.app_mode = 'tiqu_no'
        self.main.show_tips.setText(transobj['tiquzimuno'])
        self.main.startbtn.setText(transobj['kaishitiquzimu'])
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
        self.hide_show_element(self.main.layout_voice_silence, False)
        # self.main.voice_silence.setText('500')
        # 配音自动加速
        self.main.voice_autorate.hide()
        self.main.voice_autorate.setChecked(False)
        # 视频自动降速
        self.main.video_autorate.hide()
        self.main.video_autorate.setChecked(False)
        # cuda
        self.main.enable_cuda.show()

    # 启用字幕合并模式, 仅显示 选择视频、保存目录、字幕类型、自动视频降速 cuda
    # 不配音、不识别，
    def set_zimu_video(self):
        self.main.app_mode = 'hebing'
        self.main.show_tips.setText(transobj['zimu_video'])
        self.main.startbtn.setText(transobj['kaishihebing'])
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
        self.hide_show_element(self.main.layout_voice_silence, False)

        # 配音自动加速
        self.main.voice_autorate.hide()
        self.main.voice_autorate.setChecked(False)
        # 视频自动降速
        self.main.video_autorate.show()
        self.main.video_autorate.setChecked(False)
        # cuda
        self.main.enable_cuda.show()

    # 仅仅对已有字幕配音，显示目标语言、tts相关，自动加速相关，
    # 不翻译不识别
    def set_zimu_peiyin(self):
        self.main.show_tips.setText(transobj['zimu_peiyin'])
        self.main.startbtn.setText(transobj['kaishipeiyin'])
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
        self.hide_show_element(self.main.layout_voice_silence, False)
        # 配音自动加速
        self.main.voice_autorate.show()
        # 视频自动降速
        self.main.video_autorate.hide()
        self.main.video_autorate.setChecked(False)
        # cuda
        self.main.enable_cuda.show()

    # 关于页面
    def about(self):
        self.main.infofrom = InfoForm()
        self.main.infofrom.show()

    # voice_autorate video_autorate 变化
    def autorate_changed(self, state, name):
        if state:
            if name == 'voice':
                self.main.video_autorate.setChecked(False)
            else:
                self.main.voice_autorate.setChecked(False)
        if name == 'voice':
            config.params['voice_autorate'] = state
        else:
            config.params['video_autorate'] = state

    def open_dir(self, dirname=None):
        if not dirname:
            return
        if not os.path.isdir(dirname):
            dirname = os.path.dirname(dirname)
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
        self.main.btn_get_video.setDisabled(type)
        self.main.source_mp4.setDisabled(type)
        self.main.btn_save_dir.setDisabled(type)
        self.main.target_dir.setDisabled(type)
        self.main.translate_type.setDisabled(type)
        self.main.proxy.setDisabled(type)
        self.main.source_language.setDisabled(type)
        self.main.target_language.setDisabled(type)
        self.main.tts_type.setDisabled(type)
        self.main.whisper_model.setDisabled(type)
        self.main.whisper_type.setDisabled(type)
        self.main.subtitle_type.setDisabled(type)
        self.main.voice_silence.setDisabled(type)
        self.main.video_autorate.setDisabled(type)
        self.main.enable_cuda.setDisabled(type)

    def open_url(self, title):
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
        elif title == 'website':
            webbrowser.open_new_tab("https://v.wonyes.org")
        elif title == "about":
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/blob/main/about.md")
        elif title == 'download':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/releases")

    # 工具箱
    def open_toolbox(self, index=0, is_hide=False):
        try:
            import box
            if self.main.toolboxobj is None:
                self.main.toolboxobj = box.MainWindow()
            if is_hide:
                self.main.toolboxobj.hide()
                return
            self.main.toolboxobj.show()
            self.main.toolboxobj.tabWidget.setCurrentIndex(index)
            self.main.toolboxobj.raise_()
        except Exception as e:
            self.main.toolboxobj = None
            QMessageBox.critical(self.main, transobj['anerror'], str(e))
            logger.error("box" + str(e))

    # 将倒计时设为立即超时
    def set_djs_timeout(self):
        config.task_countdown = 0
        self.main.continue_compos.setText(transobj['jixuzhong'])
        self.main.continue_compos.setDisabled(True)
        self.main.stop_djs.hide()
        if self.main.shitingobj:
            self.main.shitingobj.stop = True

    # 手动点击停止自动合并倒计时
    def reset_timeid(self):
        self.main.stop_djs.hide()
        config.task_countdown = 86400
        self.main.continue_compos.setDisabled(False)
        self.main.continue_compos.setText(transobj['nextstep'])

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
                return QMessageBox.critical(self.main.w, transobj['anerror'], transobj['zhishaoxuanzeyihang'])

            for n in checked_checkbox_names:
                _, line = n.split('_')
                # 设置labe为角色名
                ck = self.main.w.findChild(QCheckBox, n)
                ck.setText(transobj['default'] if role in ['No', 'no', '-'] else role)
                ck.setChecked(False)
                config.params['line_roles'][line] = config.params['voice_role'] if role in ['No', 'no', '-'] else role
            print(config.params['line_roles'])

        self.main.w = SetLineRole()
        box = QWidget()  # 创建新的 QWidget，它将承载你的 QHBoxLayouts
        box.setLayout(QVBoxLayout())  # 设置 QVBoxLayout 为新的 QWidget 的layout
        if config.params['voice_role'] in ['No', '-', 'no']:
            return QMessageBox.critical(self.main.w, transobj['anerror'], transobj['xianxuanjuese'])
        if not self.main.subtitle_area.toPlainText().strip():
            return QMessageBox.critical(self.main.w, transobj['anerror'], transobj['youzimuyouset'])

        #  获取字幕
        srt_json = get_subtitle_from_srt(self.main.subtitle_area.toPlainText().strip(), is_file=False)
        for it in srt_json:
            # 创建新水平布局
            h_layout = QHBoxLayout()
            check = QCheckBox()
            check.setText(
                config.params['line_roles'][f'{it["line"]}'] if f'{it["line"]}' in config.params['line_roles'] else
                transobj['default'])
            check.setObjectName(f'check_{it["line"]}')
            # 创建并配置 QLineEdit
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(transobj['shezhijueseline'])

            line_edit.setText(f'[{it["line"]}] {it["text"]}')
            line_edit.setReadOnly(True)
            # 将标签和编辑线添加到水平布局
            h_layout.addWidget(check)
            h_layout.addWidget(line_edit)
            box.layout().addLayout(h_layout)
        self.main.w.select_role.addItems(self.main.current_rolelist)
        self.main.w.set_role_label.setText(transobj['shezhijuese'])

        self.main.w.select_role.currentTextChanged.connect(save)
        # 创建 QScrollArea 并将 box QWidget 设置为小部件
        scroll_area = QScrollArea()
        scroll_area.setWidget(box)
        scroll_area.setWidgetResizable(True)

        # 将 QScrollArea 添加到主窗口的 layout
        self.main.w.layout.addWidget(scroll_area)

        self.main.w.set_ok.clicked.connect(lambda: self.main.w.close())
        self.main.w.show()

    def open_youtube(self):
        def download():
            proxy = self.main.youw.proxy.text().strip()
            outdir = self.main.youw.outputdir.text()
            url = self.main.youw.url.text()
            if not url or not re.match(r'https://www.youtube.com/watch', url):
                QMessageBox.critical(self.main.youw, transobj['anerror'],
                                     'must input like https://www.youtube.com/watch?v=jNQXAC9IVRw')
                return
            self.main.settings.setValue("youtube_outdir", outdir)
            print('start download')
            cmd = ["you-get", "--itag=18", "-o", outdir]
            if proxy:
                config.proxy = proxy
                self.main.settings.setValue("proxy", proxy)
                cmd.append("-x")
                cmd.append(proxy)
            cmd.append(url)
            down = Download(cmd, self.main)
            down.start()

        def selectdir():
            dirname = QFileDialog.getExistingDirectory(self.main, "Select Dir", outdir).replace('\\', '/')
            self.main.w.outputdir.setText(dirname)

        self.main.youw = YoutubeForm()
        outdir = config.params['youtube_outdir'] if 'youtube_outdir' in config.params else os.path.join(config.homedir,
                                                                                                        'youtube').replace(
            '\\', '/')
        if not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
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
            self.main.settings.setValue("deepl_authkey", key)
            config.params['deepl_authkey'] = key
            self.main.w.close()

        self.main.w = DeepLForm()
        if config.params['deepl_authkey']:
            self.main.w.deepl_authkey.setText(config.params['deepl_authkey'])
        self.main.w.set_deepl.clicked.connect(save)
        self.main.w.show()

    def set_elevenlabs_key(self):
        def save():
            key = self.main.w.elevenlabstts_key.text()
            self.main.settings.setValue("elevenlabstts_key", key)
            config.params['elevenlabstts_key'] = key
            self.main.w.close()

        self.main.w = ElevenlabsForm()
        if config.params['elevenlabstts_key']:
            self.main.w.elevenlabstts_key.setText(config.params['elevenlabstts_key'])
        self.main.w.set.clicked.connect(save)
        self.main.w.show()

    def set_deepLX_address(self):
        def save():
            key = self.main.w.deeplx_address.text()
            self.main.settings.setValue("deeplx_address", key)
            config.deeplx_address = key
            self.main.w.close()

        self.main.w = DeepLXForm()
        if config.params["deeplx_address"]:
            self.main.w.deeplx_address.setText(config.params["deeplx_address"])
        self.main.w.set_deeplx.clicked.connect(save)
        self.main.w.show()

    # set baidu
    def set_baidu_key(self):
        def save_baidu():
            appid = self.main.w.baidu_appid.text()
            miyue = self.main.w.baidu_miyue.text()
            self.main.settings.setValue("baidu_appid", appid)
            self.main.settings.setValue("baidu_miyue", miyue)
            config.baidu_appid = appid
            config.baidu_miyue = miyue
            self.main.w.close()

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

        self.main.w = TencentForm()
        if config.params["tencent_SecretId"]:
            self.main.w.tencent_SecretId.setText(config.params["tencent_SecretId"])
        if config.params["tencent_SecretKey"]:
            self.main.w.tencent_SecretKey.setText(config.params["tencent_SecretKey"])
        self.main.w.set_tencent.clicked.connect(save)
        self.main.w.show()

    # set chatgpt
    def set_chatgpt_key(self):
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
        self.main.w.show()

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
            if name == "baidu" and not config.params["baidu_appid"]:
                QMessageBox.critical(self.main, transobj['anerror'], transobj['baidukeymust'])
                return
            if name == "chatGPT" and not config.params["chatgpt_key"]:
                QMessageBox.critical(self.main, transobj['anerror'], transobj['chatgptkeymust'])
                return
            if name == "Azure" and not config.params["azure_key"]:
                QMessageBox.critical(self.main, transobj['anerror'], transobj['tianxieazure'])
                return
            if name == "DeepL" and not config.params["deepl_authkey"]:
                QMessageBox.critical(self.main, transobj['anerror'], transobj['setdeepl_authkey'])
                return
            if name == "DeepLX" and not config.params["deeplx_address"]:
                QMessageBox.critical(self.main, transobj['anerror'], transobj['setdeeplx_address'])
                return
            config.params['translate_type'] = name
        except Exception as e:
            QMessageBox.critical(self.main, transobj['anerror'], str(e))

    def check_whisper_type(self, index):
        if index == 0:
            config.params['whisper_type'] = 'all'
        else:
            config.params['whisper_type'] = 'split'

    # check model is exits
    def check_whisper_model(self, name):
        if not os.path.exists(config.rootdir + f"/models/models--Systran--faster-whisper-{name}"):
            self.main.statusLabel.setText(
                transobj['downloadmodel'] + f" ./models/models--Systran--faster-whisper-{name}")
            QMessageBox.critical(self.main, transobj['downloadmodel'], f"./models/")
        else:
            self.main.statusLabel.setText(transobj['modelpathis'] + f" ./models/models--Systran--faster-whisper-{name}")

    # 更新执行状态
    def update_status(self, type):
        config.current_status = type
        self.main.continue_compos.hide()
        self.main.stop_djs.hide()
        if type != 'ing':
            # 结束或停止
            self.main.startbtn.setText(transobj[type])
            # 启用
            self.disabled_widget(False)
            if type == 'end':
                # 清理字幕
                self.main.subtitle_area.clear()
                # 清理输入
            self.main.statusLabel.setText(transobj['bencijieshu'])
            self.main.source_mp4.clear()
            # self.main.target_dir.clear()
            if self.main.task:
                self.main.task.requestInterruption()
                self.main.task.quit()
        else:
            # 重设为开始状态
            self.disabled_widget(True)
            self.main.startbtn.setText(transobj['running'])
            self.main.statusLabel.setText(transobj['kaishichuli'])

    # tts类型改变
    def tts_type_change(self, type):
        config.params['tts_type'] = type
        config.params['line_roles'] = {}
        if type == "openaiTTS":
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['openaitts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == 'coquiTTS':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['coquitts_role'].split(',')
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == 'elevenlabsTTS':
            self.main.voice_role.clear()
            self.main.current_rolelist = config.params['elevenlabstts_role']
            if len(self.main.current_rolelist) < 1:
                self.main.current_rolelist = get_elevenlabs_role()
            self.main.voice_role.addItems(['No'] + self.main.current_rolelist)
        elif type == 'edgeTTS':
            self.set_voice_role(self.main.target_language.currentText())

    # 试听配音
    def listen_voice_fun(self):
        currentlang = self.main.target_language.currentText()
        if currentlang in ["English", "英语"]:
            text = config.params['listen_text_en']
            lang = "en"
        elif currentlang in ["中文简", "中文繁", "Simplified_Chinese", "Traditional_Chinese"]:
            text = config.params['listen_text_cn']
            lang = "zh"
        else:
            return
        role = self.main.voice_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(self.main, transobj['anerror'], transobj['mustberole'])
        voice_dir = os.environ.get('APPDATA') or os.environ.get('appdata')
        if not voice_dir or not os.path.exists(voice_dir):
            voice_dir = config.rootdir + "/tmp/voice_tmp"
        else:
            voice_dir = voice_dir.replace('\\', '/') + "/pyvideotrans"
        if not os.path.exists(voice_dir):
            os.makedirs(voice_dir)
        voice_file = f"{voice_dir}/{config.params['tts_type']}-{lang}-{role}.mp3"
        obj = {
            "text": text,
            "rate": "+0%",
            "role": role,
            "voice_file": voice_file
        }
        from videotrans.task.play_audio import PlayMp3
        t = PlayMp3(obj, self.main)
        t.start()

    # 显示试听按钮
    def show_listen_btn(self, role):
        if config.current_status == 'ing' and config.params["voice_role"] != 'No' and role == 'No':
            QMessageBox.critical(self.main, transobj['anerror'], transobj['yunxingbukerole'])
            self.main.voice_role.setCurrentText(config.params["voice_role"])
            return
        config.params["voice_role"] = role
        t = self.main.target_language.currentText()
        if role != 'No' and t in ["中文简", "中文繁", "英语", "Simplified_Chinese", "Traditional_Chinese", "English"]:
            self.main.listen_btn.show()
            self.main.listen_btn.setDisabled(False)
        else:
            self.main.listen_btn.hide()
            self.main.listen_btn.setDisabled(True)

    # 目标语言改变时设置配音角色
    def set_voice_role(self, t):
        role = self.main.voice_role.currentText()
        # 如果tts类型是 openaiTTS，则角色不变
        # 是edgeTTS时需要改变
        if config.params['tts_type'] != 'edgeTTS':
            if role != 'No' and t in ["中文简", "中文繁", "英语", "Simplified_Chinese", "Traditional_Chinese", "English"]:
                self.main.listen_btn.show()
                self.main.listen_btn.setDisabled(False)
            else:
                self.main.listen_btn.hide()
                self.main.listen_btn.setDisabled(True)
            return
        self.main.listen_btn.hide()
        self.main.voice_role.clear()
        if t == '-':
            self.main.voice_role.addItems(['No'])
            return
        if not config.edgeTTS_rolelist:
            config.edgeTTS_rolelist = get_edge_rolelist()
        if not config.edgeTTS_rolelist:
            self.main.target_language.setCurrentText('-')
            QMessageBox.critical(self.main, transobj['anerror'], transobj['waitrole'])
            return
        try:
            vt = langlist[t][0].split('-')[0]
            if vt not in config.edgeTTS_rolelist:
                self.main.voice_role.addItems(['No'])
                return
            if len(config.edgeTTS_rolelist[vt]) < 2:
                self.main.target_language.setCurrentText('-')
                QMessageBox.critical(self.main, transobj['anerror'], transobj['waitrole'])
                return
            self.main.current_rolelist = config.edgeTTS_rolelist[vt]
            self.main.voice_role.addItems(config.edgeTTS_rolelist[vt])
        except:
            self.main.voice_role.addItems(['No'])
            # self.main.voice_role.addItems([it for item in list(config.edgeTTS_rolelist.values()) for it in item])

    # get video filter mp4
    def get_mp4(self):
        fnames, _ = QFileDialog.getOpenFileNames(self.main, transobj['selectmp4'], self.main.last_dir,
                                                 "Video files(*.mp4 *.avi *.mov *.mpg *.mkv)")
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/')

        if len(fnames) > 0:
            self.main.source_mp4.setText(fnames[0])
            config.params['source_mp4'] = self.main.source_mp4
            self.main.settings.setValue("last_dir", os.path.dirname(fnames[0]))
            config.queue_mp4 = fnames

    # 从本地导入字幕文件
    def import_sub_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self.main, transobj['selectmp4'], self.main.last_dir,
                                               "Srt files(*.srt *.txt)")
        if fname:
            with open(fname, 'r', encoding='utf-8') as f:
                self.main.subtitle_area.insertPlainText(f.read().strip())
                # self.main.import_sub.setDisabled(False)

    # 保存目录
    def get_save_dir(self):
        dirname = QFileDialog.getExistingDirectory(self.main, transobj['selectsavedir'], self.main.last_dir)
        dirname = dirname.replace('\\', '/')
        self.main.target_dir.setText(dirname)

    # 添加进度条
    def add_process_btn(self, txt, index=0):
        clickable_progress_bar = ClickableProgressBar()
        clickable_progress_bar.progress_bar.setValue(0)  # 设置当前进度值
        clickable_progress_bar.setText(
            f'{transobj["waitforstart"] if index > 0 else transobj["kaishiyuchuli"]}' + " " + txt)
        clickable_progress_bar.setMinimumSize(500, 50)

        # # 设置按钮高度为 80px，宽度撑满父控件
        # button1.setFixedHeight(50)
        # button1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        #
        # # 将按钮添加到布局中
        self.main.processlayout.addWidget(clickable_progress_bar)
        return clickable_progress_bar

    # 检测各个模式下参数是否设置正确
    def check_mode(self, *, txt=None, model=None):
        # 如果是 配音模式
        if self.main.app_mode == 'peiyin':
            if not txt or config.params['voice_role'] in ['-', 'no', 'No'] or config.params['target_language'] == '-':
                QMessageBox.critical(self.main, transobj['anerror'], transobj['peiyinmoshisrt'])
                return False
            # 去掉选择视频，去掉原始语言
            config.params['source_mp4'] = ''
            config.params['source_language'] = ''
            config.params['subtitle_type'] = 0
            config.params['voice_silence'] = '500'
            config.params['video_autorate'] = False
            config.params['whisper_model'] = 'base'
            config.params['whisper_type'] = 'all'
        # 如果是 合并模式,必须有字幕，有视频，有字幕嵌入类型，允许设置视频减速
        elif self.main.app_mode == 'hebing':
            if not config.params['source_mp4'] or config.params['subtitle_type'] < 1 or not txt:
                QMessageBox.critical(self.main, transobj['anerror'], transobj['hebingmoshisrt'])
                return False
            config.params['target_language'] = '-'
            config.params['source_language'] = '-'
            config.params['voice_silence'] = '500'
            config.params['voice_role'] = 'No'
            config.params['voice_rate'] = '+0%'
            config.params['voice_autorate'] = False
            config.params['whisper_model'] = 'base'
            config.params['whisper_type'] = 'all'
        elif self.main.app_mode == 'tiqu_no' or self.main.app_mode == 'tiqu':
            # 提取字幕模式，必须有视频、有原始语言，语音模型
            if not config.params['source_mp4']:
                QMessageBox.critical(self.main, transobj['anerror'], transobj['selectvideodir'])
                return False
            elif not os.path.exists(model):
                QMessageBox.critical(self.main, transobj['downloadmodel'], f" ./models/")
                self.main.statusLabel.setText(transobj[
                                                  'downloadmodel'] + f" ./models/models--Systran--faster-whisper-{config.params['whisper_model']}")
                return False
            if self.main.app_mode == 'tiqu' and config.params['target_language'] in ['-', 'no', 'No']:
                # 提取字幕并翻译，必须有视频，原始语言，语音模型, 目标语言
                QMessageBox.critical(self.main, transobj['anerror'], transobj['fanyimoshi1'])
                return False
            config.params['subtitle_type'] = 0
            config.params['voice_role'] = 'No'
            config.params['voice_silence'] = '500'
            config.params['voice_rate'] = '+0%'
            config.params['voice_autorate'] = False
            config.params['video_autorate'] = False
            if self.main.app_mode == 'tiqu_no':
                config.params['target_language'] = '-'
        return True

    # 检测开始状态并启动
    def check_start(self):
        if config.current_status == 'ing':
            question = show_popup(transobj['exit'], transobj['confirmstop'])
            if question == QMessageBox.AcceptRole:
                self.update_status('stop')
                return
        # 清理日志
        self.delete_process()

        # 选择视频
        config.params['source_mp4'] = self.main.source_mp4.text().strip().replace('\\', '/')
        target_dir = self.main.target_dir.text().strip().replace('\\', '/')
        # 目标文件夹
        if target_dir:
            config.params['target_dir'] = target_dir

        # 代理
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
        config.params['source_language'] = langlist[self.main.source_language.currentText()][0]
        # 目标语言
        target_language = self.main.target_language.currentText()
        config.params['target_language'] = target_language

        # 如果选择了目标语言，再去处理相关
        if '-' != target_language:
            config.params['target_language'] = langlist[target_language][0]
            # google language code
            if config.params['translate_type'] == 'google':
                config.params['target_language'] = langlist[target_language][0]
            elif config.params['translate_type'] == 'baidu':
                # baidu language code
                config.params['target_language_baidu'] = langlist[target_language][2]
                if not config.params["baidu_appid"] or not config.params["baidu_miyue"]:
                    QMessageBox.critical(self.main, transobj['anerror'], transobj['baikeymust'])
                    return
            elif config.params['translate_type'] == 'tencent':
                #     腾讯翻译
                config.params['target_language_tencent'] = langlist[target_language][4]
                if not config.params["tencent_SecretId"] or not config.params["tencent_SecretKey"]:
                    QMessageBox.critical(self.main, transobj['anerror'], transobj['tencent_key'])
                    return
            elif config.params['translate_type'] == 'chatGPT':
                # chatGPT 翻译
                config.params['target_language_chatgpt'] = english_code_bygpt[
                    self.main.languagename.index(target_language)]
                if not config.params["chatgpt_key"]:
                    QMessageBox.critical(self.main, transobj['anerror'], transobj['chatgptkeymust'])
                    return
            elif config.params['translate_type'] == 'Azure':
                # chatGPT 翻译
                config.params['target_language_azure'] = english_code_bygpt[
                    self.main.languagename.index(target_language)]
                if not config.params["azure_key"]:
                    QMessageBox.critical(self.main, transobj['anerror'], '必须填写Azure key')
                    return
            elif config.params['translate_type'] == 'Gemini':
                # chatGPT 翻译
                config.params['target_language_gemini'] = english_code_bygpt[
                    self.main.languagename.index(target_language)]
                if not config.params["gemini_key"]:
                    QMessageBox.critical(self.main, transobj['anerror'], transobj['bixutianxie'] + 'google Gemini key')
                    return
            elif config.params['translate_type'] == 'DeepL' or config.params['translate_type'] == 'DeepLX':
                # DeepL翻译
                if config.params['translate_type'] == 'DeepL' and not config.params["deepl_authkey"]:
                    QMessageBox.critical(self.main, transobj['anerror'], transobj['deepl_authkey'])
                    return
                if config.params['translate_type'] == 'DeepLX' and not config.params["deeplx_address"]:
                    QMessageBox.critical(self.main, transobj['anerror'], transobj['setdeeplx_address'])
                    return

                config.params['target_language_deepl'] = langlist[target_language][3]
                if config.params['target_language_deepl'] == 'No':
                    QMessageBox.critical(self.main, transobj['anerror'], transobj['deepl_nosupport'])
                    return
            # 目标字幕语言
            config.params['subtitle_language'] = langlist[self.main.target_language.currentText()][1]
        # 检测字幕原始语言
        config.params['detect_language'] = langlist[self.main.source_language.currentText()][0]
        # 配音角色
        config.params['voice_role'] = self.main.voice_role.currentText()

        # 配音自动加速
        config.params['voice_autorate'] = self.main.voice_autorate.isChecked()

        # 视频自动减速
        config.params['video_autorate'] = self.main.video_autorate.isChecked()
        # 语音模型
        config.params['whisper_model'] = self.main.whisper_model.currentText()
        model = config.rootdir + f"/models/models--Systran--faster-whisper-{config.params['whisper_model']}"
        # 字幕嵌入类型
        config.params['subtitle_type'] = int(self.main.subtitle_type.currentIndex())

        try:
            voice_rate = int(self.main.voice_rate.text().strip().replace('+', '').replace('%', ''))
            config.params['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"-{voice_rate}%"
        except:
            config.params['voice_rate'] = '+0%'
        try:
            voice_silence = int(self.main.voice_silence.text().strip())
            config.params['voice_silence'] = voice_silence
        except:
            config.params['voice_silence'] = '500'
        # 字幕区文字
        txt = self.main.subtitle_area.toPlainText().strip()

        if not self.check_mode(txt=txt, model=model):
            return False

        # 综合判断
        if not config.params['source_mp4'] and not txt:
            QMessageBox.critical(self.main, transobj['anerror'], transobj['bukedoubucunzai'])
            return False
        # tts类型
        if config.params['tts_type'] == 'openaiTTS' and not config.params["chatgpt_key"]:
            QMessageBox.critical(self.main, transobj['anerror'], transobj['chatgptkeymust'])
            return False
        # 如果没有选择目标语言，但是选择了配音角色，无法配音
        if config.params['target_language'] == '-' and config.params['voice_role'] != 'No':
            QMessageBox.critical(self.main, transobj['anerror'], transobj['wufapeiyin'])
            return False

        if config.params['source_mp4'] and len(config.queue_mp4) < 1:
            config.queue_mp4 = [config.params['source_mp4']]

        # 对各种设置情况判断属于什么模式
        if self.main.app_mode == 'biaozhun':
            if config.params['source_mp4'] and config.params['subtitle_type'] < 1 and config.params['voice_role'] in [
                'No', 'no', '-']:
                # tiqu 如果 存在视频但无配音 无嵌入字幕，则视为提取
                self.main.app_mode = 'tiqu_no' if config.params[
                                                      'source_language'] == target_language or target_language == '-' else 'tiqu'
            elif config.params['source_mp4'] and txt and config.params['subtitle_type'] > 0 and (
                    config.params['source_language'] == target_language or target_language == '-'):
                # hebing 存在视频，存在字幕，字幕嵌入，不存在目标语言或源目标语言相同无需翻译，视为合并
                self.main.app_mode = 'hebing'
            elif not config.params['source_mp4'] and txt:
                # peiyin
                self.main.app_mode = 'peiyin'
        if not self.check_mode(txt=txt, model=model):
            return False

        if config.params["cuda"] and not torch.cuda.is_available():
            config.params['cuda'] = False
            self.main.enable_cuda.setChecked(False)
            if os.environ.get('CUDA_OK'):
                os.environ.pop('CUDA_OK')
        self.main.save_setting()
        self.update_status("ing")

        config.queue_task = []
        # 存在视频
        if len(config.queue_mp4) > 0:
            for (i, it) in enumerate(config.queue_mp4):
                # 插入进度条
                key = it if re.search(r'\.mp4', it, re.I) else re.sub(r'\.[a-zA-Z0-9]+$', '.mp4', it, re.I)
                self.main.processbtns[key] = self.add_process_btn(key, i)
            while len(config.queue_mp4) > 0:
                config.queue_task.append(
                    {'subtitles': txt, "source_mp4": config.queue_mp4.pop(0), 'app_mode': self.main.app_mode})
        elif txt:
            # 不存在视频,已存在字幕
            config.queue_task.append({"subtitles": txt, 'app_mode': self.main.app_mode})
            self.main.processbtns["srt2wav"] = self.add_process_btn("srt2wav")
        self.main.task = Worker(self.main)
        self.main.task.start()

    # 设置按钮上的日志信息
    def set_process_btn_text(self, text, btnkey="", type="logs"):
        # btnkey=None
        if self.main.task and self.main.task.video:
            # 有视频
            # btnkey =  #self.main.task.video.source_mp4 if re.search(r'\.mp4',self.main.task.video.source_mp4,re.I) else re.sub(r'\.[a-zA-Z0-9]+$','.mp4',self.main.task.video.source_mp4,re.I)
            if type != 'succeed':
                text = f'{self.main.task.video.noextname}: {text}'
        # elif self.main.task and self.main.task.video:
        # 字幕到配音，无视频
        # btnkey = "srt2wav"

        if btnkey and btnkey in self.main.processbtns:
            if type == 'succeed':
                text, duration = text.split('##')
                self.main.processbtns[btnkey].setTarget(text)
                text = f'Time:[{duration}s] {transobj["endandopen"]}{text}'
                self.main.processbtns[btnkey].progress_bar.setValue(100)
            elif type == 'error':
                self.main.processbtns[btnkey].setStyleSheet('color:#ff0000')
                self.main.processbtns[btnkey].progress_bar.setStyleSheet('color:#ff0000')
            else:
                jindu = f'[{round(self.main.task.video.precent, 1)}%]' if self.main.task and self.main.task.video else ""
                self.main.processbtns[btnkey].progress_bar.setValue(int(self.main.task.video.precent))
                text = f'{transobj["running"]}{jindu} {text}'
            self.main.processbtns[btnkey].setText(text[:90])

    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        # 一行一行插入字幕到字幕编辑区
        if d['type'] == "subtitle":
            self.main.subtitle_area.moveCursor(QTextCursor.End)
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'set_target_dir':
            self.main.target_dir.setText(config.params['target_dir'])
            if self.main.task and self.main.task.video and self.main.task.video.source_mp4 and self.main.task.video.source_mp4 in self.main.processbtns:
                self.main.processbtns[self.main.task.video.source_mp4].setTarget(self.main.task.video.target_dir)
        elif d['type'] == "logs":
            self.set_process_btn_text(d['text'], d['btnkey'])
        elif d['type'] == 'stop' or d['type'] == 'end':
            self.update_status(d['type'])
            self.main.continue_compos.hide()
            self.main.statusLabel.setText(transobj['bencijieshu'])
            self.main.target_dir.clear()
        elif d['type'] == 'succeed':
            # 本次任务结束
            self.set_process_btn_text(d['text'], d['btnkey'], 'succeed')
        elif d['type'] == 'statusbar':
            self.main.statusLabel.setText(d['text'])
        elif d['type'] == 'error':
            # 出错停止
            self.update_status('stop')
            self.set_process_btn_text(d['text'], d['btnkey'], 'error')
            self.main.continue_compos.hide()
        elif d['type'] == 'edit_subtitle':
            # 显示出合成按钮,等待编辑字幕
            self.main.continue_compos.show()
            self.main.continue_compos.setDisabled(False)
            self.main.continue_compos.setText(d['text'])
            self.main.stop_djs.show()
            # 允许试听
            if self.main.task.video.step == 'dubbing_start':
                self.main.listen_peiyin.setDisabled(False)
        elif d['type'] == 'replace_subtitle':
            # 完全替换字幕区
            self.main.subtitle_area.clear()
            self.main.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'timeout_djs':
            self.main.stop_djs.hide()
            self.update_subtitle()
            self.main.continue_compos.setDisabled(True)
            self.main.listen_peiyin.setDisabled(True)
            self.main.listen_peiyin.setText(transobj['shitingpeiyin'])
        elif d['type'] == 'show_djs':
            self.set_process_btn_text(d['text'], d['btnkey'])
        elif d['type'] == 'check_soft_update':
            self.main.setWindowTitle(self.main.rawtitle + " -- " + d['text'])
            usetype = QPushButton(d['text'])
            usetype.setStyleSheet('color:#ff9800')
            usetype.clicked.connect(lambda: self.open_url('download'))
            self.main.container.addWidget(usetype)
        elif d['type'] == 'update_download' and self.main.youw is not None:
            self.main.youw.logs.setText("Down done succeed" if d['text'] == 'ok' else d['text'])

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
