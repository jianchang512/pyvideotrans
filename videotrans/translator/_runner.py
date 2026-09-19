from typing import Union, List, Type

from videotrans.configure.config import app_cfg, logger
from videotrans.translator._base import BaseTrans
from videotrans import get_class
from videotrans.translator._constants import (
    GOOGLE_INDEX, MICROSOFT_INDEX,    AI_TRANS_CHANNELS,ID_NAME_DICT
)
from videotrans.translator._lang_utils import get_source_target_code


def _check_gorm(name='google'):
    import requests
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,zh-HK;q=0.6,ja;q=0.5",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-model": "iPhone",
            "sec-ch-ua-platform": "iOS",
            "sec-ch-ua-platform-version": "18.5"
        }
        res=requests.get(f"https://translate.google.com/m", timeout=5,verify=False,headers=headers)
        return res.status_code
    except Exception as e:
        logger.exception(f'检测 {name} 翻译失败:{e}', exc_info=True)
    return 0


# 翻译,先根据翻译通道和目标语言，取出目标语言代码
def run(*, translate_type=0,
        text_list=None,
        is_test=False,
        source_code="",
        target_code="",
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
        "source_code": 'auto' if not source_code or source_code in ['-', 'auto'] else source_code,
        "target_code": target_code,
        "uuid": uuid,
        "is_test": is_test,
        "translate_type": translate_type
    }

    # 未设置代理并且检测google失败，则使用微软翻译
    if translate_type == GOOGLE_INDEX:
        _rs=_check_gorm(name='google')
        logger.debug(f'测试Google翻译测试返回status_code={_rs}')
        if _rs == 200:
            from videotrans.translator._google import Google
            return Google(**kwargs).run()
        if _rs == 429:
            logger.warning(f'Google翻译测试返回 429 反爬拦截，改用  googletrans 库尝试')
            from videotrans.translator._googlepy import GoogleTrans
            return GoogleTrans(**kwargs).run()

        logger.warning(f'检测google翻译失败:status_code{_rs}，改为使用微软翻译')
        translate_type = MICROSOFT_INDEX
        kwargs['translate_type']=translate_type
    _cls: Union[Type[BaseTrans], None] = get_class(translate_type,"translator",ID_NAME_DICT)
    if _cls is None:
        raise RuntimeError(f'No this Translation Channel:{translate_type}')
    return _cls(**kwargs).run()#type:ignore



# 翻译,先根据翻译通道和目标语言，取出目标语言代码
def get_model_transobj(*, translate_type=0, uuid=None) -> Union[List, str, None]:
    translate_type = int(translate_type)
    # ai渠道下，target_language_name 是语言名称
    # 其他渠道下是语言代码
    # source_code 是原语言代码

    kwargs = {
        "uuid": uuid,
        "translate_type": translate_type
    }


    _cls: Union[Type[BaseTrans], None] = get_class(translate_type,"translator",ID_NAME_DICT)
    if _cls is None:
        raise RuntimeError(f'No this Translation Channel:{translate_type}')

    return _cls(**kwargs)
