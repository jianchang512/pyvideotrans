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
AUDIOCPP_TTS=1
OMNIVOICE_TTS = 2
F5_TTS = 3
QWEN3LOCAL_TTS = 4
CONFUCIUS_TTS = 5
MOSS_TTS = 6
CHATTERBOX_TTS = 7
Supertonic_TTS = 8
HIGGS_AUDIO_TTS = 9

# cpu
ZIPVOICE_TTS = 10
PIPER_TTS = 11
VITSCNEN_TTS = 12

# 本地 API
INDEX_TTS = 13
GPTSOVITS_TTS = 14
COSYVOICE_TTS = 15
VOXCPM_TTS = 16
FIRERED3_TTS = 17

# 云 API
DEEPSEEK_TTS = 18
DOUBAO2_TTS = 19
BAILIAN_TTS = 20
XIAOMI_TTS = 21
GLM_TTS = 22
MINIMAXI_TTS = 23

# 海外 API
OPENAI_TTS = 24
GEMINI_TTS = 25
ELEVENLABS_TTS = 26

# 本地 API
CHATTTS = 27
SPARK_TTS = 28
KOKORO_TTS = 29
FISHTTS = 30

# 不推荐
# 在线API
XAI_TTS = 31
G_TTS = 32
AZURE_TTS = 33
AI302_TTS = 34
CAMB_TTS = 35

# 自定义API
TTS_API = 36
# 在线API
SILICONFLOW_API = 37
OPENROUTER_API = 38
DEEPGRAM_TTS = 39
FISHAUDIOAPI_TTS=40
CLONE_VOICE_TTS = 41

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
    AUDIOCPP_TTS,
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
    AUDIOCPP_TTS,
    MOSS_TTS,
    ZIPVOICE_TTS,
    PIPER_TTS,
    CHATTERBOX_TTS,
    Supertonic_TTS,
    VITSCNEN_TTS
]
# 支持 音量调节 的渠道，无需使用ffmpeg额外处理
SUPPORT_VOLUME=[EDGE_TTS, AZURE_TTS,FISHAUDIOAPI_TTS,MINIMAXI_TTS,DOUBAO2_TTS,GLM_TTS,AI302_TTS]

# 配音角色根据语言不同而变化的渠道
CHANGE_BY_LANGUAGE = [EDGE_TTS, MINIMAXI_TTS, AZURE_TTS, DOUBAO2_TTS, AI302_TTS, KOKORO_TTS,
                      PIPER_TTS, VITSCNEN_TTS, DEEPGRAM_TTS,FISHAUDIOAPI_TTS]

# 在设置中选择配音模型的渠道，值为保存所选模型的 params 键，渠道配音时从中读取模型
# Audio.cpp 只在任务未指定模型时（如 cli 未传入 --tts_model_name）使用保存的模型
TTS_MODEL_PARAMS = {
    AUDIOCPP_TTS: 'audiocpp_model',
    BAILIAN_TTS: 'bailian_ttsmodel',
    XIAOMI_TTS: 'xiaomi_ttsmodel',
    MINIMAXI_TTS: 'minimaxi_tts_model',
    OPENAI_TTS: 'openaitts_model',
    GEMINI_TTS: 'gemini_ttsmodel',
    ELEVENLABS_TTS: 'elevenlabstts_model',
    SILICONFLOW_API: 'siliconflow_tts_model',
    OPENROUTER_API: 'openrouter_tts_model',
    FISHAUDIOAPI_TTS: 'fishaudio_model',
}

# 在设置中还有其他会改变配音效果的参数（如 OpenAI TTS 的提示词、MiniMax 的情绪）的渠道，值为保存这些参数的 params 键，渠道配音时从中读取
TTS_STYLE_PARAMS = {
    OPENAI_TTS: ['openaitts_instructions'],
    MINIMAXI_TTS: ['minimaxi_emotion'],
    CHATTERBOX_TTS: ['chatterbox_cfg_weight', 'chatterbox_exaggeration'],
}

