def openwin():
    from PySide6.QtWidgets import (
        QWidget, QFormLayout, QLineEdit, QComboBox, QPushButton,
        QFileDialog, QMessageBox, QHBoxLayout
    )
    from videotrans.configure import config
    from videotrans.tts._googlecloud import GoogleCloudTTS

    # Import lazy do TextToSpeechClient
    from videotrans.util import tools

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
            self.lang_cb.currentTextChanged.connect(self.populate_voices)
            # popula voices logo na abertura
            self.populate_voices(self.lang_cb.currentText())

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
                        tools.show_error(
                            "O pacote google-cloud-texttospeech não está instalado.\n\n"
                            "Por favor, instale-o com:\n"
                            "pip install google-cloud-texttospeech"
                        )
                        return False
            return True

        def populate_voices(self, lang_code):
            if not self._check_tts_client():
                return

            try:
                client = TextToSpeechClient.from_service_account_file(
                    self.cred_le.text().strip()
                )
                all_voices = client.list_voices().voices
                filtered = sorted([
                    v.name for v in all_voices
                    if any(lang_code.lower() in lc.lower() for lc in v.language_codes)
                ])
                self.voice_cb.clear()
                self.voice_cb.addItems(filtered)
                # seleciona o que estava salvo ou o primeiro disponível
                saved = config.params.get("gcloud_voice_name", "")
                if saved in filtered:
                    self.voice_cb.setCurrentText(saved)
                elif filtered:
                    self.voice_cb.setCurrentText(filtered[0])
            except Exception as e:
                tools.show_error(
                    f"Falha ao buscar vozes do Google Cloud TTS:\n{str(e)}"
                )

        def save(self):
            if not self._check_tts_client():
                return

            # Atualiza apenas as configurações do Google Cloud TTS
            config.params.update({
                "gcloud_credential_json": self.cred_le.text().strip(),
                "gcloud_language_code": self.lang_cb.currentText(),
                "gcloud_voice_name": self.voice_cb.currentText(),
                "gcloud_audio_encoding": self.enc_cb.currentText()
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
                tmp = "test_gcloud.wav"
                tts._item_task({"filename": tmp, "text": "This is a test."})
                QMessageBox.information(self, "Teste OK", f"Áudio gerado com sucesso: {tmp}")
            except Exception as e:
                tools.show_error(
                    f"Falha ao testar síntese de voz:\n{str(e)}"
                )

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
