import asyncio
import re
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




def get_voice(*,
              text=None,
              role=None,
              rate="+0%",
              language=None,
              filename=None,
              set_p=True,
              inst=None,
              pitch="+0Hz",
              volume="+0%"
              ):
    if not re.match(r'^[+-]\d+%$',volume):
        volume='+0%'
    if not re.match(r'^[+-]\d+%$',rate):
        rate='+0%'
    if not re.match(r'^[+-]\d+Hz$',pitch,re.I):
        pitch='+0Hz'
    communicate = edge_tts.Communicate(text, role, rate=rate,volume=volume,pitch=pitch)
    try:
        asyncio.run(communicate.save(filename))
        if not tools.vail_file(filename):
            config.logger.error( f'edgeTTS配音失败:{text=},{filename=}')
            return True
        if tools.vail_file(filename) and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        if set_p and inst and inst.precent<80:
            inst.precent+=0.1
            tools.set_process(f'{config.transobj["kaishipeiyin"]} ',btnkey=inst.init['btnkey'] if inst else "")

    except Exception as e:
        err = str(e)
        config.logger.error(f'[edgeTTS]{text=}{err=},')
        if err.find("Invalid response status") > 0 or err.find('WinError 10054')>-1:
            if set_p:
                tools.set_process("edgeTTS过于频繁暂停5s后重试",btnkey=inst.init['btnkey'] if inst else "")
            config.settings['dubbing_thread']=1
            time.sleep(10)
            return get_voice(
              text=text,
              role=role,
              rate=rate,
              language=language,
              filename=filename,
              set_p=set_p,
              inst=inst,
              pitch=pitch,
              volume=volume
            )
        elif set_p:
            tools.set_process("有一个配音出错",btnkey=inst.init['btnkey'] if inst else "")
            config.logger.error( f'edgeTTS配音有一个失败:{text=},{filename=}')
        if inst and inst.init['btnkey']:
            config.errorlist[inst.init['btnkey']]=err
        raise Exception(err)
    else:
        return True