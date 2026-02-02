import json
import sys
from typing import List, Dict, Optional
from pathlib import Path
import re
import time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QCheckBox,
    QComboBox, QPushButton, QWidget, QGroupBox, QPlainTextEdit, 
    QMessageBox, QProgressBar, QApplication, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QGridLayout
)
from PySide6.QtGui import QIcon, QDesktopServices, QColor
from PySide6.QtCore import Qt, QTimer, QSize, QUrl

from videotrans.configure.config import tr
from videotrans.util import tools
from videotrans.configure import config


class SpeakerAssignmentDialog(QDialog):
    def __init__(
            self,
            parent=None,
            target_sub: str = None,
            all_voices: Optional[List[str]] = None,
            source_sub: str = None,
            cache_folder=None,
            target_language="en",
            tts_type=0
    ):
        super().__init__()
        self.parent = parent
        self.target_sub = target_sub
        self.source_srtstring = None
        self.cache_folder = cache_folder
        self.target_language = target_language
        self.tts_type = tts_type

        if source_sub:
            sour_pt = Path(source_sub)
            if sour_pt.as_posix() and not sour_pt.samefile(Path(target_sub)):
                try:
                    self.source_srtstring = sour_pt.read_text(encoding="utf-8")
                except:
                    self.source_srtstring = ""

        self.srt_list_dict = tools.get_subtitle_from_srt(self.target_sub)

        # 说话人数据初始化
        self.speaker_list_sub = []
        self.speakers = {}
        try:
            spk_json_path = Path(f'{self.cache_folder}/speaker.json')
            _list_sub = [] if not spk_json_path.exists() else json.loads(spk_json_path.read_text(encoding='utf-8'))
            _set = set(_list_sub) if _list_sub else None
            if _set and len(_set) > 1:
                self.speaker_list_sub = _list_sub
                self.speakers = {it: None for it in sorted(list(_set))}
        except Exception as e:
            config.logger.exception(f'获取说话人id失败:{e}', exc_info=True)

        self.all_voices = all_voices or []

        self.setWindowTitle(tr("zidonghebingmiaohou"))
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setMinimumWidth(int(parent.width*0.95))
        self.setMinimumHeight(int(parent.height*0.95))
        self.setWindowFlags(
        Qt.WindowStaysOnTopHint |       # 2. 始终在最顶层
            Qt.WindowTitleHint |            # 3. 显示标题栏
            Qt.CustomizeWindowHint |        # 4. 允许自定义标题栏按钮（否则OS会强制加关闭按钮）
            Qt.WindowMaximizeButtonHint     # 5. 只加最大化按钮，不加关闭按钮
        )

        main_layout = QVBoxLayout(self)
        
        # --- 顶部：倒计时与提示 ---
        self.count_down = int(float(config.settings.get('countdown_sec', 1)))
        top_layout = QVBoxLayout()
        hstop = QHBoxLayout()

        self.prompt_label = QLabel(tr("This window will automatically close after the countdown ends"))
        self.prompt_label.setStyleSheet('font-size:14px;color:#aaaaaa')
        self.prompt_label.setWordWrap(True)
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
        prompt_label2.setStyleSheet("color: #dddddd")
        prompt_label2.setWordWrap(True)
        top_layout.addWidget(prompt_label2)
        main_layout.addLayout(top_layout)

        # --- 查找替换区域 ---
        search_replace_layout = QHBoxLayout()
        search_replace_layout.addStretch()
        self.search_input = QLineEdit()
        self.search_input.setMaximumWidth(200)
        self.search_input.setPlaceholderText(tr("Original text"))
        search_replace_layout.addWidget(self.search_input)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText(tr("Replace"))
        self.replace_input.setMaximumWidth(200)
        search_replace_layout.addWidget(self.replace_input)
        replace_button = QPushButton(tr("Replace"))
        replace_button.setMinimumWidth(100)
        replace_button.setMaximumWidth(200)
        replace_button.setCursor(Qt.PointingHandCursor)
        replace_button.clicked.connect(self.replace_text)
        search_replace_layout.addWidget(replace_button)
        search_replace_layout.addStretch()
        main_layout.addLayout(search_replace_layout)

        # --- 中间内容区域 ---
        content_layout = QHBoxLayout()
        
        # 左侧：源字幕参考
        if self.source_srtstring:
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            self.raw_srt_edit = QPlainTextEdit()
            self.raw_srt_edit.setPlainText(self.source_srtstring)
            self.raw_srt_edit.setReadOnly(True)
            self.raw_srt_edit.setStyleSheet("color: #aaaaaa;")
            tiplabel = QLabel(tr("This is the original language subtitles for comparison reference"))
            tiplabel.setStyleSheet("color:#aaaaaa")
            left_layout.addWidget(tiplabel)
            left_layout.addWidget(self.raw_srt_edit)
            content_layout.addWidget(left_widget, stretch=2)

        # 右侧主区域
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        
        # Loading 区域
        self.loading_widget = QWidget()
        load_layout = QVBoxLayout(self.loading_widget)
        self.loading_label = QLabel(tr('Loading...'), self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        load_layout.addWidget(self.loading_label)
        self.right_layout.addWidget(self.loading_widget)

        # 表格容器
        self.table_container = QWidget()
        self.table_container_layout = QVBoxLayout(self.table_container)
        self.table_container.setVisible(False)
        self.right_layout.addWidget(self.table_container)
        
        # 底部按钮容器
        self.bottom_button_container = QWidget()
        self.bottom_button_container_layout = QHBoxLayout(self.bottom_button_container)
        self.bottom_button_container.setVisible(False)
        self.right_layout.addWidget(self.bottom_button_container)

        content_layout.addWidget(self.right_widget, stretch=7)
        main_layout.addLayout(content_layout, stretch=1)

        # --- 底部按钮 ---
        self.save_button = QPushButton(tr("nextstep"))
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setMinimumSize(QSize(300, 35))
        self.save_button.clicked.connect(self.save_and_close)

        self.save_button2 = QPushButton(tr("nosaveandstep"))
        self.save_button2.setCursor(Qt.PointingHandCursor)
        self.save_button2.setToolTip(tr('bubaocunshuoming', self.target_sub))
        self.save_button2.setMinimumSize(QSize(200, 35))
        self.save_button2.clicked.connect(self.save_and_close2)

        self.opendir_button = QPushButton(tr("opendir_button source_sub"))
        self.opendir_button.setCursor(Qt.PointingHandCursor)
        self.opendir_button.setMaximumSize(QSize(150, 30))
        self.opendir_button.clicked.connect(self.opendir_sub)

        cancel_button = QPushButton(tr("Terminate this mission"))
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setStyleSheet("background-color:transparent;color:#ff0")
        cancel_button.setMinimumSize(QSize(150, 30))
        cancel_button.clicked.connect(self.cancel_and_close)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(self.save_button2)
        bottom_layout.addWidget(self.opendir_button)
        bottom_layout.addWidget(cancel_button)
        bottom_layout.addStretch()

        main_layout.addLayout(bottom_layout)

        # 延迟加载表格
        QTimer.singleShot(10, self.load_table)


    def load_table(self):
        """极致性能加载表格"""
        if not self.isVisible():
            return

        try:
            # 1. 创建 QTableWidget（比 Model/View 快得多）
            self.table = QTableWidget()
            
            # 2. 【极致性能配置】禁用所有非必要功能
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(["Sel", tr("Line"), tr('Speaker'), tr("Dubbing role"), tr("Time Axis"), tr("Subtitle Text")])
            
            # 禁用所有视觉效果
            self.table.setAlternatingRowColors(False)
            self.table.setShowGrid(False)  # 不显示网格线
            
            # 禁用选择
            self.table.setSelectionMode(QAbstractItemView.NoSelection)
            self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
            
            # 禁用焦点
            self.table.setFocusPolicy(Qt.NoFocus)
            
            # 固定行高，避免动态计算
            self.table.verticalHeader().setDefaultSectionSize(22)
            self.table.verticalHeader().setVisible(False)
            
            # 列宽设置
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)  # Sel
            header.setSectionResizeMode(1, QHeaderView.Fixed)  # ID
            header.setSectionResizeMode(2, QHeaderView.Fixed)  # Spk
            header.setSectionResizeMode(3, QHeaderView.Fixed)  # Role
            header.setSectionResizeMode(4, QHeaderView.Fixed)  # Time
            header.setSectionResizeMode(5, QHeaderView.Stretch)  # Text
            
            self.table.setColumnWidth(0, 30)
            self.table.setColumnWidth(1, 40)
            self.table.setColumnWidth(2, 50)
            self.table.setColumnWidth(3, 150)
            self.table.setColumnWidth(4, 210)
            
            # 最小样式
            self.table.setStyleSheet("""
                QTableWidget {
                    color: #eeeeee;
                    border: none;
                }
                QHeaderView::section {
                    background-color: #2b2b2b;
                    color: white;
                    padding: 2px;
                    border: none;
                    border-right: 1px solid #3e3e3e;
                }
                QTableWidget::item {
                    padding: 2px;
                }
            """)
            
            # 3. 预计算所有显示数据
            speaker_keys = list(self.speakers.keys()) if self.speakers else []
            default_spk = speaker_keys[0] if speaker_keys else ''
            
            self.display_data = []
            for i, item in enumerate(self.srt_list_dict):
                # Speaker ID
                if self.speakers and i < len(self.speaker_list_sub):
                    spk = self.speaker_list_sub[i]
                else:
                    spk = default_spk if self.speakers else ''
                
                # 时间字符串
                duration = (item['end_time'] - item['start_time']) / 1000.0
                time_str = f"{item['startraw']}->{item['endraw']}({duration:.1f}s)"
                
                self.display_data.append({
                    'line': item['line'],
                    'spk': spk,
                    'time_str': time_str,
                    'text': item['text'],
                    'startraw': item['startraw'],
                    'endraw': item['endraw'],
                    'start_time': item['start_time'],
                    'end_time': item['end_time'],
                    'checked': False,
                    'role': ''
                })
            
            # 4. 设置行数
            total_rows = len(self.display_data)
            self.table.setRowCount(total_rows)
            
            # 5. 【批量填充数据】一次性创建所有单元格
            self._batch_fill_table(0, min(total_rows, 100))  # 先填充前100行
            
            # 6. 添加到布局
            self.table_container_layout.addWidget(self.table)
            
            # 7. 添加底部按钮
            self._setup_bottom_buttons()
            
            # 8. 显示表格
            self.loading_widget.setVisible(False)
            self.table_container.setVisible(True)
            self.bottom_button_container.setVisible(True)
            
            # 9. 延迟加载剩余数据
            if total_rows > 100:
                QTimer.singleShot(0, lambda: self._load_remaining_rows(100))
            
            # 10. 启动倒计时
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)
            self._active()
            
        except Exception as e:
            print(f"Load table failed: {e}")
            import traceback
            traceback.print_exc()
            self.loading_label.setText(f"Error: {e}")

    def _batch_fill_table(self, start_row, end_row):
        """批量填充表格数据 - 减少重绘"""
        for row in range(start_row, end_row):
            data = self.display_data[row]
            
            # 第0列：复选框
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            chk_item.setCheckState(Qt.Unchecked)
            self.table.setItem(row, 0, chk_item)
            
            # 第1列：ID（只读）
            id_item = QTableWidgetItem(str(data['line']))
            id_item.setFlags(Qt.ItemIsEnabled)  # 只读
            self.table.setItem(row, 1, id_item)
            
            # 第2列：Speaker（只读）
            spk_item = QTableWidgetItem(data['spk'])
            spk_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 2, spk_item)
            
            # 第3列：Role（只读，显示用）
            role_item = QTableWidgetItem(tr('Default Role'))
            role_item.setFlags(Qt.ItemIsEnabled)
            role_item.setForeground(QColor("#ff4d4d"))
            self.table.setItem(row, 3, role_item)
            
            # 第4列：Time（只读）
            time_item = QTableWidgetItem(data['time_str'])
            time_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 4, time_item)
            
            # 第5列：Text（可编辑）
            text_item = QTableWidgetItem(data['text'])
            text_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self.table.setItem(row, 5, text_item)

    def _load_remaining_rows(self, start_row):
        """延迟加载剩余行 - 避免界面冻结"""
        total = len(self.display_data)
        batch_size = 200  # 每批加载200行
        
        end_row = min(start_row + batch_size, total)
        self._batch_fill_table(start_row, end_row)
        
        if end_row < total:
            # 还有数据，继续加载
            QTimer.singleShot(0, lambda: self._load_remaining_rows(end_row))

    def _setup_bottom_buttons(self):
        """设置底部按钮区域"""
        # 如果有说话人，添加说话人分配区域
        if self.speakers:
            speaker_widget = self._create_speaker_assignment_area()
            # 插入到表格容器之前
            self.right_layout.insertWidget(0, speaker_widget)
        
        # 底部按钮
        self.subtitle_combo = QComboBox()
        self.subtitle_combo.addItems(self.all_voices)
        self.bottom_button_container_layout.addWidget(self.subtitle_combo)

        assign_button = QPushButton(tr("Assign roles to selected subtitles"))
        assign_button.setCursor(Qt.PointingHandCursor)
        assign_button.clicked.connect(self.assign_subtitle_roles)
        assign_button.setMinimumSize(QSize(180, 28))
        self.bottom_button_container_layout.addWidget(assign_button)

        self.listen_button = QPushButton(tr("Trial dubbing"))
        self.listen_button.setCursor(Qt.PointingHandCursor)
        self.listen_button.clicked.connect(self.listen_dubbing)
        self.bottom_button_container_layout.addWidget(self.listen_button)
        
        labe_tips=QLabel(tr('If not specified separately'))
        
        self.bottom_button_container_layout.addWidget(labe_tips)
        self.bottom_button_container_layout.addStretch()

    def _create_speaker_assignment_area(self):
        """创建说话人分配区域"""
        group = QGroupBox("")
        group.setStyleSheet("QGroupBox{border:none;}")
        layout = QVBoxLayout(group)
        label_tips = QLabel(tr("Assign a timbre to each speaker"))
        label_tips.setStyleSheet("color:#aaaaaa")
        layout.addWidget(label_tips)

        self.speaker_checks = {}
        self.speaker_labels = {}

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 5, 0, 5)
        grid_layout.setHorizontalSpacing(15)
        grid_layout.setVerticalSpacing(5)

        for i, spk_id in enumerate(self.speakers):
            row = i // 3
            col = (i % 3) * 2

            check = QCheckBox(f'{tr("Speaker")}{spk_id}')
            check.setStyleSheet("color: #dddddd;")
            
            label = QLabel("")
            label.setMinimumWidth(80)
            label.setStyleSheet("color: #ffcccc;")

            grid_layout.addWidget(check, row, col)
            grid_layout.addWidget(label, row, col + 1)

            self.speaker_checks[check] = spk_id
            self.speaker_labels[check] = label

        layout.addLayout(grid_layout)

        bottom_row = QHBoxLayout()
        self.speaker_combo = QComboBox()
        self.speaker_combo.addItems(self.all_voices)
        
        lbl = QLabel(tr('Dubbing role'))
        lbl.setStyleSheet("color: #dddddd;")
        bottom_row.addWidget(lbl)
        bottom_row.addWidget(self.speaker_combo)

        assign_button = QPushButton(tr("Assign roles"))
        assign_button.setCursor(Qt.PointingHandCursor)
        assign_button.clicked.connect(self.assign_speaker_roles)
        assign_button.setMinimumSize(QSize(120, 26))
        bottom_row.addWidget(assign_button)
        bottom_row.addStretch()

        layout.addLayout(bottom_row)
        return group

    def assign_speaker_roles(self):
        """分配角色给说话人"""
        selected_role = self.speaker_combo.currentText()
        role_value = None if selected_role == "No" else selected_role

        for check, spk_id in self.speaker_checks.items():
            if check.isChecked():
                self.speakers[spk_id] = role_value
                self.speaker_labels[check].setText(selected_role if role_value else "")
                check.setChecked(False)
        
        # 更新表格中的 Role 列
        self._update_role_column()

    def _update_role_column(self):
        """更新 Role 列显示"""
        for row, data in enumerate(self.display_data):
            # 优先显示行内角色，否则显示说话人对应的全局角色
            role = data.get('role', '')
            if not role and data['spk']:
                role = self.speakers.get(data['spk'], '')
            
            item = self.table.item(row, 3)
            if item:
                item.setText(role if role else tr('Default Role'))

    def assign_subtitle_roles(self):
        """分配角色给选中的行"""
        selected_role = self.subtitle_combo.currentText()
        role_value = None if selected_role == "No" else selected_role

        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.Checked:
                self.display_data[row]['role'] = role_value
                chk_item.setCheckState(Qt.Unchecked)
        
        self._update_role_column()

    def replace_text(self):
        """替换文本"""
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            return

        self.table.setUpdatesEnabled(False)  # 禁用更新，提升性能
        
        for row, data in enumerate(self.display_data):
            if search_text in data['text']:
                new_text = data['text'].replace(search_text, replace_text)
                data['text'] = new_text
                item = self.table.item(row, 5)
                if item:
                    item.setText(new_text)
        
        self.table.setUpdatesEnabled(True)  # 恢复更新

    def listen_dubbing(self):
        """试听配音"""
        selected_role = self.subtitle_combo.currentText()
        role_value = None if selected_role == "No" else selected_role
        if not role_value:
            return

        first_text = self.display_data[0]['text'] if self.display_data else ''
        if not first_text:
            return

        from videotrans.util.ListenVoice import ListenVoice
        
        def feed(d):
            self.listen_button.setText(tr("Trial dubbing"))
            self.listen_button.setDisabled(False)
            if d != "ok":
                tools.show_error(d)

        wk = ListenVoice(parent=self, queue_tts=[{
            "text": first_text,
            "role": role_value,
            "filename": config.TEMP_DIR + f"/{time.time()}-onlyone_setrole.wav",
            "tts_type": self.tts_type}],
            language=self.target_language,
            tts_type=self.tts_type)
        wk.uito.connect(feed)
        wk.start()
        self.listen_button.setText('Listening...')
        self.listen_button.setDisabled(True)

    def _active(self):
        if self.parent:
            self.parent.activateWindow()

    def cancel_and_close(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        self.reject()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)

    def update_countdown(self):
        self.count_down -= 1
        if self.stop_button and hasattr(self.stop_button, 'setText'):
            self.stop_button.setText(f"{tr('Click here to stop the countdown')}({self.count_down})")
        if self.count_down <= 0:
            self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.stop_button.deleteLater()
        self.prompt_label.deleteLater()

    def save_and_close2(self):
        self.accept()

    def opendir_sub(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(Path(self.target_sub).parent.as_posix()))


    def closeEvent(self, event):
        event.ignore()  # 忽略关闭请求，窗口保持不动
    
    def save_and_close(self):
        self.save_button.setDisabled(True)
        config.line_roles = {}
        srt_str_list = []

        speaker_keys = list(self.speakers.keys()) if self.speakers else []
        default_spk = speaker_keys[0] if speaker_keys else ''

        for row, data in enumerate(self.display_data):
            # 获取当前文本（从表格中获取最新值）
            text_item = self.table.item(row, 5)
            text = text_item.text().strip() if text_item else data['text'].strip()
            
            srt_str_list.append(f'{data["line"]}\n{data["startraw"]} --> {data["endraw"]}\n{text}')

            # 角色保存逻辑
            role = data.get('role', '')
            if not role and self.speakers and data['spk']:
                role = self.speakers.get(data['spk'], '')

            if role:
                config.line_roles[str(data["line"])] = role

        try:
            Path(self.target_sub).write_text("\n\n".join(srt_str_list), encoding="utf-8")
        except Exception as e:
            config.logger.error(f"Save subtitle failed: {e}")
            QMessageBox.critical(self, "Error", f"Save failed: {e}")
            self.save_button.setDisabled(False)
            return

        self.accept()