

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
     QPushButton, QScrollArea, QWidget, QGroupBox, QFrame
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer,QSize

from videotrans.configure.config import tr
from videotrans.util import tools
from videotrans.configure import config
from pathlib import Path


class EditRecognResultDialog(QDialog):
    def __init__(
        self,
        parent=None,
        source_sub: str = None
    ):
        # 初始化对话框的基本属性
        super().__init__()
        self.parent=parent
        self.source_sub=source_sub
        # 整理后的字幕
        self.srt_list_dict=tools.get_subtitle_from_srt(self.source_sub)
        


        # 设置窗口标题
        self.setWindowTitle(tr("zimubianjitishi"))
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        # 设置窗口最小宽度为 1000px
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        # 设置窗口标志：禁用关闭按钮，启用最大化按钮
        self.setWindowFlags(Qt.WindowTitleHint | Qt.WindowSystemMenuHint  | Qt.WindowMaximizeButtonHint)
        # 添加顶部提示行和按钮
        self.count_down = int(float(config.settings.get('countdown_sec', 1)))

        # 创建主布局：水平布局，用于左右分隔
        main_layout = QVBoxLayout(self)
        


        hstop=QHBoxLayout()

        self.prompt_label = QLabel(tr("jimiaohoufanyi"))
        self.prompt_label.setStyleSheet('font-size:14px;text-align:center;color:#aaaaaa')
        self.prompt_label.setWordWrap(True)
        hstop.addWidget(self.prompt_label)

        self.stop_button = QPushButton(f"{tr('Click here to stop the countdown')}({self.count_down})")
        self.stop_button.setStyleSheet("font-size: 16px;color:#ffff00")
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setMinimumSize(QSize(300, 35))
        self.stop_button.clicked.connect(self.stop_countdown)
        hstop.addWidget(self.stop_button)

        main_layout.addLayout(hstop)


        prompt_label2 = QLabel(tr("If you need to delete a line of subtitles, just clear the text in that line"))
        prompt_label2.setAlignment(Qt.AlignCenter)
        prompt_label2.setWordWrap(True)
        main_layout.addWidget(prompt_label2)


        right_widget = QWidget()  # 创建右侧容器小部件
        right_layout = QVBoxLayout(right_widget)  # 垂直布局
        

        # 添加顶部查找和替换布局
        search_replace_layout = QHBoxLayout()
        search_replace_layout.addStretch()
        self.search_input = QLineEdit()  # 创建查找目标输入框
        self.search_input.setPlaceholderText(tr("Original text"))
        self.search_input.setMaximumWidth(200)
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

        

        


        subtitle_area = self.create_subtitle_assignment_area()  # 创建字幕区域
        right_layout.addWidget(subtitle_area)  # 添加到右侧布局

        main_layout.addWidget(right_widget, stretch=7)  # 添加右侧到主布局，伸展因子 7

        # 底部保存按钮
        save_button = QPushButton(tr("nextstep"))  # 创建保存按钮
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setMinimumSize(QSize(400, 35))
        save_button.clicked.connect(self.save_and_close)  # 连接点击信号到保存方法
        cancel_button = QPushButton(tr("Terminate this mission"))  # 创建保存按钮
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMaximumSize(QSize(200, 30))
        cancel_button.clicked.connect(self.cancel_and_close)  # 连接点击信号到保存方法
        bottom_layout = QHBoxLayout()  # 水平布局用于居中按钮
        bottom_layout.addStretch()  # 左侧伸展
        bottom_layout.addWidget(save_button)  # 添加按钮
        bottom_layout.addWidget(cancel_button)  # 添加按钮
        bottom_layout.addStretch()  # 右侧伸展
        
        main_layout.addLayout(bottom_layout)  # 添加底部布局到右侧

        # 设置对话框的主布局
        self.setLayout(main_layout)

        # 启动倒计时
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
        QTimer.singleShot(0, self._active)
    
    
    def _active(self):
        self.parent.raise_()
        self.parent.activateWindow()    
    
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
        self.stop_button.setText(f"{tr('点此停止倒计时')}({self.count_down})")
        if self.count_down <= 0:
            self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        self.timer.stop()
        self.stop_button.deleteLater()
        self.prompt_label.deleteLater()


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

            # 创建时间标签，包含 时长、开始和结束时间
            duration=(item['end_time']-item['start_time'])/1000.0
            time_label = QLabel(f"{item['line']} ({duration}s) {item['startraw']}->{item['endraw']} ")
            row_outer_layout.addWidget(time_label)  # 添加时间标签

            text_edit = QLineEdit()  # 创建可编辑文本编辑器
            text_edit.setText(item['text'])  # 设置初始文本
            row_outer_layout.addWidget(text_edit)

            scroll_layout.addLayout(row_outer_layout)  # 添加行布局到滚动布局
            if i < len(self.srt_list_dict) - 1:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("color: #aaaaaa;")
                scroll_layout.addWidget(separator)
            # 存储行信息字典
            self.subtitle_rows.append({
                'text_edit': text_edit,  # 文本编辑器
                'item': item  # 对应的字幕数据项
            })

        scroll.setWidget(scroll_widget)  # 设置滚动内容
        scroll.setWidgetResizable(True)  # 允许调整大小
        layout.addWidget(scroll)  # 添加滚动区域到组布局


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


    def save_and_close(self):
        # 更新角色
        srt_str_list=[]
        # 更新所有字幕行的文本，使用编辑后的内容
        for row in self.subtitle_rows:
            # 保存修改后的字幕
            text = row['text_edit'].text().strip()
            if text:
                srt_str_list.append(f'{row["item"]["line"]}\n{row["item"]["startraw"]} --> {row["item"]["endraw"]}\n{text}')
            
        
        Path(self.source_sub).write_text("\n\n".join(srt_str_list),encoding="utf-8")
        
        # 接受对话框，关闭并返回 True (QDialog.Accepted)
        self.accept()  # Closes and returns QDialog.Accepted (which is 1, but user can check if exec() == True)
