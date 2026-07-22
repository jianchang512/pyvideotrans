from pathlib import Path
from videotrans.configure.config import logger

def _write_log(file, msg):
    try:
        Path(file).write_text(msg, encoding='utf-8')
    except Exception as e:
        logger.exception(f'写入新进程日志时出错{e}', exc_info=True)