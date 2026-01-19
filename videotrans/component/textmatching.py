import shutil
import sys
import os
import difflib
import datetime
import traceback
import time
from pathlib import Path

import requests
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QTextEdit, QFileDialog,
                               QComboBox, QCheckBox, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSettings, QUrl
from huggingface_hub import snapshot_download

from videotrans.configure import config
from videotrans.util import tools

# ==========================================
# 1. 多语言配置区域
# ==========================================

# 可选: 'zh' (中文) | 'en' (English)
CURRENT_LANG = config.defaulelang

TEXT_DB = {
    # 窗口与标题
    "window_title": {"zh": "文稿匹配自动对齐", "en": "Force Alignment Text"},
    "language": {"zh": "发音语言", "en": "Spoken Language"},

    # 区域 1: 音频
    "group_audio": {"zh": "1. 选择音频文件", "en": "1. Select Audio File"},
    "no_audio_selected": {"zh": "未选择文件", "en": "No file selected"},
    "btn_browse": {"zh": "浏览...", "en": "Browse..."},
    "dialog_select_audio": {"zh": "选择音频", "en": "Select Audio"},

    # 区域 2: 文本
    "group_text": {"zh": "2. 输入文本内容 (文件或直接输入)", "en": "2. Input Text (File or Direct Input)"},
    "no_txt_selected": {"zh": "未选择TXT文件", "en": "No TXT file selected"},
    "btn_select_txt": {"zh": "选择TXT...", "en": "Select TXT..."},
    "dialog_select_txt": {"zh": "选择文本", "en": "Select Text File"},
    "label_paste_text": {"zh": "或者在下方粘贴文本 (优先使用输入框内容):", "en": "Or paste text below (Input box takes priority):"},
    "placeholder_text": {"zh": "在此处粘贴纯文本内容...如果不填则读取上方选择的文件", "en": "Paste plain text here... If empty, the file above will be used."},
    "btn_clear": {"zh": "清空内容", "en": "Clear Content"},  # 新增

    # 区域 3: 设置
    "group_settings": {"zh": "3. 模型设置", "en": "3. Model Settings"},
    "label_model": {"zh": "模型:", "en": "Model:"},
    "check_cuda": {"zh": "使用 CUDA 加速", "en": "Use CUDA Acceleration"},

    # 区域 4: 操作
    "btn_start": {"zh": "开始对齐生成 SRT", "en": "Start Alignment (Generate SRT)"},
    "btn_open_dir": {"zh": "打开输出目录", "en": "Open Output Dir"}, # 新增
    "btn_processing": {"zh": "处理中...", "en": "Processing..."},

    # 状态与日志
    "status_ready": {"zh": "准备就绪 (配置已加载)", "en": "Ready (Settings Loaded)"},
    "status_init": {"zh": "正在初始化...", "en": "Initializing..."},
    "status_loading_model": {"zh": "正在加载模型: {} (设备: {})...", "en": "Loading model: {} (Device: {})..."},
    "status_cuda_fail": {"zh": "CUDA加载失败，尝试使用CPU (int8)...", "en": "CUDA failed, fallback to CPU (int8)..."},
    "status_transcribing": {"zh": "正在识别音频 (Word Timestamps)...", "en": "Transcribing audio (Word Timestamps)..."},
    "status_processing_seg": {"zh": "已处理 {} 个片段...", "en": "Processed {} segments..."},
    "status_extracted": {"zh": "识别完成，共提取 {} 个字符时间点。", "en": "Transcription done. Extracted {} char timestamps."},
    "status_building_map": {"zh": "正在构建文本映射...", "en": "Building text mapping..."},
    "status_aligning": {"zh": "正在执行序列对齐算法...", "en": "Running sequence alignment..."},
    "status_aligned": {"zh": "对齐完成，匹配了 {} 个字符。正在插值补全...", "en": "Alignment done. Matched {} chars. Interpolating..."},
    "status_generating": {"zh": "正在生成 SRT 字幕...", "en": "Generating SRT subtitles..."},
    "status_saved": {"zh": "完成！已保存至: {}", "en": "Done! Saved to: {}"},
    "status_error": {"zh": "发生错误", "en": "Error Occurred"},

    # 弹窗提示
    "msg_warning": {"zh": "提示", "en": "Warning"},
    "msg_error": {"zh": "错误", "en": "Error"},
    "msg_success": {"zh": "成功", "en": "Success"},
    "msg_select_audio_first": {"zh": "请先选择有效的音频文件。", "en": "Please select a valid audio file first."},
    "msg_read_txt_fail": {"zh": "读取TXT文件失败: {}", "en": "Failed to read TXT file: {}"},
    "msg_provide_text": {"zh": "请提供文本内容（直接输入或选择文件）。", "en": "Please provide text content (Input or File)."},
    "msg_text_empty": {"zh": "文本内容不能为空。", "en": "Text content cannot be empty."},
    "msg_save_fail": {"zh": "保存文件失败: {}", "en": "Failed to save file: {}"},
    "msg_success_detail": {"zh": "SRT 字幕生成成功！\n文件已保存为:\n{}", "en": "SRT generated successfully!\nFile saved as:\n{}"}
}

