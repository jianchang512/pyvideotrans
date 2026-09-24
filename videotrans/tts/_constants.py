from videotrans import ChannelProvider
from videotrans.configure._i18n import tr
"""
如果想新增渠道
1. 定义一个常量，值为以下递增的序号
2. 在 ID_NAME_DICT 中新增一个键值对，键为新增的常量，值是 ChannelProvider 实例
3. 当前目录下定义一个实际实现代码文件，可直接复制已有渠道文件
"""

# 免费推荐
EDGE_TTS = 0

# 本地内置
QWEN3LOCAL_TTS = 1
F5_TTS = 2
OMNIVOICE_TTS = 3
CONFUCIUS_TTS = 4
MOSS_TTS = 5
ZIPVOICE_TTS = 6
PIPER_TTS = 7
CHATTERBOX_TTS = 8
Supertonic_TTS = 9
VITSCNEN_TTS = 10
HIGGS_AUDIO_TTS = 11

# 本地 API
INDEX_TTS = 12
GPTSOVITS_TTS = 13
COSYVOICE_TTS = 14
VOXCPM_TTS = 15
FIRERED3_TTS = 16

# 云 API
DOUBAO2_TTS = 17
QWEN_TTS = 18
XIAOMI_TTS = 19
GLM_TTS = 20
MINIMAXI_TTS = 21

# 海外 API
OPENAI_TTS = 22
GEMINI_TTS = 23
ELEVENLABS_TTS = 24
XAI_TTS = 25
G_TTS = 26

# 本地 API
CHATTTS = 27
SPARK_TTS = 28
KOKORO_TTS = 29
FISHTTS = 30

# 不推荐
CLONE_VOICE_TTS = 31
# 在线API
AZURE_TTS = 32
AI302_TTS = 33
CAMB_TTS = 34

#自定义API
TTS_API = 35
# 在线API
SILICONFLOW_API = 36
OPENROUTER_API = 37

# 支持克隆的渠道，即存在 clone 配音角色
SUPPORT_CLONE = [
    COSYVOICE_TTS,
    CLONE_VOICE_TTS,
    F5_TTS,
    HIGGS_AUDIO_TTS,
    INDEX_TTS,
    VOXCPM_TTS,
    SPARK_TTS,
    CHATTERBOX_TTS,
    GPTSOVITS_TTS,
    QWEN3LOCAL_TTS,
    CAMB_TTS,
    OMNIVOICE_TTS,
    MOSS_TTS,
    CONFUCIUS_TTS,
    FIRERED3_TTS,
    ZIPVOICE_TTS
]
# 本地内置，在单视频模式下 校对配音时，对 is_redubb 特殊处理
LOCAL_BUILTIN = [
    QWEN3LOCAL_TTS,
    F5_TTS,
    HIGGS_AUDIO_TTS,
    OMNIVOICE_TTS,
    CONFUCIUS_TTS,
    MOSS_TTS,
    ZIPVOICE_TTS,
    PIPER_TTS,
    CHATTERBOX_TTS,
    Supertonic_TTS,
    VITSCNEN_TTS
]

# 配音角色根据语言不同而变化的渠道
CHANGE_BY_LANGUAGE = [EDGE_TTS, MINIMAXI_TTS, AZURE_TTS, DOUBAO2_TTS, AI302_TTS, KOKORO_TTS,
                      PIPER_TTS, VITSCNEN_TTS]

