from videotrans.configure.config import tr
from videotrans import ChannelProvider

"""
如果想新增渠道
1. 定义一个常量，值为以下递增的序号
2. 在 ID_NAME_DICT 中新增一个键值对，键为新增的常量，值是 ChannelProvider 实例
3. 当前目录下定义一个实际实现代码文件，可直接复制已有渠道文件
"""

GOOGLE_INDEX = 0
MICROSOFT_INDEX = 1
M2M100_INDEX = 2
HYMT2_INDEX = 3

CHATGPT_INDEX = 4
DEEPSEEK_INDEX = 5
GEMINI_INDEX = 6
ZHIPUAI_INDEX = 7
AZUREGPT_INDEX = 8
LOCALLLM_INDEX = 9

OPENROUTER_INDEX = 10
SILICONFLOW_INDEX = 11
AI302_INDEX = 12

QWENMT_INDEX = 13
ZIJIE_INDEX = 14

XIAOMI_INDEX = 15
MINIMAX_INDEX = 16
CAMB_INDEX = 17

DEEPL_INDEX = 18
DEEPLX_INDEX = 19
BAIDU_INDEX = 20
ALI_INDEX = 21

LIBRE_INDEX = 22
TENCENT_INDEX = 23
TRANSAPI_INDEX = 24

LITELLM_INDEX = 25
API_ROUTE_INDEX = 26
CHEAPERINFERENCE_INDEX = 27

# AI 翻译渠道
AI_TRANS_CHANNELS = [
    API_ROUTE_INDEX,
    LITELLM_INDEX,
    CHATGPT_INDEX,
    LOCALLLM_INDEX,
    ZIJIE_INDEX,
    AZUREGPT_INDEX,
    GEMINI_INDEX,
    QWENMT_INDEX,
    AI302_INDEX,
    ZHIPUAI_INDEX,
    SILICONFLOW_INDEX,
    DEEPSEEK_INDEX,
    OPENROUTER_INDEX,
    MINIMAX_INDEX,
    XIAOMI_INDEX,
    HYMT2_INDEX,
    CAMB_INDEX,
    CHEAPERINFERENCE_INDEX
]
# 渠道id对应的设置窗口和sk键名,
# key_name: 存储 SK 或 api url的键，通过 app_cfg.params 调用，如果不存在该值，在使用时报错未填写
# win: 对应 winform 包中的文件名及 ui 包中的文件名，用于调用打开设置窗口
# imp 为该渠道实际代码文件，位于当前目录下

