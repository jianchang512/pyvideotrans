import threading
import json
import traceback
from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QWidget, QProgressBar, QApplication, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QMenu, QInputDialog
)
from PySide6.QtGui import QIcon, QDesktopServices, QColor, QCursor, QFont
from PySide6.QtCore import Qt, QTimer, QSize, QUrl, QThread, Signal, QRect

from pydub import AudioSegment
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
from videotrans.util import tools
from videotrans.configure import config
from videotrans import tts


class ReDubb(QThread):
    uito = Signal(str)

    def __init__(self, *, parent=None, idx=0, tts_dict=None, language=None):
        super().__init__(parent=parent)
        self.tts_dict = tts_dict
        self.language = language
        self.idx = idx

    def run(self):
        try:
            tts.run(
                queue_tts=[self.tts_dict],
                language=self.language,
                tts_type=self.tts_dict['tts_type']
            )
            self.uito.emit(f"ok:{self.idx}")
        except Exception as e:
            from videotrans.configure._except import get_msg_from_except
            except_msg = get_msg_from_except(e)
            msg = f'{except_msg}:\n' + traceback.format_exc()
            self.uito.emit(msg)


class EditDubbingResultDialog(QDialog):
    def __init__(
            self,
            parent=None,
            language=None,
            cache_folder: str = None
    ):
        super().__init__()
        self.parent = parent
        self.language = language
        self.cache_folder = cache_folder
        self.queue_tts = json.loads(Path(f'{cache_folder}/queue_tts.json').read_text(encoding='utf-8'))

        self.setWindowTitle(tr("Proofreading and dubbing - Re-dubbing"))
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        self.setWindowFlags(Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMaximizeButtonHint)

        self.count_down = int(float(settings.get('countdown_sec', 1)))

        main_layout = QVBoxLayout(self)

        # Top Bar
        hstop = QHBoxLayout()
        self.prompt_label = QLabel(tr("You can check the voiceover here, or modify the text and re-encode the voiceover. Please stop the countdown before proceeding"))
        self.prompt_label.setStyleSheet('font-size:14px;color:#aaaaaa')
        self.prompt_label.setWordWrap(True)
        hstop.addWidget(self.prompt_label)

        self.stop_button = QPushButton(f"{tr('Click here to stop the countdown')}({self.count_down})")
        self.stop_button.setStyleSheet("font-size: 16px;color:#ffff00")
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setMinimumSize(QSize(300, 35))
        self.stop_button.clicked.connect(self.stop_countdown)
        hstop.addWidget(self.stop_button)
        main_layout.addLayout(hstop)

        # 操作提示
        prompt_label2 = QLabel(tr("Right-click: Menu | << >> : Adjust time")+"\n"+tr('Shortened and Exceeded mean'))
        prompt_label2.setAlignment(Qt.AlignCenter)
        prompt_label2.setWordWrap(True)
        prompt_label2.setStyleSheet("font-size: 14px;")
        main_layout.addWidget(prompt_label2)

        # Loading
        self.loading_widget = QWidget()
        load_layout = QVBoxLayout(self.loading_widget)
        self.loading_label = QLabel(tr('Loading...'), self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        load_layout.addWidget(self.loading_label)
        main_layout.addWidget(self.loading_widget)

        # Table Widget (初始隐藏)
        self.table = QTableWidget()
        self.table.setVisible(False)
        main_layout.addWidget(self.table)

        # Bottom Bar
        self.save_button = QPushButton(tr("nextstep"))
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setMinimumSize(QSize(400, 35))
        self.save_button.clicked.connect(self.save_and_close)
        
        cancel_button = QPushButton(tr("Terminate this mission"))
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMaximumSize(QSize(200, 30))
        cancel_button.setStyleSheet("background-color:transparent")
        cancel_button.clicked.connect(self.cancel_and_close)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.save_button)
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
            # 1. 创建 QTableWidget - 只有5列
            # 列：Line | Start | End | Status | Text
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels([
                tr("Line"), tr("Start Time"), tr("End Time"), tr("Dubbed Status"), tr("Subtitle Text")
            ])
            
            # 2.
            self.table.setShowGrid(True)
            self.table.setAlternatingRowColors(False)
            self.table.setWordWrap(False)
            self.table.setMouseTracking(False)
            self.table.setFocusPolicy(Qt.StrongFocus)
            self.table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
            
            # 垂直表头
            v_header = self.table.verticalHeader()
            v_header.setVisible(False)
            v_header.setSectionResizeMode(QHeaderView.Fixed)
            v_header.setDefaultSectionSize(24)  # 更小行高
            
            # 水平表头
            h_header = self.table.horizontalHeader()
            h_header.setSectionResizeMode(0, QHeaderView.Fixed)  # Line
            h_header.setSectionResizeMode(1, QHeaderView.Fixed)  # Start
            h_header.setSectionResizeMode(2, QHeaderView.Fixed)  # End
            h_header.setSectionResizeMode(3, QHeaderView.Fixed)  # Status
            h_header.setSectionResizeMode(4, QHeaderView.Stretch)  # Text
            
            # 设置列宽
            self.table.setColumnWidth(0, 50)   # Line
            self.table.setColumnWidth(1, 130)   # Start
            self.table.setColumnWidth(2, 130)   # End
            self.table.setColumnWidth(3, 120)  # Status
            

            self.table.setStyleSheet("""
                QTableWidget {
                    color: #cccccc;
                    border: 1px solid #333;
                    gridline-color: #333;
                }
                QTableWidget::item {
                    padding: 1px 3px;
                }
                QTableWidget::item:selected {
                    background-color: #0066cc;
                }
                QHeaderView::section {
                    background-color: #252525;
                    color: #aaa;
                    border: none;
                    border-right: 1px solid #3e3e3e;
                    padding: 2px;
                }
            """)
            
            # 3. 预计算数据
            self._precompute_data()
            
            # 4. 设置行数
            total_rows = len(self.queue_tts)
            self.table.setRowCount(total_rows)
            
            # 5. 分批填充数据
            self._batch_fill(0, min(total_rows, 200))
            
            # 6. 显示表格
            self.loading_widget.setVisible(False)
            self.table.setVisible(True)
            
            # 7. 延迟加载剩余数据
            if total_rows > 200:
                QTimer.singleShot(0, lambda: self._load_remaining(200))
            
            # 8. 连接信号
            self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
            self.table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self._show_context_menu)
            
            # 9. 启动倒计时
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)
            if self.parent:
                self.parent.activateWindow()
                
        except Exception as e:
            print(f"Load table failed: {e}")
            import traceback
            traceback.print_exc()
            self.loading_label.setText(f"Error: {e}")

    def _precompute_data(self):
        """预计算所有显示数据"""
        for item in self.queue_tts:
            duration = (item['end_time'] - item['start_time']) / 1000.0
            dubbing = float(item.get('dubbing_s', 0.0))
            diff = round(dubbing - duration, 3)
            
            if dubbing <= 0.0:
                msg = tr('No audio')
            elif diff > 0:
                msg = f'[{dubbing}s]{tr("Exceeded")}{diff}s'
            elif diff < 0:
                msg = f'[{dubbing}s]{tr("Shortened")}{abs(diff)}s'
            else:
                msg = f'{dubbing}s'
            
            item['_duration'] = duration
            item['_msg'] = msg

    def _batch_fill(self, start_row, end_row):
        """批量填充表格数据 - 纯文本，无按钮"""
        for row in range(start_row, end_row):
            item = self.queue_tts[row]
            
            # 0: Line
            line_item = QTableWidgetItem(str(item['line']))
            line_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            line_item.setData(Qt.UserRole, row)
            self.table.setItem(row, 0, line_item)
            
            # 1: Start (显示为  00:00:00,000)
            start_item = QTableWidgetItem(f"{item['startraw']}")
            start_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            start_item.setTextAlignment(Qt.AlignCenter)
            start_item.setToolTip(tr("Double-click: -0.1s | Right-click: adjust"))
            self.table.setItem(row, 1, start_item)
            
            # 2: End
            end_item = QTableWidgetItem(f"{item['endraw']}")
            end_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            end_item.setTextAlignment(Qt.AlignCenter)
            end_item.setToolTip(tr("Double-click: +0.1s | Right-click: adjust"))
            self.table.setItem(row, 2, end_item)
            
            # 3: Status
            msg_item = QTableWidgetItem(item['_msg'])
            msg_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            msg_item.setTextAlignment(Qt.AlignCenter)
            dubbing = float(item.get('dubbing_s', 0.0))
            diff=dubbing - float( item['_duration'])
            if dubbing <= 0:
                msg_item.setForeground(QColor("#ff4d4d"))  # 橙色
            elif  diff>0:
                msg_item.setForeground(QColor("#ff6600"))  # 红色
            elif  diff<0:
                msg_item.setForeground(QColor("#ffffff"))  # 白色
            else:
                msg_item.setForeground(QColor("#66ff66"))  # 绿色
            self.table.setItem(row, 3, msg_item)
            
            # 4: Text (可编辑)
            text_item = QTableWidgetItem(item['text'])
            text_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self.table.setItem(row, 4, text_item)

    def _load_remaining(self, start_row):
        """延迟加载剩余行"""
        total = len(self.queue_tts)
        batch_size = 500  # 更大批次
        
        end_row = min(start_row + batch_size, total)
        self._batch_fill(start_row, end_row)
        
        if end_row < total:
            QTimer.singleShot(0, lambda: self._load_remaining(end_row))

    def _on_cell_double_clicked(self, row, col):
        """单元格双击"""
        if col == 1:  # Start 列 - 减0.1秒
            self._adjust_time(row, 'start', -100)
        elif col == 2:  # End 列 - 加0.1秒
            self._adjust_time(row, 'end', 100)
        elif col == 4:  # Text 列 - 编辑
            self.table.editItem(self.table.item(row, col))

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.table.itemAt(pos)
        if not item:
            return
        
        row = item.row()
        col = item.column()
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a2a;
                color: #ccc;
                border: 1px solid #444;
            }
            QMenu::item:selected {
                background-color: #0066cc;
            }
        """)
        
        if col == 1:  # Start 列
            menu.addAction(tr("Start -0.1s"), lambda: self._adjust_time(row, 'start', -100))
            menu.addAction(tr("Start +0.1s"), lambda: self._adjust_time(row, 'start', 100))
            menu.addSeparator()
            menu.addAction(tr("Custom adjust..."), lambda: self._custom_adjust(row, 'start'))
            
        elif col == 2:  # End 列
            menu.addAction(tr("End -0.1s"), lambda: self._adjust_time(row, 'end', -100))
            menu.addAction(tr("End +0.1s"), lambda: self._adjust_time(row, 'end', 100))
            menu.addSeparator()
            menu.addAction(tr("Custom adjust..."), lambda: self._custom_adjust(row, 'end'))
            
        elif col == 3:  # Status 列
            menu.addAction(tr("Trial dubbing"), lambda: self._listen(row))
            menu.addAction(tr("Re-dubbed"), lambda: self._redub(row))
            
        elif col == 4:  # Text 列
            menu.addAction(tr("Trial dubbing"), lambda: self._listen(row))
            menu.addAction(tr("Re-dubbed"), lambda: self._redub(row))
            menu.addSeparator()
            menu.addAction(tr("Clear text"), lambda: self._clear_text(row))
        
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _custom_adjust(self, row, mode):
        """自定义时间调整"""
        ms, ok = QInputDialog.getInt(
            self, tr("Adjust time"), 
            tr("Enter milliseconds (positive or negative):"),
            0, -10000, 10000, 100
        )
        if ok:
            self._adjust_time(row, mode, ms)

    def _clear_text(self, row):
        """清空文本"""
        text_item = self.table.item(row, 4)
        if text_item:
            text_item.setText("")
            self.queue_tts[row]['text'] = ""

    def _adjust_time(self, row, mode, offset_ms):
        """调整时间"""
        self.stop_countdown()
        
        if not (0 <= row < len(self.queue_tts)):
            return

        item = self.queue_tts[row]
        prev_item = self.queue_tts[row - 1] if row > 0 else None
        next_item = self.queue_tts[row + 1] if row < len(self.queue_tts) - 1 else None

        buffer = 10

        if mode == 'start':
            new_start = item['start_time'] + offset_ms

            limit_min = 0
            if prev_item:
                limit_min = prev_item['end_time'] + buffer

            if new_start < limit_min:
                self._show_error(tr("Cannot overlap with previous subtitle"))
                return

            limit_max = item['end_time'] - buffer
            if new_start > limit_max:
                self._show_error(tr("Start time cannot exceed End time"))
                return

            item['start_time'] = new_start
            item['start_time_source'] = new_start
            item['startraw'] = self._ms_to_fmt(new_start)

        elif mode == 'end':
            new_end = item['end_time'] + offset_ms

            limit_min = item['start_time'] + buffer
            if new_end < limit_min:
                self._show_error(tr("End time cannot be less than Start time"))
                return

            limit_max = float('inf')
            if next_item:
                limit_max = next_item['start_time'] - buffer

            if new_end > limit_max:
                self._show_error(tr("Cannot overlap with next subtitle"))
                return

            item['end_time'] = new_end
            item['end_time_source'] = new_end
            item['endraw'] = self._ms_to_fmt(new_end)

        # 更新显示
        self._refresh_row(row)

    def _ms_to_fmt(self, ms):
        """毫秒转时间格式"""
        seconds, milliseconds = divmod(ms, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"

    def _refresh_row(self, row):
        """刷新指定行"""
        item = self.queue_tts[row]
        
        # 更新Start
        start_item = self.table.item(row, 1)
        if start_item:
            start_item.setText(f"{item['startraw']}")
        
        # 更新End
        end_item = self.table.item(row, 2)
        if end_item:
            end_item.setText(f"{item['endraw']}")
        
        # 重新计算状态
        duration = (item['end_time'] - item['start_time']) / 1000.0
        dubbing = float(item.get('dubbing_s', 0.0))
        diff = round(dubbing - duration, 3)
        
        if dubbing <= 0.0:
            msg = tr('No audio')
        elif diff > 0:
            msg = f'[{dubbing}s]{tr("Exceeded")}{diff}s'
        elif diff < 0:
            msg = f'[{dubbing}s]{tr("Shortened")}{abs(diff)}s'
        else:
            msg = f'{dubbing}s'
        
        msg_item = self.table.item(row, 3)
        if msg_item:
            msg_item.setText(msg)
            if dubbing <= 0:
                msg_item.setForeground(QColor("#ff4d4d"))
            elif diff>0:
                msg_item.setForeground(QColor("#ff6600"))
            elif diff<0:
                msg_item.setForeground(QColor("#ffffff"))
            else:
                msg_item.setForeground(QColor("#66ff66"))

    def _listen(self, row):
        """试听"""
        self.stop_countdown()
        item = self.queue_tts[row]
        filename = item['filename']
        
        if not tools.vail_file(filename):
            QMessageBox.information(self, tr("The audio file does not exist"), tr("The audio file does not exist"))
            return
        
        threading.Thread(target=tools.pygameaudio, args=(filename,), daemon=True).start()

    def _redub(self, row):
        """重配音"""
        self.stop_countdown()
        
        # 删除旧文件
        try:
            Path(self.queue_tts[row]['filename']).unlink(missing_ok=True)
        except Exception as e:
            print(f"删除文件失败: {e}")
        
        # 重置时长
        self.queue_tts[row]['dubbing_s'] = 0.0
        self._refresh_row(row)
        
        # 获取当前文本
        text_item = self.table.item(row, 4)
        current_text = text_item.text() if text_item else self.queue_tts[row]['text']
        
        # 准备TTS参数
        tts_dict = self.queue_tts[row].copy()
        tts_dict['text'] = current_text
        
        # 启动后台线程
        task = ReDubb(parent=self, idx=row, tts_dict=tts_dict, language=self.language)
        task.uito.connect(self._on_redub_finished, type=Qt.ConnectionType.QueuedConnection)
        task.start()

    def _on_redub_finished(self, msg):
        """重配音完成回调"""
        print(f'{msg=}')
        if msg.startswith("ok:"):
            idx = int(msg[3:])
            item = self.queue_tts[idx]
            
            # 读取新文件时长
            try:
                if Path(item['filename']).exists():
                    item['dubbing_s'] = len(AudioSegment.from_file(item['filename'])) / 1000.0
                else:
                    item['dubbing_s'] = 0.0
            except Exception:
                item['dubbing_s'] = 0.0
            
            # 更新状态显示
            self._refresh_row(idx)
            
            # 播放新音频
            threading.Thread(target=tools.pygameaudio, args=(item['filename'],), daemon=True).start()
        else:
            QMessageBox.information(self, 'Error', msg)

    def _show_error(self, msg):
        """显示错误"""
        if hasattr(self, 'prompt_label') and self.prompt_label:
            original_text = self.prompt_label.text()
            original_style = self.prompt_label.styleSheet()
            
            self.prompt_label.setText(f"Error: {msg}")
            self.prompt_label.setStyleSheet("font-size:16px; font-weight:bold; color:red;")
            
            def restore():
                if hasattr(self, 'prompt_label') and self.prompt_label:
                    self.prompt_label.setText(original_text)
                    self.prompt_label.setStyleSheet(original_style)
            QTimer.singleShot(2000, restore)

    def cancel_and_close(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        self.reject()

    def update_countdown(self):
        self.count_down -= 1
        if hasattr(self, 'stop_button') and self.stop_button:
            self.stop_button.setText(f"{tr('Click here to stop the countdown')}({self.count_down})")

        if self.count_down <= 0:
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
            self.timer = None

        if hasattr(self, 'prompt_label') and self.prompt_label:
            try:
                self.prompt_label.deleteLater()
            except RuntimeError:
                pass
            self.prompt_label = None

        if hasattr(self, 'stop_button') and self.stop_button:
            try:
                self.stop_button.deleteLater()
            except RuntimeError:
                pass
            self.stop_button = None

    def save_and_close(self):
        self.save_button.setDisabled(True)
        
        for i, item in enumerate(self.queue_tts):
            # 获取最新文本
            text_item = self.table.item(i, 4)
            text = text_item.text().strip() if text_item else item['text'].strip()
            item['text'] = text
            
            # 删除空文本对应的音频文件
            if not text:
                Path(item['filename']).unlink(missing_ok=True)
            
            # 清理临时字段
            for key in ['_duration', '_msg', '_time_str']:
                item.pop(key, None)
        
        try:
            Path(f'{self.cache_folder}/queue_tts.json').write_text(json.dumps(self.queue_tts), encoding="utf-8")
        except Exception:
            pass
        
        self.accept()