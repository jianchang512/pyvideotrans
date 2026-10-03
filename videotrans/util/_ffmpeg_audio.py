# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import Union

from videotrans.configure.config import ROOT_DIR, logger
from videotrans.configure.constants import INSTALL_RUBBERBAND_TIPS
from videotrans.util._ffmpeg_runner import runffmpeg


def conver_to_16k(audio, target_audio):
    cmd = [
        "-y",
        "-i",
        Path(audio).as_posix(),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        Path(target_audio).as_posix()
    ]
    return runffmpeg(cmd)


def create_concat_txt(filelist, concat_txt=None):
    txt = []
    for it in filelist:
        path_obj = Path(it)
        if not path_obj.exists() or path_obj.stat().st_size == 0:
            continue
        txt.append(f"file '{path_obj.name}'")
    if not txt:
        raise RuntimeError("Cannot create concat txt from an empty or invalid file list.")

    with open(concat_txt, 'w', encoding='utf-8') as f:
        f.write("\n".join(txt))
    return concat_txt


def concat_multi_audio(*, out:str=None, concat_txt:str=None)->bool:
    if out:
        out = Path(out).as_posix()

    cmd = ['-y', '-f', 'concat', '-safe', '0', '-i', concat_txt, "-b:a", "128k"]
    if out.endswith('.m4a'):
        cmd += ['-c:a', 'aac']
    elif out.endswith('.wav'):
        cmd += ['-c:a', 'pcm_s16le']
    runffmpeg(cmd + [out], cmd_dir=Path(concat_txt).parent.as_posix())
    return True


def change_speed_rubberband(input_path:str, out_file:str, target_duration:Union[float,int]):
    try:
        import pyrubberband as pyrb
    except Exception:
        logger.warning(f'进行音频变速时失败，因为未安装  rubberband 库，使用 ffmpeg 进行变速处理\n{INSTALL_RUBBERBAND_TIPS}')
        return precise_speed_up_audio(file_path=input_path, out=out_file, target_duration_ms=target_duration)

    import soundfile as sf
    import numpy as np
    try:
        y, sr = sf.read(input_path)
        if len(y) == 0:
            logger.warning(f"[Audio-RB] 空音频文件: {input_path}")
            return

        current_duration = int((len(y) / sr) * 1000)

        if target_duration <= 0: target_duration = 1

        time_stretch_rate = current_duration / target_duration

        time_stretch_rate = max(0.2, min(time_stretch_rate, 50.0))

        logger.debug(
            f"[Audio-RB] {input_path} 原长:{current_duration}ms -> 目标:{target_duration}ms 倍率:{time_stretch_rate:.2f}")

        y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)

        if y_stretched.ndim == 1:
            y_stretched = np.column_stack((y_stretched, y_stretched))

        sf.write(out_file, y_stretched, sr)

    except Exception as e:
        logger.error(f"[Audio-RB] 音频处理失败 {input_path}: {e}")
        return


def precise_speed_up_audio(*, file_path:str=None, out:str=None, target_duration_ms:Union[float,int]):
    from pydub import AudioSegment
    ext = file_path[-3:].lower()
    out_ext = ext
    if out:
        out_ext = out[-3:].lower()
    codecs = {"m4a": "aac", "mp3": "libmp3lame", "wav": "pcm_s16le"}
    audio = AudioSegment.from_file(file_path, format='mp4' if ext == 'm4a' else ext)

    current_duration_ms = len(audio)

    atempo_list = []
    speed_factor = current_duration_ms / target_duration_ms

    while speed_factor > 2.0:
        atempo_list.append("atempo=2.0")
        speed_factor /= 2.0

    atempo_list.append(f"atempo={speed_factor}")

    filter_str = ",".join(atempo_list)
    if not out:
        Path(file_path).rename(file_path + f".{ext}")
        file_path = file_path + f".{ext}"
        out = file_path
    cmd = [
        '-y',
        '-i',
        file_path,
        '-filter:a',
        filter_str,
        '-t', f"{target_duration_ms / 1000.0}",
        '-ar', "48000",
        '-ac', "2",
        '-c:a', codecs.get(out_ext, 'pcm_s16le'),
        out
    ]
    try:
        runffmpeg(cmd, force_cpu=True)
    except Exception as e:
        logger.exception(f'音频加速失败:{e}')


def cut_from_audio(*, ss, to, audio_file, out_file)->bool:
    from . import help_srt
    if not Path(audio_file).exists():
        return False
    Path(out_file).parent.mkdir(exist_ok=True, parents=True)
    cmd = [
        "-y",
        "-i",
        audio_file,
        "-ss",
        help_srt.format_time(ss, '.'),
        "-to",
        help_srt.format_time(to, '.'),
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        out_file
    ]
    return runffmpeg(cmd)


