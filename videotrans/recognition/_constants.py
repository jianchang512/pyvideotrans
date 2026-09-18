from videotrans import ChannelProvider
from videotrans.configure._i18n import tr

"""
如果想新增渠道
1. 定义一个常量，值为以下递增的序号
2. 在 ID_NAME_DICT 中新增一个键值对，键为新增的常量，值是 ChannelProvider 实例
3. 当前目录下定义一个实际实现代码文件，可直接复制已有渠道文件
"""

# 内置渠道
FASTER_WHISPER = 0
OPENAI_WHISPER = 1
QWENASR = 2
FUNASR_CN = 3
NEMOTRON_ASR = 4
FIREREDASR = 5
DOLPHIN = 6
Omnilingual = 7
HUGGINGFACE_ASR = 8
MOSS_DIARIZE = 9
VIBEVOICE_ASR = 10
Whisper_CPP = 11

# 在线API
OPENAI_API = 12
QWEN3ASR = 13
XIAOMIASR = 14
ZIJIE_RECOGN_MODEL = 15
ZHIPU_API = 16
GEMINI_SPEECH = 17

# 本地API
Faster_Whisper_XXL = 18
WHISPERX_API = 19
PARAKEET = 20

# 在线API
AI_302 = 21
ElevenLabs = 22
GOOGLE_SPEECH = 23
Deepgram = 24
CAMB_ASR = 25
STT_API = 26
# .net
WHISPER_NET = 27
# 自定义API
CUSTOM_API = 28
SILICONFLOW_API = 29
OPENROUTER_API = 30
MINIMAX_API = 31

# 允许切换不同模型的渠道
ALLOW_CHANGE_MODEL = [
    FASTER_WHISPER, Faster_Whisper_XXL, Whisper_CPP,
    OPENAI_WHISPER, FUNASR_CN, Deepgram,
    WHISPERX_API, HUGGINGFACE_ASR, QWENASR,
    WHISPER_NET, QWEN3ASR
]

