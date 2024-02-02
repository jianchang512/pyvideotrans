import asyncio
import sys
import time

import edge_tts

from videotrans.configure import config
from videotrans.util import tools

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


def get_voice(*, text=None, role=None, rate=None,language=None, filename=None,set_p=True):
    communicate = edge_tts.Communicate(text, role, rate=rate)
    try:
        asyncio.run(communicate.save(filename))
    except Exception as e:
        err = str(e)
        if err.find("Invalid response status") > 0:
            if set_p:
                tools.set_process("edgeTTS过于频繁暂停5s后重试")
            config.settings['dubbing_thread']=1
            time.sleep(5)
            asyncio.run(communicate.save(filename))
    return True