def remove_silence_wav(
    audio_file: str,
    rm_start: bool = True,
    rm_all: bool = False,
    rm_level: str = "default"
) -> bool:
    """
    移除 WAV 音频文件中的静音。

    Args:
        audio_file: 待处理的音频文件路径
        rm_start:   是否移除开头的静音部分（当 rm_all=False 时生效）
        rm_all:     是否移除开头、末尾、中间等所有静音。若为 True 则忽略 rm_start
        rm_level:   移除静音力度：
                    - "min": 轻度，保留更多自然停顿，防止切字
                    - "default" / "middle": 默认中度，平衡效果
                    - "max": 强力，激进移除，哪怕微小的呼吸声/停顿也会被移除

    Returns:
        bool: 处理成功并保存返回 True，如果整段音频均为静音或无修改则返回 False
    """
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent

    audio = AudioSegment.from_file(audio_file, format="wav")
    total_len = len(audio)
    print(f'原始长度: {total_len}ms')
    if total_len == 0:
        return False

    # 1. 根据 rm_level 配置不同检测参数
    #   - thresh_offset: 相对平均分贝(dBFS)的偏移量。越偏向 0 判定越激进。
    #   - min_silence_len: 连续多少毫秒的声音低于阈值才算静音。
    #   - padding: 语音起止点前后保留的毫秒数，防止切断辅音或尾音。
    level_configs = {
        "min": {
            "thresh_offset": -20,      # 相对基准较低，只有很安静的部分才算静音
            "fallback_thresh": -55,
            "min_silence_len": 250,    # 较长停顿才处理
            "head_padding": 150,       # 较多保留，防止吃字
            "tail_padding": 200,
        },
        "default": {
            "thresh_offset": -15,
            "fallback_thresh": -45,
            "min_silence_len": 100,
            "head_padding": 60,
            "tail_padding": 100,
        },
        "max": {
            "thresh_offset": -8,       # 接近平均音量，非常激进
            "fallback_thresh": -35,
            "min_silence_len": 60,     # 短促停顿即切
            "head_padding": 20,        # 极少保留
            "tail_padding": 40,
        }
    }

    level = rm_level.lower().strip()
    cfg = level_configs.get(level, level_configs["default"])

    # 动态计算静音分贝阈值
    if audio.dBFS == float('-inf') or audio.dBFS is None:
        silence_thresh = cfg["fallback_thresh"]
    else:
        # 基于音频平均响度计算，并限制在一个合理物理区间 [-65, -25]
        silence_thresh = max(-65.0, min(-25.0, audio.dBFS + cfg["thresh_offset"]))

    # 2. 检测所有非静音片段
    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=cfg["min_silence_len"],
        silence_thresh=silence_thresh,
        seek_step=10
    )

    # 全是静音的情况
    if not nonsilent_chunks:
        return False

    head_pad = cfg["head_padding"]
    tail_pad = cfg["tail_padding"]

    # 3. 分支处理：移除所有静音 (rm_all=True) VS 仅首尾裁切 (rm_all=False)
    if rm_all:
        # 1. 阈值设定：如果两段人声的间距小于这个值，说明是正常的字间换气或短暂停顿，不应切断
        # 间隙必须大于前后保护区之和，才具备剪切价值
        min_gap_to_cut = head_pad + tail_pad

        # 2. 先合并间距过小的人声片段（防止微切和抽搐感）
        merged_chunks = []
        for chunk in nonsilent_chunks:
            if not merged_chunks:
                merged_chunks.append(list(chunk))
            else:
                prev_start, prev_end = merged_chunks[-1]
                curr_start, curr_end = chunk

                gap = curr_start - prev_end  # 计算两个发音之间的真实静音长度

                if gap <= min_gap_to_cut:
                    # 间隙太小：合并为一个大片段，中间的静音完整保留
                    merged_chunks[-1][1] = curr_end
                else:
                    # 间隙足够大：确认为有效停顿，记录为新的独立片段
                    merged_chunks.append(list(chunk))

        # 3. 对合并后的真实大片段施加 Head/Tail Padding 保护，并切出音频
        trimmed_audio = AudioSegment.empty()
        for s, e in merged_chunks:
            # 经过上面的逻辑筛选，这里 pad 后的区间在数学上必定绝对独立，绝不会重叠
            pad_start = max(0, s - head_pad)
            pad_end = min(total_len, e + tail_pad)

            trimmed_audio += audio[pad_start:pad_end]
    else:
        # 仅裁切首尾
        raw_start = nonsilent_chunks[0][0]
        raw_end = nonsilent_chunks[-1][1]

        start_trim = max(0, raw_start - head_pad) if rm_start else 0
        end_trim = min(total_len, raw_end + tail_pad)

        trimmed_audio = audio[start_trim:end_trim]

    # 4. 导出覆盖原文件
    # print(f'结果长度: {len(trimmed_audio)}ms')
    # print(f'移除: {total_len- len(trimmed_audio) }ms')
    trimmed_audio.export(audio_file, format="wav")
    return True

def remove_silence_wav_bak(audio_file:str, rm_start=True,rm_all=False,rm_level="middle")->bool:
    """

    Args:
        audio_file: 待处理的音频文件
        rm_start:  是否移除开头的静音部分
        rm_all:  是否移除开头、末尾、中间等所有静音，若 True 则忽略 rm_start 并移除 audio_file 中所有静音
        rm_level: 移除静音力度，middle是默认，low 是轻度移除，比middle移除更少的静音， max 是最大力度移除，尽量多的移除静音

    Returns:

    """
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent

    audio = AudioSegment.from_file(audio_file, format="wav")

    silence_threshold = -50 # 越大处理越激进，移除更多静音
    min_silence_len = 100 #连续超过这些ms视为可移除的有效静音

    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_threshold,
        seek_step=10
    )

    if len(nonsilent_chunks) > 0:
        head_padding_ms = 80
        tail_padding_ms = 150

        raw_start = nonsilent_chunks[0][0]
        raw_end = nonsilent_chunks[-1][1]

        start_trim = max(0, raw_start - head_padding_ms) if rm_start else 0
        end_trim = min(len(audio), raw_end + tail_padding_ms)

        trimmed_audio = audio[start_trim:end_trim]
        trimmed_audio.export(audio_file, format="wav")
        return True

    return False
