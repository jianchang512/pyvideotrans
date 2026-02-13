import time,os,shutil
import traceback

from videotrans.configure import config
from ten_vad import TenVad
import scipy.io.wavfile as Wavfile
import numpy as np


def get_speech_timestamp_silero(input_wav,
                         threshold=None,
                         min_speech_duration_ms=None,
                         max_speech_duration_ms=None,
                         min_silent_duration_ms=None):
        # 防止填写错误
        min_speech_duration_ms=0#int(max(min_speech_duration_ms,0))
        min_silent_duration_ms=int(max(min_silent_duration_ms,50))
        max_speech_duration_ms=int(min(max(max_speech_duration_ms,min_speech_duration_ms+1000),30000))
        config.logger.debug(f'[silero-VAD]Fix:VAD断句参数：{threshold=},{min_speech_duration_ms=}ms,{max_speech_duration_ms=}ms,{min_silent_duration_ms=}ms')

        sampling_rate = 16000
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import (
            VadOptions,
            get_speech_timestamps
        )
        vad_p = {
            "threshold": threshold,
            "min_speech_duration_ms": min_speech_duration_ms,
            "max_speech_duration_s": float(max_speech_duration_ms/1000.0),
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
        return convert_to_milliseconds(speech_chunks)


def get_speech_timestamp(input_wav=None,
                         threshold=None,
                         min_speech_duration_ms=None,
                         max_speech_duration_ms=None,
                         min_silent_duration_ms=None):
    # 限定范围
    #最短语音时长不得低于250ms
    min_speech_duration_ms=int(max(250,min_speech_duration_ms))
    #切割的静音阈值，不得低于50ms
    min_silent_duration_ms=int(max(50,min_silent_duration_ms))

    config.logger.debug(f'[Ten-VAD]Fix after:VAD断句参数：{threshold=},{min_speech_duration_ms=}ms,{max_speech_duration_ms=}ms,{min_silent_duration_ms=}ms')
    frame_duration_ms = 16
    hop_size = 256
    st_=time.time()
    try:
        sr, data = Wavfile.read(input_wav)
    except Exception as e:
        msg=traceback.format_exc()
        config.logger.exception(f"Error reading wav file: {msg}",exc_info=True)
        return False

    # 计算音频能量，用于自适应阈值调整
    audio_energy = np.mean(np.abs(data)) if len(data) > 0 else 0
    # 根据音频能量调整阈值，处理噪声过大的情况
    adjusted_threshold = threshold
    if audio_energy > 10000:  # 高能量音频（可能噪声大）
        adjusted_threshold = max(threshold * 1.2, 0.3)  # 提高阈值
    elif audio_energy < 1000:  # 低能量音频
        adjusted_threshold = min(threshold * 0.8, 0.2)  # 降低阈值

    config.logger.debug(f'[Ten-VAD]音频能量: {audio_energy}, 调整后阈值: {adjusted_threshold}')

    min_sil_frames = min_silent_duration_ms / frame_duration_ms
    initial_segments = _detect_raw_segments(data, adjusted_threshold, min_sil_frames, max_speech_frames=None)

    # --- 第二阶段：细化超长片段 超过2s---
    refined_segments = []
    max_frames_limit = max_speech_duration_ms / frame_duration_ms
    tighter_min_sil_frames = (min_silent_duration_ms / 2) / frame_duration_ms
    _n=0
    _len=len(initial_segments)
    for s, e in initial_segments:
        duration = e - s
        _n+=1
        # 大于 2000ms才需要再次裁切
        if duration > (max_frames_limit+125):
            # 提取该段音频数据
            sub_data = data[s * hop_size: e * hop_size]
            # 使用减半的静音阈值重新检测，同时带上最大时长限制
            sub_segs = _detect_raw_segments(sub_data, adjusted_threshold, tighter_min_sil_frames,
                                                 max_speech_frames=max_frames_limit)

            for ss, se in sub_segs:
                refined_segments.append([s + ss, s + se])
        else:
            refined_segments.append([s, e])

    if not refined_segments:
        return False

    # --- 第三阶段：毫秒转换 & 强制硬截断保护 ---
    # 即使二次细分，如果有人一口气说了30秒没停顿，仍需硬截断
    segments_ms = []
    for s, e in refined_segments:
        start_ms = int(s * frame_duration_ms)
        end_ms = int(e * frame_duration_ms)

        # 循环确保不超 max_speech_duration_ms
        curr_s = start_ms
        while (end_ms - curr_s) > max_speech_duration_ms:
            # 尝试在静音处截断，而不是生硬截断
            # 计算当前块的中间静音区域
            block_data = data[int(curr_s/1000*sr):int((curr_s + max_speech_duration_ms)/1000*sr)]
            # 寻找最后一个静音区域
            block_segments = _detect_raw_segments(block_data, adjusted_threshold, min_sil_frames/2, max_speech_frames=None)
            if block_segments and len(block_segments) > 1:
                # 如果有多个段，使用最后一个段的开始作为截断点
                last_segment_start = block_segments[-2][1] * hop_size / sr * 1000
                truncate_point = int(curr_s + last_segment_start)
                if truncate_point > curr_s + max_speech_duration_ms * 0.8:
                    segments_ms.append([curr_s, truncate_point])
                    curr_s = truncate_point
                    continue
            # 如果没有找到合适的截断点，使用硬截断
            segments_ms.append([curr_s, curr_s + int(max_speech_duration_ms)])
            curr_s += int(max_speech_duration_ms)

        if end_ms - curr_s > 0:
            segments_ms.append([curr_s, end_ms])
    
    config.logger.debug(f'[Ten-VAD]切分用时 {int(time.time() - st_)}s')
    
    speech_len = len(segments_ms)
    if speech_len <= 1:
        return segments_ms

    # --- 优化的片段合并策略 ---
    merged_segments = []
    # 不允许最小语音片段低于500ms，可能无法有效识别而报错
    min_speech_duration_ms = max(min_speech_duration_ms or 1000, 500)
    
    # 第一轮：合并连续的短片段
    temp_segments = []
    current_merge = None
    current_duration = 0
    
    for i, segment in enumerate(segments_ms):
        duration = segment[1] - segment[0]
        
        if duration < min_speech_duration_ms:
            # 短片段，需要合并
            if current_merge is None:
                current_merge = segment.copy()
                current_duration = duration
            else:
                # 计算与当前合并段的间隔
                gap = segment[0] - current_merge[1]
                # 如果间隔较小，合并到当前段
                if gap < min_silent_duration_ms:
                    current_merge[1] = segment[1]
                    current_duration += duration + gap
                else:
                    # 间隔较大，结束当前合并，开始新的合并
                    temp_segments.append(current_merge)
                    current_merge = segment.copy()
                    current_duration = duration
        else:
            # 长片段，检查是否有未完成的合并
            if current_merge is not None:
                # 计算与前一个合并段的间隔
                gap = segment[0] - current_merge[1]
                # 如果间隔较小，合并到当前长片段
                if gap < min_silent_duration_ms * 1.5:
                    segment[0] = current_merge[0]
                else:
                    # 否则，添加合并段
                    temp_segments.append(current_merge)
                current_merge = None
                current_duration = 0
            temp_segments.append(segment)
    
    # 处理最后一个合并段
    if current_merge is not None:
        temp_segments.append(current_merge)
    
    # 第二轮：检查合并后的片段，确保没有过短的片段
    for i, segment in enumerate(temp_segments):
        duration = segment[1] - segment[0]
        
        if duration >= min_speech_duration_ms:
            merged_segments.append(segment)
        else:
            # 仍然过短，尝试合并到邻近片段
            if i == 0 and len(temp_segments) > 1:
                # 第一个片段，合并到下一个
                temp_segments[i+1][0] = segment[0]
            elif i == len(temp_segments) - 1 and len(merged_segments) > 0:
                # 最后一个片段，合并到前一个
                merged_segments[-1][1] = segment[1]
            elif len(merged_segments) > 0 and i < len(temp_segments) - 1:
                # 中间片段，合并到更近的一边
                prev_gap = segment[0] - merged_segments[-1][1]
                next_gap = temp_segments[i+1][0] - segment[1]
                
                if prev_gap <= next_gap:
                    merged_segments[-1][1] = segment[1]
                else:
                    temp_segments[i+1][0] = segment[0]
            else:
                # 无法合并的情况，添加为单独片段
                merged_segments.append(segment)
    
    config.logger.debug(f'[Ten-VAD]切分合并共用时:{int(time.time()-st_)}s')
    return merged_segments

def _detect_raw_segments(data, threshold, min_silent_frames, max_speech_frames=None):
    """
    内部辅助函数：根据给定的静音阈值和最大长度检测语音片段。
    """
    hop_size = 256
    
    ten_vad_instance = TenVad(hop_size, threshold)
    
    # 确保数据是一维数组
    if len(data.shape) > 1:
        data = np.mean(data, axis=1)  # 降维到单声道
    
    # 计算有效帧数，确保每帧长度为hop_size
    num_frames = (data.shape[0] - hop_size) // hop_size + 1

    segments = []
    triggered = False
    speech_start_frame = 0
    silence_frame_count = 0

    for i in range(num_frames):
        # 确保每次取的帧长度为hop_size
        audio_frame = data[i * hop_size: (i + 1) * hop_size]
        
        # 确保音频帧长度正确
        if len(audio_frame) != hop_size:
            continue
            
        # 确保数据类型正确
        if audio_frame.dtype != np.int16:
            audio_frame = audio_frame.astype(np.int16)

        _, is_speech = ten_vad_instance.process(audio_frame)

        if triggered:
            current_speech_len = i - speech_start_frame
            if is_speech == 1:
                silence_frame_count = 0
            else:
                silence_frame_count += 1

            # 结束条件：1. 静音满足长度 2. (可选) 达到最大长度强制切断
            is_silence_timeout = silence_frame_count >= min_silent_frames
            is_max_timeout = max_speech_frames is not None and current_speech_len >= max_speech_frames

            if is_silence_timeout or is_max_timeout:
                if is_max_timeout:
                    end_frame = i
                else:
                    end_frame = i - silence_frame_count

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

