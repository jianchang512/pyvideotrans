import copy
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


def extract_concise_error(stderr_text: str, max_lines=3, max_length=250) -> str:
    """
    Tries to extract a concise, relevant error message from stderr,
    often focusing on the last few lines or lines with error keywords.

    Args:
        stderr_text: The full stderr output string.
        max_lines: How many lines from the end to primarily consider.
        max_length: Max length of the returned string snippet.

    Returns:
        A concise string representing the likely error.
    """
    if not stderr_text:
        return "Unknown error (empty stderr)"

    lines = stderr_text.strip().splitlines()
    if not lines:
        return "Unknown error (empty stderr lines)"

    # Look for lines with common error keywords in the last few lines
    error_keywords = ["error", "invalid", "fail", "could not", "no such",
                      "denied", "unsupported", "unable", "can't open", "conversion failed"]

    relevant_lines_indices = range(max(0, len(lines) - max_lines), len(lines))

    found_error_lines = []
    for i in reversed(relevant_lines_indices):
        line = lines[i].strip()
        if not line:  # Skip empty lines
            continue

        # Check if the line contains any of the keywords (case-insensitive)
        if any(keyword in line.lower() for keyword in error_keywords):
            # Prepend the previous line if it exists and isn't empty, might add context
            context_line = ""
            if i > 0 and lines[i - 1].strip():
                context_line = lines[i - 1].strip() + "\n"  # Add newline for clarity

            found_error_lines.append(context_line + line)
            # Often, the first keyword line found (reading backwards) is the most specific
            break

    if found_error_lines:
        # Take the first one found (which was likely the last 'errorry' line in the output)
        concise_error = found_error_lines[0]
    else:
        # Fallback: take the last non-empty line if no keywords found
        last_non_empty_line = ""
        for line in reversed(lines):
            stripped_line = line.strip()
            if stripped_line:
                last_non_empty_line = stripped_line
                break
        concise_error = last_non_empty_line or "Unknown error (no specific error line found)"

    # Limit the total length
    if len(concise_error) > max_length:
        return concise_error[:max_length] + "..."
    return concise_error


def _get_preset_classification(preset: str) -> str:
    """将 libx264/x265 的 preset 归类为 'fast', 'medium', 'slow'。"""
    SOFTWARE_PRESET_CLASSIFICATION = {
        'ultrafast': 'fast', 'superfast': 'fast', 'veryfast': 'fast',
        'faster': 'fast', 'fast': 'fast',
        'medium': 'medium',
        'slow': 'slow', 'slower': 'slow', 'veryslow': 'slow',
    }
    return SOFTWARE_PRESET_CLASSIFICATION.get(preset, 'medium')  # 默认为 medium


def _translate_crf_to_hw_quality(crf_value: str, encoder_family: str) -> int | None:
    """
    将 CRF 值近似转换为不同硬件编码器的质量值。
    这是一个经验性转换，并非精确等效。
    """
    try:
        crf = int(crf_value)
        # 经验范围：CRF 越低，质量越高。
        # NVENC CQ/QP, QSV global_quality 范围 ~1-51，推荐 20-28，其值与CRF的体感接近。
        if encoder_family in ['nvenc', 'qsv', 'vaapi']:
            # 对于这些编码器，质量值与 CRF 值大致在同一数量级
            # 简单地将值限制在合理范围内
            return max(1, min(crf, 51))
        # 其他编码器（如 AMF）的质量参数不同，后续再说
        # videotoolbox 使用 -q:v 0-100，暂不转换
    except (ValueError, TypeError):
        return None
    return None


