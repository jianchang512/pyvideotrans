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

from PySide6.QtGui import QIcon, QPen, QColor, QBrush, QPalette, QPainter
from PySide6.QtCore import (
    Qt, QTimer, QSize, QThread, Signal, QAbstractListModel,
    QModelIndex, QRect, QEvent
)

from pydub import AudioSegment
from videotrans.configure.config import tr
from videotrans.util import tools
from videotrans.configure import config
from videotrans import tts

# ===========================================================================
# 0. 辅助线程 (保持不变)
# ===========================================================================
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
# 1. 数据模型 (Model)
# ===========================================================================
class DubbingModel(QAbstractListModel):
    RoleRawData = Qt.UserRole + 1
    RoleTimeStr = Qt.UserRole + 2
    RoleTipStr  = Qt.UserRole + 3

    def __init__(self, data_list=None, parent=None):
        super().__init__(parent)
        self._data = data_list or []

        # 预计算时间轴字符串
        for item in self._data:
            self._update_time_info(item)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        # 允许 启用 | 选中 | 编辑
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable


    def _update_time_info(self, item):
        """计算并缓存显示用的字符串"""
        try:
            # 只有文件存在才计算，否则默认
            if Path(item['filename']).exists():
                dubbing = len(AudioSegment.from_file(item['filename'])) / 1000.0
            else:
                dubbing = 0.0

            duration = (item['end_time'] - item['start_time']) / 1000.0
            diff = round(dubbing - duration, 3)

            if dubbing == 0.0:
                msg = tr('The audio file does not exist')
                labeltip = msg
            elif diff > 0:
                msg = f'{tr("Dubbing files")}{dubbing}s > {diff}s ({tr("Alignment needs accelerated")} {round(dubbing / duration, 2)}x)'
                labeltip = f'{tr("Dubbing files")} > {tr("Original duration")} {diff}s'
            elif diff < 0:
                msg = f'{tr("Dubbing files")}{dubbing}s < {abs(diff)}s'
                labeltip = f'{tr("Dubbing files")} < {tr("Original duration")} {abs(diff)}s'
            else:
                msg = f'{tr("Dubbing files")}={tr("Original duration")}'
                labeltip = f'{tr("Dubbing files")}={tr("Original duration")}'

            labeltex = f"[{item['line']}]  {item['startraw']}->{item['endraw']}({duration}s)  {msg}"

            item['__display_text'] = labeltex
            item['__display_tip'] = labeltip
        except Exception:
            item['__display_text'] = f"[{item['line']}] Error loading audio info"
            item['__display_tip'] = "Error"

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
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            self._data[index.row()]['text'] = value
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        return False

    def refresh_item(self, row):
        """当外部逻辑修改了文件后（如重新配音），调用此方法重新计算时间信息"""
        if 0 <= row < len(self._data):
            self._update_time_info(self._data[row])
            idx = self.index(row)
            # 通知所有角色更新
            self.dataChanged.emit(idx, idx, [Qt.DisplayRole, self.RoleTimeStr, self.RoleTipStr])

    def get_all_data(self):
        return self._data

# ===========================================================================
# 2. 委托 (Delegate) - 核心修复
# ===========================================================================

