# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Union, List

from videotrans.configure import config
# 数字代表显示顺序
from videotrans.configure.config import tr,settings,params,app_cfg,logger,ROOT_DIR
from videotrans.util import tools
from videotrans.translator._google import Google
from videotrans.translator._microsoft import Microsoft
from videotrans.translator._deepl import DeepL
from videotrans.translator._ai302 import AI302
from videotrans.translator._deeplx import DeepLX
from videotrans.translator._localllm import LocalLLM
from videotrans.translator._huoshan import HuoShan
from videotrans.translator._chatgpt import ChatGPT
from videotrans.translator._openrouter import OpenRouter
from videotrans.translator._zhipuai import ZhipuAI
from videotrans.translator._deepseek import DeepSeek
from videotrans.translator._ali import Ali
from videotrans.translator._siliconflow import SILICONFLOW
from videotrans.translator._azure import AzureGPT
from videotrans.translator._gemini import Gemini
from videotrans.translator._libre import Libre
from videotrans.translator._mymemory import MyMemory
from videotrans.translator._tencent import Tencent
from videotrans.translator._qwenmt import QwenMT
from videotrans.translator._microsoft import Microsoft
from videotrans.translator._baidu import Baidu
from videotrans.translator._ott import OTT
from videotrans.translator._transapi import TransAPI


GOOGLE_INDEX = 0
MICROSOFT_INDEX = 1
M2M100_INDEX=2


CHATGPT_INDEX = 3
DEEPSEEK_INDEX = 4
GEMINI_INDEX = 5
ZHIPUAI_INDEX = 6
AZUREGPT_INDEX = 7
LOCALLLM_INDEX = 8


OPENROUTER_INDEX = 9
SILICONFLOW_INDEX = 10
AI302_INDEX = 11

QWENMT_INDEX = 12
ZIJIE_INDEX = 13


TENCENT_INDEX = 14
BAIDU_INDEX = 15
DEEPL_INDEX = 16
DEEPLX_INDEX = 17
ALI_INDEX = 18

OTT_INDEX = 19
LIBRE_INDEX = 20

MyMemoryAPI_INDEX = 21
TRANSAPI_INDEX = 22



# AI翻译渠道，方便判断
AI_TRANS_CHANNELS=[
    CHATGPT_INDEX,
    LOCALLLM_INDEX,
    ZIJIE_INDEX,
    AZUREGPT_INDEX,
    GEMINI_INDEX,
    QWENMT_INDEX,
    AI302_INDEX,
    ZHIPUAI_INDEX,
    SILICONFLOW_INDEX,
    DEEPSEEK_INDEX,
    OPENROUTER_INDEX
]
# 翻译通道名字列表，显示在界面
_ID_NAME_DICT = {
    GOOGLE_INDEX:tr('Google'),
    MICROSOFT_INDEX:tr('Microsoft'),
    M2M100_INDEX:f'M2M100({tr("Local")})',
    
    
    CHATGPT_INDEX:tr('OpenAI ChatGPT'),
    DEEPSEEK_INDEX:"DeepSeek",
    GEMINI_INDEX:"Gemini AI",
    ZHIPUAI_INDEX:tr('Zhipu AI'),
    AZUREGPT_INDEX:"AzureGPT AI",
    LOCALLLM_INDEX:tr('Local LLM'),
    
    OPENROUTER_INDEX:"OpenRouter",
    SILICONFLOW_INDEX:tr('SiliconFlow'),
    AI302_INDEX:"302.AI",
    
    QWENMT_INDEX:tr('Ali-Bailian'),
    ZIJIE_INDEX:tr('VolcEngine LLM'),

    TENCENT_INDEX:tr('Tencent'),
    BAIDU_INDEX:tr('Baidu'),
    DEEPL_INDEX:"DeepL",
    DEEPLX_INDEX:"DeepLx",
    ALI_INDEX:tr('Alibaba Machine Translation'),

    OTT_INDEX:tr('OTT'),
    LIBRE_INDEX:tr('LibreTranslate'),
    MyMemoryAPI_INDEX:tr('MyMemoryAPI'),
    TRANSAPI_INDEX:tr('Customized API'),
}
TRANSLASTE_NAME_LIST=list(_ID_NAME_DICT.values())

