import asyncio
import sys

import edge_tts

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
def get_voice(*,text,role,rate,filename):
    communicate = edge_tts.Communicate(text, role, rate=rate)
    asyncio.run(communicate.save(filename))
    return True