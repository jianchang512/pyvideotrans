# -*- coding: utf-8 -*-
import datetime
import logging
import random
import sys
import time

from videotrans.configure._paths import ROOT_DIR


def _set_logs():
    logger = logging.getLogger('VideoTrans')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    _file_handler = logging.FileHandler(f'{ROOT_DIR}/logs/{datetime.datetime.now().strftime("%Y%m%d")}.log',
                                        encoding='utf-8')
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(formatter)
    logger.addHandler(_file_handler)

    if sys.stdout is not None:
        _console_handler = logging.StreamHandler(sys.stdout)
        _console_handler.setLevel(logging.WARNING)
        _console_handler.setFormatter(formatter)
        logger.addHandler(_console_handler)

    logging.getLogger("transformers").setLevel(logging.DEBUG)
    logging.getLogger("filelock").setLevel(logging.DEBUG)
    logging.getLogger("faster_whisper").setLevel(logging.DEBUG)
    return logger


def _write_with_retry(file_path, content, max_retries=2):
    _logger = logging.getLogger('VideoTrans')
    for attempt in range(max_retries):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except PermissionError as e:
            if attempt == max_retries - 1:
                _logger.exception(f'写入文件失败:{file_path}\n{e}', exc_info=True)
                return
            time.sleep(random.uniform(0.05, 0.2))
        except Exception:
            _logger.exception(f'写入文件失败:{file_path}', exc_info=True)
            return


def update_logging_level(new_level_str):
    new_level = getattr(logging, new_level_str.upper(), logging.INFO)
    _logger = logging.getLogger('VideoTrans')
    _logger.setLevel(new_level)
    for handler in _logger.handlers:
        if isinstance(handler, (logging.StreamHandler, logging.FileHandler)):
            handler.setLevel(new_level)
