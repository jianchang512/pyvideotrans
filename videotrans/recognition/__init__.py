from pathlib import Path
from typing import Union, List, Dict

from videotrans import translator
from videotrans.configure import config
# 判断各个语音识别模式是否支持所选语言
# 支持返回True，不支持返回错误文字字符串



# 数字代表界面中的现实顺序
FASTER_WHISPER = 0
OPENAI_WHISPER = 1
FUNASR_CN = 2
STT_API = 3
DOUBAO_API = 4
Deepgram = 5
OPENAI_API = 6
CUSTOM_API = 7
GOOGLE_SPEECH = 8
GEMINI_SPEECH = 9
Faster_Whisper_XXL = 10
AI_302 = 11
ElevenLabs = 12

RECOGN_NAME_LIST = [
    'faster-whisper(本地)' if config.defaulelang == 'zh' else 'Faster-whisper',
    'openai-whisper(本地)' if config.defaulelang == 'zh' else 'OpenAI-whisper',
    "阿里FunASR中文(本地)" if config.defaulelang == 'zh' else "FunASR-Chinese",
    "STT语音识别(本地)" if config.defaulelang == 'zh' else "STT Speech API",
    "字节火山字幕生成" if config.defaulelang == 'zh' else "VolcEngine Subtitle API",
    "Deepgram.com" if config.defaulelang == 'zh' else "Deepgram.com",
    "OpenAI语音识别" if config.defaulelang == 'zh' else "OpenAI Speech to Text",
    "自定义识别API" if config.defaulelang == 'zh' else "Custom API",
    "Google识别API(免费)" if config.defaulelang == 'zh' else "Google Speech to Text",
    "Gemini大模型识别" if config.defaulelang == 'zh' else "Gemini AI",
    "Faster-Whisper-XXL.exe",
    "302.AI",
    "ElevenLabs.io"
]


def is_allow_lang(langcode: str = None, recogn_type: int = None,model_name=None):
    if langcode=='auto' and recogn_type not in [FASTER_WHISPER,OPENAI_WHISPER,GEMINI_SPEECH,ElevenLabs]:
        return '仅在 faster-whisper/openai-whisper/Gemini模式下允许检测语言' if config.defaulelang=='zh' else 'Recognition language is only supported in faster-whisper or openai-whisper or Gemini  modes.'
    if recogn_type == FUNASR_CN:
        if model_name=='paraformer-zh' and langcode[:2] !='zh':
            return 'FunASR 下 paraformer-zh  模型仅支持中文语音识别' if config.defaulelang == 'zh' else 'paraformer-zh  models only support Chinese speech recognition'
        if model_name =='SenseVoiceSmall' and langcode[:2] not in ['zh','en','ja','ko']:
            return 'FunASR 下  SenseVoiceSmall 模型仅支持中英日韩语音识别' if config.defaulelang == 'zh' else 'SenseVoiceSmall models only support Chinese,Ja,ko,English speech recognition'
        return True

    if recogn_type == DOUBAO_API and langcode[:2] not in ["zh", "en", "ja", "ko", "es", "fr", "ru"]:
        return '豆包语音识别仅支持中英日韩法俄西班牙语言，其他不支持'
    return True

# 判断 openai whisper和 faster whisper 模型是否存在
def check_model_name(recogn_type=FASTER_WHISPER, name='',source_language_isLast=False,source_language_currentText=''):
    if recogn_type not in [OPENAI_WHISPER, FASTER_WHISPER,Faster_Whisper_XXL]:
        return True
    # 含 / 的需要下载
    if name.find('/') > 0:
        return True
    if name.endswith('.en') and source_language_isLast:
        return '.en结尾的模型不可用于自动检测' if config.defaulelang == 'zh' else 'Models ending in .en may not be used for automated detection'

    if name.endswith('.en') and translator.get_code(show_text=source_language_currentText) != 'en':
        return config.transobj['enmodelerror']

    if recogn_type == OPENAI_WHISPER:
        if name.startswith('distil'):
            return 'distil 开头的模型只可用于 faster-whisper本地模式' if config.defaulelang=='zh' else 'distil-* only use when faster-whisper'
        # 不存在，需下载
        if not Path(config.ROOT_DIR + f"/models/{name}.pt").exists():
            return 'download'
        return True
    model_path=f'models--Systran--faster-whisper-{name}'
    if name=='large-v3-turbo':
        model_path = f'models--mobiuslabsgmbh--faster-whisper-{name}'
    elif name.startswith('distil'):
        model_path = f'models--Systran--faster-{name}'
    
    file=f'{config.ROOT_DIR}/models/{model_path}'
    print(file)
    if recogn_type==Faster_Whisper_XXL:
        PATH_DIR=Path(config.settings.get('Faster_Whisper_XXL','')).parent.as_posix()+f'/.cache/hub/{model_path}'
        print(PATH_DIR)
        if Path(file).exists() or Path(PATH_DIR).exists():
            if Path(file).exists() and not Path(PATH_DIR).exists():
                import threading
                threading.Thread(target=move_model_toxxl,args=(file,PATH_DIR)).start()
            return True
        
    
    if not Path(file).exists():
        return 'download'
    return True



