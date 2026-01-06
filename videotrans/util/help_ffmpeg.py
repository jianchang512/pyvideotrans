import copy
import json
import os,re
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Union,Tuple,List,Dict


from videotrans.configure import config


def extract_concise_error(stderr_text: str, max_lines=3, max_length=250) -> str:
    if not stderr_text:
        return "Unknown error (empty stderr)"

    lines = stderr_text.strip().splitlines()
    if not lines:
        return "Unknown error (empty stderr lines)"
    
    result=re.findall(r'Error\s(.*?)\n',stderr_text)
    if not result:
        return " ".join(lines[-10:])
    return " ".join(result)


def _get_preset_classification(preset: str) -> str:
    """将 libx264/x265 的 preset 归类为 'fast', 'medium', 'slow'。"""
    if not preset:
        return 'medium'
    
    p = preset.lower()
    SOFTWARE_PRESET_CLASSIFICATION = {
        'ultrafast': 'fast', 'superfast': 'fast', 'veryfast': 'fast',
        'faster': 'fast', 'fast': 'fast',
        'medium': 'medium',
        'slow': 'slow', 'slower': 'slow', 'veryslow': 'slow',
        'placebo': 'slow'
    }
    return SOFTWARE_PRESET_CLASSIFICATION.get(p, 'medium')


def _get_preset_classification2(preset: str) -> str:
    """将 libx264/x265 的 preset 归类为 'fast', 'medium', 'slow'。"""
    SOFTWARE_PRESET_CLASSIFICATION = {
        'ultrafast': 'fast', 'superfast': 'fast', 'veryfast': 'fast',
        'faster': 'fast', 'fast': 'fast',
        'medium': 'medium',
        'slow': 'slow', 'slower': 'slow', 'veryslow': 'slow',
    }
    return SOFTWARE_PRESET_CLASSIFICATION.get(preset, 'medium')  # 默认为 medium


def _translate_crf_to_hw_quality(crf_value: str, encoder_family: str) -> Union[int, None]:
    """
    将 CRF 值近似转换为不同硬件编码器的质量值。
    """
    try:
        crf = float(crf_value) # 使用 float 兼容性更好
        crf_int = int(crf)

        # 1. NVENC (CQ), QSV (Global Quality), VAAPI
        # 范围 1-51，越小质量越高。与 CRF 逻辑一致。
        if encoder_family in ['nvenc', 'qsv', 'vaapi']:
            return max(1, min(crf_int, 51))
        
        # 2. VideoToolbox (macOS)
        # 使用 -q:v，范围 1-100。
        # 注意：VideoToolbox 的 scale 是反的（或者说是正向的品质），100 是最高质量，1 是最低。
        # CRF 0 (无损) ~ 对应 q:v 100
        # CRF 23 (默认) ~ 对应 q:v 60-70 左右
        # CRF 51 (最差) ~ 对应 q:v 1
        # 简单的线性映射公式：Quality = 100 - (CRF * 1.8) 
        if encoder_family == 'videotoolbox':
            quality = 100 - (crf * 1.8)
            return int(max(1, min(quality, 100)))

        # 3. AMF (AMD)
        # AMF 比较复杂，通常用 -qp_i / -qp_p，但也支持 -quality。
        # 简单的 CRF 映射很难精准，暂不处理以免画质崩坏。
        
    except (ValueError, TypeError):
        return None
    return None


def _translate_crf_to_hw_quality2(crf_value: str, encoder_family: str) -> Union[int, None]:
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