def _build_hw_command(args: list, hw_codec: str):
    from videotrans.configure import config
    """
    根据选择的硬件编码器，构建 ffmpeg 命令参数列表和硬件解码选项

    此函数是纯粹的，它不修改输入列表，而是返回一个新的列表。
    """
    if not hw_codec or 'libx' in hw_codec:
        return args, []

    encoder_family = hw_codec.split('_')[-1]

    # --- 参数映射表 ---
    PRESET_MAP = {
        'nvenc': {'fast': 'p1', 'medium': 'p4', 'slow': 'p7'},  # p1-p7: fastest to slowest
        'qsv': {'fast': 'veryfast', 'medium': 'medium', 'slow': 'veryslow'},
        'vaapi': {'fast': 'veryfast', 'medium': 'medium', 'slow': 'veryslow'},
        'amf': {'fast': 'speed', 'medium': 'balanced', 'slow': 'quality'},
    }

    # 定义硬件质量参数的名称
    QUALITY_PARAM_MAP = {
        'nvenc': '-cq',
        'qsv': '-global_quality',
        'vaapi': '-global_quality',
    }

    new_args = []
    hw_decode_opts = []

    i = 0
    main_input_file = ""
    while i < len(args):
        arg = args[i]

        if arg == '-i' and not main_input_file and i + 1 < len(args):
            main_input_file = args[i + 1]

        # 1. 替换视频编码器
        if arg == '-c:v' and i + 1 < len(args):
            if args[i + 1] != 'copy':
                new_args.extend(['-c:v', hw_codec])
            else:
                new_args.extend(['-c:v', 'copy'])
            i += 2
            continue

        # 2. 调整 preset 参数 (使用分类)
        if arg == '-preset' and i + 1 < len(args):
            family_presets = PRESET_MAP.get(encoder_family)
            if family_presets:
                classification = _get_preset_classification(args[i + 1])
                new_preset = family_presets.get(classification)
                if new_preset:
                    new_args.extend(['-preset', new_preset])
            i += 2
            continue

        # 3. 替换 -crf 参数
        if arg == '-crf' and i + 1 < len(args):
            hw_quality_param = QUALITY_PARAM_MAP.get(encoder_family)
            if hw_quality_param:
                crf_value = args[i + 1]
                hw_quality_value = _translate_crf_to_hw_quality(crf_value, encoder_family)
                if hw_quality_value is not None:
                    # config.logger.info(f"将 -crf {crf_value} 替换为硬件参数 {hw_quality_param} {hw_quality_value}")
                    new_args.extend([hw_quality_param, str(hw_quality_value)])
                else:
                    config.logger.error(f"无法转换 -crf {crf_value} 的值，将忽略此质量参数。")
            else:
                config.logger.error(f"编码器 {encoder_family} 不支持CRF到硬件质量参数的自动替换，将忽略 -crf。")
            i += 2
            continue

        new_args.append(arg)
        i += 1

    # --- 硬件解码逻辑 ---
    output_file = new_args[-1] if new_args else ""
    is_output_mp4 = isinstance(output_file, str) and output_file.lower().endswith('.mp4')
    is_input_media = isinstance(main_input_file, str) and main_input_file.lower().endswith(
        ('.mp4', '.mkv', '.mov', '.ts', '.txt'))

    # 无字幕嵌入时可尝试硬件解码
    # 有字幕或 -vf 滤镜时不使用，容易出错且需要上传下载数据
    if "-c:s" not in new_args and "-vf" not in new_args and is_input_media and is_output_mp4 and config.settings.get(
            'cuda_decode', False):
        if encoder_family == 'nvenc':
            hw_decode_opts = ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
            # config.logger.info("启用 CUDA 硬件解码。")
        elif encoder_family == 'qsv':
            hw_decode_opts = ['-hwaccel', 'qsv', '-hwaccel_output_format', 'qsv']
            # config.logger.info("启用 QSV 硬件解码。")
        elif encoder_family == 'videotoolbox':
            hw_decode_opts = ['-hwaccel', 'videotoolbox']
            # config.logger.info("启用 VideoToolbox 硬件解码。")

    return new_args, hw_decode_opts


