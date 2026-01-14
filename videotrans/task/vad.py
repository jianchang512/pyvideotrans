import time,os,shutil
import traceback

from videotrans.configure import config
from ten_vad import TenVad
import scipy.io.wavfile as Wavfile
import numpy as np
from concurrent.futures import ProcessPoolExecutor
# 1. 独立的 Worker 函数
# =========================================================================
def _vad_parallel_worker(args):
    data_chunk, threshold, min_silent_frames, hop_size = args
    
    # 在子进程中实例化 VAD，避免跨进程冲突
    # 假设 TenVad 类在当前文件可见，或已 import
    vad_instance = TenVad(hop_size, threshold)
    
    num_frames = data_chunk.shape[0] // hop_size
    segments = []
    
    triggered = False
    speech_start = 0
    silence_count = 0
    
    # 这是一个最简化的 detect_raw 逻辑复刻，去掉了 max_speech_frames 的判断
    # 因为并行处理只是为了第一阶段的大略切分
    for i in range(num_frames):
        frame = data_chunk[i*hop_size : (i+1)*hop_size]
        _, is_speech = vad_instance.process(frame)
        
        if triggered:
            if is_speech == 1:
                silence_count = 0
            else:
                silence_count += 1
            
            if silence_count >= min_silent_frames:
                end_frame = i - silence_count
                segments.append([speech_start, end_frame])
                triggered = False
                silence_count = 0
        else:
            if is_speech == 1:
                triggered = True
                speech_start = i
                silence_count = 0
                
    if triggered:
        segments.append([speech_start, num_frames - silence_count])
    return segments

def get_speech_timestamp_silero(input_wav,
                         threshold=None,
                         min_speech_duration_ms=None,
                         max_speech_duration_ms=None,
                         min_silent_duration_ms=None):
        # 防止填写错误
        min_speech_duration_ms=max(min_speech_duration_ms,0)
        min_silent_duration_ms=max(min_silent_duration_ms,50)
        max_speech_duration_ms=min(max(max_speech_duration_ms,min_speech_duration_ms+1000),30000)
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


