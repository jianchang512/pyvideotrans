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
from videotrans.util.help_down import check_and_down_ms, check_and_down_hf
from videotrans.util.help_misc import is_connect_hf


@dataclass
class QwenasrlocalRecogn(BaseRecogn):

    align_language:List[str]=("zh","zh-cn","zh-tw","en","ja",'ko','yue','fr','es','es-419','it','de','pt','pt-br','pt-pt','ru')

    def __post_init__(self):
        super().__post_init__()
        if self.model_name in ['1.7B','0.6B']:
            self.local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-ASR-{self.model_name}'
            self._repid=f'Qwen/Qwen3-ASR-{self.model_name}'
        else:
            self.local_dir=f'{ROOT_DIR}/models/models--ASLP-lab--CN-MultiDialect-ASR'
            self._repid='ASLP-lab/CN-MultiDialect-ASR'


    def _download(self):
        if Path(self.local_dir+'/model.safetensors').exists() and Path(f"{ROOT_DIR}/models/models--Qwen--Qwen3-ForcedAligner-0.6B/model.safetensors").exists():
            return
        if not is_connect_hf():
            check_and_down_ms(self._repid, callback=self._process_callback, local_dir=self.local_dir)
            check_and_down_ms("Qwen/Qwen3-ForcedAligner-0.6B", callback=self._process_callback, local_dir=f"{ROOT_DIR}/models/models--Qwen--Qwen3-ForcedAligner-0.6B")
        else:
            check_and_down_hf(model_id=self._repid,
                                    repo_id=self._repid,
                                    local_dir=self.local_dir,
                                    callback=self._process_callback)
            check_and_down_hf("Qwen/Qwen3-ForcedAligner-0.6B",repo_id="Qwen/Qwen3-ForcedAligner-0.6B", callback=self._process_callback, local_dir=f"{ROOT_DIR}/models/models--Qwen--Qwen3-ForcedAligner-0.6B")

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return

        logs_file = f'{config.TEMP_DIR}/{self.uuid}/qwen3asrlocal-{time.time()}.log'
        title = f"Qwen3-ASR {self.model_name}"
        cut_audio_list_file = f'{config.TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'

        if self.detect_language not in self.align_language:
            # 不支持对齐时间戳 需切片
            Path(cut_audio_list_file).write_text(json.dumps([ asdict(item) for item in self.cut_audio()]), encoding='utf-8')
        else:
            self._cut(cut_audio_list_file)

        _min_speech = max(int(float(settings.get('min_speech_duration_ms', 1000))), 1000)
        # 最长片段不得大于25s,并且不得小于 _min_speech
        _max_speech = max(min(int(float(settings.get('max_speech_duration_s', 6)) * 1000), 25000), _min_speech + 1000)

        kwargs = {
            "cut_audio_list": cut_audio_list_file,
            "logs_file": logs_file,
            "model_name": self.model_name,
            "local_dir":self.local_dir,
            "local_dir_align":f"{ROOT_DIR}/models/models--Qwen--Qwen3-ForcedAligner-0.6B",
            "hotword":settings.get('hotwords'),
            "min_speech_ms":_min_speech,
            "max_speech_ms":_max_speech,
            "force_align":self.detect_language in self.align_language,
            "detect_language":self.detect_language
        }
        from videotrans.process.stt_qwen import qwen3asr_fun
        jsdata = self._new_process(callback=qwen3asr_fun, title=title, is_cuda=self.is_cuda, kwargs=kwargs)
        return jsdata

    def _cut(self,cut_audio_list_file):
        audio = AudioSegment.from_wav(self.audio_file)
        _len=len(audio)
        _min_segments=60000#最小1分钟
        _max_segments=120000#最大2分钟，减少显存占用
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

        # 针对大于10分钟的视频，重新进行切割
        dir_name = f"{config.TEMP_DIR}/clip_{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        kw = {
            "input_wav": self.audio_file,
            "threshold": 0.45,
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