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
        """Return the list of language codes available for Google Cloud TTS."""
        # Keep this list in sync with videotrans/ui/googlecloud.py
        return [
            "pt-BR", "en-US", "en-GB", "es-ES", "fr-FR", "de-DE",
            "it-IT", "ja-JP", "ko-KR", "zh-CN", "ru-RU", "hi-IN",
            "ar-XA", "tr-TR", "th-TH", "vi-VN", "id-ID",
        ]

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
        voice_names_to_display = []
        
        # lang_code here is the one from the language dropdown in the settings form, e.g. "en-US"
        # It should be already correctly formatted for Google Cloud.

        if use_local_cache:
            try:
                # Only read from local cache
                voice_data_list = GoogleCloudTTS.get_local_voices(language_code=lang_code)
                voice_names_to_display = sorted([v_data.get("name") for v_data in voice_data_list if v_data.get("name")])
                if not voice_names_to_display:
                    # Add a message to indicate cache for this language is empty or language not found in cache
                     self.voice_cb.addItem(config.box_lang.get("local_cache_empty_for_lang", "Local cache empty for this language"))

            except Exception as e:
                QMessageBox.critical(self, "Erro ao Listar Vozes Locais", f"Falha ao buscar vozes do arquivo local:\n{str(e)}")
                # self.voice_cb.addItem("Error loading local voices") # Already handled by adding to voice_names_to_display
        else: # use_local_cache is False, so try to fetch from API and update cache
            cred = self.cred_le.text().strip()
            if not cred:
                QMessageBox.warning(self, "Credenciais Ausentes", 
                                    "Caminho para JSON de credenciais não configurado. Não é possível atualizar do API.")
                # Optionally, load from local cache as a fallback even if use_local_cache is False
                # voice_data_list = GoogleCloudTTS.get_local_voices(language_code=lang_code)
                # voice_names_to_display = sorted([v_data.get("name") for v_data in voice_data_list if v_data.get("name")])
                # if not voice_names_to_display:
                #    self.voice_cb.addItem(config.box_lang.get("local_cache_empty_for_lang_cred_missing", "Cache empty, creds missing for API"))

                # For now, let's stick to just warning and showing an empty list if API call isn't attempted.
                # Or, more consistently, let get_and_cache_voices handle it.
                # If cred is empty, get_and_cache_voices will try to use existing cache.
                pass # Let get_and_cache_voices handle this. It won't fetch API without creds.

            # Check google-cloud-texttospeech package installation
            if not self._check_tts_client(): # self._check_tts_client shows its own QMessageBox
                # If client is not available, we can't fetch from API.
                # We might still want to show what's in the cache.
                # voice_data_list = GoogleCloudTTS.get_local_voices(language_code=lang_code) # Fallback to local
                # voice_names_to_display = sorted([v_data.get("name") for v_data in voice_data_list if v_data.get("name")])
                # if not voice_names_to_display:
                #    self.voice_cb.addItem(config.box_lang.get("local_cache_empty_g_client_missing", "Cache empty, G-Client missing"))
                # For now, if client check fails, do nothing further here.
                # Let get_and_cache_voices attempt and log.
                 pass


            try:
                # Attempt to fetch from API (and update cache), then filter.
                # force_api_fetch=True ensures it tries API if creds are valid.
                # If creds are invalid/missing, it will use existing cache.
                voice_data_list = GoogleCloudTTS.get_and_cache_voices(
                    credential_path=cred,
                    language_code_filter=lang_code,
                    force_api_fetch=True 
                )
                voice_names_to_display = sorted([v_data.get("name") for v_data in voice_data_list if v_data.get("name")])
                if not voice_names_to_display:
                    # This message appears if API fetch failed AND cache was empty for this language.
                    self.voice_cb.addItem(config.box_lang.get("no_voices_api_or_cache", "No voices found (API/Cache)"))

            except Exception as e:
                QMessageBox.critical(self, "Erro ao Listar Vozes (API/Cache)", f"Falha ao buscar vozes (API/Cache):\n{str(e)}")
                # self.voice_cb.addItem("Error loading voices (API/Cache)")

        # Common logic to populate combobox
        if voice_names_to_display:
            self.voice_cb.addItems(voice_names_to_display)
            saved_voice = config.params.get("gcloud_voice_name", "")
            if saved_voice in voice_names_to_display:
                self.voice_cb.setCurrentText(saved_voice)
            # else: # Avoid selecting the first item by default if saved_voice is not found
            #    self.voice_cb.setCurrentText(voice_names_to_display[0]) 
        elif not self.voice_cb.count(): # If after all attempts, combobox is still empty
            self.voice_cb.addItem(config.box_lang.get("no_voices_available_generic", "No voices available"))

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