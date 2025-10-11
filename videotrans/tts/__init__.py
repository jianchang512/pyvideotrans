import json

from videotrans.configure import config

# 数字代表界面中的显示顺序
from videotrans.configure.config import tr

EDGE_TTS = 0
COSYVOICE_TTS = 1
CHATTTS = 2
AI302_TTS = 3
FISHTTS = 4
AZURE_TTS = 5
GPTSOVITS_TTS = 6
CLONE_VOICE_TTS = 7
OPENAI_TTS = 8
ELEVENLABS_TTS = 9
GOOGLE_TTS = 10
TTS_API = 11
VOLCENGINE_TTS = 12
F5_TTS = 13
KOKORO_TTS = 14
INDEX_TTS = 15
GEMINI_TTS = 16
CHATTERBOX_TTS = 17
QWEN_TTS = 18
MINIMAXI_TTS = 19
VOXCPM_TTS = 20
SPARK_TTS = 21
DIA_TTS = 22
GOOGLECLOUD_TTS = 23

TTS_NAME_LIST = [
    tr("Edge-TTS(free)"),
    'CosyVoice',
    "ChatTTS",
    "302.AI",
    "Fish TTS",
    "Azure-TTS",
    "GPT-SoVITS",
    'clone-voice',
    "OpenAI TTS",
    "Elevenlabs.io",
    "Google TTS",
    tr("Customize API"),
    tr("VolcEngine TTS"),
    "F5-TTS",
    "kokoro TTS",
    "Index TTS",
    "Gemini TTS",
    "ChatterBox TTS",
    "Qwen TTS",
    "Minimaxi TTS",
    "VoxCPM TTS",
    "Spark TTS",
    "Dia TTS",
    # "Google Cloud TTS",
]



# 检查当前配音渠道是否支持所选配音语言
# 返回True为支持，其他为不支持并返回错误字符串
def is_allow_lang(langcode: str = None, tts_type: int = None):
    if langcode is None or tts_type is None:
        return True
    if tts_type == GPTSOVITS_TTS and langcode[:2] not in ['zh', 'ja', 'ko', 'en', 'yu']:
        return tr("GPT-SoVITS only supports Chinese, English, Japanese,ko")


    if tts_type == COSYVOICE_TTS and langcode[:2] not in ['zh', 'ja', 'en', 'ko', 'yu']:
        return tr("CosyVoice only supports Chinese, English, Japanese and Korean")

    if tts_type == CHATTTS and langcode[:2] not in ['zh', 'en']:
        return tr("ChatTTS only supports Chinese, English")



    if tts_type == VOLCENGINE_TTS and langcode[:2] not in ['zh', 'ja', 'en', 'pt', 'es', 'th', 'vi', 'id', 'yu']:
        return tr("Byte VolcEngine TTS only supports Chinese, English, Japanese, Portuguese, Spanish, Thai, Vietnamese, Indonesian")
    if tts_type == KOKORO_TTS and langcode[:2] not in ['zh', 'ja', 'en', 'pt', 'es', 'it', 'hi', 'fr']:
        return tr("Kokoro TTS only supports Chinese, English, Japanese, Portuguese, Spanish, it, hi, fr")

    return True


