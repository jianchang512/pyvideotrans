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



# Usage
# trimmed_audio = remove_silence_from_end("1.mp3")
# trimmed_audio.export("1_trimmed.mp3", format="mp3")

def get_voice(*, text=None, role=None, rate=None,language=None, filename=None,set_p=True,is_test=False):
    if config.current_status != 'ing' and config.box_tts != 'ing' and not is_test:
        return False
    #text=text.replace('<','&#60;').replace('>','&#62;').replace('&','&#38;').replace('\'','&#39;').replace('"','&#34;').replace('‘','&#8216;').replace('’','&#8217;').replace('“','&#8220;').replace('”','&#8221;').replace('\(','&#40;').replace('\)','&#41;').replace('\[','&#91;').replace('\]','&#93;').replace('\{','&#123;').replace('\}','&#125;').replace('`','&#96;')
    print(f'{text=}')
    communicate = edge_tts.Communicate(text, role, rate=rate)
    try:
        if config.current_status != 'ing' and config.box_tts != 'ing' and not is_test:
            return False
        # print(f'开始配音:{text=},{filename=}')
        asyncio.run(communicate.save(filename))
        # print(f'结束配音:{text=},exists={os.path.exists(filename)}')
        
        # audio=AudioSegment.from_file(filename, format="mp3")
        # audio[:-100].export(filename,format="mp3")
        # 可能非该类语言，比如英语配音中出现中文等
        if not os.path.exists(filename) or os.path.getsize(filename)<1:
            config.logger.error( f'edgeTTS配音失败:{text=},{filename=}')
            return True
        if os.path.exists(filename) and os.path.getsize(filename)>0 and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
    except Exception as e:
        err = str(e)
        config.logger.error(f'[edgeTTS]{text=}{err=},')
        if err.find("Invalid response status") > 0 or err.find('WinError 10054')>-1:
            if set_p:
                tools.set_process("edgeTTS过于频繁暂停5s后重试")
            config.settings['dubbing_thread']=1
            time.sleep(10)
            asyncio.run(communicate.save(filename))
        elif set_p:
            tools.set_process("有一个配音出错")
            config.logger.error( f'edgeTTS配音有一个失败:{text=},{filename=}')
    return True
