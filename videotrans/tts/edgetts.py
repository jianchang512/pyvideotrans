import asyncio
import sys
import time
import os
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
        if not os.path.exists(filename) or os.path.getsize(filename)<1:
            raise Exception('edgeTTS dubbing error' if config.defaulelang !='zh' else 'edgeTTS配音失败')
    except Exception as e:
        err = str(e)
        config.logger.error(f'[edgeTTS]{err}')
        if err.find("Invalid response status") > 0:
            if set_p:
                tools.set_process("edgeTTS过于频繁暂停5s后重试")
            config.settings['dubbing_thread']=1
            time.sleep(10)
            asyncio.run(communicate.save(filename))
        else:
            raise  Exception(err)
    return True
