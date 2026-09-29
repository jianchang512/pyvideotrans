from dataclasses import dataclass
from typing import List, Union
import httpx
from deepgram import (
    DeepgramClient
)
from deepgram.core import ApiError

from videotrans.configure.config import tr,params,settings
from videotrans.configure.excepts import SpeechToTextError
from videotrans.process._stt_utils import _resegment
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util._ffmpeg_runner import runffmpeg


@dataclass
class DeepgramRecogn(BaseRecogn):

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        runffmpeg( ['-y', '-i', self.audio_file, '-ac', '1', '-ar', '16000', self.cache_folder + '/deepgram-tmp.mp3'])
        self.audio_file = self.cache_folder + '/deepgram-tmp.mp3'
        with open(self.audio_file, "rb") as file:
            buffer_data = file.read()
        self.signal(
            text=tr("Recognition may take a while, please be patient"))

        httpx.HTTPTransport(proxy=self.proxy_str)

        client = DeepgramClient(api_key=params.get('deepgram_apikey'))
        language=self.detect_language.split('-')[0]
        options=dict(request=buffer_data,
            model=self.model_name,
            smart_format=True,
            punctuate=True,
            utterances=True,
            utt_split=int(settings.get('min_silence_duration_ms', 600)) / 1000)

        if language=='auto':
            options['detect_language']=True
        else:
            options['language']=language
        try:
           response = client.listen.v1.media.transcribe_file(
                **options,
                request_options={"timeout":600}
            )
        except ApiError as e:
            raise SpeechToTextError(e.body)
        except httpx.ReadTimeout:
            raise SpeechToTextError('Timeout, try again')
        else:
            if language=='auto' and response.results.channels[0].detected_language:
                language=response.results.channels[0].detected_language

            text_words=[]
            for i,it in enumerate(response.results.utterances):
                tmp={
                    'text':it.transcript,
                    'words':[]
                }
                for w in it.words:
                    tmp['words'].append({"start":w.start,"end":w.end,"word":w.punctuated_word})
                text_words.append(tmp)

            min_speech = max(int(float(settings.get('min_speech_duration_ms', 1000))), 3000)
            # 最长片段不得大于25s,并且不得小于 _min_speech
            max_speech = min(int(float(settings.get('max_speech_duration_s', 6)) * 1000), 25000)
            if max_speech<=min_speech:
                max_speech=min_speech+1000
            return _resegment(text_words, language, max_speech, min_speech, logs_file=None)
