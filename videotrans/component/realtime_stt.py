#!/usr/bin/env python3

import sys,json
import time
import threading
from pathlib import Path
import sherpa_onnx
import onnxruntime
import numpy as np
import wave

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout,QMessageBox, QHBoxLayout, QComboBox, QPushButton, QPlainTextEdit, QFileDialog,QLabel
from PySide6.QtCore import QThread, Signal,Qt,QUrl,QTimer
from PySide6.QtGui import QIcon, QCloseEvent,QDesktopServices

from videotrans.configure import config as cfg
from videotrans.util import tools
import sounddevice as sd


CTC_MODEL_FILE=f"{cfg.ROOT_DIR}/models/onnx/ctc.model.onnx"
PAR_ENCODER = f"{cfg.ROOT_DIR}/models/onnx/encoder.onnx"
PAR_DECODER = f"{cfg.ROOT_DIR}/models/onnx/decoder.onnx"
PAR_TOKENS = f"{cfg.ROOT_DIR}/models/onnx/tokens.txt"



class OnnxModel:
    def __init__(self):
        session_opts = onnxruntime.SessionOptions()
        session_opts.log_severity_level = 3  # error level
        self.sess = onnxruntime.InferenceSession(CTC_MODEL_FILE, session_opts)

        self._init_punct()
        self._init_tokens()

    def _init_punct(self):
        meta = self.sess.get_modelmeta().custom_metadata_map
        punct = meta["punctuations"].split("|")
        self.id2punct = punct
        self.punct2id = {p: i for i, p in enumerate(punct)}

        self.dot = self.punct2id["。"]
        self.comma = self.punct2id["，"]
        self.pause = self.punct2id["、"]
        self.quest = self.punct2id["？"]
        self.underscore = self.punct2id["_"]

    def _init_tokens(self):
        meta = self.sess.get_modelmeta().custom_metadata_map
        tokens = meta["tokens"].split("|")
        self.id2token = tokens
        self.token2id = {t: i for i, t in enumerate(tokens)}

        unk = meta["unk_symbol"]
        assert unk in self.token2id, unk

        self.unk_id = self.token2id[unk]

    def __call__(self, text: str) -> str:
        word_list = text.split()

        words = []
        for w in word_list:
            s = ""
            for c in w:
                if len(c.encode()) > 1:
                    if s == "":
                        s = c
                    elif len(s[-1].encode()) > 1:
                        s += c
                    else:
                        words.append(s)
                        s = c
                else:
                    if s == "":
                        s = c
                    elif len(s[-1].encode()) > 1:
                        words.append(s)
                        s = c
                    else:
                        s += c
            if s:
                words.append(s)


        ids = []
        for w in words:
            if len(w[0].encode()) > 1:
                # a Chinese phrase:
                for c in w:
                    ids.append(self.token2id.get(c, self.unk_id))
            else:
                ids.append(self.token2id.get(w, self.unk_id))


        segment_size = 30
        num_segments = (len(ids) + segment_size - 1) // segment_size

        punctuations = []

        max_len = 200

        last = -1
        for i in range(num_segments):
            this_start = i * segment_size
            this_end = min(this_start + segment_size, len(ids))
            if last != -1:
                this_start = last

            inputs = ids[this_start:this_end]

            out = self.sess.run(
                [
                    self.sess.get_outputs()[0].name,
                ],
                {
                    self.sess.get_inputs()[0]
                    .name: np.array(inputs, dtype=np.int32)
                    .reshape(1, -1),
                    self.sess.get_inputs()[1].name: np.array(
                        [len(inputs)], dtype=np.int32
                    ),
                },
            )[0]
            out = out[0]  # remove the batch dim
            out = out.argmax(axis=-1).tolist()

            dot_index = -1
            comma_index = -1

            for k in range(len(out) - 1, 1, -1):
                if out[k] in (self.dot, self.quest):
                    dot_index = k
                    break
                if comma_index == -1 and out[k] == self.comma:
                    comma_index = k
            if dot_index == -1 and len(inputs) >= max_len and comma_index != -1:
                dot_index = comma_index
                out[dot_index] = self.dot

            if dot_index == -1:
                if last == -1:
                    last = this_start

                if i == num_segments - 1:
                    dot_index = len(inputs) - 1
            else:
                last = this_start + dot_index + 1

            if dot_index != -1:
                punctuations += out[: dot_index + 1]



        ans = []

        for i, p in enumerate(punctuations):
            t = self.id2token[ids[i]]
            if ans and len(ans[-1][0].encode()) == 1 and len(t[0].encode()) == 1:
                ans.append(" ")
            ans.append(t)
            if p != self.underscore:
                ans.append(self.id2punct[p])

        return "".join(ans)


