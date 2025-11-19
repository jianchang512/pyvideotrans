# zh_recogn 识别
import json
from dataclasses import dataclass
from typing import List, Dict, Union

from openai import OpenAI


from videotrans.configure import config
from videotrans.configure._except import  StopRetry
from videotrans.configure.config import tr, logs
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class ParaketRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = config.params.get('parakeet_address','')
        self._add_internal_host_noproxy(self.api_url)

    #@retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
    #       wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
    #       after=after_log(config.logger, logging.INFO))
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        # 发送请求

        client = OpenAI(api_key='123456', base_url=self.api_url)

        with open(self.audio_file, 'rb') as file:
            transcript = client.audio.transcriptions.create(
                file=(self.audio_file, file.read()),
                model='parakeet_srt_words',
                prompt=self.detect_language[:2].lower(),
                response_format="srt"
            )
            if not transcript or not isinstance(transcript, str):
                raise StopRetry(tr('The returned subtitles have no timestamp and cannot be used'))
        tmp = transcript.split("----..----")

        if len(tmp)==1 or  int(config.settings.get('rephrase',0))==0:
            return tools.get_subtitle_from_srt(tmp[0], is_file=False)
        
        words_list=[]
        try:
            words_list=json.loads(tmp[1])
        except json.JSONDecodeError:
            logs(f'获取 api 返回的word列表json格式化失败')
            words_list=[]
        
        if not words_list:    
            return tools.get_subtitle_from_srt(tmp[0], is_file=False)
            
        if int(config.settings.get('rephrase',0))==1:
            try:
                return self.re_segment_sentences(words_list)
            except Exception as e:
                logs(f'LLM重新断句失败', level="except")
        else:
            try:
                return self.re_segment_sentences_local(words_list)
            except Exception as e:
                logs(f'本地重新断句失败', level="except")
        
        return tools.get_subtitle_from_srt(tmp[0], is_file=False)
