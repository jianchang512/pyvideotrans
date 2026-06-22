import json
import os
import re
import platform
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Union

from videotrans.configure.config import ROOT_DIR, tr, app_cfg, settings, logger
from videotrans.configure import config
from videotrans.task.taskcfg import InputFile
from videotrans.configure import contants
from videotrans.configure.contants import INSTALL_RUBBERBAND_TIPS


def extract_concise_error(stderr_text: str) -> str:
    if not stderr_text:
        return "Unknown error (empty stderr)"

    lines = stderr_text.strip().splitlines()
    if not lines:
        return "Unknown error (empty stderr lines)"

    result = re.findall(r'Error\s(.*?)\n', stderr_text)
    if not result:
        return " ".join(lines[-10:])
    return " ".join(result)


def runffmpeg(arg, *, noextname=None, force_cpu=True, cmd_dir=None):
    """
    执行 ffmpeg 命令
    """
    if settings.get('force_lib'):
        force_cpu = True

    final_args = arg

    cmd = ['ffmpeg', "-hide_banner", "-nostdin", "-ignore_unknown", '-threads', '0']
    if "-y" not in final_args:
        cmd.append("-y")
    cmd.extend(final_args)

    if cmd and Path(cmd[-1]).suffix:
        cmd[-1] = Path(cmd[-1]).as_posix()

    if settings.get('ffmpeg_cmd'):
        custom_params = [p for p in settings.get('ffmpeg_cmd', '').split(' ') if p]
        cmd = cmd[:-1] + custom_params + cmd[-1:]

    try:
        if app_cfg.exit_soft:
            return
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors='replace',
            check=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            cwd=cmd_dir
        )
        if noextname:
            app_cfg.queue_novice[noextname] = "end"
        return True
    except FileNotFoundError as e:
        logger.error(f"命令未找到: {cmd[0]}。请确保 ffmpeg 已安装并在系统 PATH 中。")
        if noextname:
            app_cfg.queue_novice[noextname] = f"error:{e}"
        raise
    except subprocess.CalledProcessError as e:
        error_message = e.stderr or ""
        logger.error(f"FFmpeg 命令执行失败 (force_cpu={force_cpu})。\n命令: {' '.join(cmd)}\n错误: {error_message} {e.stdout}")
        err = extract_concise_error(e.stderr)
        if noextname:
            app_cfg.queue_novice[noextname] = f"error:{err}"
        # 针对win上路径和名称问题单独提示
        if sys.platform == 'win32' and 'No such file or directory' in str(e):
            _err = get_filepath_from_cmd(cmd)
            err = _err or err
        from videotrans.configure.excepts import FFmpegError
        raise FFmpegError(err) from e
    except Exception as e:
        if noextname:
            app_cfg.queue_novice[noextname] = f"error:{e}"
        logger.error(f"执行 ffmpeg 时发生未知错误,{cmd=}:\n{e}")
        raise


# 从 cmd 列表中获取 -i 之后的路径和 最后一个路径，以判断文件名是否规则，

def get_filepath_from_cmd(cmd: list):
    file_list = [cmd[i + 1] for i, param in enumerate(cmd) if param == '-i']
    file_list.append(cmd[-1])
    special = ['"', "'", "`", "*", "?", ":", ">", "<", "|", "\n", "\r"]
    for file in file_list:
        if len(file) >= 255:
            return tr(
                'The file path and file name may be too long. Please move the file to a flat and short directory and rename the file to a shorter name, ensuring that the length from the drive letter to the end of the file name does not exceed 255 characters: {},For example D:/videotrans/1.mp4 D:/videotrans/2.wav',
                file)
        for flag in special:
            if flag in file:
                return tr(
                    'There may be special characters in the file name or path. Please move the file to a simple directory consisting of English and numerical characters, rename the file to a simple name, and try again to avoid errors: {},For example D:/videotrans/1.mp4 D:/videotrans/2.wav',
                    file)
    return None


def check_hw_on_start(_compat=None):
    get_video_codec(264)
    get_video_codec(265)


