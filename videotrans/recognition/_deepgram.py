# stt项目识别接口
import json
import os,re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, ClassVar,Union
import requests
import zhconv
from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
from deepgram_captions import DeepgramConverter, srt
import httpx

@dataclass
class DeepgramRecogn(BaseRecogn):
    raws: List[Any] = field(default_factory=list, init=False)
    zimu_len: int = field(init=False)
    join_flag: str = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.raws = []
        if self.detect_language and self.detect_language[:2] in ['zh', 'ja', 'ko']:
            self.zimu_len = int(config.settings.get('cjk_len'))
            self.join_flag = ''
        else:
            self.zimu_len = int(config.settings.get('other_len'))
            self.join_flag = ' '
        self.proxies = self._set_proxy(type='set')


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
            text=f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient')
        try:
            if self.proxies:
                httpx.HTTPTransport(proxy=self.proxies)
            # STEP 1 Create a Deepgram client using the API key
            deepgram = DeepgramClient(config.params.get('deepgram_apikey'))
            payload: FileSource = {
                "buffer": buffer_data,
            }

            # STEP 2: Configure Deepgram options for audio analysis
            diarize=config.params.get('paraformer_spk',False)
            options = PrerecordedOptions(
                model=self.model_name,
                # detect_language=True,
                language=self.detect_language[:2],
                smart_format=True,
                punctuate=True,
                paragraphs=True,
                utterances=True,
                diarize=diarize,

                utt_split=int(config.params.get('deepgram_utt',200))/1000,
            )

            # STEP 3: Call the transcribe_file method with the text payload and options
            res = deepgram.listen.rest.v("1").transcribe_file(payload, options,timeout=600)


            # STEP 4: Print the response
            # res=response.to_json()
            raws=[]
            rephrase_ok=True
            if not diarize and config.settings.get('rephrase'):
                try:
                    words=[]
                    for seg in res['results']['utterances']:
                        for it in seg['words']:
                            words.append({
                                "start":it['start'],
                                "end":it['end'],
                                "word":it['word']
                            })
                    self._signal(text="正在重新断句..." if config.defaulelang=='zh' else "Re-segmenting...")
                    raws=self.re_segment_sentences(words,self.detect_language[:2])
                except:
                    rephrase_ok=False
            if diarize:
                for it in res['results']['utterances']:
                    tmp={
                        "line":len(raws)+1,
                        "start_time":int(it['start']*1000),
                        "end_time":int(it['end']*1000),
                        "text":f'[spk{it["speaker"]}]'+it['transcript']
                    }
                    if self.detect_language[:2] in ['zh','ja','ko']:
                        tmp['text']=re.sub(r'\s| ','',tmp['text'])
                    tmp['time']=tools.ms_to_time_string(ms=tmp['start_time'])+' --> '+tools.ms_to_time_string(ms=tmp['end_time'])
                    raws.append(tmp)
            elif not config.settings.get('rephrase') or not rephrase_ok:
                transcription = DeepgramConverter(res)
                srt_str = srt(transcription, line_length= config.settings.get('cjk_len') if self.detect_language[:2] in ['zh','ja','ko'] else config.settings.get('other_len'))
                raws=tools.get_subtitle_from_srt(srt_str, is_file=False)
                if self.detect_language[:2] in ['zh','ja','ko']:
                    for i,it in enumerate(raws):
                        if self.detect_language[:2]=='zh':
                            it['text']=zhconv.convert(it['text'], 'zh-hans')
                        raws[i]['text']=it['text'].replace(' ','')

            return raws
        except Exception as e:
            raise
