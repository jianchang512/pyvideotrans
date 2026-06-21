from typing import Union, Type
from videotrans.configure.config import tr, params, app_cfg
from videotrans.tts._base import BaseTTS
from videotrans import ChannelProvider, get_class

# 推荐
EDGE_TTS = 0
QWEN3LOCAL_TTS = 1
OMNIVOICE_TTS = 2
MOSS_TTS = 3
PIPER_TTS = 4
VITSCNEN_TTS = 5
Supertonic_TTS = 6
CHATTERBOX_TTS = 7

# 本地
F5_TTS = 8
INDEX_TTS = 9
GPTSOVITS_TTS = 10
COSYVOICE_TTS = 11
VOXCPM_TTS = 12

# 云api
DOUBAO2_TTS = 13
QWEN_TTS = 14
XIAOMI_TTS = 15
GLM_TTS = 16
MINIMAXI_TTS = 17

# 海外
OPENAI_TTS = 18
GEMINI_TTS = 19
ELEVENLABS_TTS = 20
XAI_TTS = 21

# 本地
CHATTTS = 22
SPARK_TTS = 23
DIA_TTS = 24
KOKORO_TTS = 25
CLONE_VOICE_TTS = 26
FISHTTS = 27

AZURE_TTS = 28
AI302_TTS = 29
CAMB_TTS = 30
G_TTS = 31
CONFUCIUS_TTS = 32
TTS_API = 33


# 支持克隆的渠道
SUPPORT_CLONE = [
    COSYVOICE_TTS,
    CLONE_VOICE_TTS,
    F5_TTS, 
    INDEX_TTS,
    VOXCPM_TTS,
    SPARK_TTS,
    DIA_TTS,
    CHATTERBOX_TTS,
    GPTSOVITS_TTS,
    QWEN3LOCAL_TTS,
    CAMB_TTS,
    OMNIVOICE_TTS,
    MOSS_TTS,
    CONFUCIUS_TTS
]


# 配音角色根据语言不同而变化的渠道
CHANGE_BY_LANGUAGE = [EDGE_TTS, MINIMAXI_TTS, AZURE_TTS, DOUBAO2_TTS, AI302_TTS, KOKORO_TTS,
                      PIPER_TTS, VITSCNEN_TTS]