def get_video_codec(compat=None) -> str:
    """
    通过测试确定最佳可用的硬件加速 H.264/H.265 编码器。

    根据平台优先选择硬件编码器。如果硬件测试失败，则回退到软件编码。
    结果会被缓存。此版本通过数据驱动设计和提前检查来优化结构和效率。

    依赖 'config' 模块获取设置和路径。假设 'ffmpeg' 在系统 PATH 中，
    测试输入文件存在，并且 TEMP_DIR 可写。


    Returns:
        str: 推荐的 ffmpeg 视频编码器名称 (例如 'h264_nvenc', 'libx264')。
    """
    import torch
    _codec_cache = app_cfg.codec_cache  # 使用 config 中的缓存
    try:
        if not _codec_cache and Path(f'{ROOT_DIR}/videotrans/codec.json').exists():
            _codec_cache = json.loads(Path(f'{ROOT_DIR}/videotrans/codec.json').read_text(encoding='utf-8-sig'))
    except Exception as e:
        logger.error(f'parse codec.json error:{e}')

    plat = platform.system()
    if compat and compat in [264, 265]:
        video_codec_pref = compat
    else:
        try:
            video_codec_pref = int(settings.get('video_codec', 264))
        except (ValueError, TypeError):
            logger.warning("配置中 'video_codec' 无效。将默认使用 H.264 (264)。")
            video_codec_pref = 264

    cache_key = f'{plat}-{video_codec_pref}'
    if cache_key in _codec_cache:
        logger.debug(f"返回缓存的编解码器 {cache_key}: {_codec_cache[cache_key]}")
        return _codec_cache[cache_key]

    h_prefix, default_codec = ('hevc', 'libx265') if video_codec_pref == 265 else ('h264', 'libx264')
    if video_codec_pref not in [264, 265]:
        logger.warning(f"未预期的 video_codec 值 '{video_codec_pref}'。将视为 H.264 处理。")

    ENCODER_PRIORITY = {
        'Darwin': ['videotoolbox'],
        'Windows': ['nvenc', 'qsv', 'amf'],
        'Linux': ['nvenc', 'vaapi', 'qsv']
    }

    try:
        test_input_file = Path(ROOT_DIR) / "videotrans/styles/no-remove.mp4"
        temp_dir = Path(config.TEMP_DIR)
    except Exception as e:
        logger.warning(f"准备测试硬件编码器时出错: {e}。将使用软件编码 {default_codec}。")
        _codec_cache[cache_key] = default_codec
        return default_codec

    def test_encoder_internal(encoder_to_test: str, timeout: int = 10) -> bool:
        timestamp = int(time.time() * 1000)
        output_file = temp_dir / f"test_{encoder_to_test}_{timestamp}.mp4"
        command = [
            "ffmpeg", "-y", "-hide_banner",
            "-t", "1", "-i", str(test_input_file),
            "-c:v", encoder_to_test, "-f", "mp4", str(output_file)
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

        logger.debug(f"正在测试编码器是否可用: {encoder_to_test}...")
        success = False
        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True,
                encoding='utf-8', errors='ignore', creationflags=creationflags, timeout=timeout
            )
            logger.debug(f"硬件编码器 '{encoder_to_test}' 可用。")
            success = True
        except FileNotFoundError:
            logger.error("'ffmpeg' 命令在 PATH 中未找到。无法进行编码器测试。")
            raise  # 重新抛出异常，让上层逻辑捕获并终止测试
        except subprocess.CalledProcessError:
            logger.warning(f"硬件编码器 '{encoder_to_test}' 不可用")
            raise
        except PermissionError:
            logger.warning(f"测试硬件编码器时失败:写入 {output_file} 时权限被拒绝。 {command=}")
            raise
        except subprocess.TimeoutExpired:
            logger.warning(f"硬件编码器 '{encoder_to_test}' 测试在 {timeout} 秒后超时。{command=}")
            raise
        except Exception as e:
            logger.warning(f"测试硬件编码器 {encoder_to_test} 时发生意外错误: {e} {command=}")
            raise
        finally:
            try:
                if output_file.exists():
                    output_file.unlink(missing_ok=True)
            except OSError:
                pass
            return success

    selected_codec = default_codec  # 初始化为回退选项

    encoders_to_test = ENCODER_PRIORITY.get(plat, [])
    if not encoders_to_test:
        logger.debug(f"不支持的平台: {plat}。将使用软件编码器 {default_codec}。")
    else:
        logger.debug(f"平台: {plat}。正在按优先级检测最佳的 '{h_prefix}' 编码器: {encoders_to_test}")
        try:
            for encoder_suffix in encoders_to_test:
                if encoder_suffix == 'nvenc':
                    try:
                        if not torch.cuda.is_available():
                            logger.debug("CUDA 不可用，跳过 nvenc 测试。")
                            continue  # 跳过当前循环，测试下一个编码器
                    except ImportError:
                        logger.error("未找到 torch 模块，将直接尝试 nvenc 测试。")

                full_encoder_name = f"{h_prefix}_{encoder_suffix}"
                if test_encoder_internal(full_encoder_name):
                    selected_codec = full_encoder_name
                    logger.debug(f"已选择硬件编码器: {selected_codec}")
                    break
            else:  # for-else 循环正常结束 (没有 break)
                logger.debug(f"所有硬件加速器均未通过测试。将使用软件编码器: {selected_codec}")

            _codec_cache[cache_key] = selected_codec
            # 保存缓存到本地
            Path(f"{ROOT_DIR}/videotrans/codec.json").write_text(json.dumps(_codec_cache))
        except Exception as e:
            # 发生异常不缓存
            logger.exception(f"在编码器测试期间发生意外，将使用软件编码: {e}", exc_info=True)
            selected_codec = default_codec
    # 
    _codec_cache[cache_key] = selected_codec

    logger.debug(f"最终确定使用的编码器: {selected_codec}")
    return selected_codec


