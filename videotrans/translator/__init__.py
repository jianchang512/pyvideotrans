# -*- coding: utf-8 -*-
from typing import Union, List



from videotrans.configure import config



# 数字代表显示顺序
GOOGLE_INDEX = 0
MICROSOFT_INDEX = 1
AI302_INDEX = 2
BAIDU_INDEX = 3
DEEPL_INDEX = 4
DEEPLX_INDEX = 5
OTT_INDEX = 6
TENCENT_INDEX = 7
CHATGPT_INDEX = 8
LOCALLLM_INDEX = 9
ZIJIE_INDEX = 10
AZUREGPT_INDEX = 11
GEMINI_INDEX = 12
TRANSAPI_INDEX = 13
FREEGOOGLE_INDEX = 14
# 翻译通道名字列表，显示在界面
TRANSLASTE_NAME_LIST = [
    "Google翻译" if config.defaulelang == 'zh' else 'Google',
    "微软翻译" if config.defaulelang == 'zh' else 'Microsoft',
    "302.AI",
    "百度翻译" if config.defaulelang == 'zh' else 'Baidu',
    "DeepL",
    "DeepLx",
    "离线翻译OTT" if config.defaulelang == 'zh' else 'OTT',
    "腾讯翻译" if config.defaulelang == 'zh' else 'Tencent',
    "OpenAI ChatGPT" if config.defaulelang == 'zh' else 'OpenAI ChatGPT',
    "本地大模型及兼容AI" if config.defaulelang == 'zh' else 'Local LLM',
    "字节火山大模型" if config.defaulelang == 'zh' else 'VolcEngine LLM',
    "AzureAI GPT",
    "Gemini",
    "自定义翻译API" if config.defaulelang == 'zh' else 'Customized API',
    "FreeGoogle翻译" if config.defaulelang == 'zh' else 'Free Google'
]
# subtitles language code https://zh.wikipedia.org/wiki/ISO_639-2  https://www.loc.gov/standards/iso639-2/php/code_list.php
# 腾讯翻译 https://cloud.tencent.com/document/api/551/15619
# google翻译 https://translate.google.com/
# 百度翻译 https://fanyi.baidu.com/
# deepl  https://deepl.com/
# microsoft https://api-edge.cognitive.microsofttranslator.com/translate?from=&to
LANG_CODE = {
    "zh-cn": [
        "zh-cn",  # google通道
        "chi",  # 字幕嵌入语言
        "zh",  # 百度通道
        "ZH-HANS",  # deepl deeplx通道
        "zh",  # 腾讯通道
        "zh",  # OTT通道
        "zh-Hans",  # 微软翻译
        "Simplified Chinese" if config.defaulelang != 'zh' else '简体中文'  # AI翻译
    ],
    "zh-tw": [
        "zh-tw",
        "chi",
        "cht",
        "ZH-HANT",
        "zh-TW",
        "zt",
        "zh-Hant",
        "Traditional Chinese" if config.defaulelang != 'zh' else '繁体中文'
    ],
    "en": [
        "en",
        "eng",
        "en",
        "EN-US",
        "en",
        "en",
        "en",
        "English language" if config.defaulelang != 'zh' else '英语'
    ],
    "fr": [
        "fr",
        "fre",
        "fra",
        "FR",
        "fr",
        "fr",
        "fr",
        "French language" if config.defaulelang != 'zh' else '法语'
    ],
    "de": [
        "de",
        "ger",
        "de",
        "DE",
        "de",
        "de",
        "de",
        "German language" if config.defaulelang != 'zh' else '德语'
    ],
    "ja": [
        "ja",
        "jpn",
        "jp",
        "JA",
        "ja",
        "ja",
        "ja",
        "Japanese language" if config.defaulelang != 'zh' else '日语'
    ],
    "ko": [
        "ko",
        "kor",
        "kor",
        "KO",
        "ko",
        "ko",
        "ko",
        "Korean language" if config.defaulelang != 'zh' else '韩语'
    ],
    "ru": [
        "ru",
        "rus",
        "ru",
        "RU",
        "ru",
        "ru",
        "ru",
        "Russian language" if config.defaulelang != 'zh' else '俄罗斯语'
    ],
    "es": [
        "es",
        "spa",
        "spa",
        "ES",
        "es",
        "es",
        "es",
        "Spanish language" if config.defaulelang != 'zh' else '西班牙语'
    ],
    "th": [
        "th",
        "tha",
        "th",
        "No",
        "th",
        "th",
        "th",
        "Thai language" if config.defaulelang != 'zh' else '泰国语'
    ],
    "it": [
        "it",
        "ita",
        "it",
        "IT",
        "it",
        "it",
        "it",
        "Italian language" if config.defaulelang != 'zh' else '意大利语'
    ],
    "pt": [
        "pt",  # pt-PT
        "por",
        "pt",
        "PT-PT",
        "pt",
        "pt",
        "pt",
        "Portuguese language" if config.defaulelang != 'zh' else '葡萄牙语'
    ],
    "vi": [
        "vi",
        "vie",
        "vie",
        "No",
        "vi",
        "No",
        "vi",
        "Vietnamese language" if config.defaulelang != 'zh' else '越南语'
    ],
    "ar": [
        "ar",
        "are",
        "ara",
        "AR",
        "ar",
        "ar",
        "ar",
        "Arabic language" if config.defaulelang != 'zh' else '阿拉伯语'
    ],
    "tr": [
        "tr",
        "tur",
        "tr",
        "TR",
        "tr",
        "tr",
        "tr",
        "Turkish language" if config.defaulelang != 'zh' else '土耳其语'
    ],
    "hi": [
        "hi",
        "hin",
        "hi",
        "No",
        "hi",
        "hi",
        "hi",
        "Hindi language" if config.defaulelang != 'zh' else '印度语'
    ],
    "hu": [
        "hu",
        "hun",
        "hu",
        "HU",
        "No",
        "No",
        "hu",
        "Hungarian language" if config.defaulelang != 'zh' else '匈牙利语'
    ],
    "uk": [
        "uk",
        "ukr",
        "ukr",  # 百度
        "UK",  # deepl
        "No",  # 腾讯
        "No",  # ott
        "uk",  # 微软
        "Ukrainian language" if config.defaulelang != 'zh' else '乌克兰语'
    ],
    "id": [
        "id",
        "ind",
        "id",
        "ID",
        "id",
        "No",
        "id",
        "Indonesian language" if config.defaulelang != 'zh' else '印度尼西亚语'
    ],
    "ms": [
        "ms",
        "may",
        "may",
        "No",
        "ms",
        "No",
        "ms",
        "Malay language" if config.defaulelang != 'zh' else '马来西亚语'
    ],
    "kk": [
        "kk",
        "kaz",
        "No",
        "No",
        "No",
        "No",
        "kk",
        "Kazakh language" if config.defaulelang != 'zh' else '哈萨克语'
    ],
    "cs": [
        "cs",
        "ces",
        "cs",
        "CS",
        "No",
        "No",
        "cs",
        "Czech language" if config.defaulelang != 'zh' else '捷克语'
    ],
    "pl": [
        "pl",
        "pol",
        "pl",
        "PL",
        "No",
        "No",
        "pl",
        "Polish language" if config.defaulelang != 'zh' else '波兰语'
    ],
    "nl": [
        "nl",  # google通道
        "dut",  # 字幕嵌入语言
        "nl",  # 百度通道
        "NL",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "nl",  # 微软翻译
        "Dutch" if config.defaulelang != 'zh' else '荷兰语'  # AI翻译
    ],
    "sv": [
        "sv",  # google通道
        "swe",  # 字幕嵌入语言
        "swe",  # 百度通道
        "SV",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "sv",  # 微软翻译
        "Swedish" if config.defaulelang != 'zh' else '瑞典语'  # AI翻译
    ],
    "auto":[
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
    ]
}


