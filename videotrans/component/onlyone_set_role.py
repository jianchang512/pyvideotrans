import json
import sys
from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QCheckBox,
    QComboBox, QPushButton, QScrollArea, QWidget, QGroupBox, QSplitter,QPlainTextEdit,QFrame
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer,QSize

from videotrans.configure.config import logs, tr
from videotrans.util import tools
from videotrans.configure import config
from pathlib import Path
import re

class SpeakerAssignmentDialog(QDialog):
    def __init__(
        self,
        parent=None,
        target_sub: str = None,
        all_voices: Optional[List[str]] = None,
        source_sub: str = None,
        cache_folder=None
    ):
        # 初始化对话框的基本属性
        super().__init__(parent)
        self.target_sub=target_sub
        self.source_srtstring=None
        self.cache_folder=cache_folder
        if source_sub:
            sour_pt=Path(source_sub)
            if sour_pt.as_posix() and not sour_pt.samefile(Path(target_sub)):
                # 存放原始字幕字符串
                self.source_srtstring=sour_pt.read_text(encoding="utf-8")
        
        # 整理后的需配音的字幕
        self.srt_list_dict=tools.get_subtitle_from_srt(self.target_sub)

        # 存储和字幕索引一一对应的说话人信息，
        self.speaker_list_sub=[]
        self.speakers={}
        try:
            _list_sub=[] if not Path(f'{self.cache_folder}/speaker.json').exists() else json.loads(Path(f'{self.cache_folder}/speaker.json').read_text(encoding='utf-8'))
            _set =set(_list_sub) if _list_sub else None
            if _set and len(_set)>1:
                self.speaker_list_sub=_list_sub
                self.speakers={it:None for it in _set}
        except Exception as e:
            logs(f'获取说话人id失败:{e}',level="except")
        print(self.speaker_list_sub)
        print(self.speakers)


        # 存储所有可用发音人列表，如果为空则默认为空列表
        self.all_voices = all_voices or []

        # 设置窗口标题
        self.setWindowTitle(tr("zidonghebingmiaohou"))
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        # 设置窗口最小宽度为 1000px
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        # 设置窗口标志：禁用关闭按钮，启用最大化按钮
        self.setWindowFlags(Qt.WindowTitleHint | Qt.WindowSystemMenuHint  | Qt.WindowMaximizeButtonHint)

        # 创建主布局：水平布局，用于左右分隔
        main_layout = QVBoxLayout(self)
        innerc_layout = QHBoxLayout(self)

        
        # 如果存在原始字幕
        if self.source_srtstring:
            # 左侧区域：占比约 30%，显示原始 SRT 内容
            left_widget = QWidget()  # 创建左侧容器小部件
            left_layout = QVBoxLayout(left_widget)  # 垂直布局
            self.raw_srt_edit = QPlainTextEdit()  # 创建只读文本编辑器
            self.raw_srt_edit.setPlainText(self.source_srtstring)  # 设置原始 SRT 内容
            self.raw_srt_edit.setReadOnly(True)  # 设置为只读
            tiplabel=QLabel(tr("This is the original language subtitles for comparison reference"))
            tiplabel.setStyleSheet("""color:#aaaaaa""")
            left_layout.addWidget(tiplabel)  # 添加到左侧布局
            left_layout.addWidget(self.raw_srt_edit)  # 添加到左侧布局
            innerc_layout.addWidget(left_widget, stretch=2)  # 添加到主布局，伸展因子 3

        # 右侧区域：占比约 70%
        right_widget = QWidget()  # 创建右侧容器小部件
        right_layout = QVBoxLayout(right_widget)  # 垂直布局

        # 添加顶部提示行和按钮
        self.count_down = int(float(config.settings.get('countdown_sec', 1)))
        
        top_layout = QVBoxLayout()
        


        hstop=QHBoxLayout()
        
        self.prompt_label = QLabel(tr("This window will automatically close after the countdown ends"))
        self.prompt_label.setStyleSheet('font-size:14px;text-align:center;color:#aaaaaa')
        self.prompt_label.setAlignment(Qt.AlignCenter)
        hstop.addWidget(self.prompt_label)
        
        self.stop_button = QPushButton(f"{tr('Click here to stop the countdown')}({self.count_down})")
        self.stop_button.setStyleSheet("font-size: 16px;color:#ffff00")
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setMinimumSize(QSize(300, 35))
        self.stop_button.clicked.connect(self.stop_countdown)
        hstop.addWidget(self.stop_button)
        
        top_layout.addLayout(hstop)
        
        prompt_label2 = QLabel(tr("If you need to delete a line of subtitles, just clear the text in that line"))
        prompt_label2.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(prompt_label2) 
        
        main_layout.addLayout(top_layout)

        # 添加顶部查找和替换布局
        search_replace_layout = QHBoxLayout()
        search_replace_layout.addStretch()
        self.search_input = QLineEdit()  # 创建查找目标输入框
        self.search_input.setMaximumWidth(200)
        self.search_input.setPlaceholderText(tr("Original text"))
        search_replace_layout.addWidget(self.search_input)
        self.replace_input = QLineEdit()  # 创建替换为输入框
        self.replace_input.setPlaceholderText(tr("Replace"))
        self.replace_input.setMaximumWidth(200)
        search_replace_layout.addWidget(self.replace_input)
        replace_button = QPushButton(tr("Replace"))  # 创建替换按钮
        replace_button.setMinimumWidth(100)
        replace_button.setMaximumWidth(200)
        replace_button.setCursor(Qt.PointingHandCursor)
        replace_button.clicked.connect(self.replace_text)  # 连接到替换方法
        search_replace_layout.addWidget(replace_button)
        search_replace_layout.addStretch()
        right_layout.addLayout(search_replace_layout)

        # 如果 speakers 不为 None，则右侧分为上下两部分
        if self.speakers:
            # 使用 QSplitter 垂直分隔上部和下部
            splitter = QSplitter(Qt.Vertical)
            splitter.setChildrenCollapsible(False)  # 不可折叠

            # 上部：说话人分配角色区域 (占比 40%)
            upper_widget = self.create_speaker_assignment_area()  # 创建上部区域
            splitter.addWidget(upper_widget)  # 添加到 splitter

            # 下部：字幕按行分配角色区域 (占比 60%)
            lower_widget = self.create_subtitle_assignment_area()  # 创建下部区域
            splitter.addWidget(lower_widget)  # 添加到 splitter

            # 设置 splitter 的伸展因子，上部 4，下部 6
            splitter.setStretchFactor(0, 4)
            splitter.setStretchFactor(1, 6)
            right_layout.addWidget(splitter)  # 添加 splitter 到右侧布局
        else:
            # 如果 speakers 为 None，仅显示字幕按行分配角色区域
            subtitle_area = self.create_subtitle_assignment_area()  # 创建字幕区域
            right_layout.addWidget(subtitle_area)  # 添加到右侧布局


        

        innerc_layout.addWidget(right_widget, stretch=7)  # 添加右侧到主布局，伸展因子 7

        # 底部保存按钮
        save_button = QPushButton(tr("nextstep"))  # 创建保存按钮
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setMinimumSize(QSize(400, 35))
        save_button.clicked.connect(self.save_and_close)  # 连接点击信号到保存方法
        
        cancel_button = QPushButton(tr("Terminate this mission"))  # 创建保存按钮
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMinimumSize(QSize(200, 30))
        cancel_button.clicked.connect(self.cancel_and_close)  # 连接点击信号到保存方法

        
        bottom_layout = QHBoxLayout()  # 水平布局用于居中按钮
        bottom_layout.addStretch()  # 左侧伸展
        bottom_layout.addWidget(save_button)  # 添加按钮
        bottom_layout.addWidget(cancel_button)  # 添加按钮
        bottom_layout.addStretch()  # 右侧伸展
        
        main_layout.addLayout(innerc_layout)  # 添加底部布局到右侧
        main_layout.addLayout(bottom_layout)  # 添加底部布局到右侧

        # 设置对话框的主布局
        self.setLayout(main_layout)

        # 启动倒计时
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
    
    def cancel_and_close(self):
        # 停止倒计时并关闭窗口，返回 False (QDialog.Rejected)
        if self.timer:
            self.timer.stop()
        self.reject()  # Closes and returns QDialog.Rejected (0)    

  
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)

    def update_countdown(self):
        self.count_down -= 1
        self.stop_button.setText(f"{tr('Click here to stop the countdown')}({self.count_down})")
        if self.count_down <= 0:
            self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        self.timer.stop()
        self.stop_button.deleteLater()
        self.prompt_label.deleteLater()

    def create_speaker_assignment_area(self) -> QWidget:
        # 创建说话人分配角色区域的组框
        group = QGroupBox("")
        layout = QVBoxLayout(group)  # 垂直布局

        # 初始化存储说话人复选框和标签的字典
        self.speaker_checks = {}  # 键: QCheckBox, 值: spk_id
        self.speaker_labels = {}  # 键: QCheckBox, 值: QLabel (显示分配角色)
        
        
        
        # 为每个说话人 ID 创建一行布局
        for spk_id in self.speakers:
            row_layout = QHBoxLayout()  # 水平布局
            check = QCheckBox(f'{tr("Speaker")}{spk_id}')  # 创建复选框，文本为 spk_id
            row_layout.addWidget(check)  # 添加复选框
            label = QLabel("")  # 创建初始为空的标签，用于显示分配角色
            row_layout.addWidget(label)  # 添加标签
            row_layout.addStretch()  # 添加伸展以右对齐
            layout.addLayout(row_layout)  # 添加行布局到组布局
            self.speaker_checks[check] = spk_id  # 存储复选框和 spk_id
            self.speaker_labels[check] = label  # 存储复选框和标签

        # 底部行：组合框和按钮
        bottom_row = QHBoxLayout()  # 水平布局
        self.speaker_combo = QComboBox()  # 创建下拉组合框

        for voice in self.all_voices:  # 添加所有发音人选项
            self.speaker_combo.addItem(voice)
        
        bottom_row.addWidget(QLabel(tr('Dubbing role')))  # 添加组合框
        bottom_row.addWidget(self.speaker_combo)  # 添加组合框
        
        assign_button = QPushButton(tr("Assign roles to speakers"))  # 创建分配按钮
        assign_button.setCursor(Qt.PointingHandCursor)
        assign_button.clicked.connect(self.assign_speaker_roles)  # 连接到分配方法
        assign_button.setMinimumSize(QSize(150, 30))
        bottom_row.addWidget(assign_button)  # 添加按钮
        bottom_row.addStretch()
        layout.addLayout(bottom_row)  # 添加底部行到组布局

        return group  # 返回组框

    def assign_speaker_roles(self):
        # 获取当前选中的角色文本
        selected_role = self.speaker_combo.currentText()
        # 如果是 "No"，则角色值为 None，否则为选中文本
        role_value = None if selected_role == "No" else selected_role

        # 遍历所有说话人复选框，如果选中则更新 speakers 和标签
        for check, spk_id in self.speaker_checks.items():
            if check.isChecked():
                self.speakers[spk_id] = role_value  # 更新 speakers 字典
                label = self.speaker_labels[check]  # 获取对应标签
                label.setText(selected_role if role_value else "")  # 更新标签文本

        # 清空所有选中的复选框，以便用户继续操作
        for check in self.speaker_checks:
            if check.isChecked():
                check.setChecked(False)

    def create_subtitle_assignment_area(self) -> QWidget:
        # 创建字幕按行分配角色区域的组框
        group = QGroupBox("")
        layout = QVBoxLayout(group)  # 垂直布局

        # 创建滚动区域以处理大量字幕行
        scroll = QScrollArea()
        scroll_widget = QWidget()  # 滚动内容小部件
        scroll_layout = QVBoxLayout(scroll_widget)  # 垂直布局

        # 初始化存储字幕行信息的列表
        self.subtitle_rows = []

        # 为每个字幕条目创建一行布局
        for i,item in enumerate(self.srt_list_dict):
            row_outer_layout = QVBoxLayout()  # 水平布局
            row_layout = QHBoxLayout()  # 水平布局
            text_layout = QHBoxLayout()  # 水平布局

            spkid=''
            if self.speakers and i<len(self.speaker_list_sub):
                spkid=self.speaker_list_sub[i]
            elif self.speakers:
                spkid=list(self.speakers.keys())[0]

            row_layout.addWidget(QLabel(f"[{item['line']}] {spkid}"))  # 添加标签
            check = QCheckBox()  # 创建复选框，用于选中该行
            row_layout.addWidget(check)  # 添加复选框

            role_label = QLabel("")  # 创建初始为空的标签，用于显示分配角色
            row_layout.addWidget(role_label)  # 添加标签

            # 创建时间标签，包含 spkid、时长、开始和结束时间
            duration=(item['end_time']-item['start_time'])/1000.0
            time_label = QLabel(f"{duration}s / {item['startraw']}->{item['endraw']} ")
            row_layout.addWidget(time_label)  # 添加时间标签
            row_layout.addStretch()

            text_edit = QLineEdit()  # 创建可编辑文本编辑器
            text_edit.setText(item['text'])  # 设置初始文本

            text_layout.addWidget(text_edit)  # 添加文本编辑器
            row_outer_layout.addLayout(row_layout)
            row_outer_layout.addLayout(text_layout)
            scroll_layout.addLayout(row_outer_layout)  # 添加行布局到滚动布局
            # 添加水平分隔线（除了最后一行）
            if i < len(self.srt_list_dict) - 1:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("color: #aaaaaa;")
                scroll_layout.addWidget(separator)
            # 存储行信息字典
            self.subtitle_rows.append({
                'check': check,  # 复选框
                'role_label': role_label,  # 角色标签
                'text_edit': text_edit,  # 文本编辑器
                'item': item  # 对应的字幕数据项
            })

        scroll.setWidget(scroll_widget)  # 设置滚动内容
        scroll.setWidgetResizable(True)  # 允许调整大小
        layout.addWidget(scroll)  # 添加滚动区域到组布局

        # 底部行：组合框和按钮
        bottom_row = QHBoxLayout()  # 水平布局
        self.subtitle_combo = QComboBox()  # 创建下拉组合框
        for voice in self.all_voices:  # 添加所有发音人选项
            self.subtitle_combo.addItem(voice)
        bottom_row.addWidget(self.subtitle_combo)  # 添加组合框

        assign_button = QPushButton(tr("Assign roles to selected subtitles"))  # 创建分配按钮
        assign_button.setCursor(Qt.PointingHandCursor)
        assign_button.clicked.connect(self.assign_subtitle_roles)  # 连接到分配方法
        assign_button.setMinimumSize(QSize(200, 30))
        bottom_row.addWidget(assign_button)  # 添加按钮
        bottom_row.addStretch()
        layout.addLayout(bottom_row)  # 添加底部行到组布局

        return group  # 返回组框

    def replace_text(self):
        # 获取查找和替换的文本
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()

        # 遍历所有字幕行，替换文本
        for row in self.subtitle_rows:
            current_text = row['text_edit'].text()
            updated_text = current_text.replace(search_text, replace_text)
            row['text_edit'].setText(updated_text)
            row['item']['text'] = updated_text  # 同步更新 srt_list_dict 中的文本


    def assign_subtitle_roles(self):
        # 获取当前选中的角色文本
        selected_role = self.subtitle_combo.currentText()
        # 如果是 "No"，则角色值为 None，否则为选中文本
        role_value = None if selected_role == "No" else selected_role

        # 遍历所有字幕行，如果选中则更新 item['role'] 和标签
        for row in self.subtitle_rows:
            if row['check'].isChecked():
                row['item']['role'] = role_value  # 更新字幕项的 'role'
                row['role_label'].setText(selected_role if role_value else "")  # 更新标签文本

        # 清空所有选中的复选框，以便用户继续操作
        for row in self.subtitle_rows:
            if row['check'].isChecked():
                row['check'].setChecked(False)

    def save_and_close(self):
        # 更新角色
        config.line_roles={}
        srt_str_list=[]
        # 更新所有字幕行的文本，使用编辑后的内容
        for i,row in enumerate(self.subtitle_rows):
            # 保存修改后的字幕
            text = row['text_edit'].text().strip()
            srt_str_list.append(f'{row["item"]["line"]}\n{row["item"]["startraw"]} --> {row["item"]["endraw"]}\n{text}')
            
            # 获取角色
            role= row.get('role')
            # 如果不存在，则使用说话人对应角色,最终未指定角色的统一使用默认
            if not role and self.speakers and i<len(self.speaker_list_sub):
                role=self.speakers.get(self.speaker_list_sub[i])
            # 更新该行字幕对应角色
            if role:
                config.line_roles[f'{row["item"]["line"]}']=role
        
        Path(self.target_sub).write_text("\n\n".join(srt_str_list),encoding="utf-8")
        print(f'{config.line_roles=}')
        # 接受对话框，关闭并返回 True (QDialog.Accepted)
        self.accept()  # Closes and returns QDialog.Accepted (which is 1, but user can check if exec() == True)
