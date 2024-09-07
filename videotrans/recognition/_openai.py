# openai
import os
from pathlib import Path
from typing import Union, List, Dict

import torch
import whisper
import zhconv
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


class OpenaiWhisperRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.model = None
        if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            self.flag.append(" ")
            self.maxlen = int(config.settings['cjk_len'])
        else:
            self.maxlen = int(config.settings['other_len'])

    def _output(self, srt):
        if self.inst and self.inst.precent < 75:
            self.inst.precent += 0.1
        self._signal(text=f"{config.transobj['yuyinshibiejindu']} {len(self.raws)}")
        self._signal(
            text=f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
            type='subtitle'
        )

    def _append_raws(self, cur):
        if len(cur['text']) < int(self.maxlen / 5) and len(self.raws) > 0:
            self.raws[-1]['text'] += cur['text'] if self.detect_language[:2] in ['ja', 'zh','ko'] else f' {cur["text"]}'
            self.raws[-1]['end_time'] = cur['end_time']
            self.raws[-1]['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
        else:
            self._output(cur)
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
                    language=self.detect_language,
                    word_timestamps=True,
                    initial_prompt=config.settings['initial_prompt_zh'],
                    condition_on_previous_text=config.settings['condition_on_previous_text']
                )
                for segment in result['segments']:
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

                            cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
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
                            cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                            self._append_raws(cur)
                            cur = None
                    # cur中有残留文字
                    if cur is not None:
                        cur['end_time'] = int(segment["words"][-1]["end"] * 1000) + start_time
                        cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
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