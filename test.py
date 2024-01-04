import json
import os.path
import re

from elevenlabs import generate, play,voices
from videotrans.configure import config

def get_elevenlabs_role():
  jsonfile=os.path.join(config.rootdir,'elevenlabs.json')
  voiceslist = voices()
  result={}
  for it in voiceslist:
    result[re.sub(r'[^a-zA-Z0-9_ -]+','',it.name).strip()]={"voice_id":it.voice_id,'url':it.preview_url}
  with open(jsonfile,'w',encoding="utf-8") as f:
    f.write(json.dumps(result))
  return result

# print(get_elevenlabs_role())
# exit()
#
try:
  audio = generate(
    text="Hello! 你好! ",
    voice="Santa Claus",
    model="eleven_multilingual_v2"
  )
  play(audio)
except Exception as e:
  print(e)
# with open("./2.wav","rb") as f:
#   play(f.read())