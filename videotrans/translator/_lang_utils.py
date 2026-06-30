from videotrans.configure.config import tr, params, logger
from videotrans.util.help_misc import show_error
from videotrans import winform
from videotrans.translator._constants import (
    GOOGLE_INDEX, MICROSOFT_INDEX, M2M100_INDEX,
    QWENMT_INDEX,
    TENCENT_INDEX, BAIDU_INDEX, DEEPL_INDEX, DEEPLX_INDEX, ALI_INDEX,
    LIBRE_INDEX, TRANSAPI_INDEX, CAMB_INDEX,
    AI_TRANS_CHANNELS,
)
from videotrans.translator._lang_codes import LANGNAME_DICT_REV, LANG_CODE
from videotrans.translator._registry import _ID_NAME_DICT


def get_code(show_text=None):
    # - None 即不选择语言，则返回 None，调用处需根据返回结果判断
    # 未在 LANG CODE 中找到则原样返回
    if not show_text or show_text in ['-', 'No']:
        return None
    if show_text == 'zh':
        return 'zh-cn'
    if show_text in LANG_CODE:
        return show_text
    return LANGNAME_DICT_REV.get(show_text, show_text)


# 根据显示的语言和翻译通道，获取该翻译通道要求的源语言代码和目标语言代码
# translate_type 翻译通道索引
# show_source 显示的原语言名称或 - 或  语言代码
# show_target 显示的目标语言名称 或 - 或语言代码
# 如果是AI渠道则返回语言的自然语言名称
# 新增的语言代码直接返回
# - No 是兼容早期不规范写法
def get_source_target_code(*, show_source=None, show_target=None, translate_type=None):
    source_list = None
    target_list = None

    if show_source and show_source not in ['-', 'No']:
        if show_source in LANG_CODE:  # 是语言代码
            source_list = LANG_CODE[show_source]
        elif LANGNAME_DICT_REV.get(show_source):  # 是语言显示名字
            source_list = LANG_CODE.get(LANGNAME_DICT_REV.get(show_source))
        elif show_source == 'zh':  # 特殊兼容zh
            source_list = LANG_CODE['zh-cn']

    if show_target and show_target not in ['-', 'No']:
        if show_target in LANG_CODE:  # 是语言代码
            target_list = LANG_CODE[show_target]
        elif LANGNAME_DICT_REV.get(show_target):  # 语言名字
            target_list = LANG_CODE.get(LANGNAME_DICT_REV.get(show_target))
        elif show_target == 'zh':
            # 特殊兼容zh
            target_list = LANG_CODE['zh-cn']

    # 均未找到，可能是新增语言代码
    if not source_list and not target_list:
        return show_source, show_target  # 返回原始输入

    # 未设置渠道则使用 Google
    if not translate_type or translate_type in [GOOGLE_INDEX, TRANSAPI_INDEX, CAMB_INDEX]:
        return source_list[0] if source_list else show_source, target_list[0] if target_list else show_target

    # qwenmt翻译渠道语言代码
    if translate_type == QWENMT_INDEX:
        if params.get('qwenmt_model', 'qwen-mt-turbo').startswith('qwen-mt'):
            return 'auto', target_list[9] if target_list else show_target
        return source_list[7] if source_list else show_source, target_list[7] if target_list else show_target

    # AI渠道
    if translate_type in AI_TRANS_CHANNELS:
        return source_list[7] if source_list else show_source, target_list[7] if target_list else show_target

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
    if translate_type == M2M100_INDEX:
        return source_list[10] if source_list else show_source, target_list[10] if target_list else show_target
    return show_source, show_target


# 单独返回 qwen-mt qwen-tts qwen-asr 所需要的语言名称
def get_language_qwen(langcode=None):
    if not langcode:
        return None
    if langcode == 'zh':
        langcode = 'zh-cn'
    _lang_list = LANG_CODE.get(langcode)
    return langcode if not _lang_list else _lang_list[9]


# 判断当前翻译通道和目标语言是否允许翻译
# 比如deepl不允许翻译到某些目标语言，某些通道是否填写api key 等
# translate_type翻译通道
# show_target 翻译后显示的目标语言名称
# only_key=True 仅检测 key 和api，不判断目标语言
def is_allow_translate(*, translate_type=None, show_target=None, only_key=False, return_str=False):
    if not translate_type or translate_type in [GOOGLE_INDEX, MICROSOFT_INDEX]:
        return True

    _cls = _ID_NAME_DICT.get(translate_type)
    if not _cls:
        return True
    if _cls.key_name and not params.get(_cls.key_name):
        return "Please configure the SK or API information of the channel first." if return_str else winform.get_win(_cls.win).openwin()

    # 如果只需要判断是否填写了 api key 等信息，到此返回
    if only_key:
        return True

    if show_target:
        # 再判断是否为No，即不支持
        index = 0
        target_list = None
        if translate_type == BAIDU_INDEX:
            index = 2
        elif translate_type in [DEEPLX_INDEX, DEEPL_INDEX]:
            index = 3
        elif translate_type == TENCENT_INDEX:
            index = 4
        elif translate_type == MICROSOFT_INDEX:
            index = 6
        elif translate_type == ALI_INDEX:
            index = 8
        elif translate_type == M2M100_INDEX:
            index = 10

        if show_target in LANG_CODE:
            target_list = LANG_CODE[show_target]
        elif LANGNAME_DICT_REV.get(show_target):
            target_list = LANG_CODE.get(LANGNAME_DICT_REV.get(show_target))
        elif show_target == 'zh':
            # 特殊兼容zh
            target_list = LANG_CODE['zh-cn']

        if target_list and target_list[index] == 'No':

            return tr('deepl_nosupport') + f':{show_target}' if return_str else show_error(
                tr('deepl_nosupport') + f':{show_target}')
    return True


# 获取用于进行语音识别的预设语言，比如语音是英文发音、中文发音
# 根据 原语言进行判断,基本等同于google，但只保留_之前的部分
def get_audio_code(*, show_source=None):
    if not show_source or show_source in ['auto', '-']:
        return 'auto'
    source_list = LANG_CODE[show_source] if show_source in LANG_CODE else LANG_CODE.get(
        LANGNAME_DICT_REV.get(show_source))
    return source_list[0] if source_list else "auto"


# 获取嵌入MP4视频嵌入软字幕的3位字母语言代码 ISO 639-2/T ，根据目标语言确定
# mkv视频需根据此返回的代码再调用 get_mkv_code 获取 ISO 639-2/B
def get_subtitle_code(*, show_target=None):
    try:
        if show_target in LANG_CODE:
            return LANG_CODE[show_target][1]
        if show_target in LANGNAME_DICT_REV:
            return LANG_CODE[LANGNAME_DICT_REV[show_target]][1]
    except Exception as e:
        logger.error(f'获取字幕嵌入3为语言代码错误:{e}')
    return 'eng'

# 如果是 mkv 软字幕，根据mp4所需code换算为  B 标准代码 ISO 639-2/B
def get_mkv_code(code):
    #  ISO 639-2/T :ISO 639-2/B
    langcode={
        "fra":"fre",
        "deu":"ger",
        "zho":"chi",
        "ces":"cze",
        "ell":"gre",
        "fas":"per",
        "msa":"may",
        "nld":"dut",
        "ron":"rum",
    }
    return langcode.get(code,code)
