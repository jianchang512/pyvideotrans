import multiprocessing
import os
import re
import time
from pathlib import Path

import requests
from faster_whisper import WhisperModel
from huggingface_hub.errors import LocalEntryNotFoundError, HfHubHTTPError

from videotrans.util.tools import cleartext


def run(raws, err, detect, *, model_name, is_cuda, detect_language, audio_file,
        q: multiprocessing.Queue, ROOT_DIR, TEMP_DIR, settings, defaulelang, proxy=None):
    os.chdir(ROOT_DIR)
    down_root = ROOT_DIR + "/models"
    settings['whisper_threads'] = int(float(settings.get('whisper_threads', 1)))

    def write_log(jsondata):
        try:
            q.put_nowait(jsondata)
        except:
            pass

    try:
        os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = "1200"
        if defaulelang == 'zh' and not Path(ROOT_DIR+"/huggingface.lock").exists():
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            os.environ["HF_HUB_DISABLE_XET"] = "1"
        else:
            os.environ['HF_ENDPOINT'] = 'https://huggingface.co'
            if os.environ.get("HF_HUB_DISABLE_XET"):
                os.environ.pop("HF_HUB_DISABLE_XET")
        if proxy:
            os.environ['HTTPS_PROXY']=proxy
            os.environ['HTTP_PROXY']=proxy
        else:
            if os.environ.get('HTTPS_PROXY'):
                os.environ.pop('HTTPS_PROXY')
            if os.environ.get('HTTP_PROXY'):
                os.environ.pop('HTTP_PROXY')
        print(f'{proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTPS_PROXY")},{os.environ.get("HF_ENDPOINT")}')
        msg = f'[{model_name}]若不存在将自动下载到 models 目录内' if defaulelang == 'zh' else f'If [{model_name}] not exists, download model from huggingface'
        write_log({"text": msg, "type": "logs"})
        if model_name.startswith('distil-'):
            com_type = "default"
        elif is_cuda:
            com_type = settings['cuda_com_type']
        else:
            com_type = settings['cuda_com_type']
        try:
            model = WhisperModel(
                model_name,
                device="cuda" if is_cuda else "cpu",
                compute_type=com_type,
                download_root=down_root
            )
        except Exception as e:
            import traceback
            error=traceback.format_exc()
            if isinstance(e,(requests.exceptions.ChunkedEncodingError,HfHubHTTPError)) or "Unable to open file 'model.bin'" in error or  "CAS service error" in error:
                if 'hf-mirror.com' in os.environ.get('HF_ENDPOINT',''):
                    msg='从国内镜像站下载模型失败，如果你能科学上网，请尝试从huggingface.co下载，具体方法请查看 https://pvt9.com/819  \n'
                else:
                    msg=f'下载模型失败了请确认网络稳定并能连接 huggingface.co \n' if defaulelang == 'zh' else f'Download model failed, please confirm network stable and try again.'
                err['msg']=f'{msg}:{error}'
            elif "CUBLAS_STATUS_NOT_SUPPORTED" in error:
                err['msg'] = f"数据类型不兼容：请打开菜单--工具--高级选项--faster/openai语音识别调整--CUDA数据类型--选择 float16，保存后重试:{error}" if defaulelang == 'zh' else f'Incompatible data type: Please open the menu - Tools - Advanced options - Faster/OpenAI speech recognition adjustment - CUDA data type - select float16, save and try again:{error}'
            elif "cudaErrorNoKernelImageForDevice" in error:
                err['msg'] = f"pytorch和cuda版本不兼容，请更新显卡驱动后，安装或重装CUDA12.x及cuDNN9.x:{error}" if defaulelang == 'zh' else f'Pytorch and cuda versions are incompatible. Please update the graphics card driver and install or reinstall CUDA12.x and cuDNN9.x:{error}'
            else:
                err['msg'] = error
            return

        write_log({"text": model_name + " Loaded", "type": "logs"})
        prompt = settings.get(f'initial_prompt_{detect_language}') if detect_language != 'auto' else None
        segments, info = model.transcribe(
            audio_file,
            beam_size=int(settings['beam_size']),
            best_of=int(settings['best_of']),
            condition_on_previous_text=bool(settings['condition_on_previous_text']),
            vad_filter=bool(settings['vad']),
            vad_parameters=dict(
                threshold=float(settings['threshold']),
                min_speech_duration_ms=int(settings['min_speech_duration_ms']),
                max_speech_duration_s=float(settings['max_speech_duration_s']) if float(
                    settings['max_speech_duration_s']) > 0 else float('inf'),
                min_silence_duration_ms=int(settings['min_silence_duration_ms']),
                speech_pad_ms=int(settings['speech_pad_ms'])
            ),
            word_timestamps=True,
            language=detect_language.split('-')[0] if detect_language != 'auto' else None,
            initial_prompt=prompt if prompt else None
        )
        if detect_language == 'auto' and info.language != detect['langcode']:
            detect['langcode'] = 'zh-cn' if info.language[:2] == 'zh' else info.language
        nums = 0
        for segment in segments:
            nums += 1
            if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                return
            new_seg = []
            for idx, word in enumerate(segment.words):
                new_seg.append({"start": word.start, "end": word.end, "word": word.word})
            text = cleartext(segment.text, remove_start_end=False)
            raws.append({"words": new_seg, "text": text})

            q.put_nowait({"text": f'{text}\n', "type": "subtitle"})
            q.put_nowait({"text": f' {"字幕" if defaulelang == "zh" else "Subtitles"} {len(raws) + 1} ', "type": "logs"})
    except (LookupError, ValueError, AttributeError, ArithmeticError) as e:
        err['msg'] = f'{e}'
        if detect_language == 'auto':
            err['msg'] += 'Failed to detect language, please set the voice language'
    except BaseException as e:
        import traceback
        err['msg'] = '_process:' + traceback.format_exc()
    finally:
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
        time.sleep(2)