def runffmpeg(arg, *, noextname=None, uuid=None, force_cpu=False):
    """
    执行 ffmpeg 命令，智能应用硬件加速并处理平台兼容性。

    如果硬件加速失败，会自动回退到 CPU 编码重试。

    Args:
        arg (list): ffmpeg 参数列表。
        noextname (str, optional): 用于任务队列跟踪的标识符。
        uuid (str, optional): 用于进度更新的 UUID。
        force_cpu (bool): 如果为 True，则强制使用 CPU 编码，不尝试硬件加速。
    """
    from videotrans.configure import config
    arg_copy = copy.deepcopy(arg)

    default_codec = f"libx{config.settings.get('video_codec', '264')}"

    final_args = arg
    hw_decode_opts = []

    # 如果 crf < 10 则直接强制使用软编码
    if "-crf" in final_args and final_args[-1].endswith(".mp4"):
        crf_index = final_args.index("-crf")
        if int(final_args[crf_index + 1]) <= 10:
            force_cpu = True
            if "-preset" in final_args:
                preset_index = final_args.index("-preset")
                final_args[preset_index + 1] = 'ultrafast'
            else:
                final_args.insert(-1, "-preset")
                final_args.insert(-1, "ultrafast")

    if not force_cpu:
        if not hasattr(config, 'video_codec') or not config.video_codec:
            config.video_codec = get_video_codec()

        if config.video_codec and 'libx' not in config.video_codec:
            # config.logger.info(f"检测到硬件编码器 {config.video_codec}，正在调整参数...")
            final_args, hw_decode_opts = _build_hw_command(arg, config.video_codec)
        else:
            config.logger.info("未找到或未选择硬件编码器，将使用软件编码。")

    cmd = [config.FFMPEG_BIN, "-hide_banner", "-ignore_unknown"]
    if "-y" not in final_args:
        cmd.append("-y")
    cmd.extend(hw_decode_opts)
    cmd.extend(final_args)

    if cmd and Path(cmd[-1]).suffix:
        try:
            cmd[-1] = Path(cmd[-1]).as_posix()
        except Exception:
            pass

    if config.settings.get('ffmpeg_cmd'):
        custom_params = [p for p in config.settings['ffmpeg_cmd'].split(' ') if p]
        cmd = cmd[:-1] + custom_params + cmd[-1:]

    if noextname:
        config.queue_novice[noextname] = 'ing'

    try:
        # config.logger.info(f"执行 FFmpeg 命令 (force_cpu={force_cpu}): {' '.join(cmd)}")

        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW

        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors='replace',
            check=True,
            text=True,
            creationflags=creationflags
        )
        if noextname:
            config.queue_novice[noextname] = "end"
        return True

    except FileNotFoundError:
        config.logger.error(f"命令未找到: {cmd[0]}。请确保 ffmpeg 已安装并在系统 PATH 中。")
        if noextname: config.queue_novice[noextname] = "error"
        raise

    except subprocess.CalledProcessError as e:
        error_message = e.stderr or "(无 stderr 输出)"
        config.logger.error(f"FFmpeg 命令执行失败 (force_cpu={force_cpu})。\n命令: {' '.join(cmd)}\n错误: {error_message}")

        is_video_output = cmd[-1].lower().endswith('.mp4')
        if not force_cpu and is_video_output:
            config.logger.warning("硬件加速失败，将自动回退到 CPU 编码重试...")

            fallback_args = []
            i = 0
            while i < len(arg_copy):
                if arg_copy[i] == '-c:v' and i + 1 < len(arg_copy) and arg_copy[i + 1] != 'copy':
                    fallback_args.extend(['-c:v', default_codec])
                    i += 2
                else:
                    fallback_args.append(arg_copy[i])
                    i += 1

            return runffmpeg(fallback_args, noextname=noextname, uuid=uuid, force_cpu=True)

        if noextname: config.queue_novice[noextname] = "error"
        raise RuntimeError(extract_concise_error(e.stderr))

    except Exception as e:
        if noextname: config.queue_novice[noextname] = "error"
        config.logger.exception(f"执行 ffmpeg 时发生未知错误 (force_cpu={force_cpu})。")
        raise