# Create recognizer
def create_recognizer():
    encoder = PAR_ENCODER
    decoder = PAR_DECODER
    tokens = PAR_TOKENS

    recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
        tokens=tokens,
        encoder=encoder,
        decoder=decoder,
        num_threads=2,
        sample_rate=16000,
        feature_dim=80,
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=2.4,
        rule2_min_trailing_silence=1.2,
        rule3_min_utterance_length=20,  # it essentially disables this rule
    )
    return recognizer

# Worker thread for transcription
class Worker(QThread):
    new_word = Signal(str)
    new_segment = Signal(str)
    ready = Signal()

    def __init__(self, device_idx, parent=None):
        super().__init__(parent)
        self.device_idx = device_idx
        self.running = False
        self.sample_rate = 48000
        self.samples_per_read = int(0.1 * self.sample_rate)

    def run(self):
        devices = sd.query_devices()
        if len(devices) == 0:
            return

        print(f'使用麦克风: {devices[self.device_idx]["name"]}')
        PUNCT_MODEL = OnnxModel()
        recognizer = create_recognizer()

        stream = recognizer.create_stream()

        mic_stream = sd.InputStream(
            device=self.device_idx,
            channels=1,
            dtype="float32",
            samplerate=self.sample_rate
        )
        mic_stream.start()
        wav_path=cfg.HOME_DIR+"/realtime_stt"
        Path(wav_path).mkdir(parents=True,exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H-%M-%S")
        txt_file = open(f"{wav_path}/{timestamp}.txt", 'a')
        wav_file = wave.open(f"{wav_path}/{timestamp}.wav", 'wb')
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # int16
        wav_file.setframerate(self.sample_rate)

        self.ready.emit()  # Emit ready signal after initialization

        self.running = True
        last_result = ""
        while self.running:
            samples, _ = mic_stream.read(self.samples_per_read)
            samples_int16 = (samples * 32767).astype(np.int16)
            wav_file.writeframes(samples_int16.tobytes())

            samples = samples.reshape(-1)
            stream.accept_waveform(self.sample_rate, samples)
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)

            is_endpoint = recognizer.is_endpoint(stream)
            result = recognizer.get_result(stream)

            if result != last_result:
                self.new_word.emit(result)
                last_result = result

            if is_endpoint:
                if result:
                    punctuated = PUNCT_MODEL(result)
                    txt_file.write(punctuated)
                    self.new_segment.emit(punctuated)
                recognizer.reset(stream)

        mic_stream.stop()
        wav_file.close()
        txt_file.close()

class CheckMics(QThread):
    devices = Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent)
    
    
    def run(self):
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]

        if not input_devices:
            self.devices.emit("No")
            return

        default_idx = sd.default.device[0]
        default_item = 0
        for i, d in enumerate(input_devices):            
            if d['index'] == default_idx:
                default_item = i

        self.devices.emit(json.dumps({"devices":input_devices,"default":default_item}))
        

