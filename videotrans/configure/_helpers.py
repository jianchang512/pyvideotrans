# -*- coding: utf-8 -*-
from videotrans.configure.signal_hub import SignalHub
from videotrans.task.taskcfg import SignMsg

# Module-level references set by config.py
_app_cfg_ref = None
_logger_ref = None


def set_app_cfg_ref(cfg):
    global _app_cfg_ref
    _app_cfg_ref = cfg


def set_logger_ref(lg):
    global _logger_ref
    _logger_ref = lg


def push_queue(uuid: str, msg: SignMsg):
    if _app_cfg_ref.exit_soft or uuid in _app_cfg_ref.stoped_uuid_set:
        return
    try:
        SignalHub.instance().post(uuid, msg)
    except Exception as e:
        _logger_ref.exception(f'push_queue 信号发送错误：{e}', exc_info=True)
