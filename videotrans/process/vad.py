import time
import traceback

import numpy as np
import scipy.io.wavfile as Wavfile
from ten_vad import TenVad

from videotrans.configure.config import logger


def get_speech_timestamp_silero(input_wav,
                                threshold=None,
                                min_speech_duration_ms=0,
                                max_speech_duration_ms=None,
                                min_silent_duration_ms=None):
    # 防止填写错误
    min_speech_duration_ms = 0  # int(max(min_speech_duration_ms,0))
    min_silent_duration_ms = int(max(min_silent_duration_ms, 50))
    max_speech_duration_ms = int(min(max(max_speech_duration_ms, min_speech_duration_ms + 1000), 30000))
    logger.debug(
        f'[silero-VAD]:断句参数：{threshold=},{min_speech_duration_ms=}ms,{max_speech_duration_ms=}ms,{min_silent_duration_ms=}ms')

    sampling_rate = 16000
    from faster_whisper.audio import decode_audio
    from faster_whisper.vad import (
        VadOptions,
        get_speech_timestamps
    )
    vad_p = {
        "threshold": threshold,
        "min_speech_duration_ms": min_speech_duration_ms,
        "max_speech_duration_s": float(max_speech_duration_ms / 1000.0),
        "min_silence_duration_ms": min_silent_duration_ms,
    }

    def convert_to_milliseconds(timestamps):
        milliseconds_timestamps = []
        for timestamp in timestamps:
            milliseconds_timestamps.append(
                [
                    int(round(timestamp["start"] / sampling_rate * 1000)),
                    int(round(timestamp["end"] / sampling_rate * 1000)),
                ]
            )

        return milliseconds_timestamps

    speech_chunks = get_speech_timestamps(decode_audio(input_wav,
                                                       sampling_rate=sampling_rate),
                                          vad_options=VadOptions(**vad_p)
                                          )
    
    merged_segments=convert_to_milliseconds(speech_chunks)
    if not merged_segments:
        return None
    if merged_segments[0][0]<0:
        merged_segments[0][0]=0
    _vail_segments=[]
    for it in merged_segments:
        if it[1]>it[0] and it[0]>=0:
            _vail_segments.append(it)
    return _vail_segments