def _run_ffprobe_internal(cmd: list[str]) -> str:
    """
    (内部函数) 执行 ffprobe 命令并返回其标准输出。
    """
    # 确保文件路径参数已转换为 POSIX 风格字符串，以获得更好的兼容性
    from videotrans.configure.excepts import FFmpegError
    if Path(cmd[-1]).is_file():
        cmd[-1] = Path(cmd[-1]).as_posix()

    command = ['ffprobe'] + [str(arg) for arg in cmd]
    try:
        p = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors='replace',
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        return p.stdout.strip()
    except FileNotFoundError as e:
        raise FFmpegError("Command not found: ffmpeg. Ensure FFmpeg is installed and in your PATH.") from e
    except subprocess.CalledProcessError as e:
        concise_error = extract_concise_error(e.stderr)
        logger.exception(f"ffprobe command failed: {concise_error}", exc_info=True)
        raise FFmpegError(concise_error) from e
    except (PermissionError, OSError) as e:
        logger.exception(e, exc_info=True)
        raise FFmpegError(e) from e


def runffprobe(cmd):
    stdout_result = _run_ffprobe_internal(cmd)
    if stdout_result:
        return stdout_result
    from videotrans.configure.excepts import FFmpegError
    raise FFmpegError(f"ffprobe ran successfully but produced no output. {cmd=}")


def get_video_info(mp4_file, *, video_fps=False, video_scale=False, video_time=False, get_codec=False):
    """
    获取视频信息。
    """
    from videotrans.configure.excepts import FFmpegError
    if not Path(mp4_file).exists():
        raise Exception(f'{mp4_file} is not exists')
    out_json = runffprobe(
        ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mp4_file]
    )
    if not out_json:
        raise FFmpegError(
            tr('Failed to parse {} information, please confirm that the file can be played normally', mp4_file))

    try:
        out = json.loads(out_json)
    except json.JSONDecodeError as e:
        raise FFmpegError(
            tr('Failed to parse {} information, please confirm that the file can be played normally', mp4_file)) from e

    if "streams" not in out or not out["streams"]:
        raise FFmpegError(
            tr('The original file {} does not contain any audio or video data. The file may be damaged. Please confirm that the file can be played.',
               mp4_file))

    result = {
        "video_fps": 30,
        "r_frame_rate": 30,
        "video_codec_name": "",
        "audio_codec_name": "",
        "width": 0,
        "height": 0,
        "time": 0,
        "streams_len": len(out['streams']),
        "streams_audio": 0,
        "video_streams": 0,
        "color": "yuv420p"
    }
    try:
        # 以第一个流中duration为准，但可能某些格式，例如mkv第一个流中无duration字段或始终为0
        _duration = out['streams'][0].get('duration', 'DURATION')
        # mp4 是  \d.\d 秒形式
        if re.match(r'^\d+(\.\d+)?$', _duration):
            result['time'] = int(float(_duration) * 1000)  # 第一个流的长度为准
        elif re.match(r'^\d+:', _duration):
            # 其他视频格式可能是 00:01:00.445
            _t = _duration.split('.')
            _s = float(f'0.{_t[1]}' if len(_t) >= 2 else 0)
            _tstr = _t[0].split(':')
            _s += float(_tstr[-1])
            if len(_tstr) >= 2:
                _s += float(_tstr[-2]) * 60
            if len(_tstr) >= 3:
                _s += float(_tstr[-3]) * 3600

            result['time'] = int(_s * 1000)
        else:
            result['time'] = int(float(out['format']['duration']) * 1000)
    except Exception as e:
        result['time'] = int(float(out['format']['duration']) * 1000)
        logger.exception(e, exc_info=True)

    video_stream = next((s for s in out['streams'] if s.get('codec_type') == 'video'), None)
    audio_streams = [s for s in out['streams'] if s.get('codec_type') == 'audio']

    result['streams_audio'] = len(audio_streams)
    if audio_streams:
        result['audio_codec_name'] = audio_streams[0].get('codec_name', "")

    if video_stream:
        result['video_streams'] = 1
        result['video_codec_name'] = video_stream.get('codec_name', "")
        result['width'] = int(video_stream.get('width', 0))
        result['height'] = int(video_stream.get('height', 0))
        result['color'] = video_stream.get('pix_fmt', 'yuv420p').lower()

        # FPS 计算逻辑
        def parse_fps(rate_str):
            try:
                _fps_split=str(rate_str).split('/')
                if len(_fps_split)==2:
                    num, den = map(int, _fps_split)
                    return num / den if den != 0 else 0
                
                return float(rate_str)
            except (TypeError,ValueError):
                return 0

        fps1 = parse_fps(video_stream.get('r_frame_rate'))

        if not fps1 or fps1 < 1:
            fps_avg = parse_fps(video_stream.get('avg_frame_rate'))
        else:
            fps_avg = fps1

        result['r_frame_rate']=result['video_fps'] = fps_avg if 1 <= fps_avg <= 120 else 30

    logger.debug(f'The file info after process:{result=}')
    # 确保向后兼容
    if video_time:
        return result['time']
    if video_fps:
        return result['video_fps']
    if video_scale:
        return result['width'], result['height']
    if get_codec:
        return result['video_codec_name'], result['audio_codec_name']

    return result


