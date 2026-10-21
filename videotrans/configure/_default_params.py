"""
需要配置信息的渠道的默认参数 在此集中管理

"""
from typing import Dict, Any

from videotrans.configure.constants import (
    GEMINI_TTS_MODELS,
    XIAOMI_TTS_MODELS, ELEVENLABS_TTS_MODELS,
    MINIMAX_TTS_MODELS,
    SILICONFLOW_TTS_MODELS, OPENROUTER_TTS_MODELS, OPENAIRECOGNAPI_MODELS,
    MINIMAX_MODELS,
    XIAOMI_MODELS, AI302_MODELS, BAILIAN_MODELS, CHATGPT_MODELS, AZURE_MODELS, LOCALLLM_MODELS,
    ZHIPUAI_MODELS, DEEPSEEK_MODELS, OPENROUTER_MODELS, LITELLM_MODELS, APIROUTE_MODELS, CheaperInference_MODELS,
    SILICONFLOW_MODELS, ZIJIEHUOSHAN_MODELS, GEMINI_MODELS, OPENAI_TTS_MODELS, INFISTAR_MODELS, ATLASCLOUD_MODELS

)

_default = {
    "ai302": {
        # 302.ai
        "ai302_key": "",
        "ai302_model": AI302_MODELS.split(',')[0],
    },
    "api_route": {
        # api-route.com
        "api_route_key": "",
        "api_route_model": APIROUTE_MODELS.split(',')[0],
        "api_route_max_token": 16384,
    },
    "atlascloud": {
        "atlascloud_key": "",
        "atlascloud_model": ATLASCLOUD_MODELS.split(',')[0],
        "atlascloud_max_token": 16384,
    },
    "audiocpp":{
        "audiocpp_model":"omnivoice"#默认使用TTS模型
    },
    "azure": {
        # azure gpt
        "azure_api": "",
        "azure_key": "",
        "azure_model": AZURE_MODELS.split(',')[0],
    },
    "azuretts":{
        "azuretts_key":"",
        "azuretts_region":""
    },
    "bailian": {
        # 千问百炼 API
        "bailian_key": "",
        "bailian_spaceid": "",
        "bailian_domains": "",
        "bailian_model": BAILIAN_MODELS.split(',')[0],
        "bailian_ttsmodel": "qwen3-tts-flash",
        "bailian_reasoning_effort":"default"
    },
    "chatgpt": {
        # openai chatgpt
        "chatgpt_api": "",
        "chatgpt_key": "",
        "chatgpt_reasoning_effort": "default",
        "chatgpt_max_token": 16384,
        "chatgpt_model": CHATGPT_MODELS.split(',')[0],
    },
    "cheaperinference": {
        "cheaperinference_key": "",
        "cheaperinference_model": CheaperInference_MODELS.split(',')[0],
        "cheaperinference_max_token": 16384,
    },
    "deepseek": {
        # deepseek
        "deepseek_key": "",  # SK 密钥
        "deepseek_reasoning_effort":"none",
        "deepseek_model": DEEPSEEK_MODELS.split(',')[0],
        "deepseek_max_token": 16384,  # 最大输出64k
    },
    "fishaudio":{
        "fishaudio_key":"",
        "fishaudio_model":"s2.1-pro"
    },
    "gemini": {
        # gemini
        "gemini_key": "",
        "gemini_model": GEMINI_MODELS.split(',')[0],
        "gemini_max_token": 16384,
        "gemini_ttsstyle": "",
        "gemini_ttsmodel": GEMINI_TTS_MODELS.split(',')[0],
    },
    "infistar": {
        "infistar_key": "",
        "infistar_model": INFISTAR_MODELS.split(',')[0],
        "infistar_max_token": 16384,
    },
    "litellm": {
        # liteLLM
        "litellm_api": 'http://localhost:4000/v1',
        "litellm_key": "",
        "litellm_reasoning_effort": "default",
        "litellm_model": LITELLM_MODELS.split(',')[0],
        "litellm_max_token": 16384,
    },
    "localllm": {
        # localLLM
        "localllm_api": "",
        "localllm_key": "",
        "localllm_reasoning_effort": "default",
        "localllm_model": LOCALLLM_MODELS.split(',')[0],
        "localllm_max_token": 8192,
    },
    "minimaxi": {
        # minimax
        "minimaxi_key": "",
        "minimaxi_api": "api.minimax.cn",
        "minimaxi_emotion": "",
        "minimaxi_tts_model": MINIMAX_TTS_MODELS.split(',')[0],
        "minimaxi_text_model": MINIMAX_MODELS.split(',')[0],
        "minimaxi_max_token": 16384,
        "minimaxi_reasoning_effort":"default",
    },
    "openairecognapi": {
        # openai speech to text
        "openairecognapi_api": "",
        "openairecognapi_key": "",
        "openairecognapi_prompt": "",
        "openairecognapi_model": OPENAIRECOGNAPI_MODELS.split(',')[0],
    },
    "openaitts": {
        # openai tts
        "openaitts_api": "",
        "openaitts_key": "",
        "openaitts_model": OPENAI_TTS_MODELS.split(',')[0],
        "openaitts_role": "",
        "openaitts_instructions": "",
    },
    "openrouter": {
        # openrouter.ai
        "openrouter_key": "",
        "openrouter_reasoning_effort": "default",
        "openrouter_model": OPENROUTER_MODELS.split(',')[0],
        "openrouter_tts_model": OPENROUTER_TTS_MODELS.strip().split(',')[0],
        "openrouter_max_token": 16384,  # 最大输出16k
    },
    "siliconflow": {
        # 硅基流动
        "siliconflow_key": "",
        "siliconflow_reasoning_effort":"default",
        "siliconflow_model": SILICONFLOW_MODELS.split(',')[0],
        "siliconflow_tts_model": SILICONFLOW_TTS_MODELS.strip().split(',')[0],
        "siliconflow_max_token": 16384,  # 最大输出16k
    },
    "xiaomi": {
        # 小米 mimo
        "xiaomi_key": "",
        "xiaomi_ttsmodel": XIAOMI_TTS_MODELS.split(',')[0],
        "xiaomi_reasoning_effort":"default",
        "xiaomi_model": XIAOMI_MODELS.split(',')[0],
        "xiaomi_max_token": 16384,
    },
    "zhipuai": {
        # 智谱AI
        "zhipuai_key": "",
        "zhipuai_reasoning_effort":"default",
        "zhipuai_model": ZHIPUAI_MODELS.split(',')[0],
        "zhipuai_max_token": 16384,
    },
    "zijiehuoshan": {
        # 字节火山大模型
        "zijiehuoshan_key": "",
        "zijiehuoshan_reasoning_effort":"default",
        "zijiehuoshan_max_token": 16384,
        "zijiehuoshan_model": ZIJIEHUOSHAN_MODELS.split(',')[0],
    },
    "ali": {
        # 阿里机器翻译
        "ali_id": "",
        "ali_key": "",
    },
    "audexum": {
        "audexum_key": "",
    },

    "baidu": {
        # 百度翻译
        "baidu_appid": "",
        "baidu_key": "",
    },
    "chatterbox": {
        # 内置
        "chatterbox_cfg_weight": 0.5,
        "chatterbox_exaggeration": 0.5,
    },
    "chattts": {"chattts_api": "http://127.0.0.1:9966", },
    "clone": {
        # clone-voice
        "clone_api": "http://127.0.0.1:9988",
        "clone_voicelist": "No,clone",
    },
    "confuciustts": {
        "confuciustts_url": "http://127.0.0.1:7860",
    },
    "cosyvoice": {
        "cosyvoice_url": "http://127.0.0.1:8000",
    },
    "deepgram": {
        # deepgram.com
        "deepgram_key": "",
    },
    "deepl": {
        # deepl
        "deepl_key": "",
        "deepl_api": "",
        "deepl_gid": "",
    },
    "deeplx": {
        # deeplx
        "deeplx_key": "",
        "deeplx_api": "http://127.0.0.1:1188",
    },
    "doubao2": {
        "doubao2_appid": "",
        "doubao2_access": "",
    },
    "elevenlabstts": {
        # elevenlabs.io
        "elevenlabstts_key": "",
        "elevenlabstts_model": ELEVENLABS_TTS_MODELS.split(',')[0],
    },
    "fishtts": {
        "fishtts_url": "http://127.0.0.1:8080/v1/tts",
    },
    "gradiowin": {
        "index_url": "http://127.0.0.1:7860",
        "index_version": 1,
        "voxcpm_url": "http://127.0.0.1:7860",
        "voxcpm_version": "v2",
        "firered3tts_url": "http://127.0.0.1:7860",
        "spark_url": "http://127.0.0.1:7860",
    },
    "gptsovits": {
        "gptsovits_url": "http://127.0.0.1:9880",
        "gptsovits_role": "",
        "gptsovits_isv2": True,
    },
    "kokoro": {
        # 本地 kokoro api
        "kokoro_api": "http://127.0.0.1:5066",
    },
    "libre": {
        # libre
        "libre_key": "",
        "libre_api": "",
    },
    "parakeet": {
        # 本地 parakeet api
        "parakeet_api": "",
    },
    "qwenttslocal": {
        # 本地 qwen-tts3 提示词
        "qwenttslocal_prompt": "",
    },
    "recognapi": {
        # 自定义语音识别api
        "recognapi_url": "",
        "recognapi_key": "",
    },
    "sttapi": {
        "sttapi_url": "http://127.0.0.1:9977",
    },
    "tencent": {
        # 腾讯翻译
        "tencent_key": "",
        "tencent_SecretId": "",
        "tencent_termlist": "",
    },
    "transapi": {
        # 自定义翻译 api
        "transapi_url": "",
        "transapi_key": "",
    },
    "ttsapi": {
        # 自定义 TTS API
        "ttsapi_url": "",
        "ttsapi_voice_role": "",
        "ttsapi_extra": "123456",
    },

    "whisperxapi": {
        # 本地 whisperx api
        "whisperxapi_api": "http://127.0.0.1:9092",
    },
    "xaitts": {
        # x.ai tts
        "xaitts_key": "",
    },
    "zijierecognmodel": {
        # 字节火山语音识别大模型极速版
        "zijierecognmodel_appid": "",
        "zijierecognmodel_key": "",
    },
}


# todo: 根据 name 返回配置dict???
# 返回默认值
def channel_default_params(name=None) -> Dict[str, Any]:
    if name:
        return _default.get(name)
    return {k: v for d in _default.values() for k, v in d.items()}