def get_speech_timestamp(input_wav=None,
                         threshold=None,
                         min_speech_duration_ms=None,
                         max_speech_duration_ms=None,
                         min_silent_duration_ms=None):
    st_ = time.time()
    
    try:
        sr, data = Wavfile.read(input_wav)
    except Exception as e:
        msg = traceback.format_exc()
        return None

    # 动态计算每帧时长
    hop_size = 256
    frame_duration_ms = (hop_size / sr) * 1000.0

    # 规范化参数
    min_speech_duration_ms = int(max(500, min_speech_duration_ms if min_speech_duration_ms else 1000))
    min_silent_duration_ms = int(max(50, min_silent_duration_ms if min_silent_duration_ms else 200))
    if max_speech_duration_ms is None:
        max_speech_duration_ms = 30000

    logger.debug(
        f'[Ten-VAD]:断句参数：{threshold=},{min_speech_duration_ms=}ms,{max_speech_duration_ms=}ms,{min_silent_duration_ms=}ms')

    # 能量自适应阈值
    audio_energy = np.mean(np.abs(data)) if len(data) > 0 else 0
    adjusted_threshold = threshold
    if audio_energy > 10000:
        adjusted_threshold = max(threshold * 1.2, 0.3)
    elif audio_energy < 1000:
        adjusted_threshold = min(threshold * 0.8, 0.2)

    logger.debug(f'[Ten-VAD]音频能量: {audio_energy}, 调整后阈值: {adjusted_threshold}')

    # --- 初步 VAD 检测（不设最长限制，保证自然断句） ---
    min_sil_frames = max(1, int(min_silent_duration_ms / frame_duration_ms))
    initial_segments = _detect_raw_segments(data, adjusted_threshold, min_sil_frames, max_speech_frames=None)

    if not initial_segments:
        # 完全无语音
        return None

    # --- 处理超长片段 ---
    # 使用队列递归切分，寻找微停顿，兜底用能量最低点切割
    max_speech_frames = int(max_speech_duration_ms / frame_duration_ms)
    segments_ms = []
    chunk_queue = [list(seg) for seg in initial_segments]

    while chunk_queue:
        s_frame, e_frame = chunk_queue.pop(0)
        dur_frames = e_frame - s_frame

        if dur_frames <= max_speech_frames:
            segments_ms.append([s_frame * frame_duration_ms, e_frame * frame_duration_ms])
            continue

        # 超过最大时长，尝试寻找换气点/微停顿
        sub_data = data[s_frame * hop_size : e_frame * hop_size]
        sub_segs = []
        # 尝试三档：标准静音 -> 半静音 -> 极短静音(约30ms)
        test_conditions = [
            (1.0, 1.0),                     # 原始参数
            (0.5, 1.2),                     # 一半静音时长，阈值稍严
            (max(30 / min_silent_duration_ms, 0.2), 1.5)  # 约30ms，阈值较严
        ]
        
        for sil_ratio, thresh_mult in test_conditions:
            test_sil_frames = max(1, int((min_silent_duration_ms * sil_ratio) / frame_duration_ms))
            test_thresh = min(adjusted_threshold * thresh_mult, 0.9)
            
            temp_segs = _detect_raw_segments(
                sub_data, test_thresh, test_sil_frames,
                max_speech_frames=max_speech_frames   # 传入最大帧数限制，防止子段又超长
            )
            if len(temp_segs) > 1:
                max_sub_dur = max((se - ss) for ss, se in temp_segs)
                if max_sub_dur < dur_frames:  # 确实切短了
                    sub_segs = temp_segs
                    break

        if sub_segs:
            new_chunks = [[s_frame + ss, s_frame + se] for ss, se in sub_segs]
            chunk_queue = new_chunks + chunk_queue
        else:
            # 终极兜底：在安全区内寻找能量最低点切断
            # 安全区为 50%~100% 最大时长之间
            search_start = int(max_speech_frames * 0.5)
            search_end = min(max_speech_frames, dur_frames)
            
            if search_end > search_start:
                energies = [np.sum(np.abs(sub_data[i * hop_size : (i+1) * hop_size]))
                            for i in range(search_start, search_end)]
                best_cut_idx = search_start + np.argmin(energies)
            else:
                best_cut_idx = max_speech_frames
                
            cut_point = s_frame + best_cut_idx
            # 先放后半段，再放前半段，保证按时间顺序处理
            chunk_queue.insert(0, [cut_point, e_frame])
            chunk_queue.insert(0, [s_frame, cut_point])

    logger.debug(f'[Ten-VAD]初步切分及超长处理用时 {int(time.time() - st_)}s')

    # --- 短片段合并 ---
    # 确保所有片段时长 >= min_speech_duration_ms
    segs = [seg.copy() for seg in segments_ms]
    # 先过滤掉非法片段（start>=end）
    segs = [[int(max(0, s)), int(max(0, e))] for s, e in segs if e > s]
    
    # 合并算法：利用栈，动态检查栈顶片段是否过短
    merged = []
    for seg in segs:
        if not merged:
            merged.append(seg)
            continue
        # 检查栈顶片段是否过短
        while merged and (merged[-1][1] - merged[-1][0]) < min_speech_duration_ms:
            # 栈顶短，必须与当前seg合并
            prev = merged.pop()
            # 合并到当前seg（向前合并）
            seg[0] = prev[0]
            # 如果栈非空且gap很小，也可以考虑合并，但这里简单把prev吞给seg
        # 现在再检查当前seg本身是否过短
        if (seg[1] - seg[0]) < min_speech_duration_ms:
            if merged:
                # 看看是合并到上一个更好，还是留待后面处理
                # 直接合并到上一个，因为如果留到后面可能还是得合并
                merged[-1][1] = seg[1]
            else:
                # 第一个片段本身就短，暂存
                merged.append(seg)
        else:
            merged.append(seg)
    
    # 处理栈顶可能残留的过短片段（因为后面没有片段了，只能保留）
    # 或者如果它是唯一片段，也保留
    _vail_segments = []
    for s, e in merged:
        if e > s and s>=0:
            # 再次确保非负和有效性
            _vail_segments.append([max(0, s), max(0, e)])
            
    logger.debug(f'[Ten-VAD]切分合并共用时:{int(time.time() - st_)}s')
    return _vail_segments


def _detect_raw_segments(data, threshold, min_silent_frames, max_speech_frames=None):
    """
    内部VAD检测。
    """
    hop_size = 256
    ten_vad_instance = TenVad(hop_size, threshold)

    if len(data.shape) > 1:
        data = np.mean(data, axis=1)

    # 性能优化：一次性类型转换
    if data.dtype != np.int16:
        data = data.astype(np.int16)

    num_frames = (data.shape[0] - hop_size) // hop_size + 1
    segments = []
    triggered = False
    speech_start_frame = 0
    silence_frame_count = 0

    for i in range(num_frames):
        audio_frame = data[i * hop_size: (i + 1) * hop_size]
        if len(audio_frame) != hop_size:
            continue

        _, is_speech = ten_vad_instance.process(audio_frame)

        if triggered:
            if is_speech == 1:
                silence_frame_count = 0
            else:
                silence_frame_count += 1

            is_silence_timeout = silence_frame_count >= min_silent_frames
            is_max_timeout = (max_speech_frames is not None and 
                              (i - speech_start_frame) >= max_speech_frames)

            if is_silence_timeout or is_max_timeout:
                end_frame = i if is_max_timeout else i - silence_frame_count
                segments.append([speech_start_frame, end_frame])
                triggered = False
                silence_frame_count = 0
        else:
            if is_speech == 1:
                triggered = True
                speech_start_frame = i
                silence_frame_count = 0

    if triggered:
        end_frame = num_frames - silence_frame_count
        segments.append([speech_start_frame, end_frame])

    return segments

