# 执行单个视频翻译任务时 暂停等待
import json
import time
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import QThread, Signal, QObject
from pydub import AudioSegment

from videotrans.configure.config import tr, settings, app_cfg, logger
from videotrans.task.taskcfg import TaskCfgVTT, SignMsg, InputFile
from videotrans.task.trans_create import TransCreate
from videotrans.util import tools


class Worker(QThread):
    uito = Signal(str, SignMsg)

    def __init__(self, *,
                 parent: Optional[QObject] = None,
                 obj_list: Optional[List[InputFile]] = None,
                 cfg: Optional[Dict[str, Any]] = None):
        super().__init__(parent=parent)
        self.cfg = cfg
        # 存放处理好的 视频路径等信息
        self.obj_list = obj_list
        self.uuid = None

    def run(self) -> None:
        obj = self.obj_list[0]
        # 从停止队列中移出，以便重新开始
        app_cfg.rm_uuid(obj['uuid'])
        logger.debug(f'[单视频翻译模式]:{obj.name}')
        try:
            self.uuid = obj['uuid']
            trk = TransCreate(cfg=TaskCfgVTT(**self.cfg | obj))
            # 原始语言字幕文件
            app_cfg.onlyone_source_sub = trk.cfg.source_sub
            # 目标语言字幕文件
            app_cfg.onlyone_target_sub = trk.cfg.target_sub
            if self._exit(): return
            app_cfg.set_countdown(0)
            trk.prepare()
            if self._exit(): return
            trk.recogn()
            if self._exit(): return
            trk.diariz()
            if self._exit(): return
            self._post(text=Path(trk.cfg.source_sub).read_text(encoding='utf-8'), type='replace_subtitle')

            if float(settings.get('countdown_sec', 0)) > 0:
                app_cfg.set_countdown(86400)
                self._post(text='', type='edit_subtitle_source')
                self._post(tr('The subtitle editing interface is rendering'))
                while app_cfg.task_countdown > 0:
                    time.sleep(1)
                    app_cfg.set_countdown(app_cfg.task_countdown - 1)
                    if self._exit(): return

            if trk.shoud_trans:
                app_cfg.onlyone_trans = True
                if tools.vail_file(trk.cfg.target_sub):
                    self._post(text="已存在翻译文件，跳过")
                else:
                    trk.trans()

            if self._exit(): return

            # 需要配音时
            if trk.shoud_dubbing:
                self._post(text=Path(trk.cfg.target_sub).read_text(encoding='utf-8'), type='replace_subtitle')
                if float(settings.get('countdown_sec', 0)) > 0:
                    app_cfg.set_countdown(86400)
                    # 传递过去临时目录，用于获取 speaker.json
                    self._post(text=f'{trk.cfg.cache_folder}<|>{trk.cfg.target_language_code}<|>{trk.cfg.tts_type}', type="edit_subtitle_target")
                    self._post(tr('The subtitle editing interface is rendering'))
                    while app_cfg.task_countdown > 0:
                        if self._exit(): return
                        time.sleep(1)
                        app_cfg.set_countdown(app_cfg.task_countdown - 1)

                if not self._exit():
                    trk.dubbing()

                if not trk.ignore_align and float(settings.get('countdown_sec', 0)) > 0:
                    for it in trk.queue_tts:
                        if self._exit(): return
                        # 当前配音时长,0=不存在配音文件
                        it['dubbing_s'] = (len(AudioSegment.from_file(it['filename'])) if tools.vail_file(
                            it['filename']) else 0) / 1000.0

                    # 存入临时目录
                    Path(f'{trk.cfg.cache_folder}/queue_tts.json').write_text(
                        json.dumps(trk.queue_tts, ensure_ascii=False), encoding='utf-8')

                    app_cfg.set_countdown(86400)
                    self._post(text=f"{trk.cfg.cache_folder}<|>{trk.cfg.target_language_code}", type='edit_dubbing')
                    self._post(text=tr('The subtitle editing interface is rendering'))
                    while app_cfg.task_countdown > 0:
                        if self._exit(): return
                        time.sleep(1)
                        app_cfg.set_countdown(app_cfg.task_countdown - 1)

            if not self._exit():
                trk.align()

            if not self._exit():
                trk.recogn2pass()

            if not self._exit():
                trk.assembling()

            if not self._exit():
                trk.task_done()
            self._post(text="", type='end')
        except Exception as e:
            logger.exception(f'单视频模式翻译失败{e}',exc_info=True)
            detail_back = (traceback.format_exc()).strip()
            self._post(text=str(e) + f"\n{detail_back}", type='error')

    def _post(self, text='', type='logs'):
        try:
            if self.uuid in app_cfg.stoped_uuid_set: return
            self.uito.emit(self.uuid, SignMsg(**{"text": text, "type": type, 'uuid': self.uuid}))
        except (ValueError,IndexError,TypeError):
            pass

    def _exit(self):
        if app_cfg.exit_soft or app_cfg.current_status != 'ing':
            return True
        return False
