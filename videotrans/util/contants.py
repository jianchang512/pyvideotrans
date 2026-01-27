# 各种字面常量
LISTEN_TEXT={
        "zh": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
        "zh-cn": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
        "zh-tw": "你好啊，我親愛的朋友，希望你的每一天都是美好愉快的！",
        "en": "Hello, my dear friend. I hope your every day is beautiful and enjoyable!",
        "fr": "Bonjour mon cher ami. J'espère que votre quotidien est beau et agréable !",
        "de": "Hallo mein lieber Freund. Ich hoffe, dass Ihr Tag schön und angenehm ist!",
        "ja": "こんにちは私の親愛なる友人。 あなたの毎日が美しく楽しいものでありますように！",
        "ko": "안녕, 내 사랑하는 친구. 당신의 매일이 아름답고 즐겁기를 바랍니다!",
        "ru": "Привет, мой дорогой друг. Желаю, чтобы каждый твой день был прекрасен и приятен!",
        "es": "Hola mi querido amigo. ¡Espero que cada día sea hermoso y agradable!",
        "th": "สวัสดีเพื่อนรัก. ฉันหวังว่าทุกวันของคุณจะสวยงามและสนุกสนาน!",
        "it": "Ciao caro amico mio. Spero che ogni tuo giorno sia bello e divertente!",
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

}
# 不使用代理的域名
no_proxy = (
    "tmt.tencentcloudapi.com,"
    "hf-mirror.com,"
    "api.fanyi.baidu.com,"
    "openspeech.bytedance.com,"
    "api.minimaxi.com,"
    "api.deepseek.com,"
    "modelscope.cn,"  # 涵盖了 *.modelscope.cn
    "aliyuncs.com,"  # 涵盖了 dashscope, mt.cn-hangzhou 等所有子域
    "api.siliconflow.cn,"
    "ms.show,"  # 涵盖 *.ms.show
    "bigmodel.cn,"
    "localhost,"
    "tts.speech.microsoft.com,"
    "127.0.0.1,"
    "127.0.0.1:7860,"
    "localhost:7860,"
    "127.0.0.1:9880,"
    "localhost:9880,"
    "127.0.0.1:8000,"
    "localhost:8000,"
    "127.0.0.1:5051,"
    "127.0.0.1:5052,"
    "127.0.0.1:5053,"
    "127.0.0.1:9091,"
    "127.0.0.1:9092,"
    "127.0.0.1:9093"
)

# funasr模型
FUNASR_MODEL = ['Fun-ASR-Nano-2512', 'Fun-ASR-MLT-Nano-2512', 'paraformer-zh', 'SenseVoiceSmall']
# deepgram 支持的语音识别模型
DEEPGRAM_MODEL = [
    "nova-3",
    "whisper-large",
    "whisper-medium",
    "whisper-small",
    "whisper-base",
    "whisper-tiny",
    "nova-2",
    "enhanced",
    "base",
]

# 支持的视频格式
VIDEO_EXTS = ["mp4", "mkv", "mpeg", "avi", "mov", "mts", "webm", "ogg", "ts", "flv"]
# 支持的音频格式
AUDIO_EXITS = ["mp3", "wav", "aac", "flac", "m4a"]

# 缺省 gemini 模型
DEFAULT_GEMINI_MODEL = "gemini-3-pro-preview,gemini-3-flash-preview,gemini-2.5-pro,gemini-2.5-flash,gemini-2.0-flash,gemini-2.0-flash-lite"
# openai-tts音色
OPENAITTS_ROLES = "No,alloy,ash,ballad,coral,echo,fable,onyx,nova,sage,shimmer,verse"
# gemini-tts 音色
GEMINITTS_ROLES = "No,Zephyr,Puck,Charon,Kore,Fenrir,Leda,Orus,Aoede,Callirrhoe,Autonoe,Enceladus,Iapetus,Umbriel,Algieba,Despina,Erinome,Algenib,Rasalgethi,Laomedeia,Achernar,Alnilam,Schedar,Gacrux,Pulcherrima,Achird,Zubenelgenubi,Vindemiatrix,Sadachbia,Sadaltager,Sulafat"