def _build_hw_command(args: list, hw_codec: str) -> Tuple[List[str], List[str]]:
    """
    根据选择的硬件编码器，构建 ffmpeg 命令参数列表和硬件解码选项
    此函数是纯粹的，它不修改输入列表，而是返回一个新的列表。
    """
    # 模拟外部 config 对象，防止报错，实际使用时请删除下面这行或保留原本的 import
    from videotrans.configure import config

    if not hw_codec or 'libx' in hw_codec or hw_codec == 'copy':
        return list(args), []

    # 更加健壮的 encoder_family 提取 (全小写)
    encoder_family = hw_codec.split('_')[-1].lower()

    # --- 参数映射表 ---
    PRESET_MAP = {
        # NVENC: p1 (最快) - p7 (最慢/质量最好)
        'nvenc': {'fast': 'p2', 'medium': 'p4', 'slow': 'p7'}, 
        # QSV: veryfast, faster, fast, medium, slow, slower, veryslow
        'qsv': {'fast': 'faster', 'medium': 'medium', 'slow': 'slower'},
        # AMF: speed, balanced, quality
        'amf': {'fast': 'speed', 'medium': 'balanced', 'slow': 'quality'},
        # VAAPI: 通常也接受 standard presets
        'vaapi': {'fast': 'veryfast', 'medium': 'medium', 'slow': 'veryslow'},
        # VideoToolbox: 通常不支持 -preset 参数，留空以跳过处理
        'videotoolbox': None 
    }

    # 定义硬件质量参数的名称
    QUALITY_PARAM_MAP = {
        'nvenc': '-cq',             # 还需要配合自动添加 -rc:v vbr 逻辑吗？通常 -cq 足够触发 VBR 模式
        'qsv': '-global_quality',   # ICQ 模式
        'vaapi': '-global_quality',
        'videotoolbox': '-q:v',     # 苹果硬编质量参数
    }

    new_args = []
    hw_decode_opts = []

    i = 0
    main_input_file = ""
    
    # 预扫描：检查是否包含字幕流或滤镜，用于后续决定是否开启硬件解码
    has_subtitles = "-c:s" in args
    # 检查所有形式的滤镜参数
    has_filters = any(x in args for x in ["-vf", "-filter_complex", "-lavfi"])
    
    while i < len(args):
        arg = args[i]
        
        # 记录主输入文件 (通常是第一个 -i 后的参数)
        if arg == '-i' and not main_input_file and i + 1 < len(args):
            main_input_file = args[i + 1]

        # 1. 替换视频编码器
        if arg == '-c:v' and i + 1 < len(args):
            # 确保 copy 模式不被覆盖
            if args[i + 1] == 'copy':
                new_args.extend(['-c:v', 'copy'])
            else:
                new_args.extend(['-c:v', hw_codec])
            i += 2
            continue

        # 2. 调整 preset 参数
        if arg == '-preset' and i + 1 < len(args):
            family_presets = PRESET_MAP.get(encoder_family)
            # 如果该家族有定义的 preset 映射，则替换；
            # 如果 family_presets 为 None (如 videotoolbox)，则直接丢弃原 preset 参数
            if family_presets:
                classification = _get_preset_classification(args[i + 1])
                new_preset = family_presets.get(classification)
                if new_preset:
                    new_args.extend(['-preset', new_preset])
            # 如果是 videotoolbox，直接跳过 '-preset' 和它的值，因为不支持
            i += 2
            continue

        # 3. 替换 -crf 参数
        if arg == '-crf' and i + 1 < len(args):
            hw_quality_param = QUALITY_PARAM_MAP.get(encoder_family)
            if hw_quality_param:
                crf_value = args[i + 1]
                hw_quality_value = _translate_crf_to_hw_quality(crf_value, encoder_family)
                
                if hw_quality_value is not None:
                    new_args.extend([hw_quality_param, str(hw_quality_value)])
                    
                    # 【NVENC 特殊处理】
                    # 使用 -cq 时，如果不指定 -rc，默认为 constant QP 还是 VBR 取决于驱动。
                    # 为了体感接近 CRF，强制指定 VBR 可能是个好选择，但为了保持函数纯洁性，
                    # 这里仅做参数替换。如需更稳定，可取消下面注释：
                    # if encoder_family == 'nvenc' and '-rc' not in args and '-rc:v' not in args:
                    #     new_args.extend(['-rc:v', 'vbr'])
                else:
                    # config.logger.warning(f"无法转换 -crf {crf_value}，忽略。")
                    pass
            else:
                # config.logger.warning(f"编码器 {encoder_family} 不支持 CRF 替换，忽略。")
                pass
            i += 2
            continue

        new_args.append(arg)
        i += 1
    return new_args



