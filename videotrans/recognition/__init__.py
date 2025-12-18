from typing import Union, List, Dict
from videotrans import translator
from videotrans.configure import config
import time
# 数字代表界面中的现实顺序
from videotrans.configure.config import tr
# 这2个渠道 不可局部导入，否则可能卡住
from videotrans.recognition._overall import FasterAll
from videotrans.recognition._funasr import FunasrRecogn




FASTER_WHISPER = 0
OPENAI_WHISPER = 1
FUNASR_CN = 2
HUGGINGFACE_ASR = 3

OPENAI_API = 4
GEMINI_SPEECH = 5
QWEN3ASR = 6
ZIJIE_RECOGN_MODEL=7

ElevenLabs = 8
Deepgram = 9
DOUBAO_API = 10


PARAKEET = 11
Whisper_CPP=12
Faster_Whisper_XXL = 13
AI_302 = 14
STT_API = 15
GOOGLE_SPEECH = 16
WHISPERX_API = 17
CUSTOM_API = 18

_ID_NAME_DICT = {
    FASTER_WHISPER:tr("Faster-whisper"),
    OPENAI_WHISPER:tr("OpenAI-whisper"),
    FUNASR_CN:tr("FunASR-Chinese"),
    HUGGINGFACE_ASR:'Huggingface_ASR',
    
    OPENAI_API:tr("OpenAI Speech to Text"),
    GEMINI_SPEECH:tr("Gemini AI"),
    QWEN3ASR:tr("Ali Qwen3-ASR"),    
    ZIJIE_RECOGN_MODEL:tr("VolcEngine STT"),
    
    ElevenLabs:"ElevenLabs.io",
    Deepgram:"Deepgram.com",
    DOUBAO_API:tr("VolcEngine Subtitle API"),
    
    PARAKEET:"Parakeet-tdt",
    Whisper_CPP:"Whisper.cpp",
    Faster_Whisper_XXL:"Faster-Whisper-XXL.exe",

    AI_302:"302.AI",
    STT_API:tr("STT Speech API"),
    GOOGLE_SPEECH:tr("Google Speech to Text"),
    WHISPERX_API:"WhisperX",
    CUSTOM_API:tr("Custom API"),
}
RECOGN_NAME_LIST=list(_ID_NAME_DICT.values())

HUGGINGFACE_ASR_MODELS={
"parakeet-ctc-1.1b":['en'],
"moonshine-base-ar":['ar'],
"moonshine-base-zh":['zh'],
"moonshine-base":['en'],
"moonshine-base-ja":['ja'],
"moonshine-base-ko":['ko'],
"moonshine-base-es":['es'],
"moonshine-base-uk":['uk'],
"moonshine-base-vi":['vi'],
}

def is_allow_lang(langcode: str = None, recogn_type: int = None, model_name=None):
    if (langcode == 'auto' or not langcode) and recogn_type not in [FASTER_WHISPER, OPENAI_WHISPER, GEMINI_SPEECH, ElevenLabs,Faster_Whisper_XXL,Whisper_CPP]:
        return tr("Recognition language is only supported in faster-whisper or openai-whisper or Gemini  modes.")

    if recogn_type==HUGGINGFACE_ASR and model_name in HUGGINGFACE_ASR_MODELS:
        model_lang_support=",".join(HUGGINGFACE_ASR_MODELS[model_name])
        if langcode not in HUGGINGFACE_ASR_MODELS[model_name]:
            return tr("This model only supports speech transcription of these languages:")+model_lang_support
    return True


# 判断 openai whisper和 faster whisper 模型是否存在
def check_model_name(recogn_type=FASTER_WHISPER, name='',  source_language_currentText=''):
    if recogn_type not in [OPENAI_WHISPER, FASTER_WHISPER]:
        return True
    # 含 / 的需要下载
    if name.find('/') > 0:
        return True
    if recogn_type == OPENAI_WHISPER and name.startswith('distil'):
        return tr("distil-* only use when faster-whisper")
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
        subtitle_type=0,
        max_speakers=-1 # -1 不启用说话人识别,0=不限制数量，>0最大数量
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
        "recogn_type":recogn_type,
        "split_type":split_type,
        "max_speakers":max_speakers
    }

    if recogn_type == GOOGLE_SPEECH:
        from videotrans.recognition._google import GoogleRecogn
        return GoogleRecogn(**kwargs).run()

    if recogn_type == DOUBAO_API:
        from videotrans.recognition._doubao import DoubaoRecogn
        return DoubaoRecogn(**kwargs).run()
    if recogn_type == ZIJIE_RECOGN_MODEL:
        from videotrans.recognition._zijiemodel import ZijieRecogn
        return ZijieRecogn(**kwargs).run()
    if recogn_type == CUSTOM_API:
        from videotrans.recognition._recognapi import APIRecogn
        return APIRecogn(**kwargs).run()
    if recogn_type == STT_API:
        from videotrans.recognition._stt import SttAPIRecogn
        return SttAPIRecogn(**kwargs).run()

    if recogn_type == OPENAI_API:
        from videotrans.recognition._openairecognapi import OpenaiAPIRecogn
        return OpenaiAPIRecogn(**kwargs).run()
    if recogn_type == WHISPERX_API:
        from videotrans.recognition._whisperx import WhisperXRecogn
        return WhisperXRecogn(**kwargs).run()
    if recogn_type == QWEN3ASR:
        from videotrans.recognition._qwen3asr import Qwen3ASRRecogn
        return Qwen3ASRRecogn(**kwargs).run()
    if recogn_type == FUNASR_CN:       
        return FunasrRecogn(**kwargs).run()
    if recogn_type == Deepgram:
        from videotrans.recognition._deepgram import DeepgramRecogn
        return DeepgramRecogn(**kwargs).run()
    if recogn_type == GEMINI_SPEECH:
        from videotrans.recognition._gemini import GeminiRecogn
        return GeminiRecogn(**kwargs).run()
    if recogn_type == PARAKEET:
        from videotrans.recognition._parakeet import ParaketRecogn
        return ParaketRecogn(**kwargs).run()
    if recogn_type == AI_302:
        from videotrans.recognition._ai302 import AI302Recogn
        return AI302Recogn(**kwargs).run()
    if recogn_type == ElevenLabs:
        from videotrans.recognition._elevenlabs import ElevenLabsRecogn
        return ElevenLabsRecogn(**kwargs).run()
    if recogn_type == HUGGINGFACE_ASR:
        from videotrans.recognition._huggingface import HuggingfaceRecogn
        return HuggingfaceRecogn(**kwargs).run()
    return FasterAll(**kwargs).run()

