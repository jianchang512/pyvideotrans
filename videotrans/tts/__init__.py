from videotrans.configure import config

# 数字代表界面中的显示顺序
from videotrans.configure.config import tr
from videotrans.tts._edgetts import EdgeTTS
from videotrans.tts._qwentts import QWENTTS

from videotrans.tts._minimaxi import MinimaxiTTS
from videotrans.tts._azuretts import AzureTTS
from videotrans.tts._cosyvoice import CosyVoice
from videotrans.tts._ai302tts import AI302
from videotrans.tts._chattts import ChatTTS
from videotrans.tts._fishtts import FishTTS
from videotrans.tts._kokoro import KokoroTTS
from videotrans.tts._gptsovits import GPTSoVITS
from videotrans.tts._chatterbox import ChatterBoxTTS
from videotrans.tts._clone import CloneVoice
from videotrans.tts._openaitts import OPENAITTS
from videotrans.tts._elevenlabs import ElevenLabsC
from videotrans.tts._gtts import GTTS
from videotrans.tts._geminitts import GEMINITTS
from videotrans.tts._ttsapi import TTSAPI
from videotrans.tts._doubao import DoubaoTTS
from videotrans.tts._doubao2 import Doubao2TTS
from videotrans.tts._f5tts import F5TTS
from videotrans.tts._glmtts import GLMTTS

EDGE_TTS = 0
VITSCNEN_TTS = 1
PIPER_TTS = 2

OPENAI_TTS = 3
QWEN_TTS = 4
DOUBAO2_TTS=5
ELEVENLABS_TTS = 6
DOUBAO_TTS = 7
GLM_TTS = 8
AI302_TTS = 9




GPTSOVITS_TTS = 10
COSYVOICE_TTS = 11
CHATTERBOX_TTS = 12
CHATTTS = 13

F5_TTS = 14
INDEX_TTS = 15
VOXCPM_TTS = 16
SPARK_TTS = 17
DIA_TTS = 18
KOKORO_TTS = 19
CLONE_VOICE_TTS = 20
FISHTTS = 21
MINIMAXI_TTS = 22

AZURE_TTS = 23
GOOGLE_TTS = 24
GEMINI_TTS =25

TTS_API = 26
GOOGLECLOUD_TTS = 27

_ID_NAME_DICT = {
    EDGE_TTS:tr("Edge-TTS(free)"),
    VITSCNEN_TTS:f'VITS({tr("Local")})',
    PIPER_TTS:f'piper TTS({tr("Local")})',

    OPENAI_TTS:"OpenAI TTS",
    
    QWEN_TTS:"Qwen3 TTS",
    DOUBAO2_TTS:tr("DouBao2"),
    ELEVENLABS_TTS:"Elevenlabs.io",
    DOUBAO_TTS:tr("VolcEngine TTS"),
    GLM_TTS:f'{tr("Zhipu AI")} GLM-TTS',
    AI302_TTS:"302.AI",
    
    
    GPTSOVITS_TTS:"GPT-SoVITS",
    COSYVOICE_TTS:'CosyVoice',
    CHATTERBOX_TTS:"ChatterBox TTS",
    CHATTTS:"ChatTTS",
    
    F5_TTS:"F5-TTS",
    INDEX_TTS:"Index TTS",
    VOXCPM_TTS:"VoxCPM TTS",
    SPARK_TTS:"Spark TTS",
    DIA_TTS:"Dia TTS",

    KOKORO_TTS:"kokoro TTS",
    CLONE_VOICE_TTS:'clone-voice',
    FISHTTS:"Fish TTS",

    
    MINIMAXI_TTS:"Minimaxi TTS",
    AZURE_TTS:"Azure-TTS",
    GOOGLE_TTS:"Google TTS",
    
    GEMINI_TTS:"Gemini TTS",
    TTS_API:tr("Customize API"),
    
    #GOOGLECLOUD_TTS:"Google Cloud TTS",
}

TTS_NAME_LIST=list(_ID_NAME_DICT.values())

