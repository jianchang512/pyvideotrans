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
def _get_transobj(lang:str=None):
    SUPPORT_LANG = _get_langjson_list()
    _tobj={}
    if not lang:
        return _tobj
    for n in [lang,lang.split('_')[0].lower()]:
        _langfile=SUPPORT_LANG.get(lang)
        if _langfile and Path(_langfile).exists():
            try:
                _tobj = json.loads(Path(_langfile).read_text(encoding='utf-8'))
            except Exception as e:
                Path(f'{ROOT_DIR}/start_error.txt').write_text(f"{e}")
    return _tobj

def _init_language(settings):
    global defaulelang, _transobj
    SUPPORT_LANG = _get_langjson_list()
    try:
        _lang = os.environ.get('PYVIDEOTRANS_LANG', settings.lang)
        if not _lang or not SUPPORT_LANG.get(_lang) or not Path(SUPPORT_LANG.get(_lang)).exists():
            _lang = QLocale.system().name()
    except Exception:
        _lang = "en_US"

    if _lang not in SUPPORT_LANG:
        _lang = "en_US"
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
