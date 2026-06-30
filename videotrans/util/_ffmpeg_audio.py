# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import Union

from videotrans.configure.config import ROOT_DIR, logger
from videotrans.configure.contants import INSTALL_RUBBERBAND_TIPS
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


def remove_silence_wav(audio_file:str, rm_start=True)->bool:
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent

    audio = AudioSegment.from_file(audio_file, format="wav")

    silence_threshold = audio.dBFS - 20

    min_silence_len = 100

    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_threshold,
        seek_step=10
    )

    if len(nonsilent_chunks) > 0:
        head_padding_ms = 80
        tail_padding_ms = 200

        raw_start = nonsilent_chunks[0][0]
        raw_end = nonsilent_chunks[-1][1]

        start_trim = max(0, raw_start - head_padding_ms) if rm_start else 0
        end_trim = min(len(audio), raw_end + tail_padding_ms)

        trimmed_audio = audio[start_trim:end_trim]
        trimmed_audio.export(audio_file, format="wav")
        return True

    return False
