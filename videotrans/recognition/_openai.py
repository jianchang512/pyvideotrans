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

    # def _output(self, srt):
    #     if self.inst and self.inst.precent < 75:
    #         self.inst.precent += 0.1
    #     self._signal(text=f"{config.transobj['yuyinshibiejindu']} {len(self.raws)}")
    #     self._signal(
    #         text=f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
    #         type='subtitle'
    #     )

    def _append_raws(self, cur):
        # if len(cur['text']) < int(self.maxlen / 5) and len(self.raws) > 0:
        #     self.raws[-1]['text'] += cur['text'] if self.detect_language[:2] in ['ja', 'zh','ko'] else f' {cur["text"]}'
        #     self.raws[-1]['end_time'] = cur['end_time']
        #     self.raws[-1]['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
        # else:
        #     self._output(cur)
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
        prompt = config.settings.get(f'initial_prompt_{self.detect_language}')
        try:
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
                    language=self.detect_language[:2],
                    word_timestamps=True,
                    initial_prompt=prompt if prompt else None,
                    condition_on_previous_text=config.settings['condition_on_previous_text']
                )
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
                        if word['word'][0] in self.flag:
                            split_idx = idx - 1 if idx > 0 else idx
                            split_idx_list.append(split_idx)
                        elif word['word'][-1] in self.flag:
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
                        # print(f'{split_idx=} 直接插入 {tmp["text"]}')
                        continue

                    last_idx = 0
                    try:
                        # print(f'{split_idx_list=}')
                        for idx in split_idx_list:
                            if last_idx > idx:
                                break
                            # words组里起点索引为当前切分点+1
                            st = last_idx
                            # 下一个为结束点,未到末尾
                            ed = idx
                            if segment['words'][ed]['end'] - segment['words'][st]['start'] < 1:
                                continue
                            last_idx = ed + 1
                            texts = [w['word'] for iw, w in enumerate(segment['words']) if iw >= st and iw <= ed]
                            tmp = {
                                "line": len(self.raws) + 1,
                                "start_time": int(segment['words'][st]['start'] * 1000),
                                "end_time": int(segment['words'][ed]['end'] * 1000),
                                "text": self.join_word_flag.join(texts)
                            }
                            # print(f'插入 st({st})->ed({ed}),{tmp["text"]}')
                            tmp[
                                'time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                            self._append_raws(tmp)
                        if last_idx < max_index:
                            texts = [w['word'] for iw, w in enumerate(segment['words']) if iw >= last_idx]
                            tmp = {
                                "line": len(self.raws) + 1,
                                "start_time": int(segment['words'][last_idx]['start'] * 1000),
                                "end_time": int(segment['words'][-1]['end'] * 1000),
                                "text": self.join_word_flag.join(texts)
                            }
                            tmp[
                                'time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                            self._append_raws(tmp)
                            # print(f'last_idx({last_idx})<max_index({max_index}),插入 {tmp["text"]}')
                    except Exception as e:
                        tmp = {
                            "line": len(self.raws) + 1,
                            "start_time": int(segment['words'][0]['start'] * 1000),
                            "end_time": int(segment['words'][-1]['end'] * 1000),
                            "text": segment['text'].strip()
                        }
                        tmp[
                            'time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
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
        # if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
        #     for i, it in enumerate(self.raws):
        #         self.raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
        return self.raws

    def _exec0(self) -> Union[List[Dict], None]:
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
        prompt = config.settings.get(f'initial_prompt_{self.detect_language}')
        try:
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
                    language=self.detect_language[:2],
                    word_timestamps=True,
                    initial_prompt=prompt if prompt else None,
                    condition_on_previous_text=config.settings['condition_on_previous_text']
                )
                for segment in result['segments']:
                    if self._exit():
                        return
                    if len(segment['words']) < 1:
                        continue
                    # 当前文字行字数小于 maxlen，直接使用
                    if len(segment['text'].strip()) <= self.maxlen:
                        tmp = {
                            "line": len(self.raws) + 1,
                            "start_time": int(segment['words'][0]["start"] * 1000) + start_time,
                            "end_time": int(segment['words'][-1]["end"] * 1000) + start_time,
                            "text": segment["text"].strip()
                        }
                        if tmp['end_time'] - tmp['start_time'] >= 1500:
                            tmp[
                                "time"] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                            tmp['text'] = tmp['text'].strip()
                            self._append_raws(tmp)
                        continue
                    # 当前文字行字数太多，超过 maxlen，需重新按 flag 切分
                    cur = None
                    for word in segment["words"]:
                        if self._exit():
                            return
                        if not word['word']:
                            continue
                        if not cur:
                            cur = {
                                "line": len(self.raws) + 1,
                                "start_time": int(word["start"] * 1000) + start_time,
                                "end_time": int(word["end"] * 1000) + start_time,
                                "text": word["word"]
                            }
                            continue
                        # 第一个字数是 flag 标识符
                        if word['word'][0] in self.flag:
                            cur['end_time'] = int(word["start"] * 1000) + start_time
                            if cur['end_time'] - cur['start_time'] < 1500:
                                cur['text'] += word['word']
                                cur['end_time'] = int(word["end"] * 1000) + start_time
                                continue

                            cur[
                                'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                            cur['text'] = cur['text'].strip()
                            self._append_raws(cur)

                            if len(word['word']) == 1:
                                cur = None
                                continue

                            cur = {
                                "line": len(self.raws) + 1,
                                "start_time": int(word["start"] * 1000) + start_time,
                                "end_time": int(word["end"] * 1000) + start_time,
                                "text": word["word"][1:]}
                            continue
                        cur['text'] += word["word"]

                        # 最后一个字是标识符 flag 或者超过允许字数 maxlen*1.5，强制切分
                        if word["word"][-1] in self.flag or len(cur['text']) >= self.maxlen * 1.5:
                            cur['end_time'] = int(word["end"] * 1000) + start_time
                            if cur['end_time'] - cur['start_time'] < 1500:
                                continue
                            cur[
                                'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                            self._append_raws(cur)
                            cur = None
                    # cur中有残留文字
                    if cur is not None:
                        cur['end_time'] = int(segment["words"][-1]["end"] * 1000) + start_time
                        cur[
                            'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        if len(cur['text']) <= 3:
                            self.raws[-1]['text'] += cur['text'].strip()
                            self.raws[-1]['end_time'] = cur['end_time']
                            self.raws[-1]['time'] = cur['time']
                        else:
                            cur['text'] = cur['text'].strip()
                            self._append_raws(cur)
        except Exception as e:
            raise
        finally:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                del self.model
            except Exception:
                pass
        if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
            for i, it in enumerate(self.raws):
                self.raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
        return self.raws
