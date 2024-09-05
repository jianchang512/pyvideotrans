# 均等分割识别
import json
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Union

import zhconv
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools
logging.basicConfig()
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)

class FasterAvg(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.maxlen = 30
        self.model = None
        self.info = None


    # split audio by silence
    def _shorten_voice_old(self,normalized_sound):
        normalized_sound = tools.match_target_amplitude(normalized_sound, -20.0)
        max_interval = int(config.settings['interval_split']) * 1000
        nonsilent_data = []
        audio_chunks = detect_nonsilent(
            normalized_sound,
            min_silence_len=int(config.settings['voice_silence']),
            silence_thresh=-20 - 25)
        for i, chunk in enumerate(audio_chunks):
            start_time, end_time = chunk
            n = 0
            while end_time - start_time >= max_interval:
                n += 1
                new_end = start_time + max_interval
                new_start = start_time
                nonsilent_data.append((new_start, new_end, True))
                start_time += max_interval
            nonsilent_data.append((start_time, end_time, False))
        return nonsilent_data

    def _exec(self) ->Union[List[Dict],None]:
        if self._exit():
            return
        tools.set_process(
            config.transobj['fengeyinpinshuju'],
            type="logs",
            uuid=self.uuid)
        if not tools.vail_file(self.audio_file):
            raise Exception(f'[error]not exists {self.audio_file}')


        tmp_path = Path(f'{self.cache_folder}/{Path(self.audio_file).name}_tmp')
        tmp_path.mkdir(parents=True, exist_ok=True)
        tmp_path=tmp_path.as_posix()

        nonslient_file = f'{tmp_path}/detected_voice.json'
        normalized_sound=AudioSegment.from_wav(self.audio_file)
        if tools.vail_file(nonslient_file):
            nonsilent_data = json.load(open(nonslient_file, 'r'))
        else:
            nonsilent_data = self._shorten_voice_old(normalized_sound)
            json.dump(nonsilent_data, open(nonslient_file, 'w'))

        total_length = len(nonsilent_data)

        if self.model_name.startswith('distil-'):
            com_type = "default"
        elif self.is_cuda:
            com_type = config.settings['cuda_com_type']
        else:
            com_type = 'default'
        # 如果不存在 / ，则是本地模型
        local_res = True if self.model_name.find('/') == -1 else False
        down_root = config.ROOT_DIR + "/models"
        msg = ''
        if not local_res:
            if not os.path.isdir(down_root + '/models--' + self.model_name.replace('/', '--')):
                msg = '下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Download model from huggingface'
            else:
                msg = '加载或下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Load model from local or download model from huggingface'
        if self.inst:
            self.inst.parent.status_text = msg
        tools.set_process(msg, type='logs', uuid=self.uuid)

        self.model = WhisperModel(
            self.model_name,
            device="cuda" if config.params['cuda'] else "cpu",
            compute_type=com_type,
            download_root=down_root,
            local_files_only=local_res)

        for i, duration in enumerate(nonsilent_data):
            if self._exit():
                return

            start_time, end_time, buffered = duration
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            audio_chunk = normalized_sound[start_time:end_time]
            audio_chunk.export(chunk_filename, format="wav")

            text = ""
            try:
                segments, _ = self.model.transcribe(chunk_filename,
                                               beam_size=config.settings['beam_size'],
                                               best_of=config.settings['best_of'],
                                               condition_on_previous_text=config.settings['condition_on_previous_text'],
                                               temperature=0 if config.settings['temperature'] == 0 else [0.0, 0.2, 0.4,
                                                                                                          0.6, 0.8,
                                                                                                          1.0],
                                               vad_filter=False,
                                               language=self.detect_language,
                                               initial_prompt=config.settings['initial_prompt_zh']
                                               )

                for t in segments:
                    text += t.text + " "

                text = re.sub(r'&#\d+;', '', text.replace('&#39;', "'")).strip()

                if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                    continue

                if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
                    text = zhconv.convert(text, 'zh-hans')

                start = tools.ms_to_time_string(ms=start_time)
                end = tools.ms_to_time_string(ms=end_time)

                srt_line = {
                    "line": len(self.raws) + 1,
                    "time": f"{start} --> {end}",
                    "text": text
                }
                self.raws.append(srt_line)
                if self.inst and self.inst.precent < 55:
                    self.inst.precent += 0.1
                tools.set_process(
                    f"{config.transobj['yuyinshibiejindu']} {srt_line['line']}/{total_length}",
                    type="logs",
                    uuid=self.uuid)
                tools.set_process(f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n", type='subtitle',uuid=self.uuid)

            except Exception as e:
                config.logger.exception(e,exc_info=True)
                raise
        return self.raws

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
    config.logger.info('faster模式均等分割')
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
    normalized_sound = AudioSegment.from_wav(audio_file)  # -20.0
    nonslient_file = f'{tmp_path}/detected_voice.json'
    if tools.vail_file(nonslient_file):
        nonsilent_data = json.load(open(nonslient_file, 'r'))
    else:
        nonsilent_data = shorten_voice_old(normalized_sound)
        json.dump(nonsilent_data, open(nonslient_file, 'w'))

    raw_subtitles = []
    total_length = len(nonsilent_data)
    if model_name.startswith('distil-'):
        com_type = "default"
    elif is_cuda:
        com_type = config.settings['cuda_com_type']
    else:
        com_type = 'default'
    local_res = True if model_name.find('/') == -1 else False
    down_root = config.ROOT_DIR + "/models"
    msg = ''
    if model_name.find('/') > 0:
        if not os.path.isdir(down_root + '/models--' + model_name.replace('/', '--')):
            msg = '下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Download model from huggingface'
        else:
            msg = '加载或下载模型中，用时可能较久' if config.defaulelang == 'zh' else 'Load model from local or download model from huggingface'
    if inst:
        inst.parent.status_text = msg
    tools.set_process(msg, type='logs', uuid=uuid)

    model = WhisperModel(
        model_name,
        device="cuda" if config.params['cuda'] else "cpu",
        compute_type=com_type,
        download_root=down_root,
        local_files_only=local_res)
    for i, duration in enumerate(nonsilent_data):
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return False
        start_time, end_time, buffered = duration
        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        audio_chunk = normalized_sound[start_time:end_time]
        audio_chunk.export(chunk_filename, format="wav")
        text = ""
        try:
            segments, _ = model.transcribe(chunk_filename,
                                           beam_size=config.settings['beam_size'],
                                           best_of=config.settings['best_of'],
                                           condition_on_previous_text=config.settings['condition_on_previous_text'],
                                           temperature=0 if config.settings['temperature'] == 0 else [0.0, 0.2, 0.4,
                                                                                                      0.6, 0.8, 1.0],
                                           vad_filter=False,
                                           language=detect_language,
                                           initial_prompt=config.settings['initial_prompt_zh']
                                           )

            for t in segments:
                text += t.text + " "

            text = f"{text.capitalize()}. ".replace('&#39;', "'")
            text = re.sub(r'&#\d+;', '', text).strip()
            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                continue
            if detect_language[:2] == 'zh' and config.settings['zh_hant_s']:
                text = zhconv.convert(text, 'zh-hans')
            start = tools.ms_to_time_string(ms=start_time)
            end = tools.ms_to_time_string(ms=end_time)
            srt_line = {"line": len(raw_subtitles) + 1, "time": f"{start} --> {end}", "text": text}
            raw_subtitles.append(srt_line)
            if inst and inst.precent < 55:
                inst.precent += 0.1
            tools.set_process(
                f"{config.transobj['yuyinshibiejindu']} {srt_line['line']}/{total_length}",
                type="logs",
                uuid=uuid)
            tools.set_process(f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n", type='subtitle', uuid=uuid)
        except Exception as e:
            raise

    tools.set_process(
            f"{config.transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}",
            type='logs',
            uuid=uuid
        )
    return raw_subtitles
"""