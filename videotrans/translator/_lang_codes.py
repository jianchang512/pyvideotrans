from pathlib import Path

from videotrans.configure.config import tr, ROOT_DIR, logger

# subtitles language code  https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
#  MP4视频   使用3位 T格式(ISO-639-2/T)，  MKV使用使用 3位B格式 ISO 639-2/B
# 腾讯翻译 https://cloud.tencent.com/document/api/862/126431
# google翻译 https://translate.google.com/
# 百度翻译 https://fanyi.baidu.com/
# deepl  https://deepl.com/
# microsoft https://www.bing.com/translator?mkt=zh-CN
# 阿里机器翻译
# https://help.aliyun.com/zh/machine-translation/developer-reference/machine-translation-language-code-list
# qwen-mt https://help.aliyun.com/zh/model-studio/machine-translation
# m2m100  https://github.com/ymoslem/DesktopTranslator/blob/main/utils/m2m_languages.json
LANGNAME_DICT = {
    "en": tr("en"),
    "zh-cn": tr("zh-cn"),
    "zh-tw": tr("zh-tw"),
    "fr": tr("fr"),
    "de": tr("de"),
    "ja": tr("ja"),
    "ko": tr("ko"),
    "ru": tr("ru"),
    "es": tr("es"),
    "es-419": tr("es-419"),
    "th": tr("th"),
    "it": tr("it"),
    "el": tr("el"),
    "pt": tr("pt"),
    "pt-br": tr("pt-br"),
    "vi": tr("vi"),
    "ar": tr("ar"),
    "tr": tr("tr"),
    "hi": tr("hi"),
    "hu": tr("hu"),
    "uk": tr("uk"),
    "id": tr("id"),
    "ms": tr("ms"),
    "kk": tr("kk"),
    "cs": tr("cs"),
    "pl": tr("pl"),
    "nl": tr("nl"),
    "sv": tr("sv"),
    "he": tr("he"),
    "bn": tr("bn"),
    "fa": tr("fa"),
    "fil": tr("fil"),
    "ur": tr("ur"),
    "nb": tr("nb"),  # 书面挪威语
    "yue": tr("yue"),
    "km": tr("km"),  # 高棉
    "ro": tr("ro"),  # 罗马尼亚
    "uz": tr("uz"),  # 乌兹别克斯坦
}

# 如果存在新增
try:
    if Path(ROOT_DIR + f'/videotrans/newlang.txt').exists():
        _new_lang = Path(ROOT_DIR + f'/videotrans/newlang.txt').read_text().strip().split("\n")
        for nl in _new_lang:
            LANGNAME_DICT[nl] = nl
except Exception as e:
    logger.exception(f'读取自定义新增语言代码 newlang.txt 时出错 {e}', exc_info=True)

# 反向按照显示名字查找语言代码
LANGNAME_DICT_REV = {v: k for k, v in LANGNAME_DICT.items()}