# subtitles language code https://zh.wikipedia.org/wiki/ISO_639-2%E4%BB%A3%E7%A0%81%E5%88%97%E8%A1%A8
#  https://www.loc.gov/standards/iso639-2/php/code_list.php
# 腾讯翻译 https://cloud.tencent.com/document/api/551/15619
# google翻译 https://translate.google.com/
# 百度翻译 https://fanyi.baidu.com/
# deepl  https://deepl.com/
# microsoft https://www.bing.com/translator?mkt=zh-CN
# 阿里 https://help.aliyun.com/zh/machine-translation/developer-reference/machine-translation-language-code-list?spm=a2c4g.11186623.help-menu-30396.d_4_4.4bda2b009oye8y
LANGNAME_DICT = {
    "en": tr("English"),
    "zh-cn": tr("Simplified Chinese"),
    "zh-tw": tr("Traditional Chinese"),
    "fr": tr("French"),
    "de": tr("German"),
    "ja": tr("Japanese"),
    "ko": tr("Korean"),
    "ru": tr("Russian"),
    "es": tr("Spanish"),
    "th": tr("Thai"),
    "it": tr("Italian"),
    "pt": tr("Portuguese"),
    "vi": tr("Vietnamese"),
    "ar": tr("Arabic"),
    "tr": tr("Turkish"),
    "hi": tr("Hindi"),
    "hu": tr("Hungarian"),
    "uk": tr("Ukrainian"),
    "id": tr("Indonesian"),
    "ms": tr("Malay"),
    "kk": tr("Kazakh"),
    "cs": tr("Czech"),
    "pl": tr("Polish"),
    "nl": tr("Dutch"),
    "sv": tr("Swedish"),
    "he": tr("Hebrew"),
    "bn": tr("Bengali"),
    "fa": tr("Persian"),
    "fil": tr("Filipino"),
    "ur": tr("Urdu"),
    "yue": tr("Cantonese")
}

# 如果存在新增
try:
    if Path(ROOT_DIR+f'/videotrans/newlang.txt').exists():
        _new_lang=Path(ROOT_DIR+f'/videotrans/newlang.txt').read_text().strip().split("\n")
        for nl in _new_lang:
            LANGNAME_DICT[nl]=nl
except Exception as e:
    logger.exception(f'读取自定义新增语言代码 newlang.txt 时出错 {e}', exc_info=True)