_ID_NAME_DICT = {
    EDGE_TTS: ChannelProvider(tr("Edge-TTS(free)"), "._edgetts"),
    QWEN3LOCAL_TTS: ChannelProvider(f"Qwen3-TTS({tr('Local')}{tr('Built-in')})", "._qwenttslocal"),
    OMNIVOICE_TTS: ChannelProvider(f"OmniVoice({tr('Local')}API)", "._omnivoice", key_name="omnivoice_url",   win="omnivoice"),
    MOSS_TTS: ChannelProvider(f"MOSS-TTS-Nano({tr('Local')}{tr('Built-in')})", "._mosstts"),
    PIPER_TTS: ChannelProvider(f"Piper({tr('Local')}{tr('Built-in')})", "._piper"),
    VITSCNEN_TTS: ChannelProvider(f"VITS({tr('Local')}{tr('Built-in')})", "._vits"),
    Supertonic_TTS: ChannelProvider(f"Supertonic3({tr('Local')}{tr('Built-in')})", "._supertonic"),
    CHATTERBOX_TTS: ChannelProvider(f"ChatterBox({tr('Local')}{tr('Built-in')})", "._chatterbox",  win="chatterbox"),

    GPTSOVITS_TTS: ChannelProvider(f"GPT-SoVITS({tr('Local')}API)", "._gptsovits", key_name="gptsovits_url", win="gptsovits"),
    F5_TTS: ChannelProvider(f"F5-TTS({tr('Local')}API)", "._f5tts", key_name="f5tts_url", win="f5tts"),
    INDEX_TTS: ChannelProvider(f"Index-TTS({tr('Local')}API)", "._index", key_name="indextts_url", win="f5tts"),
    COSYVOICE_TTS: ChannelProvider(f"CosyVoice({tr('Local')}API)", "._cosyvoice", key_name="cosyvoice_url",  win="cosyvoice"),
    VOXCPM_TTS: ChannelProvider(f"VoxCPM({tr('Local')}API)", "._voxcpm", key_name="voxcpmtts_url", win="f5tts"),

    DOUBAO2_TTS: ChannelProvider(tr("DouBao2"), "._doubao2", key_name="doubao2_access", win="doubao2"),
    QWEN_TTS: ChannelProvider("Qwen3-TTS", "._qwentts", key_name="qwentts_key", win="qwentts"),
    XIAOMI_TTS: ChannelProvider('XiaoMi-TTS', "._xiaomi", key_name="xiaomi_key", win="mitts"),
    GLM_TTS: ChannelProvider(f'GLM-TTS {tr("Zhipu AI")}', "._glmtts", key_name="zhipu_key", win="zhipuai"),
    MINIMAXI_TTS: ChannelProvider("Minimaxi-TTS", "._minimaxi", key_name="minimaxi_apikey", win="minimaxi"),

    OPENAI_TTS: ChannelProvider("OpenAI-TTS", "._openaitts", key_name="openaitts_key", win="openaitts"),
    GEMINI_TTS: ChannelProvider("Gemini TTS", "._geminitts", key_name="gemini_key", win="gemini"),
    ELEVENLABS_TTS: ChannelProvider("Elevenlabs.io", "._elevenlabs", key_name="elevenlabstts_key", win="elevenlabs"),
    XAI_TTS: ChannelProvider('X.AI TTS', "._xaitts", key_name="xaitts_key", win="xaitts"),


    CHATTTS: ChannelProvider(f"ChatTTS({tr('Local')}API)", "._chattts", key_name="chattts_api", win="chattts"),
    SPARK_TTS: ChannelProvider(f"Spark-TTS({tr('Local')}API)", "._spark", key_name="sparktts_url", win="f5tts"),
    DIA_TTS: ChannelProvider(f"Dia-TTS({tr('Local')}API)", "._dia", key_name="diatts_url", win="f5tts"),
    KOKORO_TTS: ChannelProvider(f"kokoro-TTS({tr('Local')}API)", "._kokoro", key_name="kokoro_api", win="kokoro"),
    CLONE_VOICE_TTS: ChannelProvider(f"clone-voice({tr('Local')}API)", "._clone", key_name="clone_api", win="clone"),
    FISHTTS: ChannelProvider(f"Fish-TTS({tr('Local')}API)", "._fishtts", key_name="fishtts_url", win="fishtts"),

    AZURE_TTS: ChannelProvider("Azure-TTS", "._azuretts", key_name="azure_speech_key", win="azuretts"),
    AI302_TTS: ChannelProvider("302.AI", "._ai302tts", key_name="ai302_key", win="ai302"),
    CAMB_TTS: ChannelProvider("CAMB AI TTS", "._cambtts", key_name="camb_api_key", win="cambtts"),
    G_TTS: ChannelProvider(f"gTTS({tr('free')})", "._gtts"),
    CONFUCIUS_TTS: ChannelProvider(f"Confucius-TTS({tr('Local')}API)", "._confuciustts",key_name="confuciustts_url", win="f5tts"),
    TTS_API: ChannelProvider(tr("Customize API"), "._ttsapi", key_name="ttsapi_url", win="ttsapi")
}
# 强制保持按照每个常量值大小排序
_ID_NAME_DICT=dict(sorted(_ID_NAME_DICT.items(),key=lambda item:item[0]))
TTS_NAME_LIST = [it.name for it in _ID_NAME_DICT.values()]


