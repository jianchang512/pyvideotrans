# 各种字面常量
LISTEN_TEXT={
        "zh": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
        "zh-cn": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
        "zh-tw": "你好啊，我親愛的朋友，希望你的每一天都是美好愉快的！",
        "nb": "Hallo, min kjære venn, jeg håper hver dag din er fantastisk og gledelig.",
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

}
FASTER_MODELS_DICT= {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "tiny": "Systran/faster-whisper-tiny",
    "base.en": "Systran/faster-whisper-base.en",
    "base": "Systran/faster-whisper-base",
    "small.en": "Systran/faster-whisper-small.en",
    "small": "Systran/faster-whisper-small",
    "medium.en": "Systran/faster-whisper-medium.en",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}

# 不使用代理的域名
_no_proxy_list = [
    # --- 腾讯云 ---
    "tencentcloudapi.com", ".tencentcloudapi.com",
    
    # --- HuggingFace ---
    "hf-mirror.com", ".hf-mirror.com",
    
    # --- 百度 (包含 fanyi.baidu 等所有子域) ---
    "baidu.com", ".baidu.com",
    
    # --- 字节跳动 (包含 openspeech 等所有子域) ---
    "bytedance.com", ".bytedance.com",".volces.com","volces.com",
    
    # --- MiniMax ---
    "api.minimaxi.com", ".minimaxi.com",

    # --- DeepSeek ---
    "api.deepseek.com", ".deepseek.com",

    # --- ModelScope ---
    "modelscope.cn", ".modelscope.cn",

    # --- 阿里云 (包含 dashscope, aliyuncs 等) ---
    "aliyuncs.com", ".aliyuncs.com",

    # --- SiliconFlow ---
    "siliconflow.cn", ".siliconflow.cn",


    "ms.show", ".ms.show",
    "bigmodel.cn", ".bigmodel.cn",
    #"microsoft.com", ".microsoft.com", # 涵盖 tts.speech.microsoft.com

    # --- 本地回环 (涵盖所有端口：7860, 8000, 9880, 5051等) ---
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
]
no_proxy = ",".join(_no_proxy_list)

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
AUDIO_EXITS = ["mp3", "wav", "aac", "flac", "m4a","ogg"]

ChatTTS_VOICE="11,12,16,2222,4444,6653,7869,9999,5,13,14,1111,3333,4099,5099,5555,8888,6666,7777"
# openai-tts音色
OPENAITTS_ROLES = "No,alloy,ash,ballad,coral,echo,fable,onyx,nova,sage,shimmer,verse"
XAITTS_ROLES='eve,ara,rex,sal,leo'
MITTS_ROLES='mimo_default,default_zh,default_en'
# 缺省 gemini 模型
DEFAULT_GEMINI_MODEL = "gemini-pro-latest,gemini-flash-latest,gemini-2.5-pro,gemini-2.5-flash,gemini-2.0-flash"
# gemini-tts 音色
GEMINITTS_ROLES = "No,Zephyr,Puck,Charon,Kore,Fenrir,Leda,Orus,Aoede,Callirrhoe,Autonoe,Enceladus,Iapetus,Umbriel,Algieba,Despina,Erinome,Algenib,Rasalgethi,Laomedeia,Achernar,Alnilam,Schedar,Gacrux,Pulcherrima,Achird,Zubenelgenubi,Vindemiatrix,Sadachbia,Sadaltager,Sulafat"

GEMINI_TTS_MODELS=[ "gemini-3.1-flash-tts-preview","gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts" ]

Whisper_cpp_models="ggml-tiny.bin,ggml-base.bin,ggml-small.bin,ggml-medium.bin,ggml-large-v1.bin,ggml-large-v2.bin,ggml-large-v3.bin,ggml-large-v3-turbo.bin"
Whisper_net_models=Whisper_cpp_models
Qwenmt_Model="qwen3.6-plus,qwen3.6-flash,qwen3-max,qwen-mt-turbo,qwen-mt-plus,qwen-mt-flash,qwen-mt-lite,qwen3-asr-flash,qwen3-asr-flash-filetrans"
Qwentts_Models='qwen3-tts-vd-2026-01-26,qwen3-tts-instruct-flash,qwen3-tts-flash'
Qpenaitts_Model="tts-1,tts-1-hd,gpt-4o-mini-tts"

Openairecognapi_Model= "whisper-1,gpt-4o-transcribe,gpt-4o-mini-transcribe,gpt-4o-transcribe-diarize"

Chatgpt_Model="gpt-5.5,gpt-5.5-pro,gpt-5.4-pro,gpt-5.4,gpt-5.4-mini,gpt-5,gpt-5-mini,gpt-4.1"
Azure_Model="gpt-5.5,gpt-5.4-mini, gpt-5.4-nano, gpt-5.4, gpt-5.4-pro,gpt-5.1, gpt-5.1-chat"
Localllm_Model="qwen3.6,deepseek-v4-flash:cloud"
Zhipuai_Model= "glm-5.1,glm-5, glm-4.7, glm-4.7-flash, glm-4.7-flashx, glm-4.6, glm-4.5-air, glm-4.5-airx, glm-4.5-flash"

Deepseek_Model="deepseek-v4-pro,deepseek-v4-flash"
Openrouter_Model="minimax/minimax-m2.7,z-ai/glm-5,qwen/qwen3-max-thinking,moonshotai/kimi-k2.5,google/gemini-3-flash-preview"
Guiji_Model="Pro/zai-org/GLM-5.1,Pro/zai-org/GLM-5,Pro/moonshotai/Kimi-K2.6,Qwen/Qwen3.6-35B-A3B,MiniMaxAI/MiniMax-M2.5"
Ai302_Models="deepseek-v4-pro,deepseek-v4-flash"
Zijiehuoshan_Model="doubao-seed-2-0-pro-260215,doubao-seed-2-0-lite-260215,doubao-seed-2-0-mini-260215"
Whisper_Models="tiny,tiny.en,base,base.en,small,small.en,medium,medium.en,large-v3-turbo,large-v1,large-v2,large-v3,distil-large-v3,distil-large-v3.5"
Openai_Whisper_Models=["tiny","tiny.en","base","base.en","small","small.en","medium","medium.en","large-v3-turbo","large-v1","large-v2","large-v3"]
MINIMAX_MODELS="MiniMax-M2.7,MiniMax-M2.7-highspeed,MiniMax-M2.5,MiniMax-M2.5-highspeed"
MINIMAX_TTS_MODELS=["speech-2.8-hd","speech-2.8-turbo","speech-2.6-hd","speech-2.6-turbo","speech-02-hd","speech-02-turbo"]


ELEVENLABS_TTS_MODELS="eleven_v3,eleven_flash_v2_5,eleven_flash_v2,eleven_multilingual_v2,eleven_multilingual_v1"