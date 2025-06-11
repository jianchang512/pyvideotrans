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
            
# New voice and language selection logic:

# 1. Determine target language code for the current task item
raw_target_lang = config.params.get("target_language", "en") # e.g., "pt-br", "en", "zh-cn"
config.logger.debug(f"Raw target language from config.params: {raw_target_lang}")

lang_normalization_map = {
    "en": "en-US", "english": "en-US",
    "pt": "pt-BR", "pt-br": "pt-BR", "portuguese": "pt-BR", "português": "pt-BR",
    "zh-cn": "zh-CN", "chinese simplified": "zh-CN", "中文简体": "zh-CN",
    "es": "es-ES", "spanish": "es-ES",
    "fr": "fr-FR", "french": "fr-FR",
    "de": "de-DE", "german": "de-DE",
    "ja": "ja-JP", "japanese": "ja-JP",
    "ko": "ko-KR", "korean": "ko-KR",
    "ru": "ru-RU", "russian": "ru-RU",
    "it": "it-IT", "italian": "it-IT",
    # Add other mappings if config.params.target_language can store other variants
}
# Normalize using the map first, then pass through if not in map (already specific)
task_target_language_code = lang_normalization_map.get(raw_target_lang.lower(), raw_target_lang)

# Further ensure region code for common base languages if Google TTS expects it
if '-' not in task_target_language_code:
    temp_lower_code = task_target_language_code.lower()
    if temp_lower_code == 'en': task_target_language_code = 'en-US'
    elif temp_lower_code == 'es': task_target_language_code = 'es-ES'
    elif temp_lower_code == 'fr': task_target_language_code = 'fr-FR'
    elif temp_lower_code == 'pt': task_target_language_code = 'pt-BR'
    elif temp_lower_code == 'de': task_target_language_code = 'de-DE'
    elif temp_lower_code == 'ja': task_target_language_code = 'ja-JP'
    elif temp_lower_code == 'ko': task_target_language_code = 'ko-KR'
    elif temp_lower_code == 'ru': task_target_language_code = 'ru-RU'
    elif temp_lower_code == 'it': task_target_language_code = 'it-IT'

config.logger.info(f"Task target language for Google TTS normalized to: {task_target_language_code} (from raw: {raw_target_lang})")

# 2. Get requested voice name
# self.voice_name is gcloud_voice_name from params.json, used as a fallback if role is not set in item
# Ensure self.voice_name itself is not "No" or empty if it's to be a fallback.
default_voice_from_params = self.voice_name if self.voice_name and self.voice_name.strip().lower() != "no" else ""
requested_voice_name = data_item.get("role", default_voice_from_params)

if not requested_voice_name or requested_voice_name.strip().lower() == "no":
    config.logger.info(f"No specific voice role provided by task item or default params. Will select based on language: {task_target_language_code}.")
    requested_voice_name = "" # Explicitly empty to trigger default voice selection for the language

# Initialize final parameters with defaults based on task target language
final_voice_name = requested_voice_name
final_language_code = task_target_language_code

# 3. Try to use/validate with local voice cache
all_voices = GoogleCloudTTS.get_local_voices()
voice_found_in_cache = False

if all_voices:
    if requested_voice_name: # Specific voice role requested
        for voice_detail in all_voices:
            if voice_detail.get('name') == requested_voice_name:
                voice_found_in_cache = True
                cached_lang_codes = voice_detail.get('language_codes', [])
                if cached_lang_codes:
                    if task_target_language_code in cached_lang_codes:
                        final_language_code = task_target_language_code
                        config.logger.info(f"Using cached voice '{final_voice_name}' confirmed for language '{final_language_code}'.")
                    else:
                        final_language_code = cached_lang_codes[0]
                        config.logger.warning(f"Voice '{requested_voice_name}' found in cache (supports {cached_lang_codes}), but not for task target language '{task_target_language_code}'. Using voice's first available language: '{final_language_code}'.")
                else: # Voice in cache, but no language codes listed for it.
                    final_language_code = task_target_language_code
                    config.logger.warning(f"Voice '{requested_voice_name}' found in cache but has no specific language codes listed. Attempting with task language '{final_language_code}'.")
                break
        if not voice_found_in_cache:
            config.logger.info(f"Requested voice '{requested_voice_name}' not found in local cache. Attempting to use it with language '{task_target_language_code}' directly with API.")
            # final_voice_name and final_language_code are already set
    else: # No specific voice role requested, try to find a default for the language
        best_cached_voice_for_lang = ""
        # Try to find a "Standard" voice first
        for voice_detail in all_voices:
            if task_target_language_code in voice_detail.get('language_codes', []):
                if "Standard" in voice_detail.get('name', ''): # Prefer standard voices
                    best_cached_voice_for_lang = voice_detail.get('name')
                    break
        # If no "Standard" voice, take the first available voice for the language
        if not best_cached_voice_for_lang:
            for voice_detail in all_voices:
                if task_target_language_code in voice_detail.get('language_codes', []):
                    best_cached_voice_for_lang = voice_detail.get('name')
                    break

        if best_cached_voice_for_lang:
            final_voice_name = best_cached_voice_for_lang
            # final_language_code is already task_target_language_code
            config.logger.info(f"No specific voice requested. Selected cached voice '{final_voice_name}' for language '{final_language_code}'.")
        else:
            config.logger.warning(f"No specific voice requested and no suitable voice found in local cache for language '{task_target_language_code}'. API will attempt to select a default voice if name is empty.")
            final_voice_name = "" # Let API pick

# Safety net: If language code somehow became empty, use the old global default from self.language_code.
if not final_language_code:
    config.logger.error(f"Critical: Language code could not be determined. Falling back to system default TTS language: '{self.language_code}'.")
    final_language_code = self.language_code # self.language_code is gcloud_language_code (e.g. en-US from params)
    # If voice also became empty, and there's a system default voice, consider using it.
    if not final_voice_name and default_voice_from_params:
         final_voice_name = default_voice_from_params
         config.logger.error(f"Also using system default TTS voice: '{final_voice_name}'.")
elif not final_voice_name and default_voice_from_params and requested_voice_name == "":
    # If no specific voice was requested and we didn't find one in cache for the language,
    # but a global default voice is set in params, should we use it?
    # For now, if requested_voice_name is intentionally empty (to let API pick for language), don't override with global default.
    # Only use default_voice_from_params if requested_voice_name was initially derived from it.
    pass


# Determine SSML gender (existing logic)
gender = getattr(
    SsmlVoiceGender,
    config.params.get("gcloud_ssml_gender", "SSML_VOICE_GENDER_UNSPECIFIED"),
    SsmlVoiceGender.SSML_VOICE_GENDER_UNSPECIFIED # Ensure a valid fallback
)

# Construct VoiceSelectionParams with the determined final_voice_name and final_language_code
voice_params = texttospeech.VoiceSelectionParams(
    language_code=final_language_code,
    name=final_voice_name, # This can be empty if we want Google to pick a default for the language
    ssml_gender=gender,
)
config.logger.info(f"Final Google TTS Request Params: LanguageCode='{final_language_code}', VoiceName='{final_voice_name if final_voice_name else 'API Default'}', Gender='{gender.name}'")
            
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