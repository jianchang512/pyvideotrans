import copy
import os
import threading
from videotrans.configure import config
from videotrans.util import tools

lasterror=""
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
        play=False,
        set_p=True):
    global lasterror
    get_voice=None
    if tts_type == "edgeTTS":
        from .edgetts import get_voice
        # lasterror=get_voice(text=text, role=role, rate=rate, language=language,filename=filename,set_p=set_p,inst=inst,volume=volume,pitch=pitch)
    elif tts_type == "AzureTTS":
        from .azuretts import get_voice
        # lasterror=get_voice(text=text, role=role, rate=rate, language=language,filename=filename,set_p=set_p,inst=inst)
    elif tts_type == "openaiTTS":
        from .openaitts import get_voice
        # lasterror=get_voice(text=text, role=role, rate=rate, language=language,filename=filename,set_p=set_p,inst=inst)
    elif tts_type == "clone-voice":
        from .clone import get_voice
        # lasterror=get_voice(text=text, role=role, language=language, filename=filename,set_p=set_p,inst=inst)
    elif tts_type=='TTS-API':
        from .ttsapi import get_voice
        # lasterror=get_voice(text=text, role=role, language=language, filename=filename,set_p=set_p,inst=inst)
    elif tts_type=='GPT-SoVITS':
        from .gptsovits import get_voice
        # lasterror=get_voice(text=text, role=role, language=language, filename=filename,set_p=set_p,inst=inst)
    elif tts_type == 'elevenlabsTTS':
        from .elevenlabs import get_voice
        # lasterror=get_voice(text=text, role=role, rate=rate,language=language, filename=filename,set_p=set_p,inst=inst)
    elif tts_type =='gtts':
        from .gtts import get_voice
    elif tts_type=='ChatTTS':
        from .chattts import get_voice
        # lasterror=get_voice(text=text, role=role, rate=rate, language=language,filename=filename,set_p=set_p,inst=inst)

    if get_voice:
        get_voice(
                text=text,
                volume=volume,
                pitch=pitch,
                role=role,
                rate=rate,
                language=language,
                filename=filename,
                set_p=set_p,
                inst=inst)
    if tools.vail_file(filename):
        if play:
            threading.Thread(target=tools.pygameaudio, args=(filename,)).start()
    else:
        config.logger.error(f'no filename={filename} {tts_type=} {text=},{role=}')


def run(*, queue_tts=None, language=None, set_p=True, inst=None):
    queue_tts_copy=copy.deepcopy(queue_tts)
    # 需要并行的数量3
    n_total = len(queue_tts)
    if n_total<1:
        return False

    n = 0
    dub_nums=config.settings['dubbing_thread']
    while len(queue_tts) > 0:
        if config.exit_soft or (config.current_status != 'ing' and config.box_tts != 'ing'):
            return True
        try:
            tolist = []
            for i in range(dub_nums):
                if len(queue_tts) > 0:
                    p=queue_tts.pop(0)
                    if p['tts_type']!='clone-voice' and tools.vail_file(p['filename']):
                        continue
                    tolist.append(threading.Thread(target=text_to_speech, kwargs={
                        "text":p['text'],
                        "role":p['role'],
                        "rate":p['rate'],
                        "pitch":p['pitch'],
                        "volume":p['volume'],
                        "filename":p['filename'],
                        "tts_type":p['tts_type'],
                        "set_p":set_p,
                        "inst":inst,
                        "language":language
                    }))
            if len(tolist)<1:
                continue
            for t in tolist:
                t.start()
            for t in tolist:
                n += 1
                if set_p and inst:
                    tools.set_process(f'{config.transobj["kaishipeiyin"]} [{n}/{n_total}]',btnkey=inst.init['btnkey'])
                t.join()
        except Exception as e:
            print(f'runtts:{str(e)}')
           
    err=0
    for it in queue_tts_copy:
        if not tools.vail_file(it['filename']):
            err+=1
    if err>=(n_total/3):
        raise Exception(f'{config.transobj["peiyindayu31"]}:{lasterror if lasterror is not True else ""}')
    return True
