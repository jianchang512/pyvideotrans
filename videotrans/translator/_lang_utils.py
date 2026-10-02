import re
from typing import Tuple

from videotrans.configure._languages_dict import LANGUAGE_M2M100
from videotrans.configure.constants import  SUBTITLE_CODE, SUBTITLE_CODE_B
from videotrans.configure.config import tr, params, logger

from videotrans import winform
from videotrans.translator._constants import (
    GOOGLE_INDEX, MICROSOFT_INDEX, M2M100_INDEX,
    QWENMT_INDEX,
    TENCENT_INDEX, BAIDU_INDEX, DEEPL_INDEX, DEEPLX_INDEX, ALI_INDEX,
    LIBRE_INDEX, TRANSAPI_INDEX, CAMB_INDEX,
    AI_TRANS_CHANNELS, ID_NAME_DICT
)
from videotrans.translator._lang_codes import LANGNAME_DICT_REV, LANG_CODE


# 判断当前翻译通道和目标语言是否允许翻译
# translate_type翻译通道
# show_target 翻译后显示的目标语言名称
# only_key=True 仅检测 key 和api，不判断目标语言
# 判断是否支持该语言时，仅提示，不再报错
def is_allow_translate(*, translate_type=None, show_target=None, only_key=False, return_str=False):
    if not translate_type or translate_type in [GOOGLE_INDEX, MICROSOFT_INDEX]:
        return True

    _cls = ID_NAME_DICT.get(translate_type)
    if not _cls:
        return True
    if _cls.key_name and not params.get(_cls.key_name):
        if return_str:
            return "Please configure the SK or API information of the channel first."
        winform.get_win(_cls.win)
        return True

    # 如果只需要判断是否填写了 api key 等信息，到此返回
    if only_key or translate_type in AI_TRANS_CHANNELS:
        return True

    if not show_target: return True
    # 再判断是否为No，即不支持
    index = 0
    target_list = None
    if translate_type == BAIDU_INDEX:
        index = 2
    elif translate_type in [DEEPLX_INDEX, DEEPL_INDEX]:
        index = 3
    elif translate_type == TENCENT_INDEX:
        index = 4
    elif translate_type == LIBRE_INDEX:
        index = 5
    elif translate_type == MICROSOFT_INDEX:
        index = 6
    elif translate_type == ALI_INDEX:
        index = 8
    elif translate_type == M2M100_INDEX:
        index = 10
    elif translate_type == QWENMT_INDEX:
        index = 9

    if show_target in LANG_CODE:
        target_list = LANG_CODE[show_target]
    elif LANGNAME_DICT_REV.get(show_target):
        target_list = LANG_CODE.get(LANGNAME_DICT_REV.get(show_target))
    elif show_target == 'zh':
        # 特殊兼容zh
        target_list = LANG_CODE['zh-cn']

    if not target_list or (target_list[index] == 'No'):
        return tr('deepl_nosupport') + f':{show_target}'
    return True


# 获取用于进行语音识别的预设语言，比如语音是英文发音、中文发音
# 根据 原语言进行判断,基本等同于google，但只保留_之前的部分
def get_audio_code(*, show_source=None):
    if not show_source or show_source in ['auto', '-', tr('auto')]:
        return 'auto'
    source_list = LANG_CODE[show_source] if show_source in LANG_CODE else LANG_CODE.get(
        LANGNAME_DICT_REV.get(show_source))
    if source_list and source_list[0]: return source_list[0].split('-')[0]
    # 兼容 zh_tw 等 下划线形式
    _t=show_source.split('_')
    if len(_t)>1 and _t[0] in LANG_CODE:
        return LANG_CODE[_t[0]][0]

    _code = get_code(show_text=show_source)
    return _code.split('-')[0] if _code else 'auto'


# 获取嵌入MP4视频嵌入软字幕的3位字母语言代码 ISO 639-2/T ，根据目标语言确定
# mkv视频需根据此返回的代码再调用 get_mkv_code 获取 ISO 639-2/B
def get_subtitle_code(*, show_target=None):
    try:
        if show_target in LANG_CODE:
            return LANG_CODE[show_target][1]
        if show_target in LANGNAME_DICT_REV:
            return LANG_CODE[LANGNAME_DICT_REV[show_target]][1]
        return SUBTITLE_CODE.get(get_code(show_target), 'zho')
    except Exception as e:
        logger.error(f'获取字幕嵌入3为语言代码错误:{e}')
    return 'eng'


