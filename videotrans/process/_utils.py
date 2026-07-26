from pathlib import Path
from videotrans.configure.config import logger,settings

def _write_log(file, msg):
    try:
        Path(file).write_text(msg, encoding='utf-8')
    except Exception as e:
        logger.exception(f'写入新进程日志时出错{e}', exc_info=True)

def convert_to_wav( mp3_file_path: str, output_wav_file_path: str, extra=None):
    cmd = [
        "-y",
        "-i",
        mp3_file_path,
        "-ar",
        "48000",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le"
    ]
    if extra:
        cmd += extra
    cmd += [
        output_wav_file_path
    ]
    try:
        from videotrans.util.help_ffmpeg import runffmpeg,remove_silence_wav
        runffmpeg(cmd, force_cpu=True)
        if settings.get('remove_dubb_silence', True):
            remove_silence_wav(output_wav_file_path)
    except Exception as e:
        logger.exception(f'转为 48k wav时失败，跳过{e}',exc_info=True)
        return False
    return True