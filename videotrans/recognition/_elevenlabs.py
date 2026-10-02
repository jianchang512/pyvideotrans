from dataclasses import dataclass
from typing import List, Union

import httpx
from elevenlabs import ElevenLabs
from elevenlabs.core import ApiError

from videotrans.configure.config import params, settings, logger
from videotrans.configure.excepts import SpeechToTextError
from videotrans.process._stt_utils import _resegment
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem


@dataclass(repr=False)
class ElevenLabsRecogn(BaseRecogn):

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return

        language_code = self.detect_language.split('-')[
            0] if self.detect_language and self.detect_language != 'auto' else None
        try:
            with open(self.audio_file, 'rb') as file:
                file_object = file.read()
            client = ElevenLabs(
                api_key=params.get('elevenlabstts_key', ''),
                httpx_client=httpx.Client(proxy=self.proxy_str)
            )

            logger.debug(f'{language_code=}')
            res = client.speech_to_text.convert(
                model_id=self.model_name,
                file=file_object,
                language_code=language_code,
            )
        except ApiError as e:
            raise SpeechToTextError(e.body)
        else:
            text_words = [{
                'text': '',
                'words': []
            }]
            logger.debug(f'elevenlabs{res=}\n')
            for it in res.words:
                if it.type == 'audio_event':
                    continue
                if not it.text.strip(): continue
                text_words[0]['words'].append({"start": it.start, "end": it.end, "word": it.text})

            min_speech = max(int(float(settings.get('min_speech_duration_ms', 1000))), 3000)
            # 最长片段不得大于25s,并且不得小于 _min_speech
            max_speech = min(int(float(settings.get('max_speech_duration_s', 6)) * 1000), 25000)
            if max_speech <= min_speech:
                max_speech = min_speech + 1000
            return _resegment(text_words, language_code or 'en', max_speech, min_speech, logs_file=None)
