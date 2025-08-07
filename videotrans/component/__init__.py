# videotrans/component/__init__.py

import importlib

# 1. 定义 __all__ 列表，这对于代码补全和静态分析很重要。
#    这个列表就是你原来 __all__ 的内容，保持不变。
__all__ = [
    "BaiduForm", "ChatgptForm", "DeepLForm", "DeepLXForm", "TencentForm", 
    "ElevenlabsForm", "InfoForm", "AzureForm", "GeminiForm", "SetLineRole", 
    "OttForm", "CloneForm", "SeparateForm", "TtsapiForm", "GPTSoVITSForm", 
    "TransapiForm", "ArticleForm", "    AzurettsForm", "ChatttsForm", "LocalLLMForm",
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

# 2. 定义一个魔法函数 __getattr__
def __getattr__(name):
    """
    这个函数只在尝试访问 component 包中不存在的属性时被调用。
    例如，执行 from videotrans.component import BaiduForm 时，
    Python会调用 __getattr__("BaiduForm")。
    """
    # 检查请求的名称是否在我们期望的 __all__ 列表中
    if name in __all__:
        try:
            # 3. 动态地从 set_form 子模块中导入我们需要的那个类
            #    这行代码实现了真正的“按需加载”
            module = importlib.import_module(".set_form", __name__)
            
            # 4. 从刚加载的模块中获取真正的类/对象
            obj = getattr(module, name)
            
            # 5. (可选但推荐) 将加载的对象设置成本模块的属性，
            #    这样下次再访问它时，就不会再触发 __getattr__，直接从缓存返回。
            globals()[name] = obj
            
            return obj
        except (ImportError, AttributeError) as e:
            # 如果导入失败或属性不存在，则抛出更明确的错误
            raise AttributeError(f"Failed to lazy-load '{name}' from videotrans.component.set_form. Reason: {e}")
    
    # 如果请求的名称不在 __all__ 中，则抛出标准的 AttributeError
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")