# openai
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Union

import httpx
from elevenlabs import ElevenLabs
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import   NO_RETRY_EXCEPT
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class ElevenLabsRecogn(BaseRecogn):
    raws: List = field(init=False, default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = pro

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        with open(self.audio_file, 'rb') as file:
            file_object = file.read()
        
        client = ElevenLabs(
            api_key=config.params['elevenlabstts_key'],
            httpx_client=httpx.Client(proxy=self.proxies) if self.proxies else None
        )

        language_code = self.detect_language[:2] if self.detect_language and self.detect_language != 'auto' else ''
        config.logger.info(f'{language_code=}')

        raws = []
        if language_code:
            res = client.speech_to_text.convert(
                model_id="scribe_v1",
                file=file_object,
                language_code=language_code,
                diarize=True
            )
        else:
            res = client.speech_to_text.convert(
                model_id="scribe_v1",
                file=file_object,
                diarize=True
            )
        last_tmp = None
        config.logger.info(f'elevenlabs{res=}\n')
        for it in res.words:
            if it.type=='audio_event':
                continue
            text = it.text
            isflag=text[0] in self.flag or text[-1] in self.flag
            spk = it.speaker_id.replace('speaker_', '')
            
            st = int(it.start * 1000)
            end = int(it.end * 1000)

            

                
            if not last_tmp:
                if not text.strip():
                    continue
                last_tmp = {
                    "line": len(raws) + 1,
                    "text": text,
                    "start_time": st,
                    "end_time": end,
                    "spk": spk
                }
                continue
            
            # 如果静音超过 200 并且句子时长已超过500，并且有标点，则断句
            diff_prev=st - last_tmp['end_time']
            segment_time=last_tmp['end_time'] - last_tmp['start_time']
            
            config.logger.info(f'\n{text=},{isflag=},{spk=},{diff_prev=},{segment_time=}\n')
            
            # 不同说话人，强制断句
            
            if spk != last_tmp['spk']:
                last_tmp['time'] = tools.ms_to_time_string(
                    ms=last_tmp['start_time']) + ' --> ' + tools.ms_to_time_string(ms=last_tmp['end_time'])
                config.logger.info(f'segments-spk:{last_tmp=}')
                if last_tmp['text'].strip():
                    raws.append(last_tmp)
                last_tmp = {
                    "line": len(raws) + 1,
                    "text": text,
                    "start_time": st,
                    "end_time": end,
                    "spk": spk
                }
                continue
            
            
            
            if (diff_prev >= 200 or segment_time>= 500) and isflag:
                # 如果标点在开始，则该word给下个，否则给当前
                if text[0] in self.flag:
                    last_tmp['text']+=text[0]
                    last_tmp['time'] = tools.ms_to_time_string(
                    ms=last_tmp['start_time']) + ' --> ' + tools.ms_to_time_string(ms=last_tmp['end_time'])
                    config.logger.info(f'segments-flag0:{last_tmp=}')
                    if last_tmp['text'].strip():
                        raws.append(last_tmp)
                    last_tmp = {
                        "line": len(raws) + 1,
                        "text": text[1:],
                        "start_time": st,
                        "end_time": end,
                        "spk": spk
                    }
                    continue
                    
                last_tmp['end_time'] = end
                last_tmp['text'] += text
                last_tmp['time'] = tools.ms_to_time_string(
                    ms=last_tmp['start_time']) + ' --> ' + tools.ms_to_time_string(ms=end)
                config.logger.info(f'segments-flag1:{last_tmp=}')
                if last_tmp['text'].strip():
                    raws.append(last_tmp)
                last_tmp = None
            else:
                last_tmp['end_time'] = end
                last_tmp['text'] +=text

        if last_tmp and last_tmp['text'].strip():
            last_tmp['time'] = tools.ms_to_time_string(ms=last_tmp['start_time']) + ' --> ' + tools.ms_to_time_string(
                ms=last_tmp['end_time'])
            config.logger.info(f'segments:{last_tmp=}')
            
            raws.append(last_tmp)
        return raws
