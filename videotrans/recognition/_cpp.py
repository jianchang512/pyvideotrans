# ToDo 将 whisper.cpp 移动到此
import re
import subprocess,platform
from dataclasses import dataclass
from pathlib import Path

from videotrans.configure import constants
from videotrans.configure._paths import ROOT_DIR
from videotrans.configure.config import tr, settings, logger, CPU_NUMS
from videotrans.configure.constants import WHISPER_CPP_URL_HF, WHISPER_CPP_LINUX_URL_HF,WHISPERCPP_MODEL_URL_HF
from videotrans.configure.excepts import SpeechToTextError
from videotrans.recognition._base import BaseRecogn
from videotrans.util._srt_parse import get_subtitle_from_srt
from videotrans.util.gpus import whisper_device
from videotrans.util.help_down import down_zip


_os=platform.system()

@dataclass(repr=False)
class CPPRecogn(BaseRecogn):

    def _download_cli(self):
        if  _os== 'Darwin':return
        # windows linux 上自动下载
        self.signal(text=f'Download whisper-cli')
        down_zip(f'{ROOT_DIR}', WHISPER_CPP_URL_HF if _os=='Windows' else WHISPER_CPP_LINUX_URL_HF, callback=self._process_callback)


    def _exec(self):
        cpp_path=f'{ROOT_DIR}/whisper-cpp/whisper-cli'#whisper-cli.exe | whisper-cli
        if _os=='Windows':
            cpp_path+='.exe'
        Path_cpp=Path(cpp_path)
        if _os=='Darwin' and not Path_cpp.exists():
            raise RuntimeError(f'Please install whisper.cpp and place the whisper-cli file in the {ROOT_DIR}/whisper-cpp directory')
        if not Path_cpp.is_file():
            self._download_cli()

        if not Path(f'{ROOT_DIR}/models/{self.model_name}').is_file():
            from videotrans.util import help_down
            url=WHISPERCPP_MODEL_URL_HF.replace('{}',self.model_name)
            help_down.down_file_from_hf(
                f"{ROOT_DIR}/models",
                [url],
                self._process_callback)

        device = whisper_device(is_cuda=self.is_cuda)

        txt_file = ROOT_DIR + '/pyvideotrans_cpp.txt'

        n_threads = str(max(min(4, CPU_NUMS - 1), 1))
        cmd = [
            cpp_path,
            "-t" if device.startswith("cuda") else "-p",
            n_threads,
            "-f",
            self.audio_file,
            "-osrt",
            "-nth",str(float(settings.get('no_speech_threshold', 0.6))),
            "-pp",
            "-np"
        ]
        if device.startswith("cpu"):
            cmd.append("-ng")
        _lang=self.detect_language.split('-')[0]
        cmd += ["-l", _lang]
        prompt = settings.get(f'initial_prompt_{self.detect_language.replace("-","_")}')
        if prompt:
            cmd += ['--prompt', prompt]
        if _lang.lower() !='auto':
            # 最多2倍设定字幕字符长度，防止过长
            _ml=2*int(settings.get('cjk_len', 15) if _lang in constants.CJK_LANG else settings.get('other_len', 60))
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
                creationflags=subprocess.CREATE_NO_WINDOW if _os == 'Windows' else 0,
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