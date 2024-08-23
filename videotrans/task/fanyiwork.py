import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.util.tools import get_subtitle_from_srt
from videotrans.translator import run as run_trans

class FanyiWorker(QThread):
    uito = Signal(str)
    def __init__(self, type, target_language, files, parent=None):
        super(FanyiWorker, self).__init__(parent)
        self.type = type
        self.target_language = target_language
        self.files = files
        self.srts = ""

    def run(self):
        # 开始翻译,从目标文件夹读取原始字幕
        config.box_trans = "ing"
        if not self.files:
            self.uito.emit("error:no srt file")
            return
        target = config.homedir+'/translate'
        Path(target).mkdir(parents=True,exist_ok=True)

        jd=1
        for i,f in enumerate(self.files):
            try:
                rawsrt = get_subtitle_from_srt(f, is_file=True)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.uito.emit(f"error:{config.transobj['srtgeshierror']}:{f}" + str(e))
                return
            try:
                self.uito.emit(f'repsour:{Path(f).read_text(encoding="utf-8")}')
                srt = run_trans(translate_type=self.type, text_list=rawsrt, target_language_name=self.target_language,set_p=False)
                srts_tmp = ""
                for it in srt:
                    srts_tmp += f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
                with open(target+'/'+os.path.basename(f), 'w', encoding='utf-8') as f:
                    f.write(srts_tmp)
                self.uito.emit(f'replace:{srts_tmp}')

            except Exception as e:
                self.uito.emit(f'error:{str(e)}')
                return
        self.uito.emit(f'ok')
