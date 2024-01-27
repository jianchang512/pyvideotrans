# -*- coding: utf-8 -*-
import re
from videotrans.configure import config

GOOGLE_NAME="Google"
BAIDU_NAME="Baidu"
DEEPL_NAME="DeepL"
DEEPLX_NAME="DeepLx"
TENCENT_NAME="Tencent"
CHATGPT_NAME="chatGPT"
AZUREGPT_NAME="AzureGPT"
GEMINI_NAME="Gemini"
SRT_NAME="srt"
# 翻译通道
TRANSNAMES = [
    GOOGLE_NAME,
    BAIDU_NAME,
    DEEPL_NAME,
    CHATGPT_NAME,
    AZUREGPT_NAME,
    GEMINI_NAME,
    TENCENT_NAME,
    DEEPLX_NAME
]
#
LANG_CODE = {
        "zh-cn": [
            "zh-cn",# google通道
            "chi",#字幕嵌入语言
            "zh",#百度通道
            "ZH",#deepl deeplx通道
            "zh" #腾讯通道
        ],
        "zh-tw": [
            "zh-tw",
            "chi",
            "cht",
            "ZH",
            "zh-TW"
        ],
        "en": [
            "en",
            "eng",
            "en",
            "EN-US",
            "en"
        ],
        "fr": [
            "fr",
            "fre",
            "fra",
            "FR",
            "fr"
        ],
        "de": [
            "de",
            "ger",
            "de",
            "DE",
            "de"
        ],
        "ja": [
            "ja",
            "jpn",
            "jp",
            "JA",
            "ja"
        ],
        "ko": [
            "ko",
            "kor",
            "kor",
            "KO",
            "ko"
        ],
        "ru": [
            "ru",
            "rus",
            "ru",
            "RU",
            "ru"
        ],
        "es": [
            "es",
            "spa",
            "spa",
            "ES",
            "es"
        ],
        "th": [
            "th",
            "tha",
            "th",
            "No",
            "th"
        ],
        "it": [
            "it",
            "ita",
            "it",
            "IT",
            "it"
        ],
        "pt": [
            "pt",
            "por",
            "pt",
            "PT",
            "pt"
        ],
        "vi": [
            "vi",
            "vie",
            "vie",
            "No",
            "vi"
        ],
        "ar": [
            "ar",
            "are",
            "ara",
            "No",
            "ar"
        ],
        "tr": [
            "tr",
            "tur",
            "tr",
            "tr",
            "tr"
        ],
        "hi": [
            "hi",
            "hin",
            "hi",
            "No",
            "hi"
        ]
}

# 根据界面显示的语言名称，比如“简体中文、English” 获取语言代码，比如 zh-cn en 等
def get_code(*,show_text=None):
    return config.rev_langlist[show_text]

# 根据显示的语言和翻译通道，获取源语言代码和目标语言代码
# translate_type翻译通道
# show_source翻译后显示的原语言名称
# show_target 翻译后显示的目标语言名称
def get_source_target_code(*,show_source=None,show_target=None,translate_type=None):
    source_list=None
    target_list=None
    if not translate_type:
        return None,None
    lower_translate_type=translate_type.lower()

    if show_source:
        source_list=LANG_CODE[config.rev_langlist[show_source]]
    if show_target:
        target_list=LANG_CODE[config.rev_langlist[show_target]]
    if lower_translate_type==GOOGLE_NAME.lower():
        return (source_list[0] if source_list else "-", target_list[0] if target_list else "-")
    if lower_translate_type==BAIDU_NAME.lower():
        return (source_list[2] if source_list else "-", target_list[2] if target_list else "-")
    if lower_translate_type in [DEEPLX_NAME.lower(),DEEPLX_NAME.lower()]:
        return (source_list[3] if source_list else "-", target_list[3] if target_list else "-")
    if lower_translate_type==TENCENT_NAME.lower():
        return (source_list[4] if source_list else "-", target_list[4] if target_list else "-")
    if lower_translate_type in [CHATGPT_NAME.lower(),AZUREGPT_NAME.lower(),GEMINI_NAME.lower()]:
        return (show_source, show_target)
    raise Exception(f"[error]{translate_type=},{show_source=},{show_target=}")

