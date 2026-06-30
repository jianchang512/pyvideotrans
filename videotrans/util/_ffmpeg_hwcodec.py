# -*- coding: utf-8 -*-
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from videotrans.configure.config import ROOT_DIR, app_cfg, settings, logger
from videotrans.configure import config


def check_hw_on_start(_compat=None):
    get_video_codec(264)
    get_video_codec(265)


def get_video_codec(compat=None) -> str:
    import torch
    _codec_cache = app_cfg.codec_cache
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
            raise
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

    selected_codec = default_codec

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
                            continue
                    except ImportError:
                        logger.error("未找到 torch 模块，将直接尝试 nvenc 测试。")

                full_encoder_name = f"{h_prefix}_{encoder_suffix}"
                if test_encoder_internal(full_encoder_name):
                    selected_codec = full_encoder_name
                    logger.debug(f"已选择硬件编码器: {selected_codec}")
                    break
            else:
                logger.debug(f"所有硬件加速器均未通过测试。将使用软件编码器: {selected_codec}")

            _codec_cache[cache_key] = selected_codec
            Path(f"{ROOT_DIR}/videotrans/codec.json").write_text(json.dumps(_codec_cache))
        except Exception as e:
            logger.exception(f"在编码器测试期间发生意外，将使用软件编码: {e}", exc_info=True)
            selected_codec = default_codec

    _codec_cache[cache_key] = selected_codec

    logger.debug(f"最终确定使用的编码器: {selected_codec}")
    return selected_codec