def _get_ms_from_media(file):
    ms = 0
    ext = Path(file).suffix.lower()[1:]
    try:
        if ext in contants.VIDEO_EXTS:
            ms = int(float(runffprobe(
                ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration', '-of',
                 'default=noprint_wrappers=1:nokey=1', file])) * 1000)
        elif ext in contants.AUDIO_EXITS:
            ms = int(float(runffprobe(
                ['-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=duration', '-of',
                 'default=noprint_wrappers=1:nokey=1', file])) * 1000)
    except Exception as e:
        # mkv 等其他格式可能无法从流中读取 duration
        logger.exception(f'无法从视频或音频流中获取时长:{file=},{e}', exc_info=True)

    if ms == 0:
        try:
            ms = int(float(runffprobe(
            ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file]))*1000)
        except Exception as e:
            logger.error(f'再次从 format=duration 中读取失败 {e}')
    return ms


# 获取无音频的视频流时长
def get_video_ms_noaudio(mp4):
    return _get_ms_from_media(mp4)


# 获取某个视频的时长 ms
def get_video_duration(file_path):
    return _get_ms_from_media(file_path)


# 获取音频时长 返回ms
def get_audio_time(audio_file):
    return _get_ms_from_media(audio_file)


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
    """
    创建供FFmpeg concat使用的连接文件。
    确保写入的是绝对路径，以避免FFmpeg因工作目录问题找不到文件。
    """
    txt = []
    for it in filelist:
        path_obj = Path(it)
        if not path_obj.exists() or path_obj.stat().st_size == 0:
            continue
        # 存放名字，避免片段过多在windows上出现命令行截断错误
        txt.append(f"file '{path_obj.name}'")
    if not txt:
        # 如果没有有效文件，创建一个空的concat文件可能导致错误，不如直接抛出异常
        raise RuntimeError("Cannot create concat txt from an empty or invalid file list.")

    with open(concat_txt, 'w', encoding='utf-8') as f:
        f.write("\n".join(txt))
    return concat_txt


# 多个音频片段连接
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


# 目前仅用于 视频翻译后，延长背景音
def change_speed_rubberband(input_path:str, out_file:str, target_duration:Union[float,int]):
    """
    使用 Rubber Band 进行音频变速
    """
    try:
        import pyrubberband as pyrb
    except Exception:
        logger.warning(f'进行音频变速时失败，因为未安装  rubberband 库，使用 ffmpeg 进行变速处理\n{INSTALL_RUBBERBAND_TIPS}')
        return precise_speed_up_audio(file_path=input_path, out=out_file, target_duration_ms=target_duration)

    import soundfile as sf
    import numpy as np  # 新增 numpy 用于声道处理
    try:
        y, sr = sf.read(input_path)
        if len(y) == 0:
            logger.warning(f"[Audio-RB] 空音频文件: {input_path}")
            return

        current_duration = int((len(y) / sr) * 1000)

        if target_duration <= 0: target_duration = 1

        time_stretch_rate = current_duration / target_duration

        # 限制范围
        time_stretch_rate = max(0.2, min(time_stretch_rate, 50.0))

        logger.debug(
            f"[Audio-RB] {input_path} 原长:{current_duration}ms -> 目标:{target_duration}ms 倍率:{time_stretch_rate:.2f}")

        y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)

        # 如果是单声道 (ndim=1)，复制为双声道
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

    # 完成使用 atempo 滤镜加速
    # 构造 atempo 滤镜链
    # atempo 限制：参数必须在 [0.5, 2.0] 之间
    atempo_list = []
    speed_factor = current_duration_ms / target_duration_ms

    # 处理加速情况 (> 2.0)
    while speed_factor > 2.0:
        atempo_list.append("atempo=2.0")
        speed_factor /= 2.0

    # 放入剩余的倍率
    atempo_list.append(f"atempo={speed_factor}")

    # 用逗号连接滤镜，形成串联效果，如 "atempo=2.0,atempo=1.5"
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
        '-t', f"{target_duration_ms / 1000.0}",  # 强制裁剪到目标时长，防止精度误差
        '-ar', "48000",
        '-ac', "2",
        '-c:a', codecs.get(out_ext, 'pcm_s16le'),
        out
    ]
    try:
        runffmpeg(cmd, force_cpu=True)
    except Exception as e:
        logger.exception(f'音频加速失败:{e}')