def get_video_codec(force_test: bool = False) -> str:
    """
    通过测试确定最佳可用的硬件加速 H.264/H.265 编码器。

    根据平台优先选择硬件编码器。如果硬件测试失败，则回退到软件编码。
    结果会被缓存。此版本通过数据驱动设计和提前检查来优化结构和效率。

    依赖 'config' 模块获取设置和路径。假设 'ffmpeg' 在系统 PATH 中，
    测试输入文件存在，并且 TEMP_DIR 可写。

    Args:
        force_test (bool): 如果为 True，则忽略缓存并重新运行测试。默认为 False。

    Returns:
        str: 推荐的 ffmpeg 视频编码器名称 (例如 'h264_nvenc', 'libx264')。
    """
    from videotrans.configure import config
    _codec_cache = config.codec_cache  # 使用 config 中的缓存

    plat = platform.system()
    try:
        video_codec_pref = int(config.settings.get('video_codec', 264))
    except (ValueError, TypeError):
        config.logger.warning("配置中 'video_codec' 无效。将默认使用 H.264 (264)。")
        video_codec_pref = 264

    cache_key = (plat, video_codec_pref)
    if not force_test and cache_key in _codec_cache:
        config.logger.info(f"返回缓存的编解码器 {cache_key}: {_codec_cache[cache_key]}")
        return _codec_cache[cache_key]

    h_prefix, default_codec = ('hevc', 'libx265') if video_codec_pref == 265 else ('h264', 'libx264')
    if video_codec_pref not in [264, 265]:
        config.logger.warning(f"未预期的 video_codec 值 '{video_codec_pref}'。将视为 H.264 处理。")

    ENCODER_PRIORITY = {
        'Darwin': ['videotoolbox'],
        'Windows': ['nvenc', 'qsv', 'amf'],
        'Linux': ['nvenc', 'vaapi', 'qsv']
    }

    try:
        test_input_file = Path(config.ROOT_DIR) / "videotrans/styles/no-remove.mp4"
        temp_dir = Path(config.TEMP_DIR)
    except Exception as e:
        config.logger.error(f"从配置构建路径时出错: {e}。将回退到 {default_codec}。")
        _codec_cache[cache_key] = default_codec
        return default_codec

    def test_encoder_internal(encoder_to_test: str, timeout: int = 20) -> bool:
        timestamp = int(time.time() * 1000)
        output_file = temp_dir / f"test_{encoder_to_test}_{timestamp}.mp4"
        command = [
            "ffmpeg", "-y", "-hide_banner",
            "-t", "1", "-i", str(test_input_file),
            "-c:v", encoder_to_test, "-f", "mp4", str(output_file)
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

        config.logger.info(f"正在尝试测试编码器: {encoder_to_test}...")
        success = False
        try:
            process = subprocess.run(
                command, check=True, capture_output=True, text=True,
                encoding='utf-8', errors='ignore', creationflags=creationflags, timeout=timeout
            )
            config.logger.info(f"成功: 编码器 '{encoder_to_test}' 测试通过。")
            success = True
        except FileNotFoundError:
            config.logger.error("'ffmpeg' 命令在 PATH 中未找到。无法进行编码器测试。")
            raise  # 重新抛出异常，让上层逻辑捕获并终止测试
        except subprocess.CalledProcessError as e:
            config.logger.warning(f"失败: 编码器 '{encoder_to_test}' 测试失败。FFmpeg 返回码: {e.returncode}")
            # 只在有 stderr 时记录，避免日志混乱
            # if e.stderr and e.stderr.strip():
            #    config.logger.warning(f"FFmpeg stderr:\n{e.stderr.strip()}")
        except PermissionError:
            config.logger.error(f"失败: 写入 {output_file} 时权限被拒绝。 {command=}")
        except subprocess.TimeoutExpired:
            config.logger.warning(f"失败: 编码器 '{encoder_to_test}' 测试在 {timeout} 秒后超时。{command=}")
        except Exception as e:
            config.logger.error(f"失败: 测试编码器 {encoder_to_test} 时发生意外错误: {e} {command=}", exc_info=True)
        finally:
            try:
                if output_file.exists():
                    output_file.unlink(missing_ok=True)
            except:
                pass
            return success

    selected_codec = default_codec  # 初始化为回退选项

    encoders_to_test = ENCODER_PRIORITY.get(plat, [])
    if not encoders_to_test:
        config.logger.info(f"不支持的平台: {plat}。将使用软件编码器 {default_codec}。")
    else:
        config.logger.info(f"平台: {plat}。正在按优先级检测最佳的 '{h_prefix}' 编码器: {encoders_to_test}")
        try:
            for encoder_suffix in encoders_to_test:
                # --- 优化点 3: 简化的 nvenc 预检查 ---
                if encoder_suffix == 'nvenc':
                    try:
                        import torch
                        if not torch.cuda.is_available():
                            config.logger.info("PyTorch 报告 CUDA 不可用，跳过 nvenc 测试。")
                            continue  # 跳过当前循环，测试下一个编码器
                    except ImportError:
                        # torch 未安装是正常情况，继续尝试测试 nvenc
                        config.logger.info("未找到 torch 模块，将直接尝试 nvenc 测试。")

                full_encoder_name = f"{h_prefix}_{encoder_suffix}"
                if test_encoder_internal(full_encoder_name):
                    selected_codec = full_encoder_name
                    config.logger.info(f"已选择硬件编码器: {selected_codec}")
                    break  # 找到第一个可用的，立即停止测试
            else:  # for-else 循环正常结束 (没有 break)
                config.logger.info(f"所有硬件加速器测试均失败。将使用软件编码器: {selected_codec}")

        except FileNotFoundError:
            config.logger.error(f"由于 'ffmpeg' 未找到，所有硬件加速测试已中止。")
            selected_codec = default_codec  # 确保回退
        except Exception as e:
            config.logger.error(f"在编码器测试期间发生意外错误: {e}", exc_info=True)
            selected_codec = default_codec

    # --- 最终结果 ---
    _codec_cache[cache_key] = selected_codec
    config.logger.info(f"最终确定的编码器: {selected_codec}")
    return selected_codec


class _FFprobeInternalError(Exception):
    """用于内部错误传递的自定义异常。"""
    pass


def _run_ffprobe_internal(cmd: list[str]) -> str:
    from videotrans.configure import config
    """
    (内部函数) 执行 ffprobe 命令并返回其标准输出。
    """
    # 确保文件路径参数已转换为 POSIX 风格字符串，以获得更好的兼容性
    if Path(cmd[-1]).is_file():
        cmd[-1] = Path(cmd[-1]).as_posix()

    command = [config.FFPROBE_BIN] + [str(arg) for arg in cmd]
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

    try:
        p = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors='replace',
            check=True,
            creationflags=creationflags
        )
        return p.stdout.strip()
    except FileNotFoundError as e:
        msg = f"Command not found: '{config.FFPROBE_BIN}'. Ensure FFmpeg is installed and in your PATH."
        config.logger.error(msg)
        raise _FFprobeInternalError(msg) from e
    except subprocess.CalledProcessError as e:
        concise_error = extract_concise_error(e.stderr)
        config.logger.error(f"ffprobe command failed: {concise_error}")
        raise _FFprobeInternalError(concise_error) from e
    except (PermissionError, OSError) as e:
        msg = f"OS error running ffprobe: {e}"
        config.logger.error(msg, exc_info=True)
        raise _FFprobeInternalError(msg) from e