# 根据界面显示的语言名称，比如“简体中文、English” 获取语言代码，比如 zh-cn en 等, 如果是cli，则直接是语言代码
def get_code(*, show_text=None):
    if not show_text or show_text in ['-']:
        return None

    if show_text in LANG_CODE:
        return show_text
    if show_text in config.rev_langlist:
        return config.rev_langlist[show_text]

    return None


# 根据显示的语言和翻译通道，获取该翻译通道要求的源语言代码和目标语言代码
# translate_type翻译通道索引
# show_source翻译后显示的原语言名称或 -
# show_target 翻译后显示的目标语言名称 或 -
# 如果是cli，则show均是语言代码
def get_source_target_code(*, show_source=None, show_target=None, translate_type=None):
    source_list = None
    target_list = None

    # 新增的自定义语言翻译代码，该代码既不在 LANG_CODE 也不在 config.rev_langlist，原羌返回即可
    customize_source_code = show_source if show_source and show_source not in LANG_CODE and show_source not in config.rev_langlist else None
    customize_target_code = show_target if show_target and show_target not in LANG_CODE and show_target not in config.rev_langlist else None
    if customize_source_code or customize_target_code:
        return customize_source_code, customize_target_code

    if show_source and show_source != '-':
        source_list = LANG_CODE[show_source] if show_source in LANG_CODE else LANG_CODE[
            config.rev_langlist[show_source]]
    if show_target and show_target != '-':
        target_list = LANG_CODE[show_target] if show_target in LANG_CODE else LANG_CODE[
            config.rev_langlist[show_target]]
    if translate_type in [GOOGLE_INDEX, TRANSAPI_INDEX, FREEGOOGLE_INDEX]:
        return (source_list[0] if source_list else "-", target_list[0] if target_list else "-")
    elif translate_type == BAIDU_INDEX:
        return (source_list[2] if source_list else "-", target_list[2] if target_list else "-")
    elif translate_type in [DEEPLX_INDEX, DEEPL_INDEX]:
        return (source_list[3] if source_list else "-", target_list[3] if target_list else "-")
    elif translate_type == TENCENT_INDEX:
        return (source_list[4] if source_list else "-", target_list[4] if target_list else "-")
    elif translate_type in [CHATGPT_INDEX, AZUREGPT_INDEX, GEMINI_INDEX,
                            LOCALLLM_INDEX, ZIJIE_INDEX, AI302_INDEX]:
        return (source_list[7] if source_list else "-", target_list[7] if target_list else "-")
    elif translate_type == OTT_INDEX:
        return (source_list[5] if source_list else "-", target_list[5] if target_list else "-")
    elif translate_type == MICROSOFT_INDEX:
        return (source_list[6] if source_list else "-", target_list[6] if target_list else "-")
    else:
        raise Exception(f"[error]get_source_target_code:{translate_type=},{show_source=},{show_target=}")


