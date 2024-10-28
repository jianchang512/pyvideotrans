import json
import re
from datetime import timedelta
from pathlib import Path
from typing import Union, List, Dict

import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.configure import config
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


class GoogleRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []

    def _exec(self) -> Union[List[Dict], None]:
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
            with open(nonslient_file, 'w') as f:
                f.write(json.dumps(nonsilent_data))

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

            try:
                with sr.AudioFile(chunk_filename) as source:
                    audio_data = recognizer.record(source)
                    try:
                        text = recognizer.recognize_google(audio_data, language=self.detect_language)
                    except sr.UnknownValueError:
                        text = ""
                    except sr.RequestError as e:
                        raise
            except Exception as e:
                raise

            text = re.sub(r'&#\d+;', '', f"{text.capitalize()}. ".replace('&#39;', "'")).strip()
            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                continue
            start = tools.ms_to_time_string(ms=start_time)

            end = tools.ms_to_time_string(ms=end_time)
            srt_line = {
                "line": len(self.raws) + 1,
                "time": f"{start} --> {end}",
                "text": text,
                "start_time":start_time,
                "end_time":end_time,
                "startraw":start,
                "endraw":end
            }
            self.raws.append(srt_line)
            if self.inst and self.inst.precent < 55:
                self.inst.precent += 0.1
            self._signal(text=f"{config.transobj['yuyinshibiejindu']} {srt_line['line']}/{total_length}")
            self._signal(text=f"{srt_line['text']}\n", type='subtitle')
        return self.raws

    # split audio by silence
    def _shorten_voice_old(self, normalized_sound):
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
