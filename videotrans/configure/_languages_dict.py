import logging
from pathlib import Path
import json
# 固定不变:M2M100 翻译渠道,
_LANGUAGE_M2M100 = {
    "af": "__af__",
    "am": "__am__",
    "ar": "__ar__",
    "ast": "__ast__",
    "az": "__az__",
    "ba": "__ba__",
    "be": "__be__",
    "bg": "__bg__",
    "bn": "__bn__",
    "br": "__br__",
    "bs": "__bs__",
    "ca": "__ca__",
    "ceb": "__ceb__",
    "cs": "__cs__",
    "cy": "__cy__",
    "da": "__da__",
    "de": "__de__",
    "el": "__el__",
    "en": "__en__",
    "es": "__es__",
    "et": "__et__",
    "fa": "__fa__",
    "ff": "__ff__",
    "fi": "__fi__",  # 芬兰
    "fr": "__fr__",
    "fy": "__fy__",
    "ga": "__ga__",
    "gd": "__gd__",
    "gl": "__gl__",
    "gu": "__gu__",
    "ha": "__ha__",
    "he": "__he__",
    "hi": "__hi__",
    "hr": "__hr__",
    "ht": "__ht__",
    "hu": "__hu__",
    "hy": "__hy__",
    "id": "__id__",
    "ig": "__ig__",
    "ilo": "__ilo__",
    "is": "__is__",
    "it": "__it__",
    "ja": "__ja__",
    "jv": "__jv__",
    "ka": "__ka__",
    "kk": "__kk__",
    "km": "__km__",
    "kn": "__kn__",
    "ko": "__ko__",
    "lb": "__lb__",
    "lg": "__lg__",
    "ln": "__ln__",
    "lo": "__lo__",
    "lt": "__lt__",
    "lv": "__lv__",
    "mg": "__mg__",
    "mk": "__mk__",
    "ml": "__ml__",
    "mn": "__mn__",
    "mr": "__mr__",
    "ms": "__ms__",
    "my": "__my__",
    "ne": "__ne__",
    "nl": "__nl__",
    "no": "__no__",
    "ns": "__ns__",
    "oc": "__oc__",
    "or": "__or__",
    "pa": "__pa__",
    "pl": "__pl__",
    "ps": "__ps__",
    "pt": "__pt__",
    "ro": "__ro__",
    "ru": "__ru__",
    "sd": "__sd__",
    "si": "__si__",
    "sk": "__sk__",
    "sl": "__sl__",
    "so": "__so__",
    "sq": "__sq__",
    "sr": "__sr__",
    "ss": "__ss__",
    "su": "__su__",
    "sv": "__sv__",
    "sw": "__sw__",
    "ta": "__ta__",
    "th": "__th__",
    "fil": "__tl__",  # 菲律宾
    "tn": "__tn__",
    "tr": "__tr__",
    "uk": "__uk__",
    "ur": "__ur__",
    "uz": "__uz__",
    "vi": "__vi__",
    "wo": "__wo__",
    "xh": "__xh__",
    "yi": "__yi__",
    "yo": "__yo__",
    "zh": "__zh__",
    "yue": "__zh__",
    "zu": "__zu__"
}
# 固定不变:小红书 TTS3 渠道 
_LANGUAGE_FIRERED3 = {
    "ar": "Arabic",
    "yue": "Cantonese",
    "zh": "Chinese",
    "cz": "Czech",
    "nl": "Dutch",
    "en": "English",
    "fr": "French",
    "de": "German",
    "el": "Greek",
    "hi": "Hindi",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "es": "Spanish",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "fi": "Finnish",
    "vi": "Vietnamese"
}
# 固定不变:edge-tts/omnivoice 可用的语言代码列表：
EDGE_LANGUANGES_CODE = [
        "zh-cn",
        "zh-tw",
        "yue",
        "en",
        "fr",
        "de",
        "ja",
        "ko",
        "ru",
        "es",
        "th",
        "it",
        "pt",
        "vi",
        "ar",
        "tr",
        "hi",
        "hu",
        "uk",
        "id",
        "ms",
        "kk",
        "cs",
        "pl",
        "nl",
        "sv",
        "he",
        "bn",
        "fil",

        "af",
        "sq",
        "am",
        "az",
        "bs",
        "bg",
        "my",
        "ca",
        "hr",
        "da",
        "et",
        "fi",
        "gl",
        "ka",
        "el",
        "gu",
        "is",
        "iu",
        "ga",
        "jv",
        "kn",
        "km",
        "lo",
        "lv",
        "lt",
        "mk",
        "ml",
        "mt",
        "mr",
        "mn",
        "ne",
        "nb",
        "ps",
        "fa",

        "ro",
        "sr",
        "si",
        "sk",
        "sl",
        "so",
        "su",
        "sw",
        "ta",
        "te",
        "ur",
        "uz",
        "cy",
        "zu"
    ]

