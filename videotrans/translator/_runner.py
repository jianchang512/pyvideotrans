from typing import Union, List, Type

from videotrans.configure.config import app_cfg, logger
from videotrans.translator._base import BaseTrans
from videotrans import get_class
from videotrans.translator._constants import (
    GOOGLE_INDEX, MICROSOFT_INDEX,
    AI_TRANS_CHANNELS,
)
from videotrans.translator._registry import _ID_NAME_DICT
from videotrans.translator._lang_utils import get_source_target_code


def _check_google():
    import requests
    try:
        requests.head(f"https://translate.google.com", timeout=5)
    except Exception as e:
        logger.exception(f'检测google翻译失败{e}', exc_info=True)
        return False

    return True


# 翻译,先根据翻译通道和目标语言，取出目标语言代码
def run(*, translate_type=0,
        text_list=None,
        is_test=False,
        source_code=None,
        target_code=None,
        uuid=None) -> Union[List, str, None]:
    translate_type = int(translate_type)
    # ai渠道下，target_language_name 是语言名称
    # 其他渠道下是语言代码
    # source_code 是原语言代码
    target_language_name = target_code
    if translate_type in AI_TRANS_CHANNELS:
        # 对AI渠道，返回目标语言的自然语言表达
        _, target_language_name = get_source_target_code(show_target=target_code, translate_type=translate_type)
    kwargs = {
        "text_list": text_list,
        "target_language_name": target_language_name,
        "source_code": source_code if source_code and source_code not in ['-', 'No'] else 'auto',
        "target_code": target_code,
        "uuid": uuid,
        "is_test": is_test,
        "translate_type": translate_type
    }

    # 未设置代理并且检测google失败，则使用微软翻译
    if translate_type == GOOGLE_INDEX:
        if app_cfg.proxy or _check_google() is True:
            from videotrans.translator._google import Google
            return Google(**kwargs).run()
        logger.warning('未设置代理并且检测google失败，改为使用微软翻译')
        translate_type = MICROSOFT_INDEX
        kwargs['translate_type']=translate_type

    _cls: Union[Type[BaseTrans], None] = get_class(translate_type,"translator",_ID_NAME_DICT)
    if _cls is None:
        raise RuntimeError(f'No this Translation Channel:{translate_type}')

    return _cls(**kwargs).run()#type:ignore
