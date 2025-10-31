# stt项目识别接口
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Dict,  Union

from pathlib import Path
import json

import httpx
import zhconv
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
from deepgram_captions import DeepgramConverter, srt
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.configure.config import tr,logs
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class DeepgramRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        if os.path.getsize(self.audio_file) > 52428800:
            tools.runffmpeg(
                ['-y', '-i', self.audio_file, '-ac', '1', '-ar', '16000', self.cache_folder + '/deepgram-tmp.mp3'])
            self.audio_file = self.cache_folder + '/deepgram-tmp.mp3'
        with open(self.audio_file, "rb") as file:
            buffer_data = file.read()
        self._signal(
            text=tr("Recognition may take a while, please be patient"))

        httpx.HTTPTransport(proxy=self.proxy_str)

        deepgram = DeepgramClient(config.params.get('deepgram_apikey'))
        payload: FileSource = {
            "buffer": buffer_data,
        }

        diarize = config.params.get('paraformer_spk', False)
        options = PrerecordedOptions(
            model=self.model_name,
            # detect_language=True,
            language=self.detect_language[:2],
            smart_format=True,
            punctuate=True,
            paragraphs=True,
            utterances=True,
            diarize=diarize,

            utt_split=int(config.settings.get('min_silence_duration_ms', 140)) / 1000,
        )

        res = deepgram.listen.rest.v("1").transcribe_file(payload, options, timeout=600)

        raws = []
        if diarize:
            speaker_list=[]
            logs(f"{res['results']['utterances']=}")
            for it in res['results']['utterances']:
                if not it.transcript.strip():
                    continue
                speaker_list.append(f'[spk{it.speaker}]')
                tmp = {
                    "line": len(raws) + 1,
                    "start_time": int(it.start * 1000),
                    "end_time": int(it.end * 1000),
                    "text": it.transcript
                }
                if self.detect_language[:2] in ['zh', 'ja', 'ko']:
                    tmp['text'] = re.sub(r'\s| ', '', tmp['text'])
                tmp['time'] = tools.ms_to_time_string(ms=tmp['start_time']) + ' --> ' + tools.ms_to_time_string(
                    ms=tmp['end_time'])
                raws.append(tmp)
            if speaker_list:
                Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
        else:
            transcription = DeepgramConverter(res)
            srt_str = srt(transcription,
                          line_length=config.settings.get('cjk_len') if self.detect_language[:2] in ['zh', 'ja','ko'] else config.settings.get('other_len'))
            raws = tools.get_subtitle_from_srt(srt_str, is_file=False)
            if self.detect_language[:2] in ['zh', 'ja', 'ko']:
                for i, it in enumerate(raws):
                    if self.detect_language[:2] == 'zh':
                        it['text'] = zhconv.convert(it['text'], 'zh-hans')
                    raws[i]['text'] = it['text'].replace(' ', '')

        return raws
