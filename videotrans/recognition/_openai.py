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


class OpenaiWhisperRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.model = None
        self.jianfan=False
        if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            self.flag.append(" ")
            self.maxlen = int(config.settings['cjk_len'])
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s'] else False
        else:
            self.maxlen = int(config.settings['other_len'])


    def _append_raws(self, cur):
        if self.inst and self.inst.precent < 75:
            self.inst.precent += 0.1
        if self.jianfan:
            cur['text'] = zhconv.convert(cur['text'], 'zh-hans')
        self._signal(text=f"{config.transobj['yuyinshibiejindu']} {len(self.raws)}")
        self._signal(
            text=f'{cur["line"]}\n{cur["time"]}\n{cur["text"]}\n\n',
            type='subtitle'
        )
        self.raws.append(cur)

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        tmp_path = Path(f'{self.cache_folder}/{Path(self.audio_file).name}_tmp')
        tmp_path.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_path.as_posix()

        # 以1200s切分
        inter = 1200000
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
                    if self.inst and hasattr(self.inst,'set_source_language'):
                        self.inst.set_source_language(last_detect)

                for segment in result['segments']:
                    if self._exit():
                        return
                    if len(segment['words']) < 1:
                        continue
                    len_text = len(segment['text'].strip())
                    # 如果小于 maxlen*1.5 或 小于 5s，则为正常语句
                    if len_text <= self.maxlen * 1.2 or (
                            segment['words'][-1]['end'] - segment['words'][0]['start']) < 3:
                        tmp = {
                            "line": len(self.raws) + 1,
                            "start_time": int(segment['words'][0]['start'] * 1000) + start_time,
                            "end_time": int(segment['words'][-1]['end'] * 1000) + start_time,
                            "text": segment['text'].strip(),
                        }
                        tmp[
                            'time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                        self._append_raws(tmp)
                        continue

                    # st
                    # words组数量
                    max_index = len(segment['words']) - 1
                    split_idx_list = []
                    for idx, word in enumerate(segment['words']):
                        if word['word'][0] in self.flag or (last_detect[:2] in ['zh','ja','ko'] and word['word'][0]==' '):
                            split_idx = idx - 1 if idx > 0 else idx
                            split_idx_list.append(split_idx)
                        elif word['word'][-1] in self.flag or (last_detect[:2] in ['zh','ja','ko'] and word['word'][-1]==' '):
                            split_idx = idx
                            split_idx_list.append(split_idx)
                    # 没有合适的切分点,不切分
                    # 去掉重复的切分点并排序
                    split_idx_list = sorted(list(set(split_idx_list)))
                    if len(split_idx_list) == 0:
                        tmp = {
                            "line": len(self.raws) + 1,
                            "start_time": int(segment['words'][0]['start'] * 1000),
                            "end_time": int(segment['words'][-1]['end'] * 1000),
                            "text": segment['text'].strip()
                        }
                        tmp[
                            'time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                        self._append_raws(tmp)
                        continue

                    last_idx = 0
                    try:
                        current_idx=split_idx_list.pop(0)
                        res_all=[];
                        res=[]
                        for iw,w in enumerate(segment['words']):
                            if iw <=current_idx:
                                res.append(w)
                            else:
                                if len(res)>0:
                                    res_all.append(res)
                                    res=[]
                                if len(split_idx_list)>0:
                                    current_idx=split_idx_list.pop(0)
                                else:
                                    current_idx=999999
                                res.append(w)
                        if len(res)>0:
                            res_all.append(res)
                        
                        for it in res_all:
                            texts = [w['word'] for  w in it]
                            tmp = {
                                "line": len(self.raws) + 1,
                                "start_time": int(it[0]['start'] * 1000),
                                "end_time": int(it[-1]['end'] * 1000),
                                "text": self.join_word_flag.join(texts)
                            }
                            tmp['time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                            self._append_raws(tmp)
                    except Exception as e:
                        tmp = {
                            "line": len(self.raws) + 1,
                            "start_time": int(segment['words'][0]['start'] * 1000),
                            "end_time": int(segment['words'][-1]['end'] * 1000),
                            "text": segment['text'].strip()
                        }
                        tmp['time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                        self._append_raws(tmp)
                        print(f'异常({last_idx=}) {e} ')
                    #ed

        except Exception as e:
            raise
        finally:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                del self.model
            except Exception:
                pass
        return self.raws