# 检查当前配音渠道是否支持所选配音语言
# 返回True为支持，其他为不支持并返回错误字符串
def is_allow_lang(langcode: str = None, tts_type: int = None):
    if langcode is None or tts_type is None:
        return True
    if tts_type == GPTSOVITS_TTS and langcode[:2] not in ['zh', 'ja', 'ko', 'en', 'yu']:
        return tr("GPT-SoVITS only supports Chinese, English, Japanese,ko")

    if tts_type == CHATTTS and langcode[:2] not in ['zh', 'en']:
        return tr("ChatTTS only supports Chinese, English")

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
    if tts_type == DOUBAO_TTS and (
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
        f5tts_win.openwin()
        return False
    if tts_type == SPARK_TTS and not config.params.get('sparktts_url',''):
        if return_str:
            return "Please configure the api and key information of the VolcEngine Spark-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin()
        return False
    if tts_type == VOXCPM_TTS and not config.params.get('voxcpmtts_url',''):
        if return_str:
            return "Please configure the api and key information of the VolcEngine VoxCPM-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin()
        return False
    if tts_type == DIA_TTS and not config.params.get('diatts_url',''):
        if return_str:
            return "Please configure the api and key information of the VolcEngine DIA-TTS channel first."
        from videotrans.winform import f5tts as f5tts_win
        f5tts_win.openwin()
        return False
    if tts_type == GOOGLECLOUD_TTS and not config.params.get('gcloud_credential_json'):
        if return_str:
            return "Please configure the Google Cloud credentials first."
        from videotrans.winform import googlecloud as googlecloud_win
        googlecloud_win.openwin()
        return False
    if tts_type == GLM_TTS and not config.params.get('zhipu_key'):
        if return_str:
            return "Please configure the ZhipuAI credentials first."
        from videotrans.winform import zhipuai as zhipuai_win
        zhipuai_win.openwin()
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
        AzureTTS(**kwargs).run()
    elif tts_type == EDGE_TTS:
        EdgeTTS(**kwargs).run()
    elif tts_type == AI302_TTS:
        AI302(**kwargs).run()
    elif tts_type == COSYVOICE_TTS:
        CosyVoice(**kwargs).run()
    elif tts_type == CHATTTS:
        ChatTTS(**kwargs).run()
    elif tts_type == FISHTTS:
        FishTTS(**kwargs).run()
    elif tts_type == KOKORO_TTS:
        KokoroTTS(**kwargs).run()
    elif tts_type == GPTSOVITS_TTS:
        GPTSoVITS(**kwargs).run()
    elif tts_type == CHATTERBOX_TTS:
        ChatterBoxTTS(**kwargs).run()
    elif tts_type == CLONE_VOICE_TTS:
        CloneVoice(**kwargs).run()
    elif tts_type == OPENAI_TTS:
        OPENAITTS(**kwargs).run()
    elif tts_type == QWEN_TTS:
        QWENTTS(**kwargs).run()
    elif tts_type == ELEVENLABS_TTS:
        ElevenLabsC(**kwargs).run()
    elif tts_type == GOOGLE_TTS:

        GTTS(**kwargs).run()
    elif tts_type == TTS_API:
        TTSAPI(**kwargs).run()
    elif tts_type == DOUBAO_TTS:
        DoubaoTTS(**kwargs).run()
    elif tts_type == DOUBAO2_TTS:
        Doubao2TTS(**kwargs).run()
    elif tts_type in [F5_TTS, INDEX_TTS, SPARK_TTS, DIA_TTS, VOXCPM_TTS]:
        F5TTS(**kwargs).run()

    elif tts_type == GEMINI_TTS:
        GEMINITTS(**kwargs).run()
    elif tts_type == MINIMAXI_TTS:
        MinimaxiTTS(**kwargs).run()
    elif tts_type == PIPER_TTS:
        from videotrans.tts._piper import PiperTTS
        PiperTTS(**kwargs).run()
    elif tts_type == VITSCNEN_TTS:
        from videotrans.tts._vits import VitsCNEN
        VitsCNEN(**kwargs).run()
    elif tts_type == GLM_TTS:
        from videotrans.tts._glmtts import GLMTTS
        GLMTTS(**kwargs).run()
