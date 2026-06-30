from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

from .main_win import MainWindow
from videotrans.task.taskcfg import InputFile

from ._actions_base_mode import WinActionBaseModeMixin
from ._actions_base_file import WinActionBaseFileMixin
from ._actions_base_misc import WinActionBaseMiscMixin


@dataclass
class WinActionBase(WinActionBaseModeMixin, WinActionBaseFileMixin, WinActionBaseMiscMixin):
    main: MainWindow = field(default_factory=MainWindow, repr=False)
    law: Optional[Any] = None

    is_render: bool = field(default=False, init=False)
    is_batch: bool = field(default=True, init=False)
    had_click_btn: bool = field(default=False, init=False)
    removing_layout: bool = field(default=False, init=False)

    scroll_area: Optional[Any] = field(default=None, init=False)
    scroll_area_after: Optional[Any] = field(default=None, init=False)
    scroll_area_search: Optional[Any] = field(default=None, init=False)

    processbtns: Dict = field(default_factory=dict, init=False)
    obj_list: List[InputFile] = field(default_factory=list, init=False)
    cfg: Dict = field(default_factory=dict, init=False)
    queue_mp4: List[str] = field(default_factory=list, init=False)
    show_adv_status: bool = False
    retry_queue_mp4: List[InputFile] = field(default_factory=list, init=False)
    uuid_queue_mp4: Dict = field(default_factory=dict, init=False)
    _proxy_test_version: int = 0