# Main GUI window
class RealTimeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1000, 500)
        self.setWindowTitle(cfg.tr("Real-time speech-to-text") +" " + cfg.tr("Only supports Chinese and English language recognition"))
        self.setWindowIcon(QIcon(f"{cfg.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.layout = QVBoxLayout(self)

        # Microphone selection
       
        self.mic_layout = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.setMinimumWidth(250)
        
        self.checkbtn=QPushButton()
        self.checkbtn.setText(cfg.tr('Detection microphone'))
        self.checkbtn.clicked.connect(self.populate_mics)
        
        self.mic_layout.addWidget(self.combo)
        self.mic_layout.addWidget(self.checkbtn)

        self.start_button = QPushButton(cfg.tr("Initiating real-time transcription"))
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setMinimumHeight(30)
        self.start_button.setMinimumWidth(150)
        self.start_button.clicked.connect(self.toggle_transcription)
        self.mic_layout.addWidget(self.start_button)
        self.mic_layout.addStretch()
        self.layout.addLayout(self.mic_layout)

        # Real-time text
        self.realtime_text = QPlainTextEdit()
        self.realtime_text.setReadOnly(True)
        self.realtime_text.setStyleSheet("background: transparent; border: none;")
        self.realtime_text.setMaximumHeight(80)
        self.layout.addWidget(self.realtime_text)

        # Text edit for segments
        self.textedit = QPlainTextEdit()
        self.textedit.setReadOnly(True)
        self.textedit.setMinimumHeight(400)
        self.textedit.setStyleSheet("color:#ffffff")
        self.layout.addWidget(self.textedit)

        # Buttons layout
        self.button_layout = QHBoxLayout()
        self.export_button = QPushButton(cfg.tr("Export to TXT"))
        self.export_button.clicked.connect(self.export_txt)
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.setMinimumHeight(35)
        self.button_layout.addWidget(self.export_button)

        self.copy_button = QPushButton(cfg.tr("Copy"))
        self.copy_button.setMinimumHeight(35)
        self.copy_button.setCursor(Qt.PointingHandCursor)
        self.copy_button.clicked.connect(self.copy_textedit)
        self.button_layout.addWidget(self.copy_button)

        self.clear_button = QPushButton(cfg.tr("Clear"))
        self.clear_button.setMinimumHeight(35)
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_textedit)
        self.button_layout.addWidget(self.clear_button)

        self.layout.addLayout(self.button_layout)
        self.btn_opendir=QPushButton(f"{cfg.tr('Recording files are stored in')}: {cfg.HOME_DIR}/realtime_stt")
        self.btn_opendir.setStyleSheet("background-color:transparent;border:0;color:#ddd")
        self.btn_opendir.clicked.connect(self.open_dir)
        self.layout.addWidget(self.btn_opendir)

        self.worker = None
        self.transcribing = False
        
        QTimer.singleShot(300, self.populate_mics)
        

    def check_model_exist(self):
        if not Path(PAR_ENCODER).exists() or not Path(CTC_MODEL_FILE).exists() or not Path(PAR_DECODER).exists():
            tools.show_download_tips(self,cfg.tr('Real-time speech-to-text'))
            return False
        return True
        
        

    def open_dir(self):
        if not Path(f'{cfg.HOME_DIR}/realtime_stt').exists():
            Path(f'{cfg.HOME_DIR}/realtime_stt').mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(f'{cfg.HOME_DIR}/realtime_stt'))
        
        

    def populate_mics(self):
        def _get_dev(data):
            self.checkbtn.setDisabled(False)
            if data=='No':
                self.checkbtn.setText(cfg.tr('No valid microphone exists'))
                return
            data=json.loads(data)
            for i, d in enumerate(data['devices']):
                self.combo.addItem(d['name'], d['index'])
            self.combo.setCurrentIndex(data['default'])
        self.checkbtn.setDisabled(True)
        task=CheckMics(self)
        task.devices.connect(_get_dev)
        task.start()
    
        
        

    def toggle_transcription(self):
        if self.check_model_exist() is not True:
            return
        if not self.transcribing:
            self.realtime_text.setPlainText(cfg.tr("Please wait"))
            device_idx = self.combo.currentData()
            self.worker = Worker(device_idx)
            self.worker.new_word.connect(self.update_realtime)
            self.worker.new_segment.connect(self.append_segment)
            self.worker.ready.connect(self.update_realtime_ready)
            self.worker.start()
            self.start_button.setText(cfg.tr("Real-time transcription"))
            self.transcribing = True
        else:
            if self.worker:
                self.worker.running = False
                self.worker.wait()
                self.worker = None
            self.start_button.setText(cfg.tr("Initiating real-time transcription"))
            self.transcribing = False
            remaining_text = self.realtime_text.toPlainText().strip()
            if remaining_text:
                self.textedit.appendPlainText(remaining_text)
                scrollbar = self.textedit.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            self.realtime_text.clear()

    def update_realtime(self, text):
        self.realtime_text.setPlainText(text)
        scrollbar = self.realtime_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_realtime_ready(self):
        self.realtime_text.setPlainText(cfg.tr("Please speak"))

    def append_segment(self, text):
        self.textedit.appendPlainText(text)
        scrollbar = self.textedit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def export_txt(self):
        text=self.textedit.toPlainText().strip()
        if not text:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Save TXT", "", "Text files (*.txt)")
        if file_name:
            if not file_name.endswith(".txt"):
                file_name += ".txt"
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(text)

    def copy_textedit(self):
        text = self.textedit.toPlainText()
        QApplication.clipboard().setText(text)

    def clear_textedit(self):
        self.textedit.clear()

    def closeEvent(self, event: QCloseEvent):
        if self.transcribing:
            self.toggle_transcription()
        super().closeEvent(event)


