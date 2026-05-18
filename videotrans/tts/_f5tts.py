from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import  handle_file
from videotrans.tts._gradio import GradioBase
from pydub import AudioSegment


@dataclass
class F5TTS(GradioBase):

    MAX_REF_AUDIO_MS=12000

    def __post_init__(self):
        self.ainame = "f5tts"
        super().__post_init__()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        ref_wav,ref_text=self.get_ref_wav(data_item)
        speed_slider = 0.5 if ref_text  and len(ref_text) < 10 else self.get_speed()
        kwargs={
            "ref_audio_input":handle_file(ref_wav),
            "ref_text_input":ref_text,
            "gen_text_input":data_item['text'].strip(),
            "remove_silence":True,
            "randomize_seed":True,
            "seed_input":0,  # 开启随机后，这个数字会被忽略，填多少都行
            "cross_fade_duration_slider":0.0, # 默认交叉淡入淡出时长
            "nfe_slider":32,            # 默认推理步数，F5-TTS 推荐 32
            "speed_slider":speed_slider,
            "api_name":'/basic_tts'
        }
        ref_wav_audio=AudioSegment.from_file(ref_wav)
        if len(ref_wav_audio)>self.MAX_REF_AUDIO_MS:
            ref_wav_audio[:self.MAX_REF_AUDIO_MS].export(ref_wav)

        return self._send(kwargs,data_item)
