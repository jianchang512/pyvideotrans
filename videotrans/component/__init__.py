import importlib

__all__ = [
    "BaiduForm", "ChatgptForm", "DeepLForm", "DeepLXForm", "TencentForm",
    "ElevenlabsForm", "InfoForm", "AzureForm", "GeminiForm", "SetLineRole",
    "OttForm", "CloneForm", "SeparateForm", "TtsapiForm", "GPTSoVITSForm",
    "TransapiForm", "ArticleForm", "AzurettsForm", "ChatttsForm", "LocalLLMForm",
    "ZijiehuoshanForm", "HebingsrtForm", "DoubaoForm", "FishTTSForm", "CosyVoiceForm",
    "AI302Form", "SetINIForm", "WatermarkForm", "GetaudioForm", "HunliuForm",
    "VASForm", "Fanyisrt", "Recognform", "Peiyinform", "Videoandaudioform",
    "Videoandsrtform", "OpenAITTSForm", "RecognAPIForm", "OpenaiRecognAPIForm",
    "FormatcoverForm", "SubtitlescoverForm", "SubtitleEditer",
    "SttAPIForm", "VolcEngineTTSForm", "F5TTSForm", "DeepgramForm", "ClaudeForm",
    "LibreForm", "AliForm", "ZhipuAIForm", "KokoroForm", "ParakeetForm",
    "ChatterboxForm", "SiliconflowForm", "DeepseekForm", "OpenrouterForm",
    "Peiyinformrole", "QwenTTSForm"
]


def __getattr__(name):
    """
    这个函数只在尝试访问 component 包中不存在的属性时被调用。
    例如，执行 from videotrans.component import BaiduForm 时，
    Python会调用 __getattr__("BaiduForm")。
    """
    if name in __all__:
        try:
            #    这行代码实现“按需加载”
            module = importlib.import_module(".set_form", __name__)

            obj = getattr(module, name)
            globals()[name] = obj

            return obj
        except (ImportError, AttributeError) as e:
            raise AttributeError(f"Failed to lazy-load '{name}' from videotrans.component.set_form. Reason: {e}")

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