# 反向按照显示名字查找语言代码
LANGNAME_DICT_REV={v:k for k,v in LANGNAME_DICT.items()}
# 根据语言代码查找各个翻译渠道对应的 代码list
LANG_CODE = {
    "zh-cn": [
        "zh-cn",  # google通道
        "chi",  # 字幕嵌入语言
        "zh",  # 百度通道
        "ZH-HANS",  # deepl deeplx通道
        "zh",  # 腾讯通道
        "zh",  # OTT通道
        "zh-Hans",  # 微软翻译
        "Simplified Chinese",  # AI翻译
        "zh",  # 阿里
        "Chinese", # qwen-mt qwen-tts qwen-asr
        "zh" # m2m100
    ],
    "ur": [
        "ur",  # google通道
        "urd",  # 字幕嵌入语言
        "ur",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "ur",  # 微软翻译
        "Urdu",  # AI翻译
        "ur",  # 阿里
        "Urdu",
        "ur" # m2m100
    ],
    "yue": [
        "yue",  # google通道
        "chi",  # 字幕嵌入语言
        "yue",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "yue",  # 微软翻译
        "Cantonese",  # AI翻译
        "yue",  # 阿里
        "Cantonese",
        "zh" # m2m100
    ],

    "fil": [
        "tl",  # google通道
        "fil",  # 字幕嵌入语言
        "fil",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "fil",  # 微软翻译
        "Filipino",  # AI翻译
        "fil",  # 阿里
        "Filipino",
        "No"
    ],
    

    "zh-tw": [
        "zh-tw",
        "chi",
        "cht",
        "ZH-HANT",
        "zh-TW",
        "zt",
        "zh-Hant",
        "Traditional Chinese",
        "zh-tw",
        "Traditional Chinese",
        "zh" # m2m100
    ],
    "en": [
        "en",
        "eng",
        "en",
        "EN-US",
        "en",
        "en",
        "en",
        "English",
        "en",
        "English",
        "en" # m2m100
    ],
    "fr": [
        "fr",
        "fre",
        "fra",
        "FR",
        "fr",
        "fr",
        "fr",
        "French",
        "fr",
        "French",
        "fr" # m2m100
    ],
    "de": [
        "de",
        "ger",
        "de",
        "DE",
        "de",
        "de",
        "de",
        "German",
        "de",
        "German",
        "de" # m2m100
    ],
    "ja": [
        "ja",
        "jpn",
        "jp",
        "JA",
        "ja",
        "ja",
        "ja",
        "Japanese",
        "ja",
        "Japanese",
        "ja" # m2m100
    ],
    "ko": [
        "ko",
        "kor",
        "kor",
        "KO",
        "ko",
        "ko",
        "ko",
        "Korean",
        "ko",
        "Korean",
        "ko" # m2m100
    ],
    "ru": [
        "ru",
        "rus",
        "ru",
        "RU",
        "ru",
        "ru",
        "ru",
        "Russian",
        "ru",
        "Russian",
        "ru" # m2m100
    ],
    "es": [
        "es",
        "spa",
        "spa",
        "ES",
        "es",
        "es",
        "es",
        "Spanish",
        "es",
        "Spanish",
        "es" # m2m100
    ],
    "th": [
        "th",
        "tha",
        "th",
        "No",
        "th",
        "th",
        "th",
        "Thai",
        "th",
        "Thai",
        "th" # m2m100
    ],
    "it": [
        "it",
        "ita",
        "it",
        "IT",
        "it",
        "it",
        "it",
        "Italian",
        "it",
        "Italian",
        "it" # m2m100
    ],
    "pt": [
        "pt",  # pt-PT
        "por",
        "pt",
        "PT-PT",
        "PT-PT",
        "pt",
        "pt",
        "Portuguese",
        "pt",
        "Portuguese",
        "pt" # m2m100
    ],
    "vi": [
        "vi",
        "vie",
        "vie",
        "vi",
        "vi",
        "vi",
        "vi",
        "Vietnamese",
        "vi",
        "Vietnamese",
        "vi" # m2m100
    ],
    "ar": [
        "ar",
        "are",
        "ara",
        "AR",
        "ar",
        "ar",
        "ar",
        "Arabic",
        "ar",
        "Arabic",
        "ar" # m2m100
    ],
    "tr": [
        "tr",
        "tur",
        "tr",
        "TR",
        "tr",
        "tr",
        "tr",
        "Turkish",
        "tr",
        "Turkish",
        "tr" # m2m100
    ],
    "hi": [
        "hi",
        "hin",
        "hi",
        "No",
        "hi",
        "hi",
        "hi",
        "Hindi",
        "hi",
        "Hindi",
        "hi" # m2m100
    ],
    "hu": [
        "hu",
        "hun",
        "hu",
        "HU",
        "No",
        "hu",
        "hu",
        "Hungarian",
        "hu",
        "Hungarian",
        "hu" # m2m100
    ],
    "uk": [
        "uk",
        "ukr",
        "ukr",  # 百度
        "UK",  # deepl
        "No",  # 腾讯
        "uk",  # ott
        "uk",  # 微软
        "Ukrainian",
        "No",
        "Ukrainian",
        "uk" # m2m100
    ],
    "id": [
        "id",
        "ind",
        "id",
        "ID",
        "id",
        "id",
        "id",
        "Indonesian",
        "id",
        "Indonesian",
        "id" # m2m100
    ],
    "ms": [
        "ms",
        "may",
        "may",
        "No",
        "ms",
        "ms",
        "ms",
        "Malay",
        "ms",
        "Malay",
        "ms" # m2m100
    ],
    "kk": [
        "kk",
        "kaz",
        "No",
        "No",
        "No",
        "No",
        "kk",
        "Kazakh",
        "kk",
        "Kazakh",
        "kk" # m2m100
    ],
    "cs": [
        "cs",
        "ces",
        "cs",
        "CS",
        "No",
        "cs",
        "cs",
        "Czech",
        "cs",
        "Czech",
        "cs" # m2m100
    ],
    "pl": [
        "pl",
        "pol",
        "pl",
        "PL",
        "No",
        "pl",
        "pl",
        "Polish",
        "pl",
        "Polish",
        "pl" # m2m100
    ],
    "nl": [
        "nl",  # google通道
        "dut",  # 字幕嵌入语言
        "nl",  # 百度通道
        "NL",  # deepl deeplx通道
        "No",  # 腾讯通道
        "nl",  # OTT通道
        "nl",  # 微软翻译
        "Dutch",  # AI翻译
        "nl",
        "Dutch",
        "nl" # m2m100
    ],
    "sv": [
        "sv",  # google通道
        "swe",  # 字幕嵌入语言
        "swe",  # 百度通道
        "SV",  # deepl deeplx通道
        "No",  # 腾讯通道
        "sv",  # OTT通道
        "sv",  # 微软翻译
        "Swedish",  # AI翻译
        "sv",
        "Swedish",
        "sv" # m2m100
    ],
    "he": [
        "he",  # google通道
        "heb",  # 字幕嵌入语言
        "heb",  # 百度通道
        "HE",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "he",  # 微软翻译
        "Hebrew",  # AI翻译
        "he",
        "Hebrew",
        "he" # m2m100
    ],
    "bn": [
        "bn",  # google通道
        "ben",  # 字幕嵌入语言
        "ben",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "bn",  # 微软翻译
        "Bengali",  # AI翻译,
        "bn",
        "Bengali",
        "bn" # m2m100
    ],
    "fa": [
        "fa",  # google通道
        "per",  # 字幕嵌入语言
        "per",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "fa",  # 微软翻译
        "Persian",  # AI翻译
        "fa",  # 阿里
        "Western Persian",
        "fa" # m2m100
    ],
    "auto": [
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto",
        "auto"
    ]
}


