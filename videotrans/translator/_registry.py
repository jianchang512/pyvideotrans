from videotrans.configure.config import tr
from videotrans import ChannelProvider
from videotrans.translator._constants import (
    GOOGLE_INDEX, MICROSOFT_INDEX, M2M100_INDEX,
    CHATGPT_INDEX, DEEPSEEK_INDEX, GEMINI_INDEX, ZHIPUAI_INDEX, AZUREGPT_INDEX, LOCALLLM_INDEX,
    OPENROUTER_INDEX, SILICONFLOW_INDEX, AI302_INDEX,
    QWENMT_INDEX, ZIJIE_INDEX,
    TENCENT_INDEX, BAIDU_INDEX, DEEPL_INDEX, DEEPLX_INDEX, ALI_INDEX,
    LIBRE_INDEX, MINIMAX_INDEX, XIAOMI_INDEX, CAMB_INDEX, TRANSAPI_INDEX,
)

_ID_NAME_DICT = {
    GOOGLE_INDEX: ChannelProvider(tr('Google'), imp="._google"),
    MICROSOFT_INDEX: ChannelProvider(tr('Microsoft'), imp="._microsoft"),
    M2M100_INDEX: ChannelProvider(f'M2M100({tr("Local")}{tr("Built-in")})', imp="._m2m100"),

    CHATGPT_INDEX: ChannelProvider(tr('OpenAI ChatGPT'),  key_name="chatgpt_key", win="chatgpt", imp="._chatgpt"),
    DEEPSEEK_INDEX: ChannelProvider("DeepSeek", key_name="deepseek_key", win="deepseek", imp="._deepseek"),
    GEMINI_INDEX: ChannelProvider("Gemini AI", key_name="gemini_key", win="gemini", imp="._gemini"),
    ZHIPUAI_INDEX: ChannelProvider(tr('Zhipu AI'), key_name="zhipu_key", win="zhipuai", imp="._zhipuai"),
    AZUREGPT_INDEX: ChannelProvider("AzureGPT AI", key_name="azure_key", win="azure", imp="._azure"),
    LOCALLLM_INDEX: ChannelProvider(tr('Local LLM'), key_name="localllm_api", win="localllm", imp="._localllm"),

    OPENROUTER_INDEX: ChannelProvider("OpenRouter",  key_name="openrouter_key", win="openrouter", imp="._openrouter"),
    SILICONFLOW_INDEX: ChannelProvider(tr('SiliconFlow'), key_name="guiji_key", win="siliconflow",  imp="._siliconflow"),
    AI302_INDEX: ChannelProvider("302.AI", key_name="ai302_key", win="ai302", imp="._ai302"),

    QWENMT_INDEX: ChannelProvider(tr('Ali-Bailian'), key_name="qwenmt_key", win="qwenmt", imp="._qwenmt"),
    ZIJIE_INDEX: ChannelProvider(tr('VolcEngine LLM'), key_name="zijiehuoshan_key", win="zijiehuoshan",  imp="._huoshan"),

    TENCENT_INDEX: ChannelProvider(tr('Tencent'), key_name="tencent_SecretKey", win="tencent", imp="._tencent"),
    BAIDU_INDEX: ChannelProvider(tr('Baidu'), key_name="baidu_miyue", win="baidu", imp="._baidu"),
    DEEPL_INDEX: ChannelProvider("DeepL", key_name="deepl_authkey", win="deepL", imp="._deepl"),
    DEEPLX_INDEX: ChannelProvider("DeepLx", key_name="deeplx_address", win="deepLX", imp="._deeplx"),
    ALI_INDEX: ChannelProvider(tr('Alibaba Machine Translation'), key_name="ali_key", win="ali", imp="._ali"),

    LIBRE_INDEX: ChannelProvider(f"{tr('LibreTranslate')}({tr('Local')}API)", key_name="libre_address", win="libre", imp="._libre"),
    MINIMAX_INDEX: ChannelProvider("MiniMax AI", key_name="minimax_key", win="minimax", imp="._minimax"),
    XIAOMI_INDEX: ChannelProvider("XiaoMi AI", key_name="xiaomi_key", win="xiaomi", imp="._xiaomi"),
    CAMB_INDEX: ChannelProvider("CAMB AI", key_name="camb_api_key", win="cambtts", imp="._camb"),
    TRANSAPI_INDEX: ChannelProvider(tr('Customized API'), key_name="trans_api_url", win="transapi", imp="._transapi"),
}

_ID_NAME_DICT = dict(sorted(_ID_NAME_DICT.items(), key=lambda item: item[0]))
TRANSLASTE_NAME_LIST = [it.name for it in _ID_NAME_DICT.values()]