# 渠道id对应的设置窗口和sk键名,
# key_name: 存储 SK 或 api url的键，通过 app_cfg.params 调用，如果不存在该值，在使用时报错未填写
# win: 对应 winform 包中的文件名及 ui 包中的文件名，用于调用打开设置窗口
# imp 为该渠道实际代码文件，位于当前目录下
ID_NAME_DICT = {
    FASTER_WHISPER: ChannelProvider(f"faster-whisper({tr('Built-in')})", imp="._whisper"),
    OPENAI_WHISPER: ChannelProvider(f"openai-whisper({tr('Built-in')})", imp="._whisper"),
    QWENASR: ChannelProvider(f"Qwen-ASR({tr('Built-in')})", imp="._qwenasrlocal"),
    FUNASR_CN: ChannelProvider(tr("FunASR-Chinese") + f"({tr('Built-in')})", imp="._funasr"),
    NEMOTRON_ASR: ChannelProvider(f"Nemotron-3.5-asr-0.6b({tr('Built-in')})", imp="._nemotronasr"),
    FIREREDASR: ChannelProvider(f"{tr('FireRed')}({tr('Built-in')})", imp="._fireredasr"),
    DOLPHIN: ChannelProvider(f"{tr('Dolphin')}({tr('Built-in')})", imp="._dolphin"),
    Omnilingual: ChannelProvider(f"{tr('Omnilingual')}({tr('Built-in')})", imp="._omnilingual"),
    HUGGINGFACE_ASR: ChannelProvider(f"Huggingface_ASR({tr('Built-in')})", imp="._huggingface"),
    MOSS_DIARIZE: ChannelProvider(f"MOSS-Diarize({tr('Built-in')})", imp="._moss"),
    VIBEVOICE_ASR: ChannelProvider(f'{tr("VibeVoice-ASR")}({tr("Built-in")})', imp="._vibeasr"),
    Whisper_CPP: ChannelProvider(f"Whisper.cpp(Win{tr('Built-in')})", imp="._cpp"),

    OPENAI_API: ChannelProvider(tr("OpenAI Speech to Text"), key_name="openairecognapi_key", win="openairecognapi",
                                imp="._openairecognapi"),
    QWEN3ASR: ChannelProvider(tr("Ali Qwen3-ASR"), key_name="qwenmt_key", win="qwenmt", imp="._qwen3asr"),
    XIAOMIASR: ChannelProvider(tr("XiaoMi"), key_name="xiaomi_key", win="xiaomi", imp="._xiaomiasr"),
    ZIJIE_RECOGN_MODEL: ChannelProvider(tr("VolcEngine STT"), key_name="zijierecognmodel_appid", win="zijierecognmodel",
                                        imp="._zijiemodel"),
    ZHIPU_API: ChannelProvider(f'{tr("Zhipu AI")} GLM-ASR', key_name="zhipu_key", win="zhipuai", imp="._glmasr"),
    GEMINI_SPEECH: ChannelProvider(tr("Gemini AI"), key_name="gemini_key", win="gemini", imp="._gemini"),

    Faster_Whisper_XXL: ChannelProvider("Faster-Whisper-XXL.exe", imp="._xxl"),
    WHISPERX_API: ChannelProvider(f"WhisperX({tr('Local')}API)", imp="._whisperx"),
    PARAKEET: ChannelProvider(f"Parakeet-tdt({tr('Local')}API)", key_name="parakeet_address", win="parakeet",
                              imp="._parakeet"),

    AI_302: ChannelProvider("302.AI", key_name="ai302_key", win="ai302", imp="._ai302"),
    ElevenLabs: ChannelProvider("ElevenLabs.io", key_name="elevenlabstts_key", win="elevenlabs", imp="._elevenlabs"),
    GOOGLE_SPEECH: ChannelProvider(tr("Google Speech to Text"), imp="._google"),
    Deepgram: ChannelProvider("Deepgram.com", key_name="deepgram_apikey", win="deepgram", imp="._deepgram"),
    CAMB_ASR: ChannelProvider("CAMB AI", key_name="camb_api_key", win="cambtts", imp="._camb"),
    STT_API: ChannelProvider(f"STT({tr('Local')}API)", key_name="stt_url", win="sttapi", imp="._stt"),
    WHISPER_NET: ChannelProvider("Whisper.NET", imp="._whispernet"),
    CUSTOM_API: ChannelProvider(tr("Custom API"), key_name="recognapi_url", win="recognapi", imp="._recognapi"),
    SILICONFLOW_API: ChannelProvider(tr("SiliconFlow"), key_name="guiji_key", win="siliconflow", imp="._siliconflow"),
    OPENROUTER_API: ChannelProvider('OpenRouter', key_name="openrouter_key", win="openrouter", imp="._openrouter"),
    MINIMAX_API: ChannelProvider('Minimax AI', key_name="minimaxi_apikey", win="minimaxi", imp="._minimaxi"),

}
# 强制保持按照每个常量值大小排序
ID_NAME_DICT=dict(sorted(ID_NAME_DICT.items(),key=lambda item:item[0]))
RECOGN_NAME_LIST = [it.name for it in ID_NAME_DICT.values()]
HUGGINGFACE_ASR_MODELS = {
    "nvidia/parakeet-tdt-0.6b-v3": ['en','bg','hr','cs','da','nl','et','fi','fr','de','el','hu','it','lv','lt','mt','pl','pt','ro','sk','sl','es','sv','ru','uk'],
    "nvidia/nemotron-3.5-asr-streaming-0.6b": ["en","es","fr","it","pt","nl","de","tr","ru","ar","hi","ja","ko","vi","uk","pl","sv","cs","nb","da","bg","fi","hr","sk","zh","hu","ro","et","el","lt","lv","mt","sl","he","th","nn"],
    "Audio8/ARK-ASR-0.6B": ['zh','en','de','ja','fr','ko','es','pl','it','ro','hu','cs','nl'],
    "Audio8/ARK-ASR-3B": ['zh','en','de','ja','fr','ko','es','pl','it','ro','hu','cs','nl'],
    "zai-org/GLM-ASR-Nano-2512": ['zh','en','yue'],

    "ibm-granite/granite-speech-4.1-2b": ['fr','en','de','es','pt','ja'],
    # hub
    "reazon-research/japanese-wav2vec2-large-rs35kh": ['ja'],#日语
    # pipeline whisper
    "kotoba-tech/kotoba-whisper-v2.0": ['ja'],#日语
    # pipeline whisper
    "vinai/Phowhisper-large": ['vi'],#越南语
    "nguyenvulebinh/wav2vec2-base-vietnamese-250h": ['vi'],#越南语
    "biodatlab/whisper-th-large-v3": ['th'],#泰语
    "sakares/wav2vec2-large-xlsr-thai-demo": ['th'],#泰语
    "SiangLao/xlsr-53-lao-asr":['lo'],# 老挝语
    "chuuhtetnaing/whisper-large-v3-myanmar":[],#缅甸语
    "1morecupofhottea/whisper-turbo-khmer-v9":[],#高棉语 柬埔寨
    "anke01/whisper-small-uyghur":[],#维吾尔语
    "kingabzpro/whisper-large-v3-turbo-urdu":[],#乌尔都语
    "vasista22/whisper-tamil-small":[],#泰米尔
    "theainerd/Wav2Vec2-large-xlsr-hindi":[],#印地语
    "cautroi/whisper-large-v3-id":[],#印尼语
    "Khalsuu/filipino-wav2vec2-l-xls-r-300m-official":[],#菲律宾
    "navai-uz/whisper-medium-uzbek":[],#乌兹别克
    "jonatasgrosman/wav2vec2-large-xlsr-53-persian":[],#波斯语
    "Ghost3454/translynx-pakistani-punjabi-whisper-small":[],#旁遮普语
    "turkmedstt/whisper-large-v3-turkish-general":[],#土耳其语
    "anton-l/wav2vec2-large-xlsr-53-mongolian":[],#蒙古语
    "HNO333333/w2v-bert-2.0-Tibetan-Amdo":[],#藏语
    "openai/whisper-large-v3": []
}
