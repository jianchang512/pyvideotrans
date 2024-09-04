import os
import time
from typing import Union, List

import openai
import requests

from videotrans.configure import config
from videotrans.util import tools


class BaseTrans:

    def __init__(self,text_list:Union[List,str]="",target_language="en", *, inst=None,  source_code="", uuid=None,is_test=False):
        # 目标语言，语言代码或文字名称
        self.target_language=target_language
        # trans_create实例
        self.inst=inst
        # 原始语言代码
        self.source_code=source_code
        # 任务文件绑定id
        self.uuid=uuid
        # 用于测试
        self.is_test=is_test
        #
        self.error=""
        # 同时翻译字幕条数
        self.trans_thread=int(config.settings.get('trans_thread',5))
        #出错重试次数
        self.retry=int(config.settings.get('retries',2))
        # 每次翻译请求完成后等待秒数
        self.wait_sec = int(config.settings.get('translation_wait',0.1))
        # 当前已重试次数
        self.iter_num=0
        # 原始需翻译的字符串或字幕list
        self.text_list=text_list
        # 翻译后的结果文本存储
        self.target_list=[]
        # 如果 text_list 不是字符串则是字幕格式
        self.is_srt= False if isinstance(text_list, str) else True
        # 整理待翻译的文字为 List[str]
        source_text = text_list.strip().split("\n") if not self.is_srt else [t['text'] for t in text_list]
        self.split_source_text= [source_text[i:i + self.trans_thread] for i in range(0, len(source_text), self.trans_thread)]
        # True=如果未设置环境代理变量，仅仅在网络代理文本框中填写了代理，则请求完毕需删除代理恢复原样
        self.shound_del=False
        self.proxies=None
    # 设置和删除代理
    def _set_proxy(self,type=None)->Union[str,None]:
        if type == 'del' and self.shound_del:
            del os.environ['http_proxy']
            del os.environ['https_proxy']
            del os.environ['all_proxy']
            self.shound_del = False
            return None
        if type == 'set':
            raw_proxy = os.environ.get('http_proxy')
            if not raw_proxy:
                proxy = tools.set_proxy()
                if proxy:
                    self.shound_del = True
                    os.environ['http_proxy'] = proxy
                    os.environ['https_proxy'] = proxy
                    os.environ['all_proxy'] = proxy
                    return proxy
        return None


    # 发出请求获取内容
    def _get_content(self,data:Union[List[str],str])->str:
        raise Exception('The method must be')


    # 实际操作
    def run(self)->Union[List,str]:
        # 开始对分割后的每一组进行处理
        for i, it in enumerate(self.split_source_text):
            print(f'{i=},{it=}')
            # 失败后重试 self.retry 次
            while 1:
                if config.exit_soft or (
                        config.current_status != 'ing' and config.box_trans != 'ing' and not self.is_test):
                    return None
                if self.iter_num > self.retry:
                    raise Exception(
                        f'{self.iter_num}{"次重试后依然出错" if config.defaulelang == "zh" else " retries after error persists "}:{self.error}')

                self.iter_num += 1
                if self.iter_num > 1:
                    tools.set_process(
                        f"第{self.iter_num}次出错重试" if config.defaulelang == 'zh' else f'{self.iter_num} retries after error',
                        type="logs",
                        uuid=self.uuid)
                    time.sleep(10)
                    continue

                try:
                    result = self._get_content(it)
                    if self.inst and self.inst.precent < 75:
                        self.inst.precent += 0.01
                    if not self.is_srt:
                        self.target_list.append(result)
                        self.iter_num=0
                        self.error=''
                        break
                    sep_res = tools.cleartext(result).split("\n")
                    raw_len = len(it)
                    sep_len = len(sep_res)
                    # 如果返回结果相差原字幕仅少一行，对最后一行进行拆分
                    if sep_len + 1 == raw_len:
                        config.logger.error('如果返回结果相差原字幕仅少一行，对最后一行进行拆分')
                        sep_res = tools.split_line(sep_res)
                        if sep_res:
                            sep_len = len(sep_res)

                    # 如果返回数量和原始语言数量不一致，则重新切割
                    if sep_len < raw_len:
                        config.logger.error(f'翻译前后数量不一致，需要重新按行翻译')
                        sep_res = []
                        for it_n in it:
                            time.sleep(self.wait_sec)
                            t = self._get_content(it_n.strip())
                            sep_res.append(t)

                    for x, result_item in enumerate(sep_res):
                        if x < len(it):
                            self.target_list.append(result_item.strip())
                            tools.set_process(
                                result_item + "\n",
                                type='subtitle',
                                uuid=self.uuid)
                            tools.set_process(
                                config.transobj['starttrans'] + f' {i * self.trans_thread + x + 1} ',
                                type="logs",
                                uuid=self.uuid)
                    if len(sep_res) < len(it):
                        tmp = ["" for x in range(len(it) - len(sep_res))]
                        self.target_list += tmp
                except requests.ConnectionError as e:
                    self.error = str(e)
                except openai.APIError as e:
                    self.error = str(e)
                except ConnectionError as e:
                    self.error = str(e)
                except Exception as e:
                    self.error = str(e)
                    time.sleep(self.wait_sec)
                    config.logger.error(f'翻译出错:暂停{self.wait_sec}s')
                else:
                    # 成功 未出错
                    self.error = ''
                    self.iter_num = 0
                finally:
                    time.sleep(self.wait_sec)
                if self.iter_num == 0:
                    # 未出错跳过while
                    break

        # 恢复原代理设置
        if self.shound_del:
            self._set_proxy(type='del')
        # text_list是字符串
        if not self.is_srt:
            return "\n".join(self.target_list)

        max_i = len(self.target_list)
        # 出错次数大于原一半
        if max_i < len(self.text_list) / 2:
            raise Exception(f'{config.transobj["fanyicuowu2"]}')

        for i, it in enumerate(self.text_list):
            if i < max_i:
                self.text_list[i]['text'] = self.target_list[i]
            else:
                self.text_list[i]['text'] = ""
        return self.text_list