# 从音频中截取一个片段
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


def send_notification(title, message):
    if app_cfg.exec_mode == 'cli':
        print(f'\n*****[{title}]: {message}*****\n')
        return
    if app_cfg.exit_soft or settings.get('dont_notify', False):
        return
    from plyer import notification
    try:
        notification.notify(
            title=title[:60],
            message=message[:120],
            ticker="pyVideoTrans",
            app_name="pyVideoTrans",
            app_icon=ROOT_DIR + '/videotrans/styles/icon.ico',
            timeout=10  # Display duration in seconds
        )
    except Exception:
        pass


# rm_start 是否也移除开头的静音片段
def remove_silence_wav(audio_file:str, rm_start=True)->bool:
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent

    audio = AudioSegment.from_file(audio_file, format="wav")

    # TTS的静音通常非常干净 如果背景仍有细微底噪，可调高
    silence_threshold = audio.dBFS - 20

    # 只要静音持续 100ms 以上就检测出来
    min_silence_len = 100

    # 3. 检测非静音片段
    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_threshold,
        seek_step=10
    )

    # 4. 处理剪切逻辑
    if len(nonsilent_chunks) > 0:
        # 在检测到的非静音首尾，额外保留 100 毫秒的声音，防止吞掉弱辅音或尾音
        head_padding_ms = 80  # 头部保留80毫秒
        tail_padding_ms = 200  # 尾音通常拖得比较长，保留200毫秒

        # 获取第一个非静音块的开始时间
        raw_start = nonsilent_chunks[0][0]
        # 获取最后一个非静音块的结束时间
        raw_end = nonsilent_chunks[-1][1]

        # 计算最终裁剪位置，使用 max 和 min 防止索引超出音频总长度
        start_trim = max(0, raw_start - head_padding_ms) if rm_start else 0
        end_trim = min(len(audio), raw_end + tail_padding_ms)

        # 裁剪音频
        trimmed_audio = audio[start_trim:end_trim]
        trimmed_audio.export(audio_file, format="wav")
        return True

    return False  # 如果全是静音，返回False


def format_video(name:Union[str,os.PathLike], target_dir:str=None)->InputFile:
    from . import help_misc
    raw_pathlib = Path(name)
    # 原始基本名字,例如 `1.mp4`
    raw_basename = raw_pathlib.name
    # 无后缀的基本名字，例如 `1`
    raw_noextname = raw_pathlib.stem
    # 后缀，如 `.mp4`
    ext = raw_pathlib.suffix.lower()[1:]
    # 所在目录
    raw_dirname = raw_pathlib.parent.resolve().as_posix()

    obj = InputFile(
        # 原始文件名含完整路径，如 F:/python/1.mp4
        name=name,
        # 原始所在目录 如 F:/python
        dirname=raw_dirname,
        # 基本名带后缀 如 1.mp4
        basename=raw_basename,
        # 基本名不带后缀,如 1
        noextname=raw_noextname,
        # 扩展名去掉点.  如 mp4
        ext=ext
        # 最终存放目标位置，直接存到这里
    )

    # 如果存在目标文件夹，则在其之下生成 以无后缀的基本名的子文件夹
    if target_dir:
        obj.target_dir = Path(f'{target_dir}/{raw_noextname}-{ext}').as_posix()
    # 唯一id标识 改为使用 名字和尺寸 和 mtime，以便使用缓存 
    _stat = raw_pathlib.stat()
    obj.uuid = help_misc.get_md5(f'{name}-{_stat.st_size}-{_stat.st_mtime}')[:10]
    return obj
