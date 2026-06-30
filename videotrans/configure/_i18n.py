# -*- coding: utf-8 -*-
import json
import os
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QLocale

from videotrans.configure._paths import ROOT_DIR

# Module-level state, set via _init_language()
defaulelang = None
_transobj = None


@lru_cache(maxsize=None)
def _get_langjson_list():
    lang_dir = Path(f'{ROOT_DIR}/videotrans/language')
    _SUPPORT_LANG = {}
    if lang_dir.exists():
        for it in lang_dir.glob('*.json'):
            if it.stat().st_size > 0:
                _SUPPORT_LANG[it.stem] = it.as_posix()
    return _SUPPORT_LANG


@lru_cache()
def _get_transobj(lang):
    SUPPORT_LANG = _get_langjson_list()
    try:
        _tobj = json.loads(Path(SUPPORT_LANG.get(lang)).read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError, TypeError):
        _tobj = None
    return _tobj


def _init_language(settings):
    global defaulelang, _transobj
    SUPPORT_LANG = _get_langjson_list()
    try:
        _lang = os.environ.get('PYVIDEOTRANS_LANG', settings.lang)
        if not _lang:
            _lang = QLocale.system().name()[:2].lower()
    except Exception:
        _lang = "en"

    if _lang not in SUPPORT_LANG:
        _lang = "en"
    if not settings.lang:
        settings.lang = _lang
        settings.save()
    defaulelang = _lang
    _transobj = _get_transobj(defaulelang)
    return defaulelang, _transobj


def tr(lang_key, *kw):
    global _transobj
    if not _transobj:
        _transobj = _get_transobj(defaulelang)
    if not _transobj:
        return lang_key

    if isinstance(lang_key, list):
        str_list = [t for t in [_transobj.get(it) for it in lang_key] if t]
        return ",".join(str_list)
    lang = _transobj.get(lang_key)
    if not lang:
        return lang_key
    if not kw:
        return lang
    try:
        return lang.format(*kw)
    except IndexError:
        return lang
