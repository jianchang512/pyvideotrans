import json
import os
import re
from datetime import timedelta
from pathlib import Path
from typing import Union, List, Dict

import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

class GoogleRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.maxlen = 30
        self.model = None
        self.info = None

    def _exec(self) ->Union[List[Dict],None]:
        if self._exit():
            return
        self._set_proxy(type='set')

        tmp_path = Path(f'{self.cache_folder}/{Path(self.audio_file).name}_tmp')
        tmp_path.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_path.as_posix()


        normalized_sound = AudioSegment.from_wav(self.audio_file)  # -20.0
        nonslient_file = f'{tmp_path}/detected_voice.json'
        if tools.vail_file(nonslient_file):
            nonsilent_data = json.load(open(nonslient_file, 'r'))
        else:
            nonsilent_data = self._shorten_voice_old(normalized_sound)
            json.dump(nonsilent_data, open(nonslient_file, 'w'))

        total_length = len(nonsilent_data)
        try:
            recognizer = sr.Recognizer()
        except Exception as e:
            raise

        for i, duration in enumerate(nonsilent_data):
            if self._exit():
                return
            start_time, end_time, buffered = duration
            if start_time == end_time:
                end_time += int(config.settings['voice_silence'])

            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            audio_chunk = normalized_sound[start_time:end_time]
            audio_chunk.export(chunk_filename, format="wav")

            text = ""
            try:
                with sr.AudioFile(chunk_filename) as source:
                    audio_data = recognizer.record(source)
                    try:
                        text = recognizer.recognize_google(audio_data, language=detect_language)
                    except sr.UnknownValueError:
                        text = ""
                    except sr.RequestError as e:
                        raise
            except Exception as e:
                raise LogExcept(e)

            text = re.sub(r'&#\d+;', '', f"{text.capitalize()}. ".replace('&#39;', "'")).strip()
            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                continue
            start = timedelta(milliseconds=start_time)
            stmp = str(start).split('.')
            if len(stmp) == 2:
                start = f'{stmp[0]},{int(int(stmp[-1]) / 1000)}'
            end = timedelta(milliseconds=end_time)
            etmp = str(end).split('.')
            if len(etmp) == 2:
                end = f'{etmp[0]},{int(int(etmp[-1]) / 1000)}'
            srt_line = {"line": len(self.raws) + 1, "time": f"{start} --> {end}", "text": text}
            self.raws.append(srt_line)
            if self.inst and self.inst.precent < 55:
                self.inst.precent += 0.1
            tools.set_process(
                f"{config.transobj['yuyinshibiejindu']} {srt_line['line']}/{total_length}", type="logs",

                uuid=self.uuid
            )
            tools.set_process(f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n", type='subtitle',
                              uuid=self.uuid)
        tools.set_process(
            f"{config.transobj['yuyinshibiewancheng']} / {len(self.raws)}",
            type='logs',
            uuid=self.uuid)
        return self.raws

    # split audio by silence
    def _shorten_voice_old(self,normalized_sound):
        normalized_sound = tools.match_target_amplitude(normalized_sound, -20.0)
        max_interval = int(config.settings['interval_split']) * 1000
        buffer = int(config.settings['voice_silence'])
        nonsilent_data = []
        audio_chunks = detect_nonsilent(normalized_sound, min_silence_len=int(config.settings['voice_silence']),
                                        silence_thresh=-20 - 25)
        for i, chunk in enumerate(audio_chunks):
            start_time, end_time = chunk
            n = 0
            while end_time - start_time >= max_interval:
                n += 1
                new_end = start_time + max_interval + buffer
                new_start = start_time
                nonsilent_data.append((new_start, new_end, True))
                start_time += max_interval
            nonsilent_data.append((start_time, end_time, False))
        return nonsilent_data

"""
def recogn(*,
           detect_language=None,
           audio_file=None,
           cache_folder=None,
           set_p=True,
           uuid=None,
           inst=None):
    tools.set_process(
            config.transobj['fengeyinpinshuju'],
            type="logs",
            uuid=uuid
        )
    if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
        return False
    proxy = tools.set_proxy()
    if proxy:
        os.environ['http_proxy'] = proxy
        os.environ['https_proxy'] = proxy
    
    noextname = os.path.basename(audio_file)
    tmp_path = Path(f'{cache_folder}/{noextname}_tmp')
    tmp_path.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_path.as_posix()

    if not tools.vail_file(audio_file):
        raise LogExcept(f'[error]not exists {audio_file}')
    normalized_sound = AudioSegment.from_wav(audio_file)  # -20.0
    nonslient_file = f'{tmp_path}/detected_voice.json'
    if tools.vail_file(nonslient_file):
        nonsilent_data = json.load(open(nonslient_file, 'r'))
    else:
        nonsilent_data = shorten_voice_old(normalized_sound)
        json.dump(nonsilent_data, open(nonslient_file, 'w'))

    raw_subtitles = []
    total_length = len(nonsilent_data)

    try:
        recognizer = sr.Recognizer()
    except Exception as e:
        raise LogExcept(f'使用Google识别需要设置代理')

    for i, duration in enumerate(nonsilent_data):
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return False
        start_time, end_time, buffered = duration
        if start_time == end_time:
            end_time += int(config.settings['voice_silence'])

        chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        audio_chunk = normalized_sound[start_time:end_time]
        audio_chunk.export(chunk_filename, format="wav")

        text = ""
        try:
            with sr.AudioFile(chunk_filename) as source:
                # Record the audio data
                audio_data = recognizer.record(source)
                try:
                    # Recognize the speech
                    text = recognizer.recognize_google(audio_data, language=detect_language)
                except sr.UnknownValueError:
                    text = ""
                except sr.RequestError as e:
                    raise LogExcept(f"Google识别出错，请检查代理是否正确：{e}")
        except Exception as e:
            raise

        text = f"{text.capitalize()}. ".replace('&#39;', "'")
        text = re.sub(r'&#\d+;', '', text).strip()
        if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
            continue
        start = timedelta(milliseconds=start_time)
        stmp = str(start).split('.')
        if len(stmp) == 2:
            start = f'{stmp[0]},{int(int(stmp[-1]) / 1000)}'
        end = timedelta(milliseconds=end_time)
        etmp = str(end).split('.')
        if len(etmp) == 2:
            end = f'{etmp[0]},{int(int(etmp[-1]) / 1000)}'
        srt_line = {"line": len(raw_subtitles) + 1, "time": f"{start} --> {end}", "text": text}
        raw_subtitles.append(srt_line)
        if inst and inst.precent < 55:
            inst.precent += 0.1
        tools.set_process(
            f"{config.transobj['yuyinshibiejindu']} {srt_line['line']}/{total_length}", type="logs",

            uuid=uuid
        )
        tools.set_process(f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n", type='subtitle', uuid=uuid)
    tools.set_process(
        f"{config.transobj['yuyinshibiewancheng']} / {len(raw_subtitles)}",
        type='logs',
        uuid=uuid)
    return raw_subtitles
"""