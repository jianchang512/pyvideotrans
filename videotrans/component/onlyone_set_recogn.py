from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize, QUrl, QThread, Signal, QSettings
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSplitter,QApplication
)

from videotrans.component._danspmixin import DanspMixin
from videotrans.configure.config import ROOT_DIR, tr, settings, logger, app_cfg
from videotrans.util._srt_parse import get_subtitle_from_srt, ms_to_time_string


class EditRecognResultDialog(QDialog,DanspMixin):
    def __init__(
            self,
            parent=None,
    ):
        super().__init__()

        self.parent = parent
        self.source_sub = app_cfg.onlyone_source_sub
        self.srt_list_dict = []

        self.setWindowTitle(tr("zimubianjitishi"))
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setMinimumWidth(parent.screen_size[0]*0.95)
        self.setMinimumHeight(parent.screen_size[1]*0.9)
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
        self.prompt_label.setStyleSheet('color:#aaaaaa')
        hstop.addWidget(self.prompt_label)
        self.stop_button = QPushButton(f"{tr('Click here to stop the countdown')}({self.count_down})")
        self.stop_button.setStyleSheet("color:#ffff00")
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setMinimumSize(QSize(300, 35))
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

        # --- Top area: video display (players created lazily on first play) ---
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #1a1a1a;")
        self.video_widget.setMinimumHeight(150)

        # Hint label over video area
        self.video_hint = QLabel(tr("Click on a subtitle below to play video"))
        self.video_hint.setStyleSheet("color:#ffcc00;  background-color:transparent;")
        self.video_hint.setAlignment(Qt.AlignCenter)
        self.video_hint.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Status label above video
        self.video_status = QLabel("")
        self.video_status.setStyleSheet("color:#aaaaaa; font-size:12px;")

        from PySide6.QtWidgets import QStackedLayout

        # --- 1. 创建按钮并添加到布局 ---
        self.btn_minus = QPushButton("-")
        self.btn_minus.setToolTip(tr('Decrease table font size'))
        self.btn_minus.setFixedWidth(30)
        self.btn_plus = QPushButton("+")
        self.btn_plus.setToolTip(tr('Increase table font size'))
        self.btn_plus.setFixedWidth(30)
        self.btn_plus.clicked.connect(lambda: self.change_table_font_size(2))
        self.btn_minus.clicked.connect(lambda: self.change_table_font_size(-2))


        videostatus_layout=QHBoxLayout()
        videostatus_layout.setContentsMargins(0, 2, 0, 2)
        self.stop_play_btn=QPushButton()
        self.stop_play_btn.setToolTip(tr('Click to pause playback'))
        self.stop_play_btn.setText(tr('Click to pause playback'))
        self.stop_play_btn.clicked.connect(self._pause_play)
        self.stop_play_btn.setCursor(Qt.PointingHandCursor)
        self.stop_play_btn.hide()
        videostatus_layout.addStretch()
        videostatus_layout.addWidget(self.btn_minus)
        videostatus_layout.addWidget(self.btn_plus)

        videostatus_layout.addWidget(self.stop_play_btn)
        videostatus_layout.addWidget(self.video_status)
        videostatus_layout.addStretch()

        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)


        # Stack hint over video so they overlap in the same area
        self._stack = QStackedLayout()
        self._stack.addWidget(self.video_widget)    # index 0: video
        self._stack.addWidget(self.video_hint)       # index 1: hint (on top)
        self._stack.setCurrentIndex(1)  # show hint initially
        top_layout.addLayout(self._stack)
        top_layout.addLayout(videostatus_layout)
        self.splitter.addWidget(top_container)

        # --- Bottom area: subtitle table + buttons ---
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Loading
        self.loading_widget = QWidget()
        self.loading_label = QLabel(tr('The subtitle editing interface is rendering'), self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        load_layout = QVBoxLayout(self.loading_widget)
        load_layout.addWidget(self.loading_label)
        bottom_layout.addWidget(self.loading_widget)

        # Table Widget
        self.table = QTableWidget()
        self.table.setVisible(False)

        sets = QSettings("pyvideotrans", "settings")
        fontsize = int(sets.value("danshipin_table_fontsize", 0))
        if fontsize>0:
            default_font = self.table.font()
            default_font.setPointSize(fontsize)  # 设置为 16px
            self.table.setFont(default_font)
            self.table.horizontalHeader().setFont(default_font)
            self.table.verticalHeader().setFont(default_font)


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
        # Splitter ratio: video 1/4, subtitles 3/4
        self.splitter.setSizes([int(parent.height * 0.22), int(parent.height * 0.68)])

        main_layout.addWidget(self.splitter, 1)
        # 延迟加载表格，表格就绪后再加载媒体
        QTimer.singleShot(200, self.load_table)


    # 暂停播放
    def _pause_play(self):
        self.video_player.pause()
        self._target_end_ms = -1
        self.video_status.setText(tr("Playback stopped"))
        self.stop_play_btn.hide()
    # 创建播放器
    def _ensure_players(self):
        if hasattr(self, '_players_created'):
            return
        self._players_created = True
        self.video_player = QMediaPlayer()
        self.video_player.setVideoOutput(self.video_widget)
        self.audio_output = QAudioOutput()
        self.video_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0) # 1.0 表示 100% 音量
        self.video_player.positionChanged.connect(self._on_video_position_changed)

    # 播放进度触发
    def _on_video_position_changed(self, position):
        if self._target_end_ms > 0 and position >= self._target_end_ms:
            self._pause_play()

    def _play_segment(self, start_ms, end_ms):
        """Start synchronized video+audio playback for a segment."""
        self._ensure_players()
        self.stop_play_btn.show()
        self._pending_start = start_ms
        self._pending_end = end_ms
        self._players_pending = 0
        try:
            if app_cfg.onlyone_name and Path(app_cfg.onlyone_name).exists():
                if not self.video_player.source().toString():
                    self.video_player.setSource(QUrl.fromLocalFile(app_cfg.onlyone_name))
                    self._players_pending += 1
            else:
                self.video_status.setText(tr('No silent video frames generated yet'))
        except Exception as e:
            self.video_status.setText(f"Load failed: {e}")
            return

        if self._players_pending > 0:
            try:
                self.video_player.mediaStatusChanged.disconnect(self._on_media_ready)
            except BaseException:
                pass
            self.video_player.mediaStatusChanged.connect(self._on_media_ready)
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
        try:
            self.video_player.mediaStatusChanged.disconnect()
        except (TypeError, RuntimeError):
            pass

    def _do_play(self, start_ms, end_ms):
        self._target_end_ms = end_ms
        self.video_player.setPosition(start_ms)
        self.video_player.play()
        self._stack.setCurrentIndex(0)
        self.video_status.setText(f"\u23F5 {ms_to_time_string(ms=start_ms)} → {ms_to_time_string(ms=end_ms)}")


    def _stop_playback(self):
        self._target_end_ms = -1
        if not hasattr(self, '_players_created'):
            return
        try:
            self.video_player.stop()
        except Exception as e:
            logger.exception(e, exc_info=True)

    def _release_media(self):
        """Release media resources before dialog closes."""
        if not hasattr(self, '_players_created'):
            return
        self._stop_playback()
        import warnings
        warnings.filterwarnings("ignore", category=RuntimeWarning, message="Failed to disconnect")
        # Disconnect all signals safely
        for sig in [self.video_player.positionChanged, self.video_player.mediaStatusChanged]:
            try:
                sig.disconnect()
            except (TypeError, RuntimeError):
                pass
        # Clear sources to release file handles
        try:
            self.video_player.setSource(QUrl())
        except Exception:
            pass
        import gc
        gc.collect()

    # ===================== Table =====================
    def load_table(self):
        try:
            self.srt_list_dict=get_subtitle_from_srt(self.source_sub)
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels([
                tr("Line"), '\u270D'+tr("Start Time")+'/s', '\u270D'+tr("End Time")+'/s','\u23F5', '\u270D'+tr("Subtitle Text")
            ])

            self.table.setShowGrid(False)
            self.table.setAlternatingRowColors(False)
            self.table.setWordWrap(True)
            self.table.setMouseTracking(False)
            self.table.setFocusPolicy(Qt.NoFocus)
            self.table.setSelectionMode(QAbstractItemView.NoSelection)

            v_header = self.table.verticalHeader()
            v_header.setVisible(False)
            v_header.setSectionResizeMode(QHeaderView.ResizeToContents)
            v_header.setMinimumSectionSize(26)

            h_header = self.table.horizontalHeader()
            h_header.setStretchLastSection(True)
            h_header.setSectionResizeMode(0, QHeaderView.Fixed)
            h_header.setSectionResizeMode(1, QHeaderView.Fixed)
            h_header.setSectionResizeMode(2, QHeaderView.Fixed)
            h_header.setSectionResizeMode(3, QHeaderView.Fixed)

            self.table.setColumnWidth(0, 120)
            self.table.setColumnWidth(1, 120)
            self.table.setColumnWidth(2, 120)
            self.table.setColumnWidth(3, 30)

            self.table.setStyleSheet(self.table_style_css)

            # Precompute display data
            self.display_data = []
            for item in self.srt_list_dict:
                self.display_data.append({
                    'line': item['line'],
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

            # Render all rows via timers — never block the UI
            QTimer.singleShot(0, lambda: self._load_remaining(0))

            # Media is loaded lazily on first play-button click — no preload

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)
            self._play_segment(0,5)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.loading_label.setText(f"Error: {e}")
        finally:
            if self.parent:
                self.raise_()
                self.activateWindow()
            return True

    def _batch_fill(self, start_row, end_row):
        for row in range(start_row, end_row):
            data = self.display_data[row]

            # 0: Line
            item0 = QTableWidgetItem(str(data['line'])+f'({(data["end_time"]-data["start_time"])/1000.0}s)')
            item0.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 0, item0)

            # 1: Time
            item1 = QTableWidgetItem(str(int(data['start_time'])/1000.0))
            item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self.table.setItem(row, 1, item1)

            item2 = QTableWidgetItem(str(int(data['end_time'])/1000.0))
            item2.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, item2)

            # 2: Play button
            btn = QPushButton("\u23F5")
            btn.setObjectName("playBtn")
            btn.setCursor(Qt.PointingHandCursor)
            s = data['start_time']
            e = data['end_time']
            btn.clicked.connect(lambda checked=False, _s=s, _e=e: self._play_segment(_s, _e))
            self.table.setCellWidget(row, 3, btn)

            # 3: Text (editable)
            item3 = QTableWidgetItem(data['text'])
            item3.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            self.table.setItem(row, 4, item3)

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
            self.stop_button.deleteLater()
            self.prompt_label.deleteLater()
            self.timer=None


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
        self.stop_countdown()
        self._release_media()
        self.accept()

    def closeEvent(self, event):
        event.ignore()

    def opendir_sub(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(Path(self.source_sub).parent.as_posix()))

    def save_and_close(self):
        self.stop_countdown()
        self.save_button.setDisabled(True)
        srt_str_list = []
        for i, data in enumerate(self.display_data):
            start_time = self.table.item(i, 1)
            end_time = self.table.item(i, 2)
            start_raw=ms_to_time_string(ms=int(float(start_time.text().strip())*1000))
            end_raw=ms_to_time_string(ms=int(float(end_time.text().strip())*1000))
            item = self.table.item(i, 4)
            text = item.text().strip() if item else data['text'].strip()
            if text:
                srt_str_list.append(f'{len(srt_str_list)+1}\n{start_raw} --> {end_raw}\n{text}')

        try:
            Path(self.source_sub).write_text("\n\n".join(srt_str_list), encoding="utf-8")
        except Exception as e:
            logger.exception(f"Save error: {e}", exc_info=True)
        self._release_media()
        self.accept()
