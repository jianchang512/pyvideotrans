try:
    import pykakasi
    PYKAKASI_AVAILABLE = True
except ImportError:
    PYKAKASI_AVAILABLE = False


# Language token map for multilingual TTS
LANGUAGE_TOKEN_MAP = {
    "zh": "请用中文朗读接下来的文字",
    "ja": "请用日语朗读接下来的文字",
    "ko": "请用韩语朗读接下来的文字",  # Korean

    "vi": "请用越南语朗读接下来的文字",  # Vietnamese
    "th": "请用泰语朗读接下来的文字",  # Thai
    "id": "请用印尼语朗读接下来的文字",  # Indonesian
    "ms": "请用马来语朗读接下来的文字",  # Malay
    "tl": "请用菲律宾语朗读接下来的文字",  # Tagalog/Filipino
    "my": "请用缅甸语朗读接下来的文字",  # Burmese
    "km": "请用高棉语朗读接下来的文字",  # Khmer
    "lo": "请用老挝语朗读接下来的文字",  # Lao

    "hi": "请用印地语朗读接下来的文字",  # Hindi
    "bn": "请用孟加拉语朗读接下来的文字",  # Bengali
    "ta": "请用泰米尔语朗读接下来的文字",  # Tamil
    "te": "请用泰卢固语朗读接下来的文字",  # Telugu
    "mr": "请用马拉地语朗读接下来的文字",  # Marathi
    "gu": "请用古吉拉特语朗读接下来的文字",  # Gujarati
    "kn": "请用卡纳达语朗读接下来的文字",  # Kannada
    "ml": "请用马拉雅拉姆语朗读接下来的文字",  # Malayalam
    "pa": "请用旁遮普语朗读接下来的文字",  # Punjabi
    "ur": "请用乌尔都语朗读接下来的文字",  # Urdu
    "ne": "请用尼泊尔语朗读接下来的文字",  # Nepali
    "si": "请用僧伽罗语朗读接下来的文字",  # Sinhala

    "en": "请用英文朗读接下来的文字",  # English
    "de": "请用德语朗读接下来的文字",  # German
    "nl": "请用荷兰语朗读接下来的文字",  # Dutch
    "sv": "请用瑞典语朗读接下来的文字",  # Swedish
    "da": "请用丹麦语朗读接下来的文字",  # Danish
    "no": "请用挪威语朗读接下来的文字",  # Norwegian
    "nb": "请用挪威语朗读接下来的文字",  # Norwegian Bokmål
    "nn": "请用挪威语朗读接下来的文字",  # Norwegian Nynorsk
    "is": "请用冰岛语朗读接下来的文字",  # Icelandic
    "af": "请用南非荷兰语朗读接下来的文字",  # Afrikaans
    "lb": "请用卢森堡语朗读接下来的文字",  # Luxembourgish
    "fy": "请用弗里斯兰语朗读接下来的文字",  # Frisian

    "fr": "请用法语朗读接下来的文字",  # French
    "es": "请用西班牙语朗读接下来的文字",  # Spanish
    "pt": "请用葡萄牙语朗读接下来的文字",  # Portuguese
    "it": "请用意大利语朗读接下来的文字",  # Italian
    "ro": "请用罗马尼亚语朗读接下来的文字",  # Romanian
    "ca": "请用加泰罗尼亚语朗读接下来的文字",  # Catalan
    "gl": "请用加利西亚语朗读接下来的文字",  # Galician
    "oc": "请用奥克语朗读接下来的文字",  # Occitan
    "la": "请用拉丁语朗读接下来的文字",  # Latin

    "ru": "请用俄语朗读接下来的文字",  # Russian
    "uk": "请用乌克兰语朗读接下来的文字",  # Ukrainian
    "pl": "请用波兰语朗读接下来的文字",  # Polish
    "cs": "请用捷克语朗读接下来的文字",  # Czech
    "sk": "请用斯洛伐克语朗读接下来的文字",  # Slovak
    "bg": "请用保加利亚语朗读接下来的文字",  # Bulgarian
    "sr": "请用塞尔维亚语朗读接下来的文字",  # Serbian
    "hr": "请用克罗地亚语朗读接下来的文字",  # Croatian
    "sl": "请用斯洛文尼亚语朗读接下来的文字",  # Slovenian
    "mk": "请用马其顿语朗读接下来的文字",  # Macedonian
    "bs": "请用波斯尼亚语朗读接下来的文字",  # Bosnian
    "be": "请用白俄罗斯语朗读接下来的文字",  # Belarusian

    "lt": "请用立陶宛语朗读接下来的文字",  # Lithuanian
    "lv": "请用拉脱维亚语朗读接下来的文字",  # Latvian

    "fi": "请用芬兰语朗读接下来的文字",  # Finnish
    "et": "请用爱沙尼亚语朗读接下来的文字",  # Estonian
    "hu": "请用匈牙利语朗读接下来的文字",  # Hungarian

    "ga": "请用爱尔兰语朗读接下来的文字",  # Irish
    "cy": "请用威尔士语朗读接下来的文字",  # Welsh
    "gd": "请用苏格兰盖尔语朗读接下来的文字",  # Scottish Gaelic
    "br": "请用布列塔尼语朗读接下来的文字",  # Breton

    "el": "请用希腊语朗读接下来的文字",  # Greek

    "sq": "请用阿尔巴尼亚语朗读接下来的文字",  # Albanian

    "eu": "请用巴斯克语朗读接下来的文字",  # Basque

    "mt": "请用马耳他语朗读接下来的文字",  # Maltese

    "tr": "请用土耳其语朗读接下来的文字",  # Turkish
    "az": "请用阿塞拜疆语朗读接下来的文字",  # Azerbaijani
    "kk": "请用哈萨克语朗读接下来的文字",  # Kazakh
    "uz": "请用乌兹别克语朗读接下来的文字",  # Uzbek
    "tk": "请用土库曼语朗读接下来的文字",  # Turkmen
    "ky": "请用吉尔吉斯语朗读接下来的文字",  # Kyrgyz
    "tt": "请用鞑靼语朗读接下来的文字",  # Tatar

    "ar": "请用阿拉伯语朗读接下来的文字",  # Arabic
    "he": "请用希伯来语朗读接下来的文字",  # Hebrew
    "am": "请用阿姆哈拉语朗读接下来的文字",  # Amharic

    "fa": "请用波斯语朗读接下来的文字",  # Persian/Farsi
    "ps": "请用普什图语朗读接下来的文字",  # Pashto
    "ku": "请用库尔德语朗读接下来的文字",  # Kurdish
    "tg": "请用塔吉克语朗读接下来的文字",  # Tajik

    "ka": "请用格鲁吉亚语朗读接下来的文字",  # Georgian
    "hy": "请用亚美尼亚语朗读接下来的文字",  # Armenian

    "sw": "请用斯瓦希里语朗读接下来的文字",  # Swahili
    "yo": "请用约鲁巴语朗读接下来的文字",  # Yoruba
    "ha": "请用豪萨语朗读接下来的文字",  # Hausa
    "ig": "请用伊博语朗读接下来的文字",  # Igbo
    "zu": "请用祖鲁语朗读接下来的文字",  # Zulu
    "xh": "请用科萨语朗读接下来的文字",  # Xhosa

    "mn": "请用蒙古语朗读接下来的文字",  # Mongolian

    "eo": "请用世界语朗读接下来的文字",  # Esperanto
}


class KatakanaConverter:
    _instance = None
    _kks = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if PYKAKASI_AVAILABLE:
                cls._kks = pykakasi.kakasi()
        return cls._instance

    def to_katakana(self, text: str) -> str:
        if self._kks is None:
            return text
        result = self._kks.convert(text)
        return ''.join([item['kana'] for item in result])


_katakana_converter = KatakanaConverter()


def get_language_token(lang: str) -> str:
    return LANGUAGE_TOKEN_MAP.get(lang, f"请用{lang}朗读接下来的文字")


def to_katakana(text: str) -> str:
    return _katakana_converter.to_katakana(text)
