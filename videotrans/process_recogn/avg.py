import json
import os
import re
from pathlib import Path

import torch
import zhconv
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from videotrans.util.tools import ms_to_time_string, match_target_amplitude, vail_file


def run(raws,err,*,cache_folder,model_name,is_cuda,detect_language,audio_file,q,settings,
TEMP_DIR,ROOT_DIR,defaulelang):
    os.chdir(ROOT_DIR)
    def write_log(jsondata):
        try:
            q.put_nowait(jsondata)
        except:
            pass

    tmp_path = Path(f'{cache_folder}/{Path(audio_file).name}_tmp')
    tmp_path.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_path.as_posix()

    nonslient_file = f'{tmp_path}/detected_voice.json'
    normalized_sound = AudioSegment.from_wav(audio_file)
    if vail_file(nonslient_file):
        nonsilent_data = json.load(open(nonslient_file, 'r'))
    else:
        nonsilent_data = _shorten_voice_old(normalized_sound,settings)
        json.dump(nonsilent_data, open(nonslient_file, 'w'))

    total_length = len(nonsilent_data)

    if model_name.startswith('distil-'):
        com_type = "default"
    elif is_cuda:
        com_type = settings['cuda_com_type']
    else:
        com_type = settings['cuda_com_type']
    # 如果不存在 / ，则是本地模型
    local_res = True if model_name.find('/') == -1 else False
    down_root = ROOT_DIR + "/models"
    if not local_res:
        if not os.path.isdir(down_root + '/models--' + model_name.replace('/', '--')):
            msg = '下载模型中，用时可能较久' if defaulelang == 'zh' else 'Download model from huggingface'
        else:
            msg = '加载或下载模型中，用时可能较久' if defaulelang == 'zh' else 'Load model from local or download model from huggingface'
        write_log({"text": msg, "type": "logs"})
    try:
        model = WhisperModel(
            model_name,
            device="cuda" if is_cuda else "cpu",
            compute_type=com_type,
            download_root=down_root,
            local_files_only=local_res)
    except Exception as e:
        if re.match(r'backend do not support',str(e),re.I):
            model = WhisperModel(
            model_name,
            device="cuda" if is_cuda else "cpu",
            compute_type='default',
            download_root=down_root,
            local_files_only=local_res)
        else:
            err['msg']=str(e)
            return

    prompt = settings.get(f'initial_prompt_{detect_language}')
    try:
        for i, duration in enumerate(nonsilent_data):
            if not Path(TEMP_DIR+f'/{os.getpid()}.lock'):
                return
            start_time, end_time, buffered = duration
            chunk_filename = tmp_path + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
            audio_chunk = normalized_sound[start_time:end_time]
            audio_chunk.export(chunk_filename, format="wav")

            text = ""
            segments, _ = model.transcribe(chunk_filename,
                                                beam_size=settings['beam_size'],
                                                best_of=settings['best_of'],
                                                condition_on_previous_text=settings[
                                                    'condition_on_previous_text'],
                                                temperature=0.0 if settings['temperature'] == 0 else [0.0, 0.2,
                                                                                                             0.4,
                                                                                                             0.6, 0.8,
                                                                                                             1.0],
                                                vad_filter=False,
                                                language=detect_language[:2],
                                                initial_prompt=prompt if prompt else None
                                                )

            for t in segments:
                text += t.text + " "

            text = re.sub(r'&#\d+;', '', text.replace('&#39;', "'")).strip()

            if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text):
                continue

            if detect_language[:2] == 'zh' and settings['zh_hant_s']:
                text = zhconv.convert(text, 'zh-hans')

            start = ms_to_time_string(ms=start_time)
            end = ms_to_time_string(ms=end_time)

            srt_line = {
                "line": len(raws) + 1,
                "time": f"{start} --> {end}",
                "text": text
            }
            raws.append(srt_line)
            write_log({"text": f"{srt_line['line']}\n{srt_line['time']}\n{srt_line['text']}\n\n" , "type": "subtitle"})
            write_log({"text":f" {srt_line['line']}/{total_length}", "type": "logs"})
    except Exception as e:
        err['msg']=str(e)
    except BaseException as e:
        err['msg']=str(e)
    finally:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass

# split audio by silence
def _shorten_voice_old( normalized_sound,settings):
    normalized_sound = match_target_amplitude(normalized_sound, -20.0)
    max_interval = int(settings['interval_split']) * 1000
    nonsilent_data = []
    audio_chunks = detect_nonsilent(
        normalized_sound,
        min_silence_len=int(settings['voice_silence']),
        silence_thresh=-20 - 25)
    for i, chunk in enumerate(audio_chunks):
        start_time, end_time = chunk
        n = 0
        while end_time - start_time >= max_interval:
            n += 1
            new_end = start_time + max_interval
            new_start = start_time
            nonsilent_data.append((new_start, new_end, True))
            start_time += max_interval
        nonsilent_data.append((start_time, end_time, False))
    return nonsilent_data