def _build_hw_command2(args: list, hw_codec: str):
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

                    new_args.extend([hw_quality_param, str(hw_quality_value)])
                else:
                    config.logger.warning(f"无法转换 -crf {crf_value} 的值，将忽略此质量参数。")
            else:
                config.logger.warning(f"编码器 {encoder_family} 不支持CRF到硬件质量参数的自动替换，将忽略 -crf。")
            i += 2
            continue

        new_args.append(arg)
        i += 1
    return new_args


def runffmpeg(arg, *, noextname=None, uuid=None, force_cpu=True,cmd_dir=None):
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
    if config.settings.get('force_lib'):
        force_cpu=True
    arg_copy = copy.deepcopy(arg)

    default_codec = f"libx{config.settings.get('video_codec', '265')}"

    final_args = arg
    #hw_decode_opts = []

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

    # 尝试硬件编码
    if not force_cpu:
        if not hasattr(config, 'video_codec') or not config.video_codec:
            config.video_codec = get_video_codec()
        if config.video_codec and 'libx' not in config.video_codec:
            config.logger.debug(f"检测到硬件编码器 {config.video_codec}，正在调整参数...")
            final_args = _build_hw_command(arg, config.video_codec)


    cmd = [config.FFMPEG_BIN, "-hide_banner", "-ignore_unknown",'-threads','0']
    if "-y" not in final_args:
        cmd.append("-y")
    #cmd.extend(hw_decode_opts)
    cmd.extend(final_args)

    if cmd and Path(cmd[-1]).suffix:
        cmd[-1] = Path(cmd[-1]).as_posix()

    if config.settings.get('ffmpeg_cmd'):
        custom_params = [p for p in config.settings.get('ffmpeg_cmd','').split(' ') if p]
        cmd = cmd[:-1] + custom_params + cmd[-1:]

    if noextname:
        config.queue_novice[noextname] = 'ing'


    try:
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
        if config.exit_soft:
            return
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors='replace',
            check=True,
            text=True,
            creationflags=creationflags,
            cwd=cmd_dir
        )
        if noextname:
            config.queue_novice[noextname] = "end"
        return True

    except FileNotFoundError as e:
        config.logger.warning(f"命令未找到: {cmd[0]}。请确保 ffmpeg 已安装并在系统 PATH 中。")
        if noextname:
            config.queue_novice[noextname] = f"error:{e}"
        raise

    except subprocess.CalledProcessError as e:
        if config.exit_soft:
            return
        error_message = e.stderr or ""
        config.logger.warning(f"FFmpeg 命令执行失败 (force_cpu={force_cpu})。\n命令: {' '.join(cmd)}\n错误: {error_message}")

        is_video_output = cmd[-1].lower().endswith('.mp4')
        if not force_cpu and is_video_output:
            config.logger.warning("回退： 硬件加速失败，将自动回退到 CPU 编码重试...")

            fallback_args = []
            i = 0
            while i < len(arg_copy):
                if arg_copy[i] == '-c:v' and i + 1 < len(arg_copy) and arg_copy[i + 1] != 'copy':
                    fallback_args.extend(['-c:v', default_codec])
                    i += 2
                else:
                    fallback_args.append(arg_copy[i])
                    i += 1

            return runffmpeg(fallback_args, noextname=noextname, uuid=uuid, force_cpu=True,cmd_dir=cmd_dir)

        err=extract_concise_error(e.stderr)
        if noextname:
            config.queue_novice[noextname] = f"error:{err}"
        raise RuntimeError(err)

    except Exception as e:
        if noextname: config.queue_novice[noextname] = f"error:{e}"
        config.logger.debug(f"执行 ffmpeg 时发生未知错误 (force_cpu={force_cpu})。")
        # 针对win上路径和名称问题单独提示
        if sys.platform=='win32' and 'No such file or directory' in str(e):
            err=get_filepath_from_cmd(cmd)
            if err:
                raise RuntimeError(err)
        raise