# 根据语言代码查找各个翻译渠道对应的 代码list
# 字幕嵌入代码默认使用  ISO 639-2/T(mp4所需)，MKV视频需使用 ISO 639-2/B 格式
LANG_CODE = {
    "zh-cn": [
        "zh-cn",  # google通道
        "zho",  # 字幕嵌入语言
        "zh",  # 百度通道
        "ZH-HANS",  # deepl deeplx通道
        "zh",  # 腾讯通道
        "zh",  # OTT通道
        "zh-Hans",  # 微软翻译
        "Simplified Chinese",  # AI翻译
        "zh",  # 阿里
        "Chinese",  # qwen-mt qwen-tts qwen-asr
        "zh"  # m2m100
    ],
    "zh-tw": [
        "zh-tw",
        "zho",
        "cht",
        "ZH-HANT",
        "zh-TW",
        "zt",
        "zh-Hant",
        "Traditional Chinese",
        "zh-tw",
        "Traditional Chinese",
        "zh"  # m2m100
    ],
    "uz": [
        "uz",  # google通道
        "uzb",  # 字幕嵌入语言
        "No",  # 百度通道
        "No",  # deepl deeplx通道
        "uz",  # 腾讯通道
        "uz",  # OTT通道
        "uz",  # 微软翻译
        "Uzbek",  # AI翻译
        "uz",  # 阿里
        "Northern Uzbek",  # qwen-mt qwen-tts qwen-asr
        "uz"  # m2m100
    ],
    "ur": [
        "ur",  # google通道
        "urd",  # 字幕嵌入语言
        "ur",  # 百度通道
        "UR",  # deepl deeplx通道
        "ur",  # 腾讯通道
        "No",  # OTT通道
        "ur",  # 微软翻译
        "Urdu",  # AI翻译
        "ur",  # 阿里
        "Urdu",
        "ur"  # m2m100
    ],
    "ro": [
        "ro",  # google通道
        "ron",  # 字幕嵌入语言
        "rom",  # 百度通道
        "RO",  # deepl deeplx通道
        "ro",  # 腾讯通道
        "No",  # OTT通道
        "ro",  # 微软翻译
        "Romanian",  # AI翻译
        "ro",  # 阿里
        "Romanian",# qwen-mt
        "ro"  # m2m100
    ],
    "km": [
        "km",  # google通道
        "khm",  # 字幕嵌入语言
        "km",  # 百度通道
        "No",  # deepl deeplx通道
        "km",  # 腾讯通道
        "No",  # OTT通道
        "km",  # 微软翻译
        "Khmer",  # AI翻译
        "km",  # 阿里
        "Khmer",
        "km"  # m2m100
    ],
    "yue": [
        "yue",  # google通道
        "chi",  # 字幕嵌入语言
        "yue",  # 百度通道
        "YUE",  # deepl deeplx通道
        "yue",  # 腾讯通道
        "No",  # OTT通道
        "yue",  # 微软翻译
        "Cantonese",  # AI翻译
        "yue",  # 阿里
        "Cantonese",
        "zh"  # m2m100
    ],

    "fil": [
        "tl",  # google通道
        "fil",  # 字幕嵌入语言
        "fil",  # 百度通道
        "No",  # deepl deeplx通道
        "fil",  # 腾讯通道
        "No",  # OTT通道
        "fil",  # 微软翻译
        "Filipino",  # AI翻译
        "fil",  # 阿里
        "Filipino",
        "No"
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
        "en"  # m2m100
    ],
    "fr": [
        "fr",
        "fra",
        "fra",
        "FR",
        "fr",
        "fr",
        "fr",
        "French",
        "fr",
        "French",
        "fr"  # m2m100
    ],
    "de": [
        "de",
        "deu",
        "de",
        "DE",
        "de",
        "de",
        "de",
        "German",
        "de",
        "German",
        "de"  # m2m100
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
        "ja"  # m2m100
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
        "ko"  # m2m100
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
        "ru"  # m2m100
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
        "es"  # m2m100
    ],
    "th": [
        "th",
        "tha",
        "th",
        "TH",
        "th",
        "th",
        "th",
        "Thai",
        "th",
        "Thai",
        "th"  # m2m100
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
        "it"  # m2m100
    ],
    "el": [
        "el",  # google
        "ell",  # subtitle embed (ISO 639-2/T)
        "el",  # baidu
        "EL",  # deepl / deeplx
        "el",  # tencent
        "el",  # OTT
        "el",  # microsoft / bing
        "Greek",  # AI (LLM)
        "el",  # alibaba
        "Greek",  # qwen-mt / qwen-tts / qwen-asr
        "el"  # m2m100
    ],
    "nb": [
        "no",  # google
        "nob",  # subtitle embed (ISO 639-2/B)
        "nob",  # baidu
        "NB",  # deepl / deeplx
        "No",  # tencent 不支持
        "No",  # OTT 不支持
        "nb",  # microsoft / bing
        "Norwegian Bokmål",  # AI (LLM) 书面挪威语
        "no",  # alibaba
        "Norwegian Bokmål",  # qwen-mt / qwen-tts / qwen-asr
        "no"  # m2m100
    ],
    "pt": [
        "pt-PT",  # pt-PT
        "por",
        "pt",
        "PT-PT",
        "pt",
        "pt",
        "pt",
        "Portuguese",
        "pt",
        "Portuguese",
        "pt"  # m2m100
    ],
    "vi": [
        "vi",
        "vie",
        "vie",
        "VI",
        "vi",
        "vi",
        "vi",
        "Vietnamese",
        "vi",
        "Vietnamese",
        "vi"  # m2m100
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
        "ar"  # m2m100
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
        "tr"  # m2m100
    ],
    "hi": [
        "hi",
        "hin",
        "hi",
        "HI",
        "hi",
        "hi",
        "hi",
        "Hindi",
        "hi",
        "Hindi",
        "hi"  # m2m100
    ],
    "hu": [
        "hu",
        "hun",
        "hu",
        "HU",
        "hu",
        "hu",
        "hu",
        "Hungarian",
        "hu",
        "Hungarian",
        "hu"  # m2m100
    ],
    "uk": [
        "uk",
        "ukr",
        "ukr",  # 百度
        "UK",  # deepl
        "uk",  # 腾讯
        "uk",  # ott
        "uk",  # 微软
        "Ukrainian",
        "No",
        "Ukrainian",
        "uk"  # m2m100
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
        "id"  # m2m100
    ],
    "ms": [
        "ms",
        "msa",
        "may",
        "MS",
        "ms",
        "ms",
        "ms",
        "Malay",
        "ms",
        "Malay",
        "ms"  # m2m100
    ],
    "kk": [
        "kk",
        "kaz",
        "KK",
        "No",
        "kk",
        "No",
        "kk",
        "Kazakh",
        "kk",
        "Kazakh",
        "kk"  # m2m100
    ],
    "cs": [
        "cs",
        "ces",
        "cs",
        "CS",
        "cs",
        "cs",
        "cs",
        "Czech",
        "cs",
        "Czech",
        "cs"  # m2m100
    ],
    "pl": [
        "pl",
        "pol",
        "pl",
        "PL",
        "pl",
        "pl",
        "pl",
        "Polish",
        "pl",
        "Polish",
        "pl"  # m2m100
    ],
    "nl": [
        "nl",  # google通道
        "nld",  # 字幕嵌入语言
        "nl",  # 百度通道
        "NL",  # deepl deeplx通道
        "nl",  # 腾讯通道
        "nl",  # OTT通道
        "nl",  # 微软翻译
        "Dutch",  # AI翻译
        "nl",
        "Dutch",
        "nl"  # m2m100
    ],
    "sv": [
        "sv",  # google通道
        "swe",  # 字幕嵌入语言
        "swe",  # 百度通道
        "SV",  # deepl deeplx通道
        "sv",  # 腾讯通道
        "sv",  # OTT通道
        "sv",  # 微软翻译
        "Swedish",  # AI翻译
        "sv",
        "Swedish",
        "sv"  # m2m100
    ],
    "he": [
        "he",  # google通道
        "heb",  # 字幕嵌入语言
        "heb",  # 百度通道
        "HE",  # deepl deeplx通道
        "he",  # 腾讯通道
        "No",  # OTT通道
        "he",  # 微软翻译
        "Hebrew",  # AI翻译
        "he",
        "Hebrew",
        "he"  # m2m100
    ],
    "bn": [
        "bn",  # google通道
        "ben",  # 字幕嵌入语言
        "ben",  # 百度通道
        "BN",  # deepl deeplx通道
        "bn",  # 腾讯通道
        "No",  # OTT通道
        "bn",  # 微软翻译
        "Bengali",  # AI翻译,
        "bn",
        "Bengali",
        "bn"  # m2m100
    ],
    "fa": [
        "fa",  # google通道
        "fas",  # 字幕嵌入语言
        "per",  # 百度通道
        "FA",  # deepl deeplx通道
        "fa",  # 腾讯通道
        "No",  # OTT通道
        "fa",  # 微软翻译
        "Persian",  # AI翻译
        "fa",  # 阿里
        "Western Persian",
        "fa"  # m2m100
    ],
    
    "pt-br": [
        "pt",  # pt-PT
        "por",#字幕
        "pot",#百度
        "PT-BR",#deepl
        "pt",#腾讯
        "pt",#ott
        "pt",#微软
        "Portuguese (Brazilian)",#AI 
        "pt",#阿里
        "Portuguese (Brazilian)",#qwen-mt
        "pt"  # m2m100
    ],
    "es-419": [
        "es",#google
        "spa",
        "spa",#baidu
        "ES-419",#deepl
        "es",#腾讯
        "es",#ott
        "es",#微软
        "Spanish",#AI
        "es",#阿里机器
        "Spanish",#qwenmt
        "es"  # m2m100
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
