import os
from typing import Union, List, Dict
from videotrans import translator
from videotrans.configure import config

# 数字代表界面中的现实顺序
from videotrans.configure.config import tr,logs

FASTER_WHISPER = 0
OPENAI_WHISPER = 1
FUNASR_CN = 2

OPENAI_API = 3
GEMINI_SPEECH = 4
QWEN3ASR = 5
ZIJIE_RECOGN_MODEL=6

ElevenLabs = 7
Deepgram = 8
DOUBAO_API = 9


PARAKEET = 10
Whisper_CPP=11
Faster_Whisper_XXL = 12
AI_302 = 13
STT_API = 14
GOOGLE_SPEECH = 15
CUSTOM_API = 16

RECOGN_NAME_LIST = [
    tr("Faster-whisper"),
    tr("OpenAI-whisper"),
    tr("FunASR-Chinese"),
    
    tr("OpenAI Speech to Text"),
    tr("Gemini AI"),
    tr("Ali Qwen3-ASR"),    
    tr("VolcEngine STT"),
    
    "ElevenLabs.io",
    "Deepgram.com",
    tr("VolcEngine Subtitle API"),
    
    "Parakeet-tdt",
    "Whisper.cpp",
    "Faster-Whisper-XXL.exe",

    "302.AI",
    tr("STT Speech API"),
    tr("Google Speech to Text"),
    tr("Custom API"),
]


def is_allow_lang(langcode: str = None, recogn_type: int = None, model_name=None):
    if (langcode == 'auto' or not langcode) and recogn_type not in [FASTER_WHISPER, OPENAI_WHISPER, GEMINI_SPEECH, ElevenLabs,Faster_Whisper_XXL,Whisper_CPP]:
        return tr("Recognition language is only supported in faster-whisper or openai-whisper or Gemini  modes.")
    if recogn_type == FUNASR_CN:
        if model_name == 'paraformer-zh' and langcode[:2] not in ('zh', 'yu'):
            return tr("paraformer-zh  models only support Chinese speech recognition")
        if model_name == 'SenseVoiceSmall' and langcode[:2] not in ['zh', 'en', 'ja', 'ko', 'yu']:
            return tr("SenseVoiceSmall models only support Chinese,Ja,ko,English speech recognition")
        return True
    if recogn_type == PARAKEET and langcode[:2] not in ('en', 'ja'):
        return tr("Parakeet-tdt  models only support English & Ja speech recognition")
    if recogn_type == DOUBAO_API and langcode[:2] not in ["zh", "en", "ja", "ko", "es", "fr", "ru", 'yu']:
        return '豆包语音识别仅支持中英日韩法俄西班牙语言，其他不支持'
    return True


# 判断 openai whisper和 faster whisper 模型是否存在
def check_model_name(recogn_type=FASTER_WHISPER, name='', source_language_isLast=False, source_language_currentText=''):
    if recogn_type not in [OPENAI_WHISPER, FASTER_WHISPER]:
        return True
    # 含 / 的需要下载
    if name.find('/') > 0:
        return True
    if name.endswith('.en') and source_language_isLast:
        return tr("Models ending in .en may not be used for automated detection")

    if (name.endswith('.en') or name.startswith("distil-")) and translator.get_code(show_text=source_language_currentText) != 'en':
        return tr('enmodelerror')

    if recogn_type == OPENAI_WHISPER:
        if name.startswith('distil'):
            return tr("distil-* only use when faster-whisper")

        return True
    return True



