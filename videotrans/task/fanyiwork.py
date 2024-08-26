import hashlib
import json
import os
import queue
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.translator import run as run_trans
from videotrans.util.tools import get_subtitle_from_srt


class FanyiWorker(QThread):
    uito = Signal(str)

    def __init__(self, type, target_language, files, parent=None):
        super(FanyiWorker, self).__init__(parent)
        self.type = type
        self.target_language = target_language
        self.files = files
        self.srts = ""
        md5_hash = hashlib.md5()
        md5_hash.update(f"{time.time()}{len(files)}{type}{target_language}".encode('utf-8'))
        self.uuid = md5_hash.hexdigest()
        self.end = False

    def post(self, msg):
        self.uito.emit(json.dumps(msg))

    def run(self):
        def getqueulog(uuid):
            while 1:
                if self.end or config.exit_soft:
                    return
                q = config.queue_dict.get(uuid)
                if not q:
                    config.queue_dict[uuid]=queue.Queue()
                    continue
                try:
                    data = q.get(True, 0.5)
                    if data:
                        print(f'@@@@@@@@@@@@@@@@@@@@@@@@@@@@{data=}')
                        self.post(data)
                except Exception:
                    pass

        threading.Thread(target=getqueulog, args=(self.uuid,)).start()

        # 开始翻译,从目标文件夹读取原始字幕
        config.box_trans = "ing"
        if not self.files:
            self.post({"type": 'error', 'text': 'no srt file'})
            return
        target = config.homedir + '/translate'
        Path(target).mkdir(parents=True, exist_ok=True)

        for i, f in enumerate(self.files):
            print(f'{i=},{f=}')
            if config.exit_soft:
                return
            try:
                self.post({"type": "clear_target"})
                rawsrt = get_subtitle_from_srt(f, is_file=True)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.post({
                    "type": 'error',
                    "text": f"{config.transobj['srtgeshierror']}:{f}{str(e)}"
                })
                return
            try:
                self.post({'type':"logs","text":f"processing {Path(f).name}"})
                self.post({"type": "set_source", "text": Path(f).read_text(encoding='utf-8')})
                srt = run_trans(
                    translate_type=self.type,
                    text_list=rawsrt,
                    target_language_name=self.target_language,
                    uuid=self.uuid,
                    set_p=True)
                srts_tmp = ""
                for it in srt:
                    srts_tmp += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
                with open(target + '/' + os.path.basename(f), 'w', encoding='utf-8') as f:
                    f.write(srts_tmp)
                self.post({"type": "replace", "text": srts_tmp})
                self.post({"type": "logs", "text": f'{round((i + 1) * 100 / len(self.files), 2)}%'})
            except Exception as e:
                self.post({"type": "error", "text": str(e)})
                return
        self.end = True
        self.post({"type": 'ok'})
