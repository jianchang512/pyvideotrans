from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, Qt

from videotrans.configure._paths import ROOT_DIR
from videotrans.configure.config import params,tr


class _Bottom_btn_layout(object):
    def openout_fn(self):
        out=self.output_data.text()
        Path(out).mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(out))

    def saveout_fn(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, tr('selectsavedir'),'')
        if not dirname:return
        self.output_data.setText(dirname or f'{ROOT_DIR}/output')
        if hasattr(self,'output_key'):
            params[self.output_key] = dirname
            params.save()

    def get_bottom_btn_layout(self):
        self.open_output = QtWidgets.QPushButton()
        self.open_output.setObjectName("open_output")
        self.open_output.setCursor(Qt.PointingHandCursor)
        self.open_output.setText(tr("Open output directory"))
        self.open_output.clicked.connect(self.openout_fn)

        self.set_output = QtWidgets.QPushButton()
        self.set_output.setObjectName("set_output")
        self.set_output.setCursor(Qt.PointingHandCursor)
        self.set_output.setText(tr("Select where to save the processed output resources"))
        self.set_output.clicked.connect(self.saveout_fn)

        self.output_data=QtWidgets.QLineEdit()
        self.output_data.setReadOnly(True)
        if hasattr(self,'output_key'):
            default_output=params.get(self.output_key) or f'{ROOT_DIR}/output'
            # 各功能直接把结果保存到该目录，但它可能还不存在：例如首次运行时的 output 目录，或选择后又被删除的目录
            try:
                Path(default_output).mkdir(parents=True, exist_ok=True)
            except OSError:
                # 无法创建时（例如所在的移动硬盘已拔出）仍照常打开窗口
                pass
            self.output_data.setPlaceholderText(f'{tr("Output directory")}:{default_output}')
            self.output_data.setText(default_output)
        self.output_data.setStyleSheet("""QLineEdit {border: none; background: transparent;}""")


        bottom_btn_layout = QtWidgets.QHBoxLayout()
        bottom_btn_layout.setSpacing(5)
        bottom_btn_layout.addWidget(self.open_output)
        bottom_btn_layout.addWidget(self.set_output)
        bottom_btn_layout.addWidget(self.output_data)
        return bottom_btn_layout