# 判断是否填写了相关配音渠道所需要的信息
# 正确返回True，失败返回False，并弹窗
def is_input_api(tts_type: int = None, return_str=False):
    if tts_type == OPENAI_TTS and not config.params.get("openaitts_key",''):
        if return_str:
            return "Please configure the api and key information of the OpenAI API channel first."
        from videotrans.winform import openaitts as openaitts_win
        openaitts_win.openwin()
        return False
    if tts_type == QWEN_TTS and not config.params.get("qwentts_key",''):
        if return_str:
            return "Please configure the api key information of the Qwen TTS  channel first."
        from videotrans.winform import qwentts as qwentts_win
        qwentts_win.openwin()
        return False
    if tts_type == MINIMAXI_TTS and not config.params.get("minimaxi_apikey",''):
        if return_str:
            return "Please configure the api key information of the MINIMAXI TTS  channel first."
        from videotrans.winform import minimaxi as minimaxi_win
        minimaxi_win.openwin()
        return False
    if tts_type == KOKORO_TTS and not config.params.get("kokoro_api",''):
        if return_str:
            return "Please configure the api  information of the kokoro tts channel first."
        from videotrans.winform import kokoro
        kokoro.openwin()
        return False
    if tts_type == AI302_TTS and not config.params.get("ai302_key",''):
        if return_str:
            return "Please configure the api and key information of the 302.AI TTS channel first."
        from videotrans.winform import ai302
        ai302.openwin()
        return False
    if tts_type == CLONE_VOICE_TTS and not config.params.get("clone_api",''):
        if return_str:
            return "Please configure the api and key information of the Clone-Voice channel first."
        from videotrans.winform import clone as clone_win
        clone_win.openwin()
        return False
    if tts_type == ELEVENLABS_TTS and not config.params.get("elevenlabstts_key",''):
        if return_str:
            return "Please configure the api and key information of the Elevenlabs.io channel first."
        from videotrans.winform import elevenlabs as elevenlabs_win
        elevenlabs_win.openwin()
        return False
    if tts_type == TTS_API and not config.params.get('ttsapi_url',''):
        if return_str:
            return "Please configure the api and key information of the TTS API channel first."
        from videotrans.winform import ttsapi as ttsapi_win
        ttsapi_win.openwin()
        return False
    if tts_type == GPTSOVITS_TTS and not config.params.get('gptsovits_url',''):
        if return_str:
            return "Please configure the api and key information of the GPT-SoVITS channel first."
        from videotrans.winform import gptsovits as gptsovits_win
        gptsovits_win.openwin()
        return False
    if tts_type == CHATTERBOX_TTS and not config.params.get('chatterbox_url',''):
        if return_str:
            return "Please configure the api and key information of the ChatterBox channel first."
        from videotrans.winform import chatterbox as chatterbox_win
        chatterbox_win.openwin()
        return False
    if tts_type == COSYVOICE_TTS and not config.params.get('cosyvoice_url',''):
        if return_str:
            return "Please configure the api and key information of the CosyVoice channel first."
        from videotrans.winform import cosyvoice as cosyvoice_win
        cosyvoice_win.openwin()
        return False
    if tts_type == FISHTTS and not config.params.get('fishtts_url',''):
        if return_str:
            return "Please configure the api and key information of the FishTTS channel first."
        from videotrans.winform import fishtts as fishtts_win
        fishtts_win.openwin()
        return False
    if tts_type == CHATTTS and not config.params.get('chattts_api',''):
        if return_str:
            return "Please configure the api and key information of the ChatTTS channel first."
        from videotrans.winform import chattts as chattts_win
        chattts_win.openwin()
        return False
    if tts_type == AZURE_TTS and (not config.params.get('azure_speech_key','') or not config.params.get('azure_speech_region','')):
        if return_str:
            return "Please configure the api and key information of the Azure TTS channel first."
        from videotrans.winform import azuretts as azuretts_win
        azuretts_win.openwin()
        return False
    if tts_type == GEMINI_TTS and not config.params.get('gemini_key',''):
        if return_str:
            return "Please configure the Gemini key information."
        from videotrans.winform import gemini as gemini_win
        gemini_win.openwin()
        return False
    if tts_type == VOLCENGINE_TTS and (
            not config.params.get('volcenginetts_appid','') or not config.params.get('volcenginetts_access','') or not config.params.get('volcenginetts_cluster','')):
        if return_str:
            return "Please configure the api and key information of the VolcEngine TTS channel first."
        from videotrans.winform import volcenginetts as volcengine_win
        volcengine_win.openwin()
        return False
    # F5_TTS_WINFORM_NAMES=['F5-TTS', 'Spark-TTS', 'Index-TTS', 'Dia-TTS','VoxCPM-TTS']
    if tts_type == F5_TTS and not config.params.get('f5tts_url',''):
        if return_str:
            return "Please configure the api and key information of the VolcEngine F5-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin()
        return False
    if tts_type == INDEX_TTS and not config.params.get('indextts_url',''):
        if return_str:
            return "Please configure the api and key information of the VolcEngine Index-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin('Index-TTS')
        return False
    if tts_type == SPARK_TTS and not config.params.get('sparktts_url',''):
        if return_str:
            return "Please configure the api and key information of the VolcEngine Spark-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin('Spark-TTS')
        return False
    if tts_type == VOXCPM_TTS and not config.params.get('voxcpmtts_url',''):
        if return_str:
            return "Please configure the api and key information of the VolcEngine VoxCPM-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin('VoxCPM-TTS')
        return False
    if tts_type == DIA_TTS and not config.params.get('diatts_url',''):
        if return_str:
            return "Please configure the api and key information of the VolcEngine DIA-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin('Dia-TTS')
        return False
    if tts_type == GOOGLECLOUD_TTS and not config.params.get('gcloud_credential_json'):
        if return_str:
            return "Please configure the Google Cloud credentials first."
        from videotrans.winform import googlecloud as googlecloud_win
        googlecloud_win.openwin()
        return False
    return True


