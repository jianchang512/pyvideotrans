import math
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QWidget, QProgressBar, QApplication, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import Qt, QTimer, QSize, QUrl

from videotrans.configure.config import tr
from videotrans.util import tools
from videotrans.configure import config


class EditRecognResultDialog(QDialog):
    def __init__(
            self,
            parent=None,
            source_sub: str = None
    ):
        super().__init__()
        self.parent = parent
        self.source_sub = source_sub
        self.srt_list_dict = tools.get_subtitle_from_srt(self.source_sub)

        self.setWindowTitle(tr("zimubianjitishi"))
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setMinimumWidth(int(parent.width*0.95))
        self.setMinimumHeight(int(parent.height*0.95))
        self.setWindowFlags(Qt.Window |         
            Qt.WindowStaysOnTopHint |       # 2. 始终在最顶层
            Qt.WindowTitleHint |            # 3. 显示标题栏
            Qt.CustomizeWindowHint |        # 4. 允许自定义标题栏按钮（否则OS会强制加关闭按钮）
            Qt.WindowMaximizeButtonHint     # 5. 只加最大化按钮，不加关闭按钮
        )

        self.count_down = int(float(config.settings.get('countdown_sec', 1)))

        main_layout = QVBoxLayout(self)

        # Top Bar
        hstop = QHBoxLayout()
        self.prompt_label = QLabel(tr("jimiaohoufanyi"))
        self.prompt_label.setStyleSheet('font-size:14px;color:#aaaaaa')
        hstop.addWidget(self.prompt_label)
        self.stop_button = QPushButton(f"{tr('Click here to stop the countdown')}({self.count_down})")
        self.stop_button.setStyleSheet("font-size: 16px;color:#ffff00")
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.clicked.connect(self.stop_countdown)
        hstop.addWidget(self.stop_button)
        main_layout.addLayout(hstop)

        prompt_label2 = QLabel(tr("If you need to delete a line of subtitles, just clear the text in that line"))
        prompt_label2.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(prompt_label2)

        # Search Bar
        search_replace_layout = QHBoxLayout()
        search_replace_layout.addStretch()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("Original text"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText(tr("Replace"))
        replace_button = QPushButton(tr("Replace"))
        replace_button.clicked.connect(self.replace_text)
        search_replace_layout.addWidget(self.search_input)
        search_replace_layout.addWidget(self.replace_input)
        search_replace_layout.addWidget(replace_button)
        search_replace_layout.addStretch()
        main_layout.addLayout(search_replace_layout)

        # Loading
        self.loading_widget = QWidget()
        self.loading_label = QLabel(tr('Loading...'), self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        load_layout = QVBoxLayout(self.loading_widget)
        load_layout.addWidget(self.loading_label)
        main_layout.addWidget(self.loading_widget)

        # Table Widget (初始隐藏)
        self.table = QTableWidget()
        self.table.setVisible(False)
        main_layout.addWidget(self.table)

        # Bottom Bar
        self.save_button = QPushButton(tr("nextstep"))
        self.save_button.clicked.connect(self.save_and_close)
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setMinimumSize(QSize(300, 35))
        self.save_button2 = QPushButton(tr("nosaveandstep"))
        self.save_button2.clicked.connect(self.save_and_close2)
        self.save_button2.setCursor(Qt.PointingHandCursor)
        self.save_button2.setMinimumSize(QSize(200, 35))
        self.opendir_button = QPushButton(tr("opendir_button source_sub"))
        self.opendir_button.setCursor(Qt.PointingHandCursor)
        self.opendir_button.clicked.connect(self.opendir_sub)
        self.opendir_button.setMaximumSize(QSize(150, 30))
        cancel_button = QPushButton(tr("Terminate this mission"))
        cancel_button.clicked.connect(self.cancel_and_close)
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMaximumSize(QSize(150, 30))
        cancel_button.setStyleSheet("background-color:transparent;color:#ff0")
        
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
            # 1. 创建 QTableWidget
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels([tr("Line"), tr("Time Axis"), tr("Subtitle Text")])
            
            # 2. 禁用所有非必要功能
            self.table.setShowGrid(False)
            self.table.setAlternatingRowColors(False)
            self.table.setWordWrap(False)
            self.table.setMouseTracking(False)
            self.table.setFocusPolicy(Qt.NoFocus)
            self.table.setSelectionMode(QAbstractItemView.NoSelection)
            
            # 垂直表头
            v_header = self.table.verticalHeader()
            v_header.setVisible(False)
            v_header.setSectionResizeMode(QHeaderView.Fixed)
            v_header.setDefaultSectionSize(22)  # 最小行高
            
            # 水平表头
            h_header = self.table.horizontalHeader()
            h_header.setStretchLastSection(True)
            h_header.setSectionResizeMode(0, QHeaderView.Fixed)
            h_header.setSectionResizeMode(1, QHeaderView.Fixed)
            h_header.setSectionResizeMode(2, QHeaderView.Fixed)
            
            self.table.setColumnWidth(0, 50)
            self.table.setColumnWidth(1, 230)
            
            self.table.setStyleSheet("""
                QTableWidget {
                    color: #cccccc;
                    border: none;
                }
                QTableWidget::item {
                    padding: 2px;
                    border: none;
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
            
            # 3. 预计算所有显示数据
            self.display_data = []
            for item in self.srt_list_dict:
                duration = (item['end_time'] - item['start_time']) / 1000.0
                time_str = f"{item['startraw']} --> {item['endraw']} ({duration:.1f}s)"
                self.display_data.append({
                    'line': item['line'],
                    'time_str': time_str,
                    'text': item['text'],
                    'startraw': item['startraw'],
                    'endraw': item['endraw']
                })
            
            # 4. 设置行数
            total_rows = len(self.display_data)
            self.table.setRowCount(total_rows)
            
            # 5. 【分批填充】先填充前100行，避免界面冻结
            self._batch_fill(0, min(total_rows, 100))
            
            # 6. 显示表格
            self.loading_widget.setVisible(False)
            self.table.setVisible(True)
            
            # 7. 延迟加载剩余数据
            if total_rows > 100:
                QTimer.singleShot(0, lambda: self._load_remaining(100))
            
            # 8. 启动倒计时
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

    def _batch_fill(self, start_row, end_row):
        """批量填充数据"""
        for row in range(start_row, end_row):
            data = self.display_data[row]
            
            # Line (只读)
            item0 = QTableWidgetItem(str(data['line']))
            item0.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 0, item0)
            
            # Time (只读)
            item1 = QTableWidgetItem(data['time_str'])
            item1.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, item1)
            
            # Text (可编辑)
            item2 = QTableWidgetItem(data['text'])
            item2.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, item2)

    def _load_remaining(self, start_row):
        """延迟加载剩余行"""
        total = len(self.display_data)
        batch_size = 300  # 每批300行
        
        end_row = min(start_row + batch_size, total)
        self._batch_fill(start_row, end_row)
        
        if end_row < total:
            QTimer.singleShot(0, lambda: self._load_remaining(end_row))

    def cancel_and_close(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        self.reject()

    def update_countdown(self):
        self.count_down -= 1
        if self.stop_button:
            self.stop_button.setText(f"{tr('Click here to stop the countdown')}({self.count_down})")
        if self.count_down <= 0:
            self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.stop_button.deleteLater()
        self.prompt_label.deleteLater()

    def replace_text(self):
        """替换文本"""
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()
        if not search_text:
            return

        # 禁用更新提升性能
        self.table.setUpdatesEnabled(False)
        
        first = -1
        last = -1
        
        for i, data in enumerate(self.display_data):
            if search_text in data['text']:
                new_text = data['text'].replace(search_text, replace_text)
                data['text'] = new_text
                
                item = self.table.item(i, 2)
                if item:
                    item.setText(new_text)
                
                if first == -1:
                    first = i
                last = i
        
        self.table.setUpdatesEnabled(True)

    def save_and_close2(self):
        self.accept()
    
    def closeEvent(self, event):
        event.ignore()  # 忽略关闭请求，窗口保持不动

    def opendir_sub(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(Path(self.source_sub).parent.as_posix()))

    def save_and_close(self):
        self.save_button.setDisabled(True)
        srt_str_list = []
        
        # 从表格获取最新文本
        for i, data in enumerate(self.display_data):
            item = self.table.item(i, 2)
            text = item.text().strip() if item else data['text'].strip()
            
            if text:
                srt_str_list.append(f'{data["line"]}\n{data["startraw"]} --> {data["endraw"]}\n{text}')
        
        try:
            Path(self.source_sub).write_text("\n\n".join(srt_str_list), encoding="utf-8")
        except Exception as e:
            print(f"Save error: {e}")
        
        self.accept()