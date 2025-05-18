import os
from videotrans.tts._base import BaseTTS
from videotrans.configure import config
from videotrans.util import tools
from google.cloud import texttospeech

# import lazy do client de TTS
try:
    from google.cloud.texttospeech import (
        TextToSpeechClient,
        SynthesisInput,
        VoiceSelectionParams,
        AudioConfig,
        SsmlVoiceGender,
        AudioEncoding,
    )
except ImportError:
    TextToSpeechClient = None


class GoogleCloudTTS(BaseTTS):
    """
    TTS usando Google Cloud Text-to-Speech.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        # parâmetros vindos do params.json
        self.cred_path = config.params.get("gcloud_credential_json", "").strip()
        self.language_code = config.params.get("gcloud_language_code", "en-US")
        self.voice_name = config.params.get("gcloud_voice_name", "")
        self.encoding = config.params.get("gcloud_audio_encoding", "MP3")
        
        if not self.cred_path or not os.path.isfile(self.cred_path):
            raise Exception("Arquivo de credenciais do Google Cloud TTS não configurado ou não encontrado")

    def _check_client(self):
        """Verifica se o cliente TTS está disponível e se o arquivo de credenciais existe."""
        if TextToSpeechClient is None:
            raise RuntimeError(
                "Pacote google-cloud-texttospeech não encontrado.\n"
                "Execute: pip install google-cloud-texttospeech"
            )
        if not os.path.isfile(self.cred_path):
            raise RuntimeError(
                f"Arquivo de credenciais Google não encontrado: {self.cred_path}\n"
                "Configure o caminho do arquivo JSON em Configurações > Google Cloud TTS"
            )

    def _exec(self):
        """Dispara threads conforme BaseTTS."""
        self._local_mul_thread()

    def _item_task(self, data_item: dict):
        """
        Executa síntese para cada segmento de texto.
        
        Args:
            data_item (dict): Dicionário contendo:
                - text: texto a ser sintetizado
                - role: nome da voz a ser usada
                - filename: caminho do arquivo de saída
                - rate: taxa de fala como string (ex: "+10%", "-5%")
                - pitch: tom da voz
        """
        if not data_item or tools.vail_file(data_item["filename"]):
            return

        text = data_item["text"].strip()
        if not text:
            return

        # checa dependências antes de tudo
        self._check_client()

        try:
            if not self.client:
                self.client = texttospeech.TextToSpeechClient.from_service_account_file(self.cred_path)

            # prepara request
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # tenta inferir gênero se precisar
            gender = getattr(
                SsmlVoiceGender,
                config.params.get("gcloud_ssml_gender", "SSML_VOICE_GENDER_UNSPECIFIED"),
                None
            )
            
            # pega a voz (role) que veio do pipeline, ou usa o default do config
            voice_name = data_item.get("role", self.voice_name)
            if not voice_name or voice_name == "No":
                config.logger.warning("Nenhuma voz selecionada, usando voz padrão")
                voice_name = self.voice_name
                
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,  # o idioma (ex: pt-BR)
                name=voice_name,
                ssml_gender=gender,
            )
            
            # Extrai e normaliza o speaking_rate
            rate_str = data_item.get("rate", "+0%")
            # remove sinal de +/– e % e converte para float
            rate_val = 0.0
            try:
                rate_val = float(rate_str.replace("%", "").replace("+", ""))
            except ValueError:
                config.logger.warning(f"Taxa de fala inválida: {rate_str}, usando 0%")
                rate_val = 0.0
            # converte de percentual para fator (ex: "+10%" → 1.10)
            speaking_rate = 1.0 + (rate_val / 100.0)
            
            # Extrai e normaliza o pitch
            pitch_str = data_item.get("pitch", "+0Hz")
            pitch_val = 0.0
            try:
                # Remove Hz e converte para float
                pitch_val = float(pitch_str.replace("Hz", "").replace("+", ""))
            except ValueError:
                config.logger.warning(f"Tom inválido: {pitch_str}, usando 0Hz")
                pitch_val = 0.0
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=getattr(texttospeech.AudioEncoding, self.encoding),
                speaking_rate=speaking_rate,
                pitch=pitch_val
            )

            # chamada à API
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config
            )

            # garante diretório
            out_path = data_item["filename"]
            parent = os.path.dirname(out_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

            # grava saída
            with open(out_path, "wb") as f:
                f.write(response.audio_content)

            # atualiza progresso
            self.has_done += 1
            self.error = ""
            self._signal(text=f"{self.has_done}/{self.len}")

        except Exception as e:
            self.error = str(e)
            config.logger.error(f"Erro ao sintetizar voz com Google Cloud TTS: {str(e)}")
            self._signal(text=f"Erro: {self.error}")
            raise 