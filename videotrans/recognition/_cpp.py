# ToDo 将 whisper.cpp 移动到此
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from videotrans.configure import contants
from videotrans.configure._paths import ROOT_DIR
from videotrans.configure.config import tr, settings, logger
from videotrans.configure.contants import WHISPER_CPP_URL_MS, WHISPER_CPP_URL_HF, WHISPERCPP_MODEL_URL_MS, \
    WHISPERCPP_MODEL_URL_HF
from videotrans.configure.excepts import SpeechToTextError
from videotrans.recognition._base import BaseRecogn
from videotrans.util._srt_parse import get_subtitle_from_srt
from videotrans.util.help_down import down_zip
from videotrans.util.help_misc import is_connect_hf


@dataclass
class CPPRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.cpp_path=f'{ROOT_DIR}/whisper-cpp/whisper-cli'#whisper-cli.exe | whisper-cli


    def _win_download_cli(self):
        # windows上自动下载exe
        self.signal(text=f'Download whisper-cli.exe ')
        down_zip(f'{ROOT_DIR}', WHISPER_CPP_URL_MS  if is_connect_hf() is False else WHISPER_CPP_URL_HF, callback=self._process_callback)


    def _exec(self):
        if sys.platform=='win32':
            self.cpp_path+='.exe'
        Path_cpp=Path(self.cpp_path)
        if not Path_cpp.is_file():
            if sys.platform!='win32':
                raise SpeechToTextError(tr('download whisper.cpp or make binary',f'{ROOT_DIR}/whisper-cpp'))
            self._win_download_cli()

        if not Path(f'{ROOT_DIR}/models/{self.model_name}').is_file():
            from videotrans.util import help_down
            if not is_connect_hf():
                url=WHISPERCPP_MODEL_URL_MS.replace('{}',self.model_name)
            else:
                url=WHISPERCPP_MODEL_URL_HF.replace('{}',self.model_name)
            help_down.down_file_from_hf(
                f"{ROOT_DIR}/models",
                [url],
                self._process_callback)
        txt_file = ROOT_DIR + '/pyvideotrans.txt'

        cmd = [
            self.cpp_path,
            "-p",str(max(min(4,int(os.cpu_count())-1),1)),
            "-f",
            self.audio_file,
            "-osrt",
            "-nth",str(float(settings.get('no_speech_threshold', 0.6))),
            "-pp",
            "-np"

        ]
        _lang=self.detect_language.split('-')[0]
        cmd += ["-l", _lang]
        prompt = settings.get(f'initial_prompt_{self.detect_language}')
        if prompt:
            cmd += ['--prompt', prompt]
        if _lang.lower() !='auto':
            # 最多2倍设定字幕字符长度，防止过长
            _ml=2*int(settings.get('cjk_len', 15) if _lang in contants.CJK_LANG else settings.get('other_len', 60))
            cmd+=['-ml', str(_ml)]

        if txt_file and Path(txt_file).exists():
            cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))
        
        _sub=f'{self.cache_folder}/cpp_srt'
        cmd.extend(['-m', f'{ROOT_DIR}/models/{self.model_name}', '-of', _sub])
        logger.debug(f'Whisper.cpp: {cmd=}')

        try:
            self.signal(text=tr("Transcription in progress, please wait"))
            log_file_path = f"{self.cache_folder}/whisper.cpp.log"
            all_logs = []

            # 2. 使用 Popen 启动子进程（实时流模式）
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将 stderr 合并到 stdout，统一读取进度和日志
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                cwd=f'{self.cache_folder}',
                bufsize=1  # 开启行缓冲，确保逐行实时输出
            )

            # 3. 打开日志文件，一边写日志，一边解析进度
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                for line in process.stdout:
                    # A. 写入日志文件并立刻 flush（保证外部查看 log 时也是实时的）
                    log_file.write(line)
                    log_file.flush()

                    # B. 收集日志，以防出错时需要抛出完整报错
                    all_logs.append(line)

                    # C. 用正则表达式抓取进度百分比
                    # whisper.cpp 输出进度格式通常为: "whisper_full_with_state: progress =  50%"
                    match = re.search(r'progress\s*=\s*(\d+)%', line)
                    if match:
                        percent = match.group(1)
                        # D. 实时向界面/信号发送最新的百分比进度
                        self.signal(text=f"{tr('Transcription in progress, please wait')}: {percent}%")

            # 4. 等待进程结束并获取状态码
            return_code = process.wait()

            if return_code != 0:
                # 进程异常退出，抛出收集到的全部错误日志
                raise SpeechToTextError("".join(all_logs))
            try:
                Path(log_file_path).unlink(missing_ok=True)
            except OSError:
                pass
            return get_subtitle_from_srt(_sub + ".srt", is_file=True)
        except Exception as e:
            raise SpeechToTextError(str(e))