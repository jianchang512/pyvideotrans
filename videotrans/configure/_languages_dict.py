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
EDGE_LANGUANGES_CODE = ['zh-cn', 'en', 'ja', 'ko', 'zh-tw', 'yue', 'fr', 'de', 'es', 'es-419', 'pt', 'pt-br', 'it',
                        'ru', 'hu', 'pl', 'nl', 'sv', 'uk', 'cs', 'el', 'nb', 'ro', 'bg', 'fi', 'vi', 'th', 'id', 'ms',
                        'fil', 'km', 'lo', 'my', 'hi', 'ur', 'bn', 'ar', 'tr', 'fa', 'kk', 'uz', 'he', 'af', 'sq', 'am',
                        'az', 'bs', 'ca', 'hr', 'da', 'et', 'gl', 'ka', 'gu', 'is', 'iu', 'ga', 'jv', 'kn', 'lv', 'lt',
                        'mk', 'ml', 'mt', 'mr', 'mn', 'ne', 'ps', 'sr', 'si', 'sk', 'sl', 'so', 'su', 'sw', 'ta', 'te',
                        'cy', 'zu']

# key 需同 videotrans/languages/*.json中译文value一致，否则无法根据界面显示获取到 edge-tts/gtts 不在 LANG_CODE 中的语言代码，进而无法获取到试听文本
EDGET_LANGUAGES_NAME2CODE = {
    "中文": "zh",
    "简体中文": "zh-cn",
    "繁体中文": "zh-tw",
    "粤语": "yue",
    "英语": "en",
    "法语": "fr",
    "德语": "de",
    "日语": "ja",
    "韩语": "ko",
    "俄语": "ru",
    "西班牙语": "es",
    "泰国语": "th",
    "意大利语": "it",
    "葡萄牙语": "pt",
    "越南语": "vi",
    "阿拉伯语": "ar",
    "土耳其语": "tr",
    "印度语": "hi",
    "匈牙利语": "hu",
    "乌克兰语": "uk",
    "印度尼西亚": "id",
    "马来语": "ms",
    "哈萨克语": "kk",
    "捷克语": "cs",
    "波兰语": "pl",
    "荷兰语": "nl",
    "瑞典语": "sv",
    "希伯来语": "he",
    "孟加拉语": "bn",
    "菲律宾语": "fil",
    "南非荷兰语": "af",
    "阿尔巴尼亚语": "sq",
    "阿姆哈拉语": "am",
    "阿塞拜疆语": "az",
    "波斯尼亚语": "bs",
    "保加利亚语": "bg",
    "缅甸语": "my",
    "加泰罗尼亚语": "ca",
    "克罗地亚语": "hr",
    "丹麦语": "da",
    "爱沙尼亚语": "et",
    "芬兰语": "fi",
    "加利西亚语": "gl",
    "格鲁吉亚语": "ka",
    "希腊语": "el",
    "古吉拉特语": "gu",
    "冰岛语": "is",
    "因纽特语": "iu",
    "爱尔兰语": "ga",
    "爪哇语": "jv",
    "卡纳达语": "kn",
    "高棉语": "km",
    "老挝语": "lo",
    "拉脱维亚语": "lv",
    "立陶宛语": "lt",
    "马其顿语": "mk",
    "马拉雅拉姆语": "ml",
    "马耳他语": "mt",
    "马拉地语": "mr",
    "蒙古语": "mn",
    "尼泊尔语": "ne",
    "挪威语(书面挪威语)": "nb",
    "普什图语": "ps",
    "波斯语": "fa",
    "罗马尼亚语": "ro",
    "塞尔维亚语": "sr",
    "僧伽罗语": "si",
    "斯洛伐克语": "sk",
    "斯洛文尼亚语": "sl",
    "索马里语": "so",
    "巽他语": "su",
    "斯瓦希里语": "sw",
    "泰米尔语": "ta",
    "泰卢固语": "te",
    "乌尔都语": "ur",
    "乌兹别克语": "uz",
    "威尔士语": "cy",
    "祖鲁语": "zu",
    "葡萄牙语(巴西)": "pt-br",
    "西班牙语(拉美)": "es-419",
}
# 英语形式
EDGET_LANGUAGES_NAME2CODE_EN = {
    "Chinese": "zh",
    "Simplified Chinese": "zh-cn",
    "Traditional Chinese": "zh-tw",
    "Cantonese": "yue",
    "English": "en",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Korean": "ko",
    "Russian": "ru",
    "Spanish": "es",
    "Thai": "th",
    "Italian": "it",
    "Portuguese": "pt",
    "Vietnamese": "vi",
    "Arabic": "ar",
    "Turkish": "tr",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Ukrainian": "uk",
    "Indonesian": "id",
    "Malay": "ms",
    "Kazakh": "kk",
    "Czech": "cs",
    "Polish": "pl",
    "Dutch": "nl",
    "Swedish": "sv",
    "Hebrew": "he",
    "Bengali": "bn",
    "Filipino": "fil",
    "Afrikaans": "af",
    "Albanian": "sq",
    "Amharic": "am",
    "Azerbaijani": "az",
    "Bosnian": "bs",
    "Bulgarian": "bg",
    "Burmese": "my",
    "Catalan": "ca",
    "Croatian": "hr",
    "Danish": "da",
    "Estonian": "et",
    "Finnish": "fi",
    "Galician": "gl",
    "Georgian": "ka",
    "Greek": "el",
    "Gujarati": "gu",
    "Icelandic": "is",
    "Inuktitut": "iu",
    "Irish": "ga",
    "Javanese": "jv",
    "Kannada": "kn",
    "Khmer": "km",
    "Lao": "lo",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Macedonian": "mk",
    "Malayalam": "ml",
    "Maltese": "mt",
    "Marathi": "mr",
    "Mongolian": "mn",
    "Nepali": "ne",
    "Norwegian (Bokmål)": "nb",
    "Pashto": "ps",
    "Persian": "fa",
    "Romanian": "ro",
    "Serbian": "sr",
    "Sinhala": "si",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Somali": "so",
    "Sundanese": "su",
    "Swahili": "sw",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur",
    "Uzbek": "uz",
    "Welsh": "cy",
    "Zulu": "zu",
    "Portuguese (Brazilian)": "pt-br",
    "Spanish (Latin America)": "es-419"
}

