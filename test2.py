from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTimeEdit, QPushButton, QLabel
from PySide6.QtCore import QTime

class TimeWidget(QWidget):
    def __init__(self):
        super().__init__()

        # 创建布局
        layout = QVBoxLayout(self)

        # 创建时间选择组件
        self.time_edit = QTimeEdit(self)
        self.time_edit.setDisplayFormat("HH:mm:ss.zzz")

        # 设置默认时间为 02:15:26
        default_time = QTime(2, 15, 26,126)
        self.time_edit.setTime(default_time)

        # 添加到布局
        layout.addWidget(self.time_edit)

        # 创建一个按钮用于获取时间值
        self.get_time_button = QPushButton("Get Time", self)
        self.get_time_button.clicked.connect(self.display_time)
        layout.addWidget(self.get_time_button)

        # 用于展示时间值的标签
        self.time_label = QLabel("Selected Time: ", self)
        layout.addWidget(self.time_label)

    def display_time(self):
        # 获取选择的时间
        selected_time = self.time_edit.time()
        self.time_label.setText(f"Selected Time: {selected_time.msecsSinceStartOfDay()}")

if __name__ == "__main__":
    app = QApplication([])

    # 创建并显示主窗口
    main_window = TimeWidget()
    main_window.setWindowTitle("Time Selector")
    main_window.show()

    app.exec()
