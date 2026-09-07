import logging
import httpx,time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

from google import genai
from google.genai import types,errors
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopRetry, SpeechToTextError,StopTask
from videotrans.configure.config import params, logger,  settings,tr
from videotrans.configure.contants import GEMINI_ASR_MODELS
from videotrans.process.vad import get_speech_timestamp_silero
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util._srt_parse import ms_to_time_string
from videotrans.process._stt_utils import _resegment
from pydub import AudioSegment

@dataclass
class GeminiRecogn(BaseRecogn):
    api_keys: List[str] = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.api_keys = params.get('gemini_key', '').strip().split(',')
        self.model_name=params.get("gemini_asrmodel",'gemini-3.5-transcribe')
        if self.model_name not in GEMINI_ASR_MODELS.split(','):
            self.model_name='gemini-3.5-transcribe'

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),  after=after_log(logger, logging.INFO))
    def _req(self,file):
        client=None
        try:
            api_key = self.api_keys.pop(0)
            self.api_keys.append(api_key)
            client = genai.Client(
                api_key=api_key,
                http_options = types.HttpOptions(
                    client_args={'proxy': self.proxy_str},
                    async_client_args={'proxy': self.proxy_str},
                ) if self.proxy_str else None
            )
            logger.debug(f'{self.proxy_str=},{self.detect_language=},{self.model_name=}')


            audio_file = client.files.upload(file=file)
            interaction = client.interactions.create(
                model=self.model_name,
                input=[
                    {
                        "type": "audio",
                        "uri": audio_file.uri,
                        "mime_type": audio_file.mime_type,
                    }
                ],
                generation_config={
                    "transcription_config": {
                        "mode": {
                            "type": "verbatim",
                            "timestamp_granularities": ["word"],
                        },
                        "language_codes":[self.detect_language] if self.detect_language !='auto' else []
                    }
                },

            )
            return self.extract_word_annotations(interaction),interaction.output_text
            
        except httpx.ConnectTimeout as e:
            raise StopTask(f' {tr("Unable to connect to remote API","Gemini AI")}\n{e}') from e
        except errors.APIError as e:
            logger.error(str(e))
            if e.code in [400,403,404,429,500]:
                raise StopRetry(e.message)
        finally:
            if client:
                client.close()
        return None,None

    def _exec(self)->Union[List[SrtItem], None]:
        srts = self._cut()
        if len(srts) < 1:
            raise SpeechToTextError(f'VAD error')
        texts = [{
            "start": 0.0,
            "end": 0.0,
            "text": "",
            "words": []
        }]
        _min_speech = max(int(float(settings.get('min_speech_duration_ms', 1000))), 1000)
        _max_speech = max(min(int(float(settings.get('max_speech_duration_s', 6)) * 1000), 20000), _min_speech + 1000)
        for i,it in enumerate(srts):                       
            words,_text=self._req(it['filename'])
            offset = it['start_time'] / 1000.0
            for j,w in enumerate(words):
                st=float(w.start_offset.replace('s',''))
                et=float(w.end_offset.replace('s',''))
                if i==0:
                    texts[0]['start']=st
                texts[0]['words'].append({"word": w.text, "start": st + offset, "end": et + offset})
                if i==len(srts)-1 and j==len(words)-1:
                    texts[0]['end']=et
            self.signal(
                text=f"{_text[:120]}\n",
                type='subtitle'
            )
            if self.asr_wait>0:
                time.sleep(self.asr_wait)
        srt_str_list = _resegment(texts, self.detect_language, _max_speech, _min_speech, f"{self.cache_folder}/gemini-stt.log")
        return srt_str_list



    def _cut(self):
        audio = AudioSegment.from_wav(self.audio_file)
        _len=len(audio)
        _min_segments=60000#最小5分钟
        _max_segments=300000#最大10分钟，减少发送次数，避免超频
        if _len<=_max_segments:
            _endraw=ms_to_time_string(ms=_len)
            return [{
                "line":1,
                "text":"",
                "start_time":0,
                "end_time":_len,
                "startraw":'00:00:00,000',
                "endraw":_endraw,
                "time":f'00:00:00,000 --> {_endraw}',
                "filename":self.audio_file
            }]


        dir_name = f"{self.cache_folder}/clip_{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        kw = {
            "input_wav": self.audio_file,
            "threshold": 0.45,
            "min_speech_duration_ms": _min_segments,
            "max_speech_duration_ms": _max_segments,
            "min_silent_duration_ms": 2000
        }
        speech_timestamps=get_speech_timestamp_silero(**kw)

        data = []
        for i, (start_ms, end_ms) in enumerate(speech_timestamps):
            startraw = ms_to_time_string(ms=start_ms)
            endraw = ms_to_time_string(ms=end_ms)
            file_name = f"{dir_name}/audio_{i}.wav"
            chunk = audio[start_ms:end_ms]
            chunk.export(file_name, format="wav")
            data.append({
                "line":i + 1,
                "text":"",
                "start_time":start_ms,
                "end_time":end_ms,
                "startraw":startraw,
                "endraw":endraw,
                "time":f'{startraw} --> {endraw}',
                "filename":file_name
            })
        return data


    def extract_word_annotations(self,interaction):
        words = []
        for step in getattr(interaction, "steps", []) or []:
            for content in getattr(step, "content", []) or []:
                for annotation in getattr(content, "annotations", []) or []:
                    if getattr(annotation, "type", None) == "word_info":
                        words.append(annotation)
        return words

