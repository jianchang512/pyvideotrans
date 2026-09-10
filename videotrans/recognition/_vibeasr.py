import json
from dataclasses import dataclass, asdict
from typing import List,  Union

from pathlib import Path
import  time

from pydub import AudioSegment

from videotrans.configure.config import logger, defaulelang, ROOT_DIR, settings
from videotrans.configure import config
from videotrans.process.vad import get_speech_timestamp_silero

from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util._srt_parse import ms_to_time_string
from videotrans.util.help_down import check_and_down_hf


@dataclass
class VibeasrRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.model_name='microsoft/VibeVoice-ASR-HF'
        self.local_dir=f'{ROOT_DIR}/models/models--microsoft--VibeVoice-ASR-HF'
        self._repid=f'microsoft/VibeVoice-ASR-HF'



    def _download(self):
        check_and_down_hf(model_id=self._repid,
                                    repo_id=self._repid,
                                    local_dir=self.local_dir,
                                    callback=self._process_callback)

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return

        logs_file = f'{config.TEMP_DIR}/{self.uuid}/vibeasr-{time.time()}.log'
        title = f"VibeVoice-ASR {self.model_name}"
        cut_audio_list_file = f'{config.TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'

        self._cut(cut_audio_list_file)


        kwargs = {
            "cut_audio_list": cut_audio_list_file,
            "logs_file": logs_file,
            "model_name": self.model_name,
            "local_dir":self.local_dir,
            "hotword":settings.get('hotwords'),
            "detect_language":self.detect_language
        }
        from videotrans.process.stt_vibeasr import videasr_fun
        jsdata = self._new_process(callback=videasr_fun, title=title, is_cuda=self.is_cuda, kwargs=kwargs)
        return jsdata

    def _cut(self,cut_audio_list_file):
        audio = AudioSegment.from_wav(self.audio_file)
        _len=len(audio)
        # 不使用 VibeVoice-ASR 内部自动断句，因中文下会生成十几秒到几十秒的超长断句
        _min_segments=3000#最小3s
        _max_segments=6000#最大10s
        if _len<=_max_segments:
            _endraw=ms_to_time_string(ms=_len)
            Path(cut_audio_list_file).write_text(json.dumps([
            {
                "line":1,
                "text":"",
                "start_time":0,
                "end_time":_len,
                "startraw":'00:00:00,000',
                "endraw":_endraw,
                "time":f'00:00:00,000 --> {_endraw}',
                "filename":self.audio_file
            }
            ]), encoding='utf-8')
            return


        dir_name = f"{config.TEMP_DIR}/clip_{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        kw = {
            "input_wav": self.audio_file,
            "threshold": float(settings.get('threshold', 0.45)),
            "min_speech_duration_ms": _min_segments,
            "max_speech_duration_ms": _max_segments,
            "min_silent_duration_ms": 2000
        }
        self.speech_timestamps=get_speech_timestamp_silero(**kw)

        data = []
        for i, (start_ms, end_ms) in enumerate(self.speech_timestamps):
            startraw = ms_to_time_string(ms=start_ms)
            endraw = ms_to_time_string(ms=end_ms)
            file_name = f"{dir_name}/audio_{i}.wav"
            chunk = audio[start_ms:end_ms]
            chunk.export(file_name, format="wav")
            data.append({
                "line":i + 1,
                "text":"",
                "start_time":start_ms,
                "end_time":end_ms,
                "startraw":startraw,
                "endraw":endraw,
                "time":f'{startraw} --> {endraw}',
                "filename":file_name
            })
        Path(cut_audio_list_file).write_text(json.dumps(data),encoding='utf-8')