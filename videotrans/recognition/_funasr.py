# stt项目识别接口
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

from funasr import AutoModel
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


@dataclass
class FunasrRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()

    def remove_unwanted_characters(self, text: str) -> str:
        # 保留中文、日文、韩文、英文、数字和常见符号，去除其他字符
        allowed_characters = re.compile(r'[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af'
                                        r'a-zA-Z0-9\s.,!@#$%^&*()_+\-=\[\]{};\'"\\|<>/?，。！｛｝【】；‘’“”《》、（）￥]+')
        return re.sub(allowed_characters, '', text)

    def _tosend(self, msg):
        self._signal(text=msg)

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        msg = tr("The model needs to be downloaded from modelscope.cn, which may take a long time, please be patient")
        self._tosend(msg)
        if self.model_name == 'SenseVoiceSmall':
            return self._exec1()
        raw_subtitles = []

        model = AutoModel(
            model=self.model_name, model_revision="v2.0.5",
            vad_model="fsmn-vad", vad_model_revision="v2.0.4",
            punc_model="ct-punc", punc_model_revision="v2.0.4",
            local_dir=config.ROOT_DIR + "/models",
            hub='ms',
            spk_model="cam++" if config.params.get('paraformer_spk', False) else None, spk_model_revision="v2.0.2",
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=self.device
        )
        msg = tr("Model loading is complete, enter recognition")
        self._tosend(msg)
        res = model.generate(input=self.audio_file, return_raw_text=True, is_final=True,
                             sentence_timestamp=True, batch_size_s=100, disable_pbar=True)

        speaker_list=[]
        for it in res[0]['sentence_info']:
            if not it.get('text','').strip():
                continue

            if config.params.get('paraformer_spk', False):
                speaker_list.append(f"spk{it.get('spk', 0)}")
            tmp = {
                "line": len(raw_subtitles) + 1,
                "text":it['text'].strip(),
                "start_time": it['start'],
                "end_time": it['end'],
                "startraw": f'{tools.ms_to_time_string(ms=it["start"])}',
                "endraw": f'{tools.ms_to_time_string(ms=it["end"])}'
            }
            self._signal(text=it['text'] + "\n", type='subtitle')
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            raw_subtitles.append(tmp)
        if speaker_list:
            Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
        return raw_subtitles

    def _exec1(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        from funasr.utils.postprocess_utils import rich_transcription_postprocess
        model = AutoModel(
            model="iic/SenseVoiceSmall",
            punc_model="ct-punc",
            device=self.device,
            local_dir=config.ROOT_DIR + "/models",
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            trust_remote_code=True,
            hub='ms'
        )
        # vad
        vm = AutoModel(
            model="fsmn-vad",
            local_dir=config.ROOT_DIR + "/models",
            max_single_segment_time=int(float(config.settings.get('max_speech_duration_s',5))*1000),
            max_end_silence_time=int(config.settings.get('min_silence_duration_ms',500)),
            hub='ms',
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=self.device)
        msg = tr("Recognition may take a while, please be patient")
        self._tosend(msg)
        segments = vm.generate(input=self.audio_file)
        audiodata = AudioSegment.from_file(self.audio_file)

        srts = []
        for seg in segments[0]['value']:
            chunk = audiodata[seg[0]:seg[1]]
            filename = f"{config.TEMP_DIR}/{seg[0]}-{seg[1]}.wav"
            chunk.export(filename)
            res = model.generate(
                input=filename,
                language=self.detect_language[:2],  # "zh", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                disable_pbar=True
            )
            text = self.remove_unwanted_characters(rich_transcription_postprocess(res[0]["text"]))
            srt = {
                "line": len(srts) + 1,
                "text": text,
                "start_time": seg[0],
                "end_time": seg[1],
                "startraw": f'{tools.ms_to_time_string(ms=seg[0])}',
                "endraw": f'{tools.ms_to_time_string(ms=seg[1])}'
            }
            srt['time'] = f"{srt['startraw']} --> {srt['endraw']}"
            srts.append(srt)

            self._signal(
                text=text + "\n",
                type='subtitle'
            )
        return srts
