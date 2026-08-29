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
    # 全局状态标识
    stoped_uuid_set: set = field(default_factory=set)
    global_msg: List = field(default_factory=list)
    exit_soft: bool = False
    current_status: str = "stop"

    # 全局窗口
    child_forms: Dict = field(default_factory=dict)
    INFO_WIN: Dict = field(default_factory=lambda: {"data": {}, "win": None})
    # 分离后的无声视频画面
    queue_novice: Dict = field(default_factory=dict)
    task_countdown: int = 0
    # 批量翻译队列
    prepare_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    regcon_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    diariz_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    trans_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    dubb_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    align_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    regcon2_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    assemb_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    taskdone_queue: Queue = field(default_factory=lambda: Queue(maxsize=0))
    
    
    # 单视频模式变量，传递各个编辑窗口
    # 单视频倒计时
    onlyone_source_sub: Any = None
    onlyone_source_wav: Any = None
    onlyone_target_sub: Any = None
    onlyone_target_wav: Any = None
    onlyone_novoice_mp4: Any = None
    onlyone_name: Any = None
    onlyone_voice_role: Any = None
    onlyone_recogn2_video:Any=None
    onlyone_voice_autorate:bool=True
    onlyone_video_autorate:bool=False    
    onlyone_align_sub_audio:bool=True
    onlyone_remove_silent_mid:bool=False
    onlyone_trans: bool = False
    onlyone_is_cuda:bool=False
    onlyone_importsrtfile:str=None

    # cli模式、qt界面模式、web模式
    exec_mode: str = "gui"
    # 视频编码
    video_codec: Any = None
    # 支持的硬件编码
    codec_cache: Dict = field(default_factory=dict)
    # 单视频按行分配角色
    line_roles: Dict = field(default_factory=dict)
    # 按角色配音功能
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
