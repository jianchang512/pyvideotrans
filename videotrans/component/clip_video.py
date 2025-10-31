import sys
import os
from pathlib import Path
import subprocess
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QListWidget, QListWidgetItem, QCheckBox,
    QComboBox, QScrollArea, QPlainTextEdit, QScroller
)
from PySide6.QtCore import Qt, QThreadPool, QRunnable, Signal, QObject, QUrl, Slot, QSize, QThread
from PySide6.QtGui import QDesktopServices, QIcon

# 全局输出文件夹
from videotrans.util import tools
from videotrans.configure import config
from videotrans.configure.config import tr


output_folder = config.HOME_DIR



class Signals(QObject):
    progress = Signal(str)
    finished = Signal()
    load_error = Signal(str)

class ClipTask(QRunnable):
    def __init__(self, video_path, sub, line_num, subtitle_name, signals, mode,video_info=None):
        super().__init__()
        self.video_path = video_path
        self.sub = sub
        self.line_num = line_num
        self.subtitle_name = subtitle_name
        self.signals = signals
        self.mode = mode
        self.video_info=video_info

    def run(self):
        try:
            start_time = self.sub["startraw"].replace(',','.')
            duration = (self.sub["end_time"] - self.sub["start_time"])/1000.0
            if duration<0.1:
                self.signals.progress.emit(f"Failed:{self.line_num} : {duration}s")
                return
            output_dir = f'{output_folder}/{self.subtitle_name}-clip'
            os.makedirs(output_dir, exist_ok=True)

            if self.mode == 0:  # 默认
                output_path = os.path.join(output_dir, f"{self.line_num}.mp4")
                cmd = [
                    "-y", "-ss", str(start_time), "-t", str(duration),
                    "-i", self.video_path, ]
                if self.video_info['streams_audio']>0:
                    cmd+=["-c:v", "copy","-c:a", "copy"]
                else:
                    cmd+=['-an','-c:v','copy']

                cmd+=[
                    "-crf","18",output_path
                ]
                tools.runffmpeg(cmd, force_cpu=True)
            elif self.mode == 1:  # 仅视频
                output_path = os.path.join(output_dir, f"{self.line_num}.mp4")
                cmd = [
                    "-y", "-ss", str(start_time), "-t", str(duration),
                    "-i", self.video_path, "-an", "-c:v", "copy","-crf","18",
                    output_path
                ]
                tools.runffmpeg(cmd, force_cpu=True)
            elif self.mode == 2:  # 仅音频
                output_path = os.path.join(output_dir, f"{self.line_num}.wav")
                cmd = [
                    "-y","-ss", str(start_time), "-t", str(duration),
                    "-i", self.video_path, "-vn", "-c:a", "pcm_s16le",
                    output_path
                ]
                tools.runffmpeg(cmd, force_cpu=True)
            elif self.mode == 3:  # 分离
                # 无声视频
                video_path_out = os.path.join(output_dir, f"{self.line_num}.mp4")
                cmd_video = [
                    "-y", "-ss", str(start_time), "-t", str(duration),
                    "-i", self.video_path, "-an", "-c:v", "copy","-crf","18",
                    video_path_out
                ]
                tools.runffmpeg(cmd_video, force_cpu=True)

                # 音频
                if self.video_info['streams_audio']>0:
                    audio_path_out = os.path.join(output_dir, f"{self.line_num}.wav")
                    cmd_audio = [
                        "-y", "-ss", str(start_time), "-t", str(duration),
                        "-i", self.video_path, "-vn", "-c:a", "pcm_s16le",
                        audio_path_out
                    ]
                    tools.runffmpeg(cmd_audio, force_cpu=True)

            self.signals.progress.emit(f"Completed: {self.line_num}Line")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.signals.progress.emit(f"Failed: {self.line_num}: {error_msg}")
        except Exception as e:
            self.signals.progress.emit(f"Failed: {self.line_num}: {str(e)}")



class ClipVideoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("appTitle"))
        self.resize(1000, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

        self.video_path = None
        self.subtitle_path = None
        self.subtitles = None
        self.subtitle_name = None
        self.selected_lines = []
        self.thread_pool = QThreadPool()
        self.is_clipping = False
        self.signals = Signals()
        self.signals.progress.connect(self.update_progress)
        self.signals.finished.connect(self.clipping_finished)
        self.signals.load_error.connect(self.on_load_error)
        self.total_clips = 0
        self.completed_clips = 0
        self.failed_clips = []
        self.open_button = None
        self.active_tasks = 0

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 文件选择
        file_layout = QHBoxLayout()
        self.video_label = QLabel(tr("noVideoSelected"))
        video_btn = QPushButton(tr("selectVideoToEdit"))
        video_btn.clicked.connect(self.select_video)
        video_btn.setMinimumSize(QSize(200, 35))
        video_btn.setCursor(Qt.PointingHandCursor)
        file_layout.addWidget(video_btn)
        file_layout.addWidget(self.video_label)

        self.subtitle_label = QLabel(tr('noSubtitleSelected'))
        subtitle_btn = QPushButton(tr('selectCorrespondingSubtitle'))
        subtitle_btn.setMinimumSize(QSize(200, 35))
        subtitle_btn.clicked.connect(self.select_subtitle)
        subtitle_btn.setCursor(Qt.PointingHandCursor)
        file_layout.addWidget(subtitle_btn)
        file_layout.addWidget(self.subtitle_label)

        # 输出模式下拉列表
        self.output_mode = QComboBox()
        self.output_mode.addItems([
            tr("optionDefault"),
            tr("optionVideoOnly"),
            tr("optionAudioOnly"),
            tr("optionSeparateAV")
        ])
        file_layout.addWidget(self.output_mode)
        file_layout.addStretch() 
        layout.addLayout(file_layout)



        # 批量选择按钮
        batch_layout = QHBoxLayout()
        self.select_all_btn = QPushButton(tr("selectAll"))
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.setVisible(False)
        batch_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton(tr("deselectAll"))
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.deselect_all_btn.setCursor(Qt.PointingHandCursor)
        self.deselect_all_btn.setVisible(False)
        batch_layout.addWidget(self.deselect_all_btn)

        self.invert_btn = QPushButton(tr("invertSelection"))
        self.invert_btn.clicked.connect(self.invert_selection)
        self.invert_btn.setVisible(False)
        self.invert_btn.setCursor(Qt.PointingHandCursor)
        batch_layout.addWidget(self.invert_btn)
        batch_layout.addStretch()
        layout.addLayout(batch_layout)

        # 字幕列表
        self.subtitle_list = QListWidget()
        QScroller.ungrabGesture(self.subtitle_list.viewport())
        self.subtitle_list.setAutoScroll(False)
        layout.addWidget(self.subtitle_list)

        # 底部按钮
        btn_layout = QHBoxLayout()

        self.clip_btn = QPushButton(tr("startEditing"))
        self.clip_btn.setCursor(Qt.PointingHandCursor)
        self.clip_btn.setMinimumSize(QSize(200, 35))
        self.clip_btn.clicked.connect(self.start_clipping)
        btn_layout.addWidget(self.clip_btn)

        self.clear_btn = QPushButton(tr("clearSelection"))
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setMaximumWidth(150)
        self.clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.clear_btn)
        
        self.open_button = QPushButton(tr("openOutputDirectory"))
        self.open_button.setMaximumWidth(200)
        self.open_button.setCursor(Qt.PointingHandCursor)
        self.open_button.clicked.connect(self.open_output_folder)
        self.open_button.hide()
        btn_layout.addWidget(self.open_button)
        

        layout.addLayout(btn_layout)

        # 进度标签
        self.progress_label = QPlainTextEdit("")
        self.progress_label.setStyleSheet('color:#2196f3;font-size:14px')
        self.progress_label.setReadOnly(True)
        self.progress_label.setFixedHeight(80)
        layout.addWidget(self.progress_label)
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setLayout(layout)

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("selectVideo"), config.settings.get('last_opendir',''), "Video Files (*.mp4 *.avi *.mkv)")
        if path:
            self.video_path = path
            self.video_label.setText(os.path.basename(path))
            config.settings['last_opendir']=Path(path).parent.as_posix()

    def select_subtitle(self):
        global output_folder
        path, _ = QFileDialog.getOpenFileName(self, tr("selectSubtitle"), config.settings.get('last_opendir',''), "Subtitle Files (*.srt *.ass *.vtt)")
        if path:
            self.progress_label.setPlainText(tr("renderingSubtitles"))
            self.subtitle_list.clear()
            output_folder=Path(path).parent.as_posix()
            self.subtitle_path = path
            self.subtitle_name = Path(path).name
            self.subtitle_label.setText(self.subtitle_name)


            self.subtitles = tools.get_subtitle_from_srt(self.subtitle_path)  # Reload if needed
            for i, it in enumerate(self.subtitles):
                item = QListWidgetItem()
                check = QCheckBox(f"第{i+1}行 [{(it['end_time']-it['start_time'])/1000.0}s] {it['startraw']}->{it['endraw']}  {it['text']}")
                self.subtitle_list.addItem(item)
                self.subtitle_list.setItemWidget(item, check)
                item.setSizeHint(check.sizeHint() + QSize(0, 10))  # 增加垂直间距
            self.progress_label.setPlainText(f"{tr('renderCompleteOutputTo')}:{output_folder}/{self.subtitle_name}-clip")
            self.select_all_btn.setVisible(True)
            self.deselect_all_btn.setVisible(True)
            self.invert_btn.setVisible(True)
            config.settings['last_opendir']=Path(self.subtitle_path).parent.as_posix()

    @Slot(str)
    def on_load_error(self, error):
        self.progress_label.setPlainText(f"{tr('subtitleRenderError')}: {error}")

    def select_all(self):
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            check = self.subtitle_list.itemWidget(item)
            check.setChecked(True)

    def deselect_all(self):
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            check = self.subtitle_list.itemWidget(item)
            check.setChecked(False)

    def invert_selection(self):
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            check = self.subtitle_list.itemWidget(item)
            check.setChecked(not check.isChecked())

    def clear_all(self):
        self.video_path = None
        self.subtitle_path = None
        self.subtitles = None
        self.subtitle_name = None
        self.selected_lines = []
        self.video_label.setText(tr("noVideoSelected"))
        self.subtitle_label.setText(tr("noSubtitleSelected"))
        self.subtitle_list.clear()
        self.progress_label.setPlainText("")
        self.clip_btn.setText(tr("startEditing"))
        self.is_clipping = False
        self.total_clips = 0
        self.completed_clips = 0
        self.failed_clips = []
        self.output_mode.setCurrentIndex(0)
        self.active_tasks = 0
        self.open_button.hide()
        self.select_all_btn.setVisible(False)
        self.deselect_all_btn.setVisible(False)
        self.invert_btn.setVisible(False)

    def start_clipping(self):
        if self.is_clipping:
            self.stop_clipping()
            return

        if not self.video_path or not self.subtitle_name:
            self.progress_label.setPlainText(tr("promptSelectVideoAndSubtitle"))
            return

        self.selected_lines = []
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            check = self.subtitle_list.itemWidget(item)
            if check.isChecked():
                self.selected_lines.append(i + 1)  # 1-based

        if not self.selected_lines:
            self.progress_label.setPlainText(tr("promptSelectAtLeastOneSubtitle"))
            return

        mode = self.output_mode.currentIndex()

        self.is_clipping = True
        self.clip_btn.setText(tr("stopImmediately"))
        self.total_clips = len(self.selected_lines)
        self.completed_clips = 0
        self.failed_clips = []
        self.open_button.show()
        self.active_tasks = self.total_clips
        self.progress_label.setPlainText(f"Total:{self.total_clips}")
        task = Worker(parent=self,mode=mode)
        task.uito.connect(self.update_progress)
        task.start()



    def stop_clipping(self):
        self.thread_pool.clear()
        self.is_clipping = False
        self.clip_btn.setText(tr("startEditing"))
        self.progress_label.setPlainText(tr("statusStopped"))
        self.active_tasks = 0

    def update_progress(self, message):
        if message.startswith("Error:"):
            self.stop_clipping()
            return
        if  message.startswith("Completed:"):
            self.completed_clips += 1
        elif message.startswith("Failed:"):
            self.failed_clips.append(message)
        self.active_tasks -= 1
        self.progress_label.setPlainText(
            f" {self.completed_clips}/{self.total_clips},  "
            f"Error: {len(self.failed_clips)}\n" + "\n".join(self.failed_clips)
        )
        if self.active_tasks <= 0 and self.is_clipping:
            self.signals.finished.emit()

    def clipping_finished(self):
        self.is_clipping = False
        self.clip_btn.setText(tr("startEditing"))
        self.active_tasks = 0


    def open_output_folder(self):
        output_dir = f'{output_folder}/{self.subtitle_name}-clip'
        QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))

class Worker(QThread):
    uito = Signal(str)

    def __init__(self, *,
        parent:ClipVideoWindow,
        mode=None):
        super().__init__(parent=parent)
        self.parent=parent
        self.mode=mode

    def run(self):
        video_info=tools.get_video_info(self.parent.video_path)
        if video_info['streams_audio']==0 and self.mode == 2:
            self.uito.emit(f"Error:{tr('errorNoAudioTrackForAudioOnly')}")
            return
        for line_num in self.parent.selected_lines:
            sub = self.parent.subtitles[line_num - 1]
            task = ClipTask(self.parent.video_path, sub, line_num, self.parent.subtitle_name, self.parent.signals, self.mode,video_info)
            self.parent.thread_pool.start(task)