# 统一调用 tts渠道入口，通过 tts_type 调用对应渠道
def run(*, queue_tts=None, language=None, uuid=None, play=False, is_test=False, tts_type=0) -> None:
    # 需要并行的数量3
    if len(queue_tts) < 1:
        return
    if config.exit_soft or (not is_test and config.current_status != 'ing' and config.box_tts != 'ing'):
        return

    kwargs = {
        "queue_tts": queue_tts,
        "language": language,
        "uuid": uuid,
        "play": play,
        "is_test": is_test,
        "tts_type":tts_type
    }
    if tts_type == AZURE_TTS:
        from videotrans.tts._azuretts import AzureTTS
        AzureTTS(**kwargs).run()
    elif tts_type == EDGE_TTS:
        from videotrans.tts._edgetts import EdgeTTS
        EdgeTTS(**kwargs).run()
    elif tts_type == AI302_TTS:
        from videotrans.tts._ai302tts import AI302
        AI302(**kwargs).run()
    elif tts_type == COSYVOICE_TTS:
        from videotrans.tts._cosyvoice import CosyVoice
        CosyVoice(**kwargs).run()
    elif tts_type == CHATTTS:
        from videotrans.tts._chattts import ChatTTS
        ChatTTS(**kwargs).run()
    elif tts_type == FISHTTS:
        from videotrans.tts._fishtts import FishTTS
        FishTTS(**kwargs).run()
    elif tts_type == KOKORO_TTS:
        from videotrans.tts._kokoro import KokoroTTS
        KokoroTTS(**kwargs).run()
    elif tts_type == GPTSOVITS_TTS:
        from videotrans.tts._gptsovits import GPTSoVITS
        GPTSoVITS(**kwargs).run()
    elif tts_type == CHATTERBOX_TTS:
        from videotrans.tts._chatterbox import ChatterBoxTTS
        ChatterBoxTTS(**kwargs).run()
    elif tts_type == CLONE_VOICE_TTS:
        from videotrans.tts._clone import CloneVoice
        CloneVoice(**kwargs).run()
    elif tts_type == OPENAI_TTS:
        from videotrans.tts._openaitts import OPENAITTS
        OPENAITTS(**kwargs).run()
    elif tts_type == QWEN_TTS:
        from videotrans.tts._qwentts import QWENTTS
        QWENTTS(**kwargs).run()
    elif tts_type == ELEVENLABS_TTS:
        from videotrans.tts._elevenlabs import ElevenLabsC
        ElevenLabsC(**kwargs).run()
    elif tts_type == GOOGLE_TTS:
        from videotrans.tts._gtts import GTTS
        GTTS(**kwargs).run()
    elif tts_type == TTS_API:
        from videotrans.tts._ttsapi import TTSAPI
        TTSAPI(**kwargs).run()
    elif tts_type == VOLCENGINE_TTS:
        from videotrans.tts._volcengine import VolcEngineTTS
        VolcEngineTTS(**kwargs).run()
    elif tts_type in [F5_TTS, INDEX_TTS, SPARK_TTS, DIA_TTS, VOXCPM_TTS]:
        from videotrans.tts._f5tts import F5TTS
        F5TTS(**kwargs).run()
    elif tts_type == GOOGLECLOUD_TTS:
        from videotrans.tts._googlecloud import GoogleCloudTTS
        GoogleCloudTTS(**kwargs).run()
    elif tts_type == GEMINI_TTS:
        from videotrans.tts._geminitts import GEMINITTS
        GEMINITTS(**kwargs).run()
    elif tts_type == MINIMAXI_TTS:
        from videotrans.tts._minimaxi import MinimaxiTTS
        MinimaxiTTS(**kwargs).run()
