# -*- coding: utf-8 -*-
import json
import os
from functools import lru_cache
from pathlib import Path

import locale

try:
    from PySide6.QtCore import QLocale
except ImportError:
    QLocale = None

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
        _lang = os.environ.get('PYVIDEOTRANS_LANG', getattr(settings, 'lang', ''))
        if not _lang:
            if QLocale is not None:
                sys_name = QLocale.system().name().replace('_', '-')
            else:
                sys_name = (locale.getdefaultlocale()[0] or "en").replace('_', '-')
            for k in SUPPORT_LANG.keys():
                if k.lower() == sys_name.lower():
                    _lang = k
                    break
            if not _lang:
                _lang = sys_name[:2].lower()
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


try:
    from videotrans.configure._i18n_keys import TranslationKey
except ImportError:
    # fallback to str if _i18n_keys.py hadn't been generated yet
    TranslationKey = str  # type: ignore


def tr(lang_key: TranslationKey, *kw) -> str:
    global _transobj
    if not _transobj:
        _transobj = _get_transobj(defaulelang)
    if not _transobj:
        if not kw:
            return lang_key
        try:
            return lang_key.format(*kw)
        except Exception:
            return lang_key

    if isinstance(lang_key, list):
        str_list = [t for t in [_transobj.get(it) for it in lang_key] if t]
        return ",".join(str_list)
    lang = _transobj.get(lang_key, lang_key)
    if not kw:
        return lang
    try:
        return lang.format(*kw)
    except Exception:
        return lang