EDGET_LANGUAGES_NAME2CODE.update(EDGET_LANGUAGES_NAME2CODE_EN)
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
        "es",  # google
        "spa",
        "spa",  # baidu
        "ES-419",  # deepl
        "es",  # 腾讯
        "es",  # ott
        "es",  # 微软
        "Spanish",  # AI
        "es",  # 阿里机器
        "Spanish",  # qwenmt
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
        "por",  # 字幕
        "pot",  # 百度
        "PT-BR",  # deepl
        "pt",  # 腾讯
        "pt",  # ott
        "pt",  # 微软
        "Portuguese (Brazilian)",  # AI
        "pt",  # 阿里
        "Portuguese (Brazilian)",  # qwen-mt
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
        "Romanian",  # qwen-mt
        "ro"  # m2m100
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
    "fi": [
        "fi",  # google通道
        "fin",  # 字幕嵌入语言
        "fin",  # 百度通道
        "FI",  # deepl deeplx通道
        "fi",  # 腾讯通道
        "fi",  # OTT通道
        "fi",  # 微软翻译
        "Finnish",  # AI翻译
        "fi",  # 阿里
        "Finnish",  # qwen-tts 
        "fi"  # m2m100
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
        "Lao",  # qwen-tts
        "lo"  # m2m100
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
        "Burmese",  # qwen-tts
        "my"  # m2m100
    ],
    # 南亚
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
        "No",
        "KK",
        "kk",
        "No",
        "kk",
        "Kazakh",
        "kk",
        "Kazakh",
        "kk"  # m2m100
    ],
    "uz": [
        "uz",  # google通道
        "uzb",  # 字幕嵌入语言
        "No",  # 百度通道
        "UZ",  # deepl deeplx通道
        "uz",  # 腾讯通道
        "uz",  # OTT通道
        "uz",  # 微软翻译
        "Uzbek",  # AI翻译
        "uz",  # 阿里
        "Northern Uzbek",  # qwen-mt qwen-tts qwen-asr
        "uz"  # m2m100
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
