from pathlib import Path
from typing import Union, List, Type

from videotrans import winform, get_class
from videotrans.configure import constants
from videotrans.configure.config import tr, params, app_cfg, logger, ROOT_DIR, settings
from videotrans.configure.constants import Qwenasr_Models
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from ._constants import *


# 根据渠道id获取模型列表
def get_model_by_type(recogn_type: int) -> List[str]:
    if recogn_type == Deepgram:
        return constants.DEEPGRAM_MODEL
    if recogn_type == Whisper_CPP:
        return settings.get('Whisper_cpp_models', '').split(',')
    if recogn_type == WHISPER_NET:
        return settings.get('Whisper_net_models', '').split(',')
    if recogn_type == QWENASR:
        return constants.QWENASR_LOCAL
    if recogn_type == FUNASR_CN:
        return constants.FUNASR_MODEL
    if recogn_type == HUGGINGFACE_ASR:
        return list(HUGGINGFACE_ASR_MODELS.keys())
    if recogn_type == OPENAI_WHISPER:
        return constants.Openai_Whisper_Models.split(',')
    if recogn_type == QWEN3ASR:
        return Qwenasr_Models.split(',')

    return settings.get('model_list', '').split(',')


# 判断所用渠道和模型是否支持该语言的语音识别
# langcode=语言代码，
# recogn_type=识别渠道,
# model_name=模型名字
def is_allow_lang(langcode: str = None, recogn_type: int = None, model_name=None):
    if recogn_type in [FASTER_WHISPER, OPENAI_WHISPER, WHISPERX_API, Faster_Whisper_XXL, Whisper_CPP, OPENAI_API,
                       AI_302, GEMINI_SPEECH, WHISPER_NET, GOOGLE_SPEECH]:
        return True

    # huggingface_asr 渠道里的 openai 和 Systran 模型也支持所有语言
    if recogn_type == HUGGINGFACE_ASR:
        if not HUGGINGFACE_ASR_MODELS.get(model_name):
            return True

        if langcode not in HUGGINGFACE_ASR_MODELS[model_name]:
            return tr(HUGGINGFACE_ASR_MODELS[model_name])
        return True

    if recogn_type == DOLPHIN:
        return tr('40 Eastern languages and 22 Chinese dialects')

    if recogn_type == FIREREDASR:
        return tr('Chinese & English and Chinese dialects')

    return True


# 判断是否填写了 SK API 等
# 正确返回True，失败返回False，并弹窗
def is_input_api(recogn_type: int = None, return_str=False):
    _cls = ID_NAME_DICT.get(recogn_type)
    if not _cls: return True
    if _cls.key_name and not params.get(_cls.key_name):
        if return_str:
            return f"Please configure the API Key information of the {_cls.name} channel first."
        winform.get_win(_cls.win)
    return True


# 统一入口
def run(*,
        detect_language="",
        audio_file=None,
        cache_folder=None,
        model_name=None,
        uuid=None,
        recogn_type: int = 0,
        is_cuda=None,
        subtitle_type=0,
        max_speakers=-1,
        recogn2pass=False
        ) -> Union[List[SrtItem], None]:
    """

    Args:
        detect_language: 语言代码或 auto
        audio_file: wav 16k 单声道
        cache_folder: tmp下缓存目录
        model_name: 模型
        uuid:
        recogn_type: 渠道ID
        is_cuda: 是否使用cuda加速
        subtitle_type: 嵌入字幕类型
        max_speakers: # -1 不启用说话人识别,0=不限制数量，>0最大数量
        recogn2pass: # 是否是二次识别，生成简短字幕

    Returns:

    """
    if app_cfg.exit_soft or (uuid and uuid in app_cfg.stoped_uuid_set): return
    kwargs = {
        "detect_language": detect_language.lower() if detect_language else "",
        "audio_file": audio_file,
        "cache_folder": cache_folder,
        "model_name": model_name,
        "uuid": uuid,
        "is_cuda": is_cuda,
        "subtitle_type": subtitle_type,
        "recogn_type": recogn_type,
        "max_speakers": max_speakers,
        "recogn2pass": recogn2pass
    }
    _cls: Union[Type[BaseRecogn], None] = get_class(recogn_type, "recognition", ID_NAME_DICT)
    if not _cls:
        raise RuntimeError(f'No this Recognition Channel:{recogn_type=}')

    return _cls(**kwargs).run()  # type:ignore