class DubbingDelegate(QStyledItemDelegate):
    # 自定义信号
    btn_redub_clicked = Signal(int)
    btn_listen_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_height = 80
        # 用于记录按下状态: (row_index, button_type_string)
        self._pressed_data = None

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.Type.ToolTip:
            rect = option.rect
            bottom_row_y = rect.top() + 40
            left_margin = rect.left() + 5
            input_rect = QRect(left_margin, bottom_row_y, rect.width() - 10, 30)
            if input_rect.contains(event.pos()):
                QToolTip.showText(event.globalPos(), tr("Double-click the text box to edit the subtitles"))
                return True
        return super().helpEvent(event, view, option, index)

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.row_height)

    def paint(self, painter, option, index):
        item = index.data(DubbingModel.RoleRawData)
        time_str = index.data(DubbingModel.RoleTimeStr)
        text = item['text']

        painter.save()

        # 0. 背景
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        rect = option.rect
        top_row_y = rect.top() + 5
        bottom_row_y = rect.top() + 40
        left_margin = rect.left() + 5

        # 1. 绘制时间轴文本
        if not Path(item['filename']).exists():
            painter.setPen(QColor("yellow"))
        elif option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            # painter.setPen(QColor("red"))
            painter.setPen(option.palette.text().color())

        text_rect = QRect(left_margin, top_row_y, rect.width() - 220, 30)
        elided_time_str = painter.fontMetrics().elidedText(time_str, Qt.TextElideMode.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_time_str)

        # 2. 绘制按钮
        btn_y = top_row_y + 2
        btn_h = 26
        btn_w = 90

        # 判断当前哪个按钮处于按下状态
        is_listen_pressed = False
        is_redub_pressed = False

        if self._pressed_data and self._pressed_data[0] == index.row():
            if self._pressed_data[1] == 'listen':
                is_listen_pressed = True
            elif self._pressed_data[1] == 'redub':
                is_redub_pressed = True

        # 按钮1: Trial dubbing
        btn_listen_rect = QRect(rect.right() - btn_w - 5, btn_y, btn_w, btn_h)
        self._draw_button(painter, btn_listen_rect, tr("Trial dubbing"), option, pressed=is_listen_pressed)

        # 按钮2: Re-dubbed
        btn_redub_rect = QRect(btn_listen_rect.left() - btn_w - 5, btn_y, btn_w, btn_h)
        self._draw_button(painter, btn_redub_rect, tr("Re-dubbed"), option, pressed=is_redub_pressed)

        # 3. 绘制输入框
        input_rect = QRect(left_margin, bottom_row_y, rect.width() - 10, 30)
        input_bg = option.palette.base().color()
        border_col = QColor("#455364")
        painter.setBrush(QBrush(input_bg))
        painter.setPen(QPen(border_col))
        painter.drawRoundedRect(input_rect, 4, 4)

        painter.setPen(option.palette.windowText().color())
        text_draw_rect = input_rect.adjusted(4, 0, -4, 0)
        elided_text = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, text_draw_rect.width())
        painter.drawText(text_draw_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_text)

        painter.restore()

    def _draw_button(self, painter, rect, text, option, pressed=False):
        """
        手动绘制按钮，增加 pressed 参数控制按压颜色
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ===========================
        # 1. 定义颜色
        # ===========================
        if pressed:
            # 按下状态：颜色更深
            bg_color = QColor("#222222")
            border_color = QColor("#222222")
            text_color = QColor("#aaaaaa") # 文字稍微暗一点
        else:
            # 正常状态
            bg_color = QColor("#455364")
            border_color = QColor("#455364")
            text_color = QColor("#DFE1E2")

        # 选中行的高亮调整
        if option.state & QStyle.StateFlag.State_Selected and not pressed:
            bg_color = QColor("#19232D")
            border_color = QColor("#19232D")
            text_color = QColor("#ffffff")

        # ===========================
        # 2. 绘制
        # ===========================
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(rect, 4, 4)

        painter.setPen(text_color)
        # 如果按下，文字可以稍微向右下偏移1像素，增加立体感
        if pressed:
            rect.translate(1, 1)

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        rect = option.rect
        top_row_y = rect.top() + 5
        btn_y = top_row_y + 2
        btn_h = 26
        btn_w = 90

        btn_listen_rect = QRect(rect.right() - btn_w - 5, btn_y, btn_w, btn_h)
        btn_redub_rect = QRect(btn_listen_rect.left() - btn_w - 5, btn_y, btn_w, btn_h)

        # 计算输入框区域 (用于双击检测)
        bottom_row_y = rect.top() + 40
        left_margin = rect.left() + 5
        input_rect = QRect(left_margin, bottom_row_y, rect.width() - 10, 30)

        # ---------------------------------------------------------
        # 1. 处理鼠标按下 (MouseButtonPress)
        #    【修改】：在按下时直接触发事件，避免 Release 因焦点丢失失效
        # ---------------------------------------------------------
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                hit_listen = btn_listen_rect.contains(event.pos())
                hit_redub = btn_redub_rect.contains(event.pos())

                if hit_listen or hit_redub:
                    # 1. 强制 Viewport 获得焦点，关闭任何可能打开的编辑器
                    #    这确保了数据提交，并让 View 进入稳定状态
                    option.widget.setFocus()

                    # 2. 设置视觉按下状态
                    if hit_listen:
                        self._pressed_data = (index.row(), 'listen')
                        # 3. 【核心变更】立即触发事件
                        self.btn_listen_clicked.emit(index.row())
                    else:
                        self._pressed_data = (index.row(), 'redub')
                        self.btn_redub_clicked.emit(index.row())

                    # 4. 触发重绘，显示“按下”的深色效果
                    option.widget.viewport().update(rect)

                    return True # 消费事件

        # ---------------------------------------------------------
        # 2. 处理鼠标释放 (MouseButtonRelease)
        #    【修改】：仅用于恢复按钮视觉状态（弹起）
        # ---------------------------------------------------------
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                if self._pressed_data:
                    # 只要有按下状态，松开时就清除状态并重绘
                    self._pressed_data = None
                    option.widget.viewport().update(rect)
                    return True

        # ---------------------------------------------------------
        # 3. 处理双击 (MouseButtonDblClick) - 手动触发编辑
        # ---------------------------------------------------------
        elif event.type() == QEvent.Type.MouseButtonDblClick:
            if input_rect.contains(event.pos()):
                view = option.widget
                if hasattr(view, 'edit'):
                    view.edit(index)
                return True

            # 防止双击按钮区域触发默认行为
            if btn_listen_rect.contains(event.pos()) or btn_redub_rect.contains(event.pos()):
                return True

        return super().editorEvent(event, model, option, index)

    # createEditor, setEditorData, setModelData, updateEditorGeometry 保持不变
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

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

        # 【修改】使用 ListView 替代 ScrollArea
        self.list_view = QListView()
        self.list_view.setUniformItemSizes(True)
        self.list_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_view.setVisible(False)
        self.list_view.setTabKeyNavigation(True)

        main_layout.addWidget(self.list_view)

        # 底部按钮
        save_button = QPushButton(tr("nextstep"))
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setMinimumSize(QSize(400, 35))
        save_button.clicked.connect(self.save_and_close)
        cancel_button = QPushButton(tr("Terminate this mission"))
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMaximumSize(QSize(200, 30))
        cancel_button.clicked.connect(self.cancel_and_close)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(save_button)
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
        self.stop_button.setText(f"{tr('Click here to stop the countdown')}({self.count_down})")
        if self.count_down <= 0:
            self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.stop_button.deleteLater()
        self.prompt_label.deleteLater()

    # 【兼容接口】保留空方法
    def create_container(self):
        pass

    def create_subtitle_assignment_area(self):
        # 【重写】初始化 Model/View
        self.model = DubbingModel(self.queue_tts, self)
        self.delegate = DubbingDelegate(self.list_view)

        # 连接 Delegate 里的按钮信号
        self.delegate.btn_listen_clicked.connect(self.listen)
        self.delegate.btn_redub_clicked.connect(self.re_dubb)

        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)

        # 【关键】禁用默认触发器，由 Delegate 全权接管点击逻辑
        self.list_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.progress_bar.setValue(100)
        self.loading_label.setText(tr("Data is ready rendering is in progress"))
        QApplication.processEvents()

    def listen(self, i):
        # 注意：i 是行号 (int)
        print(f'{i=}')
        item = self.queue_tts[i]
        filename = item['filename']
        if not tools.vail_file(filename):
            QMessageBox.information(self, tr("The audio file does not exist"), tr("The audio file does not exist"))
            return
        threading.Thread(target=tools.pygameaudio, args=(filename,)).start()

    def re_dubb(self, i):
        print(f'从新配音 {i=}')
        # 删除旧文件
        Path(self.queue_tts[i]['filename']).unlink(missing_ok=True)

        tts_dict = self.queue_tts[i]

        # 确保使用的是 Model 里最新的文本
        # Model 里的数据是引用 self.queue_tts，所以直接读即可，但为了保险起见，从 Model 读
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

            # 【重写】不再手动操作 label，而是更新 Model
            # Model 内部逻辑会重新计算时间并发出 dataChanged
            self.model.refresh_item(idx)

            # 播放音频
            threading.Thread(target=tools.pygameaudio, args=(item['filename'],)).start()
        else:
            QMessageBox.information(self, 'Error', msg)

    # 【兼容】Model 内部处理逻辑，此方法保留给 Model 使用或废弃
    def get_timeline_str(self, item):
        # 这里的逻辑已经迁移到了 Model._update_time_info
        pass

    def save_and_close(self):
        # 【重写】数据都在 self.queue_tts (被 Model 引用并修改)
        # 只需要处理空文本删除文件的逻辑

        for i, item in enumerate(self.queue_tts):
            text = item['text'].strip()
            if not text:
                Path(item['filename']).unlink(missing_ok=True)
            # item['text'] 已经被 model 的 setData 更新过了

        # 更新queue
        try:
            Path(f'{self.cache_folder}/queue_tts.json').write_text(json.dumps(self.queue_tts), encoding="utf-8")
        except Exception:
            pass

        self.accept()