# 根据界面显示的语言名称，比如“简体中文、English” 获取配置文件中的语言代码，比如 zh-cn en 等, 如果是 cli，则直接是语言代码
def get_code(show_text=None):
    # - None 即不选择语言，则返回 None，调用处需根据返回结果判断
    # 未在 LANG CODE 中找到则原样返回
    if not show_text or show_text in ['-','No']:
        return None
    if show_text=='zh':
        return 'zh-cn'
    if show_text in LANG_CODE:
        return show_text
    return LANGNAME_DICT_REV.get(show_text,show_text)


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

    if show_source and show_source not in ['-','No']:
        if show_source in LANG_CODE:# 是语言代码
            source_list = LANG_CODE[show_source] 
        elif LANGNAME_DICT_REV.get(show_source):#是语言显示名字
            source_list=LANG_CODE.get(LANGNAME_DICT_REV.get(show_source))
        elif show_source=='zh':#特殊兼容zh
            source_list=LANG_CODE['zh-cn']

    if show_target and show_target not in ['-','No']:
        if show_target in LANG_CODE:#是语言代码
            target_list = LANG_CODE[show_target] 
        elif LANGNAME_DICT_REV.get(show_target):#语言名字
            target_list=LANG_CODE.get(LANGNAME_DICT_REV.get(show_target))
        elif show_target=='zh':
            # 特殊兼容zh
            target_list=LANG_CODE['zh-cn']

    # 均未找到，可能是新增语言代码
    if not source_list and not target_list:
        return show_source,show_target#返回原始输入

    # 未设置渠道则使用 Google
    if not translate_type or translate_type in [GOOGLE_INDEX,MyMemoryAPI_INDEX, TRANSAPI_INDEX]:
        return source_list[0] if source_list else show_source, target_list[0] if target_list else show_target

    # qwenmt翻译渠道语言代码
    if translate_type == QWENMT_INDEX:
        if params.get('qwenmt_model', 'qwen-mt-turbo').startswith('qwen-mt'):
            return 'auto',target_list[9] if target_list else show_target
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

    if translate_type in [OTT_INDEX, LIBRE_INDEX]:
        return source_list[5] if source_list else show_source, target_list[5] if target_list else show_target
    if translate_type == MICROSOFT_INDEX:
        return source_list[6] if source_list else show_source, target_list[6] if target_list else show_target
    if translate_type == ALI_INDEX:
        return source_list[8] if source_list else show_source, target_list[8] if target_list else show_target
    if translate_type == M2M100_INDEX:
        return source_list[10] if source_list else show_source, target_list[10] if target_list else show_target
    return show_source,show_target

