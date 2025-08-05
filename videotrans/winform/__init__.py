"""
from . import  baidu, ai302,  fn_audiofromvideo, azure, azuretts, chatgpt, chattts, \
    clone, \
    cosyvoice, deepL, deepLX, doubao, elevenlabs, fn_fanyisrt, fishtts, gemini, gptsovits, fn_hebingsrt, \
    fn_hunliu, \
    localllm, ott, fn_peiyin, fn_recogn, fn_separate, setini, tencent, transapi, ttsapi, fn_vas, fn_watermark,  zijiehuoshan, fn_videoandaudio, fn_videoandsrt, fn_formatcover, openaitts, recognapi,sttapi, \
    openairecognapi, \
    fn_subtitlescover, fn_editer,volcenginetts,f5tts,deepgram,claude,libre,ali,zhipuai,siliconflow,kokoro,parakeet,chatterbox,deepseek,openrouter,fn_peiyinrole,qwentts
    
"""
# videotrans/winform/__init__.py

import importlib

# 一个字典，映射菜单项的名字到它对应的模块名
# 这个映射关系是你原来 from . import ... 列表的“字符串”版本
_module_map = {
    "baidu": ".baidu", "ai302": ".ai302", "fn_audiofromvideo": ".fn_audiofromvideo", 
    "azure": ".azure", "azuretts": ".azuretts", "chatgpt": ".chatgpt", 
    "chattts": ".chattts", "clone": ".clone", "cosyvoice": ".cosyvoice", 
    "deepL": ".deepL", "deepLX": ".deepLX", "doubao": ".doubao", 
    "elevenlabs": ".elevenlabs", "fn_fanyisrt": ".fn_fanyisrt", "fishtts": ".fishtts", 
    "gemini": ".gemini", "gptsovits": ".gptsovits", "fn_hebingsrt": ".fn_hebingsrt", 
    "fn_hunliu": ".fn_hunliu", "localllm": ".localllm", "ott": ".ott", 
    "fn_peiyin": ".fn_peiyin", "fn_recogn": ".fn_recogn", "fn_separate": ".fn_separate", 
    "setini": ".setini", "tencent": ".tencent", "transapi": ".transapi", 
    "ttsapi": ".ttsapi", "fn_vas": ".fn_vas", "fn_watermark": ".fn_watermark", 
    "zijiehuoshan": ".zijiehuoshan", "fn_videoandaudio": ".fn_videoandaudio", 
    "fn_videoandsrt": ".fn_videoandsrt", "fn_formatcover": ".fn_formatcover", 
    "openaitts": ".openaitts", "recognapi": ".recognapi", "sttapi": ".sttapi", 
    "openairecognapi": ".openairecognapi", "fn_subtitlescover": ".fn_subtitlescover", 
    "fn_editer": ".fn_editer", "volcenginetts": ".volcenginetts", "f5tts": ".f5tts", 
    "deepgram": ".deepgram", "claude": ".claude", "libre": ".libre", "ali": ".ali", 
    "zhipuai": ".zhipuai", "siliconflow": ".siliconflow", "kokoro": ".kokoro", 
    "parakeet": ".parakeet", "chatterbox": ".chatterbox", "deepseek": ".deepseek", 
    "openrouter": ".openrouter", "fn_peiyinrole": ".fn_peiyinrole", "qwentts": ".qwentts"
}

_loaded_modules = {} # 用于缓存已经加载过的模块

def get_win(name):
    """
    根据名字按需（懒加载）导入并返回窗口模块。
    """
    # 如果已经加载过，直接从缓存返回，避免重复导入
    if name in _loaded_modules:
        return _loaded_modules[name]

    # 检查名字是否存在于映射中
    if name not in _module_map:
        raise AttributeError(f"No winform module named '{name}' found.")

    # 动态导入模块
    # importlib.import_module的第二个参数'.'表示相对导入，相对于当前包(winform)
    try:
        module = importlib.import_module(_module_map[name], __name__)
        _loaded_modules[name] = module # 存入缓存
        return module
    except ImportError as e:
        raise ImportError(f"Could not import winform module '{name}': {e}")