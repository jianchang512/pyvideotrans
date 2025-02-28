# openai
from pathlib import Path
from typing import Union, List, Dict


from videotrans.configure import config
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools
import copy,re,httpx
from elevenlabs import ElevenLabs


class ElevenLabsRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []


    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = pro

        try:
            with open(self.audio_file, 'rb') as file:
                file_object=file.read()

            client = ElevenLabs(
                    api_key=config.params['elevenlabstts_key'],
                    httpx_client=httpx.Client(proxy=self.proxies) if self.proxies else None
            )      
            
            language_code=self.detect_language[:2] if self.detect_language and self.detect_language!='auto' else ''
            config.logger.info(f'{language_code=}')
            
            
            raws=[]

            flags=[',','.','?','!',';','，','；','。','？','！']
            if language_code:
                res=client.speech_to_text.convert(
                    model_id="scribe_v1",
                    file=file_object,
                    language_code=language_code
                )
            else:
                res=client.speech_to_text.convert(
                    model_id="scribe_v1",
                    file=file_object
                )

            last_tmp=None
            config.logger.info(f'elevenlabs{res=}')
            for it in res.words:
                text=it.text.strip()
                if not last_tmp:
                    last_tmp={
                        "line":len(raws)+1,
                        "text":text,
                        "start_time":int(it.start*1000),
                        "end_time":int(it.end*1000),
                    }
                else:
                    last_tmp['end_time']=int(it.end*1000)
                    last_tmp['text']+= ( '' if language_code in ['ja','zh','ko'] or res.language_code in ['ja','zh','ko'] else ' ') + text
                    if last_tmp['end_time']-last_tmp['start_time']>1000 and (text in flags or not text):
                        last_tmp['time']=tools.ms_to_time_string(ms=last_tmp['start_time'])+' --> '+tools.ms_to_time_string(ms=last_tmp['end_time'])
                        raws.append(last_tmp)
                        last_tmp=None

            if last_tmp:
                last_tmp['time']=tools.ms_to_time_string(ms=last_tmp['start_time'])+' --> '+tools.ms_to_time_string(ms=last_tmp['end_time'])
                raws.append(last_tmp)
            
            return raws
        except Exception as e:
            config.logger.exception(f'{self.detect_language=},{e=}',exc_info=True)
            print(f'{self.detect_language=}')
            raise