# 渠道id对应的设置窗口和sk键名,
# key_name: 存储 SK 或 api url的键，通过 app_cfg.params 调用，如果不存在该值，在使用时报错未填写
# win: 对应 winform 包中的文件名及 ui 包中的文件名，用于调用打开设置窗口
# imp 为该渠道实际代码文件，位于当前目录下
ID_NAME_DICT = {
    EDGE_TTS: ChannelProvider(tr("Edge-TTS(free)"),
                              imp="._edgetts"),
    AUDIOCPP_TTS: ChannelProvider(f"Audio.cpp({tr('Local')})",
                           imp="._audiocpp"),
    OMNIVOICE_TTS: ChannelProvider(f"OmniVoice({tr('Built-in')})",
                                   imp="._omnivoice"),
    F5_TTS: ChannelProvider(f"F5-TTS({tr('Built-in')})",
                            imp="._f5tts"),
    QWEN3LOCAL_TTS: ChannelProvider(f"Qwen3-TTS({tr('Built-in')})",
                                    imp="._qwenttslocal"),
    CONFUCIUS_TTS: ChannelProvider(f"Confucius4({tr('Built-in')})",
                                   imp="._confuciustts"),
    MOSS_TTS: ChannelProvider(f"MOSS-TTS-Nano({tr('Built-in')})",
                              imp="._mosstts"),

    CHATTERBOX_TTS: ChannelProvider(f"ChatterBox({tr('Built-in')})",
                                    imp="._chatterbox",
                                    win="chatterbox"),
    Supertonic_TTS: ChannelProvider(f"Supertonic3({tr('Built-in')})",
                                    imp="._supertonic"),
    HIGGS_AUDIO_TTS: ChannelProvider(f"Higgs-audio-v3({tr('Built-in')})",
                                     imp="._higgs"),

    ZIPVOICE_TTS: ChannelProvider(f"{tr('ZipVoice')}({tr('Built-in')})",
                                  imp="._zipvoice"),
    PIPER_TTS: ChannelProvider(f"Piper({tr('Built-in')})",
                               imp="._piper"),
    VITSCNEN_TTS: ChannelProvider(f"{tr('VITS')}({tr('Built-in')})",
                                  imp="._vits"),

    INDEX_TTS: ChannelProvider(f"Index-TTS({tr('Local')}API)",
                               imp="._index",
                               key_name="index_url",
                               win="gradiowin"),
    GPTSOVITS_TTS: ChannelProvider(f"GPT-SoVITS({tr('Local')}API)",
                                   imp="._gptsovits",
                                   key_name="gptsovits_url",
                                   win="gptsovits"),
    COSYVOICE_TTS: ChannelProvider(f"CosyVoice({tr('Local')}API)",
                                   imp="._cosyvoice",
                                   key_name="cosyvoice_url",
                                   win="cosyvoice"),
    VOXCPM_TTS: ChannelProvider(f"VoxCPM({tr('Local')}API)",
                                imp="._voxcpm",
                                key_name="voxcpm_url",
                                win="gradiowin"),
    FIRERED3_TTS: ChannelProvider(f"FireRed3({tr('Local')}API)",
                                  imp="._firered3tts",
                                  key_name="firered3tts_url",
                                  win="gradiowin"),

    DEEPSEEK_TTS: ChannelProvider('DeepSeek',
                                 imp="._deepseek",
                                 key_name="deepseek_key",
                                 win="deepseek"),
    DOUBAO2_TTS: ChannelProvider(tr("DouBao2"),
                                 imp="._doubao2",
                                 key_name="doubao2_access",
                                 win="doubao2"),
    BAILIAN_TTS: ChannelProvider(f"{tr('Ali-Bailian')}",
                              imp="._bailian",
                              key_name="bailian_key",
                              win="bailian"),
    XIAOMI_TTS: ChannelProvider(tr('XiaoMi'),
                                imp="._xiaomi",
                                key_name="xiaomi_key",
                                win="xiaomi"),
    GLM_TTS: ChannelProvider(f'{tr("Zhipu AI")}',
                             imp="._glmtts",
                             key_name="zhipuai_key",
                             win="zhipuai"),
    MINIMAXI_TTS: ChannelProvider("Minimaxi TTS",
                                  imp="._minimaxi",
                                  key_name="minimaxi_key",
                                  win="minimaxi"),

    OPENAI_TTS: ChannelProvider("OpenAI TTS",
                                imp="._openaitts",
                                key_name="openaitts_key",
                                win="openaitts"),
    GEMINI_TTS: ChannelProvider("Gemini TTS",
                                imp="._geminitts",
                                key_name="gemini_key",
                                win="gemini"),
    ELEVENLABS_TTS: ChannelProvider("Elevenlabs.io",
                                    imp="._elevenlabs",
                                    key_name="elevenlabstts_key",
                                    win="elevenlabs"),


    CHATTTS: ChannelProvider(f"ChatTTS({tr('Local')}API)",
                             imp="._chattts",
                             key_name="chattts_api",
                             win="chattts"),
    SPARK_TTS: ChannelProvider(f"Spark-TTS({tr('Local')}API)",
                               imp="._spark",
                               key_name="spark_url",
                               win="gradiowin"),
    KOKORO_TTS: ChannelProvider(f"kokoro({tr('Local')}API)",
                                imp="._kokoro",
                                key_name="kokoro_api",
                                win="kokoro"),
    FISHTTS: ChannelProvider(f"Fish TTS({tr('Local')}API)",
                             imp="._fishtts",
                             key_name="fishtts_url",
                             win="fishtts"),

    XAI_TTS: ChannelProvider('X.AI TTS',
                             imp="._xaitts",
                             key_name="xaitts_key",
                             win="xaitts"),
    G_TTS: ChannelProvider(f"gTTS({tr('free')})",
                           imp="._gtts"),
    AZURE_TTS: ChannelProvider("Azure TTS",
                               imp="._azuretts",
                               key_name="azuretts_key",
                               win="azuretts"),
    AI302_TTS: ChannelProvider("302.ai",
                               imp="._ai302",
                               key_name="ai302_key",
                               win="ai302"),
    CAMB_TTS: ChannelProvider("CAMB.ai",
                              imp="._camb",
                              key_name="camb_api_key",
                              win="camb"),

    TTS_API: ChannelProvider(tr("Customize API"),
                             imp="._ttsapi",
                             key_name="ttsapi_url",
                             win="ttsapi"),
    SILICONFLOW_API: ChannelProvider(tr("SiliconFlow"),
                                     imp="._siliconflow",
                                     key_name="siliconflow_key",
                                     win="siliconflow"),
    OPENROUTER_API: ChannelProvider("OpenRouter.ai",
                                    imp="._openrouter",
                                    key_name="openrouter_key",
                                    win="openrouter"),
    DEEPGRAM_TTS: ChannelProvider("Deepgram.com",
                                  imp="._deepgram",
                                  key_name="deepgram_key",
                                  win="deepgram"),
    FISHAUDIOAPI_TTS: ChannelProvider(f"Fish-Audio API",
                                     imp="._fishaudio",
                                     key_name="fishaudio_key",
                                     win="fishaudio"),
    CLONE_VOICE_TTS: ChannelProvider(f"clone-voice({tr('Local')}API)",
                                     imp="._clone",
                                     key_name="clone_api",
                                     win="clone"),
}

# 强制保持按照每个常量值大小排序
ID_NAME_DICT = dict(sorted(ID_NAME_DICT.items(), key=lambda item: item[0]))
TTS_NAME_LIST = [it.name for it in ID_NAME_DICT.values()]
