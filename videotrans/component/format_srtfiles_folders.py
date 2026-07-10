# -*- coding: utf-8 -*-
"""
批量创建 SRT 字幕文件夹结构工具

用于将视频同名的 SRT 字幕文件自动复制到 pyVideoTrans 标准目录结构中，
以便在视频翻译时直接使用已有字幕，免去手动创建文件夹的麻烦。

使用方法：
    from videotrans.component.format_srtfiles_folders import FormatSrtFilesFolders
    window = FormatSrtFilesFolders()
    app_cfg.child_forms["format_srtfiles_folders"] = window
    window.show()
"""
import shutil
import threading
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QProgressBar,
    QTextEdit, QGroupBox,
)
from videotrans.configure.config import ROOT_DIR, tr, app_cfg,defaulelang
from videotrans.configure import contants
from videotrans.translator import LANGNAME_DICT, get_code


class _Worker(QThread):
    """后台线程：批量复制 SRT 文件"""
    progress = Signal(int, str)  # (当前索引, 状态文本)
    finished = Signal(int, int, int)  # (总数, 成功数, 跳过数)

    def __init__(self, video_files, lang_code, parent=None):
        super().__init__(parent)
        self.video_files = video_files
        self.lang_code = lang_code
        self._stop = False

    def run(self):
        total = len(self.video_files)
        ok = 0
        skip = 0
        for i, vpath in enumerate(self.video_files):
            if self._stop:
                break
            try:
                vpath = Path(vpath)
                srt_name = vpath.stem + ".srt"
                srt_path = vpath.parent / srt_name

                if not srt_path.exists():
                    self.progress.emit(i + 1, f"[Warning]: {vpath.name} (No SRT)")
                    skip += 1
                    continue

                folder_name = f"{vpath.stem}-{vpath.suffix.lstrip('.')}"
                target_dir = vpath.parent / "_video_out" / folder_name
                target_dir.mkdir(parents=True, exist_ok=True)

                target_srt = target_dir / f"{self.lang_code}.srt"
                shutil.copy2(str(srt_path), str(target_srt))

                self.progress.emit(i + 1, f"[OK]: {vpath.name} -> {target_dir.name}/{self.lang_code}.srt")
                ok += 1
            except Exception as e:
                self.progress.emit(i + 1, f"[Error]: {vpath.name} ({e})")
                skip += 1

        self.finished.emit(total, ok, skip)

    def stop(self):
        self._stop = True


class FormatSrtFilesFolders(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self._worker = None
        self._video_files = []
        self._init_ui()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        self.hide()
        event.ignore()

    def _init_ui(self):
        self.setWindowTitle(tr("formatsrtfile_window_title"))
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)
        # --- 提示 ---
        hint_text = QLabel(tr("hint_detail"))
        hint_text.setWordWrap(True)
        hint_text.setStyleSheet("color: #999; line-height: 1.4;")
        title_=QLabel(tr("hint_title"))
        title_.setStyleSheet("color:#ffff33")
        title_.setWordWrap(True)
        main_layout.addWidget(title_)
        main_layout.addWidget(hint_text)

        # --- 文件选择 ---
        file_row = QHBoxLayout()
        self.btn_select = QPushButton(tr("select_videos"))
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.setFixedHeight(36)
        self.btn_select.setIcon(self.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.btn_select.clicked.connect(self._select_files)

        self.lbl_file_count = QLabel(tr("no_files"))
        self.lbl_file_count.setStyleSheet("color: #888; font-size: 13px;")

        

        # --- 语言选择 ---
        lang_label = QLabel(tr("select_lang"))
        self.combo_lang = QComboBox()
        self.combo_lang.setMinimumWidth(200)
        self.combo_lang.addItems(list(LANGNAME_DICT.values()))
        self.combo_lang.setCurrentIndex(0)

        file_row.addWidget(self.btn_select)
        file_row.addWidget(self.lbl_file_count)
        file_row.addStretch()
        file_row.addWidget(lang_label)
        file_row.addWidget(self.combo_lang)
        self.help_doc = QPushButton(tr("help_doc"))
        self.help_doc.setCursor(Qt.PointingHandCursor)
        self.help_doc.clicked.connect(self._help)
        
        file_row.addWidget(self.help_doc)
        main_layout.addLayout(file_row)



        # --- 开始按钮 ---
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton(tr("start_btn"))
        self.btn_start.setFixedHeight(40)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_batch)
        btn_row.addWidget(self.btn_start)
        main_layout.addLayout(btn_row)

        # --- 进度条 ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # --- 结果日志 ---
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 12px;")
        main_layout.addWidget(self.txt_log, 1)

        # --- 状态标签 ---
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #333; font-size: 13px; font-weight: bold;")
        main_layout.addWidget(self.lbl_status)


    
    def _help(self):
        from videotrans.util.help_misc import open_url
        open_url("http://pyvideotrans.com/localsrt")
    
    def _select_files(self):
        exts = " ".join([f"*.{e}" for e in contants.VIDEO_EXTS])
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("select_videos"), "", f"Video Files ({exts})"
        )
        if files:
            self._video_files = files
            self.lbl_file_count.setText(tr("file_selected",len(files)))
            self.txt_log.clear()
            self.lbl_status.setText("")

    def _start_batch(self):
        if not self._video_files:
            self.lbl_status.setStyleSheet("color: #ffff00; font-size: 14px; font-weight: bold;")
            self.lbl_status.setText(tr("no_files"))
            return

        # 获取语言代码
        display_text = self.combo_lang.currentText()
        lang_code = get_code(show_text=display_text)
        if not lang_code:
            self.lbl_status.setStyleSheet("color: #ffff00; font-size: 14px; font-weight: bold;")
            self.lbl_status.setText(tr("no_lang"))
            return

        self.btn_start.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self._video_files))
        self.progress_bar.setValue(0)
        self.txt_log.clear()
        self.lbl_status.setText(tr("processing"))
        self.lbl_status.setStyleSheet("color: #E67E22; font-size: 13px; font-weight: bold;")

        self._worker = _Worker(self._video_files, lang_code, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, current, msg):
        self.progress_bar.setValue(current)
        self.txt_log.append(msg)

    def _on_finished(self, total, ok, skip):
        self.btn_start.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(tr("done",total, ok, skip))
        self.lbl_status.setStyleSheet("color: #27AE60; font-size: 13px; font-weight: bold;")
        self.txt_log.append(f"\n{tr('done',total, ok, skip)}")
