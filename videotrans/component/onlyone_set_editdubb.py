import threading
import json
import traceback
from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QScrollArea, QWidget, QGroupBox, QFrame, QMessageBox,
    QApplication, QProgressBar, QListView, QStyle, QStyledItemDelegate,
    QStyleOptionButton, QToolTip, QAbstractItemView
)

from PySide6.QtGui import (
    QIcon, QPen, QColor, QBrush, QPalette, QPainter, 
    QFontMetrics, QCursor
)
from PySide6.QtCore import (
    Qt, QTimer, QSize, QThread, Signal, QAbstractListModel,
    QModelIndex, QRect, QEvent
)

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
            config.box_tts = 'ing'
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
# 1. 数据模型
# ===========================================================================
class DubbingModel(QAbstractListModel):
    RoleRawData = Qt.UserRole + 1
    RoleTimeStr = Qt.UserRole + 2
    RoleTipStr  = Qt.UserRole + 3
    RoleMsgOnly = Qt.UserRole + 4

    def __init__(self, data_list=None, parent=None):
        super().__init__(parent)
        self._data = data_list or []

        # 预计算时间轴字符串
        for item in self._data:
            self._update_time_info(item)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    @staticmethod
    def ms_to_fmt(ms):
        """将毫秒转换为 00:00:00,000 格式"""
        seconds, milliseconds = divmod(ms, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"

    def _update_time_info(self, item):
        """计算并缓存显示用的字符串"""
        # 直接使用缓存的 dubbing_s，避免 IO 操作
        try:
            dubbing = float(item.get('dubbing_s', 0.0))
            
            duration = (item['end_time'] - item['start_time']) / 1000.0
            diff = round(dubbing - duration, 3)

            if dubbing <= 0.0:
                # 认为是文件不存在或无效
                msg = tr('The audio file does not exist')
                labeltip = msg
            elif diff > 0:
                msg = f'{tr("Dubbing files")}{dubbing}s <{tr("Exceeded")}> {diff}s ({tr("Alignment needs accelerated")} {round(dubbing / duration, 2)}x)'
                labeltip = f'{tr("Dubbing files")} <{tr("Exceeded")}> {tr("Original duration")} {diff}s'
            elif diff < 0:
                msg = f'{tr("Dubbing files")}{dubbing}s <{tr("Shortened")}> {abs(diff)}s'
                labeltip = f'{tr("Dubbing files")} <{tr("Shortened")}> {tr("Original duration")} {abs(diff)}s'
            else:
                msg = f'{tr("Dubbing files")}={tr("Original duration")}'
                labeltip = f'{tr("Dubbing files")}={tr("Original duration")}'

            labeltex = f"[{item['line']}]  {item['startraw']}->{item['endraw']}({duration}s)  {msg}"

            item['__display_text'] = labeltex
            item['__display_tip'] = labeltip
            item['__display_msg_only'] = msg
        except Exception:
            item['__display_text'] = f"[{item['line']}] Error loading audio info"
            item['__display_tip'] = "Error"
            item['__display_msg_only'] = "Error"

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None
        item = self._data[index.row()]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return item['text']
        if role == self.RoleRawData:
            return item
        if role == self.RoleTimeStr:
            return item.get('__display_text', '')
        if role == self.RoleTipStr:
            return item.get('__display_tip', '')
        if role == self.RoleMsgOnly:
            return item.get('__display_msg_only', '')
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            self._data[index.row()]['text'] = value
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        return False

    def refresh_item(self, row):
        """外部调用刷新"""
        if 0 <= row < len(self._data):
            self._update_time_info(self._data[row])
            idx = self.index(row)
            self.dataChanged.emit(idx, idx, [Qt.DisplayRole, self.RoleTimeStr, self.RoleTipStr, self.RoleMsgOnly])

    def get_all_data(self):
        return self._data

    def adjust_time(self, row, mode, offset_ms) -> (bool, str):
        """
        调整时间
        :return: (success: bool, message: str)
        """
        if not (0 <= row < len(self._data)):
            return False, "Invalid Index"

        item = self._data[row]
        prev_item = self._data[row - 1] if row > 0 else None
        next_item = self._data[row + 1] if row < len(self._data) - 1 else None

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
            item['startraw'] = self.ms_to_fmt(new_start)
        
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
            item['endraw'] = self.ms_to_fmt(new_end)

        self.refresh_item(row)
        return True, ""


# ===========================================================================
# 2. 委托
# ===========================================================================

class DubbingDelegate(QStyledItemDelegate):
    btn_redub_clicked = Signal(int)
    btn_listen_clicked = Signal(int)
    btn_adjust_time = Signal(int, str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_height = 80
        self._pressed_data = None

    def _get_layout_metrics(self, rect, item, font_metrics):
        """统一计算各部分坐标，供 paint/editorEvent/helpEvent 使用"""
        if item is None:
            return None

        top_row_y = rect.top() + 5
        left_margin = rect.left() + 5
        
        # 1. 行号
        line_str = f"[{item['line']}] "
        w_line = font_metrics.horizontalAdvance(line_str)
        
        current_x = left_margin + w_line + 5
        
        # 2. Start 组
        w_btn = 20
        w_txt = 26
        s_minus_rect = QRect(current_x, top_row_y + 3, w_btn, 20)
        s_plus_rect = QRect(current_x + w_btn + w_txt, top_row_y + 3, w_btn, 20)
        s_group_rect = s_minus_rect.united(s_plus_rect).adjusted(0,0,0,0)
        
        current_x = s_plus_rect.right() + 10
        
        # 3. 时间文本
        duration = (item['end_time'] - item['start_time']) / 1000.0
        time_info_str = f"{item['startraw']} -> {item['endraw']} ({duration:.2f}s)"
        w_time = font_metrics.horizontalAdvance(time_info_str)
        time_rect = QRect(current_x, top_row_y, w_time, 26)
        
        current_x += w_time + 10
        
        # 4. End 组
        e_minus_rect = QRect(current_x, top_row_y + 3, w_btn, 20)
        e_plus_rect = QRect(current_x + w_btn + w_txt, top_row_y + 3, w_btn, 20)
        e_group_rect = e_minus_rect.united(e_plus_rect).adjusted(0,0,0,0)

        current_x = e_plus_rect.right() + 15

        # 5. Msg 区域
        msg_start_x = current_x

        # 6. 右侧按钮
        btn_y = top_row_y + 2
        btn_h = 26
        btn_w = 90
        btn_listen_rect = QRect(rect.right() - btn_w - 5, btn_y, btn_w, btn_h)
        btn_redub_rect = QRect(btn_listen_rect.left() - btn_w - 5, btn_y, btn_w, btn_h)

        # 7. 输入框
        bottom_row_y = rect.top() + 40
        input_rect = QRect(left_margin, bottom_row_y, rect.width() - 10, 30)

        return {
            'line_rect': QRect(left_margin, top_row_y, w_line, 26),
            's_minus': s_minus_rect,
            's_plus': s_plus_rect,
            's_group': s_group_rect,
            's_text_rect': QRect(s_minus_rect.right(), top_row_y + 3, w_txt, 20),
            'time_rect': time_rect,
            'time_str': time_info_str,
            'e_minus': e_minus_rect,
            'e_plus': e_plus_rect,
            'e_group': e_group_rect,
            'e_text_rect': QRect(e_minus_rect.right(), top_row_y + 3, w_txt, 20),
            'msg_x': msg_start_x,
            'btn_listen': btn_listen_rect,
            'btn_redub': btn_redub_rect,
            'input_rect': input_rect
        }

    def helpEvent(self, event, view, option, index):
        # 1. 安全检查
        if not index.isValid():
            return False
        
        if event.type() == QEvent.Type.ToolTip:
            item = index.data(DubbingModel.RoleRawData)
            # 2. 空值检查
            if item is None:
                return False
                
            fm = option.widget.fontMetrics()
            metrics = self._get_layout_metrics(option.rect, item, fm)
            if not metrics:
                return False
                
            pos = event.pos()
            
            if metrics['s_group'].contains(pos):
                QToolTip.showText(event.globalPos(), tr("Click the + or - symbols to move the start time of this subtitle"))
                return True
            
            if metrics['e_group'].contains(pos):
                QToolTip.showText(event.globalPos(), tr("Click the + or - symbols to move the end time of this subtitle"))
                return True

            if metrics['input_rect'].contains(pos):
                QToolTip.showText(event.globalPos(), tr("Double-click the text box to edit the subtitles"))
                return True

        return super().helpEvent(event, view, option, index)

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.row_height)

    def paint(self, painter, option, index):
        if not index.isValid():
            return

        item = index.data(DubbingModel.RoleRawData)
        if item is None:
            return

        msg_str = index.data(DubbingModel.RoleMsgOnly)
        text = item['text']

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # 获取坐标布局
        metrics = self._get_layout_metrics(option.rect, item, painter.fontMetrics())
        if not metrics:
            painter.restore()
            return

        # 字体颜色
        if float(item.get('dubbing_s', 0)) <= 0:
            text_color = QColor("yellow")
        elif option.state & QStyle.StateFlag.State_Selected:
            text_color = option.palette.highlightedText().color()
        else:
            text_color = option.palette.text().color()
        
        painter.setPen(text_color)

        # A. 行号
        line_str = f"[{item['line']}] "
        painter.drawText(metrics['line_rect'], Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line_str)

        # B. Start 调节组
        is_s_minus_pressed = (self._pressed_data == (index.row(), 's-'))
        is_s_plus_pressed = (self._pressed_data == (index.row(), 's+'))
        
        self._draw_mini_button(painter, metrics['s_minus'], "-", option, is_s_minus_pressed)
        painter.setPen(text_color)
        painter.drawText(metrics['s_text_rect'], Qt.AlignmentFlag.AlignCenter, "0.1")
        self._draw_mini_button(painter, metrics['s_plus'], "+", option, is_s_plus_pressed)

        # C. 时间文本
        painter.setPen(text_color)
        painter.drawText(metrics['time_rect'], Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, metrics['time_str'])

        # D. End 调节组
        is_e_minus_pressed = (self._pressed_data == (index.row(), 'e-'))
        is_e_plus_pressed = (self._pressed_data == (index.row(), 'e+'))

        self._draw_mini_button(painter, metrics['e_minus'], "-", option, is_e_minus_pressed)
        painter.setPen(text_color)
        painter.drawText(metrics['e_text_rect'], Qt.AlignmentFlag.AlignCenter, "0.1")
        self._draw_mini_button(painter, metrics['e_plus'], "+", option, is_e_plus_pressed)

        # E. Msg 信息
        right_limit = option.rect.width() - 200
        msg_width = right_limit - metrics['msg_x']
        if msg_width > 0:
            msg_rect = QRect(metrics['msg_x'], metrics['time_rect'].top(), msg_width, 26)
            elided_msg = painter.fontMetrics().elidedText(msg_str, Qt.TextElideMode.ElideRight, msg_width)
            painter.setPen(text_color)
            painter.drawText(msg_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_msg)

        # 右侧大按钮
        is_listen_pressed = (self._pressed_data == (index.row(), 'listen'))
        is_redub_pressed = (self._pressed_data == (index.row(), 'redub'))

        self._draw_button(painter, metrics['btn_listen'], tr("Trial dubbing"), option, pressed=is_listen_pressed)
        self._draw_button(painter, metrics['btn_redub'], tr("Re-dubbed"), option, pressed=is_redub_pressed)

        # 底部输入框
        input_rect = metrics['input_rect']
        input_bg = option.palette.base().color()
        border_col = QColor("#455364")
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QBrush(input_bg))
        painter.setPen(QPen(border_col))
        painter.drawRoundedRect(input_rect, 4, 4)

        painter.setPen(option.palette.windowText().color())
        text_draw_rect = input_rect.adjusted(4, 0, -4, 0)
        elided_text = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, text_draw_rect.width())
        painter.drawText(text_draw_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_text)

        painter.restore()

    def _draw_mini_button(self, painter, rect, text, option, pressed=False):
        painter.save()
        if pressed:
            bg_color = QColor("#666666")
            text_color = QColor("#ffffff")
        else:
            bg_color = QColor("#3A4550")
            text_color = QColor("#aaaaaa")
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 2, 2)
        
        painter.setPen(text_color)
        if pressed:
            painter.drawText(rect.adjusted(1,1,0,0), Qt.AlignmentFlag.AlignCenter, text)
        else:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def _draw_button(self, painter, rect, text, option, pressed=False):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if pressed:
            bg_color = QColor("#222222")
            border_color = QColor("#222222")
            text_color = QColor("#aaaaaa")
        else:
            bg_color = QColor("#455364")
            border_color = QColor("#455364")
            text_color = QColor("#DFE1E2")
        if option.state & QStyle.StateFlag.State_Selected and not pressed:
            bg_color = QColor("#19232D")
            border_color = QColor("#19232D")
            text_color = QColor("#ffffff")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(text_color)
        if pressed:
            rect.translate(1, 1)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if not index.isValid():
            return False
            
        item = index.data(DubbingModel.RoleRawData)
        if item is None:
            return False

        fm = option.widget.fontMetrics()
        metrics = self._get_layout_metrics(option.rect, item, fm)
        if not metrics:
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                pos = event.pos()
                targets = [
                    (metrics['btn_listen'], 'listen'),
                    (metrics['btn_redub'], 'redub'),
                    (metrics['s_minus'], 's-'),
                    (metrics['s_plus'], 's+'),
                    (metrics['e_minus'], 'e-'),
                    (metrics['e_plus'], 'e+')
                ]
                for rect_area, btn_id in targets:
                    if rect_area.contains(pos):
                        option.widget.setFocus()
                        self._pressed_data = (index.row(), btn_id)
                        if btn_id == 'listen':
                            self.btn_listen_clicked.emit(index.row())
                        elif btn_id == 'redub':
                            self.btn_redub_clicked.emit(index.row())
                        elif btn_id == 's-':
                            self.btn_adjust_time.emit(index.row(), 'start', -100)
                        elif btn_id == 's+':
                            self.btn_adjust_time.emit(index.row(), 'start', 100)
                        elif btn_id == 'e-':
                            self.btn_adjust_time.emit(index.row(), 'end', -100)
                        elif btn_id == 'e+':
                            self.btn_adjust_time.emit(index.row(), 'end', 100)
                        option.widget.viewport().update(option.rect)
                        return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                if self._pressed_data:
                    self._pressed_data = None
                    option.widget.viewport().update(option.rect)
                    return True
        elif event.type() == QEvent.Type.MouseButtonDblClick:
            if metrics['input_rect'].contains(event.pos()):
                view = option.widget
                if hasattr(view, 'edit'):
                    view.edit(index)
                return True
            if any(r.contains(event.pos()) for r in [metrics['btn_listen'], metrics['btn_redub'], metrics['s_group'], metrics['e_group']]):
                return True
        return super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.ItemDataRole.EditRole)
        editor.setText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        rect = option.rect
        editor.setGeometry(rect.left() + 5, rect.top() + 40, rect.width() - 10, 30)

