from videotrans.configure import config
from videotrans.tts._ai302tts import AI302
from videotrans.tts._azuretts import AzureTTS
from videotrans.tts._chattts import ChatTTS
from videotrans.tts._clone import CloneVoice
from videotrans.tts._cosyvoice import CosyVoice
from videotrans.tts._edgetts import EdgeTTS
from videotrans.tts._elevenlabs import ElevenLabs
from videotrans.tts._fishtts import FishTTS
from videotrans.tts._gptsovits import GPTSoVITS
from videotrans.tts._gtts import GTTS
from videotrans.tts._openaitts import OPENAITTS
from videotrans.tts._ttsapi import TTSAPI
from videotrans.winform import openaitts as openaitts_win, ai302tts as ai302tts_win, clone as clone_win, \
    elevenlabs as elevenlabs_win, ttsapi as ttsapi_win, gptsovits as gptsovits_win, cosyvoice as cosyvoice_win, \
    fishtts as fishtts_win, chattts as chattts_win, \
    azuretts as azuretts_win

# 数字代表界面中的显示顺序
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

TTS_NAME_LIST = [
    "Edge-TTS",
    'CosyVoice',
    "ChatTTS",
    "302.AI",
    "FishTTS",
    "Azure-TTS",
    "GPT-SoVITS",
    "clone-voice",
    "OpenAI TTS",
    "Elevenlabs.io",
    "Google TTS",
    "自定义TTS API" if config.defaulelang == 'zh' else 'Customize API'
]


# 检查当前配音渠道是否支持所选配音语言
# 返回True为支持，其他为不支持并返回错误字符串
def is_allow_lang(langcode: str = None, tts_type: int = None):
    if tts_type == GPTSOVITS_TTS and langcode[:2] not in ['zh', 'ja', 'en']:
        return 'GPT-SoVITS 仅支持中日英语言配音' if config.defaulelang == 'zh' else 'GPT-SoVITS only supports Chinese, English, Japanese'
    if tts_type == COSYVOICE_TTS and langcode[:2] not in ['zh', 'ja', 'en', 'ko']:
        return 'CosyVoice仅支持中日韩语言配音' if config.defaulelang == 'zh' else 'CosyVoice only supports Chinese, English, Japanese and Korean'

    if tts_type == CHATTTS and langcode[:2] not in ['zh', 'en']:
        return 'ChatTTS 仅支持中英语言配音' if config.defaulelang == 'zh' else 'ChatTTS only supports Chinese, English'

    if tts_type == FISHTTS and langcode[:2] not in ['zh', 'ja', 'en']:
        return 'FishTTS 仅支持中日英语言配音' if config.defaulelang == 'zh' else 'FishTTS only supports Chinese, English, Japanese'

    if tts_type == AI302_TTS and config.params['ai302tts_model'] == 'doubao' and langcode[:2] not in ['zh', 'ja', 'en']:
        return '302.ai豆包通道 仅支持中日英语言配音' if config.defaulelang == 'zh' else '302.ai doubao model only supports Chinese, English, Japanese'

    return True


# 判断是否填写了相关配音渠道所需要的信息
# 正确返回True，失败返回False，并弹窗
def is_input_api(tts_type: int = None,return_str=False):
    if tts_type == OPENAI_TTS and not config.params["chatgpt_key"]:
        if return_str:
            return "Please configure the api and key information of the OpenAI API channel first."
        openaitts_win.openwin()
        return False
    if tts_type == AI302_TTS and not config.params["ai302tts_key"]:
        if return_str:
            return "Please configure the api and key information of the 302.AI TTS channel first."
        ai302tts_win.openwin()
        return False
    if tts_type == CLONE_VOICE_TTS and not config.params["clone_api"]:
        if return_str:
            return "Please configure the api and key information of the Clone-Voice channel first."
        clone_win.openwin()
        return False
    if tts_type == ELEVENLABS_TTS and not config.params["elevenlabstts_key"]:
        if return_str:
            return "Please configure the api and key information of the Elevenlabs.io channel first."
        elevenlabs_win.openwin()
        return False
    if tts_type == TTS_API and not config.params['ttsapi_url']:
        if return_str:
            return "Please configure the api and key information of the TTS API channel first."
        ttsapi_win.openwin()
        return False
    if tts_type == GPTSOVITS_TTS and not config.params['gptsovits_url']:
        if return_str:
            return "Please configure the api and key information of the GPT-SoVITS channel first."
        gptsovits_win.openwin()
        return False
    if tts_type == COSYVOICE_TTS and not config.params['cosyvoice_url']:
        if return_str:
            return "Please configure the api and key information of the CosyVoice channel first."
        cosyvoice_win.openwin()
        return False
    if tts_type == FISHTTS and not config.params['fishtts_url']:
        if return_str:
            return "Please configure the api and key information of the FishTTS channel first."
        fishtts_win.openwin()
        return False
    if tts_type == CHATTTS and not config.params['chattts_api']:
        if return_str:
            return "Please configure the api and key information of the ChatTTS channel first."
        chattts_win.openwin()
        return False
    if tts_type == AZURE_TTS and (not config.params['azure_speech_key'] or not config.params['azure_speech_region']):
        if return_str:
            return "Please configure the api and key information of the Azure TTS channel first."
        azuretts_win.openwin()
        return False
    return True


def run(*, queue_tts=None, language=None, inst=None, uuid=None, play=False, is_test=False) -> None:
    # 需要并行的数量3
    if len(queue_tts) < 1:
        return
    if config.exit_soft or (not is_test and config.current_status != 'ing' and config.box_tts != 'ing'):
        return
    tts_type = queue_tts[0]['tts_type']
    kwargs = {
        "queue_tts": queue_tts,
        "language": language,
        "inst": inst,
        "uuid": uuid,
        "play": play,
        "is_test": is_test
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
    elif tts_type == GPTSOVITS_TTS:
        GPTSoVITS(**kwargs).run()
    elif tts_type == CLONE_VOICE_TTS:
        CloneVoice(**kwargs).run()
    elif tts_type == OPENAI_TTS:
        OPENAITTS(**kwargs).run()
    elif tts_type == ELEVENLABS_TTS:
        ElevenLabs(**kwargs).run()
    elif tts_type == GOOGLE_TTS:
        GTTS(**kwargs).run()
    elif tts_type == TTS_API:
        TTSAPI(**kwargs).run()
