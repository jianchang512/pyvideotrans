"""Localization helpers dedicated to the Gradio WebUI.

Desktop/Qt translations live in videotrans/language. Keeping the WebUI catalog
separate prevents a partial WebUI locale from being advertised as a desktop
locale.
"""

import json
import os
from functools import cache
from pathlib import Path



def normalize_locale(value):
    """Normalize common locale aliases used by the WebUI."""
    return {
        "fr": "fr_FR",
        "fr-FR": "fr_FR",
        "zh": "zh_CN",
        "zh-CN": "zh_CN",
        "en": "en_US",
        "en-US": "en_US",
    }.get(value, value)


# 合并 webui 翻译字典和sp翻译字典
@cache
def _load_catalog(locale):
    from videotrans.configure.config import ROOT_DIR
    """Load only WebUI-owned translations for locale."""
    locale = normalize_locale(locale)
    path = Path(f"{ROOT_DIR}/videotrans/webui_languages/{locale}.json")
    webui_langobj={}
    path_sp = Path(f"{ROOT_DIR}/videotrans/language/{locale}.json")
    sp_langobj={}
    if path.is_file():
        try:
            webui_langobj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    if path_sp.is_file():
        try:
            sp_langobj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return sp_langobj|webui_langobj


WEBUI_LOCALE = normalize_locale(os.environ.get("PYVIDEOTRANS_LANG", "zh_CN"))
_CATALOG = _load_catalog(WEBUI_LOCALE)


def tr(key, *args):
    """Translate a WebUI key, falling back to the key itself."""
    value = _CATALOG.get(key, key)
    return value.format(*args) if args else value
