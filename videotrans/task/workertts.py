# -*- coding: utf-8 -*-
# primary ui
import copy
import json
import os
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.task._rate import SpeedRate
from videotrans.tts import run as run_tts
from videotrans.util import tools
from videotrans.util.tools import get_subtitle_from_srt


# 合成
class WorkerTTS(QThread):
    uito = Signal(str)

    def __init__(self, *,
                 files=None,
                 role=None,
                 rate=None,
                 volume="+0%",
                 pitch="+0Hz",
                 wavname=None,
                 tts_type=None,
                 voice_autorate=False,
                 langcode=None,
                 out_ext='wav',
                 parent=None):
        super(WorkerTTS, self).__init__(parent)
        self.volume = volume
        self.pitch = pitch
        self.all_text = []
        self.files = files
        self.role = role
        self.rate = rate
        self.out_ext=out_ext
        self.wavname = wavname
        self.tts_type = tts_type
        self.langcode = langcode
        self.voice_autorate = voice_autorate
        self.tmpdir = config.TEMP_HOME
        Path(self.tmpdir).mkdir(parents=True, exist_ok=True)
        self.uuid = tools.get_md5(
            f"{time.time()}{out_ext}{role}{rate}{volume}{pitch}{voice_autorate}{','.join(files)}{tts_type}{langcode}")
        self.end = False

    def run(self):
        config.box_tts = 'ing'

        def getqueulog(uuid):
            while 1:
                if self.end or config.exit_soft:
                    return
                q = config.queue_dict.get(uuid)
                if not q:
                    continue
                try:
                    data = q.get(True, 0.5)
                    if data:
                        self.post(data)
                except Exception:
                    pass

        threading.Thread(target=getqueulog, args=(self.uuid,)).start()
        # 字幕格式
        self.all_text = []
        for it in self.files:
            content = ""
            try:
                with open(it, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            except:
                with open(it, 'r', encoding='gbk') as f:
                    content = f.read().strip()
            finally:
                if content:
                    self.all_text.append({"text": content, "file": os.path.basename(it)})
        try:
            errs, success = self.before_tts()
            config.box_tts = 'stop'
            if success == 0:
                self.post({"type": "error", "text": '全部失败了请打开输出目录中txt文件查看失败记录'})
            elif errs > 0:
                self.post({"type": "error", "text": f"error:失败{errs}个，成功{success}个，请查看输出目录中txt文件查看失败记录"})
        except Exception as e:
            self.post({"type": "error", "text": f'error:{str(e)}'})

        config.box_tts = 'stop'
        self.post({"type": "ok", "text": ""})

    def post(self, jsondata):
        self.uito.emit(json.dumps(jsondata))

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
        # 如果仅仅生成配音，则不限制时长
        # 整合一个队列到 exec_tts 执行
        length = len(self.all_text)
        errs = 0
        config.settings['remove_white_ms'] = int(config.settings['remove_white_ms'])
        jd = 0
        for n, item in enumerate(self.all_text):
            jd += (n / length)
            queue_tts = []
            # 获取字幕
            self.post({"type": "replace", "text": item["text"]})
            subs = get_subtitle_from_srt(item["text"], is_file=False)

            # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
            self.post({"type": "jd", "text": f'{round(jd * 100, 2)}%'})
            for k, it in enumerate(subs):
                queue_tts.append({
                    "text": it['text'],
                    "role": self.role,
                    "start_time_source": it['start_time'],
                    "start_time": it['start_time'],
                    "end_time_source": it['end_time'],
                    "end_time": it['end_time'],
                    "rate": self.rate,
                    "startraw": it['startraw'],
                    "endraw": it['endraw'],
                    "tts_type": self.tts_type,
                    "language": self.langcode,
                    "pitch": self.pitch,
                    "volume": self.volume,
                    "filename": f"{self.tmpdir}/tts-{time.time()}-{it['start_time']}.mp3"})
            try:
                run_tts(queue_tts=copy.deepcopy(queue_tts), language=self.langcode, set_p=True, uuid=self.uuid)
                audio_inst = SpeedRate(
                    queue_tts=copy.deepcopy(queue_tts),
                    shoud_audiorate=self.voice_autorate,
                    uuid=self.uuid,
                    # 处理后的配音文件
                    target_audio=f'{self.wavname}-{Path(item["file"]).stem}.{self.out_ext}'
                )
                audio_inst.run()
            except Exception as e:
                import traceback
                traceback.print_stack(file=f'{self.wavname}-error.txt')
                errs += 1
                self.post({"type": "logs", "text": f'srt文件 {item["file"]} 合成失败，原因为:{str(e)}'})
        return errs, length - errs
