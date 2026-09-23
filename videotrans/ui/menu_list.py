from videotrans.configure._i18n import tr

# list中一个tuple是一个菜单
# 0:键名([a-zA-Z][a-zA-Z0-9_]+)
# 1: 菜单显示名称
# 2:
#   None:点击菜单时调用 winform.{键名}模块。
#   False: 什么也不做
#   http开头的url地址:在浏览器中打开
#   其他字符串: 弹窗

# 菜单--翻译设置，每个  tuple 是一个菜单，
MENU_CFG_TRANS = [
    ("deepseek", 'DeepSeek', None),
    ("chatgpt", tr("OpenAI API & Compatible AI"), None),
    ("gemini", "Gemini AI", None),
    ("localllm", tr("Local LLM API"), None),
    ("zijiehuoshan", tr("ByteDance Ark"), None),
    ("zhipuai", tr("Zhipu AI"), None),

    ("minimaxi", "Minimaxi AI", None),

    ("qwenmt", tr('Ali Qwen3-ASR'), None),
    ("azure", tr("AzureOpenAI Translation"), None),
    ("openrouter", 'OpenRouter.AI', None),
    ("siliconflow", tr("SiliconFlow"), None),
    ("ai302", "302.AI", None),
    ("litellm", 'LiteLLM', None),
    ("cambtts", "CAMB.AI", None),
    ("api_route", 'API-ROUTE.com', None),
    ("cheaperinference", 'Cheaper Inference', None),

    ("deepL", "DeepL API", None),
    ("deepLX", "DeepLX API", None),
    ("tencent", tr("Tencent Key"), None),
    ("baidu", tr("Baidu"), None),
    ("ali", tr("Alibaba Translation"), None),
    ("libre", "LibreTranslate API", None),
    ("transapi", tr("Transate API"), None),
]

# 菜单--TTS设置，每个  tuple 是一个菜单，

MENU_CFG_TTS = [

    # tts
    ("refaudio", tr("Set reference audio"), None),

    ("openaitts", "OpenAI TTS", None),
    ("doubao2", tr("DouBao2"), None),
    ("xiaomi", tr("XiaoMi"), None),
    ("qwentts", f"{tr('Ali-Bailian')}/Qwen3-TTS", None),


    ("xaitts", "X.AI TTS", None),
    ("elevenlabs", "ElevenLabs.io", None),
    ("azuretts", tr("AzureAI TTS"), None),

    ("gptsovits", "GPT-SoVITS", None),
    ("gradiowin", "Index/VoxCPM/SparK/FireRed3", None),
    ("chatterbox", "ChatterBox-TTS", None),
    ("cosyvoice", "CosyVoice-TTS", None),
    ("chattts", "ChatTTS", None),
    ("kokoro", "Kokoro-TTS", None),
    ("fishtts", "Fish-TTS", None),
    ("clone", tr("Clone-Voice TTS"), None),

    ("qwenttslocal", f"Qwen3 TTS({tr('Local')})", None),
    ("ttsapi", tr("TTS API"), None),
]
# 菜单--语音识别设置，每个  tuple 是一个菜单，

MENU_CFG_STT = [

    # 语音识别
    ("openairecognapi", tr("OpenAI Speech to Text API"), None),
    ("zijierecognmodel", tr("VolcEngine STT"), None),
    ("parakeet", 'Nvidia parakeet-tdt', None),
    ("whisperxapi", 'WhisperX-API', None),
    ("deepgram", tr("Deepgram Speech Recognition API"), None),
    ("set_xxl", 'Faster_Whisper_XXL.exe', None),
    ("sttapi", tr("STT Speech Recognition API"), None),
    ("recognapi", tr("Custom Speech Recognition API"), None),
]

# 菜单--工具/选项，每个  tuple 是一个菜单，

MENU_CFG_TOOLS = [

    # 工具选项
    ("setini", tr("Options"), None),

    ("clip_video", tr("Edit video on subtitles"), None),
    ("realtime_stt", tr("Real-time speech-to-text"), None),
    ("textmatching", tr("Text matching and timing"), None),
    ("formatsrtfiles", tr("Batch create folder structure"), None),

    ("fn_audiofromvideo", tr("Separate Video to audio"), None),
    ("fn_separate", tr("Vocal & instrument Separate"), None),

    ("fn_hebingsrt", tr("Combine Two Subtitles"), None),
    ("fn_videoandaudio", tr("Batch video/audio merger"), None),
    ("fn_videoandsrt", tr("Batch Video Srt merger"), None),
    ("fn_hunliu", tr("Mixing 2 Audio Streams"), None),

    ("fn_formatcover", tr("Batch Audio/Video conver"), None),
    ("fn_subtitlescover", tr("Conversion Subtitle Format"), None),
    ("fn_watermark", tr("Add watermark to video"), None),
]
# 菜单--帮助，每个  tuple 是一个菜单，
MENU_CFG_HELP = [
    # 帮助
    ("website", tr("Documents"), "https://pyvideotrans.com"),
    ("bbs", tr("Having problems? Ask"), "https://bbs.pyvideotrans.com"),
    ("git", "Github Repository", "https://github.com/jianchang512/pyvideotrans"),
    ("issue", tr("Post issue"), "https://github.com/jianchang512/pyvideotrans/issues"),
    ("download", tr("Solution to model download failure"), "https://pyvideotrans.com/allmodels"),
    ("cuda", 'CUDA & cuDNN', "https://pyvideotrans.com/gpu"),

    ("ffmpeg", "FFmpeg", "https://www.ffmpeg.org/download.html"),
    ("ocrsp", tr("Download Hard Subtitle Extraction Software"), "https://pyvideotrans.com/ocrsp"),

    ("lawalert", tr("Disclaimer"), None),
    ("info", tr("Donating developers"), None),
]

# 主界面左侧面板菜单，每个  tuple 是一个菜单，
MENU_CFG_PANEL = [
    # 左侧菜单
    ("action_biaozhun", tr("Standard Function Mode"), False),
    ("action_tiquzimu", tr("Extract Srt And Translate"), False),
    ("fn_recogn", tr("Speech Recognition Text"), None),
    ("fn_peiyin", tr("From  Text  Into  Speech"), None),
    ("fn_fanyisrt", tr("Text  Or Srt  Translation"), None),
    ("fn_peiyinrole", tr("Multi voice dubbing for SRT"), None),
    ("fn_vas", tr("Video Subtitles Merging"), None),
]
