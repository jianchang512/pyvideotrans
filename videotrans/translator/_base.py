import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from tenacity import RetryError

from videotrans import translator
from videotrans.configure.base import BaseCon
from videotrans.configure.config import tr, settings, logger, TEMP_ROOT
from videotrans.task.taskcfg import SrtItem
from videotrans.util.help_srt import get_subtitle_from_srt,cleartext
from videotrans.util.help_misc import get_md5,serial

@dataclass
class BaseTrans(BaseCon):
    # 翻译渠道
    translate_type: int = 0
    # 存放待翻译的字幕列表字典
    text_list: List[SrtItem] = None
    # 唯一任务id
    uuid: Optional[str] = None
    # 测试时不使用缓存
    is_test: bool = False
    # 原始语言代码
    source_code: str = ""
    # 目标语言代码
    target_code: str = ""
    # 对于AI渠道，这是目标语言的自然语言表达，其他渠道等于 target_code
    target_language_name: str = ""

    # 翻译API 地址
    api_url: str = field(default="", init=False)
    # 模型名
    model_name: str = field(default="", init=False)
    # 同时翻译的字幕行数量
    trans_thread: int = 5
    # 翻译后暂停秒
    wait_sec: float = float(settings.get('translation_wait', 0))


    #  是AI翻译渠道并且选中了以完整srt格式字幕发送
    aisendsrt: bool = False

    def __post_init__(self):
        super().__post_init__()
        Path(TEMP_ROOT + f'/translate_cache').mkdir(parents=True, exist_ok=True)
        self.aisendsrt = settings.get('aisendsrt', False) and self.translate_type in translator.AI_TRANS_CHANNELS
        if self.aisendsrt:
            self.trans_thread = int(settings.get('aitrans_thread', 20)) if not settings.get('aitrans_context') else len(self.text_list)
        else:
            self.trans_thread = int(settings.get('trans_thread', 5))

    def _item_task(self, data: Union[List[str], str]):
        raise NotImplemented()

    # 实际操作 run  -> run_text|run_srt -> _item_task
    def run(self) -> List[SrtItem]:
        if hasattr(self, '_download'):
            self._download()
        try:
            if not self.aisendsrt:
                # 是文字列表  [str,...]
                source_text = [t['text'].replace("\n", " ") for t in self.text_list]
                return self._run_text(
                    [source_text[i:i + self.trans_thread] for i in range(0, len(source_text), self.trans_thread)])
            # 是srt格式字幕列表 [SrtItem,...]
            return self._run_srt(
                    [self.text_list[i:i + self.trans_thread] for i in range(0, len(self.text_list), self.trans_thread)])
        except RetryError as e:
            raise e.last_attempt.exception()
        finally:
            if hasattr(self, '_unload'):
                self._unload()


    def _run_text(self, split_source_text: List[List[str]]):
        # 传统翻译渠道或AI翻译渠道以按行形式翻译
        """
        split_source_text=[
            ["字幕文本1","字幕文本2",...],
            ["字幕文本1","字幕文本2",...],
            ["字幕文本1","字幕文本2",...],
            ...
        ]
        """
        target_list = []
        logger.debug(f'以纯文本行形式翻译，每次翻译{self.trans_thread}行，翻译后暂停{self.wait_sec}s')
        for i, it in enumerate(split_source_text):
            """ it=['你好啊我的朋友','第二行']  此时 _item_task 接收的是 list[str] """
            if self._exit(): return
            self.signal(text=tr('starttrans') + f' {i} ')
            result = self._get_cache(it)
            if not result:
                result = cleartext(self._item_task(it))
                self._set_cache(it, result)
            sep_res = result.split("\n")
            for x, result_item in enumerate(sep_res):
                if x < len(it):
                    target_list.append(result_item.strip())
                    self.signal(text=result_item + "\n", type='subtitle')
            # 行数不匹配填充空行
            if len(sep_res) < len(it):
                logger.debug(f'行数不匹配，原始：{len(it)}, 结果：{len(sep_res)}\n{it=}\n{sep_res=}')
                tmp = ["" for x in range(len(it) - len(sep_res))]
                target_list += tmp
            time.sleep(self.wait_sec)
        max_i = len(target_list)
        logger.debug(f'原始行数:{len(self.text_list)},翻译后行数:{max_i}')
        _empty_line = 0
        for i, it in enumerate(self.text_list):
            text = target_list[i].strip() if i < max_i else ""
            if not text:
                _empty_line += 1
            self.text_list[i]['text'] = text

        if _empty_line >= len(self.text_list):
            from videotrans.configure.excepts import TranslateSrtError
            raise TranslateSrtError(tr("Translate result is empty")+f'\n{self.api_url}')
        return self.text_list

    # 发送完整字幕格式内容进行翻译
    # 此时 _item_task 接收的是 srt 格式的字符串
    def _run_srt(self, split_source_text: List[List[SrtItem]]):
        """
        split_source_text=[
            [{text:"",start_time:"",line:""},{...},...]
            ...
        ]
        """
        logger.debug(f'以SRT字幕块翻译，每次翻译 {self.trans_thread} 条字幕块，翻译后暂停{self.wait_sec}s')
        from videotrans.configure.excepts import TranslateSrtError
        raws_list = []
        for i, it in enumerate(split_source_text):
            if self._exit(): return
            self.signal(text=tr('starttrans') + f' {i} ')
            # 组成合法的srt格式字符串
            srt_str = "\n\n".join(
                [f"{srt_dict['line']}\n{srt_dict['time']}\n{srt_dict['text'].strip()}" for srt_dict in it])
            result = self._get_cache(srt_str)
            if not result:
                result = self._item_task(srt_str)
                if not result.strip():
                    raise TranslateSrtError(tr("Translate result is empty")+f'\n{self.api_url}')
                self._set_cache(it, result)

            self.signal(text=result, type='subtitle')
            raws_list.extend(get_subtitle_from_srt(result, is_file=False))
            time.sleep(self.wait_sec)

        _empty_line = 0
        for it in raws_list:
            if not it['text'].strip():
                _empty_line += 1
        if _empty_line >= len(raws_list):
            raise TranslateSrtError(tr("Translate result is empty")+f'\n{self.api_url}')
        logger.debug(f'原始字幕行数：{len(self.text_list)}, 翻译后行数:{len(raws_list)}')
        return raws_list

    def _set_cache(self, it, res_str):
        if not res_str.strip(): return
        file_cache = TEMP_ROOT + f'/translate_cache/{self._get_key(it)}.txt'
        Path(file_cache).write_text(res_str, encoding='utf-8')

    def _get_cache(self, it) -> Union[str,None]:
        if self.is_test: return
        file_cache = TEMP_ROOT + f'/translate_cache/{self._get_key(it)}.txt'
        if Path(file_cache).exists():
            logger.debug(f'本次跳过翻译，使用缓存')
            return Path(file_cache).read_text(encoding='utf-8')
        return

    def _get_key(self, it) -> str:
        it=serial(it)
        key_str = f'{self.translate_type}-{self.api_url}-{self.aisendsrt}-{self.model_name}-{self.source_code}-{self.target_code}-{it}'
        return get_md5(key_str)