def runffprobe(cmd):
    from videotrans.configure import config
    """
    (兼容性接口) 运行 ffprobe。
    """
    try:
        stdout_result = _run_ffprobe_internal(cmd)
        if stdout_result:
            return stdout_result

        # 如果 stdout 为空，但进程没有出错（不常见），则模拟旧的错误路径
        #  _run_ffprobe_internal 中，如果 stderr 有内容且返回码非0，
        # 会直接抛出异常，所以这段逻辑主要为了覆盖极端的边缘情况。
        config.logger.error("ffprobe ran successfully but produced no output.")
        raise Exception("ffprobe ran successfully but produced no output.")

    except _FFprobeInternalError as e:
        raise
    except Exception as e:
        # 捕获其他意料之外的错误并重新引发，保持行为一致
        config.logger.error(f"An unexpected error occurred in runffprobe: {e}", exc_info=True)
        raise


def get_video_info(mp4_file, *, video_fps=False, video_scale=False, video_time=False, get_codec=False):
    """
    (兼容性接口) 获取视频信息。
    """
    from videotrans.configure import config
    if not Path(mp4_file).exists():
        raise Exception(f'{mp4_file} is not exists')
    try:
        out_json = runffprobe(
            ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mp4_file]
        )
        if not out_json:
            raise Exception('ffprobe error: dont get video information')
    except Exception as e:
        # 确保抛出的异常与旧版本一致
        raise Exception(f'ffprobe error: {e}. {mp4_file=}') from e

    # 解析 JSON 并填充结果字典
    try:
        out = json.loads(out_json)
    except json.JSONDecodeError as e:
        raise Exception('ffprobe error: failed to parse JSON output') from e

    result = {
        "video_fps": 30,
        "video_codec_name": "",
        "audio_codec_name": "",
        "width": 0,
        "height": 0,
        "time": 0,
        "streams_len": 0,
        "streams_audio": 0,
        "color": "yuv420p"
    }

    if "streams" not in out or not out["streams"]:
        raise Exception('ffprobe error: streams is 0')

    result['streams_len'] = len(out['streams'])

    if "format" in out and out['format'].get('duration'):
        try:
            # 保持返回整数毫秒的逻辑
            result['time'] = int(float(out['format']['duration']) * 1000)
        except (ValueError, TypeError):
            config.logger.warning(f"Could not parse duration: {out['format'].get('duration')}")

    video_stream = next((s for s in out['streams'] if s.get('codec_type') == 'video'), None)
    audio_streams = [s for s in out['streams'] if s.get('codec_type') == 'audio']

    result['streams_audio'] = len(audio_streams)
    if audio_streams:
        result['audio_codec_name'] = audio_streams[0].get('codec_name', "")

    if video_stream:
        result['video_codec_name'] = video_stream.get('codec_name', "")
        result['width'] = int(video_stream.get('width', 0))
        result['height'] = int(video_stream.get('height', 0))
        result['color'] = video_stream.get('pix_fmt', 'yuv420p').lower()

        # FPS 计算逻辑
        def parse_fps(rate_str):
            try:
                num, den = map(int, rate_str.split('/'))
                return num / den if den != 0 else 0
            except (ValueError, ZeroDivisionError, AttributeError):
                return 0

        fps1 = parse_fps(video_stream.get('r_frame_rate'))
        fps_avg = parse_fps(video_stream.get('avg_frame_rate'))

        # 优先使用 avg_frame_rate
        final_fps = fps_avg if fps_avg != 0 else fps1

        # 保持旧的帧率范围限制
        result['video_fps'] = final_fps if 1 <= final_fps <= 60 else 30

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


