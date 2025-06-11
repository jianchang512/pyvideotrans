import os
import json
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
    LOCAL_VOICES_FILE = os.path.join(config.ROOT_DIR, "videotrans", "data", "google_cloud_tts_voices.json")

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

    @staticmethod
    def get_local_voices(language_code: str = None) -> list:
        if not os.path.exists(GoogleCloudTTS.LOCAL_VOICES_FILE):
            # config.logger.warning(f"Local voices file not found: {GoogleCloudTTS.LOCAL_VOICES_FILE}") # Less noisy
            return []
        try:
            with open(GoogleCloudTTS.LOCAL_VOICES_FILE, 'r', encoding='utf-8') as f:
                voices = json.load(f)
        except Exception as e:
            config.logger.error(f"Error loading local voices file: {e}")
            return []

        if language_code:
            # Ensure language_code format matches what's in language_codes list (e.g. "en-US")
            filtered_voices = [
                voice for voice in voices
                if any(lc.lower() == language_code.lower() for lc in voice.get("language_codes", []))
            ]
            return filtered_voices
        return voices

    @staticmethod
    def _save_voices_to_local_cache(voices_data_list: list):
        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(GoogleCloudTTS.LOCAL_VOICES_FILE)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            with open(GoogleCloudTTS.LOCAL_VOICES_FILE, 'w', encoding='utf-8') as f:
                json.dump(voices_data_list, f, ensure_ascii=False, indent=2)
            config.logger.info(f"Saved {len(voices_data_list)} voices to local cache: {GoogleCloudTTS.LOCAL_VOICES_FILE}")
        except Exception as e:
            config.logger.error(f"Error saving voices to local cache: {e}")

    @staticmethod
    def _fetch_voices_from_api(credential_path: str) -> list:
        global TextToSpeechClient # TextToSpeechClient is defined at module level with try-except
        if TextToSpeechClient is None:
            try: 
                from google.cloud.texttospeech import TextToSpeechClient as TTSClientImport
                TextToSpeechClient = TTSClientImport
                if TextToSpeechClient is None: 
                     raise ImportError("TextToSpeechClient is still None after import attempt.")
            except ImportError:
                config.logger.error("google-cloud-texttospeech client not available for _fetch_voices_from_api.")
                return []

        if not credential_path or not os.path.isfile(credential_path):
            config.logger.error(f"Credential file not found or path not set for API fetch: {credential_path}")
            return []

        fetched_voices_data = []
        try:
            client = TextToSpeechClient.from_service_account_file(credential_path)
            api_voices_result = client.list_voices().voices
            
            # texttospeech module is imported as 'texttospeech' at the top of the file
            for voice in api_voices_result:
                fetched_voices_data.append({
                    "name": voice.name,
                    "language_codes": [lc for lc in voice.language_codes],
                    "ssml_gender": texttospeech.SsmlVoiceGender.Name(voice.ssml_gender),
                    "natural_sample_rate_hertz": voice.natural_sample_rate_hertz
                })
            config.logger.info(f"Fetched {len(fetched_voices_data)} voices from API.")
        except Exception as e:
            config.logger.error(f"Error fetching voices from Google Cloud API: {e}")
            if "PERMISSION_DENIED" in str(e):
                config.logger.error("API permission denied. Check credentials.")
            elif "invalid_grant" in str(e).lower():
                config.logger.error("Invalid or expired API credentials.")
            return [] 
        return fetched_voices_data

    @staticmethod
    def get_and_cache_voices(credential_path: str, language_code_filter: str = None, force_api_fetch: bool = False) -> list:
        cached_voices = GoogleCloudTTS.get_local_voices() 

        if force_api_fetch or not cached_voices:
            if credential_path and os.path.isfile(credential_path):
                config.logger.info(f"Cache is empty or refresh forced. Fetching from API for Google Cloud TTS.")
                api_voices = GoogleCloudTTS._fetch_voices_from_api(credential_path)
                if api_voices: 
                    GoogleCloudTTS._save_voices_to_local_cache(api_voices)
                    cached_voices = api_voices 
                elif not cached_voices: 
                    config.logger.warning("API fetch failed and local cache is empty for Google Cloud TTS.")
                    return [] 
            elif not cached_voices:
                config.logger.warning("Local cache empty and no credential path provided for API fetch (Google Cloud TTS).")
                return [] 

        if language_code_filter:
            final_filtered_voices = [
                voice for voice in cached_voices
                if any(lc.lower() == language_code_filter.lower() for lc in voice.get("language_codes", []))
            ]
            return final_filtered_voices
        return cached_voices