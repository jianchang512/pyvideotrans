from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QCheckBox, QLabel, QLineEdit, QPlainTextEdit, QFrame)

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        # 垂直布局
        v_layout = QVBoxLayout(self)
        v_layout.setSpacing(5)

        # 将布局添加到 QScrollArea
        scroll_area = QScrollArea()
        v_layout.addWidget(scroll_area)

        # 创建一个 QWidget 作为 QScrollArea 的内容
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)

        # 在内容 widget 中添加布局
        content_layout = QVBoxLayout(content_widget)

        #添加 n 个元素到布局
        n = 10 # 只是一个示例值，根据实际需要改变 n 的值
        for i in range(n):
            # 创建一个新的布局
            new_h_layout = QHBoxLayout()
            new_h_layout.addWidget(QCheckBox("Checkbox " + str(i)))
            new_h_layout.addWidget(QLabel("Label " + str(i)))
            content_layout.addLayout(new_h_layout)

            # 创建一个 QLineEdit 元素
            content_layout.addWidget(QLineEdit())

            # 创建一个 QPlainTextEdit 元素
            content_layout.addWidget(QPlainTextEdit())

            # 加入一个5px的间距和水平线，然后再加入5px的间距
            if i < n - 1:  # 只在垂直布局元素之间加入水平线
                content_layout.addSpacing(5)

                hline = QFrame()
                hline.setFrameShape(QFrame.HLine)
                hline.setFrameShadow(QFrame.Sunken)
                content_layout.addWidget(hline)

                content_layout.addSpacing(5)

        self.show()

app = QApplication([])
window = MyWindow()
app.exec_()