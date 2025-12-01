import math
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QScrollArea, QWidget, QGroupBox, QFrame,
    QProgressBar, QApplication, QListView, QStyle, QStyledItemDelegate,QToolTip
)
from PySide6.QtGui import QIcon, QPen, QColor, QBrush, QPalette
from PySide6.QtCore import Qt, QTimer, QSize, QAbstractListModel, QModelIndex, QRect, QEvent

from videotrans.configure.config import tr
from videotrans.util import tools
from videotrans.configure import config

# ===========================================================================
# 1. 定义数据模型 负责管理字幕数据列表，提供给 ListView 读取和修改

class SubtitleModel(QAbstractListModel):
    # 自定义角色，用于区分获取整个数据项还是仅获取特定字段
    RawDataRole = Qt.UserRole + 1

    def __init__(self, subtitles=None, parent=None):
        super().__init__(parent)
        self._data = subtitles or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None

        item = self._data[index.row()]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return item['text']

        if role == self.RawDataRole:
            return item

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            # 更新内存中的数据
            self._data[index.row()]['text'] = value
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        # 允许选中和编辑
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def get_all_data(self):
        return self._data

# ===========================================================================
# 2. 定义委托 负责绘制每一行（模拟原有的两行布局），以及创建编辑器

class SubtitleDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_height = 70  # 保持原有高度
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

    def paint(self, painter, option, index):
        # 获取数据
        item = index.data(SubtitleModel.RawDataRole)
        text = item['text']

        # 计算时间显示字符串
        duration = (item['end_time'] - item['start_time']) / 1000.0
        time_str = f"[{item['line']}] {item['startraw']}->{item['endraw']}({duration}s) "

        painter.save()

        # 绘制背景（如果被选中）
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # 定义区域
        rect = option.rect
        # 上半部分：时间标签区域
        time_rect = QRect(rect.left() + 5, rect.top() + 5, rect.width() - 10, 20)
        # 下半部分：文本编辑框模拟区域
        text_rect = QRect(rect.left() + 5, rect.top() + 30, rect.width() - 10, 30)

        # 1. 绘制时间文本 (模拟 QLabel)
        # 选中时字体颜色需要适配
        if option.state & QStyle.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        painter.drawText(time_rect, Qt.AlignLeft | Qt.AlignVCenter, time_str)

        # 2. 绘制“伪”输入框背景 (模拟 QLineEdit)
        # 我们画一个框框，让用户知道这里是文本
        input_bg_color = option.palette.base().color()
        border_color = QColor("#455364")

        painter.setBrush(QBrush(input_bg_color))
        painter.setPen(QPen(border_color))
        # 圆角
        painter.drawRoundedRect(text_rect, 4, 4)

        # 3. 绘制字幕内容
        # 输入框内的文字通常是黑色的（除非暗色模式），这里用 WindowText
        painter.setPen(option.palette.windowText().color())
        # 文字稍微缩进一点，不要贴着边框
        text_draw_rect = text_rect.adjusted(4, 0, -4, 0)

        painter.drawText(text_draw_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

        painter.restore()

    # 创建编辑器时（用户双击或按回车时调用）
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

    # 设置编辑器的数据
    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.EditRole)
        editor.setText(text)

    # 将编辑器的数据保存回模型
    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.EditRole)

    # 关键：确保编辑器只出现在“下半部分”，覆盖我们画的那个框框
    def updateEditorGeometry(self, editor, option, index):
        rect = option.rect
        # 编辑器位置与 paint 中的 text_rect 一致
        editor.setGeometry(rect.left() + 5, rect.top() + 30, rect.width() - 10, 30)


# ===========================================================================
# 3. 主窗口
class EditRecognResultDialog(QDialog):
    def __init__(
        self,
        parent=None,
        source_sub: str = None
    ):
        super().__init__()
        self.parent=parent
        self.source_sub=source_sub
        self.srt_list_dict=tools.get_subtitle_from_srt(self.source_sub)

        self.setWindowTitle(tr("zimubianjitishi"))
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        self.setWindowFlags(Qt.WindowTitleHint | Qt.WindowSystemMenuHint  | Qt.WindowMaximizeButtonHint)

        self.count_down = int(float(config.settings.get('countdown_sec', 1)))

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

        # 查找和替换布局
        search_replace_layout = QHBoxLayout()
        search_replace_layout.addStretch()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("Original text"))
        self.search_input.setMaximumWidth(200)
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

        # Loading 控件 
        self.loading_widget = QWidget()
        load_layout = QVBoxLayout(self.loading_widget)
        self.loading_label = QLabel(tr('The subtitle editing interface is rendering'), self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(5)

        load_layout.addWidget(self.loading_label)
        load_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.loading_widget)


        self.list_view = QListView()
        self.list_view.setUniformItemSizes(True) # 优化性能关键
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setVisible(False) # 初始隐藏，等待 lazy_load
        # 设置按 TAB 键切换到下一行编辑
        self.list_view.setTabKeyNavigation(True)

        main_layout.addWidget(self.list_view)

        # 底部保存按钮
        self.save_button = QPushButton(tr("nextstep"))
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setMinimumSize(QSize(400, 35))
        self.save_button.clicked.connect(self.save_and_close)
        cancel_button = QPushButton(tr("Terminate this mission"))
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMaximumSize(QSize(200, 30))
        cancel_button.clicked.connect(self.cancel_and_close)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(cancel_button)
        bottom_layout.addStretch()

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)
        QTimer.singleShot(50,self.lazy_load_interface)

    def lazy_load_interface(self):
        # 调用数据加载
        self.create_subtitle_assignment_area()
        QApplication.processEvents()

        def _finish():
            # 显示 ListView，隐藏 Loading
            self.list_view.setVisible(True)
            self.loading_widget.deleteLater()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)
            self._active()

        QTimer.singleShot(50, _finish)

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
        self.stop_button.setText(f"{tr('点此停止倒计时')}({self.count_down})")
        if self.count_down <= 0:
            self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.stop_button.deleteLater()
        self.prompt_label.deleteLater()


    def create_subtitle_assignment_area(self):

        # 1. 创建 Model
        self.model = SubtitleModel(self.srt_list_dict, self)

        # 2. 创建 Delegate
        self.delegate = SubtitleDelegate(self.list_view)

        # 3. 绑定到 View
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)

        # 更新进度条
        self.progress_bar.setValue(100)
        self.loading_label.setText(tr("Data is ready rendering is in progress"))
        QApplication.processEvents()

    def replace_text(self):
        # 获取查找和替换的文本
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            return

        # model.get_all_data() 返回的是引用，直接修改它后通知 Model 更新视图
        source_data = self.model.get_all_data()

        # 批量更新标志
        data_changed = False

        for i, item in enumerate(source_data):
            if search_text in item['text']:
                item['text'] = item['text'].replace(search_text, replace_text)
                # 标记这一行发生了改变
                index = self.model.index(i)
                self.model.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
                data_changed = True

        if data_changed:
            # 强制刷新一下界面
            self.list_view.viewport().update()

    def save_and_close(self):
        self.save_button.setDisabled(True)
        # 更新角色
        srt_str_list=[]

        # 从 Model 获取最终数据
        all_items = self.model.get_all_data()

        for item in all_items:
            text = item['text'].strip()
            if text:
                srt_str_list.append(f'{item["line"]}\n{item["startraw"]} --> {item["endraw"]}\n{text}')

        Path(self.source_sub).write_text("\n\n".join(srt_str_list), encoding="utf-8")

        self.accept()