# 自定义识别、openai-api识别、zh_recogn识别是否填写了相关信息和sk等
# 正确返回True，失败返回False，并弹窗
def is_input_api(recogn_type: int = None, return_str=False):
    from videotrans.winform import recognapi as recognapi_win, openairecognapi as openairecognapi_win, \
        doubao as doubao_win, sttapi as sttapi_win, deepgram as deepgram_win, gemini as gemini_win, ai302, \
        parakeet as parakeet_win,qwenmt as qwenmt_win,zijierecognmodel as zijierecogn_win
    if recogn_type == STT_API and not config.params.get('stt_url',''):
        if return_str:
            return "Please configure the api and key information of the stt channel first."
        sttapi_win.openwin()
        return False

    if recogn_type == PARAKEET and not config.params.get('parakeet_address',''):
        if return_str:
            return "Please configure the url address."
        parakeet_win.openwin()
        return False
    if recogn_type == QWEN3ASR and not config.params.get('qwenmt_key',''):
        if return_str:
            return "Please configure the api key ."
        qwenmt_win.openwin()
        return False

    if recogn_type == CUSTOM_API and not config.params.get('recognapi_url',''):
        if return_str:
            return "Please configure the api and key information of the CUSTOM_API channel first."
        recognapi_win.openwin()
        return False

    if recogn_type == OPENAI_API and not config.params.get('openairecognapi_key',''):
        if return_str:
            return "Please configure the api and key information of the OPENAI_API channel first."
        openairecognapi_win.openwin()
        return False
    if recogn_type == DOUBAO_API and not config.params.get('doubao_appid',''):
        if return_str:
            return "Please configure the api and key information of the DOUBAO_API channel first."
        doubao_win.openwin()
        return False
    if recogn_type == ZIJIE_RECOGN_MODEL and not config.params.get('zijierecognmodel_appid',''):
        if return_str:
            return "Please configure the api and key information of the Volcengine channel first."
        zijierecogn_win.openwin()
        return False
    if recogn_type == Deepgram and not config.params.get('deepgram_apikey',''):
        if return_str:
            return "Please configure the API Key information of the Deepgram channel first."
        deepgram_win.openwin()
        return False
    if recogn_type == GEMINI_SPEECH and not config.params.get('gemini_key',''):
        if return_str:
            return "Please configure the API Key information of the Gemini channel first."
        gemini_win.openwin()
        return False
    if recogn_type == AI_302 and not config.params.get('ai302_key',''):
        if return_str:
            return "Please configure the API Key information of the Gemini channel first."
        ai302.openwin()
        return False
    # ElevenLabs
    if recogn_type == ElevenLabs and not config.params.get('elevenlabstts_key',''):
        if return_str:
            return "Please configure the API Key information of the ElevenLabs channel first."
        from videotrans.winform import elevenlabs as elevenlabs_win
        elevenlabs_win.openwin()
        return False
    return True


# 统一入口
def run(*,
        split_type=0,
        detect_language=None,
        audio_file=None,
        cache_folder=None,
        model_name=None,
        uuid=None,
        recogn_type: int = 0,
        is_cuda=None,
        subtitle_type=0
        ) -> Union[List[Dict], None]:
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return
    kwargs = {
        "detect_language": detect_language,
        "audio_file": audio_file,
        "cache_folder": cache_folder,
        "model_name": model_name,
        "uuid": uuid,
        "is_cuda": is_cuda,
        "subtitle_type": subtitle_type,
        "recogn_type":recogn_type

    }            

    if recogn_type == GOOGLE_SPEECH:
        from ._google import GoogleRecogn
        return GoogleRecogn(**kwargs).run()

    if recogn_type == DOUBAO_API:
        from ._doubao import DoubaoRecogn
        return DoubaoRecogn(**kwargs).run()
    if recogn_type == ZIJIE_RECOGN_MODEL:
        from ._zijiemodel import ZijieRecogn
        return ZijieRecogn(**kwargs).run()
    if recogn_type == CUSTOM_API:
        from ._recognapi import APIRecogn
        return APIRecogn(**kwargs).run()
    if recogn_type == STT_API:
        from ._stt import SttAPIRecogn
        return SttAPIRecogn(**kwargs).run()

    if recogn_type == OPENAI_API:
        from ._openairecognapi import OpenaiAPIRecogn
        return OpenaiAPIRecogn(**kwargs).run()
    if recogn_type == QWEN3ASR:
        from ._qwen3asr import Qwen3ASRRecogn
        return Qwen3ASRRecogn(**kwargs).run()
    if recogn_type == FUNASR_CN:     
        from ._funasr import FunasrRecogn
        return FunasrRecogn(**kwargs).run()
    if recogn_type == Deepgram:
        from ._deepgram import DeepgramRecogn
        return DeepgramRecogn(**kwargs).run()
    if recogn_type == GEMINI_SPEECH:
        from ._gemini import GeminiRecogn
        return GeminiRecogn(**kwargs).run()
    if recogn_type == PARAKEET:
        from ._parakeet import ParaketRecogn
        return ParaketRecogn(**kwargs).run()
    if recogn_type == AI_302:
        from ._ai302 import AI302Recogn
        return AI302Recogn(**kwargs).run()

    if recogn_type == ElevenLabs:
        from ._elevenlabs import ElevenLabsRecogn
        return ElevenLabsRecogn(**kwargs).run()
    
    from videotrans.process._iscache import _MODELS
    if recogn_type != OPENAI_WHISPER:
        kwargs['split_type']=0 if split_type==0 or model_name not in _MODELS else 1
    from ._overall import FasterAll    
    return FasterAll(**kwargs).run()

