import logging
from pathlib import Path
import json

# 固定不变:M2M100 翻译渠道,
LANGUAGE_M2M100 = {
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
LANGUAGE_FIRERED3 = {
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
# 每增加一个语言，需在此添加对应的试听词
LISTEN_TEXT = {
    "zh": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
    "zh-cn": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
    "zh-tw": "你好啊，我親愛的朋友，希望你的每一天都是美好愉快的！",
    "yue": "你好呀，我親愛嘅朋友，希望你每一日都係美好同愉快嘅！",
    "en": "Hello, my dear friend, I hope every day of yours is wonderful and joyful!",
    "fr": "Bonjour, mon cher ami, j'espère que chacune de tes journées sera belle et agréable !",
    "de": "Hallo, mein lieber Freund, ich hoffe, dass jeder deiner Tage wunderbar und erfreulich ist!",
    "ja": "こんにちは、親愛なる友よ。あなたの日々がいつも素晴らしく、楽しいものでありますように！",
    "ko": "안녕, 나의 소중한 친구야. 너의 매일매일이 아름답고 즐겁기를 바라!",
    "ru": "Привет, мой дорогой друг! Надеюсь, каждый твой день будет прекрасным и радостным!",
    "es": "¡Hola, mi querido amigo! ¡Espero que cada uno de tus días sea hermoso y agradable!",
    "th": "สวัสดีเพื่อนรักของฉัน ขอให้ทุกๆ วันของคุณเป็นวันที่สวยงามและมีความสุขนะ!",
    "it": "Ciao, mio caro amico, spero che ogni tuo giorno sia meraviglioso e piacevole!",
    "pt": "Olá, meu querido amigo, espero que cada um dos seus dias seja maravilhoso e agradável!",
    "vi": "Xin chào người bạn thân yêu của tôi, chúc bạn mỗi ngày đều thật tươi đẹp và vui vẻ!",
    "ar": "مرحبًا يا صديقي العزيز، أتمنى أن يكون كل يوم من أيامك جميلاً وممتعًا!",
    "tr": "Merhaba sevgili dostum, umarım her günün güzel ve neşeli geçer!",
    "hi": "नमस्ते, मेरे प्यारे दोस्त, मुझे आशा है कि आपका हर दिन सुंदर और सुखद हो!",
    "hu": "Szia, kedves barátom! Remélem, minden napod szép és kellemes lesz!",
    "uk": "Привіт, мій дорогий друже! Сподіваюся, кожен твій день буде прекрасним і радісним!",
    "id": "Halo, sahabatku tersayang, semoga setiap harimu indah dan menyenangkan!",
    "ms": "Helo, sahabatku yang dikasihi, semoga setiap hari anda indah dan menyeronokkan!",
    "kk": "Сәлем, менің қымбатты досым, әр күнің тамаша әрі қуанышты өтсін деп тілеймін!",
    "cs": "Ahoj, můj drahý příteli, doufám, že každý tvůj den bude krásný a příjemný!",
    "pl": "Cześć, mój drogi przyjacielu, mam nadzieję, że każdy Twój dzień będzie piękny i radosny!",
    "nl": "Hallo, mijn beste vriend, ik hoop dat al je dagen mooi en vreugdevol zijn!",
    "sv": "Hej, min kära vän, jag hoppas att varje dag blir underbar och glädjefylld!",
    "he": "שלום, חברי היקר, אני מקווה שכל יום שלך יהיה יפה ומהנה!",
    "bn": "হ্যালো, আমার প্রিয় বন্ধু, আশা করি তোমার প্রতিটি দিন সুন্দর এবং আনন্দময় হোক!",
    "fil": "Kumusta, aking matalik na kaibigan, sana ang bawat araw mo ay maging maganda at masaya!",
    "af": "Hallo, my liewe vriend, ek hoop dat elkeen van jou dae mooi en aangenaam sal wees!",
    "sq": "Përshëndetje, miku im i dashur, shpresoj që çdo ditë e jotja të jetë e bukur dhe e gëzueshme!",
    "am": "ሰላም፣ ውድ ጓደኛዬ፣ እያንዳንዱ ቀንህ ውብ እና አስደሳች እንዲሆን ተስፋ አደርጋለሁ!",
    "az": "Salam, əziz dostum, ümid edirəm ki, hər günün gözəl və sevincli keçər!",
    "bs": "Zdravo, dragi moj prijatelju, nadam se da će ti svaki dan biti lijep i ugodan!",
    "bg": "Здравей, скъпи приятелю, надявам се всеки твой ден да бъде прекрасен и приятен!",
    "my": "မင်္ဂလာပါ ချစ်လှစွာသောသူငယ်ချင်း၊ မင်းရဲ့နေ့ရက်တိုင်းဟာ လှပပြီး ပျော်ရွှင်ဖွယ်ကောင်းပါစေလို့ မျှော်လင့်ပါတယ်။",
    "ca": "Hola, estimat amic, espero que cadascun dels teus dies sigui bonic i agradable!",
    "hr": "Bok, dragi moj prijatelju, nadam se da će ti svaki dan biti lijep i ugodan!",
    "da": "Hej, min kære ven, jeg håber, at hver af dine dage er smuk og dejlig!",
    "et": "Tere, mu kallis sõber, loodan, et iga su päev on ilus ja meeldiv!",
    "fi": "Hei, rakas ystäväni, toivon että jokainen päiväsi on kaunis ja iloinen!",
    "gl": "Ola, meu querido amigo, espero que cada un dos teus días sexa fermoso e agradable!",
    "ka": "გამარჯობა, ჩემო ძვირფასო მეგობარო, იმედი მაქვს, შენი ყოველი დღე ლამაზი და სასიამოვნო იქნება!",
    "el": "Γεια σου, αγαπημένε μου φίλε, ελπίζω κάθε μέρα σου να είναι όμορφη και ευχάριστη!",
    "gu": "નમસ્તે, મારા વ્હાલા મિત્ર, આશા છે કે તમારો દરેક દિવસ સુંદર અને આનંદમય રહે!",
    "is": "Halló, kæri vinur minn, ég vona að hver einasti dagur þinn sé dásamlegur og ánægjulegur!",
    "iu": "ᐊᐃᓐᖓᐃ, ᓇᒡᓕᒋᔭᕋ ᐱᖃᑎᒐ, ᓂᕆᐅᑉᐳᖓ ᖃᐅᑕᒫᑦ ᐊᓕᐊᓇᐃᑦᑐᒥᒃ ᖁᕕᐊᓇᖅᑐᒥᒡᓗ ᐱᖃᑦᑕᕐᓂᐊᖅᐳᑎᑦ!",
    "ga": "Dia duit, a chara mo chroí, tá súil agam go mbeidh gach lá agat go hálainn agus taitneamhach!",
    "jv": "Halo, kanca kinasihku, muga-muga saben dinamu tansah endah lan nyenengake!",
    "kn": "ನಮಸ್ಕಾರ, ನನ್ನ ಆತ್ಮೀಯ ಗೆಳೆಯ, ನಿನ್ನ ಪ್ರತಿಯೊಂದು ದಿನವೂ ಸುಂದರ ಹಾಗೂ ಸಂತೋಷದಾಯಕವಾಗಿರಲಿ ಎಂದು ಆಶಿಸುತ್ತೇನೆ!",
    "km": "សួស្តី មិត្តសម្លាញ់របស់ខ្ញុំ សង្ឃឹមថាជារៀងរាល់ថ្ងៃរបស់អ្នកសុទ្ធតែស្រស់ស្អាតនិងពោរពេញដោយភាពរីករាយ!",
    "lo": "ສະບາຍດີ, ເພື່ອນຮັກຂອງຂ້ອຍ, ຫວັງວ່າທຸກໆມື້ຂອງເຈົ້າຈະສວຍງາມ ແລະ ມີຄວາມສຸກ!",
    "lv": "Sveiks, mans dārgais draugs! Ceru, ka katra tava diena būs skaista un patīkama!",
    "lt": "Labas, mano brangus drauge, tikiuosi, kad kiekviena tavo diena bus graži ir maloni!",
    "mk": "Здраво, драг мој пријателе, се надевам дека секој твој ден ќе биде убав и пријатен!",
    "ml": "ഹലോ, എൻ്റെ പ്രിയ സുഹൃത്തേ, നിങ്ങളുടെ ഓരോ ദിവസവും മനോഹരവും സന്തോഷകരവുമായിരിക്കട്ടെ എന്ന് ഞാൻ ആശംസിക്കുന്നു!",
    "mt": "Hello, għażiż ħabib tiegħi, nittama li kull jum tiegħek ikun sabiħ u pjaċevoli!",
    "mr": "नमस्कार, माझ्या प्रिय मित्रा, तुझा प्रत्येक दिवस सुंदर आणि आनंददायी जावो अशी आशा आहे!",
    "mn": "Сайн байна уу, хайрт найз минь, өдөр бүр чинь үзэсгэлэнтэй бөгөөд баяр баясгалантай байх болтугай!",
    "ne": "नमस्ते, मेरो प्यारो साथी, म आशा गर्छु कि तिम्रो हरेक दिन सुन्दर र रमाइलो होस्!",
    "nb": "Hei, min kjære venn, jeg håper hver dag for deg er vakker og gledelig!",
    "ps": "سلام، زما ګرانه ملګریه، هیله لرم چې ستا هره ورځ ښکلې او خوندوره وي!",
    "fa": "سلام، دوست عزیز من، امیدوارم هر روزت زیبا و لذت‌بخش باشد!",
    "ro": "Bună, dragul meu prieten, sper ca fiecare zi a ta să fie frumoasă și plăcută!",
    "sr": "Здраво, драги мој пријатељу, надам се да ће ти сваки дан бити леп и пријатан!",
    "si": "ආයුබෝවන්, මගේ ආදරණීය මිතුරා, ඔබේ සෑම දවසක්ම සුන්දර සහ ප්‍රීතිමත් වේවායි මම ප්‍රාර්ථනා කරමි!",
    "sk": "Ahoj, môj drahý priateľ, dúfam, že každý tvoj deň bude krásny a príjemný!",
    "sl": "Živjo, moj dragi prijatelj, upam, da bo vsak tvoj dan lep in prijeten!",
    "so": "Waad salaamantahay saaxiibkayga qaaliga ahow, waxaan rajaynayaa in maalin kasta oo ka mid ah noloshaadu ay noqoto mid qurux badan oo farxad leh!",
    "su": "Halo, sobat kuring anu dipikanyaah, mugia unggal dinten anjeun endah tur pikabitaeun!",
    "sw": "Hujambo, rafiki yangu mpendwa, natumai kila siku yako itakuwa nzuri na ya kupendeza!",
    "ta": "வணக்கம், என் அன்பு நண்பரே, உங்கள் ஒவ்வொரு நாளும் அழகாகவும் மகிழ்ச்சியாகவும் அமையட்டும்!",
    "te": "హలో, నా ప్రియమైన మిత్రమా, నీ ప్రతి రోజు అందంగా మరియు ఆహ్లాదకరంగా ఉండాలని ఆశిస్తున్నాను!",
    "ur": "ہیلو، میرے پیارے دوست، مجھے امید ہے کہ آپ کا ہر دن خوبصورت اور خوشگوار گزرے گا!",
    "uz": "Salom, mening qadrdon do'stim, har bir kuning go'zal va quvonchli o'tishini tilayman!",
    "cy": "Helo, fy ffrind annwyl, rwy'n gobeithio bod pob un o'th ddiwrnodau'n hyfryd ac yn bleserus!",
    "zu": "Sawubona, mngane wami othandekayo, ngithemba ukuthi zonke izinsuku zakho zizoba zinhle futhi zijabulise!"
}
# 字幕嵌入代码 T 类型
SUBTITLE_CODE = {
    "zh": "zho",
    "zh-cn": "zho",
    "zh-tw": "zho",
    "yue": "yue",
    "en": "eng",
    "fr": "fra",
    "de": "deu",
    "ja": "jpn",
    "ko": "kor",
    "ru": "rus",
    "es": "spa",
    "th": "tha",
    "it": "ita",
    "pt": "por",
    "vi": "vie",
    "ar": "ara",
    "tr": "tur",
    "hi": "hin",
    "hu": "hun",
    "uk": "ukr",
    "id": "ind",
    "ms": "msa",
    "kk": "kaz",
    "cs": "ces",
    "pl": "pol",
    "nl": "nld",
    "sv": "swe",
    "he": "heb",
    "bn": "ben",
    "fil": "fil",
    "af": "afr",
    "sq": "sqi",
    "am": "amh",
    "az": "aze",
    "bs": "bos",
    "bg": "bul",
    "my": "mya",
    "ca": "cat",
    "hr": "hrv",
    "da": "dan",
    "et": "est",
    "fi": "fin",
    "gl": "glg",
    "ka": "kat",
    "el": "ell",
    "gu": "guj",
    "is": "isl",
    "iu": "iku",
    "ga": "gle",
    "jv": "jav",
    "kn": "kan",
    "km": "khm",
    "lo": "lao",
    "lv": "lav",
    "lt": "lit",
    "mk": "mkd",
    "ml": "mal",
    "mt": "mlt",
    "mr": "mar",
    "mn": "mon",
    "ne": "nep",
    "nb": "nob",
    "ps": "pus",
    "fa": "fas",
    "ro": "ron",
    "sr": "srp",
    "si": "sin",
    "sk": "slk",
    "sl": "slv",
    "so": "som",
    "su": "sun",
    "sw": "swa",
    "ta": "tam",
    "te": "tel",
    "ur": "urd",
    "uz": "uzb",
    "cy": "cym",
    "zu": "zul",
    "pt-br": "por",
    "es-419": "spa",
    "ug": "uig"
}
# 字幕嵌入代码，根据 T 类型获取 B类型
SUBTITLE_CODE_B = {
    "zho": "chi",
    "fra": "fre",
    "deu": "ger",
    "msa": "may",
    "ces": "cze",
    "nld": "dut",
    "sqi": "alb",
    "mya": "bur",
    "kat": "geo",
    "ell": "gre",
    "isl": "ice",
    "mkd": "mac",
    "fas": "per",
    "ron": "rum",
    "slk": "slo",
    "cym": "wel",
    "bod": "tib",
    "eus": "baq",
    "hye": "arm",
    "mri": "mao"
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
    # 主要语言
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
        "zh",  # qwen-mt
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
        "en",
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
        "ja",
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
        "ko",
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
        "zh_tw",
    ],
    "yue": [
        "yue",  # google通道
        "chi",  # 字幕嵌入语言
        "yue",  # 百度通道
        "YUE",  # deepl deeplx通道
        "zh-HK",  # 腾讯通道
        "No",  # OTT通道
        "yue",  # 微软翻译
        "Cantonese",  # AI翻译
        "yue",  # 阿里
        "yue",
    ],
    # 欧洲
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
        "fr",
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
        "de",
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
        "es",
    ],
    "es-419": [
        "es",  # google
        "spa",
        "spa",  # baidu
        "ES-419",  # deepl
        "es",  # 腾讯
        "es",  # ott
        "es",  # 微软
        "Spanish",  # AI
        "es",  # 阿里机器
        "es",  # qwenmt
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
        "pt",
    ],
    "pt-br": [
        "pt",  # pt-PT
        "por",  # 字幕
        "pot",  # 百度
        "PT-BR",  # deepl
        "pt",  # 腾讯
        "pt",  # ott
        "pt",  # 微软
        "Portuguese (Brazilian)",  # AI
        "pt",  # 阿里
        "pt",  # qwen-mt
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
        "it",
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
        "ru",
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
        "hu",
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
        "pl",
    ],
    "nl": [
        "nl",  # google通道
        "nld",  # 字幕嵌入语言
        "nl",  # 百度通道
        "NL",  # deepl deeplx通道
        "No",  # 腾讯通道
        "nl",  # OTT通道
        "nl",  # 微软翻译
        "Dutch",  # AI翻译
        "nl",
        "nl",
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
        "sv",
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
        "uk",
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
        "cs",
    ],
    "el": [
        "el",  # google
        "ell",  # subtitle embed (ISO 639-2/T)
        "el",  # baidu
        "EL",  # deepl / deeplx
        "No",  # tencent
        "el",  # OTT
        "el",  # microsoft / bing
        "Greek",  # AI (LLM)
        "el",  # alibaba
        "el",  # qwen-mt
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
        "nb",  # qwen-mt
    ],
    "ro": [
        "ro",  # google通道
        "ron",  # 字幕嵌入语言
        "rom",  # 百度通道
        "RO",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "ro",  # 微软翻译
        "Romanian",  # AI翻译
        "ro",  # 阿里
        "ro",  # qwen-mt
    ],
    "bg": ['bg', 'bul', 'bul', 'BG', 'No', 'No', 'bg', 'Bulgarian', 'bg', 'bg'],
    "fi": [
        "fi",  # google通道
        "fin",  # 字幕嵌入语言
        "fin",  # 百度通道
        "FI",  # deepl deeplx通道
        "No",  # 腾讯通道
        "fi",  # OTT通道
        "fi",  # 微软翻译
        "Finnish",  # AI翻译
        "fi",  # 阿里
        "fi",  # qwen-tts
    ],

    # 东南亚
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
        "vi",
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
        "th",
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
        "id",
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
        "ms",
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
        "No",
    ],
    "km": [
        "km",  # google通道
        "khm",  # 字幕嵌入语言
        "km",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "km",  # 微软翻译
        "Khmer",  # AI翻译
        "km",  # 阿里
        "km",
    ],
    "lo": [
        "lo",  # google通道
        "lao",  # 字幕嵌入语言
        "lao",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "lo",  # 微软翻译
        "Lao",  # AI翻译
        "lo",  # 阿里
        "lo",  # qwen-tts
    ],
    "my": [
        "my",  # google通道
        "mya",  # 字幕嵌入语言
        "bur",  # 百度通道
        "MY",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "my",  # 微软翻译
        "Burmese",  # AI翻译
        "my",  # 阿里
        "my",  # qwen-tts
    ],
    # 南亚
    "hi": [
        "hi",
        "hin",
        "hi",
        "HI",
        "No",
        "hi",
        "hi",
        "Hindi",
        "hi",
        "hi",
    ],
    "ur": [
        "ur",  # google通道
        "urd",  # 字幕嵌入语言
        "ur",  # 百度通道
        "UR",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "ur",  # 微软翻译
        "Urdu",  # AI翻译
        "ur",  # 阿里
        "ur",
    ],
    "bn": [
        "bn",  # google通道
        "ben",  # 字幕嵌入语言
        "ben",  # 百度通道
        "BN",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "bn",  # 微软翻译
        "Bengali",  # AI翻译,
        "bn",
        "bn",
    ],
    # 中东 中亚
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
        "ar",
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
        "tr",
    ],
    "fa": [
        "fa",  # google通道
        "fas",  # 字幕嵌入语言
        "per",  # 百度通道
        "FA",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "fa",  # 微软翻译
        "Persian",  # AI翻译
        "fa",  # 阿里
        "fa",
    ],
    "kk": [
        "kk",
        "kaz",
        "No",
        "KK",
        "No",
        "No",
        "kk",
        "Kazakh",
        "kk",
        "kk",
    ],
    "uz": [
        "uz",  # google通道
        "uzb",  # 字幕嵌入语言
        "No",  # 百度通道
        "UZ",  # deepl deeplx通道
        "No",  # 腾讯通道
        "uz",  # OTT通道
        "uz",  # 微软翻译
        "Uzbek",  # AI翻译
        "uz",  # 阿里
        "uz",  # qwen-mt
    ],
    "az": [
        "az",  # google通道
        "aze",  # 字幕嵌入语言
        "No",  # 百度通道
        "No",  # deepl deeplx通道
        "No",  # 腾讯通道
        "No",  # OTT通道
        "az",  # 微软翻译
        "Azerbaijani",  # AI翻译
        "No",  # 阿里
        "Azerbaijani",  # qwen-mt qwen-tts qwen-asr
        "az"  # m2m100
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
        "he",
    ],
    'af': ['af', 'afr', 'afr', 'AF', 'No', 'No', 'af', 'Afrikaans', 'af', 'af'],
    'sq': ['sq', 'sqi', 'alb', 'SQ', 'No', 'No', 'sq', 'Albanian', 'sq',
           'sq'], 'am': ['am', 'amh', 'amh', 'No', 'No', 'No', 'am', 'Amharic', 'am', 'No'],
    'az': ['az', 'aze', 'aze', 'AZ', 'No', 'No', 'az', 'Azerbaijani',
           'az', 'az'], 'bs': ['bs', 'bos', 'bos', 'BS', 'No', 'No', 'bs', 'Bosnian', 'bs', 'bs'],
    'ca': ['ca', 'cat', 'cat', 'CA', 'No', 'No', 'ca', 'Catalan', 'ca', 'ca'],
    'hr': ['hr', 'hrv', 'hrv', 'HR', 'No', 'No', 'hr', 'Croatian', 'hbs', 'hr'],
    'da': ['da', 'dan', 'dan', 'DA', 'No', 'No', 'da', 'Danish', 'da', 'da'],
    'et': ['et', 'est', 'est', 'ET', 'No', 'No', 'et', 'Estonian', 'et', 'et'],
    'gl': ['gl', 'glg', 'glg', 'GL', 'No', 'No', 'gl', 'Galician', 'gl', 'gl'],
    'ka': ['ka', 'kat', 'geo', 'KA', 'No', 'No', 'ka', 'Georgian', 'ka', 'ka'],
    'gu': ['gu', 'guj', 'guj', 'GU', 'No', 'No', 'gu', 'Gujarati', 'gu', 'gu'],
    'is': ['is', 'isl', 'ice', 'IS', 'No', 'No', 'is', 'Icelandic', 'is', 'is'],
    'iu': ['iu', 'iku', 'iku', 'No', 'No', 'No', 'iu', 'Inuktitut', 'iu', 'No'],
    'ga': ['ga', 'gle', 'gle', 'GA', 'No', 'No', 'ga', 'Irish', 'ga', 'No'],
    'jv': ['jv', 'jav', 'jav', 'JV', 'No', 'No', 'jav', 'Javanese', 'jv', 'jv'],
    'kn': ['kn', 'kan', 'kan', 'No', 'No', 'No', 'kn', 'Kannada', 'kn', 'kn'],
    'lv': ['lv', 'lav', 'lav', 'LV', 'No', 'No', 'lv', 'Latvian', 'lv', 'lv'],
    'lt': ['lt', 'lit', 'lit', 'LT', 'No', 'No', 'lt', 'Lithuanian', 'lt', 'lt'],
    'mk': ['mk', 'mkd', 'mac', 'MK', 'No', 'No', 'mk', 'Macedonian', 'mk', 'mk'],
    'ml': ['ml', 'mal', 'mal', 'ML', 'No', 'No', 'ml', 'Malayalam', 'ml', 'No'],
    'mt': ['mt', 'mlt', 'mlt', 'MT', 'No', 'No', 'mt', 'Maltese', 'mt', 'mt'],
    'mr': ['mr', 'mar', 'mar', 'MR', 'No', 'No', 'mr', 'Marathi', 'mr', 'mr'],
    'mn': ['mn', 'mon', 'No', 'MN', 'No', 'No', 'mn-Mong', 'Mongolian', 'mn', 'No'],
    'ne': ['ne', 'nep', 'nep', 'NE', 'No', 'No', 'ne', 'Nepali', 'ne', 'ne'],
    'ps': ['ps', 'pus', 'pus', 'PS', 'No', 'No', 'ps', 'Pashto', 'ps', 'No'],
    'sr': ['sr', 'srp', 'srp', 'SR', 'No', 'No', 'sr-Cyrl', 'Serbian', 'No', 'sr'],
    'si': ['si', 'sin', 'sin', 'No', 'No', 'No', 'si', 'Sinhala', 'si', 'si'],
    'sk': ['sk', 'slk', 'sk', 'SK', 'No', 'No', 'sk', 'Slovak', 'sk', 'sk'],
    'sl': ['sl', 'slv', 'slo', 'SL', 'No', 'No', 'sl', 'Slovenian', 'sl', 'sl'],
    'so': ['so', 'som', 'som', 'No', 'No', 'No', 'so', 'Somali', 'so', 'No'],
    'su': ['su', 'sun', 'sun', 'SU', 'No', 'No', 'su', 'Sundanese', 'su', 'No'],
    'sw': ['sw', 'swa', 'swa', 'SW', 'No', 'No', 'sw', 'Swahili', 'sw', 'sw'],
    'ta': ['ta', 'tam', 'tam', 'TA', 'No', 'No', 'ta', 'Tamil', 'ta', 'ta'],
    'te': ['te', 'tel', 'tel', 'TE', 'No', 'No', 'te', 'Telugu', 'te', 'te'],
    'cy': ['cy', 'cym', 'wel', 'CY', 'No', 'No', 'cy', 'Welsh', 'cy', 'cy'],
    'zu': ['zu', 'zul', 'zul', 'ZU', 'No', 'No', 'zu', 'Zulu',
           'zu', 'No'],

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
    ]
}


# 合并自定义语言
def _merge_newlang():
    from ._paths import ROOT_DIR
    _f = f'{ROOT_DIR}/videotrans/languages.json'
    if Path(_f).exists():
        try:
            _newlang = json.loads(Path(_f).read_text(encoding='utf-8'))
            if _newlang:
                LANG_CODE.update(_newlang)
        except Exception as e:
            logging.getLogger('VideoTrans').exception(f'加载自定义语言数据失败：{e}', exc_info=True)
    else:
        Path(_f).write_text('{}', encoding='utf-8')


_merge_newlang()
