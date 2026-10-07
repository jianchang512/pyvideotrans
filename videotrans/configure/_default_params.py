"""
设置各个外部 API 的默认参数

"""
from typing import Dict, Any

from videotrans.configure.constants import (
     GEMINI_TTS_MODELS,
    XIAOMI_MODELS, XIAOMI_TTS_MODELS, ELEVENLABS_TTS_MODELS,
    MINIMAX_TTS_MODELS, MINIMAX_MODELS,
    SILICONFLOW_TTS_MODELS, OPENROUTER_TTS_MODELS, GEMINI_MODELS
)

# todo: 根据 name 返回配置dict???
def channel_default_params(_settings=None) -> Dict[str, Any]:
    return {
        # deepseek
        "deepseek_key": "",# SK 密钥
        "deepseek_thinking": False,# 默认不启用思考
        # 默认模型
        "deepseek_model": str(_settings.get('deepseek_model', '-')).strip().split(',')[0],
        "deepseek_max_token": 16384,  # 最大输出64k

        # openai chatgpt
        "chatgpt_api": "",
        "chatgpt_key": "",
        "chatgpt_reasoning_effort": "default",
        "chatgpt_max_token": 16384,
        "chatgpt_model": str(_settings.get('chatgpt_model', '-')).strip().split(',')[0],
        # azure gpt
        "azure_api": "",
        "azure_key": "",
        "azure_model": str(_settings.get('azure_model', '-')).strip().split(',')[0],
        # gemini
        "gemini_key": "",
        "gemini_model": GEMINI_MODELS.split(',')[0],
        "gemini_max_token": 16384,
        "gemini_ttsstyle": "",
        "gemini_ttsmodel": GEMINI_TTS_MODELS.split(',')[0],
        # localLLM
        "localllm_api": "",
        "localllm_key": "",
        "localllm_reasoning_effort": "default",
        "localllm_model": str(_settings.get('localllm_model', '-')).strip().split(',')[0],
        "localllm_max_token": 8192,

        # 智谱AI
        "zhipuai_key": "",
        "zhipuai_thinking": False,
        "zhipuai_model": str(_settings.get('zhipuai_model', '-')).strip().split(',')[0],
        "zhipuai_max_token": 16384,
        # 硅基流动
        "siliconflow_key": "",
        "siliconflow_thinking": False,
        "siliconflow_model": str(_settings.get('siliconflow_model', '-')).strip().split(',')[0],
        "siliconflow_tts_model": SILICONFLOW_TTS_MODELS.strip().split(',')[0],
        "siliconflow_max_token": 16384,  # 最大输出16k
        # openrouter.ai
        "openrouter_key": "",
        "openrouter_reasoning_effort": "default",
        "openrouter_model": str(_settings.get('openrouter_model', '-')).strip().split(',')[0],
        "openrouter_tts_model": OPENROUTER_TTS_MODELS.strip().split(',')[0],
        "openrouter_max_token": 16384,  # 最大输出16k
        # liteLLM
        "litellm_api": 'http://localhost:4000/v1',
        "litellm_key": "",
        "litellm_reasoning_effort": "default",
        "litellm_model": str(_settings.get('litellm_model', '-')).strip().split(',')[0],
        "litellm_max_token": 16384,
        # api-route.com
        "api_route_key": "",
        "api_route_model": str(_settings.get('api_route_model', '-')).strip().split(',')[0],
        "api_route_max_token": 16384,

        "cheaperinference_key": "",
        "cheaperinference_model": str(_settings.get('cheaperinference_model', '-')).strip().split(',')[0],
        "cheaperinference_max_token": 16384,

        "atlascloud_key": "",
        "atlascloud_model": str(_settings.get('atlascloud_model', '-')).strip().split(',')[0],
        "atlascloud_max_token": 16384,

        "infistar_key": "",
        "infistar_model": str(_settings.get('infistar_model', '-')).strip().split(',')[0],
        "infistar_max_token": 16384,

        # 字节火山大模型
        "zijiehuoshan_key": "",
        "zijiehuoshan_thinking": False,
        "zijiehuoshan_max_token": 16384,
        "zijiehuoshan_model": str(_settings.get('zijiehuoshan_model', '-')).strip().split(',')[0],

        # 千问百炼 API
        "qwenmt_key": "",
        "qwenmt_spaceid": "",
        "qwenmt_domains": "",
        "qwenmt_model": "qwen-mt-turbo",
        "qwenmt_ttsmodel": "qwen3-tts-flash",
        # 本地

        # 302.ai
        "ai302_key": "",
        "ai302_model": "",

        # elevenlabs.io
        "elevenlabstts_key": "",
        "elevenlabstts_model": ELEVENLABS_TTS_MODELS.split(',')[0],

        # openai tts
        "openaitts_api": "",
        "openaitts_key": "",
        "openaitts_model": "tts-1",
        "openaitts_role": "",
        "openaitts_instructions": "",

        # x.ai tts
        "xaitts_key": "",

        # 小米 mimo
        "xiaomi_key": "",
        "xiaomi_ttsmodel": XIAOMI_TTS_MODELS.split(',')[0],
        "xiaomi_thinking": False,
        "xiaomi_model": XIAOMI_MODELS.split(',')[0],
        "xiaomi_max_token": 16384,

        # openai speech to text
        "openairecognapi_api": "",
        "openairecognapi_key": "",
        "openairecognapi_prompt": "",
        "openairecognapi_model": "whisper-1",

        # minimax
        "minimaxi_key": "",
        "minimaxi_api": "api.minimax.cn",
        "minimaxi_emotion": "",
        "minimaxi_tts_model": MINIMAX_TTS_MODELS.split(',')[0],
        "minimaxi_text_model": MINIMAX_MODELS.split(',')[0],
        "minimaxi_max_token": 16384,
        "minimaxi_thinking": False,

        # azure tts
        "azure_speech_key": "",
        "azure_speech_region": "",

        "doubao2_appid": "",
        "doubao2_access": "",

        # 字节火山语音识别大模型极速版
        "zijierecognmodel_appid": "",
        "zijierecognmodel_key": "",

        # deepgram.com
        "deepgram_key": "",

        "audexum_key": "",
        # deepl
        "deepl_key": "",
        "deepl_api": "",
        "deepl_gid": "",
        # deeplx
        "deeplx_key": "",
        "deeplx_api": "http://127.0.0.1:1188",
        # libre
        "libre_key": "",
        "libre_api": "",
        # 腾讯翻译
        "tencent_key": "",
        "tencent_SecretId": "",
        "tencent_termlist": "",
        # 阿里机器翻译
        "ali_id": "",
        "ali_key": "",
        # 百度翻译
        "baidu_appid": "",
        "baidu_key": "",

    }
