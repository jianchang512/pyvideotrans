# 执行语音识别
import os
import re

from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition import run as run_recogn


class RecognWorker(QThread):
    uito = Signal(str)
    def __init__(self, *,
                 audio_paths=None,
                 model=None,
                 language=None,
                 model_type='faster',
                 out_path=None,
                 is_cuda=False,
                 split_type='all',
                 parent=None):
        super(RecognWorker, self).__init__(parent)
        self.audio_paths = audio_paths
        self.model = model
        self.model_type = model_type
        self.language = language
        self.out_path = out_path
        self.is_cuda = is_cuda
        self.split_type = split_type

    def run(self):
        errs = []
        length = len(self.audio_paths)
        time_dur = 1
        while len(self.audio_paths) > 0:
            try:
                config.box_recogn = 'ing'
                audio_path = self.audio_paths.pop(0)
                if not audio_path.endswith('.wav'):
                    outfile = config.TEMP_HOME + "/" + os.path.basename(audio_path) + '.wav'
                    cmd = [
                        "-y",
                        "-i",
                        audio_path,
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        outfile
                    ]
                    tools.runffmpeg(cmd)
                    audio_path = outfile
                if not os.path.exists(audio_path):
                    errs.append(f'{audio_path} 不存在')
                    continue

                jindu = f'{int((length - len(self.audio_paths)) * 49 / length)}%'
                self.uito.emit(f'jd:{jindu}')
                srts = run_recogn(
                    type=self.split_type,
                    audio_file=audio_path,
                    model_name=self.model,
                  detect_language=self.language,
                  set_p=False,
                  cache_folder=config.TEMP_DIR,
                  model_type=self.model_type,
                  is_cuda=self.is_cuda)
                text = []
                for it in srts:
                    text.append(f'{it["line"]}\n{it["time"]}\n{it["text"].strip(".")}')
                text = "\n\n".join(text)
                with open(self.out_path + f"/{os.path.basename(audio_path)}.srt", 'w', encoding='utf-8') as f:
                    f.write(text)
                self.uito.emit(f'replace:{text}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                msg = f'{str(e)}{str(e.args)}'
                errs.append(f'失败，{msg}')
                if re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M):
                    msg = f'【缺少cuBLAS.dll】请点击菜单栏-帮助/支持-下载cublasxx.dll,或者切换为openai模型  {msg}' if config.defaulelang == 'zh' else f'[missing cublasxx.dll] Open menubar Help&Support->Download cuBLASxx.dll or use openai model {msg}'
                elif re.search(r'out\s+?of.*?memory', msg, re.I):
                    msg = f'显存不足，请使用较小模型，比如 tiny/base/small {msg}' if config.defaulelang == 'zh' else f'Insufficient video memory, use a smaller model such as tiny/base/small {msg}'
                elif re.search(r'cudnn', msg, re.I):
                    msg = f'cuDNN错误，请尝试升级显卡驱动，重新安装CUDA12.x和cuDNN9 {msg}' if config.defaulelang == 'zh' else f'cuDNN error, please try upgrading the graphics card driver and reinstalling CUDA12.x and cuDNN9 {msg}'
                self.uito.emit('error:{msg}')
                config.box_recogn = 'stop'
                return
        self.uito.emit('ok')
        config.box_recogn = 'stop'

