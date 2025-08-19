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
            raise SpeechToTextError(f'{e}:{self.__class__.__name__}') from e
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

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