# 判断当前翻译通道和目标语言是否允许翻译
# 比如deepl不允许翻译到某些目标语言，某些通道是否填写api key 等
# translate_type翻译通道
# show_target 翻译后显示的目标语言名称
# only_key=True 仅检测 key 和api，不判断目标语言
def is_allow_translate(*, translate_type=None, show_target=None, only_key=False, win=None,return_str=False):
    if translate_type in [GOOGLE_INDEX, FREEGOOGLE_INDEX,MICROSOFT_INDEX]:
        return True

    if translate_type == CHATGPT_INDEX and not config.params['chatgpt_key']:
        if return_str:
            return "Please configure the api and key information of the OpenAI ChatGPT channel first."
        from videotrans.winform import chatgpt
        chatgpt.openwin()
        return False
    if translate_type == AI302_INDEX and not config.params['ai302_key']:
        if return_str:
            return "Please configure the api and key information of the 302.AI channel first."
        from videotrans.winform import ai302
        ai302.openwin()
        return False
    if translate_type == TRANSAPI_INDEX and not config.params['trans_api_url']:
        if return_str:
            return "Please configure the api and key information of the Trans_API channel first."
        from videotrans.winform import  transapi
        transapi.openwin()
        return False

    if translate_type == LOCALLLM_INDEX and not config.params['localllm_api']:
        if return_str:
            return "Please configure the api and key information of the LocalLLM channel first."
        from videotrans.winform import  localllm
        localllm.openwin()
        return False
    if translate_type == ZIJIE_INDEX and (
            not config.params['zijiehuoshan_model'].strip() or not config.params['zijiehuoshan_key'].strip()):
        if return_str:
            return "Please configure the api and key information of the ZiJie channel first."
        from videotrans.winform import zijiehuoshan
        zijiehuoshan.openwin()
        return False

    if translate_type == GEMINI_INDEX and not config.params['gemini_key']:
        if return_str:
            return "Please configure the api and key information of the Gemini channel first."
        from videotrans.winform import gemini
        gemini.openwin()
        return False
    if translate_type == AZUREGPT_INDEX and (
            not config.params['azure_key'] or not config.params['azure_api']):
        if return_str:
            return "Please configure the api and key information of the Azure GPT channel first."
        from videotrans.winform import azure
        azure.openwin()
        return False

    if translate_type == BAIDU_INDEX and (
            not config.params["baidu_appid"] or not config.params["baidu_miyue"]):
        if return_str:
            return "Please configure the api and key information of the Baidu channel first."
        from videotrans.winform import baidu
        baidu.openwin()
        return False
    if translate_type == TENCENT_INDEX and (
            not config.params["tencent_SecretId"] or not config.params["tencent_SecretKey"]):
        if return_str:
            return "Please configure the api and key information of the Tencent channel first."
        from videotrans.winform import tencent
        tencent.openwin()
        return False
    if translate_type == DEEPL_INDEX and not config.params["deepl_authkey"]:
        if return_str:
            return "Please configure the api and key information of the DeepL channel first."
        from videotrans.winform import deepL
        deepL.openwin()
        return False
    if translate_type == DEEPLX_INDEX and not config.params["deeplx_address"]:
        if return_str:
            return "Please configure the api and key information of the DeepLx channel first."
        from videotrans.winform import deepLX
        deepLX.openwin()
        return False

    if translate_type == TRANSAPI_INDEX and not config.params["trans_api_url"]:
        if return_str:
            return "Please configure the api and key information of the TransAPI channel first."
        from videotrans.winform import transapi
        transapi.openwin()
        return False
    if translate_type == OTT_INDEX and not config.params["ott_address"]:
        if return_str:
            return "Please configure the api and key information of the OTT channel first."
        from videotrans.winform import  ott
        ott.openwin()
        return False
    # 如果只需要判断是否填写了 api key 等信息，到此返回
    if only_key:
        return True
    # 再判断是否为No，即不支持
    index = 0
    if translate_type == BAIDU_INDEX:
        index = 2
    elif translate_type in [DEEPLX_INDEX, DEEPL_INDEX]:
        index = 3
    elif translate_type == TENCENT_INDEX:
        index = 4
    elif translate_type == MICROSOFT_INDEX:
        index = 6

    if show_target:
        # 新增自定义语言代码
        if show_target not in LANG_CODE and show_target not in config.rev_langlist:
            return True
        target_list = LANG_CODE[show_target] if show_target in LANG_CODE else LANG_CODE[
            config.rev_langlist[show_target]]
        if target_list[index].lower() == 'no':
            if return_str:
                return config.transobj['deepl_nosupport'] + f':{show_target}'
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(win, config.transobj['anerror'],
                                 config.transobj['deepl_nosupport'] + f':{show_target}')
            return False
    return True