# 获取某个视频的时长 ms
def get_video_duration(file_path):
    return get_video_info(file_path, video_time=True)


def conver_to_16k(audio, target_audio):
    return runffmpeg([
        "-y",
        "-i",
        Path(audio).as_posix(),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        Path(target_audio).as_posix(),
    ])


# wav转为 m4a cuda + h264_cuvid
def wav2m4a(wavfile, m4afile, extra=None):
    cmd = [
        "-y",
        "-i",
        Path(wavfile).as_posix(),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        Path(m4afile).as_posix()
    ]
    if extra:
        cmd = cmd[:3] + extra + cmd[3:]
    return runffmpeg(cmd)


def create_concat_txt(filelist, concat_txt=None):
    from videotrans.configure import config

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
        raise ValueError("Cannot create concat txt from an empty or invalid file list.")

    config.logger.info(f'{txt=},{concat_txt=},{filelist[0]=}')
    with open(concat_txt, 'w', encoding='utf-8') as f:
        f.write("\n".join(txt))
        f.flush()
    # 进入路径下
    os.chdir(os.path.dirname(concat_txt))
    return concat_txt


# 多个音频片段连接
def concat_multi_audio(*, out=None, concat_txt=None):
    if out:
        out = Path(out).as_posix()

    os.chdir(os.path.dirname(concat_txt))
    cmd = ['-y', '-f', 'concat', '-safe', '0', '-i', concat_txt, "-b:a", "128k"]
    if out.endswith('.m4a'):
        cmd += ['-c:a', 'aac']
    elif out.endswith('.wav'):
        cmd += ['-c:a', 'pcm_s16le']
    runffmpeg(cmd + [out])
    from videotrans.configure import config
    os.chdir(config.TEMP_DIR)
    return True


