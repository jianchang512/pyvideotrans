# openai
import os
from pathlib import Path
from typing import Union, List, Dict

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
        self.maxlen = 30
        self.model = None
        self.info = None

    def _output(self,srt):
        if self.inst and self.inst.precent < 75:
            self.inst.precent += 0.1
        tools.set_process(
            f"{config.transobj['yuyinshibiejindu']} {len(self.raws)} line",
            type="logs",
            uuid=self.uuid
        )
        tools.set_process(
            f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
            type='subtitle',
            uuid=self.uuid
        )

    def _append_raws(self,cur):
        if len(cur['text']) < int(self.maxlen / 5) and len(self.raws) > 0:
            self.raws[-1]['text'] += cur['text'] if self.detect_language[:2] in ['ja', 'zh', 'ko'] else f' {cur["text"]}'
            self.raws[-1]['end_time'] = cur['end_time']
            self.raws[-1][
                'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
        else:
            self._output(cur)
            self.raws.append(cur)

    def _exec(self) ->Union[List[Dict],None]:
        if self._exit():
            return
        noextname = os.path.basename(self.audio_file)
        tmp_path = Path(f'{self.cache_folder}/{noextname}_tmp')
        tmp_path.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_path.as_posix()

        if not tools.vail_file(self.audio_file):
            raise Exception(f'[error]not exists {self.audio_file}')

        inter = 1200000
        normalized_sound = AudioSegment.from_wav(self.audio_file)  # -20.0
        total_length = 1 + (len(normalized_sound) // inter)

        if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            self.flag.append(" ")
            self.maxlen = int(config.settings['cjk_len'])
        else:
            self.maxlen = int(config.settings['other_len'])

        self.model = whisper.load_model(
            self.model_name,
            device="cuda" if self.is_cuda else "cpu",
            download_root=config.ROOT_DIR + "/models"
        )

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

            try:
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

                    cur = None
                    for word in segment["words"]:
                        if not cur:
                            cur = {
                                "line": len(self.raws) + 1,
                                "start_time": int(word["start"] * 1000) + start_time,
                                "end_time": int(word["end"] * 1000) + start_time,
                                "text": word["word"]
                            }
                            continue
                        if not word['word']:
                            continue
                        if word['word'][0] in self.flag:
                            cur['end_time'] = int(word["start"] * 1000) + start_time
                            if cur['end_time'] - cur['start_time'] < 1500:
                                cur['text'] += word['word']
                                continue
                            cur[
                                'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                            cur['text'] = cur['text'].strip()
                            self._append_raws(cur)
                            if len(word['word']) < 2:
                                cur = None
                                continue
                            cur = {
                                "line": len(self.raws) + 1,
                                "start_time": int(word["start"] * 1000) + start_time,
                                "end_time": int(word["end"] * 1000) + start_time,
                                "text": word["word"][1:]}
                            continue
                        cur['text'] += word["word"]
                        if word["word"][-1] in self.flag or len(cur['text']) >= self.maxlen * 1.5:
                            cur['end_time'] = int(word["end"] * 1000) + start_time
                            if cur['end_time'] - cur['start_time'] < 1500:
                                continue
                            cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                            cur['text'] = cur['text'].strip()
                            self._append_raws(cur)
                            cur = None

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
                config.logger.exception(e)
                raise
        if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
            for i, it in enumerate(self.raws):
                self.raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
        return self.raws

"""      
def recogn(*,
           detect_language=None,
           audio_file=None,
           cache_folder=None,
           model_name="tiny",
           set_p=True,
           uuid=None,
           inst=None,
           is_cuda=None):

    tools.set_process(
            config.transobj['fengeyinpinshuju'],
            type="logs",
            uuid=uuid)
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    
    noextname = os.path.basename(audio_file)
    tmp_path = Path(f'{cache_folder}/{noextname}_tmp')
    tmp_path.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_path.as_posix()

    if not tools.vail_file(audio_file):
        raise Exception(f'[error]not exists {audio_file}')

    inter = 1200000
    normalized_sound = AudioSegment.from_wav(audio_file)  # -20.0
    total_length = 1 + (len(normalized_sound) // inter)

    raws = []
    flag = [
        ",",
        ":",
        "'",
        "\"",
        ".",
        "?",
        "!",
        ";",
        ")",
        "]",
        "}",
        ">",
        "，",
        "。",
        "？",
        "；",
        "’",
        "”",
        "》",
        "】",
        "｝",
        "！"
    ]
    if detect_language[:2].lower() in ['zh', 'ja', 'ko']:
        flag.append(" ")
        maxlen = int(config.settings['cjk_len'])
    else:
        maxlen = int(config.settings['other_len'])
    model = whisper.load_model(
        model_name,
        device="cuda" if is_cuda else "cpu",
        download_root=config.ROOT_DIR + "/models"
    )

    def output(srt):
        if inst and inst.precent < 75:
            inst.precent += 0.1
        tools.set_process(
            f"{config.transobj['yuyinshibiejindu']} {len(raws)} line",
            type="logs",
            uuid=uuid
        )
        tools.set_process(
            f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
            type='subtitle',
            uuid=uuid
        )

    def append_raws(cur):
        if len(cur['text']) < int(maxlen / 5) and len(raws) > 0:
            raws[-1]['text'] += cur['text'] if detect_language[:2] in ['ja', 'zh', 'ko'] else f' {cur["text"]}'
            raws[-1]['end_time'] = cur['end_time']
            raws[-1][
                'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
        else:
            output(cur)
            raws.append(cur)

    for i in range(total_length):
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return False
        start_time = i * inter
        if i < total_length - 1:
            end_time = start_time + inter
        else:
            end_time = len(normalized_sound)

        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        audio_chunk = normalized_sound[start_time:end_time]
        audio_chunk.export(chunk_filename, format="wav")
        try:
            result = model.transcribe(
                chunk_filename,
                language=detect_language,
                word_timestamps=True,
                initial_prompt=config.settings['initial_prompt_zh'],
                condition_on_previous_text=config.settings['condition_on_previous_text']
            )
            for segment in result['segments']:
                if len(segment['words']) < 1:
                    continue
                if len(segment['text'].strip()) <= maxlen:
                    tmp = {
                        "line": len(raws) + 1,
                        "start_time": int(segment['words'][0]["start"] * 1000) + start_time,
                        "end_time": int(segment['words'][-1]["end"] * 1000) + start_time,
                        "text": segment["text"].strip()
                    }
                    if tmp['end_time'] - tmp['start_time'] >= 1500:
                        tmp[
                            "time"] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                        tmp['text'] = tmp['text'].strip()
                        append_raws(tmp)
                    continue

                cur = None
                for word in segment["words"]:
                    if not cur:
                        cur = {
                            "line": len(raws) + 1,
                            "start_time": int(word["start"] * 1000) + start_time,
                            "end_time": int(word["end"] * 1000) + start_time,
                            "text": word["word"]
                        }
                        continue
                    if not word['word']:
                        continue
                    if word['word'][0] in flag:
                        cur['end_time'] = int(word["start"] * 1000) + start_time
                        if cur['end_time'] - cur['start_time'] < 1500:
                            cur['text'] += word['word']
                            continue
                        cur[
                            'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        cur['text'] = cur['text'].strip()
                        append_raws(cur)
                        if len(word['word']) < 2:
                            cur = None
                            continue
                        cur = {
                            "line": len(raws) + 1,
                            "start_time": int(word["start"] * 1000) + start_time,
                            "end_time": int(word["end"] * 1000) + start_time,
                            "text": word["word"][1:]}
                        continue
                    cur['text'] += word["word"]
                    if word["word"][-1] in flag or len(cur['text']) >= maxlen * 1.5:
                        cur['end_time'] = int(word["end"] * 1000) + start_time
                        if cur['end_time'] - cur['start_time'] < 1500:
                            continue
                        cur[
                            'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        cur['text'] = cur['text'].strip()
                        append_raws(cur)
                        cur = None

                if cur is not None:
                    cur['end_time'] = int(segment["words"][-1]["end"] * 1000) + start_time
                    cur[
                        'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                    if len(cur['text']) <= 3:
                        raws[-1]['text'] += cur['text'].strip()
                        raws[-1]['end_time'] = cur['end_time']
                        raws[-1]['time'] = cur['time']
                    else:
                        cur['text'] = cur['text'].strip()
                        append_raws(cur)
        except Exception as e:
            config.logger.exception(e)
            raise
    tools.set_process(
            f"{config.transobj['yuyinshibiewancheng']} / {len(raws)}",
            type='logs',
            uuid=uuid)
    if detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
        for i, it in enumerate(raws):
            raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
    return raws
"""