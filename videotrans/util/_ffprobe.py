# -*- coding: utf-8 -*-
import json
import re
import subprocess
import sys
from pathlib import Path

from videotrans.configure.config import ROOT_DIR, tr, app_cfg, logger
from videotrans.configure import contants
from videotrans.util._ffmpeg_runner import extract_concise_error


def _run_ffprobe_internal(cmd: list[str]) -> str:
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
        _duration = out['streams'][0].get('duration')
        if not _duration:
            result['time'] = int(float(out['format']['duration']) * 1000)            
        elif re.match(r'^\d+(\.\d+)?$', _duration):
            result['time'] = int(float(_duration) * 1000)
        elif re.match(r'^\d+:', _duration):
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
        raise FFmpegError(tr('Unable to obtain video duration data, please check the video data')+f"\n{mp4_file}\n{e}")
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
        logger.exception(f'无法从视频或音频流中获取时长:{file=},{e}', exc_info=True)

    if ms == 0:
        try:
            ms = int(float(runffprobe(
            ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file]))*1000)
        except Exception as e:
            logger.error(f'再次从 format=duration 中读取失败 {e}')
    return ms


def get_video_ms_noaudio(mp4):
    return _get_ms_from_media(mp4)


def get_video_duration(file_path):
    return _get_ms_from_media(file_path)


def get_audio_time(audio_file):
    return _get_ms_from_media(audio_file)