# 检查当前配音渠道是否支持所选配音语言
# 返回True为支持，其他为不支持并返回错误字符串
def is_allow_lang(langcode: str = None, tts_type: int = None):
    if langcode is None or tts_type is None:
        return True
    name = _ID_NAME_DICT.get(tts_type).name
    if tts_type == GPTSOVITS_TTS and langcode[:2] not in ['zh', 'ja', 'ko', 'en', 'yu']:
        return name + tr('Dubbing channel') + ' ' + tr('Only support') + tr(
            ['zh', 'ja', 'ko', 'en', 'yu'])
    # 中文、英文、日文、韩文、德文、法文、俄文、葡萄牙文、西班牙文、意大利文
    if tts_type == QWEN3LOCAL_TTS and langcode[:2] not in ['zh', 'ja', 'ko', 'en', 'yu', 'de', 'fr', 'ru', 'pt', 'es',
                                                           'it']:
        return name + tr('Dubbing channel') + ' ' + tr('Only support') + tr(
            ['zh', 'ja', 'ko', 'en', 'yu', 'de', 'fr', 'ru', 'pt', 'es', 'it'])

    if tts_type == CHATTTS and langcode[:2] not in ['zh', 'en']:
        return name + tr('Dubbing channel') + ' ' + tr('Only support') + tr(['zh', 'en'])
    if tts_type == Supertonic_TTS and langcode[:2] not in ['ar','cs','nl','en','fr','de','el','hi','hu','id','it','ja','ko','pl','pt','ro','ru','es','sv','tr','uk','vi']:
        return name + tr('Dubbing channel') + tr('may not support') + tr(langcode)

    # moss-tts ["zh","en","ja"]
    if tts_type==MOSS_TTS and langcode[:2] not in ["zh","yu","en","de","es","fr","ja","it","hu","ko","ru","fa","ar","pl","pt","cs","sv","el","tr","da"]:
        return name + tr('Dubbing channel') + tr('may not support') + tr(langcode)
    #Arabic, Danish, German, Greek, English, Spanish, Finnish, French, Hebrew, Hindi, Italian, Japanese, Korean, Malay, Dutch, Norwegian, Polish, Portuguese, Russian, Swedish, Swahili, Turkish, Chinese
    if tts_type==CHATTERBOX_TTS and langcode[:2] not in ["zh","yu","en","de","es","fr","ja","it","ko","ru","ar","pl","pt","sv","el","tr","da","he",'hi',"ms","nl","nb"]:
        return name + tr('Dubbing channel') + tr('may not support') + tr(langcode)
    if tts_type==CONFUCIUS_TTS and langcode[:2] not in ["zh", "en", "ja", "ko", "de", "fr", "th", 
    "id", "vi", "es", "pt", "it", "ru", "ms"]:
        return name + tr('Dubbing channel') + tr('may not support') + tr(langcode)
    return True


# 判断是否填写了相关配音渠道所需要的信息
# 正确返回True，失败返回False，并弹窗
def is_input_api(tts_type: int = None, return_str=False):
    _cls = _ID_NAME_DICT.get(tts_type)
    if not _cls:
        return True
    if _cls.key_name and not params.get(_cls.key_name):
        from videotrans import winform
        return "Please configure the SK or API information of the channel first." if return_str else winform.get_win(_cls.win).openwin()
    return True


def clone_tips(tts_type, role: str = 'No', recogn_type=9):
    if tts_type in SUPPORT_CLONE and role == 'clone':
        return tr('clone_dubb_tips1') + (tr('clone_dubb_tips2') if recogn_type < 2 else '')
    return


# 统一调用 tts渠道入口，通过 tts_type 调用对应渠道
def run(*, queue_tts=None, language=None, uuid=None, play=False, is_test=False, tts_type=0, is_cuda=False) -> None:
    # 需要并行的数量3
    if len(queue_tts) < 1 or app_cfg.exit_soft or (uuid and uuid in app_cfg.stoped_uuid_set): return

    kwargs = {
        "queue_tts": queue_tts,
        "language": language,
        "uuid": uuid,
        "play": play,
        "is_test": is_test,
        "tts_type": tts_type,
        "is_cuda": is_cuda
    }

    _cls: Union[Type[BaseTTS], None] = get_class(tts_type, "tts", _ID_NAME_DICT)
    if not _cls:
        from videotrans.configure.excepts import DubbingSrtError
        raise DubbingSrtError(f'No this TTS Channel:{tts_type=}')

    return _cls(**kwargs).run()  # type:ignore