# 获取用于进行语音识别的预设语言，比如语音是英文发音、中文发音
# 根据 原语言进行判断,基本等同于google，但只保留_之前的部分
def get_audio_code(*, show_source=None):
    source_list = LANG_CODE[show_source] if show_source in LANG_CODE else LANG_CODE[config.rev_langlist[show_source]]
    return source_list[0]


# 获取嵌入软字幕的3位字母语言代码，根据目标语言确定
def get_subtitle_code(*, show_target=None):
    if show_target in LANG_CODE:
        return LANG_CODE[show_target][1]
    if show_target in config.rev_langlist:
        return LANG_CODE[config.rev_langlist[show_target]][1]
    return 'eng'


# 翻译,先根据翻译通道和目标语言，取出目标语言代码
def run(*, translate_type=None,
        text_list=None,
        target_language_name=None,
        inst=None,
        is_test=False,
        source_code=None,
        uuid=None) -> Union[List, str, None]:
    translate_type=int(translate_type)
    _, target_language = get_source_target_code(show_target=target_language_name, translate_type=translate_type)
    kwargs = {
        "text_list": text_list,
        "target_language": target_language,
        "inst": inst,
        "source_code": source_code,
        "uuid": uuid,
        "is_test": is_test,
    }

    if translate_type == GOOGLE_INDEX:
        from videotrans.translator._google import Google
        return Google(**kwargs).run()
    if translate_type == FREEGOOGLE_INDEX:
        from videotrans.translator._freegoogle import FreeGoogle
        return FreeGoogle(**kwargs).run()

    if translate_type == MICROSOFT_INDEX:
        from videotrans.translator._microsoft import Microsoft
        return Microsoft(**kwargs).run()

    if translate_type == TENCENT_INDEX:
        from videotrans.translator._tencent import Tencent
        return Tencent(**kwargs).run()

    if translate_type == BAIDU_INDEX:
        from videotrans.translator._baidu import Baidu
        return Baidu(**kwargs).run()

    if translate_type == OTT_INDEX:
        from videotrans.translator._ott import OTT
        return OTT(**kwargs).run()

    if translate_type == TRANSAPI_INDEX:
        from videotrans.translator._transapi import TransAPI
        return TransAPI(**kwargs).run()

    if translate_type == DEEPL_INDEX:
        from videotrans.translator._deepl import DeepL
        return DeepL(**kwargs).run()

    if translate_type == DEEPLX_INDEX:
        from videotrans.translator._deeplx import DeepLX
        return DeepLX(**kwargs).run()

    if translate_type == AI302_INDEX:
        from videotrans.translator._ai302 import AI302
        return AI302(**kwargs).run()

    if translate_type == LOCALLLM_INDEX:
        from videotrans.translator._localllm import LocalLLM
        return LocalLLM(**kwargs).run()

    if translate_type == ZIJIE_INDEX:
        from videotrans.translator._huoshan import HuoShan
        return HuoShan(**kwargs).run()

    if translate_type == CHATGPT_INDEX:
        from videotrans.translator._chatgpt import ChatGPT
        return ChatGPT(**kwargs).run()

    if translate_type == AZUREGPT_INDEX:
        from videotrans.translator._azure import AzureGPT
        return AzureGPT(**kwargs).run()

    if translate_type == GEMINI_INDEX:
        from videotrans.translator._gemini import Gemini
        return Gemini(**kwargs).run()

    raise Exception('No translation channel')
