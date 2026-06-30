# -*- coding: utf-8 -*-
import os
from pathlib import Path

from videotrans.configure.config import ROOT_DIR, app_cfg, settings
from videotrans.task.taskcfg import InputFile


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
            timeout=10
        )
    except Exception:
        pass


def format_video(name, target_dir=None)->InputFile:
    from . import help_misc
    raw_pathlib = Path(name)
    raw_basename = raw_pathlib.name
    raw_noextname = raw_pathlib.stem
    ext = raw_pathlib.suffix.lower()[1:]
    raw_dirname = raw_pathlib.parent.resolve().as_posix()

    obj = InputFile(
        name=name,
        dirname=raw_dirname,
        basename=raw_basename,
        noextname=raw_noextname,
        ext=ext
    )

    if target_dir:
        obj.target_dir = Path(f'{target_dir}/{raw_noextname}-{ext}').as_posix()
    _stat = raw_pathlib.stat()
    obj.uuid = help_misc.get_md5(f'{name}-{_stat.st_size}-{_stat.st_mtime}')[:10]
    return obj
