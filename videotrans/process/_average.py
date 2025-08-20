import json
import os
import re
import tempfile
import time
from pathlib import Path

import zhconv
from faster_whisper import WhisperModel
from huggingface_hub.errors import LocalEntryNotFoundError
from pydub import AudioSegment

from videotrans.util.tools import ms_to_time_string, vail_file, cleartext


def run(raws, err, detect, *, model_name, is_cuda, detect_language, audio_file, q, settings,
        TEMP_DIR, ROOT_DIR, defaulelang, proxy=None):
    os.chdir(ROOT_DIR)

    def write_log(jsondata):
        try:
            q.put_nowait(jsondata)
        except:
            pass

    tmp_path = Path(tempfile.gettempdir() + f'/recogn_{time.time()}')
    tmp_path.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_path.as_posix()

    nonslient_file = f'{tmp_path}/detected_voice.json'
    normalized_sound = AudioSegment.from_wav(audio_file)
    if vail_file(nonslient_file):
        nonsilent_data = json.load(open(nonslient_file, 'r'))
    else:
        nonsilent_data = _shorten_voice_old(normalized_sound, settings)
        with open(nonslient_file, 'w') as f:
            f.write(json.dumps(nonsilent_data))

    total_length = len(nonsilent_data)

    if model_name.startswith('distil-'):
        com_type = "default"
    elif is_cuda:
        com_type = settings['cuda_com_type']
    else:
        com_type = settings['cuda_com_type']

    down_root = ROOT_DIR + "/models"
    msg = f'[{model_name}]若不存在将从 hf-mirror.com 下载到 models 目录内' if defaulelang == 'zh' else f'If [{model_name}] not exists, download model from huggingface'
    write_log({"text": msg, "type": "logs"})

    try:
        model = WhisperModel(
            model_name,
            device="cuda" if is_cuda else "cpu",
            compute_type=com_type,
            download_root=down_root)
    except LocalEntryNotFoundError:
        err['msg'] = '下载模型失败了请确认网络稳定后重试，如果已使用代理，请尝试关闭。 访问网址  https://pvt9.com/820  可查看详细详细解决方案' if defaulelang == 'zh' else 'Download model failed, please confirm network stable and try again. Visit https://pvt9.com/820 for more detail.'
        return
    except Exception as e:
        error = str(e)
        if "CUBLAS_STATUS_NOT_SUPPORTED" in error:
            err['msg'] = "数据类型不兼容：请打开菜单--工具--高级选项--faster/openai语音识别调整--CUDA数据类型--选择 float16，保存后重试" if defaulelang == 'zh' else 'Incompatible data type: Please open the menu - Tools - Advanced options - Faster/OpenAI speech recognition adjustment - CUDA data type - select float16, save and try again'
        elif "cudaErrorNoKernelImageForDevice" in error:
            err['msg'] = "pytorch和cuda版本不兼容，请更新显卡驱动后，安装或重装CUDA12.x及cuDNN9.x" if defaulelang == 'zh' else 'Pytorch and cuda versions are incompatible. Please update the graphics card driver and install or reinstall CUDA12.x and cuDNN9.x'
        else:
            err['msg'] = str(e)
        return

    write_log({"text": model_name + " Loaded", "type": "logs"})
    prompt = settings.get(f'initial_prompt_{detect_language}') if detect_language != 'auto' else None
    try:
        last_detect = detect_language
        for i, duration in enumerate(nonsilent_data):
            if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                return
            start_time, end_time, buffered = duration
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            audio_chunk = normalized_sound[start_time:end_time]
            audio_chunk.export(chunk_filename, format="wav")

            text = ""
            segments, info = model.transcribe(chunk_filename,
                                              beam_size=settings['beam_size'],
                                              best_of=settings['best_of'],
                                              condition_on_previous_text=settings[
                                                  'condition_on_previous_text'],
                                              vad_filter=False,
                                              language=detect_language.split('-')[
                                                  0] if detect_language != 'auto' else None,
                                              initial_prompt=prompt if prompt else None
                                              )
            if last_detect == 'auto':
                detect['langcode'] = 'zh-cn' if info.language[:2] == 'zh' else info.language
                last_detect = detect['langcode']
            for t in segments:
                text += t.text + " "

            text = re.sub(r'&#\d+;', '', text.replace('&#39;', "'")).strip()

            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                continue

            if detect['langcode'][:2] == 'zh' and settings['zh_hant_s']:
                text = zhconv.convert(text, 'zh-hans')

            start = ms_to_time_string(ms=start_time)
            end = ms_to_time_string(ms=end_time)
            text = cleartext(text)
            srt_line = {
                "line": len(raws) + 1,
                "time": f"{start} --> {end}",
                "text": text,
                "start_time": start_time,
                "end_time": end_time,
                "startraw": start,
                "endraw": end
            }
            raws.append(srt_line)
            write_log({"text": f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n", "type": "subtitle"})
            write_log({"text": f" {srt_line['line']}/{total_length}", "type": "logs"})
    except (LookupError, ValueError, AttributeError, ArithmeticError) as e:
        err['msg'] = f'{e}'
        if detect_language == 'auto':
            err['msg'] += 'Failed to detect language, please set the voice language'
    except BaseException as e:
        err['msg'] = str(e)
    finally:
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass


# split audio by silence
def _shorten_voice_old(normalized_sound, settings):
    max_interval = int(float(settings.get('interval_split', 1))) * 1000
    nonsilent_data = []
    import math
    maxlen = math.ceil(len(normalized_sound) / max_interval)
    for i in range(maxlen):
        if i < maxlen - 1:
            end_time = i * max_interval + max_interval
            start_time = i * max_interval
        else:
            end_time = len(normalized_sound)
            start_time = i * max_interval
        nonsilent_data.append((start_time, end_time, False))
    return nonsilent_data
