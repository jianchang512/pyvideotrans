from typing import Union, Type
from videotrans.configure.config import tr, params, app_cfg
from videotrans.tts._base import BaseTTS
from videotrans import get_class
from ._constants import *


# 检查当前配音渠道是否支持所选配音语言
# 返回True为支持，其他为不支持并返回错误字符串
def is_allow_lang(langcode: str = None, tts_type: int = None):
    """

    Args:
        langcode: 语言代码
        tts_type: TTS渠道ID

    Returns:

    """
    if langcode is None or tts_type is None or tts_type in [EDGE_TTS, G_TTS, HIGGS_AUDIO_TTS, OMNIVOICE_TTS, AZURE_TTS]:
        return True

    name = ID_NAME_DICT.get(tts_type).name
    _lang2 = langcode.split('-')[0]
    if tts_type == DOUBAO2_TTS and _lang2 not in ["zh", "en", "ja", "id", "es", "ar", "de", "fr", "ko", "ms", "pt","ru", "th", "fil", "vi", "it","yue"]:
        return name + tr('Dubbing channel') + ' ' + tr('may not support') + tr(langcode)

    if tts_type in [CHATTTS, ZIPVOICE_TTS, VITSCNEN_TTS, SPARK_TTS] and _lang2 not in ['zh', 'en']:
        return name + tr('Dubbing channel') + ' ' + tr('may not support') + tr(langcode)

    if tts_type in [INDEX_TTS] and _lang2 not in ['zh', 'en', 'ja', 'es', 'ar']:
        return name + tr('Dubbing channel') + ' ' + tr('may not support') + tr(langcode)

    if tts_type == GPTSOVITS_TTS and _lang2 not in ['zh', 'ja', 'ko', 'en', 'yue']:
        return name + tr('Dubbing channel') + ' ' + tr('may not support') + tr(langcode)

    # 中文、英文、日文、韩文、德文、法文、俄文、葡萄牙文、西班牙文、意大利文
    if tts_type == QWEN3LOCAL_TTS and _lang2 not in ['zh', 'ja', 'ko', 'en', 'yue', 'de', 'fr', 'ru', 'pt', 'es', 'it']:
        return name + tr('Dubbing channel') + ' ' + tr('may not support') + tr(langcode)

    if tts_type == F5_TTS and _lang2 not in ['zh', 'ja', 'it', 'en', 'de', 'fr', 'ru', 'hi', 'es', 'ar', 'tr', 'vi']:
        return name + tr('Dubbing channel') + ' ' + tr('may not support') + tr(langcode)

    if tts_type == Supertonic_TTS and _lang2 not in ['ar', 'cs', 'nl', 'en', 'fr', 'de', 'el', 'hi', 'hu', 'id', 'it',
                                                     'ja', 'ko', 'pl', 'pt', 'ro', 'ru', 'es', 'sv', 'tr', 'uk', 'vi']:
        return name + tr('Dubbing channel') + tr('may not support') + tr(langcode)

    if tts_type == MOSS_TTS and _lang2 not in ["zh", "yue", "en", "de", "es", "fr", "ja", "it", "hu", "ko", "ru", "fa",
                                               "ar", "pl", "pt", "cs", "sv", "el", "tr", "da"]:
        return name + tr('Dubbing channel') + tr('may not support') + tr(langcode)

    if tts_type == CHATTERBOX_TTS and _lang2 not in ["zh", "yue", "en", "de", "es", "fr", "ja", "it", "ko", "ru", "ar",
                                                     "pl", "pt", "sv", "el", "tr", "da", "he", 'hi', "ms", "nl", "nb"]:
        return name + tr('Dubbing channel') + tr('may not support') + tr(langcode)

    if tts_type == CONFUCIUS_TTS and _lang2 not in ["zh", "en", "ja", "ko", "de", "fr", "th",
                                                    "id", "vi", "es", "pt", "it", "ru", "ms"]:
        return name + tr('Dubbing channel') + tr('may not support') + tr(langcode)
    _mainsupport = ["ar", "cs", "de", "el", "en", "es", "fa", "fr", "hi", "hu", "id", "it", "kk", "nl", "pl", "pt",
                    "ro", "ru", "sv", "tr", "uk", "ur", "vi", "zh", "ja"]
    return True


# 判断是否填写了相关配音渠道所需要的信息,例如 SK API地址等
# 正确返回True，失败返回False，并弹窗
def is_input_api(tts_type: int = None, return_str=False):
    _cls = ID_NAME_DICT.get(tts_type)
    if not _cls:
        return True
    if _cls.key_name and not params.get(_cls.key_name):
        if return_str:
            return "Please configure the SK or API information of the channel first."
        from videotrans import winform
        winform.get_win(_cls.win)
    return True


# 使用 clone 音色时提示，字幕需保持在 3-10s
def clone_tips(role: str = 'No'):
    return tr('clone_dubb_tips1') + tr('clone_dubb_tips2') if role == 'clone' else ""


# 统一调用 tts渠道入口，通过 tts_type 调用对应渠道
def run(*, queue_tts=None, language="", uuid=None, play=False, tts_type=0, is_cuda=False,
        is_redubb=False) -> None:
    """

    Args:
        queue_tts: 需配音的字幕数据队列
        language:
        uuid:
        play: 是否需立即播放，当试听时为True
        tts_type: 渠道id
        is_cuda:
        is_redubb: 是否是 在校对配音页面重新进行配音

    Returns:

    """
    # 需要并行的数量3
    if len(queue_tts) < 1 or app_cfg.exit_soft or (uuid and uuid in app_cfg.stoped_uuid_set): return

    kwargs = {
        "queue_tts": queue_tts,
        "language": language.lower() if language else "",
        "uuid": uuid,
        "play": play,
        "tts_type": tts_type,
        "is_cuda": is_cuda,
        "is_redubb": is_redubb
    }

    _cls: Union[Type[BaseTTS], None] = get_class(tts_type, "tts", ID_NAME_DICT)
    if not _cls:
        from videotrans.configure.excepts import DubbingSrtError
        raise DubbingSrtError(f'No this TTS Channel:{tts_type=}')

    return _cls(**kwargs).run()  # type:ignore
