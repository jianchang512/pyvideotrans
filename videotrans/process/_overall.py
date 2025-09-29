import multiprocessing
import os
import time
from pathlib import Path


# 该文件运行在独立进程
def run(raws, err, detect, *, model_name, is_cuda, detect_language, audio_file,
        q: multiprocessing.Queue, ROOT_DIR, TEMP_DIR, settings, defaulelang, proxy=None):
    os.chdir(ROOT_DIR)
    from videotrans.process._iscache import check_cache_and_setproxy, down_model_err
    has_cache = False
    try:
        has_cache = check_cache_and_setproxy(model_name, ROOT_DIR, proxy, defaulelang)
    except Exception as e:
        pass
    if has_cache:
        msg = f"模型 {model_name} 已存在，直接使用" if defaulelang == 'zh' else f'Model {model_name} already exists, use it directly'
    else:
        msg = f"模型 {model_name} 不存在，将自动下载 {os.environ.get('HF_ENDPOINT')}" if defaulelang == 'zh' else f'Model {model_name} does not exist and will be automatically downloaded'

    settings['whisper_threads'] = int(float(settings.get('whisper_threads', 1)))

    def write_log(jsondata):
        try:
            q.put_nowait(jsondata)
        except:
            pass

    from faster_whisper import WhisperModel
    from videotrans.util.tools import cleartext
    down_root = ROOT_DIR + "/models"
    try:
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
            err['msg'] = down_model_err(e, model_name, down_root, defaulelang)
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
