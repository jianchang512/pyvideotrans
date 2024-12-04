# openai
from pathlib import Path
from typing import Union, List, Dict

import torch
import whisper
import zhconv
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools
import copy,re


class OpenaiWhisperRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.model = None
    def get_srtlist(self,alllist):
        jianfan=config.settings.get('zh_hant_s')
        for i in alllist:
            if len(i['words'])<1:
                continue
            tmp = {
                'text': zhconv.convert(i['text'], 'zh-hans') if jianfan and self.detect_language[:2]=='zh' else i['text'],
                'start_time': int(i['words'][0]['start'] * 1000),
                'end_time': int(i['words'][-1]['end'] * 1000)
            }
            tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
            tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            self.raws.append(tmp)    
    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        if self.model_name.find('/')>-1:
            raise Exception('huggingface上的自定义模型只可用于faster-whisper模式' if config.defaulelang=='zh' else 'The model only use when faster-whisper')
        tmp_path = Path(f'{self.cache_folder}/{Path(self.audio_file).name}_tmp')
        tmp_path.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_path.as_posix()

        # 以600s切分
        inter = 600000
        normalized_sound = AudioSegment.from_wav(self.audio_file)  # -20.0
        total_length = 1 + (len(normalized_sound) // inter)

        self.model = whisper.load_model(
            self.model_name,
            device="cuda" if self.is_cuda else "cpu",
            download_root=config.ROOT_DIR + "/models"
        )
        prompt = config.settings.get(f'initial_prompt_{self.detect_language}') if self.detect_language!='auto' else None
        try:
            last_detect=self.detect_language
            alllist=[]
            for i in range(total_length):
                if self._exit():
                    return
                start_time = i * inter
                if i < total_length - 1:
                    end_time = start_time + inter
                else:
                    end_time = len(normalized_sound)

                chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
                audio_chunk = normalized_sound[start_time:end_time]
                audio_chunk.export(chunk_filename, format="wav")

                result = self.model.transcribe(
                    chunk_filename,
                    language=self.detect_language[:2] if self.detect_language!='auto' else None,
                    word_timestamps=True,
                    initial_prompt=prompt if prompt else None,
                    condition_on_previous_text=config.settings['condition_on_previous_text']
                )
                if self.detect_language=='auto' and last_detect=='auto':
                    last_detect='zh-cn' if result['language'][:2]=='zh' else result['language']
                    self.detect_language=last_detect
                nums=0
                for segment in result['segments']:
                    if self._exit():
                        return
                    nums+=1
                    new_seg=copy.deepcopy(segment['words'])
                    text=tools.cleartext(segment['text'],remove_start_end=False)
                    for idx, word in enumerate(new_seg):
                        new_seg[idx]['start']=word['start']+start_time/1000
                        new_seg[idx]['end']=word['end']+start_time/1000
                    alllist.append({"words":new_seg,"text":text})
                    self._signal(text=f"{config.transobj['yuyinshibiejindu']} {nums}" )
                    self._signal(
                        text=f'{text}\n',
                        type='subtitle'
                    )
            if len(alllist)>0:
                if not config.settings['rephrase']:
                    self.get_srtlist(alllist)                    
                else:
                    try:
                        words_list = []
                        for it in list(alllist):
                            words_list += it['words']
                        self._signal(text="正在重新断句..." if config.defaulelang=='zh' else "Re-segmenting...")
                        self.raws = self.re_segment_sentences(words_list,self.detect_language[:2])
                    except:
                        self.get_srtlist(alllist)
        except Exception as e:
            raise
        finally:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                del self.model
            except Exception:
                pass
        if len(self.raws)<1:
            raise RuntimeError('识别结果为空' if config.defaulelang=='zh' else 'Recognition result is empty')
        return self.raws

