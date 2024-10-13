from videotrans.configure import config



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
        from videotrans.winform import openaitts as openaitts_win
        openaitts_win.openwin()
        return False
    if tts_type == AI302_TTS and not config.params["ai302tts_key"]:
        if return_str:
            return "Please configure the api and key information of the 302.AI TTS channel first."
        from videotrans.winform import  ai302tts as ai302tts_win
        ai302tts_win.openwin()
        return False
    if tts_type == CLONE_VOICE_TTS and not config.params["clone_api"]:
        if return_str:
            return "Please configure the api and key information of the Clone-Voice channel first."
        from videotrans.winform import clone as clone_win
        clone_win.openwin()
        return False
    if tts_type == ELEVENLABS_TTS and not config.params["elevenlabstts_key"]:
        if return_str:
            return "Please configure the api and key information of the Elevenlabs.io channel first."
        from videotrans.winform import elevenlabs as elevenlabs_win
        elevenlabs_win.openwin()
        return False
    if tts_type == TTS_API and not config.params['ttsapi_url']:
        if return_str:
            return "Please configure the api and key information of the TTS API channel first."
        from videotrans.winform import ttsapi as ttsapi_win
        ttsapi_win.openwin()
        return False
    if tts_type == GPTSOVITS_TTS and not config.params['gptsovits_url']:
        if return_str:
            return "Please configure the api and key information of the GPT-SoVITS channel first."
        from videotrans.winform import gptsovits as gptsovits_win
        gptsovits_win.openwin()
        return False
    if tts_type == COSYVOICE_TTS and not config.params['cosyvoice_url']:
        if return_str:
            return "Please configure the api and key information of the CosyVoice channel first."
        from videotrans.winform import cosyvoice as cosyvoice_win
        cosyvoice_win.openwin()
        return False
    if tts_type == FISHTTS and not config.params['fishtts_url']:
        if return_str:
            return "Please configure the api and key information of the FishTTS channel first."
        from videotrans.winform import fishtts as fishtts_win
        fishtts_win.openwin()
        return False
    if tts_type == CHATTTS and not config.params['chattts_api']:
        if return_str:
            return "Please configure the api and key information of the ChatTTS channel first."
        from videotrans.winform import chattts as chattts_win
        chattts_win.openwin()
        return False
    if tts_type == AZURE_TTS and (not config.params['azure_speech_key'] or not config.params['azure_speech_region']):
        if return_str:
            return "Please configure the api and key information of the Azure TTS channel first."
        from videotrans.winform import  azuretts as azuretts_win
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
    elif tts_type == GPTSOVITS_TTS:
        from videotrans.tts._gptsovits import GPTSoVITS
        GPTSoVITS(**kwargs).run()
    elif tts_type == CLONE_VOICE_TTS:
        from videotrans.tts._clone import CloneVoice
        CloneVoice(**kwargs).run()
    elif tts_type == OPENAI_TTS:
        from videotrans.tts._openaitts import OPENAITTS
        OPENAITTS(**kwargs).run()
    elif tts_type == ELEVENLABS_TTS:
        from videotrans.tts._elevenlabs import ElevenLabs
        ElevenLabs(**kwargs).run()
    elif tts_type == GOOGLE_TTS:
        from videotrans.tts._gtts import GTTS
        GTTS(**kwargs).run()
    elif tts_type == TTS_API:
        from videotrans.tts._ttsapi import TTSAPI
        TTSAPI(**kwargs).run()
