from videotrans.translator._constants import *
from videotrans.translator._lang_codes import (  # noqa: F401
    LANGNAME_DICT,
    LANGNAME_DICT_REV,
    LANG_CODE,
)

from videotrans.translator._lang_utils import (  # noqa: F401
    get_code,
    get_source_target_code,
    is_allow_translate,
    get_audio_code,
    get_subtitle_code,
    get_mkv_code,
)

from videotrans.translator._runner import (  # noqa: F401
    run,
    _check_gorm,
)

from videotrans.translator._base import BaseTrans  # noqa: F401


# 根据 llm_ai_type 当前所选的索引，获取对应key name 或 常量
def get_name_index(idx, return_type='key'):
    idx = int(idx)
    _key = list(LLM_CONCERT_MAP.keys())[idx]
    if return_type == 'index':
        return LLM_CONCERT_INDEX.get(_key)
    if return_type == 'name':
        return LLM_CONCERT_MAP[_key]
    return _key