# 针对AI渠道目标语言，返回自然名称
def get_ai_language_name(show_target=None,translate_type=None):


    target_list=None
    if show_target in LANG_CODE:
        target_list=LANG_CODE[show_target][7]
    elif show_target in LANGNAME_DICT_REV:
        target_list=LANG_CODE[LANGNAME_DICT_REV.get(show_target)][7]
    else:
        return 'auto',show_target

    if not target_list:
        return None
    if translate_type is not None and translate_type==QWENMT_INDEX and params.get('qwenmt_model', 'qwen-mt-turbo').startswith('qwen-mt'):
        # qwen-mt特殊处理
        return 'auto',target_list[9] if target_list else show_target
    return target_list[7],target_list[7]

# 单独返回 qwen-mt qwen-tts qwen-asr 所需要的语言名称
def get_language_qwen(langcode=None):
    if not langcode:
        return None
    if langcode=='zh':
        langcode='zh-cn'
    _lang_list=LANG_CODE.get(langcode)
    if not _lang_list:
        return None
    return _lang_list[9]


# 判断当前翻译通道和目标语言是否允许翻译
# 比如deepl不允许翻译到某些目标语言，某些通道是否填写api key 等
# translate_type翻译通道
# show_target 翻译后显示的目标语言名称
# only_key=True 仅检测 key 和api，不判断目标语言
def is_allow_translate(*, translate_type=None, show_target=None, only_key=False,  return_str=False):
    if not translate_type:
        return True
    if translate_type in [GOOGLE_INDEX, MyMemoryAPI_INDEX, MICROSOFT_INDEX]:
        return True

    if translate_type == CHATGPT_INDEX and not params.get('chatgpt_key',''):
        if return_str:
            return "Please configure the api and key information of the OpenAI ChatGPT channel first."
        from videotrans.winform import chatgpt
        chatgpt.openwin()
        return False
    if translate_type == ZHIPUAI_INDEX and not params.get('zhipu_key',''):
        if return_str:
            return "请在菜单-智谱AI中填写智谱AI的api key"
        from videotrans.winform import zhipuai
        zhipuai.openwin()
        return False
    if translate_type == DEEPSEEK_INDEX and not params.get('deepseek_key',''):
        if return_str:
            return "请在菜单-DeepSeek中填写api key"
        from videotrans.winform import deepseek
        deepseek.openwin()
        return False
    if translate_type == OPENROUTER_INDEX and not params.get('openrouter_key',''):
        if return_str:
            return "请在菜单-OpenRouter中填写api key"
        from videotrans.winform import openrouter
        openrouter.openwin()
        return False

    if translate_type == SILICONFLOW_INDEX and not params.get('guiji_key',''):
        if return_str:
            return "请在菜单-硅基流动中填写硅基流动的api key"
        from videotrans.winform import siliconflow
        siliconflow.openwin()
        return False
    if translate_type == AI302_INDEX and not params.get('ai302_key',''):
        if return_str:
            return "Please configure the api and key information of the 302.AI channel first."
        from videotrans.winform import ai302
        ai302.openwin()
        return False

    if translate_type == TRANSAPI_INDEX and not params.get('trans_api_url',''):
        if return_str:
            return "Please configure the api and key information of the Trans_API channel first."
        from videotrans.winform import transapi
        transapi.openwin()
        return False

    if translate_type == LOCALLLM_INDEX and not params.get('localllm_api',''):
        if return_str:
            return "Please configure the api and key information of the LocalLLM channel first."
        from videotrans.winform import localllm
        localllm.openwin()
        return False
    if translate_type == ZIJIE_INDEX and (
            not params.get('zijiehuoshan_model','').strip() or not params.get('zijiehuoshan_key','').strip()):
        if return_str:
            return "Please configure the api and key information of the ZiJie channel first."
        from videotrans.winform import zijiehuoshan
        zijiehuoshan.openwin()
        return False

    if translate_type == GEMINI_INDEX and not params.get('gemini_key',''):
        if return_str:
            return "Please configure the api and key information of the Gemini channel first."
        from videotrans.winform import gemini
        gemini.openwin()
        return False
    if translate_type == QWENMT_INDEX and not params.get('qwenmt_key',''):
        if return_str:
            return "Please configure the api and key information of the QwenMT channel first."
        from videotrans.winform import qwenmt
        qwenmt.openwin()
        return False
    if translate_type == AZUREGPT_INDEX and (
            not params.get('azure_key','') or not params.get('azure_api','')):
        if return_str:
            return "Please configure the api and key information of the Azure GPT channel first."
        from videotrans.winform import azure
        azure.openwin()
        return False

    if translate_type == BAIDU_INDEX and (
            not params.get("baidu_appid",'') or not params.get("baidu_miyue",'')):
        if return_str:
            return "Please configure the api and key information of the Baidu channel first."
        from videotrans.winform import baidu
        baidu.openwin()
        return False
    if translate_type == TENCENT_INDEX and (
            not params.get("tencent_SecretId",'') or not params.get("tencent_SecretKey",'')):
        if return_str:
            return "Please configure the appid and key information of the Tencent channel first."
        from videotrans.winform import tencent
        tencent.openwin()
        return False
    if translate_type == ALI_INDEX and (
            not params.get("ali_id",'') or not params.get("ali_key",'')):
        if return_str:
            return "Please configure the appid and key information of the Alibaba translate channel first."
        from videotrans.winform import ali
        ali.openwin()
        return False
    if translate_type == DEEPL_INDEX and not params.get("deepl_authkey",''):
        if return_str:
            return "Please configure the api and key information of the DeepL channel first."
        from videotrans.winform import deepL
        deepL.openwin()
        return False
    if translate_type == DEEPLX_INDEX and not params.get("deeplx_address",''):
        if return_str:
            return "Please configure the api and key information of the DeepLx channel first."
        from videotrans.winform import deepLX
        deepLX.openwin()
        return False
    if translate_type == LIBRE_INDEX and not params.get("libre_address",''):
        if return_str:
            return "Please configure the api and key information of the LibreTranslate channel first."
        from videotrans.winform import libre
        libre.openwin()
        return False

    if translate_type == TRANSAPI_INDEX and not params.get("trans_api_url",''):
        if return_str:
            return "Please configure the api and key information of the TransAPI channel first."
        from videotrans.winform import transapi
        transapi.openwin()
        return False
    if translate_type == OTT_INDEX and not params.get("ott_address",''):
        if return_str:
            return "Please configure the api and key information of the OTT channel first."
        from videotrans.winform import ott
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
    elif translate_type == ALI_INDEX:
        index = 8
    elif translate_type == M2M100_INDEX:
        index = 10

    if show_target:
        target_list=None
        if show_target in LANG_CODE:
            target_list = LANG_CODE[show_target]
        elif LANGNAME_DICT_REV.get(show_target):
            target_list=LANG_CODE.get(LANGNAME_DICT_REV.get(show_target))
        elif show_target=='zh':
            # 特殊兼容zh
            target_list=LANG_CODE['zh-cn']
        if target_list and target_list[index].lower() == 'no':
            if return_str:
                return tr('deepl_nosupport') + f':{show_target}'
            tools.show_error(tr('deepl_nosupport') + f':{show_target}')
            return False
    return True


