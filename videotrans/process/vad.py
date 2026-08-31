import time
import traceback

import numpy as np
import scipy.io.wavfile as Wavfile
from ten_vad import TenVad

from videotrans.configure.config import logger


def get_speech_timestamp_silero(input_wav,
                                threshold=0.5,
                                min_speech_duration_ms=0,
                                max_speech_duration_ms=None,
                                min_silent_duration_ms=None, **kw):
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
        if it[1]<=it[0] or it[0]<0:
            continue
        if not _vail_segments or (it[1]-it[0]>1000) or (_vail_segments[-1][1]-_vail_segments[-1][0]>10000):
            _vail_segments.append(it)
        else:
            _vail_segments[-1][1]=it[1]
        
    return _vail_segments




def get_speech_timestamp(input_wav=None,
                         threshold=0.5,
                         min_speech_duration_ms=None,
                         max_speech_duration_ms=None,
                         min_silent_duration_ms=None, **kw):
    st_ = time.time()
    
    try:
        sr, data = Wavfile.read(input_wav)
    except Exception as e:
        logger.exception(e,exc_info=True)
        return None

    # 动态计算每帧时长
    hop_size = 256
    frame_duration_ms = (hop_size / sr) * 1000.0

    # 规范化参数
    min_speech_duration_ms = int(max(1000, min_speech_duration_ms if min_speech_duration_ms else 1000))
    min_silent_duration_ms = int(max(50, min_silent_duration_ms if min_silent_duration_ms else 200))
    if max_speech_duration_ms is None:
        max_speech_duration_ms = 12000

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


    min_sil_frames = max(1, int(min_silent_duration_ms / frame_duration_ms))
    max_speech_frames = int(max_speech_duration_ms / frame_duration_ms)+1000
    initial_segments = _detect_raw_segments(
        data, 
        adjusted_threshold, 
        min_sil_frames, 
        max_speech_frames=max_speech_frames
        )

    if not initial_segments:
        # 完全无语音
        return None


    segments_ms = []
    chunk_queue = [list(seg) for seg in initial_segments]
    
    while chunk_queue:
        s_frame, e_frame = chunk_queue.pop(0)

        segments_ms.append([s_frame * frame_duration_ms, e_frame * frame_duration_ms])

    # 先过滤掉非法片段（start>=end）
    segs = [[int(max(0, s)), int(max(0, e))] for s, e in segments_ms if e > s]
    if not segs:
        return None
    
    
    
    _len=len(segs)
    merged = []
    for i,seg in enumerate(segs):
        # 当前结束时间大于后边开始时间，非法，移除
        if _len>1 and i<_len-1 and seg[1]>segs[i+1][0]:
            continue
        if not merged:
            merged.append(seg)
            continue
        
        # 小于1s
        if seg[1]-seg[0]<1000:
            if i==_len-1:
                merged[-1][1]=seg[1]
                continue
            
            if merged[-1][1]-merged[-1][0]<max_speech_duration_ms:
                merged[-1][1]=seg[1]
                continue
        
        merged.append(seg)
            
    if not merged:
        return None
    _s,_e=None,None
    if len(merged)>1 and merged[0][1]-merged[0][0]<1000:
        _s=merged.pop(0)

    if len(merged)>1 and merged[-1][1]-merged[-1][0]<1000:
        _e=merged.pop(-1)
    
    
    if _s:
        merged[0][0]=_s[0]
    if _e:
        merged[-1][1]=_e[1]
    logger.debug(f'[Ten-VAD]切分合并共用时:{int(time.time() - st_)}s')
    return merged


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