# ------------配音试听---------------
# 每增加一个语言，需在此添加对应的试听词
LISTEN_TEXT = {
    "zh": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
    "bg": "Здравей, скъпи приятелю, надявам се всеки твой ден да е прекрасен и радостен.",
    "uz": "Salom, aziz do'stim, umid qilamanki, har bir kuningiz ajoyib va ​​quvonchli o'tadi!",
    "en": "Hello, my dear friend. I hope your every day is beautiful and enjoyable!",
    "fr": "Bonjour mon cher ami. J'espère que votre quotidien est beau et agréable !",
    "de": "Hallo mein lieber Freund. Ich hoffe, dass Ihr Tag schön und angenehm ist!",
    "ja": "こんにちは私の親愛なる友人。 あなたの毎日が美しく楽しいものでありますように！",
    "ko": "안녕, 내 사랑하는 친구. 당신의 매일이 아름답고 즐겁기를 바랍니다!",
    "ru": "Привет, мой дорогой друг. Желаю, чтобы каждый твой день был прекрасен и приятен!",
    "es": "Hola mi querido amigo. ¡Espero que cada día sea hermoso y agradable!",
    "th": "สวัสดีเพื่อนรัก. ฉันหวังว่าทุกวันของคุณจะสวยงามและสนุกสนาน!",
    "it": "Ciao caro amico mio. Spero che ogni tuo giorno sia bello e divertente!",
    "el": "Γεια σου, αγαπητέ μου φίλε. Εύχομαι κάθε σου μέρα να είναι όμορφη και ευχάριστη!",
    "pt": "Olá meu querido amigo. Espero que todos os seus dias sejam lindos e agradáveis!",
    "vi": "Xin chào người bạn thân yêu của tôi. Tôi hy vọng mỗi ngày của bạn đều đẹp và thú vị!",
    "ar": "مرحبا صديقي العزيز. أتمنى أن يكون كل يوم جميلاً وممتعًا!",
    "tr": "Merhaba sevgili arkadaşım. Umarım her gününüz güzel ve keyifli geçer!",
    "hi": "नमस्ते मेरे प्यारे दोस्त। मुझे आशा है कि आपका हर दिन सुंदर और आनंददायक हो!!",
    "hu": "Helló kedves barátom. Remélem minden napod szép és kellemes!",
    "uk": "Привіт, мій дорогий друже, сподіваюся, ти щодня прекрасна!",
    "id": "Halo, temanku, semoga kamu cantik setiap hari!",
    "ms": "Helo, sahabat saya, saya harap anda cantik setiap hari!",
    "kk": "Сәлеметсіз бе, менің қымбатты досым, сендер күн сайын әдемісің деп үміттенемін!",
    "cs": "Ahoj, můj drahý příteli, doufám, že jsi každý den krásná!",
    "pl": "Witam, mój drogi przyjacielu, mam nadzieję, że jesteś piękna każdego dnia!",
    "nl": "Hallo mijn lieve vriend, ik hoop dat elke dag goed en fijn voor je is!!",
    "sv": "Hej min kära vän, jag hoppas att varje dag är en bra och trevlig dag för dig!",
    "he": "שלום, ידידי היקר, אני מקווה שכל יום בחייך יהיה נפלא ומאושר!",
    "bn": "হ্যালো, আমার প্রিয় বন্ধু, আমি আশা করি আপনার জীবনের প্রতিটি দিন চমৎকার এবং সুখী হোক!",
    "fil": "Hello, kaibigan ko",
    "fa": "سلام دوستای گلم امیدوارم هر روز از زندگیتون عالی و شاد باشه.",
    "ur": "ہیلو پیارے دوست، مجھے امید ہے کہ آپ آج خوش ہوں گے۔",
    "yue": "你好啊親愛嘅朋友，希望你今日好開心",
    "ro": "Bună, draga mea prietenă, sper ca fiecare zi a ta să fie minunată și plină de bucurie!",
    "km": "សួស្តីមិត្តជាទីស្រឡាញ់របស់ខ្ញុំ ខ្ញុំសង្ឃឹមថារាល់ថ្ងៃរបស់អ្នកគឺអស្ចារ្យ និងរីករាយ។!",
    "nb": "Hallo, min kjære venn, jeg håper hver dag din er fantastisk og gledelig.",
}


# 根据语言代码查找各个翻译渠道对应的 代码list
# 字幕嵌入代码默认使用  ISO 639-2/T(mp4所需)，MKV视频需使用 ISO 639-2/B 格式 https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
#  MP4视频   使用3位 T格式(ISO-639-2/T)，  MKV使用使用 3位B格式 ISO 639-2/B
# 腾讯翻译 https://cloud.tencent.com/document/api/862/126431
# google翻译 https://docs.cloud.google.com/translate/docs/languages
# 百度翻译 https://fanyi-api.baidu.com/product/113
# deepl/deeplx  https://developers.deepl.com/docs/getting-started/supported-languages
# microsoft https://www.bing.com/translator?mkt=zh-CN
# 阿里机器翻译
# https://help.aliyun.com/zh/machine-translation/developer-reference/machine-translation-language-code-list
# qwen-mt https://help.aliyun.com/zh/model-studio/machine-translation
# m2m100  https://github.com/ymoslem/DesktopTranslator/blob/main/utils/m2m_languages.json
# 视频翻译中可用的语言代码及不同代码形式
# 每增加一个语言，需在此添加对应不同渠道所需语言代码形式
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
    "bg": [
        "bg",  # google通道
        "bul",  # 字幕嵌入语言
        "bg",  # 百度通道
        "BG",  # deepl deeplx通道
        "bg",  # 腾讯通道
        "bg",  # OTT通道
        "bg",  # 微软翻译
        "Bulgarian",  # AI翻译
        "bg",  # 阿里
        "Bulgarian",  # qwen-mt qwen-tts qwen-asr
        "bg"  # m2m100
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

# 合并自定义语言
def _merge_newlang():
    from ._paths import ROOT_DIR
    _f=f'{ROOT_DIR}/videotrans/languages.json'
    if Path(_f).exists():
        try:
            _newlang=json.loads(Path(_f).read_text(encoding='utf-8'))
            if _newlang:
                LANG_CODE.update(_newlang)
        except Exception as e:
            logging.getLogger('VideoTrans').exception(f'加载自定义语言数据失败：{e}', exc_info=True)
    else:
        Path(_f).write_text('{}',encoding='utf-8')
_merge_newlang()