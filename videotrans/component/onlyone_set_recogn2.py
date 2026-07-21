from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize, QUrl, QThread, Signal
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSplitter, QApplication
)

from videotrans.configure.config import ROOT_DIR, tr, settings, logger
from videotrans.util import tools


class EditRecognResultDialog2(QDialog):
    def __init__(
            self,
            target_sub: str = None,       # 二次识别后的字幕
            target_wav: str = None,       # 用于播放的完整配音音频
            novoice_mp4: str = None,      # 处理后的无声视频
            parent=None,
    ):
        super().__init__()
        self.parent = parent
        self.source_sub = target_sub
        self.source_wav = target_wav
        self.novoice_mp4 = novoice_mp4
        self.srt_list_dict = []

        self.setWindowTitle(tr("zimubianjitishi"))
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setMinimumWidth(1200)
        self.setMinimumHeight(700)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.WindowTitleHint |
            Qt.CustomizeWindowHint |
            Qt.WindowMaximizeButtonHint
        )

        self.count_down = int(float(settings.get('countdown_sec', 1)))
        self._target_end_ms = -1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

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

        # ===================== Splitter: video (top) + subtitles (bottom) =====================
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setHandleWidth(6)

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #1a1a1a;")
        self.video_widget.setMinimumHeight(150)

        self.video_hint = QLabel(tr("Click on a subtitle below to play video"))
        self.video_hint.setStyleSheet("color:#ffcc00; font-size:14px; background-color:transparent;")
        self.video_hint.setAlignment(Qt.AlignCenter)
        self.video_hint.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.video_status = QLabel("")
        self.video_status.setStyleSheet("color:#aaaaaa; font-size:12px;")
        self.video_status.setAlignment(Qt.AlignCenter)

        from PySide6.QtWidgets import QStackedLayout
        self._stack = QStackedLayout()
        self._stack.addWidget(self.video_widget)
        self._stack.addWidget(self.video_hint)
        self._stack.setCurrentIndex(1)

        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.video_status)
        top_layout.addLayout(self._stack, 1)
        self.splitter.addWidget(top_container)

        # --- Bottom area ---
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.loading_widget = QWidget()
        self.loading_label = QLabel(tr('The subtitle editing interface is rendering'), self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        load_layout = QVBoxLayout(self.loading_widget)
        load_layout.addWidget(self.loading_label)
        bottom_layout.addWidget(self.loading_widget)

        self.table = QTableWidget()
        self.table.setVisible(False)
        bottom_layout.addWidget(self.table, 1)

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

        bottom_layout_row = QHBoxLayout()
        bottom_layout_row.addStretch()
        bottom_layout_row.addWidget(self.save_button)
        bottom_layout_row.addWidget(self.save_button2)
        bottom_layout_row.addWidget(self.opendir_button)
        bottom_layout_row.addWidget(cancel_button)
        bottom_layout_row.addStretch()
        bottom_layout.addLayout(bottom_layout_row)

        self.splitter.addWidget(bottom_container)
        self.splitter.setSizes([int(parent.height * 0.22), int(parent.height * 0.68)])

        main_layout.addWidget(self.splitter, 1)

        QTimer.singleShot(10, self.load_table)

    # ===================== Audio-driven sync =====================
    def _ensure_players(self):
        if hasattr(self, '_players_created'):
            return
        self._players_created = True
        self.video_player = QMediaPlayer()
        self.video_player.setVideoOutput(self.video_widget)
        self.video_player.positionChanged.connect(self._on_audio_position_changed)
        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)
        self.audio_player.positionChanged.connect(self._on_audio_position_changed)

        # Timer to poll video position (more reliable than signal)
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_video_position)

    def _on_audio_position_changed(self, position):
        if self._target_end_ms > 0 and position >= self._target_end_ms:
            self._stop_and_display()

    def _poll_video_position(self):
        if self._video_end_ms <= 0:
            return
        try:
            pos = self.video_player.position()
            if pos >= self._video_end_ms:
                self._stop_and_display()
        except Exception:
            pass

    def _stop_and_display(self):
        self._poll_timer.stop()
        try:
            self.video_player.pause()
            self.audio_player.stop()
        except Exception:
            pass
        self._video_end_ms = -1
        self._target_end_ms = -1
        self.video_status.setText(tr("Playback stopped"))
    def _play_segment(self, start_ms, end_ms):
        self._ensure_players()
        self._pending_start = start_ms
        self._pending_end = end_ms

        self._players_pending = 0
        try:
            if self.novoice_mp4 and Path(self.novoice_mp4).exists():
                if not self.video_player.source().toString():
                    self.video_player.setSource(QUrl.fromLocalFile(self.novoice_mp4))
                    self._players_pending += 1
            if self.source_wav and Path(self.source_wav).exists():
                if not self.audio_player.source().toString():
                    self.audio_player.setSource(QUrl.fromLocalFile(self.source_wav))
                    self._players_pending += 1
        except Exception as e:
            self.video_status.setText(f"Load failed: {e}")
            return

        if self._players_pending > 0:
            for player in [self.video_player, self.audio_player]:
                try:
                    player.mediaStatusChanged.disconnect(self._on_media_ready)
                except BaseException:
                    pass
                player.mediaStatusChanged.connect(self._on_media_ready)
            return

        self._do_play(start_ms, end_ms)

    def _on_media_ready(self, status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status in (QMediaPlayer.MediaStatus.BufferedMedia, QMediaPlayer.MediaStatus.LoadedMedia):
            self._players_pending -= 1
            if self._players_pending <= 0:
                self._disconnect_media_signals()
                self._do_play(self._pending_start, self._pending_end)

    def _disconnect_media_signals(self):
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, message="Failed to disconnect")
        for player in [self.video_player, self.audio_player]:
            for sig in [player.positionChanged, player.mediaStatusChanged]:
                try:
                    sig.disconnect()
                except (TypeError, RuntimeError):
                    pass

    def _do_play(self, start_ms, end_ms):
        self._video_end_ms = end_ms
        self._target_end_ms = end_ms
        try:
            self.video_player.setPosition(start_ms)
            self.audio_player.setPosition(start_ms)
        except Exception:
            pass
        self.video_player.play()
        self.audio_player.play()
        self._stack.setCurrentIndex(0)
        self.video_status.setText(f"\u23F5 {tools.ms_to_time_string(ms=start_ms)} \u2192 {tools.ms_to_time_string(ms=end_ms)}")
        #self.stop_countdown()
        # Start polling timer for reliable video position tracking
        if hasattr(self, '_poll_timer'):
            self._poll_timer.start(100)

    def _stop_playback(self):
        self._target_end_ms = -1
        self._video_end_ms = -1
        if hasattr(self, '_poll_timer'):
            self._poll_timer.stop()
        if not hasattr(self, '_players_created'):
            return
        try:
            self.video_player.stop()
            self.audio_player.stop()
        except Exception as e:
            logger.exception(e, exc_info=True)

    def _release_media(self):
        if not hasattr(self, '_players_created'):
            return
        self._stop_playback()
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, message="Failed to disconnect")
        for player in [self.video_player, self.audio_player]:
            for sig in [player.positionChanged, player.mediaStatusChanged]:
                try:
                    sig.disconnect()
                except (TypeError, RuntimeError):
                    pass
        if hasattr(self, '_poll_timer'):
            try:
                self._poll_timer.timeout.disconnect()
            except (TypeError, RuntimeError):
                pass
        try:
            self.video_player.setSource(QUrl())
        except Exception:
            pass
        try:
            self.audio_player.setSource(QUrl())
        except Exception:
            pass
        import gc
        gc.collect()

    # ===================== Table =====================
    def load_table(self):
        try:
            self.srt_list_dict = tools.get_subtitle_from_srt(self.source_sub)
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels([
                tr("Line"), tr('Subtitles') + tr("Time Axis"), "\u23F5", tr("Subtitle Text")
            ])

            self.table.setShowGrid(False)
            self.table.setAlternatingRowColors(False)
            self.table.setWordWrap(False)
            self.table.setMouseTracking(False)
            self.table.setFocusPolicy(Qt.NoFocus)
            self.table.setSelectionMode(QAbstractItemView.NoSelection)

            v_header = self.table.verticalHeader()
            v_header.setVisible(False)
            v_header.setSectionResizeMode(QHeaderView.Fixed)
            v_header.setDefaultSectionSize(26)

            h_header = self.table.horizontalHeader()
            h_header.setStretchLastSection(True)
            h_header.setSectionResizeMode(0, QHeaderView.Fixed)
            h_header.setSectionResizeMode(1, QHeaderView.Fixed)
            h_header.setSectionResizeMode(2, QHeaderView.Fixed)

            self.table.setColumnWidth(0, 50)
            self.table.setColumnWidth(1, 230)
            self.table.setColumnWidth(2, 30)

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
                QPushButton#playBtn {
                    background-color: #3a7c3a;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    font-size: 9px;
                    padding: 1px 4px;
                    min-width: 20px;
                    max-width: 24px;
                }
                QPushButton#playBtn:hover {
                    background-color: #4caf50;
                }
                QPushButton#playBtn:pressed {
                    background-color: #2e5e2e;
                }
            """)

            self.display_data = []
            for item in self.srt_list_dict:
                duration = (item['end_time'] - item['start_time']) / 1000.0
                time_str = f"{item['startraw']} --> {item['endraw']} ({duration:.1f}s)"
                self.display_data.append({
                    'line': item['line'],
                    'time_str': time_str,
                    'text': item['text'],
                    'startraw': item['startraw'],
                    'endraw': item['endraw'],
                    'start_time': item['start_time'],
                    'end_time': item['end_time'],
                })

            total_rows = len(self.display_data)
            self.table.setRowCount(total_rows)

            self.loading_widget.setVisible(False)
            self.table.setVisible(True)

            QTimer.singleShot(0, lambda: self._load_remaining(0))

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)
            if self.parent:
                self.raise_()
                self.activateWindow()
                self._play_segment(0,5)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.loading_label.setText(f"Error: {e}")

    def _batch_fill(self, start_row, end_row):
        for row in range(start_row, end_row):
            data = self.display_data[row]

            item0 = QTableWidgetItem(str(data['line']))
            item0.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 0, item0)

            item1 = QTableWidgetItem(data['time_str'])
            item1.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, item1)

            btn = QPushButton("\u23F5")
            btn.setObjectName("playBtn")
            btn.setCursor(Qt.PointingHandCursor)
            s = data['start_time']
            e = data['end_time']
            btn.clicked.connect(lambda checked=False, _s=s, _e=e: self._play_segment(_s, _e))
            self.table.setCellWidget(row, 2, btn)

            item3 = QTableWidgetItem(data['text'])
            item3.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self.table.setItem(row, 3, item3)

    def _load_remaining(self, start_row):
        total = len(self.display_data)
        batch_size = 50
        end_row = min(start_row + batch_size, total)
        self._batch_fill(start_row, end_row)
        if end_row < total:
            QTimer.singleShot(0, lambda: self._load_remaining(end_row))

    # ===================== Actions =====================
    def cancel_and_close(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        self._release_media()
        self.reject()

    def update_countdown(self):
        self.count_down -= 1
        if self.stop_button:
            self.stop_button.setText(f"{tr('Click here to stop the countdown')}({self.count_down})")
        if self.count_down <= 0:
            self.timer.stop()
            self.save_and_close()

    def stop_countdown(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        if hasattr(self, 'stop_button') and self.stop_button:
            try:
                self.stop_button.deleteLater()
            except RuntimeError:
                pass
            self.stop_button = None
        if hasattr(self, 'prompt_label') and self.prompt_label:
            try:
                self.prompt_label.deleteLater()
            except RuntimeError:
                pass
            self.prompt_label = None

    def replace_text(self):
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()
        if not search_text:
            return
        self.table.setUpdatesEnabled(False)
        for i, data in enumerate(self.display_data):
            if search_text in data['text']:
                new_text = data['text'].replace(search_text, replace_text)
                data['text'] = new_text
                item = self.table.item(i, 3)
                if item:
                    item.setText(new_text)
        self.table.setUpdatesEnabled(True)

    def save_and_close2(self):
        self._release_media()
        self.accept()

    def closeEvent(self, event):
        event.ignore()

    def opendir_sub(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(Path(self.source_sub).parent.as_posix()))

    def save_and_close(self):
        self.save_button.setDisabled(True)
        srt_str_list = []
        for i, data in enumerate(self.display_data):
            item = self.table.item(i, 3)
            text = item.text().strip() if item else data['text'].strip()
            if text:
                srt_str_list.append(f'{data["line"]}\n{data["startraw"]} --> {data["endraw"]}\n{text}')
        try:
            Path(self.source_sub).write_text("\n\n".join(srt_str_list), encoding="utf-8")
        except Exception as e:
            logger.exception(f"Save error: {e}", exc_info=True)
        self._release_media()
        self.accept()
