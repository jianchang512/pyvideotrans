from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QPushButton,
    QFileDialog, QMessageBox, QHBoxLayout, QCheckBox
)
from videotrans.configure import config
from videotrans.tts._googlecloud import GoogleCloudTTS

# Import lazy do TextToSpeechClient
TextToSpeechClient = None
try:
    from google.cloud.texttospeech import TextToSpeechClient
except ImportError:
    # Caso falhe, tentamos o import legacy
    try:
        from google.cloud import texttospeech
        TextToSpeechClient = texttospeech.TextToSpeechClient
    except ImportError:
        pass  # Deixamos None para tratar depois


class GoogleCloudSettingsForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Google Cloud TTS Settings")

        # --- Layout principal
        layout = QFormLayout(self)

        # 1) Credential JSON + botão Browse
        self.cred_le = QLineEdit()
        self.cred_le.setText(config.params.get("gcloud_credential_json", ""))
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.on_browse)

        # para não sobrescrever a mesma célula, colocamos num HBox
        hbox = QHBoxLayout()
        hbox.addWidget(self.cred_le)
        hbox.addWidget(browse_btn)
        layout.addRow("Credential JSON:", hbox)

        # 2) Language ComboBox
        self.lang_cb = QComboBox()
        self.lang_cb.addItems(self._available_languages())
        self.lang_cb.setCurrentText(config.params.get("gcloud_language_code", "en-US"))
        layout.addRow("Language:", self.lang_cb)

        # 3) Voice ComboBox (vazio por enquanto)
        self.voice_cb = QComboBox()
        layout.addRow("Voice:", self.voice_cb)

        # 4) Audio Encoding ComboBox
        self.enc_cb = QComboBox()
        self.enc_cb.addItems(["MP3", "LINEAR16", "OGG_OPUS"])
        self.enc_cb.setCurrentText(config.params.get("gcloud_audio_encoding", "MP3"))
        layout.addRow("Audio Encoding:", self.enc_cb)

        # Checkbox for local cache
        self.local_cache_checkbox = QCheckBox("Load voices from local cache")
        initial_cache_pref = config.params.get("gcloud_use_local_cache", False)
        self.local_cache_checkbox.setChecked(bool(initial_cache_pref))
        layout.addRow(self.local_cache_checkbox)

        # 5) Buttons Save / Test
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save)
        btn_test = QPushButton("Test")
        btn_test.clicked.connect(self.test)
        btn_box = QHBoxLayout()
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_test)
        layout.addRow(btn_box)

        # --- Signals
        self.local_cache_checkbox.stateChanged.connect(self.on_local_cache_toggle)
        self.lang_cb.currentTextChanged.connect(
            lambda lang_code_text: self.populate_voices(lang_code_text, use_local_cache=self.local_cache_checkbox.isChecked())
        )
        # popula voices logo na abertura, respecting checkbox state
        self.populate_voices(self.lang_cb.currentText(), use_local_cache=self.local_cache_checkbox.isChecked())

    def on_local_cache_toggle(self):
        use_local = self.local_cache_checkbox.isChecked()
        current_lang = self.lang_cb.currentText()
        self.populate_voices(current_lang, use_local_cache=use_local)

    def _available_languages(self):
        # use a mesma lista de idiomas que o dropdown principal
        # ou extraia de config.params / hardcode: ["en-US","pt-BR",...]
        return ["en-US", "pt-BR", "es-ES", "fr-FR", "..."]

    def on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Credential JSON", "", "JSON Files (*.json)"
        )
        if path:
            self.cred_le.setText(path)

    def _check_tts_client(self):
        """Verifica se o cliente TTS está disponível e instala se necessário."""
        global TextToSpeechClient
        if TextToSpeechClient is None:
            try:
                from google.cloud.texttospeech import TextToSpeechClient
            except ImportError:
                try:
                    from google.cloud import texttospeech
                    TextToSpeechClient = texttospeech.TextToSpeechClient
                except ImportError:
                    QMessageBox.critical(
                        self,
                        "Erro de Dependência",
                        "O pacote google-cloud-texttospeech não está instalado.\n\n"
                        "Por favor, instale-o com:\n"
                        "pip install google-cloud-texttospeech"
                    )
                    return False
        return True

    def populate_voices(self, lang_code, use_local_cache=False):
        self.voice_cb.clear()
        voices_to_display = []

        if use_local_cache:
            try:
                # Call as a static method
                local_voice_data = GoogleCloudTTS.get_local_voices(language_code=lang_code)
                voices_to_display = sorted([v_data.get("name") for v_data in local_voice_data if v_data.get("name")])
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erro ao Listar Vozes Locais",
                    f"Falha ao buscar vozes do arquivo local:\n{str(e)}"
                )
        else: # API logic
            if not self.cred_le.text().strip():
                QMessageBox.warning(self, "Credenciais Ausentes", "O caminho para o arquivo JSON de credenciais do Google Cloud não foi configurado.")
                # Do not attempt API call if creds are missing
            elif not self._check_tts_client(): # Checks if google-cloud-texttospeech is installed
                pass # _check_tts_client already shows a message
            else:
                try:
                    client = TextToSpeechClient.from_service_account_file(
                        self.cred_le.text().strip()
                    )
                    all_voices_api = client.list_voices().voices # Get all voices
                    filtered_api_voices = [
                        v.name for v in all_voices_api
                        if any(lang_code.lower() in lc.lower() for lc in v.language_codes)
                    ]
                    voices_to_display = sorted(filtered_api_voices)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Erro ao Listar Vozes (API)",
                        f"Falha ao buscar vozes do Google Cloud TTS (API):\n{str(e)}"
                    )
        
        self.voice_cb.addItems(voices_to_display)
        if voices_to_display:
            saved_voice = config.params.get("gcloud_voice_name", "")
            if saved_voice in voices_to_display:
                self.voice_cb.setCurrentText(saved_voice)
            # else: # Removed to avoid selecting the first if saved_voice is not found
            #    self.voice_cb.setCurrentText(voices_to_display[0])
            # Keep current selection or previously saved if valid, otherwise it will be blank or first by default.

    def save(self):
        if not self._check_tts_client():
            return

        # Atualiza apenas as configurações do Google Cloud TTS
        config.params.update({
            "gcloud_credential_json": self.cred_le.text().strip(),
            "gcloud_language_code":   self.lang_cb.currentText(),
            "gcloud_voice_name":      self.voice_cb.currentText(),
            "gcloud_audio_encoding":  self.enc_cb.currentText(),
            "gcloud_use_local_cache": self.local_cache_checkbox.isChecked()
        })
        # Salva todas as configurações
        config.getset_params(config.params)
        QMessageBox.information(self, "Salvo", "Configurações do Google Cloud TTS salvas.")
        self.close()

    def test(self):
        if not self._check_tts_client():
            return

        try:
            tts = GoogleCloudTTS()
            # cria um arquivo temporário simples
            tmp = "test_gcloud.mp3"
            tts._item_task({"filename": tmp, "text": "This is a test."})
            QMessageBox.information(self, "Teste OK", f"Áudio gerado com sucesso: {tmp}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro no Teste",
                f"Falha ao testar síntese de voz:\n{str(e)}"
            )


def openwin():
    """Função de entrada para abrir o formulário de configurações do Google Cloud TTS."""
    winobj = config.child_forms.get('googlecloudw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return

    winobj = GoogleCloudSettingsForm()
    config.child_forms['googlecloudw'] = winobj
    winobj.show() 