def precise_speed_up_audio(*, file_path=None, out=None, target_duration_ms=None):
    from pydub import AudioSegment
    ext = file_path[-3:]
    audio = AudioSegment.from_file(file_path, format='mp4' if ext == 'm4a' else ext)

    # 首先确保原时长和目标时长单位一致（毫秒）,缩短音频到 target_duration_ms
    current_duration_ms = len(audio)
    if not target_duration_ms or target_duration_ms <= 0 or current_duration_ms <= 0 or current_duration_ms <= target_duration_ms:
        return True
    from videotrans.configure import config
    temp_file = config.SYS_TMP + f'/{time.time_ns()}.{ext}'
    atempo = current_duration_ms / target_duration_ms
    if atempo <= 1:
        return True
    atempo = min(100, atempo)
    runffmpeg(["-i", file_path, "-filter:a", f"atempo={atempo}", temp_file])
    audio = AudioSegment.from_file(temp_file, format='mp4' if ext == 'm4a' else ext)
    diff = len(audio) - target_duration_ms
    if diff > 0:
        audio = audio[:-diff]
    if out:
        audio.export(out, format=ext)
        return True
    audio.export(file_path, format=ext)
    return True


# 从音频中截取一个片段
def cut_from_audio(*, ss, to, audio_file, out_file):
    from . import help_srt
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
        out_file
    ]
    return runffmpeg(cmd)


def send_notification(title, message):
    from videotrans.configure import config
    if config.exec_mode == 'api' or config.exit_soft:
        return
    from plyer import notification
    try:
        notification.notify(
            title=title[:60],
            message=message[:120],
            ticker="pyVideoTrans",
            app_name="pyVideoTrans",  # config.uilanglist['SP-video Translate Dubbing'],
            app_icon=config.ROOT_DIR + '/videotrans/styles/icon.ico',
            timeout=10  # Display duration in seconds
        )
    except:
        pass


# 获取音频时长
def get_audio_time(audio_file):
    # 如果存在缓存并且没有禁用缓存
    out = runffprobe(['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', audio_file])
    if out is False:
        raise Exception(f'ffprobe error:dont get video information')
    out = json.loads(out)
    return float(out['format']['duration'])


# input_file_path 可能是字符串：文件路径，也可能是音频数据
def remove_silence_from_end(input_file_path, silence_threshold=-50.0, chunk_size=10, is_start=True):
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    """
    Removes silence from the end of an audio file.

    :param input_file_path: path to the input mp3 file
    :param silence_threshold: the threshold in dBFS considered as silence
    :param chunk_size: the chunk size to use in silence detection (in milliseconds)
    :return: an AudioSegment without silence at the end
    """
    # Load the audio file
    format = "wav"
    if isinstance(input_file_path, str):
        format = input_file_path.split('.')[-1].lower()
        if format in ['wav', 'mp3', 'm4a']:
            audio = AudioSegment.from_file(input_file_path, format=format if format in ['wav', 'mp3'] else 'mp4')
        else:
            # 转为mp3
            try:
                runffmpeg(['-y', '-i', input_file_path, input_file_path + ".mp3"])
                audio = AudioSegment.from_file(input_file_path + ".mp3", format="mp3")
            except Exception:
                return input_file_path

    else:
        audio = input_file_path

    # Detect non-silent chunks
    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=chunk_size,
        silence_thresh=silence_threshold
    )

    # If we have nonsilent chunks, get the start and end of the last nonsilent chunk
    if nonsilent_chunks:
        start_index, end_index = nonsilent_chunks[-1]
    else:
        # If the whole audio is silent, just return it as is
        return input_file_path

    # Remove the silence from the end by slicing the audio segment
    trimmed_audio = audio[:end_index]
    if is_start and nonsilent_chunks[0] and nonsilent_chunks[0][0] > 0:
        trimmed_audio = audio[nonsilent_chunks[0][0]:end_index]
    if isinstance(input_file_path, str):
        if format in ['wav', 'mp3', 'm4a']:
            trimmed_audio.export(input_file_path, format=format if format in ['wav', 'mp3'] else 'mp4')
            return input_file_path
        try:
            trimmed_audio.export(input_file_path + ".mp3", format="mp3")
            runffmpeg(['-y', '-i', input_file_path + ".mp3", input_file_path])
        except Exception:
            pass
        return input_file_path
    return trimmed_audio


