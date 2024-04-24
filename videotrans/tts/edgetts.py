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




def get_voice(*, text=None, role=None, rate=None,language=None, filename=None,set_p=True,is_test=False,inst=None):
    if config.current_status != 'ing' and config.box_tts != 'ing' and not is_test:
        return False
    communicate = edge_tts.Communicate(text, role, rate=rate)
    try:
        if config.current_status != 'ing' and config.box_tts != 'ing' and not is_test:
            return False
        asyncio.run(communicate.save(filename))
        if not tools.vail_file(filename):
            config.logger.error( f'edgeTTS配音失败:{text=},{filename=}')
            return True
        if tools.vail_file(filename) and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p and inst and inst.precent<80:
            inst.precent+=0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ',btnkey=inst.btnkey if inst else "")
    except Exception as e:
        err = str(e)
        config.logger.error(f'[edgeTTS]{text=}{err=},')
        if err.find("Invalid response status") > 0 or err.find('WinError 10054')>-1:
            if set_p:
                tools.set_process("edgeTTS过于频繁暂停5s后重试",btnkey=inst.btnkey if inst else "")
            config.settings['dubbing_thread']=1
            time.sleep(10)
            asyncio.run(communicate.save(filename))
        elif set_p:
            tools.set_process("有一个配音出错",btnkey=inst.btnkey if inst else "")
            config.logger.error( f'edgeTTS配音有一个失败:{text=},{filename=}')
        if inst and inst.btnkey:
            config.errorlist[inst.btnkey]=err
    return True
