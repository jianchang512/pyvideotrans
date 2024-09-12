import multiprocessing
import os
import re
import time
from pathlib import Path

import torch
import zhconv
from faster_whisper import WhisperModel

from videotrans.util.tools import ms_to_time_string


def run(raws, err, *, model_name, is_cuda, detect_language, audio_file, maxlen, flag, join_word_flag,
        q: multiprocessing.Queue, ROOT_DIR, TEMP_DIR, settings, defaulelang):
    os.chdir(ROOT_DIR)
    jianfan = True if detect_language[:2] == 'zh' and settings['zh_hant_s'] else False
    down_root = ROOT_DIR + "/models"

    def write_log(jsondata):
        try:
            q.put_nowait(jsondata)
        except:
            pass

    def append_raws(tmp):
        try:
            if jianfan:
                tmp['text'] = zhconv.convert(tmp['text'], 'zh-hans')
            q.put_nowait({"text": f'{tmp["line"]}\n{tmp["time"]}\n{tmp["text"]}\n\n', "type": "subtitle"})
            q.put_nowait({"text": f' {"字幕" if defaulelang == "zh" else "Subtitles"} {len(raws) + 1} ', "type": "logs"})
        except:
            pass
        raws.append(tmp)

    try:
        # 不存在 / ，是普通本地已有模型，直接本地加载，否则在线下载
        local_res = True if model_name.find('/') == -1 else False
        if not local_res:
            if not os.path.isdir(down_root + '/models--' + model_name.replace('/', '--')):
                msg = '下载模型中，用时可能较久' if defaulelang == 'zh' else 'Download model from huggingface'
            else:
                msg = '加载或下载模型中，用时可能较久' if defaulelang == 'zh' else 'Load model from local or download model from huggingface'
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
                download_root=down_root,
                num_workers=settings['whisper_worker'],
                cpu_threads=os.cpu_count() if int(settings['whisper_threads']) < 1 else int(
                    settings['whisper_threads']),
                local_files_only=local_res

            )
        except Exception as e:
            if re.match(r'backend do not support', str(e), re.I):
                # 如果所选数据类型不支持，则使用默认
                model = WhisperModel(
                    model_name,
                    device="cuda" if is_cuda else "cpu",
                    compute_type="default",
                    download_root=down_root,
                    num_workers=settings['whisper_worker'],
                    cpu_threads=os.cpu_count() if int(settings['whisper_threads']) < 1 else int(
                        settings['whisper_threads']),
                    local_files_only=local_res
                )
            else:
                err['msg'] = str(e)
                return

        prompt = settings.get(f'initial_prompt_{detect_language}')
        segments, nfo = model.transcribe(
            audio_file,
            beam_size=settings['beam_size'],
            best_of=settings['best_of'],
            condition_on_previous_text=settings['condition_on_previous_text'],
            temperature=0.0 if int(settings['temperature']) == 0 else [0.0, 0.2, 0.4, 0.6,
                                                                       0.8, 1.0],
            vad_filter=bool(settings['vad']),
            vad_parameters=dict(
                min_silence_duration_ms=settings['overall_silence'],
                max_speech_duration_s=float('inf'),
                threshold=settings['overall_threshold'],
                speech_pad_ms=settings['overall_speech_pad_ms']
            ),
            word_timestamps=True,
            language=detect_language[:2],
            initial_prompt=prompt if prompt else None
        )
        for segment in segments:
            if not Path(TEMP_DIR + f'/{os.getpid()}.lock'):
                return
            if len(segment.words) < 1:
                continue
            len_text = len(segment.text.strip())
            # 如果小于 maxlen*1.5 或 小于 5s，则为正常语句
            if len_text <= maxlen * 1.2 or (segment.words[-1].end - segment.words[0].start) < 3:
                tmp = {
                    "line": len(raws) + 1,
                    "start_time": int(segment.words[0].start * 1000),
                    "end_time": int(segment.words[-1].end * 1000),
                    "text": segment.text.strip(),
                }
                tmp[
                    'time'] = f'{ms_to_time_string(ms=tmp["start_time"])} --> {ms_to_time_string(ms=tmp["end_time"])}'
                append_raws(tmp)
                continue

            # 寻找最靠近中间的拆分点
            split_idx = 0
            # words组数量
            max_index = len(segment.words) - 1
            # 字符组个数中间值
            middel_idx = int((max_index + 1) / 2)
            # 拆分点距离中间值距离绝对值
            abs_middel_idx = 99999
            # 所有的标点切分点索引数组
            split_idx_list = []
            for idx, word in enumerate(segment.words):
                if word.word[0] in flag:
                    if abs(middel_idx - idx) < abs_middel_idx:
                        split_idx = idx - 1 if idx > 0 else idx
                        split_idx_list.append(split_idx)
                        abs_middel_idx = abs(middel_idx - idx)
                elif word.word[-1] in flag:
                    if abs(middel_idx - idx) < abs_middel_idx:
                        split_idx = idx
                        split_idx_list.append(split_idx)
                        abs_middel_idx = abs(middel_idx - idx)
            # 没有合适的切分点
            if split_idx == 0:
                if len_text <= maxlen * 1.3:
                    tmp = {
                        "line": len(raws) + 1,
                        "start_time": int(segment.words[0].start * 1000),
                        "end_time": int(segment.words[-1].end * 1000),
                        "text": segment.text.strip()
                    }
                    tmp[
                        'time'] = f'{ms_to_time_string(ms=tmp["start_time"])} --> {ms_to_time_string(ms=tmp["end_time"])}'
                    append_raws(tmp)
                    continue
                else:
                    split_idx = middel_idx

            # 去掉重复的切分点并排序
            split_idx_list = sorted(list(set(split_idx_list)))

            # 如果2个切分点挨着，则删除一个
            wait_del = []
            for i, n in enumerate(split_idx_list):
                if i < len(split_idx_list) - 1:
                    if n + 1 == split_idx_list[i + 1]:
                        wait_del.append(n)
            if len(wait_del) > 0:
                for n in wait_del:
                    split_idx_list.remove(n)
            if len(split_idx_list) > 0:
                # 第一个设为-1,方便计算+1
                if split_idx_list[0] != 0:
                    split_idx_list.insert(0, -1)
                else:
                    split_idx_list[0] = -1
            # 切分点多于2个，并且时长大于4s，则两两切分组装
            if len(split_idx_list) > 2 and (segment.words[-1].end - segment.words[0].start) > 4:
                # 取出所有切分点，两两组合
                for i, idx in enumerate(split_idx_list):
                    # words组里起点索引为当前切分点+1
                    st = idx + 1
                    # 下一个为结束点,未到末尾
                    if i < len(split_idx_list) - 1:
                        ed = split_idx_list[i + 1]
                    else:
                        # 已到末尾
                        ed = len(segment.words) - 1
                    texts = []
                    for k in range(st, ed + 1):
                        texts.append(segment.words[k].word)
                    tmp = {
                        "line": len(raws) + 1,
                        "start_time": int(segment.words[st].start * 1000),
                        "end_time": int(segment.words[ed].end * 1000),
                        "text": join_word_flag.join(texts)
                    }
                    tmp[
                        'time'] = f'{ms_to_time_string(ms=tmp["start_time"])} --> {ms_to_time_string(ms=tmp["end_time"])}'
                    append_raws(tmp)
                continue
            # [0:split_idx] [split_idx:-1]
            tmp = {
                "line": len(raws) + 1,
                "start_time": int(segment.words[0].start * 1000),
                "end_time": int(segment.words[split_idx].end * 1000),
                "text": join_word_flag.join(
                    [word.word for i, word in enumerate(segment.words) if i <= split_idx])
            }
            tmp[
                'time'] = f'{ms_to_time_string(ms=tmp["start_time"])} --> {ms_to_time_string(ms=tmp["end_time"])}'
            append_raws(tmp)
            tmp = {
                "line": len(raws) + 1,
                "start_time": int(segment.words[split_idx + 1].start * 1000),
                "end_time": int(segment.words[-1].end * 1000),
                "text": join_word_flag.join(
                    [word.word for i, word in enumerate(segment.words) if i > split_idx])
            }
            tmp[
                'time'] = f'{ms_to_time_string(ms=tmp["start_time"])} --> {ms_to_time_string(ms=tmp["end_time"])}'
            append_raws(tmp)
    except Exception as e:
        err['msg'] = str(e)
    except BaseException as e:
        err['msg'] = str(e)
    finally:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
        time.sleep(2)
