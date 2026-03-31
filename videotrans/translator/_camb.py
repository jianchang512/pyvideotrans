# -*- coding: utf-8 -*-
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure.config import tr, params, settings, app_cfg, logger, ROOT_DIR
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.translator._base import BaseTrans

RETRY_NUMS = 3
RETRY_DELAY = 5


def _get_camb_lang_id(langcode):
    """Map pyvideotrans language code to CAMB AI integer language ID."""
    cache_file = Path(ROOT_DIR + '/videotrans/voicejson/camb_languages.json')
    if cache_file.exists():
        mapping = json.loads(cache_file.read_text(encoding='utf-8'))
        # Try exact match first, then prefix match
        if langcode in mapping:
            return mapping[langcode]
        prefix = langcode.split('-')[0] if '-' in langcode else langcode
        if prefix in mapping:
            return mapping[prefix]
    return None


def refresh_camb_languages():
    """Fetch and cache CAMB AI language mappings."""
    try:
        from camb.client import CambAI
        client = CambAI(api_key=params.get('camb_api_key', '') or os.environ.get('CAMB_API_KEY', ''))
        source_langs = client.languages.get_source_languages()

        mapping = {}
        for lang in source_langs:
            lang_id = lang.id if hasattr(lang, 'id') else lang.get('id')
            short_name = lang.short_name if hasattr(lang, 'short_name') else lang.get('short_name', '')
            if lang_id and short_name:
                # Map both full code and prefix
                mapping[short_name] = lang_id
                prefix = short_name.split('-')[0]
                if prefix not in mapping:
                    mapping[prefix] = lang_id

        cache_file = Path(ROOT_DIR + '/videotrans/voicejson/camb_languages.json')
        cache_file.write_text(json.dumps(mapping, indent=2), encoding='utf-8')
        return mapping
    except Exception as e:
        logger.exception(f'Failed to refresh CAMB AI languages: {e}', exc_info=True)
        return {}


@dataclass
class CambTranslator(BaseTrans):
    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = True

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(logger, logging.INFO),
           after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit():
            return
        if isinstance(data, list):
            text = "\n".join([i.strip() for i in data])
        else:
            text=data
        
        source_id = _get_camb_lang_id(self.source_code)
        target_id = _get_camb_lang_id(self.target_code)

        # If language IDs not cached, refresh
        if not source_id or not target_id:
            refresh_camb_languages()
            source_id = _get_camb_lang_id(self.source_code)
            target_id = _get_camb_lang_id(self.target_code)

        if not target_id:
            raise StopRetry(f"CAMB AI does not support target language: {self.target_code}")

        try:
            from camb.client import CambAI
            client = CambAI(
                api_key=params.get('camb_api_key', '') or os.environ.get('CAMB_API_KEY', ''),
                httpx_client=httpx.Client(proxy=self.proxy_str) if self.proxy_str else None
            )

            try:
                result = client.translation.translation_stream(
                    source_language=source_id if source_id else 1,
                    target_language=target_id,
                    text=text,
                )
                # translation_stream may return an HttpResponse wrapper
                if hasattr(result, 'data') and result.data:
                    data = result.data
                    if isinstance(data, str):
                        return data
                    if hasattr(data, 'texts'):
                        return "\n".join(data.texts)
                    if isinstance(data, dict) and 'texts' in data:
                        return "\n".join(data['texts'])
                    return str(data)
                if isinstance(result, str):
                    return result
                return str(result)
            except Exception as e:
                # SDK throws ApiError for plain-text responses (not JSON)
                # but the body contains the actual translation on status 200
                from camb.core.api_error import ApiError
                if isinstance(e, ApiError) and e.status_code == 200:
                    return str(e.body)
                raise

        except Exception as e:
            err_str = str(e)
            if '401' in err_str or '403' in err_str or 'Unauthorized' in err_str:
                raise StopRetry(err_str)
            raise
