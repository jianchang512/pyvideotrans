import copy
import threading

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.tts._azuretts import AzureTTS
from videotrans.tts._chattts import ChatTTS
from videotrans.tts._clone import CloneVoice
from videotrans.tts._cosyvoice import CosyVoice
from videotrans.tts._edgetts import EdgeTTS

from videotrans.tts._ai302tts import AI302
from videotrans.tts._elevenlabs import ElevenLabs
from videotrans.tts._fishtts import FishTTS
from videotrans.tts._gptsovits import GPTSoVITS
from videotrans.tts._gtts import GTTS
from videotrans.tts._openaitts import OPENAITTS
from videotrans.tts._ttsapi import TTSAPI
from videotrans.util import tools
from videotrans.winform import openaitts as openaitts_win, ai302tts as ai302tts_win, clone as clone_win, \
    elevenlabs as elevenlabs_win, ttsapi as ttsapi_win, gptsovits as gptsovits_win, cosyvoice as cosyvoice_win, \
    fishtts as fishtts_win, chattts as chattts_win, \
    azuretts as azuretts_win

lasterror = ""

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
def is_input_api(tts_type: int = None):
    if tts_type == OPENAI_TTS and not config.params["chatgpt_key"]:
        openaitts_win.open()
        return False
    if tts_type == AI302_TTS and not config.params["ai302tts_key"]:
        ai302tts_win.open()
        return False
    if tts_type == CLONE_VOICE_TTS and not config.params["clone_api"]:
        clone_win.open()
        return False
    if tts_type == ELEVENLABS_TTS and not config.params["elevenlabstts_key"]:
        elevenlabs_win.open()
        return False
    if tts_type == TTS_API and not config.params['ttsapi_url']:
        ttsapi_win.open()
        return False
    if tts_type == GPTSOVITS_TTS and not config.params['gptsovits_url']:
        gptsovits_win.open()
        return False
    if tts_type == COSYVOICE_TTS and not config.params['cosyvoice_url']:
        cosyvoice_win.open()
        return False
    if tts_type == FISHTTS and not config.params['fishtts_url']:
        fishtts_win.open()
        return False
    if tts_type == CHATTTS and not config.params['chattts_api']:
        chattts_win.open()
        return False
    if tts_type == AZURE_TTS and (not config.params['azure_speech_key'] or not config.params['azure_speech_region']):
        azuretts_win.open()
        return False
    return True


# 文字合成
def text_to_speech(
        inst=None,
        text="",
        role="",
        rate='+0%',
        pitch="+0Hz",
        volume="+0%",
        language=None,
        filename=None,
        tts_type=None,
        uuid=None,
        play=False,
        set_p=True):
    pass
    # global lasterror
    # get_voice = None
    # # if tts_type == EDGE_TTS:
    # #     from .edgetts import get_voice
    # # elif tts_type == AZURE_TTS:
    # #     from .azuretts import get_voice
    # elif tts_type == OPENAI_TTS:
    #     from .openaitts import get_voice
    # elif tts_type == CLONE_VOICE_TTS:
    #     from .clone import get_voice
    # elif tts_type == TTS_API:
    #     from .ttsapi import get_voice
    # elif tts_type == GPTSOVITS_TTS:
    #     from .gptsovits import get_voice
    # elif tts_type == COSYVOICE_TTS:
    #     from .cosyvoice import get_voice
    # elif tts_type == FISHTTS:
    #     from .fishtts import get_voice
    # elif tts_type == ELEVENLABS_TTS:
    #     from .elevenlabs import get_voice
    # elif tts_type == GOOGLE_TTS:
    #     from .gtts import get_voice
    # elif tts_type == CHATTTS:
    #     from .chattts import get_voice
    # elif tts_type == AI302_TTS:
    #     from .ai302tts import get_voice
    #
    # if get_voice:
    #     try:
    #         get_voice(
    #             text=text,
    #             volume=volume,
    #             pitch=pitch,
    #             role=role,
    #             rate=rate,
    #             language=language,
    #             filename=filename,
    #             uuid=uuid,
    #             set_p=set_p,
    #             inst=inst)
    #     except Exception as e:
    #         lasterror = str(e)
    # if tools.vail_file(filename):
    #     if play:
    #         threading.Thread(target=tools.pygameaudio, args=(filename,)).start()
    # else:
    #     config.logger.error(f'no filename={filename} {tts_type=} {text=},{role=}')



def run(*, queue_tts=None, language=None, inst=None, uuid=None,play=False,is_test=False)->None:
    # 需要并行的数量3
    if len(queue_tts) < 1:
        return

    if config.exit_soft  or ( not is_test and config.current_status != 'ing' and config.box_tts != 'ing'):
        return
    tts_type=queue_tts[0]['tts_type']
    obj=None
    kwargs={
        "queue_tts":queue_tts,
        "language":language,
        "inst":inst,
        "uuid":uuid,
        "play":play,
        "is_test":is_test
    }
    if tts_type == AZURE_TTS:
        obj=AzureTTS(**kwargs)
    elif tts_type==EDGE_TTS:
        obj=EdgeTTS(**kwargs)
    elif tts_type==AI302_TTS:
        obj=AI302(**kwargs)
    elif tts_type==COSYVOICE_TTS:
        obj=CosyVoice(**kwargs)
    elif tts_type==CHATTTS:
        obj=ChatTTS(**kwargs)
    elif tts_type==FISHTTS:
        obj=FishTTS(**kwargs)
    elif tts_type==GPTSOVITS_TTS:
        obj=GPTSoVITS(**kwargs)
    elif tts_type==CLONE_VOICE_TTS:
        obj=CloneVoice(**kwargs)
    elif tts_type==OPENAI_TTS:
        obj=OPENAITTS(**kwargs)
    elif tts_type==ELEVENLABS_TTS:
        obj=ElevenLabs(**kwargs)
    elif tts_type==GOOGLE_TTS:
        obj=GTTS(**kwargs)
    elif tts_type==TTS_API:
        obj=TTSAPI(**kwargs)
    if obj is None:
        raise Exception('No dubbing channel')
    obj.run()

    err = 0
    for it in queue_tts:
        if not tools.vail_file(it['filename']):
            err += 1
    if err >= (len(queue_tts) / 3):
        raise LogExcept(f'{config.transobj["peiyindayu31"]}:{obj.error if obj.error  else ""}')
    return