_MODELS= {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "tiny": "Systran/faster-whisper-tiny",
    "base.en": "Systran/faster-whisper-base.en",
    "base": "Systran/faster-whisper-base",
    "small.en": "Systran/faster-whisper-small.en",
    "small": "Systran/faster-whisper-small",
    "medium.en": "Systran/faster-whisper-medium.en",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}

def tr(key, *args):
    """翻译辅助函数"""
    lang_dict = TEXT_DB.get(key, {})
    text = lang_dict.get(CURRENT_LANG, key) # 默认回退到key本身
    if args:
        return text.format(*args)
    return text

# ==========================================
# 2. 核心逻辑线程
# ==========================================

class AlignmentWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, audio_path, text_content, model_name, device, compute_type,language=None):
        super().__init__()
        self.audio_path = audio_path
        self.text_content = text_content
        self.device = device
        self.model_name=model_name
        self.compute_type = compute_type
        self.language =None if language=='auto' else  language
        self.local_dir = f'{config.ROOT_DIR}/models/models--' + _MODELS[model_name].replace('/', '--')

    def ms_to_srt_time(self, seconds):
        if seconds is None:
            return "00:00:00,000"
        td = datetime.timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        millis = int(td.microseconds / 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    def run(self):
        try:
            self.log_signal.emit(tr("status_loading_model", self.model_name, self.device))
            tools.check_and_down_hf(self.model_name,_MODELS[self.model_name],self.local_dir,callback=self._progress_callback)
            from faster_whisper import WhisperModel

            try:
                model = WhisperModel(self.local_dir, device=self.device, compute_type=self.compute_type)
            except Exception as e:
                if self.device == "cuda":
                    self.log_signal.emit(tr("status_cuda_fail"))
                    model = WhisperModel(self.local_dir, device="cpu", compute_type="float32")
                else:
                    raise e

            self.log_signal.emit(tr("status_transcribing"))
            tempfile=f'{config.TEMP_DIR}/textmatching-{time.time()}.wav'
            tools.conver_to_16k(self.audio_path,tempfile)
            segments, info = model.transcribe(
                  tempfile,
                  vad_filter=True,
                  condition_on_previous_text=False,
                  word_timestamps=True,
                  language=self.language,
                  temperature=0.0,
                  initial_prompt=config.settings.get(f'initial_prompt_{self.language}') if self.language != 'auto' else None,
                beam_size=int(config.settings.get('beam_size', 5)),
                best_of=int(config.settings.get('best_of', 5)),
                repetition_penalty=float(config.settings.get('repetition_penalty', 1.0)),
                compression_ratio_threshold=float(config.settings.get('compression_ratio_threshold', 2.2)),
                )

            whisper_chars = []
            seg_count = 0
            text_list=[]
            for segment in segments:
                text_list.append(segment.text)
                seg_count += 1
                if seg_count % 5 == 0:
                    self.log_signal.emit(tr("status_processing_seg", seg_count))

                self.log_signal.emit(segment.text)
                for word in segment.words:
                    w_text = word.word.strip()
                    if not w_text: continue
                    duration = word.end - word.start
                    char_duration = duration / len(w_text)
                    for i, char in enumerate(w_text):
                        whisper_chars.append({
                            'char': char,
                            'start': word.start + (i * char_duration),
                            'end': word.start + ((i + 1) * char_duration)
                        })

            self.log_signal.emit(tr("status_extracted", len(whisper_chars)))

            target_chars_map = []
            punctuations = set(['，', '。', '？', '！', '；', '：', ',', '.', '?', '!', ';', ':'])
            comparison_target = []

            for i, char in enumerate(self.text_content):
                is_punc = char in punctuations or char.strip() == ""
                target_chars_map.append({
                    'original_char': char,
                    'is_punc': is_punc,
                    'start': None,
                    'end': None,
                })
                if not is_punc:
                    comparison_target.append(char)

            self.log_signal.emit(tr("status_aligning"))
            comparison_whisper = [x['char'] for x in whisper_chars]
            matcher = difflib.SequenceMatcher(None, comparison_target, comparison_whisper)

            comp_to_orig_map = []
            for idx, item in enumerate(target_chars_map):
                if not item['is_punc']:
                    comp_to_orig_map.append(idx)

            match_count = 0
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    count = i2 - i1
                    for k in range(count):
                        orig_idx = comp_to_orig_map[i1 + k]
                        whisper_idx = j1 + k
                        target_chars_map[orig_idx]['start'] = whisper_chars[whisper_idx]['start']
                        target_chars_map[orig_idx]['end'] = whisper_chars[whisper_idx]['end']
                        match_count += 1

            self.log_signal.emit(tr("status_aligned", match_count))

            # 插值逻辑
            non_punc_indices = [i for i, x in enumerate(target_chars_map) if not x['is_punc']]
            for i in range(len(non_punc_indices)):
                curr_real_idx = non_punc_indices[i]
                curr_item = target_chars_map[curr_real_idx]

                if curr_item['start'] is None:
                    prev_time = 0.0
                    if i > 0:
                        prev_item = target_chars_map[non_punc_indices[i-1]]
                        if prev_item['end'] is not None:
                            prev_time = prev_item['end']

                    next_time = None
                    dist = 0
                    for j in range(i + 1, len(non_punc_indices)):
                        next_real_idx = non_punc_indices[j]
                        if target_chars_map[next_real_idx]['start'] is not None:
                            next_time = target_chars_map[next_real_idx]['start']
                            dist = j - i
                            break

                    if next_time is not None:
                        duration_per_char = (next_time - prev_time) / (dist + 1)
                        curr_item['start'] = prev_time
                        curr_item['end'] = prev_time + duration_per_char
                    else:
                        curr_item['start'] = prev_time
                        curr_item['end'] = prev_time + 0.2

            self.log_signal.emit(tr("status_generating"))
            srt_parts = []
            srt_index = 1
            sentence_buffer = []
            line_start_time = None
            line_end_time = 0.0
            MAX_CHARS = 30

            for idx, item in enumerate(target_chars_map):
                char = item['original_char']
                is_punc = item['is_punc']
                start = item['start']
                end = item['end']

                if char.strip() == "" and not is_punc:
                    continue

                if not is_punc and start is not None:
                    if len(sentence_buffer) == 0:
                        line_start_time = start
                    line_end_time = end

                sentence_buffer.append(char)

                should_break = False
                if is_punc: should_break = True
                elif len(sentence_buffer) >= MAX_CHARS: should_break = True
                elif idx == len(target_chars_map) - 1: should_break = True

                if should_break and sentence_buffer:
                    text_line = "".join(sentence_buffer).strip()
                    if text_line and line_start_time is not None:
                        self.log_signal.emit(text_line)
                        srt_parts.append(f"{srt_index}\n{self.ms_to_srt_time(line_start_time)} --> {self.ms_to_srt_time(line_end_time)}\n{text_line}\n")
                        srt_index += 1

                    sentence_buffer = []
                    line_start_time = None

            final_srt = "\n".join(srt_parts)
            self.finished_signal.emit(final_srt)
        except Exception as e:
            err_msg = traceback.format_exc()
            self.error_signal.emit(str(e) + "\n\n" + err_msg)



    def _progress_callback(self, data):
        msg_type = data.get("type")
        percent = data.get("percent")
        filename = data.get("filename")
        print(f'{data=}')

        if msg_type == "file":
            self.log_signal.emit(f"Downloading {filename} {percent:.2f}%")
        else:
            current_file_idx = data.get("current")
            total_files = data.get("total")
            self.log_signal.emit(f"Downloading {current_file_idx}/{total_files} files")



# ==========================================
# 3. 界面主类
# ==========================================

class TextmatchingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MyTools", "WhisperForceAlign")
        self.setWindowTitle(tr("window_title"))
        self.resize(800, 700)
        self.worker = None

        # 记录上一次成功的输出目录
        self.last_output_dir = None

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        # 1. 音频选择

        audio_layout = QHBoxLayout()
        btn_audio = QPushButton(tr("btn_browse"))
        btn_audio.clicked.connect(self.select_audio)
        btn_audio.setCursor(Qt.PointingHandCursor)
        btn_audio.setMinimumHeight(30)
        audio_layout.addWidget(QLabel(tr("group_audio")))
        audio_layout.addWidget(btn_audio)
        main_layout.addLayout(audio_layout)
        self.audio_label = QLabel(tr("no_audio_selected"))
        self.audio_label.setStyleSheet("""color:#aaa;margin-left:10px""")
        main_layout.addWidget(self.audio_label)

        # 2.1 文件选择行
        file_layout = QHBoxLayout()
        self.txt_file_label = QLabel(tr("no_txt_selected"))
        self.txt_file_label.setStyleSheet("color: #aaa;margin-left:10px")
        btn_txt = QPushButton(tr("btn_select_txt"))
        btn_txt.clicked.connect(self.select_txt)
        btn_txt.setCursor(Qt.PointingHandCursor)
        btn_txt.setMinimumHeight(30)
        file_layout.addWidget(QLabel(tr("group_text")))
        file_layout.addWidget(btn_txt)
        main_layout.addLayout(file_layout)
        main_layout.addWidget(self.txt_file_label)


        # 2.2 标签 + 清空按钮行
        label_btn_layout = QHBoxLayout()
        label_btn_layout.addWidget(QLabel(tr("label_paste_text")))
        label_btn_layout.addStretch() # 弹簧，把清空按钮顶到右边

        btn_clear = QPushButton(tr("btn_clear"))
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setToolTip("Clear text")
        # 直接连接 clear 槽函数
        btn_clear.clicked.connect(self.clear_text_edit)
        btn_clear.setCursor(Qt.PointingHandCursor)

        label_btn_layout.addWidget(btn_clear)
        main_layout.addLayout(label_btn_layout)

        # 2.3 文本框
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(tr("placeholder_text"))
        main_layout.addWidget(self.text_edit)

        # 3. 设置

        settings_layout = QHBoxLayout()

        settings_layout.addWidget(QLabel(tr("label_model")))
        self.combo_model = QComboBox()
        self.combo_model.setMinimumWidth(150)
        self.combo_model.addItems([ "large-v2", "large-v3","large-v3-turbo", "medium"])
        settings_layout.addWidget(self.combo_model)
        settings_layout.addWidget(QLabel(tr("language")))
        self.language = QComboBox()
        self.language.setMinimumWidth(100)
        self.language.addItems(["auto", "zh", "en", "ja", "ko","ru","es","de","fr","it","pt","vi","th","ms","ar","kk","hi","hu","id","tr","nl","he","bn","ur","uk","nl","sw","yue"])
        settings_layout.addWidget(self.language)

        settings_layout.addStretch()

        self.check_cuda = QCheckBox(tr("check_cuda"))
        self.check_cuda.setChecked(True)
        settings_layout.addWidget(self.check_cuda)
        main_layout.addLayout(settings_layout)

        # 4. 操作区 (开始按钮 + 打开文件夹按钮)
        operation_layout = QHBoxLayout()

        self.btn_start = QPushButton(tr("btn_start"))
        self.btn_start.setFixedHeight(40)
        self.btn_start.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_process)
        operation_layout.addWidget(self.btn_start)

        # 新增：打开输出目录按钮
        self.btn_open_dir = QPushButton(tr("btn_open_dir"))
        self.btn_open_dir.setFixedHeight(40)
        self.btn_open_dir.setCursor(Qt.PointingHandCursor)
        # 略微改一下样式，使其与开始按钮区分
        self.btn_open_dir.setStyleSheet("font-size: 12px;")
        self.btn_open_dir.hide() # 初始隐藏
        self.btn_open_dir.clicked.connect(self.open_output_dir)
        operation_layout.addWidget(self.btn_open_dir)

        # 调整比例，让开始按钮占主要部分 (例如 3:1)
        operation_layout.setStretch(0, 3)
        operation_layout.setStretch(1, 1)

        main_layout.addLayout(operation_layout)

        # 5. 日志区
        self.log_label = QLabel(tr("status_ready"))
        self.log_label.setAlignment(Qt.AlignCenter)
        self.log_label.setStyleSheet("padding: 10px; color: #aaa;")
        self.log_label.setWordWrap(True)
        main_layout.addWidget(self.log_label)

    # 辅助槽函数：清空文本框
    def clear_text_edit(self):
        self.text_edit.clear()

    # 辅助槽函数：打开输出目录
    def open_output_dir(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output_dir))
        else:
            QMessageBox.warning(self, tr("msg_warning"), "Directory does not exist.")

    # ==========================
    # 配置保存与读取逻辑
    # ==========================
    def load_settings(self):
        """启动时加载配置"""
        saved_model = self.settings.value("model_size", "large-v3-turbo")
        index = self.combo_model.findText(saved_model)
        if index != -1:
            self.combo_model.setCurrentIndex(index)
        language = self.settings.value("language", "auto")
        self.language.setCurrentText(language)

        use_cuda = self.settings.value("use_cuda", True, type=bool)
        self.check_cuda.setChecked(use_cuda)

        self.last_audio_dir = self.settings.value("last_audio_dir", "")
        self.last_txt_dir = self.settings.value("last_txt_dir", "")

    def save_current_settings(self):
        """保存当前面板上的设置"""
        self.settings.setValue("model_size", self.combo_model.currentText())
        self.settings.setValue("language", self.language.currentText())
        self.settings.setValue("use_cuda", self.check_cuda.isChecked())

    # ==========================
    # 业务逻辑
    # ==========================
    def select_audio(self):
        start_dir = self.last_audio_dir if self.last_audio_dir else ""
        path, _ = QFileDialog.getOpenFileName(self, tr("dialog_select_audio"), start_dir, "Audio Video Files (*.wav *.mp3 *.m4a *.flac *.aac *.mp4 *.mkv *.mov *.mpeg *.flv *.avi *.mpeg *.wmv *.wma *.ogg *.webm)")

        if path:
            self.audio_label.setText(path)
            self.audio_label.setStyleSheet("color: #ff0;")
            new_dir = os.path.dirname(path)
            self.last_audio_dir = new_dir
            self.settings.setValue("last_audio_dir", new_dir)

    def select_txt(self):
        start_dir = self.last_txt_dir if self.last_txt_dir else ""
        path, _ = QFileDialog.getOpenFileName(self, tr("dialog_select_txt"), start_dir, "Text Files (*.txt)")

        if path:
            self.txt_file_label.setText(path)
            self.txt_file_label.setStyleSheet("color: #ff0;")
            new_dir = os.path.dirname(path)
            self.last_txt_dir = new_dir
            self.settings.setValue("last_txt_dir", new_dir)

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.text_edit.clear()
                    self.text_edit.setText(content)
            except Exception as e:
                QMessageBox.warning(self, tr("msg_warning"), tr("msg_read_txt_fail", str(e)))

    def start_process(self):
        self.save_current_settings()

        # 重新开始时隐藏打开目录按钮
        self.btn_open_dir.hide()

        audio_path = self.audio_label.text()
        if audio_path == tr("no_audio_selected") or not os.path.exists(audio_path):
            QMessageBox.warning(self, tr("msg_warning"), tr("msg_select_audio_first"))
            return

        text_content = self.text_edit.toPlainText().strip()
        if not text_content:
            txt_path = self.txt_file_label.text()
            if txt_path != tr("no_txt_selected") and os.path.exists(txt_path):
                try:
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                except Exception as e:
                    QMessageBox.critical(self, tr("msg_error"), tr("msg_read_txt_fail", str(e)))
                    return
            else:
                QMessageBox.warning(self, tr("msg_warning"), tr("msg_provide_text"))
                return

        if not text_content:
             QMessageBox.warning(self, tr("msg_warning"), tr("msg_text_empty"))
             return

        self.btn_start.setEnabled(False)
        self.btn_start.setText(tr("btn_processing"))
        self.log_label.setText(tr("status_init"))
        self.log_label.setStyleSheet("padding: 10px; border-radius: 5px; color: #148CD2;")

        model_size = self.combo_model.currentText()
        language = self.language.currentText()
        device = "cuda" if self.check_cuda.isChecked() else "cpu"
        compute_type = "float16" if device == "cuda" else "float32"

        self.worker = AlignmentWorker(audio_path, text_content, model_size, device, compute_type,language)
        self.worker.log_signal.connect(self.update_log)
        self.worker.finished_signal.connect(self.process_finished)
        self.worker.error_signal.connect(self.process_error)
        self.worker.start()

    @Slot(str)
    def update_log(self, message):
        self.log_label.setText(message)

    @Slot(str)
    def process_finished(self, srt_content):
        audio_path = self.audio_label.text()
        base_name = os.path.splitext(audio_path)[0]
        srt_path = f"{base_name}.srt"
        print(f'{audio_path=},{base_name=},{srt_path=}')

        try:
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)

            self.log_label.setText(tr("status_saved", srt_path))
            self.log_label.setStyleSheet("padding: 10px; border-radius: 5px; color: #ff0;")

            # 记录目录并显示打开按钮
            self.last_output_dir = os.path.dirname(srt_path)
            self.btn_open_dir.show()

        except Exception as e:
            self.process_error(tr("msg_save_fail", str(e)))

        self.reset_ui_state()

    @Slot(str)
    def process_error(self, error_msg):
        self.log_label.setText(tr("status_error"))
        self.log_label.setStyleSheet("background-color: #fff1f0; padding: 10px; border-radius: 5px; color: #cf1322;")
        self.reset_ui_state()
        QMessageBox.critical(self, tr("msg_error"), error_msg)

    def reset_ui_state(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText(tr("btn_start"))

if __name__ == "__main__":
    app = QApplication(sys.argv)

    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    window = TextmatchingWindow()
    window.show()
    sys.exit(app.exec())