# 渠道id对应的设置窗口和sk键名,
# key_name: 存储 SK 或 api url的键，通过 app_cfg.params 调用，如果不存在该值，在使用时报错未填写
# win: 对应 winform 包中的文件名及 ui 包中的文件名，用于调用打开设置窗口
# imp 为该渠道实际代码文件，位于当前目录下
ID_NAME_DICT = {
    EDGE_TTS: ChannelProvider(tr("Edge-TTS(free)"), imp="._edgetts"),
    QWEN3LOCAL_TTS: ChannelProvider(f"Qwen3-TTS({tr('Built-in')})", imp="._qwenttslocal"),
    F5_TTS: ChannelProvider(f"F5-TTS({tr('Built-in')})", imp="._f5tts"),
    OMNIVOICE_TTS: ChannelProvider(f"OmniVoice({tr('Built-in')})", imp="._omnivoice"),
    CONFUCIUS_TTS: ChannelProvider(f"Confucius4({tr('Built-in')})", imp="._confuciustts"),
    MOSS_TTS: ChannelProvider(f"MOSS-TTS-Nano({tr('Built-in')})", imp="._mosstts"),
    ZIPVOICE_TTS: ChannelProvider(f"{tr('ZipVoice')}({tr('Built-in')})", imp="._zipvoice"),
    PIPER_TTS: ChannelProvider(f"Piper({tr('Built-in')})", imp="._piper"),
    CHATTERBOX_TTS: ChannelProvider(f"ChatterBox({tr('Built-in')})", imp="._chatterbox", win="chatterbox"),
    Supertonic_TTS: ChannelProvider(f"Supertonic3({tr('Built-in')})", imp="._supertonic"),
    VITSCNEN_TTS: ChannelProvider(f"{tr('VITS')}({tr('Built-in')})", imp="._vits"),
    HIGGS_AUDIO_TTS: ChannelProvider(f"Higgs-audio-v3({tr('Built-in')})", imp="._higgs"),

    INDEX_TTS: ChannelProvider(f"Index-TTS({tr('Local')}API)", imp="._index", key_name="indextts_url", win="gradiowin"),
    GPTSOVITS_TTS: ChannelProvider(f"GPT-SoVITS({tr('Local')}API)", imp="._gptsovits", key_name="gptsovits_url",
                                   win="gptsovits"),
    COSYVOICE_TTS: ChannelProvider(f"CosyVoice({tr('Local')}API)", imp="._cosyvoice", key_name="cosyvoice_url",
                                   win="cosyvoice"),
    VOXCPM_TTS: ChannelProvider(f"VoxCPM({tr('Local')}API)", imp="._voxcpm", key_name="voxcpmtts_url", win="gradiowin"),
    FIRERED3_TTS: ChannelProvider(f"FireRed3({tr('Local')}API)", imp="._firered3tts", key_name="firered3tts_url",
                                  win="gradiowin"),

    DOUBAO2_TTS: ChannelProvider(tr("DouBao2"), imp="._doubao2", key_name="doubao2_access", win="doubao2"),
    QWEN_TTS: ChannelProvider(f"{tr('Ali-Bailian')}/Qwen3-TTS", imp="._qwentts", key_name="qwentts_key", win="qwentts"),
    XIAOMI_TTS: ChannelProvider(tr('XiaoMi'), imp="._xiaomi", key_name="xiaomi_key", win="xiaomi"),
    GLM_TTS: ChannelProvider(f'GLM TTS {tr("Zhipu AI")}', imp="._glmtts", key_name="zhipu_key", win="zhipuai"),
    MINIMAXI_TTS: ChannelProvider("Minimaxi TTS", imp="._minimaxi", key_name="minimaxi_apikey", win="minimaxi"),

    OPENAI_TTS: ChannelProvider("OpenAI TTS", imp="._openaitts", key_name="openaitts_key", win="openaitts"),
    GEMINI_TTS: ChannelProvider("Gemini TTS", imp="._geminitts", key_name="gemini_key", win="gemini"),
    ELEVENLABS_TTS: ChannelProvider("Elevenlabs.io", imp="._elevenlabs", key_name="elevenlabstts_key", win="elevenlabs"),
    XAI_TTS: ChannelProvider('X.AI TTS', imp="._xaitts", key_name="xaitts_key", win="xaitts"),
    G_TTS: ChannelProvider(f"gTTS({tr('free')})", imp="._gtts"),

    CHATTTS: ChannelProvider(f"ChatTTS({tr('Local')}API)", imp="._chattts", key_name="chattts_api", win="chattts"),
    SPARK_TTS: ChannelProvider(f"Spark-TTS({tr('Local')}API)", imp="._spark", key_name="sparktts_url", win="f5tts"),
    KOKORO_TTS: ChannelProvider(f"kokoro({tr('Local')}API)", imp="._kokoro", key_name="kokoro_api", win="kokoro"),
    FISHTTS: ChannelProvider(f"Fish TTS({tr('Local')}API)", imp="._fishtts", key_name="fishtts_url", win="fishtts"),

    CLONE_VOICE_TTS: ChannelProvider(f"clone-voice({tr('Local')}API)", imp="._clone", key_name="clone_api", win="clone"),
    AZURE_TTS: ChannelProvider("Azure TTS", imp="._azure", key_name="azure_speech_key", win="azuretts"),
    AI302_TTS: ChannelProvider("302.AI", imp="._ai302", key_name="ai302_key", win="ai302"),
    CAMB_TTS: ChannelProvider("CAMB AI", imp="._cambtts", key_name="camb_api_key", win="cambtts"),

    TTS_API: ChannelProvider(tr("Customize API"), imp="._ttsapi", key_name="ttsapi_url", win="ttsapi"),
    SILICONFLOW_API: ChannelProvider(tr("SiliconFlow"), imp="._siliconflow", key_name="guiji_key", win="siliconflow" ),
    OPENROUTER_API: ChannelProvider("OpenRouter", imp="._openrouter", key_name="openrouter_key", win="openrouter" ),
}

# 强制保持按照每个常量值大小排序
ID_NAME_DICT = dict(sorted(ID_NAME_DICT.items(), key=lambda item: item[0]))
TTS_NAME_LIST = [it.name for it in ID_NAME_DICT.values()]