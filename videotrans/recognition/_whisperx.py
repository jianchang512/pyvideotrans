# zh_recogn 识别
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import httpx
from openai import OpenAI
from pydub import AudioSegment
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class WhisperXRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.api_url = params.get('whisperx_api', 'http://127.0.0.1:9092')
        self._add_internal_host_noproxy(self.api_url)


    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        # self.model_name
        client = OpenAI(
            api_key='123456',
            base_url=self.api_url.rstrip('/')+"/v1"
        )
        raws = []
        speaker_list = []
        speaker_name = []
        logger.debug(f'[whisperx-api]:指定最大说话人：{self.max_speakers=}')
        with open(self.audio_file, 'rb') as file:

            transcript = client.audio.transcriptions.create(
                file=(self.audio_file, file.read()),
                model=self.model_name,
                language=self.detect_language[:2].lower(),
                response_format="diarized_json",
                extra_body={
                  "max_speakers": self.max_speakers #-1不启用，0=不限制数量，>0 最大数量
                },
            )

            if not hasattr(transcript, 'segments') or not transcript.segments:
                raise RuntimeError('No support gpt-4o-transcribe-diarize')
            for it in transcript.segments:
                raws.append({
                    "line": len(raws) + 1,
                    "start_time": it.start * 1000,
                    "end_time": it.end * 1000,
                    "text": it.text,
                    "time": tools.ms_to_time_string(ms=it.start * 1000) + ' --> ' + tools.ms_to_time_string(
                        ms=it.end * 1000),

                })
                if self.max_speakers>-1:
                    sp = getattr(it,"speaker",'-')
                    speaker_list.append(sp)
                    if sp not in speaker_name:
                        speaker_name.append(sp)

        if speaker_name:
            try:
                #默认未识别出后的回退说话人
                next_spk=f'spk{len(speaker_name)}'
                for i,it in enumerate(speaker_list):
                    if it=='-':
                        speaker_list[i]=next_spk
                    else:
                        speaker_list[i]=f'spk{speaker_name.index(it)}'
                if speaker_list:
                    Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
            except Exception as e:
                logger.exception(f'说话人重排序出错，忽略{e}',exc_info=True)
        return raws