# 从 cmd 列表中获取 -i 之后的路径和 最后一个路径，以判断文件名是否规则，

def get_filepath_from_cmd(cmd:list):
    from videotrans.configure.config import tr
    file_list=[cmd[i+1] for i,param in enumerate(cmd) if param=='-i']
    file_list.append(cmd[-1])
    special=['"',"'","`","*","?",":",">","<","|","\n","\r"]
    for file in file_list:
        if len(file)>=255:
            return  tr('The file path and file name may be too long. Please move the file to a flat and short directory and rename the file to a shorter name, ensuring that the length from the drive letter to the end of the file name does not exceed 255 characters: {},For example D:/videotrans/1.mp4 D:/videotrans/2.wav',file)
        for flag in special:
            if flag in file:
                return tr('There may be special characters in the file name or path. Please move the file to a simple directory consisting of English and numerical characters, rename the file to a simple name, and try again to avoid errors: {},For example D:/videotrans/1.mp4 D:/videotrans/2.wav',file)
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

    Args:
        force_test (bool): 如果为 True，则忽略缓存并重新运行测试。默认为 False。

    Returns:
        str: 推荐的 ffmpeg 视频编码器名称 (例如 'h264_nvenc', 'libx264')。
    """
    from videotrans.configure import config
    _codec_cache = config.codec_cache  # 使用 config 中的缓存
    try:
        if not _codec_cache and Path(f'{config.ROOT_DIR}/videotrans/codec.json').exists():
            _codec_cache=json.loads(Path(f'{config.ROOT_DIR}/videotrans/codec.json').read_text(encoding='utf-8'))
    except Exception as e:
        config.logger.debug(f'parse codec.json error:{e}')
        
    
    plat = platform.system()
    if compat and compat in [264,265]:
        video_codec_pref=compat
    else:
        try:
            video_codec_pref = int(config.settings.get('video_codec', 264))
        except (ValueError, TypeError):
            config.logger.warning("配置中 'video_codec' 无效。将默认使用 H.264 (264)。")
            video_codec_pref = 264

    cache_key = f'{plat}-{video_codec_pref}'
    if cache_key in _codec_cache:
        config.logger.debug(f"返回缓存的编解码器 {cache_key}: {_codec_cache[cache_key]}")
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
        config.logger.warning(f"准备测试硬件编码器时出错: {e}。将使用软件编码 {default_codec}。")
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

        config.logger.debug(f"正在测试编码器是否可用: {encoder_to_test}...")
        success = False
        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True,
                encoding='utf-8', errors='ignore', creationflags=creationflags, timeout=timeout
            )
            config.logger.debug(f"硬件编码器 '{encoder_to_test}' 可用。")
            success = True
        except FileNotFoundError:
            config.logger.debug("'ffmpeg' 命令在 PATH 中未找到。无法进行编码器测试。")
            raise  # 重新抛出异常，让上层逻辑捕获并终止测试
        except subprocess.CalledProcessError as e:
            config.logger.debug(f"硬件编码器 '{encoder_to_test}' 不可用")
            raise
        except PermissionError:
            config.logger.debug(f"测试硬件编码器时失败:写入 {output_file} 时权限被拒绝。 {command=}")
            raise
        except subprocess.TimeoutExpired:
            config.logger.debug(f"硬件编码器 '{encoder_to_test}' 测试在 {timeout} 秒后超时。{command=}")
            raise
        except Exception as e:
            config.logger.debug(f"测试硬件编码器 {encoder_to_test} 时发生意外错误: {e} {command=}")
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
        config.logger.debug(f"不支持的平台: {plat}。将使用软件编码器 {default_codec}。")
    else:
        config.logger.debug(f"平台: {plat}。正在按优先级检测最佳的 '{h_prefix}' 编码器: {encoders_to_test}")
        try:
            for encoder_suffix in encoders_to_test:
                if encoder_suffix == 'nvenc':
                    try:
                        import torch
                        if not torch.cuda.is_available():
                            config.logger.debug("CUDA 不可用，跳过 nvenc 测试。")
                            continue  # 跳过当前循环，测试下一个编码器
                    except ImportError:
                        config.logger.debug("未找到 torch 模块，将直接尝试 nvenc 测试。")

                full_encoder_name = f"{h_prefix}_{encoder_suffix}"
                if test_encoder_internal(full_encoder_name):
                    selected_codec = full_encoder_name
                    config.logger.debug(f"已选择硬件编码器: {selected_codec}")
                    break
            else:  # for-else 循环正常结束 (没有 break)
                config.logger.debug(f"所有硬件加速器均未通过测试。将使用软件编码器: {selected_codec}")

            _codec_cache[cache_key] = selected_codec
            # 保存缓存到本地
            Path(f"{config.ROOT_DIR}/videotrans/codec.json").write_text(json.dumps(_codec_cache))
        except Exception as e:
            # 发生异常不缓存
            config.logger.exception(f"在编码器测试期间发生意外，将使用软件编码: {e}", exc_info=True)
            selected_codec = default_codec
    # 
    _codec_cache[cache_key] = selected_codec
    
    config.logger.debug(f"最终确定使用的编码器: {selected_codec}")
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
    # print(command)
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
        config.logger.warning(msg)
        raise _FFprobeInternalError(msg) from e
    except subprocess.CalledProcessError as e:
        concise_error = extract_concise_error(e.stderr)
        config.logger.exception(f"ffprobe command failed: {concise_error}", exc_info=True)
        raise _FFprobeInternalError(concise_error) from e
    except (PermissionError, OSError) as e:
        config.logger.exception(e, exc_info=True)
        raise _FFprobeInternalError(e) from e


def runffprobe(cmd):
    try:
        stdout_result = _run_ffprobe_internal(cmd)
        if stdout_result:
            return stdout_result

        # 如果 stdout 为空，但进程没有出错（不常见），则模拟旧的错误路径
        #  _run_ffprobe_internal 中，如果 stderr 有内容且返回码非0，
        # 会直接抛出异常，所以这段逻辑主要为了覆盖极端的边缘情况。
        config.logger.warning("ffprobe ran successfully but produced no output.")
        raise Exception("ffprobe ran successfully but produced no output.")

    except _FFprobeInternalError as e:
        raise
    except Exception as e:
        # 捕获其他意料之外的错误并重新引发，保持行为一致
        config.logger.exception(e, exc_info=True)
        raise



def get_video_info(mp4_file, *, video_fps=False, video_scale=False, video_time=False, get_codec=False):
    """
    获取视频信息。
    """
    from videotrans.configure import config

    if not Path(mp4_file).exists():
        raise Exception(f'{mp4_file} is not exists')
    try:
        out_json = runffprobe(
            ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mp4_file]
        )
        if not out_json:
            raise RuntimeError(config.tr('Failed to parse {} information, please confirm that the file can be played normally',mp4_file))
    except Exception as e:
        raise

    try:
        out = json.loads(out_json)
    except json.JSONDecodeError:
        raise RuntimeError(config.tr('Failed to parse {} information, please confirm that the file can be played normally',mp4_file))


    if "streams" not in out or not out["streams"]:
        raise RuntimeError(config.tr('The original file {} does not contain any audio or video data. The file may be damaged. Please confirm that the file can be played.',mp4_file))

    result = {
        "video_fps": 30,
        "r_frame_rate":30,
        "video_codec_name": "",
        "audio_codec_name": "",
        "width": 0,
        "height": 0,
        "time": 0,
        "streams_len": len(out['streams']),
        "streams_audio": 0,
        "video_streams":0,
        "color": "yuv420p"
    }
    try:
        # 以第一个流中duration为准，但可能某些格式，例如mkv第一个流中无duration字段或始终为0
        result['time']=int(float(out['streams'][0]['duration'])*1000)#第一个流的长度为准
        if result['time']<=0:
            result['time']=int(float(out['format']['duration'])*1000)
    except:
        result['time']=int(float(out['format']['duration'])*1000)
    
        

    video_stream = next((s for s in out['streams'] if s.get('codec_type') == 'video'), None)
    audio_streams = [s for s in out['streams'] if s.get('codec_type') == 'audio']

    result['streams_audio'] = len(audio_streams)
    if audio_streams:
        result['audio_codec_name'] = audio_streams[0].get('codec_name', "")

    if video_stream:
        result['video_streams']=1
        result['video_codec_name'] = video_stream.get('codec_name', "")
        result['width'] = int(video_stream.get('width', 0))
        result['height'] = int(video_stream.get('height', 0))
        result['color'] = video_stream.get('pix_fmt', 'yuv420p').lower()

        # FPS 计算逻辑
        def parse_fps(rate_str):
            try:
                num, den = map(int, rate_str.split('/'))
                return num / den if den != 0 else 0
            except:
                return 0

        fps1 = parse_fps(video_stream.get('r_frame_rate'))
        
        if not fps1 or fps1<1:
            fps_avg=parse_fps(video_stream.get('avg_frame_rate'))
        else:
            fps_avg = fps1



        result['video_fps'] = fps_avg if 1 <= fps_avg <= 120 else 30
        result['r_frame_rate'] = video_stream.get('r_frame_rate',result['video_fps'])

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
    ms=0
    ext=Path(file).suffix.lower()[1:]
    try:
        if ext in config.VIDEO_EXTS:
            ms=int(float(runffprobe(['-v','error','-select_streams','v:0','-show_entries','stream=duration','-of','default=noprint_wrappers=1:nokey=1',file]))*1000)
        elif ext in config.AUDIO_EXITS:
            ms=int(float(runffprobe(['-v','error','-select_streams','a:0','-show_entries','stream=duration','-of','default=noprint_wrappers=1:nokey=1',file]))*1000)
    except Exception:
        # mkv 等其他格式可能无法从流中读取 duration
        pass
    if ms==0:
        ms=int(float(runffprobe(['-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',file])))
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
    cmd=[
            "-y",
            "-i",
            Path(audio).as_posix(),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            '-af', "volume=2.0,alimiter=limit=1.0",
            Path(target_audio).as_posix()
    ]
    print(f'{cmd=}')
    return runffmpeg(cmd)

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

    config.logger.debug(f'{concat_txt=},{filelist[0]=}')
    with open(concat_txt, 'w', encoding='utf-8') as f:
        f.write("\n".join(txt))
    return concat_txt


# 多个音频片段连接
def concat_multi_audio(*, out=None, concat_txt=None):
    if out:
        out = Path(out).as_posix()


    cmd = ['-y', '-f', 'concat', '-safe', '0', '-i', concat_txt, "-b:a", "128k"]
    if out.endswith('.m4a'):
        cmd += ['-c:a', 'aac']
    elif out.endswith('.wav'):
        cmd += ['-c:a', 'pcm_s16le']
    runffmpeg(cmd + [out],cmd_dir=Path(concat_txt).parent.as_posix())
    return True


def precise_speed_up_audio(*, file_path=None, out=None, target_duration_ms=None):
    from pydub import AudioSegment
    ext = file_path[-3:].lower()
    out_ext=ext
    if out:
        out_ext=out[-3:].lower()
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
    rubberband_filter_str = f"rubberband=tempo={current_duration_ms / target_duration_ms}"
    if not out:
        Path(file_path).rename(file_path+f".{ext}")
        file_path=file_path+f".{ext}"
        out=file_path
    cmd = [
        '-y',
        '-i',
        file_path,
        '-filter:a',
        rubberband_filter_str,
        '-t', f"{target_duration_ms/1000.0}",  # 强制裁剪到目标时长，防止精度误差
        '-ar', "48000",
        '-ac', "2",
        '-c:a', codecs.get(out_ext,'pcm_s16le'),
        out
    ]
    try:
        runffmpeg(cmd, force_cpu=True)
    except Exception as e:
        cmd[4]=filter_str
        runffmpeg(cmd, force_cpu=True)


# 从音频中截取一个片段
def cut_from_audio(*, ss, to, audio_file, out_file):
    from . import help_srt
    from pathlib import Path
    if not Path(audio_file).exists():
        return False
    Path(out_file).parent.mkdir(exist_ok=True,parents=True)
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
    if config.settings.get('dont_notify',False):
        return
    from plyer import notification
    try:
        notification.notify(
            title=title[:60],
            message=message[:120],
            ticker="pyVideoTrans",
            app_name="pyVideoTrans",
            app_icon=config.ROOT_DIR + '/videotrans/styles/icon.ico',
            timeout=10  # Display duration in seconds
        )
    except Exception:
        pass




def remove_silence_wav(audio_file):
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    audio=AudioSegment.from_file(audio_file,format="wav")
    # 2. 激进的参数设置
    # TTS通常比较干净，我们可以把阈值设得离平均音量更近一些
    # 这里设置为比平均音量低 10dB 即视为静音（非常激进）
    silence_threshold = audio.dBFS - 20

    # 只要静音持续 10ms 以上就检测出来
    min_silence_len = 50

    # 3. 检测非静音片段
    # seek_step=1 保证毫秒级的精度
    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_threshold,
        seek_step=1
    )

    # 4. 处理剪切逻辑
    if len(nonsilent_chunks) > 0:
        # 获取第一个非静音块的开始时间
        start_trim = nonsilent_chunks[0][0]
        # 获取最后一个非静音块的结束时间
        end_trim = nonsilent_chunks[-1][1]
        # 裁剪音频
        trimmed_audio = audio[start_trim:end_trim]
        trimmed_audio.export(audio_file,format="wav")
    return True


# input_file_path 可能是字符串：文件路径，也可能是音频数据
def remove_silence_from_end(input_file_path,is_start=True):
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent

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
        min_silence_len=10,
        silence_thresh=audio.dBFS - 20
    )

    # If we have nonsilent chunks, get the start and end of the last nonsilent chunk
    if nonsilent_chunks:
        start_index, end_index = nonsilent_chunks[-1]
    else:
        # If the whole audio is silent, just return it as is
        return input_file_path

    # Remove the silence from the end by slicing the audio segment
    trimmed_audio = audio[:end_index]
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

    obj = {
        # 原始文件名含完整路径，如 F:/python/1.mp4
        "name": name,
        # 原始所在目录 如 F:/python
        "dirname": raw_dirname,
        # 基本名带后缀 如 1.mp4
        "basename": raw_basename,
        # 基本名不带后缀,如 1
        "noextname": raw_noextname,
        # 扩展名去掉点.  如 mp4
        "ext": ext
        # 最终存放目标位置，直接存到这里
    }

    # 如果存在目标文件夹，则在其之下生成 以无后缀的基本名的子文件夹
    if target_dir:
        obj['target_dir'] = Path(f'{target_dir}/{raw_noextname}-{ext}').as_posix()
    # 唯一id标识
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