# 如果是 mkv 软字幕，根据mp4所需code换算为  B 标准代码 ISO 639-2/B
def get_mkv_code(code):
    #  ISO 639-2/T :ISO 639-2/B
    return SUBTITLE_CODE_B.get(code, code)


# 根据显示的语言和翻译通道，获取该翻译通道要求的源语言代码和目标语言代码
# translate_type 翻译通道索引
# show_source 显示的原语言名称或 - 或  语言代码
# show_target 显示的目标语言名称 或 - 或语言代码
# 如果是AI渠道则返回语言的自然语言名称
# - No 是兼容早期不规范写法
def get_source_target_code(*, show_source=None, show_target=None, translate_type=None) -> Tuple[str, str]:
    source_list = None
    target_list = None
    if show_source == '-':
        show_source = None
    if show_target == '-':
        show_target = None
    # 先从 LANG_CODE 中获取手动指定的
    if show_source:
        if show_source in LANG_CODE:  # 是语言代码，可能是 cli.py 传入
            source_list = LANG_CODE[show_source]
        elif LANGNAME_DICT_REV.get(show_source):  # 是语言显示名字
            source_list = LANG_CODE.get(LANGNAME_DICT_REV.get(show_source))
        elif show_source == 'zh':  # 特殊兼容zh
            source_list = LANG_CODE['zh-cn']

    if show_target:
        if show_target in LANG_CODE:  # 是语言代码 cli.py
            target_list = LANG_CODE[show_target]
        elif LANGNAME_DICT_REV.get(show_target):  # 语言名字
            target_list = LANG_CODE.get(LANGNAME_DICT_REV.get(show_target))
        elif show_target == 'zh':
            # 特殊兼容zh
            target_list = LANG_CODE['zh-cn']



    # AI渠道
    if translate_type in AI_TRANS_CHANNELS:
        return source_list[7] if source_list else show_source,target_list[7] if target_list else show_target

    # 非AI渠道，需返回语言的代码形式

    if show_source and not source_list:
        show_source = get_code(show_source)

    if show_target and not target_list:
        show_target = get_code(show_target)

    # 未设置渠道则使用 Google
    if not translate_type or translate_type in [GOOGLE_INDEX, TRANSAPI_INDEX, CAMB_INDEX]:
        return source_list[0] if source_list else show_source, target_list[0] if target_list else show_target

    if translate_type == BAIDU_INDEX:
        return source_list[2] if source_list else show_source, target_list[2] if target_list else show_target

    if translate_type in [DEEPLX_INDEX, DEEPL_INDEX]:
        return source_list[3] if source_list else show_source, target_list[3] if target_list else show_target

    if translate_type == TENCENT_INDEX:
        return source_list[4] if source_list else show_source, target_list[4] if target_list else show_target

    if translate_type in [LIBRE_INDEX]:
        return source_list[5] if source_list else show_source, target_list[5] if target_list else show_target
    if translate_type == MICROSOFT_INDEX:
        return source_list[6] if source_list else show_source, target_list[6] if target_list else show_target
    if translate_type == ALI_INDEX:
        return source_list[8] if source_list else show_source, target_list[8] if target_list else show_target

    # qwen-mt 翻译渠道语言代码
    if translate_type == QWENMT_INDEX:
        return source_list[9] if source_list else None, target_list[9] if target_list else None
    if translate_type == M2M100_INDEX:
        s,t=None,None
        if source_list:
            s=LANGUAGE_M2M100.get(source_list[0].split('-')[0])
        if target_list:
            t=LANGUAGE_M2M100.get(target_list[0].split('-')[0])
        return s ,t
    return show_source, show_target


# 获取频道 模型无关的语言代码, 对应 videotrans/configure/constants.py 中 LANG_CODE 键
# 用于原始、目标语言字幕文件名，以及 AI翻译渠道时用于换取 语言名称
def get_code(show_text: str = None):
    if not show_text or show_text in ['-','No']: return None
    if show_text == 'zh': return 'zh-cn'
    # 是语言代码本身，例如 zh-cn,en
    if show_text in LANG_CODE: return show_text
    # 是语言显示名称，例如 简体中文，English
    if show_text in LANGNAME_DICT_REV: return LANGNAME_DICT_REV.get(show_text)
    if show_text == tr('auto') or show_text.lower() == 'auto': return 'auto'

    # 否则，可能是 语言名称，则从翻译字典中获取
    return tr(show_text)
