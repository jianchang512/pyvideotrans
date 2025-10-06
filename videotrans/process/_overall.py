import multiprocessing
import os
import time
from pathlib import Path


# 该文件运行在独立进程


def run(raws, err, detect, *, model_name, is_cuda, detect_language, audio_file,
        q: multiprocessing.Queue,proxy=None):
    from videotrans.configure import config
    from videotrans.process._iscache import check_cache_and_setproxy, down_model_err
    os.chdir(config.ROOT_DIR)
    has_cache = False
    try:
        has_cache = check_cache_and_setproxy(model_name, config.ROOT_DIR, proxy)
    except Exception as e:
        pass
    if has_cache:
        msg = f"模型 {model_name} 已存在，直接使用" if config.defaulelang == 'zh' else f'Model {model_name} already exists, use it directly'
    else:
        msg = f"模型 {model_name} 不存在，将自动下载 {os.environ.get('HF_ENDPOINT')}" if config.defaulelang == 'zh' else f'Model {model_name} does not exist and will be automatically downloaded'


    def write_log(jsondata):
        try:
            q.put_nowait(jsondata)
        except Exception:
            pass

    from faster_whisper import WhisperModel
    from videotrans.util.tools import cleartext
    down_root = config.ROOT_DIR + "/models"
    try:
        write_log({"text": msg, "type": "logs"})
        if model_name.startswith('distil-'):
            com_type = "default"
        else:
            com_type = config.settings.get('cuda_com_type','default')

        try:
            model = WhisperModel(
                model_name,
                device="cuda" if is_cuda else "cpu",
                compute_type=com_type,
                download_root=down_root
            )
        except Exception as e:
            err['msg'] = down_model_err(e, model_name, down_root, config.defaulelang)
            return

        write_log({"text": model_name + " Loaded", "type": "logs"})
        prompt = config.settings.get(f'initial_prompt_{detect_language}') if detect_language != 'auto' else None
        segments, info = model.transcribe(
            audio_file,
            beam_size=int(config.settings.get('beam_size',5)),
            best_of=int(config.settings.get('best_of',5)),
            condition_on_previous_text=bool(config.settings.get('condition_on_previous_text',False)),
            vad_filter=bool(config.settings.get('vad',False)),
            vad_parameters=dict(
                threshold=float(config.settings.get('threshold',0.45)),
                min_speech_duration_ms=int(config.settings.get('min_speech_duration_ms',0)),
                max_speech_duration_s=float(config.settings.get('max_speech_duration_s',5)),
                min_silence_duration_ms=int(config.settings.get('min_silence_duration_ms',140)),
                speech_pad_ms=int(config.settings.get('speech_pad_ms',0))
            ),
            word_timestamps=True,
            language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
            initial_prompt=prompt if prompt else None
        )
        if detect_language == 'auto' and info.language != detect['langcode']:
            detect['langcode'] = 'zh-cn' if info.language[:2] == 'zh' else info.language
        nums = 0
        for segment in segments:
            nums += 1
            if not Path(config.TEMP_DIR + f'/{os.getpid()}.lock').exists():
                return
            new_seg = []
            for idx, word in enumerate(segment.words):
                new_seg.append({"start": word.start, "end": word.end, "word": word.word})
            text = cleartext(segment.text, remove_start_end=False)
            raws.append({"words": new_seg, "text": text})

            q.put_nowait({"text": f'{text}\n', "type": "subtitle"})
            q.put_nowait({"text": f' {config.tr("Subtitles")}  {len(raws) + 1} ', "type": "logs"})
    except Exception:
        import traceback
        err['msg'] = traceback.format_exc()
    finally:
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        time.sleep(1)
