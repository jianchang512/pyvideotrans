# -*- coding: utf-8 -*-
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import settings,params,logger
from videotrans.configure.excepts import NO_RETRY_EXCEPT, TranslateSrtError, StopTask
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


@dataclass
class Baidu(BaseTrans):

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join(data)
        salt = int(time.time())
        strtext = f"{params.get('baidu_appid','')}{text}{salt}{params.get('baidu_miyue','')}"
        md5 = hashlib.md5()
        md5.update(strtext.encode('utf-8'))
        sign = md5.hexdigest()
        tocode = self.target_code
        if tocode.lower() == 'zh-tw':
            tocode = 'cht'
        elif tocode.lower() == 'zh-cn':
            tocode = 'zh'
        requrl = f"http://api.fanyi.baidu.com/api/trans/vip/translate?q={text}&from=auto&to={tocode}&appid={params.get('baidu_appid','')}&salt={salt}&sign={sign}"

        logger.debug(f'[Baidu]请求数据:{requrl=}')
        resraw = requests.get(requrl)
        resraw.raise_for_status()
        res = resraw.json()
        logger.debug(f'[Baidu]返回响应:{res=}')

        if "error_code" in res or "trans_result" not in res or len(res['trans_result']) < 1:
            logger.debug(f'Baidu 返回响应:{resraw}')
            raise StopTask('请检查appid是否正确，或是否已开通对应服务服务是否开通' if int(res.get('error_code',0))==52003 else res['error_msg'])

        result = [tools.cleartext(tres['dst']) for tres in res['trans_result']]
        if not result or len(result) < 1:
            raise TranslateSrtError(f'no result:{res=}')
        return "\n".join(result)
