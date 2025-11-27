import importlib

_module_map = {
"ai302":".ai302",
"ali":".ali",
"azure":".azure",
"azuretts":".azuretts",
"baidu":".baidu",
"chatgpt":".chatgpt",
"chatterbox":".chatterbox",
"chattts":".chattts",
"clone":".clone",
"cosyvoice":".cosyvoice",
"deepgram":".deepgram",
"deepL":".deepL",
"deepLX":".deepLX",
"deepseek":".deepseek",
"doubao":".doubao",
"doubao2":".doubao2",
"elevenlabs":".elevenlabs",
"f5tts":".f5tts",
"fishtts":".fishtts",
"fn_audiofromvideo":".fn_audiofromvideo",
"fn_fanyisrt":".fn_fanyisrt",
"fn_formatcover":".fn_formatcover",
"fn_hebingsrt":".fn_hebingsrt",
"fn_hunliu":".fn_hunliu",
"fn_peiyin":".fn_peiyin",
"fn_peiyinrole":".fn_peiyinrole",
"fn_recogn":".fn_recogn",
"fn_separate":".fn_separate",
"fn_subtitlescover":".fn_subtitlescover",
"fn_vas":".fn_vas",
"fn_videoandaudio":".fn_videoandaudio",
"fn_videoandsrt":".fn_videoandsrt",
"fn_watermark":".fn_watermark",
"gemini":".gemini",
#"googlecloud":".googlecloud",
"gptsovits":".gptsovits",
"kokoro":".kokoro",
"libre":".libre",
"localllm":".localllm",
"minimaxi":".minimaxi",
"openairecognapi":".openairecognapi",
"openaitts":".openaitts",
"openrouter":".openrouter",
"ott":".ott",
"parakeet":".parakeet",
"qwenmt":".qwenmt",
"qwentts":".qwentts",
"recognapi":".recognapi",
"setini":".setini",
"siliconflow":".siliconflow",
"sttapi":".sttapi",
"tencent":".tencent",
"transapi":".transapi",
"ttsapi":".ttsapi",
"volcenginetts":".volcenginetts",
"zhipuai":".zhipuai",
"zijiehuoshan":".zijiehuoshan",
"zijierecognmodel":".zijierecognmodel",
"whisperxapi":".whisperxapi",
}

_loaded_modules = {}  # 用于缓存已经加载过的模块


def get_win(name):
    """
    根据名字按需（懒加载）导入并返回窗口模块。
    """
    if name in _loaded_modules:
        return _loaded_modules[name]

    if name not in _module_map:
        raise AttributeError(f"No winform module named '{name}' found.")

    # importlib.import_module的第二个参数'.'表示相对导入，相对于当前包(winform)
    try:
        module = importlib.import_module(_module_map[name], __name__)
        _loaded_modules[name] = module
        return module
    except ImportError as e:
        raise ImportError(f"Could not import winform module '{name}': {e}")
