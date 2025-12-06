import json
import sys
from typing import List, Dict, Optional
from pathlib import Path
import re

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QCheckBox,
    QComboBox, QPushButton, QScrollArea, QWidget, QGroupBox, QSplitter,
    QPlainTextEdit, QFrame, QMessageBox, QProgressBar, QApplication,
    QListView, QStyle, QStyledItemDelegate,QStyleOptionButton,QToolTip
)
from PySide6.QtGui import QIcon, QPen, QColor, QBrush, QPainter
from PySide6.QtCore import Qt, QTimer, QSize, QAbstractListModel, QModelIndex, QRect, QPoint,QEvent

from videotrans.configure.config import logs, tr
from videotrans.util import tools
from videotrans.configure import config


# 1. 数据模型 
class SubtitleSpeakerModel(QAbstractListModel):
    # 定义自定义角色
    RoleRawData = Qt.UserRole + 1   # 获取原始字典数据
    RoleChecked = Qt.UserRole + 2   # 获取/设置选中状态
    RoleRole    = Qt.UserRole + 3   # 获取/设置分配的角色

    def __init__(self, subtitles=None, speaker_list_sub=None, speakers=None, parent=None):
        super().__init__(parent)
        self._data = subtitles or []
        self.speaker_list_sub = speaker_list_sub or []
        self.speakers = speakers or {} # id -> role map

        # 添加选中状态 checked 和 预计算显示用的 speaker_id
        # 为了避免每次 paint 都计算 speaker id
        for i, item in enumerate(self._data):
            if 'checked' not in item:
                item['checked'] = False

            # 计算这一行的 speaker 显示文本
            spkid = ''
            if self.speakers:
                if i < len(self.speaker_list_sub):
                    spkid = self.speaker_list_sub[i]
                else:
                    spkid = list(self.speakers.keys())[0]
            item['display_spkid'] = spkid

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

        if role == self.RoleChecked:
            return item['checked']

        if role == self.RoleRole:
            return item.get('role', '')

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        row = index.row()

        if role == Qt.EditRole:
            self._data[row]['text'] = value
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True

        if role == self.RoleChecked:
            self._data[row]['checked'] = value
            # 选中状态改变，需要重绘 Checkbox 区域
            self.dataChanged.emit(index, index, [self.RoleChecked])
            return True

        if role == self.RoleRole:
            self._data[row]['role'] = value
            # 角色改变，需要重绘显示角色的区域
            self.dataChanged.emit(index, index, [self.RoleRole])
            return True

        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def get_all_data(self):
        return self._data

