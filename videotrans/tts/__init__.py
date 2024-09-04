import copy
import threading

from videotrans.configure import config
from videotrans.configure._except import LogExcept
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
    "edgeTTS",
    'CosyVoice',
    "ChatTTS",
    "302.ai",
    "FishTTS",
    "AzureTTS",
    "GPT-SoVITS",
    "clone-voice",
    "OpenAI TTS",
    "elevenlabs.io",
    "Google TTS",
    "自定义TTS API" if config.defaulelang == 'zh' else 'Customize TTS api'
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
    global lasterror
    get_voice = None
    if tts_type == EDGE_TTS:
        from .edgetts import get_voice
    elif tts_type == AZURE_TTS:
        from .azuretts import get_voice
    elif tts_type == OPENAI_TTS:
        from .openaitts import get_voice
    elif tts_type == CLONE_VOICE_TTS:
        from .clone import get_voice
    elif tts_type == TTS_API:
        from .ttsapi import get_voice
    elif tts_type == GPTSOVITS_TTS:
        from .gptsovits import get_voice
    elif tts_type == COSYVOICE_TTS:
        from .cosyvoice import get_voice
    elif tts_type == FISHTTS:
        from .fishtts import get_voice
    elif tts_type == ELEVENLABS_TTS:
        from .elevenlabs import get_voice
    elif tts_type == GOOGLE_TTS:
        from .gtts import get_voice
    elif tts_type == CHATTTS:
        from .chattts import get_voice
    elif tts_type == AI302_TTS:
        from .ai302tts import get_voice

    if get_voice:
        try:
            get_voice(
                text=text,
                volume=volume,
                pitch=pitch,
                role=role,
                rate=rate,
                language=language,
                filename=filename,
                uuid=uuid,
                set_p=set_p,
                inst=inst)
        except Exception as e:
            lasterror = str(e)
    if tools.vail_file(filename):
        if play:
            threading.Thread(target=tools.pygameaudio, args=(filename,)).start()
    else:
        config.logger.error(f'no filename={filename} {tts_type=} {text=},{role=}')


# 单独处理 AzureTTS 批量
def _azuretts(queue_tts, language=None, set_p=False, inst=None, uuid=None):
    from .azuretts import get_voice
    num = int(config.settings['azure_lines'])
    qlist = [queue_tts[i:i + num] for i in range(0, len(queue_tts), num)]
    for i, q in enumerate(qlist):
        get_voice(
            text=q,
            volume=queue_tts[0]["volume"],
            pitch=queue_tts[0]["pitch"],
            role=queue_tts[0]["role"],
            rate=queue_tts[0]["rate"],
            language=language,
            uuid=uuid,
            set_p=set_p)
        if inst:
            inst.precent += 1
        tools.set_process(f"AzureTTS...", type="logs", uuid=uuid)


def run(*, queue_tts=None, language=None, set_p=True, inst=None, uuid=None):
    queue_tts_copy = copy.deepcopy(queue_tts)
    # 需要并行的数量3
    n_total = len(queue_tts)
    if n_total < 1:
        return False

    n = 0
    dub_nums = int(config.settings['dubbing_thread'])
    if config.exit_soft or (config.current_status != 'ing' and config.box_tts != 'ing'):
        return True
    if len(queue_tts) > 0 and queue_tts[0]['tts_type'] == AZURE_TTS:
        _azuretts(queue_tts, language=language, set_p=set_p, inst=inst, uuid=uuid)
    else:
        while len(queue_tts) > 0:
            if config.exit_soft or (config.current_status != 'ing' and config.box_tts != 'ing'):
                return True
            try:
                tolist = []
                for i in range(dub_nums):
                    if len(queue_tts) > 0:
                        p = queue_tts.pop(0)
                        if p['role'] != 'clone' and tools.vail_file(p['filename']):
                            continue
                        tolist.append(threading.Thread(target=text_to_speech, kwargs={
                            "text": p['text'],
                            "role": p['role'],
                            "rate": p['rate'],
                            "pitch": p['pitch'],
                            "volume": p['volume'],
                            "filename": p['filename'],
                            "tts_type": p['tts_type'],
                            "set_p": set_p,
                            "inst": inst,
                            "language": language
                        }))
                if len(tolist) < 1:
                    continue
                for t in tolist:
                    t.start()
                for t in tolist:
                    n += 1
                    if set_p:
                        tools.set_process(f'{config.transobj["kaishipeiyin"]} [{n}/{n_total}]', type="logs", uuid=uuid)
                    t.join()
            except Exception as e:
                print(f'runtts:{str(e)}')

    err = 0
    for it in queue_tts_copy:
        if not tools.vail_file(it['filename']):
            err += 1
    if err >= (n_total / 3):
        raise LogExcept(f'{config.transobj["peiyindayu31"]}:{lasterror if lasterror is not True else ""}')
    return True
