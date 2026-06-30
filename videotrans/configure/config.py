# -*- coding: utf-8 -*-
import os
from pathlib import Path

from videotrans.configure._paths import (  # noqa: F401
    IS_FROZEN, SYS_TMP, ROOT_DIR, TEMP_ROOT, LOGS_DIR, TEMP_DIR, TRANSLATE_CACHE, _set_env
)
from videotrans.configure._logging import _set_logs, _write_with_retry, update_logging_level  # noqa: F401
from videotrans.configure._i18n import _get_langjson_list, _get_transobj, _init_language, tr  # noqa: F401
from videotrans.configure._app_cfg import AppCfg
from videotrans.configure._app_settings import AppSettings
from videotrans.configure._app_params import AppParams, set_settings_ref
from videotrans.configure._helpers import push_queue, set_app_cfg_ref, set_logger_ref  # noqa: F401


_set_env()

logger = _set_logs()

app_cfg: AppCfg = AppCfg()
settings: AppSettings = AppSettings()
set_settings_ref(settings)
params: AppParams = AppParams()

HOME_DIR = settings.homedir
Path(HOME_DIR).mkdir(parents=True, exist_ok=True)

defaulelang, _transobj = _init_language(settings)

set_app_cfg_ref(app_cfg)
set_logger_ref(logger)

_proxy = settings.proxy or os.environ.get('HTTPS_PROXY', '')
if _proxy:
    os.environ['HTTPS_PROXY'] = _proxy
    os.environ['HTTP_PROXY'] = _proxy
    app_cfg.proxy = _proxy
    if not settings.proxy:
        settings['proxy'] = _proxy


def init_run():
    global TEMP_DIR
    TEMP_DIR = f'{TEMP_ROOT}/{os.getpid()}'
    Path(f"{TEMP_DIR}").mkdir(parents=True, exist_ok=True)
    Path(f'{TEMP_ROOT}/translate_cache').mkdir(exist_ok=True, parents=True)
    Path(f'{ROOT_DIR}/models').mkdir(exist_ok=True, parents=True)
    Path(f'{ROOT_DIR}/f5-tts').mkdir(exist_ok=True, parents=True)
