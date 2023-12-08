# -*- coding: utf-8 -*-
import copy
import datetime
import json
import shutil
import sys
import os
import threading
import webbrowser
import torch

from PyQt5 import QtWidgets
from PyQt5.QtGui import QTextCursor, QIcon, QDesktopServices
from PyQt5.QtCore import QSettings, QUrl, Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QLabel, QPushButton, QToolBar
import warnings

from videotrans.component.set_form import InfoForm
from videotrans.task.check_update import CheckUpdateWorker
from videotrans.task.logs_worker import LogsWorker
from videotrans.task.main_worker import Worker, Shiting

warnings.filterwarnings('ignore')

from videotrans import VERSION
from videotrans.component import DeepLForm, DeepLXForm, BaiduForm, TencentForm, ChatgptForm
from videotrans.component.controlobj import TextGetdir
from videotrans.configure.config import langlist, transobj, logger, homedir
from videotrans.configure.language import english_code_bygpt
from videotrans.util.tools import show_popup, set_proxy, set_process, get_edge_rolelist, is_vlc
from videotrans.configure import config
import pygame

if config.defaulelang == "zh":
    from videotrans.ui.cn import Ui_MainWindow
else:
    from videotrans.ui.en import Ui_MainWindow


# primary ui
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.cfg = config.video
        self.task = None
        self.toolboxobj = None
        self.shitingobj = None
        self.initUI()
        self.setWindowIcon(QIcon("./icon.ico"))
        self.rawtitle = f"{'视频翻译配音' if config.defaulelang != 'en' else ' Video Translate & Dubbing'} {VERSION}"
        self.setWindowTitle(self.rawtitle)

    def initUI(self):
        self.settings = QSettings("Jameson", "VideoTranslate")
        # 获取最后一次选择的目录
        self.last_dir = self.settings.value("last_dir", ".", str)
        # language code
        self.languagename = list(langlist.keys())
        self.app_mode = 'biaozhun'
        # 上次缓存
        self.get_setting()

        self.splitter.setSizes([1000, 360])

        # start
        self.startbtn.clicked.connect(self.check_start)
        # 隐藏倒计时
        self.stop_djs.clicked.connect(self.reset_timeid)
        self.stop_djs.hide()
        # subtitle btn
        self.continue_compos.hide()
        self.continue_compos.clicked.connect(self.set_djs_timeout)

        # select and save
        self.btn_get_video.clicked.connect(self.get_mp4)
        self.source_mp4.setAcceptDrops(True)
        self.btn_save_dir.clicked.connect(self.get_save_dir)
        self.target_dir.setAcceptDrops(True)
        self.proxy.setText(config.proxy)
        self.open_targetdir.clicked.connect(lambda: self.open_dir(self.target_dir.text()))

        # language
        self.source_language.addItems(self.languagename)
        self.source_language.setCurrentIndex(2)

        # 目标语言改变时，如果当前tts是 edgeTTS，则根据目标语言去修改显示的角色
        self.target_language.addItems(["-"] + self.languagename)
        # 目标语言改变
        self.target_language.currentTextChanged.connect(self.set_voice_role)
        self.voice_role.currentTextChanged.connect(self.show_listen_btn)

        self.listen_btn.hide()
        self.listen_btn.clicked.connect(self.listen_voice_fun)

        #  translation type
        self.translate_type.addItems(["google", "baidu", "chatGPT", "tencent", "DeepL", "DeepLX", "baidu(noKey)"])
        self.translate_type.setCurrentText(self.cfg['translate_type'])
        self.translate_type.currentTextChanged.connect(self.set_translate_type)

        #         model
        self.whisper_type.addItems([transobj['whisper_type_all'], transobj['whisper_type_split']])
        self.whisper_type.currentIndexChanged.connect(self.check_whisper_type)
        if self.cfg['whisper_type']:
            self.whisper_type.setCurrentIndex(0 if self.cfg['whisper_type'] == 'all' else 1)
        self.whisper_model.addItems(['base', 'small', 'medium', 'large', 'large-v3'])
        self.whisper_model.setCurrentText(self.cfg['whisper_model'])
        self.whisper_model.currentTextChanged.connect(self.check_whisper_model)

        #
        self.voice_rate.setText(self.cfg['voice_rate'])
        self.voice_rate.textChanged.connect(self.voice_rate_changed)
        self.voice_silence.setText(self.cfg['voice_silence'])

        self.voice_autorate.stateChanged.connect(
            lambda: self.autorate_changed(self.voice_autorate.isChecked(), "voice"))
        self.video_autorate.stateChanged.connect(
            lambda: self.autorate_changed(self.video_autorate.isChecked(), "video"))

        # 设置角色类型，如果当前是OPENTTS或 coquiTTS则设置，如果是edgeTTS，则为No
        if self.cfg['tts_type'] == 'edgeTTS':
            self.voice_role.addItems(['No'])
        elif self.cfg['tts_type'] == 'openaiTTS':
            self.voice_role.addItems(['No'] + self.cfg['openaitts_role'].split(','))
        elif self.cfg['tts_type'] == 'coquiTTS':
            self.voice_role.addItems(['No'] + self.cfg['coquitts_role'].split(','))
        # 设置 tts_type
        self.tts_type.addItems(self.cfg['tts_type_list'])
        self.tts_type.setCurrentText(self.cfg['tts_type'])
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.tts_type_change)
        self.enable_cuda.stateChanged.connect(self.check_cuda)
        self.enable_cuda.setChecked(self.cfg['enable_cuda'])

        # subtitle 0 no 1=embed subtitle 2=softsubtitle
        self.subtitle_type.addItems([transobj['nosubtitle'], transobj['embedsubtitle'], transobj['softsubtitle']])
        self.subtitle_type.setCurrentIndex(self.cfg['subtitle_type'])

        # 字幕编辑
        self.subtitle_area = TextGetdir(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.subtitle_area.setSizePolicy(sizePolicy)
        self.subtitle_area.setMinimumSize(300, 0)
        self.subtitle_area.setPlaceholderText(transobj['subtitle_tips'])

        self.subtitle_layout.insertWidget(0, self.subtitle_area)
        self.import_sub = QPushButton("导入字幕")
        self.import_sub.setMinimumSize(80, 35)
        self.import_sub.clicked.connect(self.import_sub_fun)
        self.listen_peiyin = QPushButton("试听配音")
        self.listen_peiyin.setMinimumSize(0, 35)
        self.listen_peiyin.setDisabled(True)
        self.listen_peiyin.setToolTip("先启动任务，待字幕翻译完成后可试听,配音速度、自动加速实时修改生效")
        self.listen_peiyin.clicked.connect(self.shiting_peiyin)
        self.layout_sub_bottom.insertWidget(0, self.import_sub)
        self.layout_sub_bottom.insertWidget(1, self.listen_peiyin)

        # menubar
        self.actionbaidu_key.triggered.connect(self.set_baidu_key)
        self.actiontencent_key.triggered.connect(self.set_tencent_key)
        self.actionchatgpt_key.triggered.connect(self.set_chatgpt_key)
        self.actiondeepL_key.triggered.connect(self.set_deepL_key)
        self.actiondeepLX_address.triggered.connect(self.set_deepLX_address)
        self.action_vlc.triggered.connect(lambda: self.open_url('vlc'))
        self.action_ffmpeg.triggered.connect(lambda: self.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.open_url('discord'))
        self.action_website.triggered.connect(lambda: self.open_url('website'))
        self.action_issue.triggered.connect(lambda: self.open_url('issue'))
        self.action_tool.triggered.connect(self.open_toolbox)
        self.action_about.triggered.connect(self.about)
        self.action_clone.triggered.connect(lambda: show_popup(transobj['yinsekaifazhong'], transobj['yinsekelong']))

        # 设置QAction的大小
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # 设置QToolBar的大小，影响其中的QAction的大小
        self.toolBar.setIconSize(QSize(100, 45))  # 设置图标大小
        self.action_biaozhun.triggered.connect(self.set_biaozhun)
        self.action_tiquzimu.triggered.connect(self.set_tiquzimu)
        self.action_tiquzimu_no.triggered.connect(self.set_tiquzimu_no)
        self.action_zimu_video.triggered.connect(self.set_zimu_video)
        self.action_zimu_peiyin.triggered.connect(self.set_zimu_peiyin)
        self.action_yuyinshibie.triggered.connect(lambda: self.open_toolbox(2))
        self.action_yuyinhecheng.triggered.connect(lambda: self.open_toolbox(3))
        self.action_yinshipinfenli.triggered.connect(lambda: self.open_toolbox(0))
        self.action_yingyinhebing.triggered.connect(lambda: self.open_toolbox(1))
        self.action_geshi.triggered.connect(lambda: self.open_toolbox(4))
        self.action_hun.triggered.connect(lambda: self.open_toolbox(5))
        self.action_fanyi.triggered.connect(lambda: self.open_toolbox(6))

        # 底部状态栏
        self.statusLabel = QLabel(transobj['modelpathis'] + " /models")
        self.statusLabel.setStyleSheet("color:#00a67d")
        self.statusBar.addWidget(self.statusLabel)

        rightbottom = QPushButton(" 捐助该软件！ ")
        rightbottom.setToolTip("如果有你的捐助，软件将能得到持续维护，点击查看")
        rightbottom.clicked.connect(self.about)

        usetype = QPushButton(" 快速使用技巧 ")
        usetype.setToolTip("查看常见使用技巧")
        usetype.clicked.connect(self.usetype)
        container = QToolBar()
        container.addWidget(rightbottom)
        container.addWidget(usetype)
        self.statusBar.addPermanentWidget(container)
        #     日志
        self.task_logs = LogsWorker(self)
        self.task_logs.post_logs.connect(self.update_data)
        self.task_logs.start()

        self.check_update = CheckUpdateWorker(self)
        self.check_update.start()

    def check_cuda(self, state):
        res = state
        # 选中如果无效，则取消
        if state and not torch.cuda.is_available():
            QMessageBox.critical(self, '你的设备不满足CUDA加速要求',
                                 '请确认是NVIDIA显卡，并已安装 CUDA 11.8，如未安装，请去 developer.nvidia.com/cuda-downloads 安装匹配当前系统的 cuda 11.8,然后重启软件')
            self.enable_cuda.setChecked(False)
            self.enable_cuda.setDisabled(True)
            res = False
        config.cuda = res
        if config.cuda:
            os.environ['CUDA_OK'] = "yes"
        elif os.environ.get('CUDA_OK'):
            os.environ.pop('CUDA_OK')

    # 配音速度改变时，更改全局
    def voice_rate_changed(self, text):
        text = int(str(text).replace('+', '').replace('%', ''))
        text = f'+{text}%' if text >= 0 else f'-{text}%'
        config.voice_rate = text

    # 字幕下方试听配音
    def shiting_peiyin(self):
        if not self.task:
            return
        if self.voice_role.currentText() == 'No':
            return QMessageBox.critical(self, "出错了", "未选择角色，不可试听")
        if self.shitingobj:
            self.shitingobj.stop = True
            self.shitingobj = None
            self.listen_peiyin.setText('重听中')
        else:
            self.listen_peiyin.setText('试听中/点击重听')
        obj = {
            "sub_name": self.task.video.targetdir_target_sub,
            "noextname": self.task.video.noextname,
            "cache_folder": self.task.video.cache_folder,
            "source_wav": self.task.video.targetdir_source_sub,
            "voice_role": config.voice_role,
            "voice_autorate": config.voice_autorate,
            "voice_rate": config.voice_rate,
            "tts_type": self.task.video.obj['tts_type'],
        }
        txt=self.subtitle_area.toPlainText().strip()
        if not txt:
            return QMessageBox.critical(self,"出错了",'无字幕内容，不可试听')
        with open(self.task.video.targetdir_target_sub,'w',encoding='utf-8') as f:
            f.write(txt)
        self.shitingobj = Shiting(obj, self)
        self.shitingobj.start()

    # 启用标准模式
    def set_biaozhun(self):
        self.app_mode = 'biaozhun'
        self.show_tips.setText("")
        self.startbtn.setText("开始处理")
        self.action_tiquzimu_no.setChecked(False)
        self.action_biaozhun.setChecked(True)
        self.action_tiquzimu.setChecked(False)
        self.action_zimu_video.setChecked(False)
        self.action_zimu_peiyin.setChecked(False)

        # 选择视频
        self.hide_show_element(self.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.layout_target_dir, True)
        self.open_targetdir.show()

        # 翻译渠道
        self.hide_show_element(self.layout_translate_type, True)
        # 代理
        self.hide_show_element(self.layout_proxy, True)
        # 原始语言
        self.hide_show_element(self.layout_source_language, True)
        # 目标语言
        self.hide_show_element(self.layout_target_language, True)
        # tts类型
        self.hide_show_element(self.layout_tts_type, True)
        # 配音角色
        self.hide_show_element(self.layout_voice_role, True)
        # 试听按钮
        self.hide_show_element(self.listen_layout, False)
        # 语音模型
        self.hide_show_element(self.layout_whisper_model, True)
        # 字幕类型
        self.hide_show_element(self.layout_subtitle_type, True)

        # 配音语速
        self.hide_show_element(self.layout_voice_rate, True)
        # 静音片段
        self.hide_show_element(self.layout_voice_silence, True)
        # 配音自动加速
        self.voice_autorate.show()
        # 视频自动降速
        self.video_autorate.show()
        # cuda
        self.enable_cuda.show()

    # 视频提取字幕并翻译，无需配音
    def set_tiquzimu(self):
        self.app_mode = 'tiqu'
        self.show_tips.setText("原始语言设为视频发音语言，目标语言设为想翻译为的语言")
        self.startbtn.setText("开始提取和翻译")
        self.action_tiquzimu_no.setChecked(False)
        self.action_tiquzimu.setChecked(True)
        self.action_biaozhun.setChecked(False)
        self.action_zimu_video.setChecked(False)
        self.action_zimu_peiyin.setChecked(False)

        # 选择视频
        self.hide_show_element(self.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.layout_target_dir, True)
        self.open_targetdir.show()

        # 翻译渠道
        self.hide_show_element(self.layout_translate_type, True)
        # 代理
        self.hide_show_element(self.layout_proxy, True)
        # 原始语言
        self.hide_show_element(self.layout_source_language, True)
        # 目标语言
        self.hide_show_element(self.layout_target_language, True)
        # tts类型
        self.hide_show_element(self.layout_tts_type, False)
        # 配音角色
        self.hide_show_element(self.layout_voice_role, False)
        # self.voice_role.setCurrentText('No')
        # 试听按钮
        self.hide_show_element(self.listen_layout, False)
        # 语音模型
        self.hide_show_element(self.layout_whisper_model, True)
        # 字幕类型
        self.hide_show_element(self.layout_subtitle_type, False)
        # self.subtitle_type.setCurrentIndex(0)

        # 配音语速
        self.hide_show_element(self.layout_voice_rate, False)
        # self.voice_rate.setText('+0%')
        # 静音片段
        self.hide_show_element(self.layout_voice_silence, False)
        # self.voice_silence.setText('500')
        # 配音自动加速
        self.voice_autorate.hide()
        self.voice_autorate.setChecked(False)
        # 视频自动降速
        self.video_autorate.hide()
        self.video_autorate.setChecked(False)
        # cuda
        self.enable_cuda.show()

    # 从视频提取字幕，不翻译
    # 只显示 选择视频、保存目标、原始语言、语音模型，其他不需要
    def set_tiquzimu_no(self):
        self.app_mode = 'tiqu_no'
        self.show_tips.setText("原始语言设为视频发音语言")
        self.startbtn.setText("开始提取字幕")
        self.action_tiquzimu.setChecked(False)
        self.action_tiquzimu_no.setChecked(True)
        self.action_biaozhun.setChecked(False)
        self.action_zimu_video.setChecked(False)
        self.action_zimu_peiyin.setChecked(False)

        # 选择视频
        self.hide_show_element(self.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.layout_target_dir, True)
        self.open_targetdir.show()

        # 翻译渠道
        self.hide_show_element(self.layout_translate_type, False)
        # 代理
        self.hide_show_element(self.layout_proxy, False)
        # self.proxy.setText('')
        # 原始语言
        self.hide_show_element(self.layout_source_language, True)

        # 目标语言
        self.hide_show_element(self.layout_target_language, False)
        # self.target_language.setCurrentText('-')
        # tts类型
        self.hide_show_element(self.layout_tts_type, False)

        # 配音角色
        self.hide_show_element(self.layout_voice_role, False)
        # self.voice_role.setCurrentText('No')
        # 试听按钮
        self.hide_show_element(self.listen_layout, False)
        # 语音模型
        self.hide_show_element(self.layout_whisper_model, True)
        # 字幕类型
        self.hide_show_element(self.layout_subtitle_type, False)
        # self.subtitle_type.setCurrentIndex(0)

        # 配音语速
        self.hide_show_element(self.layout_voice_rate, False)
        # self.voice_rate.setText('+0%')
        # 静音片段
        self.hide_show_element(self.layout_voice_silence, False)
        # self.voice_silence.setText('500')
        # 配音自动加速
        self.voice_autorate.hide()
        self.voice_autorate.setChecked(False)
        # 视频自动降速
        self.video_autorate.hide()
        self.video_autorate.setChecked(False)
        # cuda
        self.enable_cuda.show()

    # 启用字幕合并模式, 仅显示 选择视频、保存目录、字幕类型、自动视频降速 cuda
    # 不配音、不识别，
    def set_zimu_video(self):
        self.app_mode = 'hebing'
        self.show_tips.setText("选择要合并的视频，将字幕srt文件拖拽到右侧字幕区")
        self.startbtn.setText("开始合并")
        self.action_tiquzimu_no.setChecked(False)
        self.action_biaozhun.setChecked(False)
        self.action_tiquzimu.setChecked(False)
        self.action_zimu_video.setChecked(True)
        self.action_zimu_peiyin.setChecked(False)

        # 选择视频
        self.hide_show_element(self.layout_source_mp4, True)
        # 保存目标
        self.hide_show_element(self.layout_target_dir, True)
        self.open_targetdir.show()

        # 翻译渠道
        self.hide_show_element(self.layout_translate_type, False)
        # 代理
        self.hide_show_element(self.layout_proxy, False)
        # 原始语言
        self.hide_show_element(self.layout_source_language, False)
        # 目标语言
        self.hide_show_element(self.layout_target_language, False)
        # tts类型
        self.hide_show_element(self.layout_tts_type, False)
        # 配音角色
        self.hide_show_element(self.layout_voice_role, False)
        # 试听按钮
        self.hide_show_element(self.listen_layout, False)
        # 语音模型
        self.hide_show_element(self.layout_whisper_model, False)
        # 字幕类型
        self.hide_show_element(self.layout_subtitle_type, True)

        # 配音语速
        self.hide_show_element(self.layout_voice_rate, False)
        # 静音片段
        self.hide_show_element(self.layout_voice_silence, False)

        # 配音自动加速
        self.voice_autorate.hide()
        self.voice_autorate.setChecked(False)
        # 视频自动降速
        self.video_autorate.show()
        self.video_autorate.setChecked(False)
        # cuda
        self.enable_cuda.show()

    # 仅仅对已有字幕配音，显示目标语言、tts相关，自动加速相关，
    # 不翻译不识别
    def set_zimu_peiyin(self):
        self.show_tips.setText("请将目标语言设为字幕所用语言，并选择配音角色")
        self.startbtn.setText("开始配音")
        self.action_tiquzimu_no.setChecked(False)
        self.action_biaozhun.setChecked(False)
        self.action_tiquzimu.setChecked(False)
        self.action_zimu_video.setChecked(False)
        self.action_zimu_peiyin.setChecked(True)
        self.app_mode = 'peiyin'
        # 选择视频
        self.hide_show_element(self.layout_source_mp4, False)
        # 保存目标
        self.hide_show_element(self.layout_target_dir, True)
        self.open_targetdir.show()

        # 翻译渠道
        self.hide_show_element(self.layout_translate_type, False)
        # 代理 openaitts
        self.hide_show_element(self.layout_proxy, True)

        # 原始语言
        self.hide_show_element(self.layout_source_language, False)
        # 目标语言
        self.hide_show_element(self.layout_target_language, True)
        # tts类型
        self.hide_show_element(self.layout_tts_type, True)
        # 配音角色
        self.hide_show_element(self.layout_voice_role, True)
        # 试听按钮
        self.hide_show_element(self.listen_layout, True)
        # 语音模型
        self.hide_show_element(self.layout_whisper_model, False)
        # 字幕类型
        self.hide_show_element(self.layout_subtitle_type, False)

        # 配音语速
        self.hide_show_element(self.layout_voice_rate, True)
        # 静音片段
        self.hide_show_element(self.layout_voice_silence, False)
        # 配音自动加速
        self.voice_autorate.show()
        # 视频自动降速
        self.video_autorate.hide()
        self.video_autorate.setChecked(False)
        # cuda
        self.enable_cuda.show()

    # 使用指南
    def usetype(self):
        string = """
【标准模式】 
根据需要设置各个选项，自由配置组合，实现翻译和配音、合并等

【提取字幕不翻译】 
选择视频文件，选择视频源语言，则从视频识别出文字并自动导出字幕文件到目标文件夹

【提取字幕并翻译】 
选择视频文件，选择视频源语言，设置想翻译到的目标语言，则从视频识别出文字并翻译为目标语言，然后导出双语字幕文件到目标文件夹

【字幕和视频合并】 
选择视频，然后将已有的字幕文件拖拽到右侧字幕区，将源语言和目标语言都设为字幕所用语言、然后选择配音类型和角色，开始执行

【为字幕创建配音】 
将本地的字幕文件拖拽到右侧字幕编辑器，然后选择目标语言、配音类型和角色，将生成配音后的音频文件到目标文件夹

【音视频识别文字】
将视频或音频拖拽到识别窗口，将识别出文字并导出为srt字幕格式

【将文字合成语音】
将一段文字或者字幕，使用指定的配音角色生成配音

【从视频分离音频】
将视频文件分离为音频文件和无声视频

【音视频字幕合并】
音频文件、视频文件、字幕文件合并为一个视频文件

【音视频格式转换】
各种格式之间的相互转换

        """
        QMessageBox.information(self, "常见使用方式", string)

    # 关于页面
    def about(self):
        self.infofrom = InfoForm()
        self.infofrom.show()

    # voice_autorate video_autorate 变化
    def autorate_changed(self, state, name):
        if state:
            if name == 'voice':
                self.video_autorate.setChecked(False)
            else:
                self.voice_autorate.setChecked(False)
        if name == 'voice':
            config.voice_autorate = state
        else:
            config.video_autorate = state

    def open_dir(self, dirname=None):
        if not dirname:
            return
        if not os.path.isdir(dirname):
            dirname = os.path.dirname(dirname)
        QDesktopServices.openUrl(QUrl(f"file:{dirname}"))

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

    # 开启执行后，禁用按钮，停止或结束后，启用按钮
    def disabled_widget(self, type):
        self.import_sub.setDisabled(type)
        self.btn_get_video.setDisabled(type)
        self.source_mp4.setDisabled(type)
        self.btn_save_dir.setDisabled(type)
        self.target_dir.setDisabled(type)
        self.translate_type.setDisabled(type)
        self.proxy.setDisabled(type)
        self.source_language.setDisabled(type)
        self.target_language.setDisabled(type)
        self.tts_type.setDisabled(type)
        self.whisper_model.setDisabled(type)
        self.whisper_type.setDisabled(type)
        self.subtitle_type.setDisabled(type)
        self.voice_silence.setDisabled(type)
        self.video_autorate.setDisabled(type)
        self.enable_cuda.setDisabled(type)

    def closeEvent(self, event):
        # 在关闭窗口前执行的操作
        if self.toolboxobj is not None:
            self.toolboxobj.close()
        if config.current_status == 'ing':
            config.current_status = 'end'
            msg = QMessageBox()
            msg.setWindowTitle(transobj['exit'])
            msg.setWindowIcon(QIcon(config.rootdir + "/icon.ico"))
            msg.setText(transobj['waitclear'])
            msg.addButton(transobj['queding'], QMessageBox.AcceptRole)
            msg.setIcon(QMessageBox.Information)
            msg.exec_()  # 显示消息框
            event.accept()
        else:
            event.accept()

    def get_setting(self):
        # 从缓存获取默认配置
        config.baidu_appid = self.settings.value("baidu_appid", "")
        config.baidu_miyue = self.settings.value("baidu_miyue", "")
        config.deepl_authkey = self.settings.value("deepl_authkey", "")
        config.deeplx_address = self.settings.value("deeplx_address", "")
        config.chatgpt_api = self.settings.value("chatgpt_api", "")
        config.chatgpt_key = self.settings.value("chatgpt_key", "")
        config.tencent_SecretId = self.settings.value("tencent_SecretId", "")
        config.tencent_SecretKey = self.settings.value("tencent_SecretKey", "")

        os.environ['OPENAI_API_KEY'] = config.chatgpt_key
        config.chatgpt_model = self.settings.value("chatgpt_model", self.cfg['chatgpt_model'])
        self.cfg['translate_type'] = self.settings.value("translate_type", self.cfg['translate_type'])
        self.cfg['subtitle_type'] = self.settings.value("subtitle_type", self.cfg['subtitle_type'], int)
        config.proxy = self.settings.value("proxy", "", str)
        self.cfg['voice_rate'] = self.settings.value("voice_rate", self.cfg['voice_rate'], str)
        self.cfg['voice_silence'] = self.settings.value("voice_silence", self.cfg['voice_silence'], str)
        self.cfg['enable_cuda'] = False if not config.cuda else self.settings.value("enable_cuda", False, bool)
        self.cfg['whisper_model'] = self.settings.value("whisper_model", self.cfg['whisper_model'], str)
        self.cfg['whisper_type'] = self.settings.value("whisper_type", self.cfg['whisper_type'], str)
        self.cfg['tts_type'] = self.settings.value("tts_type", self.cfg['tts_type'], str)
        if not self.cfg['tts_type']:
            self.cfg['tts_type'] = 'edgeTTS'

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

    # 工具箱
    def open_toolbox(self, index=0):
        try:
            import box
            if self.toolboxobj is None:
                self.toolboxobj = box.MainWindow()
            self.toolboxobj.show()
            self.toolboxobj.tabWidget.setCurrentIndex(index)
            self.toolboxobj.raise_()
        except Exception as e:
            self.toolboxobj = None
            QMessageBox.critical(self, "出错了", "你可能需要先安装VLC解码器，" + str(e))
            logger.error("vlc" + str(e))

    # 将倒计时设为立即超时
    def set_djs_timeout(self):
        config.task_countdown = 0
        self.continue_compos.setText("继续执行中")
        self.continue_compos.setDisabled(True)
        self.stop_djs.hide()
        self.process.clear()
        if self.shitingobj:
            self.shitingobj.stop = True

    # 手动点击停止自动合并倒计时
    def reset_timeid(self):
        self.stop_djs.hide()
        config.task_countdown = 86400
        self.process.moveCursor(QTextCursor.End)
        self.process.insertHtml("<br><strong>倒计时停止，修改后请手动点击“继续执行”按钮</strong><br>")
        self.continue_compos.setDisabled(False)
        self.continue_compos.setText("继续下一步")

    # set deepl key
    def set_deepL_key(self):
        def save():
            key = self.w.deepl_authkey.text()
            self.settings.setValue("deepl_authkey", key)
            config.deepl_authkey = key
            self.w.close()

        self.w = DeepLForm()
        if config.deepl_authkey:
            self.w.deepl_authkey.setText(config.deepl_authkey)
        self.w.set_deepl.clicked.connect(save)
        self.w.show()

    def set_deepLX_address(self):
        def save():
            key = self.w.deeplx_address.text()
            self.settings.setValue("deeplx_address", key)
            config.deeplx_address = key
            self.w.close()

        self.w = DeepLXForm()
        if config.deeplx_address:
            self.w.deeplx_address.setText(config.deeplx_address)
        self.w.set_deeplx.clicked.connect(save)
        self.w.show()

    # set baidu
    def set_baidu_key(self):
        def save_baidu():
            appid = self.w.baidu_appid.text()
            miyue = self.w.baidu_miyue.text()
            self.settings.setValue("baidu_appid", appid)
            self.settings.setValue("baidu_miyue", miyue)
            config.baidu_appid = appid
            config.baidu_miyue = miyue
            self.w.close()

        self.w = BaiduForm()
        if config.baidu_appid:
            self.w.baidu_appid.setText(config.baidu_appid)
        if config.baidu_miyue:
            self.w.baidu_miyue.setText(config.baidu_miyue)
        self.w.set_badiu.clicked.connect(save_baidu)
        self.w.show()

    def set_tencent_key(self):
        def save():
            SecretId = self.w.tencent_SecretId.text()
            SecretKey = self.w.tencent_SecretKey.text()
            self.settings.setValue("tencent_SecretId", SecretId)
            self.settings.setValue("tencent_SecretKey", SecretKey)
            config.tencent_SecretId = SecretId
            config.tencent_SecretKey = SecretKey
            self.w.close()

        self.w = TencentForm()
        if config.tencent_SecretId:
            self.w.tencent_SecretId.setText(config.tencent_SecretId)
        if config.tencent_SecretKey:
            self.w.tencent_SecretKey.setText(config.tencent_SecretKey)
        self.w.set_tencent.clicked.connect(save)
        self.w.show()

    # set chatgpt
    def set_chatgpt_key(self):
        def save_chatgpt():
            key = self.w.chatgpt_key.text()
            api = self.w.chatgpt_api.text()
            model = self.w.chatgpt_model.currentText()
            template = self.w.chatgpt_template.toPlainText()
            self.settings.setValue("chatgpt_key", key)
            self.settings.setValue("chatgpt_api", api)

            self.settings.setValue("chatgpt_model", model)
            self.settings.setValue("chatgpt_template", template)

            os.environ['OPENAI_API_KEY'] = key
            config.chatgpt_key = key
            config.chatgpt_api = api
            config.chatgpt_model = model
            config.chatgpt_template = template
            self.w.close()

        self.w = ChatgptForm()
        if config.chatgpt_key:
            self.w.chatgpt_key.setText(config.chatgpt_key)
        if config.chatgpt_api:
            self.w.chatgpt_api.setText(config.chatgpt_api)
        if config.chatgpt_model:
            self.w.chatgpt_model.setCurrentText(config.chatgpt_model)
        if config.chatgpt_template:
            self.w.chatgpt_template.setPlainText(config.chatgpt_template)
        self.w.set_chatgpt.clicked.connect(save_chatgpt)
        self.w.show()

    # 翻译渠道变化时，检测条件
    def set_translate_type(self, name):
        try:
            if name == "baidu" and not config.baidu_appid:
                QMessageBox.critical(self, transobj['anerror'], transobj['baidukeymust'])
                return
            if name == "chatGPT" and not config.chatgpt_key:
                QMessageBox.critical(self, transobj['anerror'], transobj['chatgptkeymust'])
                return
            if name == "DeepL" and not config.deepl_authkey:
                QMessageBox.critical(self, transobj['anerror'], transobj['setdeepl_authkey'])
                return
            if name == "DeepLX" and not config.deeplx_address:
                QMessageBox.critical(self, transobj['anerror'], transobj['setdeeplx_address'])
                return
            self.cfg['translate_type'] = name
        except Exception as e:
            QMessageBox.critical(self, transobj['anerror'], str(e))

    def check_whisper_type(self, index):
        if index == 0:
            self.cfg['whisper_type'] = 'all'
        else:
            self.cfg['whisper_type'] = 'split'

    # check model is exits
    def check_whisper_model(self, name):
        if not os.path.exists(config.rootdir + f"/models/{name}.pt"):
            self.statusLabel.setText(transobj['downloadmodel'] + f" ./models/{name}.pt")
            QMessageBox.critical(self, transobj['downloadmodel'], f"./models/{name}.pt")
        else:
            self.statusLabel.setText(transobj['modelpathis'] + f" ./models/{name}.pt")

    # 更新执行状态
    def update_status(self, type):
        config.current_status = type
        self.continue_compos.hide()
        self.stop_djs.hide()
        if type != 'ing':
            # 结束或停止
            self.startbtn.setText(transobj[type])
            # 启用
            self.disabled_widget(False)
            if type == 'end':
                # 清理字幕
                self.subtitle_area.clear()
                # 清理输入
            self.statusLabel.setText("本次任务结束")
            self.source_mp4.clear()
            self.target_dir.clear()
            if self.task:
                self.task.requestInterruption()
                self.task.quit()
        else:
            # 重设为开始状态
            self.disabled_widget(True)
            self.startbtn.setText(transobj['running'])
            self.statusLabel.setText("开始处理...")

    # tts类型改变
    def tts_type_change(self, type):
        self.cfg['tts_type'] = type
        # 如果任务是在进行中，则更改
        if type == "openaiTTS":
            self.voice_role.clear()
            self.voice_role.addItems(['No'] + self.cfg['openaitts_role'].split(','))
        elif type == 'coquiTTS':
            self.voice_role.addItems(['No'] + self.cfg['coquitts_role'].split(','))
        elif type == 'edgeTTS':
            self.set_voice_role(self.target_language.currentText())

    # 试听配音
    def listen_voice_fun(self):
        currentlang = self.target_language.currentText()
        if currentlang in ["English", "英语"]:
            text = self.cfg['listen_text_en']
            lang = "en"
        elif currentlang in ["中文简", "中文繁", "Simplified_Chinese", "Traditional_Chinese"]:
            text = self.cfg['listen_text_cn']
            lang = "zh"
        else:
            return
        role = self.voice_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(self, transobj['anerror'], transobj['mustberole'])
        voice_dir = os.environ.get('APPDATA') or os.environ.get('appdata')
        if not voice_dir or not os.path.exists(voice_dir):
            voice_dir = config.rootdir + "/tmp/voice_tmp"
        else:
            voice_dir = voice_dir.replace('\\', '/') + "/pyvideotrans"
        if not os.path.exists(voice_dir):
            os.makedirs(voice_dir)
        voice_file = f"{voice_dir}/{self.cfg['tts_type']}-{lang}-{role}.mp3"
        obj = {
            "text": text,
            "rate": "+0%",
            "role": role,
            "voice_file": voice_file,
            "tts_type": self.cfg['tts_type'],
        }
        from videotrans.task.play_audio import PlayMp3
        t = PlayMp3(obj, self)
        t.start()

    # 显示试听按钮
    def show_listen_btn(self, role):
        if config.current_status == 'ing' and config.voice_role != 'No' and role == 'No':
            QMessageBox.critical(self, transobj['anerror'], '运行中，不可改为无配音角色')
            self.voice_role.setCurrentText(config.voice_role)
            return
        config.voice_role = role
        t = self.target_language.currentText()
        if role != 'No' and t in ["中文简", "中文繁", "英语", "Simplified_Chinese", "Traditional_Chinese", "English"]:
            self.listen_btn.show()
            self.listen_btn.setDisabled(False)
        else:
            self.listen_btn.hide()
            self.listen_btn.setDisabled(True)

    # 目标语言改变时设置配音角色
    def set_voice_role(self, t):
        role = self.voice_role.currentText()
        # 如果tts类型是 openaiTTS，则角色不变
        # 是edgeTTS时需要改变
        if self.cfg['tts_type'] != 'edgeTTS':
            if role != 'No' and t in ["中文简", "中文繁", "英语", "Simplified_Chinese", "Traditional_Chinese", "English"]:
                self.listen_btn.show()
                self.listen_btn.setDisabled(False)
            else:
                self.listen_btn.hide()
                self.listen_btn.setDisabled(True)
            return
        self.listen_btn.hide()
        self.voice_role.clear()
        if t == '-':
            self.voice_role.addItems(['No'])
            return
        if not config.edgeTTS_rolelist:
            self.target_language.setCurrentText('-')
            QMessageBox.critical(self, transobj['anerror'], transobj['waitrole'])
            return
        try:
            vt = langlist[t][0].split('-')[0]
            if vt not in config.edgeTTS_rolelist:
                self.voice_role.addItems(['No'])
                return
            if len(config.edgeTTS_rolelist[vt]) < 2:
                self.target_language.setCurrentText('-')
                QMessageBox.critical(self, transobj['anerror'], transobj['waitrole'])
                return
            self.voice_role.addItems(config.edgeTTS_rolelist[vt])
        except:
            self.voice_role.addItems([it for item in list(config.edgeTTS_rolelist.values()) for it in item])

    # get video filter mp4
    def get_mp4(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, transobj['selectmp4'], self.last_dir,
                                                 "Video files(*.mp4 *.avi *.mov *.mpg *.mkv)")
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/')

        if len(fnames) > 0:
            self.source_mp4.setText(fnames[0])
            self.settings.setValue("last_dir", os.path.dirname(fnames[0]))
            config.queue_mp4 = fnames

    # 从本地导入字幕文件
    def import_sub_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self, transobj['selectmp4'], self.last_dir,
                                               "Srt files(*.srt *.txt)")
        if fname:
            with open(fname, 'r', encoding='utf-8') as f:
                self.subtitle_area.insertPlainText(f.read().strip())

    # 保存目录
    def get_save_dir(self):
        dirname = QFileDialog.getExistingDirectory(self, transobj['selectsavedir'], self.last_dir)
        dirname = dirname.replace('\\', '/')
        self.target_dir.setText(dirname)

    # 检测开始状态并启动
    def check_start(self):
        if config.current_status == 'ing':
            question = show_popup(transobj['exit'], transobj['confirmstop'])
            if question == QMessageBox.AcceptRole:
                self.update_status('stop')
                return
        # 清理日志
        self.process.clear()
        # 选择视频
        self.cfg['source_mp4'] = self.source_mp4.text().strip().replace('\\', '/')
        target_dir = self.target_dir.text().strip().lower().replace('\\', '/')
        # 目标文件夹
        if target_dir:
            self.cfg['target_dir'] = target_dir
        elif self.cfg['source_mp4']:
            self.cfg['target_dir'] = os.path.dirname(self.cfg['source_mp4']) + "/_video_out"
        self.target_dir.setText(self.cfg['target_dir'])

        # 代理
        config.proxy = self.proxy.text().strip()
        if config.proxy:
            # 设置代理
            set_proxy(config.proxy)
        else:
            # 删除代理
            set_proxy('del')

        # 原始语言
        self.cfg['source_language'] = langlist[self.source_language.currentText()][0]
        # 目标语言
        target_language = self.target_language.currentText()
        self.cfg['target_language'] = target_language

        # 如果选择了目标语言，再去处理相关
        if '-' != target_language:
            self.cfg['target_language'] = langlist[target_language][0]
            # google language code
            if self.cfg['translate_type'] == 'google':
                self.cfg['target_language'] = langlist[target_language][0]
            elif self.cfg['translate_type'] == 'baidu(noKey)':
                self.cfg['target_language_baidu'] = langlist[target_language][2]
            elif self.cfg['translate_type'] == 'baidu':
                # baidu language code
                self.cfg['target_language_baidu'] = langlist[target_language][2]
                if not config.baidu_appid or not config.baidu_miyue:
                    QMessageBox.critical(self, transobj['anerror'], transobj['baikeymust'])
                    return
            elif self.cfg['translate_type'] == 'tencent':
                #     腾讯翻译
                self.cfg['target_language_tencent'] = langlist[target_language][4]
                if not config.tencent_SecretId or not config.tencent_SecretKey:
                    QMessageBox.critical(self, transobj['anerror'], transobj['tencent_key'])
                    return
            elif self.cfg['translate_type'] == 'chatGPT':
                # chatGPT 翻译
                self.cfg['target_language_chatgpt'] = english_code_bygpt[self.languagename.index(target_language)]
                if not config.chatgpt_key:
                    QMessageBox.critical(self, transobj['anerror'], transobj['chatgptkeymust'])
                    return
            elif self.cfg['translate_type'] == 'DeepL' or self.cfg['translate_type'] == 'DeepLX':
                # DeepL翻译
                if self.cfg['translate_type'] == 'DeepL' and not config.deepl_authkey:
                    QMessageBox.critical(self, transobj['anerror'], transobj['deepl_authkey'])
                    return
                if self.cfg['translate_type'] == 'DeepLX' and not config.deeplx_address:
                    QMessageBox.critical(self, transobj['anerror'], transobj['setdeeplx_address'])
                    return

                self.cfg['target_language_deepl'] = langlist[target_language][3]
                if self.cfg['target_language_deepl'] == 'No':
                    QMessageBox.critical(self, transobj['anerror'], transobj['deepl_nosupport'])
                    return
            # 目标字幕语言
            self.cfg['subtitle_language'] = langlist[self.target_language.currentText()][1]
        # 检测字幕原始语言
        self.cfg['detect_language'] = langlist[self.source_language.currentText()][0]
        # 配音角色
        self.cfg['voice_role'] = self.voice_role.currentText()
        config.voice_role = self.cfg['voice_role']
        # 配音自动加速
        self.cfg['voice_autorate'] = self.voice_autorate.isChecked()
        config.voice_autorate = self.cfg['voice_autorate']
        # 视频自动减速
        self.cfg['video_autorate'] = self.video_autorate.isChecked()
        # 语音模型
        self.cfg['whisper_model'] = self.whisper_model.currentText()
        model = config.rootdir + f"/models/{self.cfg['whisper_model']}.pt"
        # 字幕嵌入类型
        self.cfg['subtitle_type'] = int(self.subtitle_type.currentIndex())

        try:
            voice_rate = int(self.voice_rate.text().strip().replace('+', '').replace('%', ''))
            self.cfg['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"-{voice_rate}%"
        except:
            self.cfg['voice_rate'] = '+0%'
        config.voice_rate = self.cfg['voice_rate']
        try:
            voice_silence = int(self.voice_silence.text().strip())
            self.cfg['voice_silence'] = voice_silence
        except:
            self.cfg['voice_silence'] = '500'
        # 字幕区文字
        txt = self.subtitle_area.toPlainText().strip()

        # 如果是 配音模式
        if self.app_mode == 'peiyin':
            if not txt or self.cfg['voice_role'] in ['-', 'no', 'No']:
                return QMessageBox.critical(self, transobj['anerror'], '配音模式下必须选择配音角色、目标语言、并将本地srt字幕文件拖拽到右侧字幕区')
            # 去掉选择视频，去掉原始语言
            self.cfg['source_mp4'] = ''
            self.cfg['subtitle_type'] = 0
            self.cfg['voice_silence'] = '500'
            self.cfg['video_autorate'] = False
            self.cfg['whisper_model'] = 'base'
            self.cfg['whisper_type'] = 'all'
        # 如果是 合并模式,必须有字幕，有视频，有字幕嵌入类型，允许设置视频减速
        elif self.app_mode == 'hebing':
            if not self.cfg['source_mp4'] or self.cfg['subtitle_type'] < 1 or not txt:
                return QMessageBox.critical(self, transobj['anerror'], '合并模式下，必须选择视频、字幕嵌入类型、并将字幕srt文件拖拽到右侧字幕区')
            self.cfg['target_language'] = '-'
            self.cfg['source_language'] = '-'
            self.cfg['voice_silence'] = '500'
            self.cfg['voice_role'] = 'No'
            self.cfg['voice_rate'] = '+0%'
            self.cfg['voice_autorate'] = False
            self.cfg['whisper_model'] = 'base'
            self.cfg['whisper_type'] = 'all'
        elif self.app_mode == 'tiqu_no' or self.app_mode == 'tiqu':
            self.cfg['subtitle_type'] = 0
            self.cfg['voice_role'] = 'No'
            self.cfg['voice_silence'] = '500'
            self.cfg['voice_rate'] = '+0%'
            self.cfg['voice_autorate'] = False
            self.cfg['video_autorate'] = False
            # 提取字幕模式，必须有视频、有原始语言，语音模型
            if not self.cfg['source_mp4']:
                return QMessageBox.critical(self, transobj['anerror'], '必须选择视频')
            elif not os.path.exists(model) or os.path.getsize(model) < 100:
                QMessageBox.critical(self, transobj['downloadmodel'], f" ./models/{self.cfg['whisper_model']}.pt")
                self.statusLabel.setText(transobj['downloadmodel'] + f" ./models/{self.cfg['whisper_model']}.pt")
                return
            if self.app_mode == 'tiqu' and self.cfg['target_language'] in ['-', 'no', 'No']:
                # 提取字幕并翻译，必须有视频，原始语言，语音模型, 目标语言
                return QMessageBox.critical(self, transobj['anerror'], '提取字幕并翻译模式下，你必须选择要翻译到的目标语言')
            if self.app_mode == 'tiqu_no':
                self.cfg['target_language'] = '-'
        # 综合判断
        if not self.cfg['source_mp4'] and not txt:
            return QMessageBox.critical(self, transobj['anerror'], '视频和字幕不能同时都不存在哦！')

        # tts类型
        if self.cfg['tts_type'] == 'openaiTTS' and not self.cfg['chatgpt_key']:
            QMessageBox.critical(self, transobj['anerror'], transobj['chatgptkeymust'])
            return
        # 如果没有选择目标语言，但是选择了配音角色，无法配音
        if self.cfg['target_language'] == '-' and self.cfg['voice_role'] != 'No':
            return QMessageBox.critical(self, transobj['anerror'], '没有选择目标语言，无法进行配音哦，请选择目标语言或取消配音角色')
        if self.cfg['source_mp4'] and len(config.queue_mp4) < 1:
            config.queue_mp4 = [self.cfg['source_mp4']]
        # 配音模式 无视频
        # 保存设置
        if config.cuda and not torch.cuda.is_available():
            self.cfg['enable_cuda'] = False
            config.cuda = False
            self.enable_cuda.setChecked(False)
            if os.environ.get('CUDA_OK'):
                os.environ.pop('CUDA_OK')
        self.save_setting()
        self.update_status("ing")

        # 已存在字幕
        if txt:
            self.cfg['subtitles']=txt
        config.queue_task = []
        # 存在视频
        if len(config.queue_mp4) > 0:
            while len(config.queue_mp4) > 0:
                self.cfg['source_mp4'] = config.queue_mp4.pop(0)
                config.queue_task.append(copy.deepcopy(self.cfg))
        else:
            # 不存在视频
            config.queue_task.append(copy.deepcopy(self.cfg))

        self.task = Worker(self)
        self.task.start()

    # 存储本地数据
    def save_setting(self):
        self.settings.setValue("target_dir", self.cfg['target_dir'])
        self.settings.setValue("proxy", config.proxy)
        self.settings.setValue("whisper_model", self.cfg['whisper_model'])
        self.settings.setValue("whisper_type", self.cfg['whisper_type'])
        self.settings.setValue("voice_rate", self.cfg['voice_rate'])
        self.settings.setValue("voice_silence", self.cfg['voice_silence'])
        self.settings.setValue("voice_autorate", self.cfg['voice_autorate'])
        self.settings.setValue("video_autorate", self.cfg['video_autorate'])
        self.settings.setValue("subtitle_type", self.cfg['subtitle_type'])
        self.settings.setValue("translate_type", self.cfg['translate_type'])
        self.settings.setValue("enable_cuda", config.cuda)
        self.settings.setValue("tts_type", self.cfg['tts_type'])
        self.settings.setValue("tencent_SecretKey", self.cfg['tencent_SecretKey'])
        self.settings.setValue("tencent_SecretId", self.cfg['tencent_SecretId'])

    # 判断是否存在字幕文件，如果存在，则读出填充字幕区
    def get_sub_toarea(self, noextname):
        if not os.path.exists(f"{config.rootdir}/tmp/{noextname}"):
            os.makedirs(f"{config.rootdir}/tmp/{noextname}", exist_ok=True)
        sub_name = f"{config.rootdir}/tmp/{noextname}/{noextname}.srt"
        c = self.subtitle_area.toPlainText().strip()
        #     判断 如果右侧字幕区无字幕，并且已存在字幕文件，则读取
        if not c and os.path.exists(sub_name) and os.path.getsize(sub_name) > 0:
            with open(sub_name, 'r', encoding="utf-8") as f:
                self.subtitle_area.setPlainText(f.read().strip())
                return True
        # 右侧存在，则创建字幕
        if c:
            with open(sub_name, 'w', encoding="utf-8") as f:
                f.write(self.subtitle_area.toPlainText().strip())
                return True
        return False

    # 更新 UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        # 一行一行插入字幕到字幕编辑区
        if d['type'] == "subtitle":
            self.subtitle_area.moveCursor(QTextCursor.End)
            self.subtitle_area.insertPlainText(d['text'])
        elif d['type']=='set_target_dir':
            self.target_dir.setText(d['text'])
        elif d['type'] == "logs":
            self.process.moveCursor(QTextCursor.End)
            self.process.insertHtml(d['text'])
        elif d['type'] == 'stop' or d['type'] == 'end':
            self.update_status(d['type'])
            self.continue_compos.hide()
            if d['text']:
                self.process.moveCursor(QTextCursor.End)
                self.process.insertHtml(d['text'])
            self.statusLabel.setText('本次任务结束')
        elif d['type']=='succeed':
            #本次任务结束
            self.process.clear()
            self.process.setHtml(d['text'])
            self.subtitle_area.clear()
        elif d['type'] == 'statusbar':
            self.statusLabel.setText(d['text'])
        elif d['type'] == 'error':
            # 出错停止
            self.update_status('stop')
            self.process.moveCursor(QTextCursor.End)
            self.process.insertHtml(d['text'])
            self.continue_compos.hide()
        elif d['type'] == 'edit_subtitle':
            # 显示出合成按钮,等待编辑字幕
            self.continue_compos.show()
            self.continue_compos.setDisabled(False)
            self.continue_compos.setText(d['text'])
            self.stop_djs.show()
            # 允许试听
            if self.task.video.step=='dubbing_before':
                self.listen_peiyin.setDisabled(False)
        elif d['type'] == 'replace_subtitle':
            # 完全替换字幕区
            self.subtitle_area.clear()
            self.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'timeout_djs':
            self.stop_djs.hide()
            self.continue_compos.setDisabled(True)
            self.update_subtitle()
            self.listen_peiyin.setDisabled(True)
            self.listen_peiyin.setText('试听配音')
        elif d['type'] == 'show_djs':
            self.process.clear()
            self.process.insertHtml(d['text'])
        elif d['type'] == 'check_soft_update':
            self.setWindowTitle(self.rawtitle + " -- " + d['text'])

    # update subtitle 手动 点解了 立即合成按钮，或者倒计时结束超时自动执行
    def update_subtitle(self):
        # sub_name = self.task.video.sub_name
        # noextname = self.task.video.noextname
        self.stop_djs.hide()
        self.continue_compos.setDisabled(True)
        # 如果当前是等待翻译阶段，则更新原语言字幕,然后清空字幕区
        txt=self.subtitle_area.toPlainText().strip()
        with open(self.task.video.targetdir_source_sub if self.task.video.step == 'translate_before' else self.task.video.targetdir_target_sub, 'w', encoding='utf-8') as f:
            f.write(txt)
        if self.task.video.step == 'translate_before':
            self.subtitle_area.clear()
        config.task_countdown = 0
        return True
        # try:
        #     if self.get_sub_toarea(noextname):
        #         config.task_countdown = 0
        #         return True
        #     if not self.subtitle_area.toPlainText().strip() and not os.path.exists(sub_name):
        #         set_process("[error]出错了，不存在有效字幕", 'error')
        # except Exception as e:
        #     set_process("[error]:写入字幕出错了：" + str(e), 'error')
        #     logger.error("[error]:写入字幕出错了：" + str(e), 'error')
        # return False


def pygameinit():
    pygame.init()
    pygame.mixer.init()


if __name__ == "__main__":
    threading.Thread(target=get_edge_rolelist).start()
    threading.Thread(target=is_vlc).start()
    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        if not os.path.exists(config.rootdir + "/models"):
            os.mkdir(config.rootdir + "/models")
        if not os.path.exists(config.rootdir + "/tmp"):
            os.makedirs(config.rootdir + "/tmp")
        if shutil.which('ffmpeg') is None:
            QMessageBox.critical(main, transobj['anerror'], transobj["installffmpeg"])
    except Exception as e:
        QMessageBox.critical(main, transobj['anerror'], transobj['createdirerror'])

    # or in new API
    with open(f'{config.rootdir}/videotrans/styles/style.qss', 'r', encoding='utf-8') as f:
        main.setStyleSheet(f.read())
    try:
        import qdarkstyle

        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    except:
        pass

    main.show()
    threading.Thread(target=pygameinit).start()
    sys.exit(app.exec())
