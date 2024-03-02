import os
import threading
import time

from videotrans.configure import config
from videotrans.util import tools

thread_err=[]

# 文字合成
def text_to_speech(stop_event=None,*, text="", role="", rate='+0%',language=None, filename=None, tts_type=None, play=False, set_p=True):
    global thread_err
    try:
        if stop_event and stop_event.is_set():
            return
        if rate != '+0%' and set_p:
            tools.set_process(f'text to speech speed {rate}')
        if tts_type == "edgeTTS":
            from .edgetts import get_voice
            get_voice(text=text, role=role, rate=rate, filename=filename,set_p=set_p)
        elif tts_type == "openaiTTS":
            from .openaitts import get_voice
            get_voice(text=text, role=role, rate=rate, filename=filename,set_p=set_p)
        elif tts_type == "clone-voice":
            from .clone import get_voice
            get_voice(text=text, role=role, language=language, filename=filename,set_p=set_p)
        elif tts_type=='TTS-API':
            from .ttsapi import get_voice
            get_voice(text=text, role=role, language=language, filename=filename,set_p=set_p)
        elif tts_type=='GPT-SoVITS':
            from .gptsovits import get_voice
            get_voice(text=text, role=role, language=language, filename=filename,set_p=set_p)
        elif tts_type == 'elevenlabsTTS':
            from .elevenlabs import get_voice
            get_voice(text=text, role=role, rate=rate, filename=filename,set_p=set_p)
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            if play:
                threading.Thread(target=tools.pygameaudio, args=(filename,)).start()
            return True
        else:
            config.logger.error(f'no filename={filename} {tts_type=} {text=},{role=}')
            return False
    except Exception as e:
        err=str(e)
        if stop_event:
            stop_event.set()
        thread_err.append(err)
        raise Exception(f'{err}')


def run(*, queue_tts=None, language=None,set_p=True,inst=None):
    global thread_err
    thread_err=[]
    stop_event = threading.Event()  # 停止事件
    def get_item(q):
        return {"text": q['text'], "role": q['role'], "rate": q["rate"],
                "filename": q["filename"], "tts_type": q['tts_type'],"language":language}

    # 需要并行的数量3
    n_total = len(queue_tts)
    if n_total<1:
        raise Exception(f'[error]queue_tts length < 1')
    n = 0
    dub_nums=config.settings['dubbing_thread']
    while len(queue_tts) > 0:
        if config.current_status != 'ing' and config.box_tts != 'ing':
            raise config.Myexcept('stop')
        try:
            tolist = []
            for i in range(dub_nums):
                if len(queue_tts) > 0:
                    p=get_item(queue_tts.pop(0))
                    p["set_p"]=set_p
                    tolist.append(threading.Thread(target=text_to_speech, kwargs=p,args=(stop_event,)))
            for t in tolist:
                t.start()
            for t in tolist:
                if len(thread_err)>0:
                    raise Exception(thread_err.pop(0))
                n += 1
                if set_p:
                    if inst and inst.precent<90:
                        inst.precent+=round(n/n_total,2)
                    tools.set_process(f'{config.transobj["kaishipeiyin"]} [{n}/{n_total}]')
                t.join()
        except Exception as e:
            raise config.Myexcept(f'{str(e)}')
    return True