## 
# 多进程vad 
def get_speech_timestamp(input_wav=None,
                         threshold=None,
                         min_speech_duration_ms=None,
                         max_speech_duration_ms=None,
                         min_silent_duration_ms=None):
    # 限定范围
    min_speech_duration_ms=max(250,min_speech_duration_ms)#最短语音时长不得低于250ms
    min_silent_duration_ms=max(50,min_silent_duration_ms)#切割的静音阈值，不得低于50ms
    config.logger.debug(f'[Ten-VAD]Fix after:VAD断句参数：{threshold=},{min_speech_duration_ms=}ms,{max_speech_duration_ms=}ms,{min_silent_duration_ms=}ms')
    frame_duration_ms = 16
    hop_size = 256
    st_=time.time()
    try:
        sr, data = Wavfile.read(input_wav)
    except Exception as e:
        msg=traceback.format_exc()
        config.logger.exception(f"Error reading wav file: {msg}",exc_info=True)
        return False,msg

    # --- 策略分支：决定单核还是多核 ---
    total_len_samples = len(data)
    total_duration_minutes = (total_len_samples / sr) / 60.0
    
    # 阈值：大于20分钟  切分为多片加速执行
    PARALLEL_THRESHOLD_MINUTES = 20 
    
    min_sil_frames = min_silent_duration_ms / frame_duration_ms
    initial_segments = []
    num_cores=1
    if total_duration_minutes > PARALLEL_THRESHOLD_MINUTES:
        # 每个音频分片>=10分钟
        num_cores = min((total_duration_minutes//10)+1, os.cpu_count()-1)

    # Case A: 短音频 -> 走老路 (单核) 
    if total_duration_minutes <= PARALLEL_THRESHOLD_MINUTES:
        config.logger.debug(f"Audio duration {total_duration_minutes:.2f}m,{PARALLEL_THRESHOLD_MINUTES=}m. Using Single Core.")
        initial_segments = _detect_raw_segments(data, threshold, min_sil_frames, max_speech_frames=None)
    
    # Case B: 长音频 -> 走新路 (多核)
    else:
        config.logger.debug(f"Long Audio Detected ({total_duration_minutes:.2f}m). Using {num_cores} Cores Parallel Processing.")
        
        try:
            # 1. 分为切片并行处理
            chunk_len = total_len_samples // num_cores
            # 强制对齐到 hop_size (防止帧错位)
            chunk_len = (chunk_len // hop_size) * hop_size
            
            tasks = []
            for i in range(num_cores):
                start = i * chunk_len
                # 最后一个核拿走剩下的所有数据
                end = start + chunk_len if i < num_cores - 1 else total_len_samples
                
                sub_data = data[start:end]
                tasks.append((sub_data, threshold, min_sil_frames, hop_size))
            
            # 2. 并行执行
            # 注意：直接调用外部函数
            with ProcessPoolExecutor(max_workers=num_cores) as executor:
                results = list(executor.map(_vad_parallel_worker, tasks))
            
            # 3. 合并结果并修正坐标
            for i, segments in enumerate(results):
                offset_samples = i * chunk_len
                offset_frames = offset_samples // hop_size
                
                for s, e in segments:
                    initial_segments.append([s + offset_frames, e + offset_frames])
            
            # 排序（以防万一）
            initial_segments.sort(key=lambda x: x[0])
            
        except Exception as e:
            config.logger.error(f"Parallel processing failed: {e}. Falling back to single core.")
            # 兜底：万一多进程挂了，切回单核跑
            initial_segments = _detect_raw_segments(data, threshold, min_sil_frames, max_speech_frames=None)


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
            sub_segs = _detect_raw_segments(sub_data, threshold, tighter_min_sil_frames,
                                                 max_speech_frames=max_frames_limit)

            for ss, se in sub_segs:
                refined_segments.append([s + ss, s + se])
        else:
            refined_segments.append([s, e])

    if not refined_segments:
        return False,'Unknow error'

    # --- 第三阶段：毫秒转换 & 强制硬截断保护 ---
    # 即使二次细分，如果有人一口气说了30秒没停顿，仍需硬截断
    segments_ms = []
    for s, e in refined_segments:
        start_ms = int(s * frame_duration_ms)
        end_ms = int(e * frame_duration_ms)

        # 循环确保不超 max_speech_duration_ms
        curr_s = start_ms
        while (end_ms - curr_s) > max_speech_duration_ms:
            segments_ms.append([curr_s, curr_s + int(max_speech_duration_ms)])
            curr_s += int(max_speech_duration_ms)

        if end_ms - curr_s > 0:
            segments_ms.append([curr_s, end_ms])
    
    config.logger.debug(f'[Ten-VAD]切分用时 {int(time.time() - st_)}s')
    
    speech_len = len(segments_ms)
    if speech_len <= 1:
        return segments_ms,None

    check_1 = []

    # 不允许最小语音片段低于500ms，可能无法有效识别而报错
    min_speech_duration_ms = max(min_speech_duration_ms or 1000, 500)
    for i, it in enumerate(segments_ms):
        diff = it[1] - it[0]
        if diff >= min_speech_duration_ms:
            check_1.append(it)
        else:
            # 200-min_speech_duration_ms 之间的语音片段合并到邻近
            # 距离前面空隙
            prev_diff = it[0] - check_1[-1][1] if len(check_1) > 0 else None
            # 距离下个空隙
            next_diff = segments_ms[i + 1][0] - it[1] if i < speech_len - 1 else None
            if prev_diff is None and next_diff is not None:
                # 插入后边
                segments_ms[i + 1][0] = it[0]
            elif prev_diff is not None and next_diff is None:
                # 前面延长
                check_1[-1][1] = it[1]
            elif prev_diff is not None and next_diff is not None:
                if prev_diff < next_diff:
                    check_1[-1][1] = it[1]
                else:
                    segments_ms[i + 1][0] = it[0]
            else:
                check_1.append(it)
    config.logger.debug(f'[Ten-VAD]切分合并共用时:{int(time.time()-st_)}s')
    return check_1,None

def _detect_raw_segments(data, threshold, min_silent_frames, max_speech_frames=None):
    """
    内部辅助函数：根据给定的静音阈值和最大长度检测语音片段。
    """
    hop_size = 256
    
    ten_vad_instance = TenVad(hop_size, threshold)
    
    # ============== 优化开始 ==============
    # 1. 预先检查并一次性转换数据类型
    # 避免在循环中重复进行 10万次 的 int16->float32 转换和内存分配
    if data.dtype != np.int16:
        # 将 int16 归一化到 -1.0 ~ 1.0 的 float32
        # 这是 VAD 模型最喜欢的格式，处理速度最快
        int16_data = data.astype(np.int16) / 32768.0
    else:
        int16_data = data

    num_frames = int16_data.shape[0] // hop_size

    segments = []
    triggered = False
    speech_start_frame = 0
    silence_frame_count = 0

    for i in range(num_frames):
        audio_frame=int16_data[i * hop_size: (i + 1) * hop_size]

        #audio_frame = data[i * hop_size: (i + 1) * hop_size]
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
