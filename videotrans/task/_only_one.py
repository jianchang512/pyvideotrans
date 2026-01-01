# 执行单个视频翻译任务时 暂停等待
import json,os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydub import AudioSegment
from PySide6.QtCore import QThread, Signal, QObject

from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.task.taskcfg import TaskCfg

from videotrans.task.trans_create import TransCreate
from videotrans.util import tools


class Worker(QThread):
    uito = Signal(str)

    def __init__(self, *,
                 parent: Optional[QObject] = None,
                 obj_list: Optional[List[Dict[str, Any]]] = None,
                 cfg: Optional[Dict[str, Any]] = None):
        super().__init__(parent=parent)
        self.cfg = cfg
        # 存放处理好的 视频路径等信息
        self.obj_list = obj_list
        self.uuid = None
    # 使用冗余的 if self._exit(): return 来处理倒计时延迟问题
    def run(self) -> None:
        obj=self.obj_list[0]
        try:
            self.uuid = obj['uuid']
            trk = TransCreate(cfg=TaskCfg(**self.cfg|obj))
            # 原始语言字幕文件
            config.onlyone_source_sub=trk.cfg.source_sub
            # 目标语言字幕文件
            config.onlyone_target_sub=trk.cfg.target_sub
            if self._exit(): return
            config.task_countdown = 0
            trk.prepare()
            if self._exit(): return
            trk.recogn()
            if self._exit(): return
            trk.diariz()
            if self._exit(): return
            self._post(text=Path(trk.cfg.source_sub).read_text(encoding='utf-8'), type='replace_subtitle')

            if float(config.settings.get('countdown_sec',0))>0:
                config.task_countdown=86400
                self._post(text='', type='edit_subtitle_source')
                self._post(tr('The subtitle editing interface is rendering'))
                # 等待编辑原字幕后翻译,允许修改字幕
                while config.task_countdown > 0:
                    time.sleep(1)
                    config.task_countdown -= 1
                    if self._exit(): return
            
            if trk.shoud_trans:
                config.onlyone_trans=True
                if tools.vail_file(trk.cfg.target_sub):
                    self._post(text="已存在翻译文件，跳过")
                else:
                    trk.trans()
            
            if self._exit(): return
            
            # 插入指定说话人，进行倒计时处理后再返回此处继续
            # 需要配音时
            if trk.shoud_dubbing:
                self._post(text=Path(trk.cfg.target_sub).read_text(encoding='utf-8'), type='replace_subtitle')
                if float(config.settings.get('countdown_sec',0))>0:
                    config.task_countdown=86400
                    # 传递过去临时目录，用于获取 speaker.json
                    self._post(text=f'{trk.cfg.cache_folder}<|>{trk.cfg.target_language_code}<|>{trk.cfg.tts_type}', type="edit_subtitle_target")
                    self._post(tr('The subtitle editing interface is rendering'))
                    while config.task_countdown > 0:
                        if self._exit(): return
                        # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
                        time.sleep(1)
                        # 倒计时中
                        config.task_countdown -= 1

                if not self._exit():
                    trk.dubbing()

                # 没有忽略配音
                if not trk.ignore_align and float(config.settings.get('countdown_sec',0))>0:
                        # 调整配音，对 trk.queue_tts 进行调整
                    for it in trk.queue_tts:
                        if self._exit(): return
                        # 当前配音时长,0=不存在配音文件
                        it['dubbing_s']=(len(AudioSegment.from_file(it['filename'])) if tools.vail_file(it['filename']) else 0)/1000.0

                    # 存入临时目录
                    Path(f'{trk.cfg.cache_folder}/queue_tts.json').write_text(json.dumps(trk.queue_tts,ensure_ascii=False),encoding='utf-8')

                    config.task_countdown=86400
                    self._post(text=f"{trk.cfg.cache_folder}<|>{trk.cfg.target_language_code}", type='edit_dubbing')
                    self._post(text=tr('The subtitle editing interface is rendering'))
                    while config.task_countdown > 0:
                        if self._exit(): return
                        # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
                        time.sleep(1)
                        # 倒计时中
                        config.task_countdown -= 1

                    # 重新整理赋值给 trk.queue_tts
                    trk.queue_tts=json.loads(Path(f'{trk.cfg.cache_folder}/queue_tts.json').read_text(encoding='utf-8'))


            if not self._exit():
                trk.align()
            
            if not self._exit():
                trk.assembling()
            
            if not self._exit():
                trk.task_done()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._post(text=str(e), type='error')

    def _post(self, text='', type='logs'):
        try:
            self.uito.emit(json.dumps({"text": text, "type": type, 'uuid': self.uuid}))
        except TypeError:
            pass

    def _exit(self):
        if config.exit_soft or config.current_status != 'ing':
            return True
        return False
