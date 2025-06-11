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

        # 3) Voice ComboBox and Refresh Button
        voice_hbox = QHBoxLayout()
        self.voice_cb = QComboBox()
        voice_hbox.addWidget(self.voice_cb)

        self.refresh_voices_btn = QPushButton("Refresh Voices")
        self.refresh_voices_btn.setMinimumSize(self.cred_le.minimumSizeHint().width() // 4, self.cred_le.minimumSizeHint().height()) # Adjust size as needed
        voice_hbox.addWidget(self.refresh_voices_btn)
        layout.addRow("Voice:", voice_hbox)

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
        btn_test.clicked.connect(self.test) # Connects to the updated test method
        btn_box = QHBoxLayout()
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_test)
        layout.addRow(btn_box)

        # --- Signals
        self.local_cache_checkbox.stateChanged.connect(self.on_local_cache_toggle)
        self.lang_cb.currentTextChanged.connect(
            lambda lang_code_text: self.populate_voices(lang_code_text, use_local_cache=self.local_cache_checkbox.isChecked())
        )
        self.refresh_voices_btn.clicked.connect(self.handle_refresh_voices) # Connect new button

        # popula voices logo na abertura, respecting checkbox state
        self.populate_voices(self.lang_cb.currentText(), use_local_cache=self.local_cache_checkbox.isChecked())

    def handle_refresh_voices(self):
        """Handles the click of the 'Refresh Voices' button."""
        current_lang_code = self.lang_cb.currentText()
        use_cache = self.local_cache_checkbox.isChecked()
        # Add some user feedback that refresh is happening, e.g., disable button
        self.refresh_voices_btn.setEnabled(False)
        self.refresh_voices_btn.setText("Refreshing...")
        try:
            self.populate_voices(lang_code=current_lang_code, use_local_cache=use_cache)
        finally:
            # Re-enable button and restore text even if populate_voices fails
            self.refresh_voices_btn.setEnabled(True)
            self.refresh_voices_btn.setText("Refresh Voices")

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
        voice_names_to_display = []
        # Get current credential path from UI for potential API calls
        current_ui_cred_path = self.cred_le.text().strip()
        
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
            # Use current_ui_cred_path from UI for API calls
            if not current_ui_cred_path:
                QMessageBox.warning(self, "Credenciais Ausentes", 
                                    "Caminho para JSON de credenciais não configurado. Não é possível atualizar da API.")
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
                    credential_path=current_ui_cred_path, # Pass credential path from UI
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

        # Store the globally saved/previously selected voice name
        previously_selected_voice = config.params.get("gcloud_voice_name", "")

        if voice_names_to_display:
            self.voice_cb.addItems(voice_names_to_display)

            if previously_selected_voice and previously_selected_voice in voice_names_to_display:
                self.voice_cb.setCurrentText(previously_selected_voice)
            elif voice_names_to_display: # If previous not found, but list is not empty, select first
                self.voice_cb.setCurrentIndex(0)
            # If voice_names_to_display is empty, and previously_selected_voice was not in it (e.g. list is empty)
            # then the combobox will be empty, and we add a placeholder below.

        if not self.voice_cb.count(): # If after all attempts, combobox is still empty (no items added)
            self.voice_cb.addItem(config.box_lang.get("no_voices_available_for_lang", "No voices for this language"))
            # Clear gcloud_voice_name in config if no voices are available for the selected language?
            # This could be aggressive. For now, just UI update.
            # If config.params['gcloud_language_code'] == lang_code: # only clear if it's for the current language
            #    config.params['gcloud_voice_name'] = ""


    def save(self):
        if not self._check_tts_client():
            return

        current_lang_code = self.lang_cb.currentText()
        current_voice_name = self.voice_cb.currentText()
        placeholder_text_for_empty_voices = config.box_lang.get("no_voices_available_for_lang", "No voices for this language")

        # Validation for save: only if a voice is selected, ensure it's valid for the language.
        # Saving with no voice selected (i.e., current_voice_name is the placeholder or empty) is allowed,
        # which will effectively clear/empty gcloud_voice_name.
        if current_voice_name and current_voice_name != placeholder_text_for_empty_voices:
            # A voice is selected, so validate it against the current language
            available_voices_for_lang = GoogleCloudTTS.get_local_voices(language_code=current_lang_code)
            available_voice_names = [v['name'] for v in available_voices_for_lang]
            if current_voice_name not in available_voice_names:
                QMessageBox.warning(self, "Erro de Validação",
                                    f"A voz selecionada '{current_voice_name}' não é válida para o idioma '{current_lang_code}'.\n"
                                    "Por favor, atualize a lista de vozes ou selecione uma voz/idioma diferente antes de salvar.")
                return

        # If validation passes or no voice is selected (placeholder is showing), proceed to save.
        # If placeholder is showing, current_voice_name will be that placeholder string.
        # We should save an empty string if that's the case, or if voice_cb is genuinely empty.
        voice_to_save = current_voice_name
        if current_voice_name == placeholder_text_for_empty_voices or self.voice_cb.count() == 0:
            voice_to_save = ""


        # Atualiza apenas as configurações do Google Cloud TTS
        config.params.update({
            "gcloud_credential_json": self.cred_le.text().strip(),
            "gcloud_language_code":   current_lang_code, # Use variable already fetched
            "gcloud_voice_name":      voice_to_save,
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

        # Read current values from UI for testing
        current_cred_path = self.cred_le.text().strip()
        current_lang_code = self.lang_cb.currentText()
        current_voice_name = self.voice_cb.currentText()
        current_audio_encoding = self.enc_cb.currentText()

        placeholder_text_for_empty_voices = config.box_lang.get("no_voices_available_for_lang", "No voices for this language")

        # Validation for test: A valid voice must be selected.
        if not current_voice_name or current_voice_name == placeholder_text_for_empty_voices or self.voice_cb.count() == 0:
            QMessageBox.warning(self, "Erro de Validação",
                                "Por favor, selecione uma voz válida antes de testar.")
            return

        if not current_cred_path:
             QMessageBox.warning(self, "Credenciais Ausentes",
                                    "Por favor, forneça o caminho para o arquivo JSON de credenciais para o teste.")
             return

        # Further validation: selected voice must be valid for the selected language
        available_voices_for_lang = GoogleCloudTTS.get_local_voices(language_code=current_lang_code)
        available_voice_names = [v['name'] for v in available_voices_for_lang]
        if current_voice_name not in available_voice_names:
            QMessageBox.warning(self, "Erro de Validação",
                                f"A voz selecionada '{current_voice_name}' não é válida para o idioma '{current_lang_code}'.\n"
                                "Por favor, atualize a lista de vozes ou selecione uma voz/idioma diferente.")
            return

        # Temporarily update config.params for the duration of this test
        original_params_backup = {
            "gcloud_credential_json": config.params.get("gcloud_credential_json"),
            "gcloud_language_code": config.params.get("gcloud_language_code"),
            "gcloud_voice_name": config.params.get("gcloud_voice_name"),
            "gcloud_audio_encoding": config.params.get("gcloud_audio_encoding")
        }

        config.params['gcloud_credential_json'] = current_cred_path
        config.params['gcloud_language_code'] = current_lang_code
        config.params['gcloud_voice_name'] = current_voice_name
        config.params['gcloud_audio_encoding'] = current_audio_encoding

        try:
            # GoogleCloudTTS() will now use the updated config.params for this instance
            tts_instance = GoogleCloudTTS()

            # Define a temporary file path for the test audio
            # Ensure TEMP_HOME is defined in config and accessible
            if not hasattr(config, 'TEMP_HOME') or not config.TEMP_HOME:
                # Fallback if TEMP_HOME is not set, though it should be
                import tempfile
                temp_dir = tempfile.gettempdir()
                tmp_audio_file = os.path.join(temp_dir, "test_gcloud.mp3")
            else:
                tmp_audio_file = os.path.join(config.TEMP_HOME, "test_gcloud.mp3")

            # The _item_task uses settings loaded during GoogleCloudTTS.__init__
            tts_instance._item_task({
                "filename": tmp_audio_file,
                "text": "This is a test using Google Cloud Text-to-Speech."
                # Role and language for the actual synthesis are taken from
                # tts_instance.voice_name and tts_instance.language_code,
                # which were set from config.params in __init__.
            })
            QMessageBox.information(self, "Teste OK", f"Áudio gerado com sucesso: {tmp_audio_file}")
        except Exception as e:
            # Log the full error for debugging if possible
            config.logger.error(f"Google Cloud TTS test error: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Erro no Teste",
                f"Falha ao testar síntese de voz:\n{str(e)}"
            )
        finally:
            # Restore original params to avoid side effects
            config.params.update(original_params_backup)


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