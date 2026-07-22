import time
import threading,shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from videotrans.configure.config import tr, app_cfg, settings, logger
from videotrans.configure import config
from videotrans.translator import get_audio_code
from videotrans.task._base import BaseTask
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.configure import contants

from videotrans.task._stage_prepare import PrepareMixin
from videotrans.task._stage_recogn import RecognMixin
from videotrans.task._stage_diariz import DiarizMixin
from videotrans.task._stage_translate import TranslateMixin
from videotrans.task._stage_dubbing import DubbingMixin
from videotrans.task._stage_align import AlignMixin
from videotrans.task._stage_audio import AudioMixin
from videotrans.task._stage_subtitle import SubtitleMixin
from videotrans.task._stage_assemble import AssembleMixin


@dataclass
class TransCreate(
    AssembleMixin,
    SubtitleMixin,
    AudioMixin,
    AlignMixin,
    DubbingMixin,
    TranslateMixin,
    DiarizMixin,
    RecognMixin,
    PrepareMixin,
    BaseTask,
):
    cfg: TaskCfgVTT = field(default_factory=TaskCfgVTT, repr=False)
    source_srt_list: List = field(default_factory=list)
    target_srt_list: List = field(default_factory=list)
    video_time: float = 0.0
    video_info: Dict = field(default_factory=dict, repr=False)
    is_copy_video: bool = False
    video_codec_num: int = 264
    ignore_align: bool = False
    is_audio_trans: bool = False
    queue_tts: List = field(default_factory=list, repr=False)
    clone_ref: str = ""
    cost_duration:float=0.0
    should_recogn2:bool=False

    def __post_init__(self):
        super().__post_init__()
        self.cost_duration=time.time()
        if not self.cfg.cache_folder:
            self.cfg.cache_folder = f"{config.TEMP_DIR}/{self.uuid}"
        if self.cfg.clear_cache:
            if self.cfg.target_dir and Path(self.cfg.target_dir).is_dir():
                shutil.rmtree(self.cfg.target_dir, ignore_errors=True)
            if self.cfg.cache_folder and Path(self.cfg.cache_folder).is_dir():
                shutil.rmtree(self.cfg.cache_folder, ignore_errors=True)

        self.signal(text=tr('kaishichuli'))
        self.max_speakers = self.cfg.nums_diariz if self.cfg.enable_diariz else -1
        if self.max_speakers > 0:
            self.max_speakers += 1
        self.should_recogn = True
        self.video_codec_num = int(settings.get('video_codec', 264))

        self.cfg.detect_language = get_audio_code(show_source=self.cfg.source_language_code)

        self.cfg.novoice_mp4 = f"{self.cfg.cache_folder}/novoice.mp4"

        self.cfg.source_sub = f"{self.cfg.target_dir}/{self.cfg.source_language_code}.srt"
        self.cfg.source_wav_output = f"{self.cfg.target_dir}/{self.cfg.source_language_code}.m4a"
        self.cfg.source_wav = f"{self.cfg.cache_folder}/{self.cfg.source_language_code}.wav"

        self.cfg.target_sub = f"{self.cfg.target_dir}/{self.cfg.target_language_code}.srt"
        self.cfg.target_wav_output = f"{self.cfg.target_dir}/{self.cfg.target_language_code}.m4a"
        self.cfg.target_wav = f"{self.cfg.cache_folder}/target.wav"

        self.cfg.targetdir_mp4 = f"{self.cfg.target_dir}/{self.cfg.noextname}.mp4"

        if self.cfg.voice_role and self.cfg.voice_role != 'No' and self.cfg.target_language_code:
            self.should_dubbing = True

        if self.cfg.app_mode != 'tiqu' and (self.should_dubbing or self.cfg.subtitle_type > 0):
            self.should_hebing = True

        if self.cfg.target_language_code and self.cfg.target_language_code != self.cfg.source_language_code:
            self.should_trans = True

        if self.cfg.voice_role and self.cfg.voice_role != 'No' and self.cfg.source_language_code == self.cfg.target_language_code:
            self.cfg.target_wav_output = f"{self.cfg.target_dir}/{self.cfg.target_language_code}-dubbing.m4a"
            self.cfg.target_wav = f"{self.cfg.cache_folder}/target-dubbing.wav"
            self.should_dubbing = True

        if self.cfg.ext in contants.AUDIO_EXITS:
            self.is_audio_trans = True
            self.should_hebing = False

        if not self.cfg.target_language_code:
            self.should_dubbing = False
            self.should_trans = False

        if self.cfg.voice_role == 'No':
            self.should_dubbing = False

        if self.cfg.app_mode == 'tiqu':
            self.cfg.enable_diariz = False
            self.should_dubbing = False
        self.should_separate = self.cfg.is_separate
        self.should_recogn2 = self.cfg.recogn2pass and self.should_dubbing and self.cfg.subtitle_type<3 and (self.cfg.source_language_code != self.cfg.target_language_code)

        self.cfg.vocal = f"{self.cfg.cache_folder}/vocal.wav"
        self.cfg.instrument = f"{self.cfg.cache_folder}/instrument.wav"

        logger.debug(f"[TransCreate]最终配置信息：{self=}\n{self.cfg=}")
        self.signal(text="forbid", type="disabled_edit")

        def runing():
            t = time.time()
            while not self.hasend:
                if self._exit(): return
                time.sleep(1)
                self.signal(text=f"{int(time.time() - t)}???{self.precent}", type="set_precent")

        if app_cfg.exec_mode != 'cli':
            threading.Thread(target=runing, daemon=True).start()

