import logging
import re
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.configure.config import tr
from videotrans.translator._base import BaseTrans

RETRY_NUMS = 3
RETRY_DELAY = 5


@dataclass
class Google(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False


    # 实际发出请求获取结果
    @retry( retry=retry_if_not_exception_type(NO_RETRY_EXCEPT),stop=(stop_after_attempt(RETRY_NUMS)),
           wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
           after=after_log(config.logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:

        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        source_code = 'auto' if not self.source_code else self.source_code
        url = f"https://translate.google.com/m?sl={source_code}&tl={self.target_code}&hl={self.target_code}&q={text}"
        config.logger.debug(f'[Google] {self.target_code=} {self.source_code=}')
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        }
        response = requests.get(url, headers=headers,  verify=False)
        response.raise_for_status()
        config.logger.debug(f'[Google]返回code:{response.status_code=}')

        re_result = re.search(r'<div\s+class=\Wresult-container\W>([^<]+?)<', response.text)
        if not re_result or len(re_result.groups()) < 1:
            config.logger.debug(f'[Google]返回数据:{response.text=}')
            raise RuntimeError(tr("Google Translate error"))
        return re_result.group(1)

    def clean_srt(self, srt):
        # 翻译后的srt字幕极大可能存在各种语法错误，符号和格式错乱
        try:
            srt = re.sub(r'(\d{2})\s*[:：]\s*(\d{2})[:：]\s*(\d{2})[\s\,，]+(\d{3})', r'\1:\2:\3,\4', srt,flags=re.I | re.S)
        except re.error:
            pass
        srt = re.sub(r'&gt;', '>', srt,flags=re.I | re.S)
        # ：: 换成 :
        srt = re.sub(r'([：:])\s*', ':', srt,flags=re.I | re.S)
        # ,， 换成 ,
        srt = re.sub(r'([,，])\s*', ',', srt,flags=re.I | re.S)
        srt = re.sub(r'([`’\'\"])\s*', '', srt,flags=re.I | re.S)

        # 秒和毫秒间的.换成,
        srt = re.sub(r'(:\d+)\.\s*?(\d+)', r'\1,\2', srt,flags=re.I | re.S)
        # 时间行前后加空格
        time_line = r'(\s?\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s?)'
        srt = re.sub(time_line, r"\n\1 --> \2\n", srt,flags=re.I | re.S)
        # twenty one\n00:01:18,560 --> 00:01:22,000\n
        srt = re.sub(r'\s?[a-zA-Z ]{3,}\s*?\n?(\d{2}:\d{2}:\d{2}\,\d{3}\s*?\-\->\s*?\d{2}:\d{2}:\d{2}\,\d{3})\s?\n?',
                     "\n" + r'1\n\1\n', srt,flags=re.I | re.S)
        # 去除多余的空行
        srt = "\n".join([it.strip() for it in srt.splitlines() if it.strip()])

        # 删掉以空格或换行连接的多个时间行
        time_line2 = r'(\s\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s)(?:\s*\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s*)'
        srt = re.sub(time_line2, r'\n\1 --> \2\n', srt,flags=re.I | re.S)
        srt_list = [it.strip() for it in srt.splitlines() if it.strip()]

        remove_list = []
        for it in srt_list:
            if len(remove_list) > 0 and str(it) == str(remove_list[-1]):
                if re.match(r'^\d{1,4}$', it):
                    continue
                if re.match(r'\d+:\d+:\d+([,.]\d+)? --> \d+:\d+:\d+([,.]\d+)?',it):
                    continue
            remove_list.append(it)

        srt = "\n".join(remove_list)

        # 行号前添加换行符
        srt = re.sub(r'\s?(\d+)\s+?(\d+:\d+:\d+)', r"\n\n\1\n\2", srt,flags=re.I | re.S)
        return srt.strip().replace('&#39;', '"').replace('&quot;', "'")
