# ToDo 将 whisper.cpp 移动到此
import json
import re
import shutil
import subprocess,platform
from dataclasses import dataclass
from pathlib import Path

from videotrans.configure import constants
from videotrans.configure._paths import ROOT_DIR
from videotrans.configure.config import tr, settings, logger, CPU_NUMS, app_cfg
from videotrans.configure.constants import WHISPER_CPP_URL_HF, WHISPER_CPP_LINUX_URL_HF, WHISPERCPP_MODEL_URL_HF, \
    WHISPER_CPP_VULKAN_URL_HF
from videotrans.configure.excepts import SpeechToTextError, FallbackError
from videotrans.process._stt_utils import _resegment
from videotrans.recognition._base import BaseRecogn
from videotrans.util._srt_parse import get_subtitle_from_srt
from videotrans.util.gpus import whisper_device
from videotrans.util.help_down import down_zip


_os=platform.system()

@dataclass(repr=False)
class CPPRecogn(BaseRecogn):

    def _download_cli(self,device=None):
        self.signal(text=f'Download whisper-cli')
        if _os=='Linux':
            return down_zip(f'{ROOT_DIR}', WHISPER_CPP_LINUX_URL_HF, callback=self._process_callback)
        # windows 上
        return  down_zip(f'{ROOT_DIR}', WHISPER_CPP_VULKAN_URL_HF if device=='vulkan' else WHISPER_CPP_URL_HF, callback=self._process_callback)

    def _run(self,device,_sub,cpp_path,_lang):
        Path_cpp=Path(cpp_path)
        if _os=='Darwin' and not Path_cpp.exists():
            raise RuntimeError(f'Please install whisper.cpp and place the whisper-cli file in the {ROOT_DIR}/whisper-cpp directory')
        if not Path_cpp.is_file():
            self._download_cli(device)
        if not Path(f'{ROOT_DIR}/models/{self.model_name}').is_file():
            from videotrans.util import help_down
            url=WHISPERCPP_MODEL_URL_HF.replace('{}',self.model_name)
            help_down.down_file_from_hf(
                f"{ROOT_DIR}/models",
                [url],
                self._process_callback)

        txt_file = ROOT_DIR + '/pyvideotrans_cpp.txt'
        cmd = [
            cpp_path,
            # "-t" if device.startswith("cuda") else "-p",
            # n_threads,
            "-f",
            self.audio_file,
            "-ojf",
            "-nth",str(float(settings.get('no_speech_threshold', 0.6))),
            "-pp",
            "-np",
            "-bs",str(settings.get('beam_size', 5)),
            "-bo",str(settings.get('best_of', 5)),
        ]
        if device.startswith("cpu"):
            cmd.append("-ng")

        cmd += ["-l", _lang]
        prompt = settings.get(f'initial_prompt_{self.detect_language.replace("-","_")}')
        if prompt:
            cmd += ['--prompt', prompt]

        if txt_file and Path(txt_file).exists():
            cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))

        cmd.extend(['-m', f'{ROOT_DIR}/models/{self.model_name}', '-of', _sub])
        logger.debug(f'Whisper.cpp: {cmd=}')
        self.signal(text=tr("Transcription in progress, please wait"))
        log_file_path = f"{self.cache_folder}/whisper.cpp.log"

        all_logs = []

        # 实时流模式
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

        # 一边写日志，一边解析进度
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()

                all_logs.append(line)
                # whisper.cpp 输出进度格式 "whisper_full_with_state: progress =  50%"
                match = re.search(r'progress\s*=\s*(\d+)%', line)
                if match:
                    percent = match.group(1)
                    self.signal(text=f"{tr('Transcription in progress, please wait')}: {percent}%")

        #等待进程结束并获取状态码
        return_code = process.wait()

        # WINDOWS 可能vulkan加速失败，而cpu也无法正常运行，需重新下载 cuda+cpu版
        if return_code != 0 and not all_logs and device=='vulkan' and _os=='Windows' and Path(f'{ROOT_DIR}/whisper-cpp/ggml-vulkan.dll').exists():
            raise FallbackError(tr("Vulkan acceleration failed. Please try deleting all files into that folder before re-executing",ROOT_DIR,WHISPER_CPP_URL_HF))

        if not Path(f'{_sub}.json').exists():
            raise SpeechToTextError("".join(all_logs))


    def _exec(self):
        cpp_path=f'{ROOT_DIR}/whisper-cpp/whisper-cli'#whisper-cli.exe | whisper-cli
        if _os=='Windows':
            cpp_path+='.exe'

        # window上只要没有cuda，始终尝试 vulkan
        device="vulkan" if _os=='Windows' and app_cfg.NVIDIA_CUDA_NUMS<1 and app_cfg.VULKAN_LIST else whisper_device(is_cuda=self.is_cuda)

        # 当windows使用vulkan失败时，cpu也可能执行失败，此时用户需重新下载cuda版本在cpu运行
        # if device=='vulkan' and not Path(f'{ROOT_DIR}/whisper-cpp/ggml-vulkan.dll').exists():
        #     device="cpu"
        _sub=f'{self.cache_folder}/cpp_srt'
        _lang=self.detect_language.split('-')[0]

        try:
            self._run(device,_sub,cpp_path,_lang)
        except FallbackError:
            logger.error(f'Windows上使用vulkan加速失败，回退cpu')
            shutil.rmtree(f'{ROOT_DIR}/whisper-cpp',ignore_errors=True)
            self._run("cpu",_sub,cpp_path,_lang)

        try:
            texts=[]
            d=json.loads(Path(_sub+".json").read_text(encoding="utf-8"))
            for segment in d['transcription']:
                tmp={
                    "text": segment["text"],
                    "start": segment["offsets"]["from"]/1000,
                    "end": segment["offsets"]["to"]/1000,
                    "words": []
                }
                for it in segment['tokens']:
                    if it['text'].startswith("[") and it['text'].endswith(']'):
                        continue
                    tmp['words'].append({"word":it['text'],"start":it['offsets']['from']/1000,"end":it['offsets']['to']/1000})
                texts.append(tmp)

            min_speech = max(int(float(settings.get('min_speech_duration_ms', 1000))), 200)
            # 最长片段不得大于25s,并且不得小于 _min_speech
            max_speech = min(int(float(settings.get('max_speech_duration_s', 6)) * 1000), 25000)
            if max_speech<=min_speech:
                max_speech=min_speech+1000
            return _resegment(texts, _lang, max_speech, min_speech, logs_file=None)
        except Exception as e:
            raise SpeechToTextError(str(e))