# 判断当前翻译通道和目标语言是否允许翻译
# 比如deepl不允许翻译到某些目标语言，某些通道是否填写api key 等
# translate_type翻译通道
# show_target 翻译后显示的目标语言名称
# only_key=True 仅检测 key 和api，不判断目标语言
def is_allow_translate(*,translate_type=None,show_target=None,only_key=False):
    lower_translate_type=translate_type.lower()
    if lower_translate_type==CHATGPT_NAME and not config.params['chatgpt_key']:
        return config.transobj['chatgptkeymust']
    if lower_translate_type==GEMINI_NAME and not config.params['gemini_key']:
        return config.transobj['chatgptkeymust']
    if lower_translate_type==AZUREGPT_NAME.lower() and (not config.params['azure_key'] or not config.params['azure_api']):
        return 'No Azure key'

    if lower_translate_type==BAIDU_NAME.lower() and (not config.params["baidu_appid"] or not config.params["baidu_miyue"]):
        return config.transobj['baikeymust']
    if lower_translate_type==TENCENT_NAME.lower() and (not config.params["tencent_SecretId"] or not config.params["tencent_SecretKey"]):
        return config.transobj['tencent_key']
    if lower_translate_type==DEEPL_NAME.lower() and  not config.params["deepl_authkey"]:
        return config.transobj['deepl_authkey']
    if lower_translate_type==DEEPLX_NAME.lower() and  not config.params["deeplx_address"]:
        return config.transobj['setdeeplx_address']

    if only_key:
        return True


    index=0
    if lower_translate_type==BAIDU_NAME.lower():
        index=2
    elif lower_translate_type in [DEEPLX_NAME.lower(),DEEPLX_NAME.lower()]:
        index=3
    elif lower_translate_type == TENCENT_NAME.lower():
        index=4

    if show_target:
        target_list=LANG_CODE[config.rev_langlist[show_target]]
        if target_list[index].lower()=='no':
            return config.transobj['deepl_nosupport']

    return True

# 获取用于进行语音识别的预设语言，比如语音是英文发音、中文发音
# 根据 原语言进行判断,基本等同于google，但只保留_之前的部分
def get_audio_code(*,show_source=None):
    source_list=LANG_CODE[config.rev_langlist[show_source]]
    return re.split(r'_|-',source_list[0])[0]

# 获取嵌入软字幕的3位字母语言代码，根据目标语言确定
def get_subtitle_code(*,show_target=None):
    target_list=LANG_CODE[config.rev_langlist[show_target]]
    return target_list[1]

# 翻译,先根据翻译通道和目标语言，取出目标语言代码
def run(*,translate_type=None,text_list=None,target_language_name=None,set_p=True):
    _,target_language=get_source_target_code(show_target=target_language_name,translate_type=translate_type)
    if translate_type==GOOGLE_NAME:
        from videotrans.translator.google import trans
    elif translate_type==BAIDU_NAME:
        from videotrans.translator.baidu import trans
    elif translate_type==DEEPL_NAME:
        from videotrans.translator.deepl import trans
    elif translate_type==DEEPLX_NAME:
        from videotrans.translator.deeplx import trans
    elif translate_type==TENCENT_NAME:
        from videotrans.translator.tencent import trans
    elif translate_type==CHATGPT_NAME:
        from videotrans.translator.chatgpt import trans
    elif translate_type==GEMINI_NAME:
        from videotrans.translator.gemini import trans
    elif translate_type==AZUREGPT_NAME:
        from videotrans.translator.azure import trans
    else:
        raise Exception(f"[error]{translate_type=},{target_language_name=}")
    return trans(text_list,target_language,set_p=set_p)
