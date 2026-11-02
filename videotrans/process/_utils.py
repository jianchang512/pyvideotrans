from pathlib import Path
from videotrans.configure.config import logger

def _write_log(file, msg):
    if not file:return
    try:
        Path(file).write_text(msg, encoding='utf-8')
    except Exception as e:
        logger.exception(f'写入新进程日志时出错{e}', exc_info=True)

# 校对配音面板中重新配音时，F5-TTS 等内置渠道在子进程中用此函数转换配音
# 与主进程一样使用 BaseCon.convert_to_wav，静音移除、配音峰值归一化等设置同样生效
def convert_to_wav( mp3_file_path: str, output_wav_file_path: str, extra=None):
    from videotrans.configure.base import BaseCon
    return BaseCon.convert_to_wav(mp3_file_path, output_wav_file_path, extra)