def format_video(name, target_dir=None):
    from videotrans.configure import config
    from . import help_misc
    raw_pathlib = Path(name)
    raw_basename = raw_pathlib.name
    raw_noextname = raw_pathlib.stem
    ext = raw_pathlib.suffix
    raw_dirname = raw_pathlib.parent.resolve().as_posix()

    obj = {
        "name": name,
        # 处理后 移动后符合规范的目录名
        "dirname": raw_dirname,
        # 符合规范的基本名带后缀
        "basename": raw_basename,
        # 符合规范的不带后缀
        "noextname": raw_noextname,
        # 扩展名
        "ext": ext[1:]
        # 最终存放目标位置，直接存到这里
    }
    rule = r'[\[\]\*\?\"\|\'\:]'
    if re.search(rule, raw_noextname) or re.search(r'[\s\.]$', raw_noextname):
        # 规范化名字
        raw_noextname = re.sub(rule, f'', raw_noextname)
        raw_noextname = re.sub(r'[\.\s]$', f'', raw_noextname)
        raw_noextname = raw_noextname.strip()

        if Path(f'{config.TEMP_DIR}/{raw_noextname}{ext}').exists():
            raw_noextname += f'{chr(random.randint(97, 122))}'

        new_name = f'{config.TEMP_DIR}/{raw_noextname}{ext}'
        shutil.copy2(name, new_name)
        obj['name'] = new_name
        obj['noextname'] = raw_noextname
        obj['basename'] = f'{raw_noextname}{ext}'
        obj['shound_del_name'] = new_name

    if target_dir:
        obj['target_dir'] = Path(f'{target_dir}/{raw_noextname}').as_posix()

    obj['uuid'] = help_misc.get_md5(f'{name}-{time.time()}')[:10]
    return obj


# 导出可能较大的 wav 文件时，使用该函数，避免 大于4G 的音频出错
def large_wav_export_with_soundfile(audio_segment, output_path: str):
    import numpy as np
    import soundfile as sf

    # audio_segment = AudioSegment.from_file(...)
    """
    使用 soundfile 模块导出 pydub 的 AudioSegment 对象，以支持大文件。
    
    :param audio_segment: pydub 的音频对象
    :param output_path: 输出的 .wav 文件路径
    """
    print(f"正在使用 soundfile 导出到: {output_path}")

    # 1. 从 pydub 获取原始 PCM 数据（bytes）
    raw_data = audio_segment.raw_data

    # 2. 将原始数据转换为 NumPy 数组，这是 soundfile 的标准输入格式
    #    需要确定正确的数据类型 (dtype)
    sample_width = audio_segment.sample_width
    if sample_width == 1:
        dtype = np.int8  # 8-bit PCM
    elif sample_width == 2:
        dtype = np.int16  # 16-bit PCM
    elif sample_width == 4:
        dtype = np.int32  # 32-bit PCM
    else:
        raise ValueError(f"不支持的采样位宽: {sample_width}")

    # frombuffer 从字节串创建数组，'C' 表示按C语言顺序
    numpy_array = np.frombuffer(raw_data, dtype=dtype)

    # 3. 如果是多声道，需要将一维数组重塑为 (n_frames, n_channels)
    num_channels = audio_segment.channels
    if num_channels > 1:
        numpy_array = numpy_array.reshape((-1, num_channels))

    # 4. 使用 soundfile 写入文件
    #    soundfile 会自动处理文件大小，在需要时切换到 RF64
    sf.write(
        output_path,
        numpy_array,
        audio_segment.frame_rate,
        subtype='PCM_16' if sample_width == 2 else ('PCM_24' if sample_width == 3 else 'PCM_32')  # 根据需要选择子类型
    )
    print("使用 soundfile 导出成功！")
