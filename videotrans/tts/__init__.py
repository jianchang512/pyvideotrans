import os
import threading
import time

from videotrans.configure import config
from videotrans.util import tools


# 文字合成
def text_to_speech(*, text="", role="", rate='+0%', filename=None, tts_type=None, play=False, set_p=True):
    try:
        if rate != '+0%' and set_p:
            tools.set_process(f'text to speech speed {rate}')
        if tts_type == "edgeTTS":
            from .edgetts import get_voice
            if not get_voice(text=text, role=role, rate=rate, filename=filename):
                raise Exception(f"edgeTTS error")
        elif tts_type == "openaiTTS":
            from .openaitts import get_voice
            if not get_voice(text, role, rate, filename):
                raise Exception(f"openaiTTS error")
        elif tts_type == 'elevenlabsTTS':
            from .elevenlabs import get_voice
            if not get_voice(text, role, rate, filename):
                raise Exception(f"elevenlabsTTS error")
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            if play:
                threading.Thread(target=tools.pygameaudio, args=(filename,)).start()
            return True
        else:
            config.logger.error(f'no filename={filename} {tts_type=} {text=},{role=}')
            return False
    except Exception as e:
        err=str(e)
        raise Exception(f'error:{err}')


def run(*, queue_tts=None, set_p=True):
    def get_item(q):
        return {"text": q['text'], "role": q['role'], "rate": q["rate"],
                "filename": q["filename"], "tts_type": q['tts_type']}

    # 需要并行的数量3
    n_total = len(queue_tts)
    n = 0
    while len(queue_tts) > 0:
        if config.current_status != 'ing' and config.box_status != 'ing':
            raise config.Myexcept('Had stop')
        try:
            tolist = []
            for i in range(config.settings['dubbing_thread']):
                if len(queue_tts) > 0:
                    p=get_item(queue_tts.pop(0))
                    p["set_p"]=set_p
                    tolist.append(threading.Thread(target=text_to_speech, kwargs=p))
            for t in tolist:
                t.start()
            for t in tolist:
                n += 1
                if set_p:
                    tools.set_process(f'{config.transobj["kaishipeiyin"]} [{n}/{n_total}]')
                t.join()
        except Exception as e:
            raise config.Myexcept(f'[error]exec_tts:{str(e)}')
    return True
