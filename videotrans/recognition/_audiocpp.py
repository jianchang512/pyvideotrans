import json
import logging,time
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union, Dict, Any

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure._paths import ROOT_DIR
from videotrans.configure.config import params,settings,logger
from videotrans.configure.constants import AUDIOCPP_ASR_MODELS
from videotrans.configure.excepts import NO_RETRY_EXCEPT, SpeechToTextError
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util._srt_parse import ms_to_time_string
from videotrans.util.help_down import down_audiocpp_bin, down_file_from_hf
from videotrans.util.help_misc import exec_audiocpp


@dataclass(repr=False)
class AudiocppRecogn(BaseRecogn):
    gguf_obj: Dict[str, Any] = field(default_factory=dict, repr=False)
    def __post_init__(self):
        super().__post_init__()


    def _download(self):
        self.signal(text=f'Checking audio.cpp cli exists ')
        down_audiocpp_bin(process_callback=self._process_callback)

        self.gguf_obj = AUDIOCPP_ASR_MODELS.get(self.model_name)
        if not self.gguf_obj or not self.gguf_obj.get('file') or not self.gguf_obj.get('url'):
            raise RuntimeError(f'No {self.model_name} in Audio.cpp\n{self.gguf_obj}')


        gguf_file = f"{ROOT_DIR}/audio_cpp/models/{self.gguf_obj.get('file')}"

        if Path(gguf_file).exists(): return True
        model_url = self.gguf_obj.get('url', '').replace('https://huggingface.co', '')
        down_file_from_hf(
            Path(gguf_file).parent.as_posix(),
            [model_url],
            self._process_callback)
        return True

    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        self.signal(text=f"start speech to srt")



        raws = self.cut_audio()
        langcode=None
        if self.detect_language !='auto' and self.gguf_obj.get('allow_language_tag'):
            langcode = self.detect_language.split('-')[0].lower()


        err=''
        ok_nums=0
        for i, it in enumerate(raws):
            txt_file=f'{self.cache_folder}/audio_asr_txt_{i}.txt'
            cmd = [
                        f"{ROOT_DIR}/audio_cpp/audiocpp_cli",
                        "--task",
                        "asr",
                        "--family",
                        self.model_name,
                        "--model",
                        f"models/{self.gguf_obj['file']}",
                        "--backend",
                        "best",
                        "--audio",
                        it['filename'],
            ]
            if langcode:
                cmd.extend(['--language',langcode])

            if self.gguf_obj.get('extra'):
                cmd.extend(self.gguf_obj.get('extra'))
            cmd.extend(["--text-out",txt_file])
            exec_audiocpp(cmd)
            text=Path(txt_file).read_text(encoding="utf-8").strip() if Path(txt_file).exists() else None
            if self.model_name=='moss_transcribe_diarize':
                text=re.sub(r'\[[a-zA-Z0-9_.-]+?\]','',text,flags=re.I)
            if not text:
                err=f'error:{i} {cmd=}'
                continue
            raws[i]['text'] =text
            ok_nums+=1
        if ok_nums<1:
            raise SpeechToTextError(err)
        return raws

