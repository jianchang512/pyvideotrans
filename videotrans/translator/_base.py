import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from videotrans import translator
from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.configure.config import tr
from videotrans.util import tools


@dataclass
class BaseTrans(BaseCon):
    # 翻译渠道
    translate_type:int=0
    # 存放待翻译的字幕列表字典,{text,time,line}
    text_list: List[dict] = field(default_factory=list)
    # 唯一任务id
    uuid: Optional[str] = None
    # 测试时不使用缓存
    is_test: bool = False
    # 原始语言代码
    source_code: str = ""
    #目标语言代码
    target_code: str = ""
    # 对于AI渠道，这是目标语言的自然语言表达，其他渠道等于 target_code
    target_language_name: str = ""

    # 翻译API 地址
    api_url: str = field(default="", init=False)
    # 模型名
    model_name: str = field(default="", init=False)

    # 同时翻译的字幕行数量
    trans_thread: int = int(config.settings.get('trans_thread', 5))
    # 翻译后暂停秒
    wait_sec: float = float(config.settings.get('translation_wait', 0))
    aisendsrt: bool = False

    def __post_init__(self):
        super().__post_init__()
        #是AI翻译渠道并且选中了以完整字幕发送
        if config.settings.get('aisendsrt', False) and self.translate_type in translator.AI_TRANS_CHANNELS:
            self.aisendsrt=True
        print(f'{self.aisendsrt=}')

    # 发出请求获取内容 data=[text1,text2,text] | text
    # 按行翻译时，data=[text_str,...]
    # AI发送完整字幕时 data=srt_string
    def _item_task(self, data: Union[List[str], str]) -> str:
        pass

    def _exit(self):
        if config.exit_soft or (config.current_status != 'ing' and config.box_trans != 'ing' and not self.is_test):
            return True
        return False

    # 实际操作 run|runsrt -> _item_task
    def run(self) -> Union[List, str, None]:
        # 开始对分割后的每一组进行处理
        Path(config.TEMP_HOME).mkdir(parents=True, exist_ok=True)
        self._signal(text="")
        config.logger.info(f'#### 字幕翻译前准备1:{self.aisendsrt=},{self.trans_thread=}')

        # 如果是不是以 完整字幕格式发送，则组成字符串列表，否则组成 [dict,dict] 列表，每个dict都是字幕行信息
        if not self.aisendsrt:
            # 是文字列表  [text_str,...]
            source_text = [t['text'] for t in self.text_list]
        else:
            # 是srt格式字幕列表 [{text,line,time},...]
            source_text=self.text_list

        split_source_text = [source_text[i:i + self.trans_thread] for i in range(0, len(self.text_list), self.trans_thread)]
        config.logger.info(f'字幕翻译前准备2')
        from tenacity import RetryError
        try:
            if self.aisendsrt:
                return self._run_srt(split_source_text)
            return self._run_text(split_source_text)
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            raise

    def _run_text(self,split_source_text):
        # 传统翻译渠道或AI翻译渠道以按行形式翻译
        target_list=[]
        for i, it in enumerate(split_source_text):
            """ it=['你好啊我的朋友','第二行'] 
                此时 _item_task 接收的是 list[str]
            """
            config.logger.info(f'##### [以文字行形式翻译]')
            if self._exit(): return

            result = self._get_cache(it)
            if not result:
                result = tools.cleartext(self._item_task(it))
                self._set_cache(it, result)


            sep_res = result.split("\n")

            for x, result_item in enumerate(sep_res):
                if x < len(it):
                    target_list.append(result_item.strip())
                    self._signal(
                        text=result_item + "\n",
                        type='subtitle')
                    self._signal(
                        text=tr('starttrans') + f' {i * self.trans_thread + x + 1} ')
            # 行数不匹配填充空行
            if len(sep_res) < len(it):
                tmp = ["" for x in range(len(it) - len(sep_res))]
                target_list += tmp

            time.sleep(self.wait_sec)

        max_i = len(target_list)
        for i, it in enumerate(self.text_list):
            if i < max_i:
                self.text_list[i]['text'] = target_list[i]
            else:
                self.text_list[i]['text'] = ""
        return self.text_list

    # 发送完整字幕格式内容进行翻译
    # 此时 _item_task 接收的是 srt格式的字符串
    def _run_srt(self,split_source_text):
        result_srt_str_list = []
        for i, it in enumerate(split_source_text):
            # 是字幕类表，此时 it=[{text,line,time}]
            config.logger.info(f'#### [以完整SRT格式发送翻译]，it应是dict列表')
            if self._exit(): return
            for j, srt in enumerate(it):
                it[j]['text'] = srt['text'].strip().replace("\n", " ")
            # 组成合法的srt格式字符串
            srt_str = "\n\n".join(
                [f"{srt_dict['line']}\n{srt_dict['time']}\n{srt_dict['text'].strip()}" for srt_dict in it])
            result = self._get_cache(srt_str)
            if not result:
                result = self._item_task(srt_str)
                if not result.strip():
                    raise RuntimeError(tr("Translate result is empty"))
                self._set_cache(it, result)


            self._signal(text=result, type='subtitle')
            result_srt_str_list.append(result)

            time.sleep(self.wait_sec)

        raws_list = tools.get_subtitle_from_srt("\n\n".join(result_srt_str_list), is_file=False)

        # 双语翻译结果，只取最后一行
        config.logger.info(f'原始返回SRT翻译结果：{result_srt_str_list=}\n整理为list[dict]后的结果:{raws_list=}')
        for i, it in enumerate(raws_list):
            it['text'] = it['text'].strip().split("\n")
            if it['text']:
                it['text'] = it['text'][-1]
            raws_list[i] = it
        return raws_list

    def _set_cache(self, it, res_str):
        if not res_str.strip():
            return
        key_cache = self._get_key(it)

        file_cache = config.TEMP_DIR + f'/translate_cache/{key_cache}.txt'
        if not Path(config.TEMP_DIR + f'/translate_cache').is_dir():
            Path(config.TEMP_DIR + f'/translate_cache').mkdir(parents=True, exist_ok=True)
        Path(file_cache).write_text(res_str, encoding='utf-8')

    def _get_cache(self, it):
        if self.is_test: return None
        key_cache = self._get_key(it)
        file_cache = config.TEMP_DIR + f'/translate_cache/{key_cache}.txt'
        if Path(file_cache).exists():
            return Path(file_cache).read_text(encoding='utf-8')
        return None

    def _get_key(self, it):
        Path(config.TEMP_DIR + '/translate_cache').mkdir(parents=True, exist_ok=True)
        key_str=f'{self.translate_type}-{self.api_url}-{self.aisendsrt}-{self.model_name}-{self.source_code}-{self.target_code}-{it if isinstance(it, str) else json.dumps(it)}'
        return tools.get_md5(key_str)