def move_model_toxxl(src,dest):
    import shutil
    config.copying=True
    shutil.copytree(src,dest,dirs_exist_ok=True)
    config.copying=False

# 自定义识别、openai-api识别、zh_recogn识别是否填写了相关信息和sk等
# 正确返回True，失败返回False，并弹窗
def is_input_api(recogn_type: int = None,return_str=False):
    from videotrans.winform import recognapi as recognapi_win,  openairecognapi as openairecognapi_win, doubao as doubao_win,sttapi as sttapi_win,deepgram as deepgram_win, gemini as gemini_win,ai302
    if recogn_type == STT_API and not config.params['stt_url']:
        if return_str:
            return "Please configure the api and key information of the stt channel first."
        sttapi_win.openwin()
        return False
        
    if recogn_type == CUSTOM_API and not config.params['recognapi_url']:
        if return_str:
            return "Please configure the api and key information of the CUSTOM_API channel first."
        recognapi_win.openwin()
        return False

    if recogn_type == OPENAI_API and not config.params['openairecognapi_key']:
        if return_str:
            return "Please configure the api and key information of the OPENAI_API channel first."
        openairecognapi_win.openwin()
        return False
    if recogn_type == DOUBAO_API and not config.params['doubao_appid']:
        if return_str:
            return "Please configure the api and key information of the DOUBAO_API channel first."
        doubao_win.openwin()
        return False
    if recogn_type == Deepgram and not config.params['deepgram_apikey']:
        if return_str:
            return "Please configure the API Key information of the Deepgram channel first."
        deepgram_win.openwin()
        return False
    if recogn_type == GEMINI_SPEECH and not config.params['gemini_key']:
        if return_str:
            return "Please configure the API Key information of the Gemini channel first."
        gemini_win.openwin()
        return False
    if recogn_type == AI_302 and not config.params['ai302_key']:
        if return_str:
            return "Please configure the API Key information of the Gemini channel first."
        ai302.openwin()
        return False
    #ElevenLabs
    if recogn_type == ElevenLabs and not config.params['elevenlabstts_key']:
        if return_str:
            return "Please configure the API Key information of the ElevenLabs channel first."
        from videotrans.winform import elevenlabs as elevenlabs_win
        elevenlabs_win.openwin()
        return False
    return True

# 统一入口
def run(*,
        split_type="all",
        detect_language=None,
        audio_file=None,
        cache_folder=None,
        model_name=None,
        inst=None,
        uuid=None,
        recogn_type: int = 0,
        is_cuda=None,
        target_code=None,
        subtitle_type=0
        ) -> Union[List[Dict], None]:
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return
    if model_name and model_name.startswith('distil-'):
        model_name = model_name.replace('-whisper', '')
    kwargs = {
        "detect_language": detect_language,
        "audio_file": audio_file,
        "cache_folder": cache_folder,
        "model_name": model_name,
        "uuid": uuid,
        "inst": inst,
        "is_cuda": is_cuda,
        "subtitle_type":subtitle_type,
        "target_code":target_code
    }
    if recogn_type == OPENAI_WHISPER:
        from ._openai import OpenaiWhisperRecogn
        return OpenaiWhisperRecogn(**kwargs).run()
    if recogn_type == GOOGLE_SPEECH:
        from ._google import GoogleRecogn
        return GoogleRecogn(**kwargs).run()

    if recogn_type == DOUBAO_API:
        from ._doubao import DoubaoRecogn
        return DoubaoRecogn(**kwargs).run()
    if recogn_type == CUSTOM_API:
        from ._recognapi import APIRecogn
        return APIRecogn(**kwargs).run()
    if recogn_type == STT_API:
        from ._stt import SttAPIRecogn
        return SttAPIRecogn(**kwargs).run()
        
    if recogn_type == OPENAI_API:
        from ._openairecognapi import OpenaiAPIRecogn
        return OpenaiAPIRecogn(**kwargs).run()
    if recogn_type==FUNASR_CN:
        from ._funasr import FunasrRecogn
        return FunasrRecogn(**kwargs).run()
    if recogn_type==Deepgram:
        from ._deepgram import DeepgramRecogn
        return DeepgramRecogn(**kwargs).run()
    if recogn_type==GEMINI_SPEECH:
        from ._gemini import GeminiRecogn
        return GeminiRecogn(**kwargs).run()
    if recogn_type==AI_302:
        from ._ai302 import AI302Recogn
        return AI302Recogn(**kwargs).run()

    if recogn_type==ElevenLabs:
        from ._elevenlabs import ElevenLabsRecogn
        return ElevenLabsRecogn(**kwargs).run()

    if split_type == 'avg':
        from ._average import FasterAvg
        return FasterAvg(**kwargs).run()

    from ._overall import FasterAll
    return FasterAll(**kwargs).run()
