# 整体识别，全部传给模型
import logging
import os
from typing import List, Dict, Union

import torch
import zhconv
from faster_whisper import WhisperModel

from videotrans.configure import config
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools
logging.basicConfig()
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)

class FasterAll(BaseRecogn):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.raws=[]
        self.maxlen=30
        self.model = None
        self.info=None

    def _output(self,srt,segment=None):
        tools.set_process(
            f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
            type='subtitle',
            uuid=self.uuid
        )
        if self.inst and self.inst.precent < 55:
            self.inst.precent += round(segment.end * 0.5 / self.info.duration, 2)
        tools.set_process(
            f'{config.transobj["zimuhangshu"]} {srt["line"]}',
            type="logs",
            uuid=self.uuid
        )
    def _append_raws(self,cur,segment=None):
        if len(cur['text']) < int(self.maxlen / 5) and len(self.raws) > 0:
            self.raws[-1]['text'] += cur['text'] if self.detect_language[:2] in ['ja', 'zh', 'ko'] else f' {cur["text"]}'
            self.raws[-1]['end_time'] = cur['end_time']
            self.raws[-1][
                'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
        else:
            self._output(cur,segment=segment)
            self.raws.append(cur)

    def _exec(self) ->Union[List[Dict],None]:
        if self._exit():
            return
        down_root = config.ROOT_DIR + "/models"
        msg = ""
        if self.model_name.find('/') > 0:
            if not os.path.isdir(down_root + '/models--' + self.model_name.replace('/', '--')):
                msg = '下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Download model from huggingface'
            elif self.inst:
                msg = '加载或下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Load model from local or download model from huggingface'
        else:
            msg = f"{config.transobj['kaishishibie']}"
        if self.inst:
            self.inst.parent.status_tex = msg

        tools.set_process(msg, type="logs", uuid=self.uuid)


        try:
            if self.model_name.startswith('distil-'):
                com_type = "default"
            elif self.is_cuda:
                com_type = config.settings['cuda_com_type']
            else:
                com_type = 'default'

            local_res = True if self.model_name.find('/') == -1 else False

            self.model = WhisperModel(
                self.model_name,
                device="cuda" if self.is_cuda else "cpu",
                compute_type=com_type,
                download_root=down_root,
                num_workers=config.settings['whisper_worker'],
                cpu_threads=os.cpu_count() if int(config.settings['whisper_threads']) < 1 else int(
                    config.settings['whisper_threads']),
                local_files_only=local_res
            )

            if self._exit():
                return

            if not tools.vail_file(self.audio_file):
                raise Exception(f'no exists {self.audio_file}')
            segments, self.info = self.model.transcribe(
                self.audio_file,
                beam_size=config.settings['beam_size'],
                best_of=config.settings['best_of'],
                condition_on_previous_text=config.settings['condition_on_previous_text'],

                temperature=0 if config.settings['temperature'] == 0 else [0.0, 0.2, 0.4, 0.6,
                                                                           0.8, 1.0],
                vad_filter=bool(config.settings['vad']),
                vad_parameters=dict(
                    min_silence_duration_ms=config.settings['overall_silence'],
                    max_speech_duration_s=float('inf'),
                    threshold=config.settings['overall_threshold'],
                    speech_pad_ms=config.settings['overall_speech_pad_ms']
                ),
                word_timestamps=True,
                language=self.detect_language,
                initial_prompt=config.settings['initial_prompt_zh']
            )

            if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
                self.flag.append(" ")
                self.maxlen = config.settings['cjk_len']
            else:
                self.maxlen = config.settings['other_len']





            for segment in segments:
                if len(segment.words) < 1:
                    continue
                if len(segment.text.strip()) <= self.maxlen:
                    tmp = {
                        "line": len(self.raws) + 1,
                        "start_time": int(segment.words[0].start * 1000),
                        "end_time": int(segment.words[-1].end * 1000),
                        "text": segment.text.strip()
                    }
                    if tmp['end_time'] - tmp['start_time'] >= 1500:
                        tmp["time"] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                        self._append_raws(tmp,segment=segment)
                        continue

                cur = None
                for word in segment.words:
                    if not cur:
                        cur = {"line": len(self.raws) + 1,
                               "start_time": int(word.start * 1000),
                               "end_time": int(word.end * 1000),
                               "text": word.word}
                        continue
                    # 第一个字符 是标点并且大于最小字符数
                    if word.word[0] in self.flag:
                        cur['end_time'] = int(word.start * 1000)
                        if cur['end_time'] - cur['start_time'] < 1500:
                            cur['text'] += word.word
                            continue
                        cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        cur['text'] = cur['text'].strip()
                        self._append_raws(cur,segment=segment)
                        if len(word.word) < 2:
                            cur = None
                            continue
                        cur = {
                            "line": len(self.raws) + 1,
                            "start_time": int(word.start * 1000),
                            "end_time": int(word.end * 1000),
                            "text": word.word[1:]
                        }
                        continue
                    cur['text'] += word.word
                    if word.word[-1] in self.flag or len(cur['text']) >= self.maxlen * 1.5:
                        cur['end_time'] = int(word.end * 1000)
                        if cur['end_time'] - cur['start_time'] < 1500:
                            continue
                        cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                        cur['text'] = cur['text'].strip()
                        self._append_raws(cur,segment=segment)
                        cur = None

                if cur is not None:
                    cur['end_time'] = int(segment.words[-1].end * 1000)
                    cur['time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                    if len(cur['text'].strip()) <= 3:
                        self.raws[-1]['text'] += cur['text'].strip()
                        self.raws[-1]['end_time'] = cur['end_time']
                        self.raws[-1]['time'] = cur['time']
                    else:
                        cur['text'] = cur['text'].strip()
                        self._append_raws(cur,segment=segment)
            if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
                for i, it in enumerate(self.raws):
                    self.raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
            return self.raws
        except Exception as e:
            raise
        finally:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                del self.model
            except Exception:
                pass

"""
def recogn(*,
           detect_language=None,
           audio_file=None,
           cache_folder=None,
           model_name="tiny",
           set_p=True,
           inst=None,
           uuid=None,
           is_cuda=None):
    
    config.logger.info('faster模式 整体识别')
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    down_root = config.ROOT_DIR + "/models"
    msg = ""
    if model_name.find('/') > 0:
        if not os.path.isdir(down_root + '/models--' + model_name.replace('/', '--')):
            msg = '下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Download model from huggingface'
        elif inst:
            msg = '加载或下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Load model from local or download model from huggingface'
    else:
        msg = f"{config.transobj['kaishishibie']}"
    if inst:
        inst.parent.status_tex = msg

    tools.set_process(msg, type="logs", uuid=uuid)
    model = None
    raws = []
    try:
        if model_name.startswith('distil-'):
            com_type = "default"
        elif is_cuda:
            com_type = config.settings['cuda_com_type']
        else:
            com_type = 'default'
        local_res = True if model_name.find('/') == -1 else False

        model = WhisperModel(
            model_name,
            device="cuda" if is_cuda else "cpu",
            compute_type=com_type,
            download_root=down_root,
            num_workers=config.settings['whisper_worker'],
            cpu_threads=os.cpu_count() if int(config.settings['whisper_threads']) < 1 else int(
                config.settings['whisper_threads']),
            local_files_only=local_res
        )
        if config.current_status != 'ing' and config.box_recogn != 'ing':
            return False
        if not tools.vail_file(audio_file):
            raise Exception(f'no exists {audio_file}')
        segments, info = model.transcribe(
            audio_file,
            beam_size=config.settings['beam_size'],
            best_of=config.settings['best_of'],
            condition_on_previous_text=config.settings['condition_on_previous_text'],

            temperature=0 if config.settings['temperature'] == 0 else [0.0, 0.2, 0.4, 0.6,
                                                                       0.8, 1.0],
            vad_filter=bool(config.settings['vad']),
            vad_parameters=dict(
                min_silence_duration_ms=config.settings['overall_silence'],
                max_speech_duration_s=float('inf'),
                threshold=config.settings['overall_threshold'],
                speech_pad_ms=config.settings['overall_speech_pad_ms']
            ),
            word_timestamps=True,
            language=detect_language,
            initial_prompt=config.settings['initial_prompt_zh']
        )
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
            maxlen = config.settings['cjk_len']
        else:
            maxlen = config.settings['other_len']

        def output(srt):
            if set_p:
                tools.set_process(
                    f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
                    type='subtitle',
                    uuid=uuid
                )
                if inst and inst.precent < 55:
                    inst.precent += round(segment.end * 0.5 / info.duration, 2)
                tools.set_process(
                    f'{config.transobj["zimuhangshu"]} {srt["line"]}',
                    type="logs",
                    uuid=uuid
                )

        def append_raws(self,cur):
            if len(cur['text']) < int(maxlen / 5) and len(raws) > 0:
                raws[-1]['text'] += cur['text'] if detect_language[:2] in ['ja', 'zh', 'ko'] else f' {cur["text"]}'
                raws[-1]['end_time'] = cur['end_time']
                raws[-1][
                    'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
            else:
                output(cur)
                raws.append(cur)

        for segment in segments:
            if len(segment.words) < 1:
                continue
            if len(segment.text.strip()) <= maxlen:
                tmp = {
                    "line": len(raws) + 1,
                    "start_time": int(segment.words[0].start * 1000),
                    "end_time": int(segment.words[-1].end * 1000),
                    "text": segment.text.strip()
                }
                if tmp['end_time'] - tmp['start_time'] >= 1500:
                    tmp[
                        "time"] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                    append_raws(tmp)
                    continue

            cur = None
            for word in segment.words:
                if not cur:
                    cur = {"line": len(raws) + 1,
                           "start_time": int(word.start * 1000),
                           "end_time": int(word.end * 1000),
                           "text": word.word}
                    continue
                # 第一个字符 是标点并且大于最小字符数
                if word.word[0] in flag:
                    cur['end_time'] = int(word.start * 1000)
                    if cur['end_time'] - cur['start_time'] < 1500:
                        cur['text'] += word.word
                        continue
                    cur[
                        'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                    cur['text'] = cur['text'].strip()
                    append_raws(cur)
                    if len(word.word) < 2:
                        cur = None
                        continue
                    cur = {
                        "line": len(raws) + 1,
                        "start_time": int(word.start * 1000),
                        "end_time": int(word.end * 1000),
                        "text": word.word[1:]
                    }
                    continue
                cur['text'] += word.word

                if word.word[-1] in flag or len(cur['text']) >= maxlen * 1.5:
                    cur['end_time'] = int(word.end * 1000)
                    if cur['end_time'] - cur['start_time'] < 1500:
                        continue
                    cur[
                        'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                    cur['text'] = cur['text'].strip()
                    append_raws(cur)
                    cur = None

            if cur is not None:
                cur['end_time'] = int(segment.words[-1].end * 1000)
                cur[
                    'time'] = f'{tools.ms_to_time_string(ms=cur["start_time"])} --> {tools.ms_to_time_string(ms=cur["end_time"])}'
                if len(cur['text'].strip()) <= 3:
                    raws[-1]['text'] += cur['text'].strip()
                    raws[-1]['end_time'] = cur['end_time']
                    raws[-1]['time'] = cur['time']
                else:
                    cur['text'] = cur['text'].strip()
                    append_raws(cur)
    except Exception as e:
        raise
    else:
        if detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
            for i, it in enumerate(raws):
                raws[i]['text'] = zhconv.convert(it['text'], 'zh-hans')
        return raws
"""