# ===========================================================================
# 2. 定义委托 负责绘制复选框、标签、时间、文本框
class SubtitleSpeakerDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_height = 75  # 行高

    def helpEvent(self, event, view, option, index):
        """
        处理 ToolTip 事件：
        当鼠标悬停在输入框区域时，显示提示文本。
        """
        if event.type() == QEvent.Type.ToolTip:
            # 1. 重新计算输入框区域 
            rect = option.rect
            bottom_row_y = rect.top() + 40
            left_margin = rect.left() + 5
            # 输入框区域
            input_rect = QRect(left_margin, bottom_row_y, rect.width() - 10, 30)

            # 2. 检查鼠标位置是否在输入框内
            # event.pos() 是相对于 View 的坐标
            if input_rect.contains(event.pos()):
                # 显示提示
                QToolTip.showText(event.globalPos(), tr("Double-click the text box to edit the subtitles"))
                return True

        return super().helpEvent(event, view, option, index)

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.row_height)

    def _draw_checkbox(self, painter, rect, checked):
        """
        手动绘制适配暗色主题的复选框
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ===========================
        # 1. 定义颜色
        # ===========================
        if checked:
            # 选中状态：蓝色背景，无边框
            bg_color = QColor("#2b79a0")
            border_color = QColor("#2b79a0")
            tick_color = QColor("#ffffff") # 白色对号
        else:
            # 未选中状态：深灰背景，浅灰边框
            bg_color = QColor("#32414B")
            border_color = QColor("#888888")
            tick_color = Qt.GlobalColor.transparent

        # ===========================
        # 2. 绘制方框
        # ===========================
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.5))
        # 绘制圆角矩形 (半径3)
        painter.drawRoundedRect(rect, 3, 3)

        # ===========================
        # 3. 绘制对号 (仅在选中时)
        # ===========================
        if checked:
            painter.setPen(QPen(tick_color, 2))

            # 计算对号的坐标 (基于 rect 动态计算)
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

            # 对号的三个关键点：左中，下中，右上
            # p1: x+20%, y+50%
            # p2: x+45%, y+75%
            # p3: x+80%, y+25%

            p1 = QPoint(int(x + w * 0.25), int(y + h * 0.45))
            p2 = QPoint(int(x + w * 0.45), int(y + h * 0.70))
            p3 = QPoint(int(x + w * 0.75), int(y + h * 0.25))

            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)

        painter.restore()

    def paint(self, painter, option, index):
        item = index.data(SubtitleSpeakerModel.RoleRawData)

        # 基础数据
        text = item['text']
        spkid = item.get('display_spkid', '')
        line_idx = item['line']
        is_checked = item['checked']
        assigned_role = item.get('role', '') # 当前分配的角色

        # 时间计算
        duration = (item['end_time'] - item['start_time']) / 1000.0
        time_str = f"{item['startraw']}->{item['endraw']}({duration}s)"

        painter.save()

        # 0. 绘制选中背景
        # PySide6 枚举修复: QStyle.StateFlag.State_Selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        rect = option.rect

        # 布局定义
        top_y = rect.top() + 8
        content_x = rect.left() + 10

        # 1. 绘制 "[Index] SpkID"
        info_text = f"[{line_idx}] {spkid}"
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        painter.drawText(content_x, top_y + 12, info_text)

        # 计算刚才画的文字宽度
        fm = painter.fontMetrics()
        w_info = fm.horizontalAdvance(info_text)
        content_x += w_info + 15

        # 2. 绘制复选框 (CheckBox)
        cb_rect = QRect(content_x, top_y, 16, 16)
        self._draw_checkbox(painter, cb_rect, is_checked)


        content_x += 25

        # 3. 绘制分配的角色 (Role Label)
        if assigned_role:
            role_text = assigned_role
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(QColor("#ffcccc"))
            else:
                painter.setPen(QColor("#ff0000"))
            painter.drawText(content_x, top_y + 12, role_text)
            content_x += fm.horizontalAdvance(role_text) + 15
        else:
            content_x += 5 # 占个位

        # 4. 绘制时间 (Time Label)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
        painter.drawText(content_x, top_y + 12, time_str)

        # 5. 绘制下半部分：模拟文本输入框
        input_rect = QRect(rect.left() + 5, rect.top() + 35, rect.width() - 10, 30)

        input_bg = option.palette.base().color()
        border_col = QColor("#455364")
        painter.setBrush(QBrush(input_bg))
        painter.setPen(QPen(border_col))
        painter.drawRoundedRect(input_rect, 4, 4)

        # 画文字
        painter.setPen(option.palette.windowText().color())
        text_draw_rect = input_rect.adjusted(4, 0, -4, 0)
        # 文本过长省略
        elided_text = fm.elidedText(text, Qt.TextElideMode.ElideRight, text_draw_rect.width())
        painter.drawText(text_draw_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_text)

        painter.restore()

    # 处理点击事件
    # 处理点击事件
    def editorEvent(self, event, model, option, index):
        # 使用 QEvent.Type.MouseButtonRelease
        if event.type() == QEvent.Type.MouseButtonRelease:
            # 重算复选框位置
            item = index.data(SubtitleSpeakerModel.RoleRawData)
            spkid = item.get('display_spkid', '')
            line_idx = item['line']

            fm = option.fontMetrics
            info_text = f"[{line_idx}] {spkid}"
            w_info = fm.horizontalAdvance(info_text)

            content_x = option.rect.left() + 10 + w_info + 15
            top_y = option.rect.top() + 8
            cb_rect = QRect(content_x, top_y, 16, 16)

            click_rect = cb_rect.adjusted(-2, -2, 2, 2)

            if click_rect.contains(event.pos()):
                current_state = model.data(index, SubtitleSpeakerModel.RoleChecked)
                model.setData(index, not current_state, SubtitleSpeakerModel.RoleChecked)
                return True

        return super().editorEvent(event, model, option, index)

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
        editor.setGeometry(rect.left() + 5, rect.top() + 35, rect.width() - 10, 30)
# ===========================================================================
# 3. 主窗口
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
        self.parent=parent
        self.target_sub=target_sub
        self.source_srtstring=None
        self.cache_folder=cache_folder
        self.target_language=target_language
        self.tts_type=tts_type
        if source_sub:
            sour_pt=Path(source_sub)
            if sour_pt.as_posix() and not sour_pt.samefile(Path(target_sub)):
                self.source_srtstring=sour_pt.read_text(encoding="utf-8")

        self.srt_list_dict=tools.get_subtitle_from_srt(self.target_sub)

        self.speaker_list_sub=[]
        self.speakers={}
        try:
            _list_sub=[] if not Path(f'{self.cache_folder}/speaker.json').exists() else json.loads(Path(f'{self.cache_folder}/speaker.json').read_text(encoding='utf-8'))
            _set =set(_list_sub) if _list_sub else None
            if _set and len(_set)>1:
                self.speaker_list_sub=_list_sub
                self.speakers={it:None for it in sorted(list(_set))}
        except Exception as e:
            logs(f'获取说话人id失败:{e}',level="except")

        self.all_voices = all_voices or []

        self.setWindowTitle(tr("zidonghebingmiaohou"))
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        self.setWindowFlags(Qt.WindowTitleHint | Qt.WindowSystemMenuHint  | Qt.WindowMaximizeButtonHint)

        main_layout = QVBoxLayout(self)
        innerc_layout = QHBoxLayout(self)

        if self.source_srtstring:
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            self.raw_srt_edit = QPlainTextEdit()
            self.raw_srt_edit.setPlainText(self.source_srtstring)
            self.raw_srt_edit.setReadOnly(True)
            tiplabel=QLabel(tr("This is the original language subtitles for comparison reference"))
            tiplabel.setStyleSheet("""color:#aaaaaa""")
            left_layout.addWidget(tiplabel)
            left_layout.addWidget(self.raw_srt_edit)
            innerc_layout.addWidget(left_widget, stretch=2)

        self.count_down = int(float(config.settings.get('countdown_sec', 1)))

        top_layout = QVBoxLayout()
        hstop=QHBoxLayout()

        self.prompt_label = QLabel(tr("This window will automatically close after the countdown ends"))
        self.prompt_label.setStyleSheet('font-size:14px;text-align:center;color:#aaaaaa')
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
        prompt_label2.setWordWrap(True)
        top_layout.addWidget(prompt_label2)

        main_layout.addLayout(top_layout)

        self.loading_widget = QWidget()
        load_layout = QVBoxLayout(self.loading_widget)
        self.loading_label = QLabel(tr('The subtitle editing interface is rendering'), self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(1)

        load_layout.addWidget(self.loading_label)
        load_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.loading_widget)

        # 查找替换
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
        right_widget=QWidget()
        self.right_layout=QVBoxLayout(right_widget)

        # 初始化 List View
        self.list_view = QListView()
        self.list_view.setUniformItemSizes(True)
        self.list_view.setResizeMode(QListView.ResizeMode.Adjust)

        self.list_view.setVisible(False)
        self.list_view.setTabKeyNavigation(True)
        # 支持扩展选择
        self.list_view.setSelectionMode(QListView.ExtendedSelection)

        # 如果 speakers 不为 None，则右侧分为上下两部分
        if self.speakers:
            upper_widget = self.create_speaker_assignment_area()
            self.right_layout.addWidget(upper_widget)
            # 下部改为 ListView
            self.right_layout.addWidget(self.list_view)
        else:
            self.right_layout.addWidget(self.list_view)

        innerc_layout.addWidget(right_widget, stretch=7)

        # 底部保存按钮
        self.save_button = QPushButton(tr("nextstep"))
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setMinimumSize(QSize(400, 35))
        self.save_button.clicked.connect(self.save_and_close)

        cancel_button = QPushButton(tr("Terminate this mission"))
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMinimumSize(QSize(200, 30))
        cancel_button.clicked.connect(self.cancel_and_close)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(cancel_button)
        bottom_layout.addStretch()

        main_layout.addLayout(innerc_layout)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)
        QTimer.singleShot(100, self.lazy_load_interface)


    def lazy_load_interface(self):
        self.create_subtitle_assignment_area()
        QApplication.processEvents()
        def _finish():
            self.list_view.setVisible(True) # 显示 ListView
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
        if self.stop_button and hasattr(self.stop_button,'setText'):
            self.stop_button.setText(f"{tr('Click here to stop the countdown')}({self.count_down})")
        if self.count_down <= 0:
            self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.stop_button.deleteLater()
        self.prompt_label.deleteLater()

    def create_speaker_assignment_area(self) -> QWidget:
        group = QGroupBox("")
        layout = QVBoxLayout(group)
        label_tips=QLabel(tr("Assign a timbre to each speaker"))
        label_tips.setStyleSheet("color:#aaaaaa")
        layout.addWidget(label_tips)

        self.speaker_checks = {}
        self.speaker_labels = {}

        # 使用 row_widget 来承载每行的 checkboxes，然后将 widget 添加到主 layout

        current_row_widget = None
        current_row_layout = None

        for i, spk_id in enumerate(self.speakers):
            # 每 3 个元素或者刚开始时，创建一个新行 Widget
            if i % 3 == 0:
                current_row_widget = QWidget()
                current_row_widget.setFixedHeight(40) # 给一点高度
                current_row_layout = QHBoxLayout(current_row_widget)
                current_row_layout.setContentsMargins(0, 5, 0, 5) # 设置边距

                # 将这个 Widget 添加到主垂直布局中
                layout.addWidget(current_row_widget)

            # 创建控件
            check = QCheckBox(f'{tr("Speaker")}{spk_id}')
            label = QLabel("")

            # 添加到当前行的水平布局
            current_row_layout.addWidget(check)
            current_row_layout.addWidget(label)
            current_row_layout.addStretch() # 每个条目后面加弹簧，保持间距

            self.speaker_checks[check] = spk_id
            self.speaker_labels[check] = label

        # 底部操作行
        bottom_row = QHBoxLayout()
        self.speaker_combo = QComboBox()

        for voice in self.all_voices:
            self.speaker_combo.addItem(voice)

        bottom_row.addWidget(QLabel(tr('Dubbing role')))
        bottom_row.addWidget(self.speaker_combo)

        assign_button = QPushButton(tr("Assign roles to speakers"))
        assign_button.setCursor(Qt.PointingHandCursor)
        assign_button.clicked.connect(self.assign_speaker_roles)
        assign_button.setMinimumSize(QSize(150, 30))
        bottom_row.addWidget(assign_button)
        bottom_row.addStretch()

        layout.addLayout(bottom_row)

        return group

    def assign_speaker_roles(self):
        selected_role = self.speaker_combo.currentText()
        role_value = None if selected_role == "No" else selected_role

        for check, spk_id in self.speaker_checks.items():
            if check.isChecked():
                self.speakers[spk_id] = role_value
                label = self.speaker_labels[check]
                label.setText(selected_role if role_value else "")

        for check in self.speaker_checks:
            if check.isChecked():
                check.setChecked(False)

    def create_subtitle_assignment_area(self) :
        # 0. 添加提示 Label 到 right_layout (ListView 上方)
        label_tips = QLabel(tr('assign a specific voice to a line of subtitles'))
        label_tips.setWordWrap(True)
        label_tips.setStyleSheet("color:#aaaaaa")

        idx = self.right_layout.indexOf(self.list_view)
        if idx != -1:
            self.right_layout.insertWidget(idx, label_tips)

        # 1. 创建 Model
        self.model = SubtitleSpeakerModel(
            subtitles=self.srt_list_dict,
            speaker_list_sub=self.speaker_list_sub,
            speakers=self.speakers,
            parent=self
        )

        # 2. 创建 Delegate
        self.delegate = SubtitleSpeakerDelegate(self.list_view)

        # 3. 绑定
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)

        # 进度条假装跑一下
        self.progress_bar.setValue(100)
        self.loading_label.setText(tr("Data is ready rendering is in progress"))
        QApplication.processEvents()

        # 4. 创建底部操作栏 
        bottom_row = QHBoxLayout()
        self.subtitle_combo = QComboBox()
        for voice in self.all_voices:
            self.subtitle_combo.addItem(voice)
        bottom_row.addWidget(self.subtitle_combo)

        assign_button = QPushButton(tr("Assign roles to selected subtitles"))
        assign_button.setCursor(Qt.PointingHandCursor)
        assign_button.clicked.connect(self.assign_subtitle_roles)
        assign_button.setMinimumSize(QSize(200, 30))
        bottom_row.addWidget(assign_button)

        self.listen_button = QPushButton(tr("Trial dubbing"))
        self.listen_button.setCursor(Qt.PointingHandCursor)
        self.listen_button.clicked.connect(self.listen_dubbing)

        bottom_row.addWidget(self.listen_button)
        bottom_row.addStretch()

        self.right_layout.addLayout(bottom_row)

    def listen_dubbing(self):
        selected_role = self.subtitle_combo.currentText()
        role_value = None if selected_role == "No" else selected_role
        if not role_value:
            return

        # 取第一条数据
        first_item = self.model.data(self.model.index(0), SubtitleSpeakerModel.RoleRawData)
        if not first_item:
            return

        from videotrans.util.ListenVoice import ListenVoice
        import time
        def feed(d):
            self.listen_button.setText(tr("Trial dubbing"))
            self.listen_button.setDisabled(False)
            if d == "ok":
                QMessageBox.information(self, "ok", "Test Ok")
            else:
                tools.show_error(d)

        wk = ListenVoice(parent=self, queue_tts=[{
            "text": first_item['text'],
            "role": role_value,
            "filename": config.TEMP_DIR + f"/{time.time()}-onlyone_setrole.wav",
            "tts_type": self.tts_type}],
                         language=self.target_language,
                         tts_type=self.tts_type)
        wk.uito.connect(feed)
        wk.start()
        self.listen_button.setText('Listening...')
        self.listen_button.setDisabled(True)

    def replace_text(self):
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            return

        # 批量修改 Model
        source_data = self.model.get_all_data()
        data_changed = False

        for i, item in enumerate(source_data):
            if search_text in item['text']:
                item['text'] = item['text'].replace(search_text, replace_text)
                idx = self.model.index(i)
                self.model.dataChanged.emit(idx, idx, [Qt.DisplayRole, Qt.EditRole])
                data_changed = True

        if data_changed:
            self.list_view.viewport().update()

    def assign_subtitle_roles(self):
        selected_role = self.subtitle_combo.currentText()
        role_value = None if selected_role == "No" else selected_role

        # 遍历 Model 数据，查找 'checked' 为 True 的项
        source_data = self.model.get_all_data()

        for i, item in enumerate(source_data):
            if item.get('checked', False):
                item['role'] = role_value
                # 重置选中状态
                item['checked'] = False

                # 通知视图更新：RoleChecked (取消选中) 和 RoleRole (角色变更)
                idx = self.model.index(i)
                self.model.dataChanged.emit(idx, idx, [SubtitleSpeakerModel.RoleChecked, SubtitleSpeakerModel.RoleRole])

    def save_and_close(self):
        self.save_button.setDisabled(True)
        config.line_roles={}
        srt_str_list=[]

        source_data = self.model.get_all_data()

        for i, row_item in enumerate(source_data):
            text = row_item['text'].strip()
            srt_str_list.append(f'{row_item["line"]}\n{row_item["startraw"]} --> {row_item["endraw"]}\n{text}')

            # 获取角色逻辑
            role = row_item.get('role')
            # 如果没有为该行单独指定角色，则查看是否有 Speaker 对应的默认角色
            if not role and self.speakers:
                # 获取该行的 speaker id
                spk_id = None
                if i < len(self.speaker_list_sub):
                    spk_id = self.speaker_list_sub[i]
                elif self.speakers:
                    spk_id = list(self.speakers.keys())[0]

                if spk_id:
                    role = self.speakers.get(spk_id)

            if role:
                config.line_roles[f'{row_item["line"]}'] = role

        Path(self.target_sub).write_text("\n\n".join(srt_str_list), encoding="utf-8")

        self.accept()