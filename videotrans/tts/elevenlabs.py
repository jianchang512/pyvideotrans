import json
import os
from elevenlabs import generate, Voice,set_api_key
from videotrans.configure import config
from videotrans.util import tools


def get_voice(*,text=None, role=None, rate=None,language=None, filename=None,set_p=True):
    try:
        with open(os.path.join(config.rootdir,'elevenlabs.json'),'r',encoding="utf-8") as f:
            jsondata=json.loads(f.read())
        if config.params['elevenlabstts_key']:
            set_api_key(config.params['elevenlabstts_key'])
        if config.current_status != 'ing' and config.box_tts != 'ing':
            return False
        audio = generate(
            text=text,
            voice=Voice(voice_id=jsondata[role]['voice_id']),
            model="eleven_multilingual_v2"
        )
        with open(filename,'wb') as f:
            f.write(audio)
        if os.path.exists(filename) and os.path.getsize(filename)>0 and config.settings['remove_silence']:
            tools.remove_silence_from_end(filename)
        return True
    except Exception as e:
        error=str(e)
        if set_p:
            tools.set_process(f'elevenlabs:{error}')
        config.logger.error(f"elevenlabsTTS：request error:{error}")
        raise Exception(f"elevenlabsTTS:{error}")
