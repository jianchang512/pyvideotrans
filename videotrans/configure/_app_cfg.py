# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from queue import Queue
from typing import Dict, Any, List

from videotrans.configure._i18n import _get_langjson_list


@dataclass
class AppCfg:
    """
    存储直接属于 config.py 的运行时属性 (原全局变量)。
    """
    NVIDIA_GPU_NUMS: int = -1

    stoped_uuid_set: set = field(default_factory=set)
    global_msg: List = field(default_factory=list)
    exit_soft: bool = False
    indextts_default_choice: str = 'Same as the voice reference'

    child_forms: Dict = field(default_factory=dict)
    INFO_WIN: Dict = field(default_factory=lambda: {"data": {}, "win": None})

    queue_novice: Dict = field(default_factory=dict)
    current_status: str = "stop"
    task_countdown: int = 0

    prepare_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    regcon_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    diariz_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    trans_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    dubb_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    align_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    regcon2_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    assemb_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    taskdone_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))

    exec_mode: str = "gui"
    video_codec: Any = None
    codec_cache: Dict = field(default_factory=dict)
    line_roles: Dict = field(default_factory=dict)
    
    onlyone_source_sub: Any = None
    onlyone_source_wav: Any = None
    onlyone_target_sub: Any = None
    onlyone_target_wav: Any = None
    onlyone_novoice_mp4: Any = None
    onlyone_voice_autorate:bool=True
    onlyone_video_autorate:bool=False    
    onlyone_align_sub_audio:bool=True
    onlyone_remove_silent_mid:bool=False
    onlyone_trans: bool = False
    
    dubbing_role: Dict = field(default_factory=dict)
    SUPPORT_LANG: Dict = field(default_factory=dict)
    proxy: str = ''
    new_version_pvt = ""

    def __post_init__(self):
        self.SUPPORT_LANG = _get_langjson_list()


    def set_countdown(self, sec=86400):
        self.task_countdown = sec

    def rm_uuid(self, uuid=None):
        if not uuid:
            return
        try:
            self.stoped_uuid_set.remove(uuid)
        except KeyError:
            pass