# ===========================================================================
# 3. 主窗口
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
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        self.setWindowFlags(Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMaximizeButtonHint)

        self.count_down = int(float(config.settings.get('countdown_sec', 1)))

        main_layout = QVBoxLayout(self)

        hstop = QHBoxLayout()
        self.prompt_label = QLabel(tr("You can check the voiceover here, or modify the text and re-encode the voiceover. Please stop the countdown before proceeding"))
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

        prompt_label2 = QLabel(tr("To remove a voiceover, simply clear the text. A voiceover duration of 0 seconds indicates a failed voiceover"))
        prompt_label2.setAlignment(Qt.AlignCenter)
        prompt_label2.setWordWrap(True)
        main_layout.addWidget(prompt_label2)

        self.loading_widget = QWidget()
        load_layout = QVBoxLayout(self.loading_widget)
        self.loading_label = QLabel(tr('The subtitle editing interface is rendering'), self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        load_layout.addWidget(self.loading_label)
        load_layout.addWidget(self.progress_bar)

        main_layout.addWidget(self.loading_widget)

        self.list_view = QListView()
        self.list_view.setUniformItemSizes(True)
        self.list_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_view.setVisible(False)
        self.list_view.setTabKeyNavigation(True)
        self.list_view.setSpacing(2)
        main_layout.addWidget(self.list_view)

        self.save_button = QPushButton(tr("nextstep"))
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setMinimumSize(QSize(400, 35))
        self.save_button.clicked.connect(self.save_and_close)
        cancel_button = QPushButton(tr("Terminate this mission"))
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMaximumSize(QSize(200, 30))
        cancel_button.setStyleSheet("""background-color:transparent""")
        cancel_button.clicked.connect(self.cancel_and_close)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(cancel_button)
        bottom_layout.addStretch()

        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)
        QTimer.singleShot(100, self.lazy_load_interface)

    def lazy_load_interface(self):
        self.create_subtitle_assignment_area()
        QApplication.processEvents()
        def _finish():
            self.list_view.setVisible(True)
            self.loading_widget.deleteLater()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)
            self._active()
        QTimer.singleShot(50,_finish)

    def _active(self):
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

    def create_container(self):
        pass

    def create_subtitle_assignment_area(self):
        self.model = DubbingModel(self.queue_tts, self)
        self.delegate = DubbingDelegate(self.list_view)
        
        self.delegate.btn_listen_clicked.connect(self.listen)
        self.delegate.btn_redub_clicked.connect(self.re_dubb)
        self.delegate.btn_adjust_time.connect(self.adjust_subtitle_time)

        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.progress_bar.setValue(100)
        self.loading_label.setText(tr("Data is ready rendering is in progress"))
        QApplication.processEvents()

    def adjust_subtitle_time(self, row, mode, offset):
        self.stop_countdown()
        
        success, msg = self.model.adjust_time(row, mode, offset)
        if not success:
            QToolTip.showText(QCursor.pos(), msg, self.list_view, QRect(), 3000)
            
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

    def listen(self, i):
        self.stop_countdown()
        item = self.queue_tts[i]
        filename = item['filename']
        if not tools.vail_file(filename):
            QMessageBox.information(self, tr("The audio file does not exist"), tr("The audio file does not exist"))
            return
        threading.Thread(target=tools.pygameaudio, args=(filename,),daemon=True).start()

    def re_dubb(self, i):
        self.stop_countdown()
        print(f'从新配音 {i=}')
        # 删除旧文件
        Path(self.queue_tts[i]['filename']).unlink(missing_ok=True)
        # 重置缓存的时长，并立即刷新UI显示
        self.queue_tts[i]['dubbing_s'] = 0.0
        self.model.refresh_item(i)

        tts_dict = self.queue_tts[i]
        idx = self.model.index(i)
        current_text = self.model.data(idx, Qt.EditRole)
        tts_dict['text'] = current_text
        task = ReDubb(parent=self, idx=i, tts_dict=tts_dict, language=self.language)
        task.uito.connect(self.feed)
        task.start()

    def feed(self, msg):
        print(f'{msg=}')
        if msg.startswith("ok:"):
            idx = int(msg[3:])
            item = self.queue_tts[idx]
            
            # 仅在配音完成后，读取一次文件，更新缓存
            try:
                if Path(item['filename']).exists():
                    item['dubbing_s'] = len(AudioSegment.from_file(item['filename'])) / 1000.0
                else:
                    item['dubbing_s'] = 0.0
            except Exception:
                item['dubbing_s'] = 0.0

            self.model.refresh_item(idx)
            threading.Thread(target=tools.pygameaudio, args=(item['filename'],),daemon=True).start()
        else:
            QMessageBox.information(self, 'Error', msg)

    def get_timeline_str(self, item):
        pass

    def save_and_close(self):
        self.save_button.setDisabled(True)
        for i, item in enumerate(self.queue_tts):
            text = item['text'].strip()
            if not text:
                Path(item['filename']).unlink(missing_ok=True)
            try:
                del item['__display_text']
                del item['__display_tip']
                del item['__display_msg_only']
            except Exception:
                pass
        try:
            Path(f'{self.cache_folder}/queue_tts.json').write_text(json.dumps(self.queue_tts), encoding="utf-8")
        except Exception:
            pass
        self.accept()