ID_NAME_DICT = {
    GOOGLE_INDEX: ChannelProvider(tr('Google'), imp="._google"),
    MICROSOFT_INDEX: ChannelProvider(tr('Microsoft'), imp="._microsoft"),
    M2M100_INDEX: ChannelProvider(f'M2M100({tr("Built-in")})', imp="._m2m100"),
    HYMT2_INDEX: ChannelProvider(f'Hy-MT2-1.8B({tr("Built-in")})', imp="._hymt2"),

    CHATGPT_INDEX: ChannelProvider(tr('OpenAI ChatGPT'), key_name="chatgpt_key", win="chatgpt", imp="._chatgpt"),
    DEEPSEEK_INDEX: ChannelProvider("DeepSeek", key_name="deepseek_key", win="deepseek", imp="._deepseek"),
    GEMINI_INDEX: ChannelProvider("Gemini AI", key_name="gemini_key", win="gemini", imp="._gemini"),
    ZHIPUAI_INDEX: ChannelProvider(tr('Zhipu AI'), key_name="zhipu_key", win="zhipuai", imp="._zhipuai"),
    AZUREGPT_INDEX: ChannelProvider("Azure AI", key_name="azure_key", win="azure", imp="._azure"),
    LOCALLLM_INDEX: ChannelProvider(tr('Local LLM'), key_name="localllm_api", win="localllm", imp="._localllm"),

    OPENROUTER_INDEX: ChannelProvider("OpenRouter", key_name="openrouter_key", win="openrouter", imp="._openrouter"),
    SILICONFLOW_INDEX: ChannelProvider(tr('SiliconFlow'), key_name="guiji_key", win="siliconflow", imp="._siliconflow"),
    AI302_INDEX: ChannelProvider("302.AI", key_name="ai302_key", win="ai302", imp="._ai302"),

    QWENMT_INDEX: ChannelProvider(tr('Ali-Bailian'), key_name="qwenmt_key", win="qwenmt", imp="._qwenmt"),
    ZIJIE_INDEX: ChannelProvider(tr('VolcEngine LLM'), key_name="zijiehuoshan_key", win="zijiehuoshan",
                                 imp="._huoshan"),

    TENCENT_INDEX: ChannelProvider(tr('Tencent'), key_name="tencent_SecretKey", win="tencent", imp="._tencent"),
    BAIDU_INDEX: ChannelProvider(tr('Baidu'), key_name="baidu_miyue", win="baidu", imp="._baidu"),
    DEEPL_INDEX: ChannelProvider("DeepL", key_name="deepl_authkey", win="deepL", imp="._deepl"),
    DEEPLX_INDEX: ChannelProvider("DeepLx", key_name="deeplx_address", win="deepLX", imp="._deeplx"),
    ALI_INDEX: ChannelProvider(tr('Alibaba Machine Translation'), key_name="ali_key", win="ali", imp="._ali"),

    LIBRE_INDEX: ChannelProvider(f"{tr('LibreTranslate')}({tr('Local')}API)", key_name="libre_address", win="libre",
                                 imp="._libre"),
    MINIMAX_INDEX: ChannelProvider("MiniMax AI", key_name="minimaxi_apikey", win="minimaxi", imp="._minimaxi"),
    XIAOMI_INDEX: ChannelProvider(tr("XiaoMi"), key_name="xiaomi_key", win="xiaomi", imp="._xiaomi"),
    CAMB_INDEX: ChannelProvider("CAMB AI", key_name="camb_api_key", win="cambtts", imp="._camb"),
    TRANSAPI_INDEX: ChannelProvider(tr('Customized API'), key_name="trans_api_url", win="transapi", imp="._transapi"),
    LITELLM_INDEX: ChannelProvider("LiteLLM", key_name="litellm_key", win="litellm", imp="._litellm"),
    API_ROUTE_INDEX: ChannelProvider("API Route", key_name="api_route_key", win="api_route", imp="._api_route"),
    CHEAPERINFERENCE_INDEX: ChannelProvider("Cheaper Inference", key_name="cheaperinference_key", win="cheaperinference",
                                            imp="._cheaperinference"),
}

# 菜单--工具/选项--高级选项-通用设置--LLM纠错所用渠道的显示数据
# LLM 纠错中根据 索引获取 name
LLM_CONCERT_MAP = {
    "chatgpt": tr("OpenAI ChatGPT"),
    "deepseek": "DeepSeek",
    "ai302": "302.AI",
    "azure": "Azure",
    "zijiehuoshan": tr("VolcEngine LLM"),
    "localllm": tr("Local LLM"),
    "minimax": "MiniMax AI",
    "openrouter": "OpenRouter",
    "siliconflow": tr("SiliconFlow"),
    "xiaomi": tr("XiaoMi"),
    "zhipuai": tr("Zhipu AI"),
    "api_route": "API Route",
    "cheaperinference": "Cheaper Inference"
}

LLM_CONCERT_INDEX = {
    "chatgpt": CHATGPT_INDEX,
    "deepseek": DEEPSEEK_INDEX,
    "ai302": AI302_INDEX,
    "azure": AZUREGPT_INDEX,
    "zijiehuoshan": ZIJIE_INDEX,
    "localllm": LOCALLLM_INDEX,
    "minimax": MINIMAX_INDEX,
    "openrouter": OPENROUTER_INDEX,
    "siliconflow": SILICONFLOW_INDEX,
    "xiaomi": XIAOMI_INDEX,
    "zhipuai": ZHIPUAI_INDEX,
    "api_route": API_ROUTE_INDEX,
    "cheaperinference": CHEAPERINFERENCE_INDEX
}

ID_NAME_DICT = dict(sorted(ID_NAME_DICT.items(), key=lambda item: item[0]))
TRANSLASTE_NAME_LIST = [it.name for it in ID_NAME_DICT.values()]
