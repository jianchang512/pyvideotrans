import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.configure._except import SpeechToTextError
from videotrans.util import tools


@dataclass
class BaseRecogn(BaseCon):
    detect_language: Optional[str] = None
    audio_file: Optional[str] = None
    cache_folder: Optional[str] = None
    model_name: Optional[str] = None
    inst: Optional[Any] = None
    uuid: Optional[str] = None
    is_cuda: Optional[bool] = None
    target_code: Optional[str] = None
    subtitle_type: int = 0

    has_done: bool = field(default=False, init=False)
    error: str = field(default='', init=False)
    api_url: str = field(default='', init=False)
    proxies: Optional = field(default=None, init=False)

    device: str = field(init=False)
    flag: List[str] = field(init=False)
    raws: List = field(default_factory=list, init=False)
    join_word_flag: str = field(init=False)
    jianfan: bool = field(init=False)
    maxlen: int = field(init=False)




    def __post_init__(self):
        super().__init__()
        self.device = 'cuda' if self.is_cuda else 'cpu'
        # 断句标志
        self.flag = [
            ",", ".", "?", "!", ";",
            "，", "。", "？", "；", "！"
        ]
        # 连接字符 中日韩粤语 直接连接，无需空格，其他语言空格连接
        self.join_word_flag = " "

        if self.detect_language and self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            self.maxlen = int(float(config.settings.get('cjk_len', 20)))
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings.get('zh_hant_s') else False
        else:
            self.maxlen = int(float(config.settings.get('other_len', 60)))
            self.jianfan = False

        if not tools.vail_file(self.audio_file):
            raise RuntimeError(f'No {self.audio_file}')

    # run->_exec
    def run(self) -> Union[List[Dict], None]:
        Path(config.TEMP_HOME).mkdir(parents=True, exist_ok=True)
        self._signal(text="")
        try:
            if self.detect_language[:2].lower() in ['zh', 'ja', 'ko', 'yu']:
                self.flag.append(" ")
                self.join_word_flag = ""
            return self._exec()
        except Exception as e:
            config.logger.exception(e, exc_info=True)
            raise
        finally:
            if self.shound_del:
                self._set_proxy(type='del')

    def _exec(self) -> Union[List[Dict], None]:
        pass

    def re_segment_sentences(self, words, langcode=None):

        try:
            from videotrans.translator._chatgpt import ChatGPT
            ob = ChatGPT()
            if self.inst and self.inst.status_text:
                self.inst.status_text = "正在重新断句..." if config.defaulelang == 'zh' else "Re-segmenting..."
            return ob.llm_segment(words, self.inst, config.settings.get('llm_ai_type', 'openai'))
        except json.decoder.JSONDecodeError as e:
            self.inst.status_text = "使用LLM重新断句失败,所用模型可能不支持输出JSON格式" if config.defaulelang == 'zh' else "Re-segmenting Error"
            config.logger.error(f"重新断句失败[JSONDecodeError]，已恢复原样 {e}")
            raise
        except Exception as e:
            self.inst.status_text = "使用LLM重新断句失败" if config.defaulelang == 'zh' else "Re-segmenting Error"
            config.logger.error(f"重新断句失败[except]，已恢复原样 {e}")
            raise


    def get_srtlist(self, raws):
        import zhconv
        jianfan = config.settings.get('zh_hant_s')
        for i in list(raws):
            if len(i['words']) < 1:
                continue

            # 判断当前 whisper已断好的句子， 是否大于 max_speech_duration_s 最大语音持续时间，如何是，则强制断句
            diff=int(i['words'][-1]['end'] * 1000) - int(i['words'][0]['start'] * 1000)
            max_s=int(config.settings.get('max_speech_duration_s', 12))*1000
            if diff>max_s:
                tmp=None
                for w in i['words']:
                    if not tmp:
                        tmp={
                            'text': zhconv.convert(w['word'], 'zh-hans') if jianfan and self.detect_language[:2] == 'zh' else w['word'],
                            'start_time': int(w['start'] * 1000),
                            'end_time': int(w['end'] * 1000)
                        }
                    else:
                        # 当前单词所占时间
                        current_diff=int((w['end']-w['start'])*1000)
                        # 当前tmp[text]末尾或当前word开头是否有标点符号
                        is_flag=tmp['text'][-1] in self.flag or w['word'][0] in self.flag
                        # 当前tmp时长
                        has_time_diff=tmp['end_time']-tmp['start_time']
                        ## 已存在的并且大于500ms，并且（大于允许时长或存在标点）
                        if has_time_diff>500 and ( has_time_diff+current_diff>=max_s or is_flag):
                            self.raws.append(tmp)
                            tmp={
                                'text': zhconv.convert(w['word'], 'zh-hans') if jianfan and self.detect_language[:2] == 'zh' else w['word'],
                                'start_time': int(w['start'] * 1000),
                                'end_time': int(w['end'] * 1000)
                            }
                        else:
                            tmp['text'] += zhconv.convert(w['word'], 'zh-hans') if jianfan and self.detect_language[:2] == 'zh' else w['word']
                            tmp['end_time'] = int(w['end'] * 1000)

                self.raws.append(tmp)
            else:
                tmp = {
                    'text': zhconv.convert(i['text'], 'zh-hans') if jianfan and self.detect_language[:2] == 'zh' else i['text'],
                    'start_time': int(i['words'][0]['start'] * 1000),
                    'end_time': int(i['words'][-1]['end'] * 1000)
                }
                tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
                tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
                self.raws.append(tmp)

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