# 获取用于进行语音识别的预设语言，比如语音是英文发音、中文发音
# 根据 原语言进行判断,基本等同于google，但只保留_之前的部分
def get_audio_code(*, show_source=None):
    if not show_source or show_source in ['auto','-']:
        return 'auto'
    source_list = LANG_CODE[show_source] if show_source in LANG_CODE else LANG_CODE.get(LANGNAME_DICT_REV.get(show_source))
    return source_list[0] if source_list else "auto"


# 获取嵌入软字幕的3位字母语言代码，根据目标语言确定
def get_subtitle_code(*, show_target=None):
    if show_target in LANG_CODE:
        return LANG_CODE[show_target][1]
    if show_target in LANGNAME_DICT_REV:
        return LANG_CODE[LANGNAME_DICT_REV[show_target]][1]
    return 'eng'

def _check_google():
    import requests
    try:
        requests.head(f"https://translate.google.com",timeout=5)
    except Exception as e:
        logger.exception(f'检测google翻译失败{e}', exc_info=True)
        return False
    
    return True
    


# 翻译,先根据翻译通道和目标语言，取出目标语言代码
def run(*, translate_type=0,
        text_list=None,
        is_test=False,
        source_code=None,
        target_code=None,
        uuid=None) -> Union[List, str, None]:
    translate_type = int(translate_type)
    # ai渠道下，target_language_name 是语言名称
    # 其他渠道下是语言代码
    # source_code 是原语言代码
    target_language_name = target_code
    if translate_type in AI_TRANS_CHANNELS:
        # 对AI渠道，返回目标语言的自然语言表达
        _, target_language_name = get_source_target_code(show_target=target_code, translate_type=translate_type)
    kwargs = {
        "text_list": text_list,
        "target_language_name": target_language_name,
        "source_code": source_code if source_code and source_code not in ['-', 'No'] else 'auto',
        "target_code": target_code,
        "uuid": uuid,
        "is_test": is_test,
        "translate_type":translate_type
    }

    # 未设置代理并且检测google失败，则使用微软翻译
    if translate_type == GOOGLE_INDEX:
        if app_cfg.proxy or _check_google() is True:
            return Google(**kwargs).run()
        logger.warning('==未设置代理并且检测google失败，使用微软翻译')
        return Microsoft(**kwargs).run()
        
    if translate_type == MyMemoryAPI_INDEX:
        return MyMemory(**kwargs).run()
    if translate_type == QWENMT_INDEX:
        return QwenMT(**kwargs).run()

    if translate_type == MICROSOFT_INDEX:
        return Microsoft(**kwargs).run()

    if translate_type == TENCENT_INDEX:
        return Tencent(**kwargs).run()

    if translate_type == BAIDU_INDEX:
        return Baidu(**kwargs).run()

    if translate_type == OTT_INDEX:
        return OTT(**kwargs).run()

    if translate_type == TRANSAPI_INDEX:
        return TransAPI(**kwargs).run()

    if translate_type == DEEPL_INDEX:
        return DeepL(**kwargs).run()

    if translate_type == DEEPLX_INDEX:
        return DeepLX(**kwargs).run()

    if translate_type == AI302_INDEX:
        return AI302(**kwargs).run()

    if translate_type == LOCALLLM_INDEX:
        return LocalLLM(**kwargs).run()

    if translate_type == ZIJIE_INDEX:
        return HuoShan(**kwargs).run()

    if translate_type == CHATGPT_INDEX:
        return ChatGPT(**kwargs).run()
    if translate_type == ZHIPUAI_INDEX:
        return ZhipuAI(**kwargs).run()
    if translate_type == OPENROUTER_INDEX:
        return OpenRouter(**kwargs).run()
    if translate_type == DEEPSEEK_INDEX:
        return DeepSeek(**kwargs).run()

    if translate_type == SILICONFLOW_INDEX:
        return SILICONFLOW(**kwargs).run()

    if translate_type == AZUREGPT_INDEX:
        return AzureGPT(**kwargs).run()

    if translate_type == GEMINI_INDEX:
        return Gemini(**kwargs).run()
    if translate_type == LIBRE_INDEX:
        return Libre(**kwargs).run()
    if translate_type == ALI_INDEX:
        return Ali(**kwargs).run()
    if translate_type == M2M100_INDEX:
        from videotrans.translator._m2m100 import M2M100Trans 
        return M2M100Trans(**kwargs).run()

    raise RuntimeError('未选中任何翻译渠道')
