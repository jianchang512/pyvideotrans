from dataclasses import dataclass
from typing import List, Union

from openai import OpenAI

from videotrans.configure.excepts import SpeechToTextError
from videotrans.configure.config import tr, params
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools

@dataclass
class ParaketRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = params.get('parakeet_address', '')

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        client = OpenAI(api_key='123456', base_url=self.api_url)

        with open(self.audio_file, 'rb') as file:
            transcript = client.audio.transcriptions.create(
                file=(self.audio_file, file.read()),
                model='parakeet_srt_words',
                prompt=self.detect_language[:2].lower(),
                response_format="srt",
                timeout=3600
            )
            if not transcript or not isinstance(transcript, str):
                raise SpeechToTextError(tr('The returned subtitles have no timestamp and cannot be used'))
        return tools.get_subtitle_from_srt(transcript.split("----..----")[0], is_file=False)
