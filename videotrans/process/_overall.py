import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
import multiprocessing
import shutil
import time
from pathlib import Path



# 该文件运行在独立进程


def run(raws, err, detect, *, model_name, is_cuda, detect_language, audio_file,
        q: multiprocessing.Queue,proxy=None,TEMP_DIR=None,settings=None,defaulelang='zh',split_type=0,whisper_type=0):
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["OMP_NUM_THREADS"] = "1"
    import torch
    from videotrans.configure import config
    from videotrans.process._iscache import check_cache_and_setproxy, down_model_err,_MODELS
    from videotrans.util.tools import cleartext
    os.chdir(config.ROOT_DIR)
    has_cache = False
    


    def write_log(jsondata):
        try:
            q.put_nowait(jsondata)
        except Exception:
            pass
    
    down_root = config.ROOT_DIR + "/models"
    model=None
    batched_model=None
    
    prompt = settings.get(f'initial_prompt_{detect_language}') if detect_language != 'auto' else None
    if whisper_type==1:
        import whisper
        if not Path(f'{down_root}/{model_name}.pt').exists():
            msg = f"模型 {model_name} 不存在，将自动下载 " if defaulelang == 'zh' else f'Model {model_name} does not exist and will be automatically downloaded'
            write_log({"text": msg, "type": "logs"})
        try:
            model = whisper.load_model(
                model_name,
                device="cuda" if is_cuda else "cpu",
                download_root=down_root
            )
            result = model.transcribe(
                    audio_file,
                    language=detect_language.split('-')[0] if detect_language != 'auto' else None,
                    word_timestamps=True,
                    initial_prompt=prompt if prompt else None,
                    condition_on_previous_text=config.settings.get('condition_on_previous_text',False)
                )
            nums = 0

            for segment in result['segments']:
                nums += 1
                if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                    return
                new_seg = []
                for idx, word in enumerate(segment['words']):
                    new_seg.append({"start": word['start'], "end": word['end'], "word": word['word']})
                text = cleartext(segment['text'], remove_start_end=False)
                raws.append({"words": new_seg, "text": text})

                write_log({"text": f'{text}\n', "type": "subtitle"})
                write_log({"text": f' Subtitles {len(raws) + 1} ', "type": "logs"})
        except Exception as e:
            import traceback
            err['msg'] = traceback.format_exc()
    else:
        try:
            has_cache = check_cache_and_setproxy(model_name, config.ROOT_DIR, proxy)
        except Exception as e:
            pass
            
        if not has_cache:
            write_log({"text": f"模型 {model_name} 不存在，将自动下载 {os.environ.get('HF_ENDPOINT')}" if defaulelang == 'zh' else f'Model {model_name} does not exist and will be automatically downloaded', "type": "logs"})
        
        from faster_whisper import WhisperModel,BatchedInferencePipeline
        if model_name not in _MODELS:
            split_type=0
        
        try:
            if model_name.startswith('distil-'):
                com_type = "default"
            else:
                com_type = settings.get('cuda_com_type','default')

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
            
            # 批量或均等分割
            if split_type==1 or settings.get('faster_batch'):
                chunk_length=int(float(settings.get('max_speech_duration_s',6)))
                chunk_length=max(chunk_length,1)
                batched_model = BatchedInferencePipeline(model=model)
                segments, info=batched_model.transcribe(audio_file,
                    batch_size=16,
                    beam_size=int(settings.get('beam_size',5)),
                    best_of=int(settings.get('best_of',5)),
                    condition_on_previous_text=bool(settings.get('condition_on_previous_text',False)),
                    vad_filter=bool(settings.get('vad',False)),
                    vad_parameters=dict(
                        threshold=float(settings.get('threshold',0.45)),
                        min_speech_duration_ms=int(settings.get('min_speech_duration_ms',0)),
                        min_silence_duration_ms=int(settings.get('min_silence_duration_ms',140)),
                        speech_pad_ms=int(settings.get('speech_pad_ms',0))
                    ),
                    chunk_length=chunk_length,
                    word_timestamps=True,
                    language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
                    initial_prompt=prompt if prompt else None
                )
            else:
                segments, info = model.transcribe(
                    audio_file,
                    beam_size=int(settings.get('beam_size',5)),
                    best_of=int(settings.get('best_of',5)),
                    condition_on_previous_text=bool(settings.get('condition_on_previous_text',False)),
                    vad_filter=bool(settings.get('vad',False)),
                    vad_parameters=dict(
                        threshold=float(settings.get('threshold',0.45)),
                        min_speech_duration_ms=int(settings.get('min_speech_duration_ms',0)),
                        max_speech_duration_s=float(settings.get('max_speech_duration_s',5)),
                        min_silence_duration_ms=int(settings.get('min_silence_duration_ms',140)),
                        speech_pad_ms=int(settings.get('speech_pad_ms',0))
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
                if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                    return
                new_seg = []
                for idx, word in enumerate(segment.words):
                    new_seg.append({"start": word.start, "end": word.end, "word": word.word})
                text = cleartext(segment.text, remove_start_end=False)
                raws.append({"words": new_seg, "text": text})

                write_log({"text": f'{text}\n', "type": "subtitle"})
                write_log({"text": f' Subtitles {len(raws) + 1} ', "type": "logs"})
        except BaseException as e:
            import traceback
            err['msg'] = traceback.format_exc()

    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        import gc
        gc.collect()
        del model
        del batched_model
    except Exception:
        pass
    time.sleep(1)
