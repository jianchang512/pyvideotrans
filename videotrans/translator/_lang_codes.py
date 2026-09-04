from videotrans.configure.config import tr
from videotrans.configure.contants import LANG_CODE


# 视频翻译、语音转录、字幕翻译、文字配音(Edge-TTS/OmniVoice外) 用于显示的可选语言 {代码名：语言名,...}
LANGNAME_DICT={}
for code in LANG_CODE.keys():
    LANGNAME_DICT[code]=tr(code)
# 反向按照显示名字查找语言代码
LANGNAME_DICT_REV = {v: k for k, v in LANGNAME_DICT.items()}
