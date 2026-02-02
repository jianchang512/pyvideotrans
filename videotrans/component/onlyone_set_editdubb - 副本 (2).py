import threading
import json
import traceback
from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QWidget, QProgressBar, QApplication, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QToolTip
)
from PySide6.QtGui import QIcon, QDesktopServices, QColor, QCursor
from PySide6.QtCore import Qt, QTimer, QSize, QUrl, QThread, Signal, QRect

from pydub import AudioSegment
from videotrans.configure.config import tr
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


# ===========================================================================
# 2. 主窗口 - 极致性能版
# ===========================================================================
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
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setMinimumWidth(int(parent.width*0.95))
        self.setMinimumHeight(int(parent.height*0.95))
        self.setWindowFlags(
        Qt.WindowStaysOnTopHint |       # 2. 始终在最顶层
            Qt.WindowTitleHint |            # 3. 显示标题栏
            Qt.CustomizeWindowHint |        # 4. 允许自定义标题栏按钮（关键！否则OS会强制加关闭按钮）
            Qt.WindowMaximizeButtonHint     # 5. 只加最大化按钮，不加关闭按钮
        )

        self.count_down = int(float(config.settings.get('countdown_sec', 1)))

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

        prompt_label2 = QLabel(tr("To remove a voiceover, simply clear the text. A voiceover duration of 0 seconds indicates a failed voiceover")+"\n"+tr('Shortened and Exceeded mean'))
        prompt_label2.setAlignment(Qt.AlignCenter)
        prompt_label2.setWordWrap(True)
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
            # 1. 创建 QTableWidget
            # 列：Line | Start- | Start+ | Time | End- | End+ | Msg | Listen | Redub | Text
            self.table.setColumnCount(10)
            self.table.setHorizontalHeaderLabels([
                tr("Line"), "-", "+", tr("Time Axis"), "-", "+", tr("Status"), 
                tr("Trial dubbing"), tr("Re-dubbed"), tr("Subtitle Text")
            ])
            
            # 2. 【极致性能配置】
            self.table.setShowGrid(False)
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
            v_header.setDefaultSectionSize(28)
            
            # 水平表头
            h_header = self.table.horizontalHeader()
            h_header.setSectionResizeMode(0, QHeaderView.Fixed)  # Line
            h_header.setSectionResizeMode(1, QHeaderView.Fixed)  # Start-
            h_header.setSectionResizeMode(2, QHeaderView.Fixed)  # Start+
            h_header.setSectionResizeMode(3, QHeaderView.Fixed)  # Time
            h_header.setSectionResizeMode(4, QHeaderView.Fixed)  # End-
            h_header.setSectionResizeMode(5, QHeaderView.Fixed)  # End+
            h_header.setSectionResizeMode(6, QHeaderView.Fixed)  # Status
            h_header.setSectionResizeMode(7, QHeaderView.Fixed)  # Listen
            h_header.setSectionResizeMode(8, QHeaderView.Fixed)  # Redub
            h_header.setSectionResizeMode(9, QHeaderView.Stretch)  # Text
            
            # 设置列宽
            self.table.setColumnWidth(0, 50)   # Line
            self.table.setColumnWidth(1, 30)   # Start-
            self.table.setColumnWidth(2, 30)   # Start+
            self.table.setColumnWidth(3, 220)  # Time
            self.table.setColumnWidth(4, 30)   # End-
            self.table.setColumnWidth(5, 30)   # End+
            self.table.setColumnWidth(6, 200)  # Status
            self.table.setColumnWidth(7, 80)   # Listen
            self.table.setColumnWidth(8, 80)   # Redub
            
            # 极简样式
            self.table.setStyleSheet("""
                QTableWidget {
                    background-color: #1e1e1e;
                    color: #cccccc;
                    border: none;
                    gridline-color: #333333;
                }
                QTableWidget::item {
                    padding: 2px 4px;
                    border: none;
                }
                QTableWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QHeaderView::section {
                    background-color: #2b2b2b;
                    color: #dddddd;
                    border: none;
                    border-right: 1px solid #3e3e3e;
                    padding: 3px;
                    height: 24px;
                }
            """)
            
            # 3. 预计算数据
            self._precompute_data()
            
            # 4. 设置行数
            total_rows = len(self.queue_tts)
            self.table.setRowCount(total_rows)
            
            # 5. 分批填充数据
            self._batch_fill(0, min(total_rows, 100))
            
            # 6. 显示表格
            self.loading_widget.setVisible(False)
            self.table.setVisible(True)
            
            # 7. 延迟加载剩余数据
            if total_rows > 100:
                QTimer.singleShot(0, lambda: self._load_remaining(100))
            
            # 8. 连接信号
            self.table.cellClicked.connect(self._on_cell_clicked)
            self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
            self.table.itemChanged.connect(self._on_item_changed)
            
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
                msg = tr('The audio file does not exist')
            elif diff > 0:
                msg = f'{tr("Exceeded")} {diff}s'
            elif diff < 0:
                msg = f'{tr("Shortened")} {abs(diff)}s'
            else:
                msg = tr("OK")
            
            item['_duration'] = duration
            item['_msg'] = msg
            item['_time_str'] = f"{item['startraw']} -> {item['endraw']} ({duration:.1f}s)"

    def _batch_fill(self, start_row, end_row):
        """批量填充表格数据"""
        for row in range(start_row, end_row):
            item = self.queue_tts[row]
            
            # 0: Line (只读)
            line_item = QTableWidgetItem(str(item['line']))
            line_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            line_item.setData(Qt.UserRole, row)  # 存储行索引
            self.table.setItem(row, 0, line_item)
            
            # 1: Start- (按钮)
            btn_minus = QPushButton("-")
            btn_minus.setFixedSize(26, 22)
            btn_minus.setStyleSheet("QPushButton { background-color: #3A4550; color: #aaaaaa; border: none; }")
            btn_minus.setProperty("row", row)
            btn_minus.setProperty("action", "s-")
            btn_minus.clicked.connect(self._on_time_button)
            self.table.setCellWidget(row, 1, btn_minus)
            
            # 2: Start+ (按钮)
            btn_plus = QPushButton("+")
            btn_plus.setFixedSize(26, 22)
            btn_plus.setStyleSheet("QPushButton { background-color: #3A4550; color: #aaaaaa; border: none; }")
            btn_plus.setProperty("row", row)
            btn_plus.setProperty("action", "s+")
            btn_plus.clicked.connect(self._on_time_button)
            self.table.setCellWidget(row, 2, btn_plus)
            
            # 3: Time (只读)
            time_item = QTableWidgetItem(item['_time_str'])
            time_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 3, time_item)
            
            # 4: End- (按钮)
            btn_eminus = QPushButton("-")
            btn_eminus.setFixedSize(26, 22)
            btn_eminus.setStyleSheet("QPushButton { background-color: #3A4550; color: #aaaaaa; border: none; }")
            btn_eminus.setProperty("row", row)
            btn_eminus.setProperty("action", "e-")
            btn_eminus.clicked.connect(self._on_time_button)
            self.table.setCellWidget(row, 4, btn_eminus)
            
            # 5: End+ (按钮)
            btn_eplus = QPushButton("+")
            btn_eplus.setFixedSize(26, 22)
            btn_eplus.setStyleSheet("QPushButton { background-color: #3A4550; color: #aaaaaa; border: none; }")
            btn_eplus.setProperty("row", row)
            btn_eplus.setProperty("action", "e+")
            btn_eplus.clicked.connect(self._on_time_button)
            self.table.setCellWidget(row, 5, btn_eplus)
            
            # 6: Status (只读)
            msg_item = QTableWidgetItem(item['_msg'])
            msg_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            # 根据状态设置颜色
            dubbing = float(item.get('dubbing_s', 0.0))
            if dubbing <= 0:
                msg_item.setForeground(QColor("yellow"))
            self.table.setItem(row, 6, msg_item)
            
            # 7: Listen (按钮)
            btn_listen = QPushButton("\u266B")
            btn_listen.setFixedSize(70, 24)
            btn_listen.setStyleSheet("QPushButton { background-color: #455364; color: #DFE1E2; border: none; }")
            btn_listen.setProperty("row", row)
            btn_listen.clicked.connect(self._on_listen)
            self.table.setCellWidget(row, 7, btn_listen)
            
            # 8: Redub (按钮)
            btn_redub = QPushButton("\u2668")
            btn_redub.setFixedSize(70, 24)
            btn_redub.setStyleSheet("QPushButton { background-color: #455364; color: #DFE1E2; border: none; }")
            btn_redub.setProperty("row", row)
            btn_redub.clicked.connect(self._on_redub)
            self.table.setCellWidget(row, 8, btn_redub)
            
            # 9: Text (可编辑)
            text_item = QTableWidgetItem(item['text'])
            text_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self.table.setItem(row, 9, text_item)

    def _load_remaining(self, start_row):
        """延迟加载剩余行"""
        total = len(self.queue_tts)
        batch_size = 200
        
        end_row = min(start_row + batch_size, total)
        self._batch_fill(start_row, end_row)
        
        if end_row < total:
            QTimer.singleShot(0, lambda: self._load_remaining(end_row))

    def _on_time_button(self):
        """时间调节按钮点击"""
        btn = self.sender()
        if not btn:
            return
        
        row = btn.property("row")
        action = btn.property("action")
        
        self.stop_countdown()
        
        mode = 'start' if action in ('s-', 's+') else 'end'
        offset = 100 if action in ('s+', 'e+') else -100
        
        success, msg = self._adjust_time(row, mode, offset)
        if not success:
            QToolTip.showText(QCursor.pos(), msg, self.table, QRect(), 3000)
            self._show_error_prompt(msg)

    def _adjust_time(self, row, mode, offset_ms):
        """调整时间"""
        if not (0 <= row < len(self.queue_tts)):
            return False, "Invalid Index"

        item = self.queue_tts[row]
        prev_item = self.queue_tts[row - 1] if row > 0 else None
        next_item = self.queue_tts[row + 1] if row < len(self.queue_tts) - 1 else None

        buffer = 10  # 10ms buffer

        if mode == 'start':
            new_start = item['start_time'] + offset_ms

            limit_min = 0
            if prev_item:
                limit_min = prev_item['end_time'] + buffer

            if new_start < limit_min:
                return False, tr("Cannot overlap with previous subtitle")

            limit_max = item['end_time'] - buffer
            if new_start > limit_max:
                return False, tr("Start time cannot exceed End time")

            item['start_time'] = new_start
            item['start_time_source'] = new_start
            item['startraw'] = self._ms_to_fmt(new_start)

        elif mode == 'end':
            new_end = item['end_time'] + offset_ms

            limit_min = item['start_time'] + buffer
            if new_end < limit_min:
                return False, tr("End time cannot be less than Start time")

            limit_max = float('inf')
            if next_item:
                limit_max = next_item['start_time'] - buffer

            if new_end > limit_max:
                return False, tr("Cannot overlap with next subtitle")

            item['end_time'] = new_end
            item['end_time_source'] = new_end
            item['endraw'] = self._ms_to_fmt(new_end)

        # 更新显示
        self._refresh_row(row)
        return True, ""

    def _ms_to_fmt(self, ms):
        """毫秒转时间格式"""
        seconds, milliseconds = divmod(ms, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"

    def _refresh_row(self, row):
        """刷新指定行的显示"""
        item = self.queue_tts[row]
        
        # 重新计算时间字符串
        duration = (item['end_time'] - item['start_time']) / 1000.0
        time_str = f"{item['startraw']} -> {item['endraw']} ({duration:.1f}s)"
        
        # 更新Time列
        time_item = self.table.item(row, 3)
        if time_item:
            time_item.setText(time_str)

    def _on_listen(self):
        """试听按钮"""
        btn = self.sender()
        if not btn:
            return
        
        row = btn.property("row")
        self.stop_countdown()
        
        item = self.queue_tts[row]
        filename = item['filename']
        
        if not tools.vail_file(filename):
            QMessageBox.information(self, tr("The audio file does not exist"), tr("The audio file does not exist"))
            return
        
        threading.Thread(target=tools.pygameaudio, args=(filename,), daemon=True).start()

    def _on_redub(self):
        """重配音按钮"""
        btn = self.sender()
        if not btn:
            return
        
        row = btn.property("row")
        self.stop_countdown()
        
        # 删除旧文件
        try:
            Path(self.queue_tts[row]['filename']).unlink(missing_ok=True)
        except Exception as e:
            print(f"删除文件失败: {e}")
        
        # 重置时长
        self.queue_tts[row]['dubbing_s'] = 0.0
        self._update_status(row)
        
        # 获取当前文本
        text_item = self.table.item(row, 9)
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
            self._update_status(idx)
            
            # 播放新音频
            threading.Thread(target=tools.pygameaudio, args=(item['filename'],), daemon=True).start()
        else:
            QMessageBox.information(self, 'Error', msg)

    def _update_status(self, row):
        """更新状态列"""
        item = self.queue_tts[row]
        duration = (item['end_time'] - item['start_time']) / 1000.0
        dubbing = float(item.get('dubbing_s', 0.0))
        diff = round(dubbing - duration, 3)
        
        if dubbing <= 0.0:
            msg = tr('The audio file does not exist')
        elif diff > 0:
            msg = f'{tr("Exceeded")} {diff}s'
        elif diff < 0:
            msg = f'{tr("Shortened")} {abs(diff)}s'
        else:
            msg = tr("OK")
        
        msg_item = self.table.item(row, 6)
        if msg_item:
            msg_item.setText(msg)
            if dubbing <= 0:
                msg_item.setForeground(QColor("yellow"))
            else:
                msg_item.setForeground(QColor("#cccccc"))

    def _on_cell_clicked(self, row, col):
        """单元格点击"""
        # 点击按钮列时不做特殊处理
        if col in (1, 2, 4, 5, 7, 8):
            return

    def _on_cell_double_clicked(self, row, col):
        """单元格双击 - 进入编辑模式"""
        # 只有Text列可编辑
        if col == 9:
            self.table.editItem(self.table.item(row, col))

    def _on_item_changed(self, item):
        """文本编辑完成"""
        if item.column() == 9:
            row = item.row()
            self.queue_tts[row]['text'] = item.text()

    def _show_error_prompt(self, msg):
        """显示错误提示"""
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)

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

    def closeEvent(self, event):
        event.ignore()  # 忽略关闭请求，窗口保持不动

    def save_and_close(self):
        self.save_button.setDisabled(True)
        
        for i, item in enumerate(self.queue_tts):
            # 获取最新文本
            text_item = self.table.item(i, 9)
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