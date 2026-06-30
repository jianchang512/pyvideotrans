import json, traceback
from pathlib import Path
from videotrans.configure.config import logger


def _write_log(file=None, msg=None, type='logs'):
    if not file or not msg:
        return
    try:
        Path(file).write_text(json.dumps({"text": msg, "type": type}), encoding='utf-8')
    except Exception as e:
        logger.exception(f'写入新进程日志时出错{e}', exc_info=True)
