"""
pyVideoTrans WebUI — Gradio-based web interface for video translation.

TODO:
    拆分 webui.py 各个部分到 videotrans/webui_codes/ 中

Usage:
    uv run webui.py
    # or
    uv run python webui.py

Requires: uv sync --extra webui
"""

import os
import sys
import json
import time
import asyncio
import traceback
from pathlib import Path
from typing import List

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ---------------------------------------------------------------------------
# WebUI localization
# ---------------------------------------------------------------------------
# WebUI translations are intentionally isolated from the desktop/Qt catalogs.
from videotrans.webui_i18n import tr  # noqa: E402

# ---------------------------------------------------------------------------
# 初始化 videotrans 环境
# ---------------------------------------------------------------------------
from videotrans.configure import config  # noqa: E402

config.init_run()

from videotrans.configure.config import ROOT_DIR, TEMP_DIR, app_cfg, params, settings
from videotrans.configure.constants import FASTER_MODELS_DICT, DEEPGRAM_ASR_MODELS, OPENAI_WHISPER_MODELS, FUN_ASR_MODELS
from videotrans import recognition, translator, tts
from videotrans.util import tools
from videotrans.util.gpus import getset_gpu
from videotrans.util.help_role import role_menu

# ---------------------------------------------------------------------------
# params / settings 持久化路径
# ---------------------------------------------------------------------------
PARAMS_JSON = Path(ROOT_DIR) / "videotrans" / "params.json"
SETTINGS_JSON = Path(ROOT_DIR) / "videotrans" / "cfg.json"


def _load_params() -> dict:
    """从 params.json 加载"""
    try:
        if PARAMS_JSON.exists():
            return json.loads(PARAMS_JSON.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_params(data: dict):
    """保存到 params.json"""
    PARAMS_JSON.parent.mkdir(parents=True, exist_ok=True)
    PARAMS_JSON.write_text(
        json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    # 同步更新内存中的 params
    params.getset_params(data)


def _load_settings() -> dict:
    try:
        if SETTINGS_JSON.exists():
            return json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_settings(data: dict):
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_JSON.write_text(
        json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    settings.parse_init(data)


# 加载当前配置
_user_params = _load_params()
_user_settings = _load_settings()

# ---------------------------------------------------------------------------
# 渠道名称列表
# ---------------------------------------------------------------------------
RECOGN_NAMES: List[str] = recognition.RECOGN_NAME_LIST
TRANSLATE_NAMES: List[str] = translator.TRANSLASTE_NAME_LIST
TTS_NAMES: List[str] = tts.TTS_NAME_LIST
LANGNAME_DICT: dict = translator.LANGNAME_DICT

# ---------------------------------------------------------------------------
# 可选渠道索引
# ---------------------------------------------------------------------------
SELECTABLE_RECOGN = {0, 1, 2, 3, 4}
DEFAULT_RECOGN = 0
SELECTABLE_TRANSLATE = {0, 1, 2}
DEFAULT_TRANSLATE = 0
SELECTABLE_TTS = {0, 1, 3, 4, 5, 6, 7, 31}
DEFAULT_TTS = 0

FASTER_MODEL_NAMES = list(FASTER_MODELS_DICT.keys())
DEFAULT_MODEL = (
    "large-v3-turbo"
    if "large-v3-turbo" in FASTER_MODEL_NAMES
    else FASTER_MODEL_NAMES[0]
)

LANG_DISPLAY_NAMES = list(LANGNAME_DICT.values())
LANG_CHOICES = [(name, code) for code, name in LANGNAME_DICT.items()]
DEFAULT_SOURCE_LANG = next(iter(LANGNAME_DICT))
DEFAULT_TARGET_LANG = "-"

SUBTITLE_TYPES = {
    tr("No subtitles"): 0,
    tr("Embed hard subtitles"): 1,
    tr("Embed soft subtitles"): 2,
    tr("Embed hard subtitles (bilingual)"): 3,
    tr("Embed soft subtitles (bilingual)"): 4,
}
DEFAULT_SUBTITLE_TYPE = tr("Embed hard subtitles")
PUNC_OPTIONS = {tr("Default punctuation"): 0, tr("Restore punctuation"): 1, tr("Remove punctuation"): 2}
LOOP_BGM_OPTIONS = {tr("Truncate background audio"): 0, tr("Loop background audio"): 1}

# ---------------------------------------------------------------------------
# ASS 字幕样式
# ---------------------------------------------------------------------------
ASS_JSON_FILE = f"{ROOT_DIR}/videotrans/ass.json"

DEFAULT_ASS_STYLE = {
    "Name": "Default",
    "Fontname": "Arial",
    "Bottom_Fontname": "Arial",
    "Fontsize": 16,
    "Bottom_Fontsize": 16,
    "PrimaryColour": "&H00FFFFFF&",
    "Bottom_PrimaryColour": "&H00FFFFFF&",
    "SecondaryColour": "&H00FFFFFF&",
    "OutlineColour": "&H00000000&",
    "BackColour": "&H00000000&",
    "Bold": 0,
    "Italic": 0,
    "Bottom_SecondaryColour": "&H00FFFFFF&",
    "Bottom_OutlineColour": "&H00000000&",
    "Bottom_BackColour": "&H00000000&",
    "Bottom_Bold": 0,
    "Bottom_Italic": 0,
    "Underline": 0,
    "StrikeOut": 0,
    "ScaleX": 100,
    "ScaleY": 100,
    "Spacing": 0,
    "Angle": 0,
    "BorderStyle": 1,
    "Outline": 0.5,
    "Shadow": 0.5,
    "Alignment": 2,
    "MarginL": 10,
    "MarginR": 10,
    "MarginV": 10,
    "Encoding": 1,
}


def _parse_ass_color(c):
    if not c.startswith("&H") or not c.endswith("&"):
        return "#ffffff"
    h = c[2:-1].upper()
    if len(h) == 6:
        return f"#{int(h[4:6], 16):02x}{int(h[2:4], 16):02x}{int(h[0:2], 16):02x}"
    elif len(h) == 8:
        return f"#{int(h[6:8], 16):02x}{int(h[4:6], 16):02x}{int(h[2:4], 16):02x}"
    return "#ffffff"


def _to_ass_color(h):
    h = h.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"&H00{b:02X}{g:02X}{r:02X}&"
    return "&H00FFFFFF&"


def _load_ass_style():
    try:
        if Path(ASS_JSON_FILE).exists():
            return json.loads(Path(ASS_JSON_FILE).read_text(encoding="utf-8"))
    except Exception:
        pass
    return DEFAULT_ASS_STYLE.copy()


def _save_ass_style(s):
    Path(ASS_JSON_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(ASS_JSON_FILE).write_text(
        json.dumps(s, indent=4, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _lang_code_from_display(d):
    for code, name in LANGNAME_DICT.items():
        if name == d:
            return code
    return d


def _tts_index_from_display(d):
    for i, name in enumerate(TTS_NAMES):
        if name == d:
            return i
    return 0


def _recogn_index_from_display(d):
    for i, name in enumerate(RECOGN_NAMES):
        if name == d:
            return i
    return 0


def _translate_index_from_display(d):
    for i, name in enumerate(TRANSLATE_NAMES):
        if name == d:
            return i
    return 0


def _format_rate(v):
    return f"+{v}%" if v >= 0 else f"{v}%"


def _format_pitch(v):
    return f"+{v}Hz" if v >= 0 else f"{v}Hz"


def _safe_get(key, default=""):
    """从 _user_params 读取值，支持 str/int/float/bool"""
    v = _user_params.get(key, default)
    if v is None:
        return default
    return v


# ---------------------------------------------------------------------------
# 渠道设置面板定义
# ---------------------------------------------------------------------------
CHANNEL_SETTINGS = {
    # === 翻译渠道 ===
    tr("ChatGPT Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "chatgpt_api",
                "label": "API URL",
                "type": "text",
                "default": "",
                "placeholder": tr("Leave empty to use official API"),
            },
            {
                "key": "chatgpt_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
                "placeholder": "API Key",
            },
            {
                "key": "chatgpt_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
            {
                "key": "chatgpt_model",
                "label": tr("Model"),
                "type": "text",
                "default": "gpt-4o-mini",
                "placeholder": tr("Enter model name"),
            },
        ],
    },
    tr("DeepSeek Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "deepseek_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
                "placeholder": "API Key",
            },
            {
                "key": "deepseek_model",
                "label": tr("Model"),
                "type": "text",
                "default": "deepseek-chat",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "deepseek_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("Gemini Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {"key": "gemini_key", "label": "Gemini Key", "type": "text", "default": ""},
            {
                "key": "gemini_model",
                "label": tr("Model"),
                "type": "text",
                "default": "gemini-2.5-flash",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "gemini_maxtoken",
                "label": tr("Max Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("AzureGPT Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {"key": "azure_api", "label": "API URL", "type": "text", "default": ""},
            {"key": "azure_key", "label": tr("SK Key"), "type": "text", "default": ""},
            {
                "key": "azure_model",
                "label": tr("Model"),
                "type": "text",
                "default": "gpt-4o-mini",
                "placeholder": tr("Enter model name"),
            },
        ],
    },
    tr("Local LLM"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "localllm_api",
                "label": "API URL",
                "type": "text",
                "default": "http://127.0.0.1:11434/v1",
                "placeholder": tr("e.g. http://127.0.0.1:11434/v1"),
            },
            {
                "key": "localllm_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "no-key",
                "placeholder": tr("Usually fill in no-key"),
            },
            {
                "key": "localllm_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
            {
                "key": "localllm_model",
                "label": tr("Model"),
                "type": "text",
                "default": "",
                "placeholder": tr("Enter model name"),
            },
        ],
    },
    tr("DeepL Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "deepl_authkey",
                "label": "AUTH KEY",
                "type": "text",
                "default": "",
            },
            {
                "key": "deepl_api",
                "label": tr("API URL (Third-party)"),
                "type": "text",
                "default": "",
                "placeholder": tr("Leave empty to use official API"),
            },
            {
                "key": "deepl_gid",
                "label": tr("Glossary ID"),
                "type": "text",
                "default": "",
            },
        ],
    },
    tr("Baidu Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {"key": "baidu_appid", "label": "App ID", "type": "text", "default": ""},
            {"key": "baidu_miyue", "label": tr("Secret Key"), "type": "text", "default": ""},
        ],
    },
    tr("Tencent Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "tencent_SecretId",
                "label": "SecretId",
                "type": "text",
                "default": "",
            },
            {
                "key": "tencent_SecretKey",
                "label": "SecretKey",
                "type": "text",
                "default": "",
            },
        ],
    },
    tr("Alibaba Bailian (QwenMT)"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "qwenmt_key",
                "label": tr("Bailian SK"),
                "type": "text",
                "default": "",
            },
            {
                "key": "qwenmt_model",
                "label": tr("Translation Model"),
                "type": "text",
                "default": "qwen-mt-plus",
                "placeholder": tr("Must start with qwen-mt"),
            },
            {
                "key": "qwenmt_asr_model",
                "label": tr("ASR Model"),
                "type": "text",
                "default": "qwen3-asr-flash",
                "placeholder": tr("Must start with qwen3-asr"),
            },
        ],
    },
    tr("ByteDance VolcEngine"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "zijiehuoshan_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
            },
            {
                "key": "zijiehuoshan_model",
                "label": tr("Inference Endpoint"),
                "type": "text",
                "default": "",
                "placeholder": tr("Enter endpoint name"),
            },
        ],
    },
    tr("MiniMax Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "minimax_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
            },
            {
                "key": "minimax_api",
                "label": "API URL",
                "type": "text",
                "default": "api.minimax.io",
            },
            {
                "key": "minimax_model",
                "label": tr("Model"),
                "type": "text",
                "default": "MiniMax-M3",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "minimax_max_tokens",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("Zhipu AI Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {"key": "zhipu_key", "label": tr("SK Key"), "type": "text", "default": ""},
            {
                "key": "zhipu_model",
                "label": tr("Model"),
                "type": "text",
                "default": "glm-4-flash",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "zhipu_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("SiliconFlow"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {"key": "guiji_key", "label": tr("SK Key"), "type": "text", "default": ""},
            {
                "key": "guiji_model",
                "label": tr("Model"),
                "type": "text",
                "default": "Qwen/Qwen3-32B",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "guiji_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("OpenRouter Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "openrouter_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
            },
            {
                "key": "openrouter_model",
                "label": tr("Model"),
                "type": "text",
                "default": "",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "openrouter_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("API Route Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {"key": "api_route_key", "label": "API Key", "type": "text", "default": ""},
            {
                "key": "api_route_model",
                "label": tr("Model"),
                "type": "text",
                "default": "gpt-5.4-mini",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "api_route_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("Cheaper Inference Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "cheaperinference_key",
                "label": "API Key",
                "type": "text",
                "default": "",
            },
            {
                "key": "cheaperinference_model",
                "label": tr("Model"),
                "type": "text",
                "default": "gpt-5.4-mini",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "cheaperinference_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("Infistar Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {"key": "infistar_key", "label": "API Key", "type": "text", "default": ""},
            {
                "key": "infistar_model",
                "label": tr("Model"),
                "type": "text",
                "default": "gpt-5.4-mini",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "infistar_max_token",
                "label": tr("Max Output Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    tr("Atlas Cloud 翻译"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {"key": "atlascloud_key", "label": "API Key", "type": "text", "default": ""},
            {"key": "atlascloud_model", "label": "模型", "type": "text", "default": "deepseek-ai/deepseek-v4-flash", "placeholder": "输入模型名称"},
            {"key": "atlascloud_max_token", "label": "最大输出 Token", "type": "text", "default": "8192"},
        ],
    },
    tr("Xiaomi AI Translation"): {
        "category": tr("Subtitle Translation Channels"),
        "fields": [
            {
                "key": "xiaomi_key",
                "label": tr("Xiaomi Key"),
                "type": "text",
                "default": "",
            },
            {
                "key": "xiaomi_model",
                "label": tr("Model"),
                "type": "text",
                "default": "mimo-v2.5-pro",
                "placeholder": tr("Enter model name"),
            },
            {
                "key": "xiaomi_maxtoken",
                "label": tr("Max Tokens"),
                "type": "text",
                "default": "8192",
            },
        ],
    },
    # === 语音识别渠道 ===
    "OpenAI ASR": {
        "category": tr("ASR Channels"),
        "fields": [
            {
                "key": "openairecognapi_url",
                "label": "API URL",
                "type": "text",
                "default": "",
                "placeholder": tr("Leave empty to use official API"),
            },
            {
                "key": "openairecognapi_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
            },
            {
                "key": "openairecognapi_model",
                "label": tr("Model"),
                "type": "text",
                "default": "whisper-1",
                "placeholder": tr("Enter model name"),
            },
        ],
    },
    "Deepgram ASR": {
        "category": tr("ASR Channels"),
        "fields": [
            {
                "key": "deepgram_apikey",
                "label": "API Key",
                "type": "text",
                "default": "",
            },
        ],
    },
    "Audexum ASR": {
        "category": tr("ASR Channels"),
        "fields": [
            {"key": "audexum_key", "label": "API Key", "type": "text", "default": ""},
        ],
    },
    "Parakeet ASR": {
        "category": tr("ASR Channels"),
        "fields": [
            {
                "key": "parakeet_address",
                "label": "API URL",
                "type": "text",
                "default": "http://127.0.0.1:8080",
            },
        ],
    },
    tr("ByteDance ASR"): {
        "category": tr("ASR Channels"),
        "fields": [
            {
                "key": "zijierecognmodel_appid",
                "label": "AppID",
                "type": "text",
                "default": "",
            },
            {
                "key": "zijierecognmodel_token",
                "label": "Access Token",
                "type": "text",
                "default": "",
            },
        ],
    },
    # === 配音渠道 ===
    "OpenAI TTS": {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "openaitts_api",
                "label": "API URL",
                "type": "text",
                "default": "",
                "placeholder": tr("Leave empty to use official API"),
            },
            {
                "key": "openaitts_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
            },
            {
                "key": "openaitts_model",
                "label": tr("Model"),
                "type": "text",
                "default": "tts-1",
                "placeholder": tr("Enter model name"),
            },
        ],
    },
    "Azure TTS": {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "azure_speech_key",
                "label": "SPEECH KEY",
                "type": "text",
                "default": "",
            },
            {
                "key": "azure_speech_region",
                "label": "Region / URL",
                "type": "text",
                "default": "eastasia",
                "placeholder": tr("e.g. eastasia or full URL"),
            },
        ],
    },
    "ElevenLabs TTS": {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "elevenlabstts_key",
                "label": "API Key",
                "type": "text",
                "default": "",
            },
        ],
    },
    "GPT-SoVITS": {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "gptsovits_url",
                "label": "API URL",
                "type": "text",
                "default": "http://127.0.0.1:9880",
            },
        ],
    },
    "Spark / Index / VoxCPM": {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "sparktts_url",
                "label": "Spark-TTS URL",
                "type": "text",
                "default": "http://127.0.0.1:7860",
            },
            {
                "key": "indextts_url",
                "label": "Index-TTS URL",
                "type": "text",
                "default": "http://127.0.0.1:7860",
            },
            {
                "key": "voxcpmtts_url",
                "label": "VoxCPM URL",
                "type": "text",
                "default": "http://127.0.0.1:7860",
            },
        ],
    },
    "CosyVoice TTS": {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "cosyvoice_url",
                "label": "WebUI URL",
                "type": "text",
                "default": "http://127.0.0.1:8000",
            },
            {
                "key": "cosyvoice_instruct_text",
                "label": tr("Prompt Text"),
                "type": "text",
                "default": "",
            },
        ],
    },
    tr("Alibaba Bailian TTS (Qwen-TTS)"): {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "qwentts_key",
                "label": tr("Bailian SK"),
                "type": "text",
                "default": "",
            },
            {
                "key": "qwentts_model",
                "label": tr("Model"),
                "type": "text",
                "default": "qwen3-tts-flash",
                "placeholder": tr("Enter model name"),
            },
        ],
    },
    tr("Qwen-TTS Local"): {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "qwenttslocal_prompt",
                "label": tr("Custom Voice Prompt"),
                "type": "text",
                "default": "",
            },
        ],
    },
    tr("Doubao TTS 2.0"): {
        "category": tr("TTS Channel"),
        "fields": [
            {"key": "doubao2_appid", "label": "App ID", "type": "text", "default": ""},
            {
                "key": "doubao2_access",
                "label": "Access Token",
                "type": "text",
                "default": "",
            },
        ],
    },
    "Minimaxi TTS": {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "minimaxi_apikey",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
            },
            {
                "key": "minimaxi_apiurl",
                "label": "API URL",
                "type": "text",
                "default": "api.minimaxi.com",
            },
        ],
    },
    "X.AI TTS": {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "xaitts_key",
                "label": tr("SK Key"),
                "type": "text",
                "default": "",
            },
        ],
    },
    tr("Xiaomi TTS"): {
        "category": tr("TTS Channel"),
        "fields": [
            {
                "key": "xiaomi_key",
                "label": tr("Xiaomi Key"),
                "type": "text",
                "default": "",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# ASS 样式编辑器（纯 Gradio）
# ---------------------------------------------------------------------------
def build_ass_editor():
    import gradio as gr

    style = _load_ass_style()

    with gr.Accordion(tr("Hard Subtitle Style Editor"), open=False):
        gr.Markdown(tr("Click 'Save Style' after modifying, style will apply to all tasks with embedded hard subtitles."))
        with gr.Tabs():
            with gr.Tab(tr("Primary Subtitle")):
                with gr.Row():
                    ass_fontname = gr.Textbox(
                        label=tr("Font Name"), value=style.get("Fontname", "Arial")
                    )
                    ass_fontsize = gr.Slider(
                        label=tr("Font Size"),
                        minimum=1,
                        maximum=200,
                        value=style.get("Fontsize", 16),
                        step=1,
                    )
                with gr.Row():
                    ass_primary_color = gr.ColorPicker(
                        label=tr("Primary Color"),
                        value=_parse_ass_color(
                            style.get("PrimaryColour", "&H00FFFFFF&")
                        ),
                    )
                    ass_outline_color = gr.ColorPicker(
                        label=tr("Outline Color"),
                        value=_parse_ass_color(
                            style.get("OutlineColour", "&H00000000&")
                        ),
                    )
                    ass_back_color = gr.ColorPicker(
                        label=tr("Background Color"),
                        value=_parse_ass_color(style.get("BackColour", "&H00000000&")),
                    )
                with gr.Row():
                    ass_bold = gr.Checkbox(
                        label=tr("Bold"), value=bool(style.get("Bold", 0))
                    )
                    ass_italic = gr.Checkbox(
                        label=tr("Italic"), value=bool(style.get("Italic", 0))
                    )
                    ass_underline = gr.Checkbox(
                        label=tr("Underline"), value=bool(style.get("Underline", 0))
                    )
                    ass_strikeout = gr.Checkbox(
                        label=tr("Strikeout"), value=bool(style.get("StrikeOut", 0))
                    )
            with gr.Tab(tr("Bottom Subtitle (Bilingual)")):
                with gr.Row():
                    ass_bottom_fontname = gr.Textbox(
                        label=tr("Font Name"),
                        value=style.get("Bottom_Fontname", "Arial"),
                    )
                    ass_bottom_fontsize = gr.Slider(
                        label=tr("Font Size"),
                        minimum=1,
                        maximum=200,
                        value=style.get("Bottom_Fontsize", 16),
                        step=1,
                    )
                with gr.Row():
                    ass_bottom_primary_color = gr.ColorPicker(
                        label=tr("Primary Color"),
                        value=_parse_ass_color(
                            style.get("Bottom_PrimaryColour", "&H00FFFFFF&")
                        ),
                    )
                    ass_bottom_outline_color = gr.ColorPicker(
                        label=tr("Outline Color"),
                        value=_parse_ass_color(
                            style.get("Bottom_OutlineColour", "&H00000000&")
                        ),
                    )
                    ass_bottom_back_color = gr.ColorPicker(
                        label=tr("Background Color"),
                        value=_parse_ass_color(
                            style.get("Bottom_BackColour", "&H00000000&")
                        ),
                    )
                with gr.Row():
                    ass_bottom_bold = gr.Checkbox(
                        label=tr("Bold"), value=bool(style.get("Bottom_Bold", 0))
                    )
                    ass_bottom_italic = gr.Checkbox(
                        label=tr("Italic"), value=bool(style.get("Bottom_Italic", 0))
                    )
            with gr.Tab(tr("Global Style")):
                with gr.Row():
                    ass_border_style = gr.Dropdown(
                        label=tr("Border Style"),
                        choices=[tr("Outline"), tr("Opaque Background")],
                        value=tr("Outline")
                        if style.get("BorderStyle", 1) == 1
                        else tr("Opaque Background"),
                    )
                    ass_outline = gr.Slider(
                        label=tr("Outline Width"),
                        minimum=0.0,
                        maximum=10.0,
                        value=style.get("Outline", 0.5),
                        step=0.1,
                    )
                    ass_shadow = gr.Slider(
                        label=tr("Shadow"),
                        minimum=0.0,
                        maximum=10.0,
                        value=style.get("Shadow", 0.5),
                        step=0.1,
                    )
                with gr.Row():
                    ass_scale_x = gr.Slider(
                        label=tr("Scale X %"),
                        minimum=1,
                        maximum=1000,
                        value=style.get("ScaleX", 100),
                        step=1,
                    )
                    ass_scale_y = gr.Slider(
                        label=tr("Scale Y %"),
                        minimum=1,
                        maximum=1000,
                        value=style.get("ScaleY", 100),
                        step=1,
                    )
                    ass_spacing = gr.Slider(
                        label=tr("Letter Spacing"),
                        minimum=-100,
                        maximum=100,
                        value=style.get("Spacing", 0),
                        step=1,
                    )
                    ass_angle = gr.Slider(
                        label=tr("Rotation Angle"),
                        minimum=-360,
                        maximum=360,
                        value=style.get("Angle", 0),
                        step=1,
                    )
                with gr.Row():
                    ass_margin_l = gr.Slider(
                        label=tr("Left Margin"),
                        minimum=0,
                        maximum=1000,
                        value=style.get("MarginL", 10),
                        step=1,
                    )
                    ass_margin_r = gr.Slider(
                        label=tr("Right Margin"),
                        minimum=0,
                        maximum=1000,
                        value=style.get("MarginR", 10),
                        step=1,
                    )
                    ass_margin_v = gr.Slider(
                        label=tr("Vertical Margin"),
                        minimum=0,
                        maximum=1000,
                        value=style.get("MarginV", 10),
                        step=1,
                    )
                ass_alignment = gr.Dropdown(
                    label=tr("Alignment"),
                    choices=[
                        tr("Bottom Left"),
                        tr("Bottom Center"),
                        tr("Bottom Right"),
                        tr("Middle Left"),
                        tr("Center"),
                        tr("Middle Right"),
                        tr("Top Left"),
                        tr("Top Center"),
                        tr("Top Right"),
                    ],
                    value={
                        1: tr("Bottom Left"),
                        2: tr("Bottom Center"),
                        3: tr("Bottom Right"),
                        4: tr("Middle Left"),
                        5: tr("Center"),
                        6: tr("Middle Right"),
                        7: tr("Top Left"),
                        8: tr("Top Center"),
                        9: tr("Top Right"),
                    }.get(style.get("Alignment", 2), tr("Bottom Center")),
                )
        with gr.Row():
            ass_save_btn = gr.Button(tr("Save Style"), variant="primary")
            ass_reset_btn = gr.Button(tr("Restore Default"))
            ass_status = gr.Textbox(label=tr("Status"), interactive=False, visible=True)

        def save_ass_style(
            fontname,
            fontsize,
            primary_color,
            outline_color,
            back_color,
            bold,
            italic,
            underline,
            strikeout,
            bottom_fontname,
            bottom_fontsize,
            bottom_primary_color,
            bottom_outline_color,
            bottom_back_color,
            bottom_bold,
            bottom_italic,
            border_style,
            outline,
            shadow,
            scale_x,
            scale_y,
            spacing,
            angle,
            margin_l,
            margin_r,
            margin_v,
            alignment,
        ):
            am = {
                tr("Bottom Left"): 1,
                tr("Bottom Center"): 2,
                tr("Bottom Right"): 3,
                tr("Middle Left"): 4,
                tr("Center"): 5,
                tr("Middle Right"): 6,
                tr("Top Left"): 7,
                tr("Top Center"): 8,
                tr("Top Right"): 9,
            }
            _save_ass_style(
                {
                    "Name": "Default",
                    "Fontname": fontname,
                    "Bottom_Fontname": bottom_fontname,
                    "Fontsize": int(fontsize),
                    "Bottom_Fontsize": int(bottom_fontsize),
                    "PrimaryColour": _to_ass_color(primary_color),
                    "Bottom_PrimaryColour": _to_ass_color(bottom_primary_color),
                    "SecondaryColour": "&H00FFFFFF&",
                    "OutlineColour": _to_ass_color(outline_color),
                    "BackColour": _to_ass_color(back_color),
                    "Bold": 1 if bold else 0,
                    "Italic": 1 if italic else 0,
                    "Bottom_SecondaryColour": "&H00FFFFFF&",
                    "Bottom_OutlineColour": _to_ass_color(bottom_outline_color),
                    "Bottom_BackColour": _to_ass_color(bottom_back_color),
                    "Bottom_Bold": 1 if bottom_bold else 0,
                    "Bottom_Italic": 1 if bottom_italic else 0,
                    "Underline": 1 if underline else 0,
                    "StrikeOut": 1 if strikeout else 0,
                    "ScaleX": int(scale_x),
                    "ScaleY": int(scale_y),
                    "Spacing": int(spacing),
                    "Angle": int(angle),
                    "BorderStyle": 1 if border_style == tr("Outline") else 3,
                    "Outline": float(outline),
                    "Shadow": float(shadow),
                    "Alignment": am.get(alignment, 2),
                    "MarginL": int(margin_l),
                    "MarginR": int(margin_r),
                    "MarginV": int(margin_v),
                    "Encoding": 1,
                }
            )
            return tr("Style saved")

        def reset_ass_style():
            _save_ass_style(DEFAULT_ASS_STYLE.copy())
            s = DEFAULT_ASS_STYLE
            return (
                s["Fontname"],
                s["Fontsize"],
                _parse_ass_color(s["PrimaryColour"]),
                _parse_ass_color(s["OutlineColour"]),
                _parse_ass_color(s["BackColour"]),
                bool(s["Bold"]),
                bool(s["Italic"]),
                bool(s["Underline"]),
                bool(s["StrikeOut"]),
                s["Bottom_Fontname"],
                s["Bottom_Fontsize"],
                _parse_ass_color(s["Bottom_PrimaryColour"]),
                _parse_ass_color(s["Bottom_OutlineColour"]),
                _parse_ass_color(s["Bottom_BackColour"]),
                bool(s["Bottom_Bold"]),
                bool(s["Bottom_Italic"]),
                tr("Outline") if s["BorderStyle"] == 1 else tr("Opaque Background"),
                s["Outline"],
                s["Shadow"],
                s["ScaleX"],
                s["ScaleY"],
                s["Spacing"],
                s["Angle"],
                s["MarginL"],
                s["MarginR"],
                s["MarginV"],
                {
                    1: tr("Bottom Left"),
                    2: tr("Bottom Center"),
                    3: tr("Bottom Right"),
                    4: tr("Middle Left"),
                    5: tr("Center"),
                    6: tr("Middle Right"),
                    7: tr("Top Left"),
                    8: tr("Top Center"),
                    9: tr("Top Right"),
                }.get(s["Alignment"], tr("Bottom Center")),
                tr("Restored default style"),
            )

        ass_save_btn.click(
            fn=save_ass_style,
            inputs=[
                ass_fontname,
                ass_fontsize,
                ass_primary_color,
                ass_outline_color,
                ass_back_color,
                ass_bold,
                ass_italic,
                ass_underline,
                ass_strikeout,
                ass_bottom_fontname,
                ass_bottom_fontsize,
                ass_bottom_primary_color,
                ass_bottom_outline_color,
                ass_bottom_back_color,
                ass_bottom_bold,
                ass_bottom_italic,
                ass_border_style,
                ass_outline,
                ass_shadow,
                ass_scale_x,
                ass_scale_y,
                ass_spacing,
                ass_angle,
                ass_margin_l,
                ass_margin_r,
                ass_margin_v,
                ass_alignment,
            ],
            outputs=[ass_status],
        )

        ass_reset_btn.click(
            fn=reset_ass_style,
            inputs=[],
            outputs=[
                ass_fontname,
                ass_fontsize,
                ass_primary_color,
                ass_outline_color,
                ass_back_color,
                ass_bold,
                ass_italic,
                ass_underline,
                ass_strikeout,
                ass_bottom_fontname,
                ass_bottom_fontsize,
                ass_bottom_primary_color,
                ass_bottom_outline_color,
                ass_bottom_back_color,
                ass_bottom_bold,
                ass_bottom_italic,
                ass_border_style,
                ass_outline,
                ass_shadow,
                ass_scale_x,
                ass_scale_y,
                ass_spacing,
                ass_angle,
                ass_margin_l,
                ass_margin_r,
                ass_margin_v,
                ass_alignment,
                ass_status,
            ],
        )


# ---------------------------------------------------------------------------
# 渠道设置面板构建
# ---------------------------------------------------------------------------
def build_channel_settings():
    """构建所有渠道设置面板"""
    import gradio as gr

    # 按 category 分组
    categories = {}
    for name, cfg in CHANNEL_SETTINGS.items():
        cat = cfg["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((name, cfg))

    gr.Markdown(tr("### Channel Settings"))
    gr.Markdown(
        tr(
            "Configure API URLs and keys for channels. **Saved settings are shared with desktop version (sp.exe)** in `videotrans/params.json`."
        )
    )

    with gr.Tabs():
        for cat_name, channels in categories.items():
            with gr.Tab(cat_name):
                for ch_name, ch_cfg in channels:
                    with gr.Accordion(ch_name, open=False):
                        fields = []
                        for f in ch_cfg["fields"]:
                            val = str(_safe_get(f["key"], f.get("default", "")))
                            tb = gr.Textbox(
                                label=f["label"],
                                value=val,
                                placeholder=f.get("placeholder", ""),
                                interactive=True,
                            )
                            fields.append((f["key"], tb))

                        save_btn = gr.Button(tr("Save"), size="sm")
                        status = gr.Textbox(
                            label="", interactive=False, visible=True, show_label=False
                        )

                        # 使用闭包捕获当前值
                        def make_save_handler(field_keys, field_widgets):
                            def handler(*values):
                                data = {}
                                for k, v in zip(field_keys, values):
                                    data[k] = v
                                _save_params(data)
                                return tr("Saved")

                            return handler

                        save_btn.click(
                            fn=make_save_handler(
                                [f[0] for f in fields], [f[1] for f in fields]
                            ),
                            inputs=[f[1] for f in fields],
                            outputs=[status],
                        )

        # === 参考音频 Tab ===
        with gr.Tab(tr("Set Reference Audio")):
            gr.Markdown(tr("### Voice Clone Reference Audio Settings"))
            gr.Markdown(
                tr(
                    "Configure reference audio for voice cloning. One per line: `filename.wav#spoken text`\n- Audio files must be placed in `{}/f5-tts/`\n- File format must be wav\n- Use `#` to separate filename and text",
                    ROOT_DIR,
                )
            )

            ref_audio_text = gr.Textbox(
                label=tr("Reference Audio List"),
                value=str(_safe_get("f5tts_role", "")),
                placeholder=tr(
                    "myaudio1.wav#You say all is void, yet why keep your eyes closed\nmyaudio2.wav#Hello, this is a test audio"
                ),
                lines=8,
                interactive=True,
            )

            ref_audio_save = gr.Button(tr("Save Reference Audio"), variant="primary")
            ref_audio_status = gr.Markdown("", visible=False)

            def save_ref_audio(text):
                text = text.strip()
                if not text:
                    return gr.Markdown(tr("Please enter reference audio info"), visible=True)

                lines = text.split("\n")
                errors = []
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("#")
                    if len(parts) != 2:
                        errors.append(
                            tr("Line {} format error: must separate filename and text with #", i + 1)
                        )
                        continue

                    filename = parts[0].strip()
                    f5tts_dir = Path(ROOT_DIR) / "f5-tts"

                    # 检查文件是否存在（支持带/不带 .wav 后缀）
                    if (
                        not (f5tts_dir / filename).exists()
                        and not (f5tts_dir / f"{filename}.wav").exists()
                    ):
                        errors.append(
                            tr(
                                "Line {}: file `{}` does not exist in f5-tts/",
                                i + 1,
                                filename,
                            )
                        )
                        continue

                    # 自动补全 .wav 后缀
                    if (
                        not filename.endswith(".wav")
                        and (f5tts_dir / f"{filename}.wav").exists()
                    ):
                        lines[i] = f"{filename}.wav#{parts[1].strip()}"

                if errors:
                    return gr.Markdown(
                        tr("Save failed:\n") + "\n".join(errors), visible=True
                    )

                role_text = "\n".join(line for line in lines if line.strip())
                _save_params({"f5tts_role": role_text})
                return gr.Markdown(tr("Reference audio saved"), visible=True)

            ref_audio_save.click(
                fn=save_ref_audio,
                inputs=[ref_audio_text],
                outputs=[ref_audio_status],
            )


# ---------------------------------------------------------------------------
# 高级选项设置面板
# ---------------------------------------------------------------------------
COMBO_BOX_KEYS = {
    "cuda_com_type",
    "llm_ai_type",
    "vad_type",
    "speaker_type",
    "video_codec",
    "preset",
    "lang",
    "uvr_models",
    "out_video_ext",
    "fps_mode",
}
COMBO_BOX_OPTIONS = {
    "cuda_com_type": [
        "default",
        "auto",
        "int8",
        "int16",
        "float16",
        "float32",
        "bfloat16",
        "int8_float16",
        "int8_float32",
        "int8_bfloat16",
    ],
    "fps_mode": ["vfr", "cfr"],
    "llm_ai_type": ["chatgpt", "deepseek"],
    "vad_type": ["tenvad", "silero"],
    "speaker_type": ["built", "ali_CAM", "pyannote", "reverb"],
    "video_codec": ["264", "265"],
    "preset": [
        "ultrafast",
        "superfast",
        "veryfast",
        "faster",
        "fast",
        "medium",
        "slow",
        "slower",
        "veryslow",
    ],
    "uvr_models": [
        "spleeter",
        "UVR-MDX-NET-Inst_HQ_4",
        "UVR-MDX-NET-Inst_HQ_1",
        "UVR-MDX-NET-Inst_HQ_2",
        "UVR-MDX-NET-Inst_HQ_3",
        "UVR-MDX-NET-Inst_HQ_5",
        "UVR-MDX-NET-Inst_Main",
        "UVR-MDX-NET-Inst_1",
        "UVR-MDX-NET-Inst_2",
        "UVR-MDX-NET-Inst_3",
    ],
    "out_video_ext": [".mp4", ".mkv"],
}

# Whisper 提示词 keys 和中文标签
_prompt_keys_list = [
    "initial_prompt_zh-cn",
    "initial_prompt_zh-tw",
    "initial_prompt_en",
    "initial_prompt_ja",
    "initial_prompt_ko",
    "initial_prompt_fr",
    "initial_prompt_de",
    "initial_prompt_ru",
    "initial_prompt_es",
    "initial_prompt_pt",
    "initial_prompt_it",
    "initial_prompt_ar",
    "initial_prompt_vi",
    "initial_prompt_th",
    "initial_prompt_tr",
    "initial_prompt_hi",
]
_prompt_labels = {
    k: tr("whisper {} prompt", k.replace("initial_prompt_", ""))
    for k in _prompt_keys_list
}

# 全局 widget 注册表
_all_widgets = {}


def _w(key, label, tip="", area=False):
    """创建一个设置项：标题在上，组件在下"""
    import gradio as gr

    val = str(_user_settings.get(key, ""))
    with gr.Column():
        label_text = f"**{label}**" + (f"\n<sub>{tip}</sub>" if tip else "")
        gr.Markdown(label_text)
        if key in COMBO_BOX_KEYS:
            options = COMBO_BOX_OPTIONS.get(key, [val])
            w = gr.Dropdown(
                choices=options,
                value=val if val in options else options[0],
                label="",
                interactive=True,
                show_label=False,
            )
        elif val.lower() in ("true", "false"):
            w = gr.Checkbox(
                value=val.lower() == "true",
                label="",
                show_label=False,
                interactive=True,
            )
        else:
            w = gr.Textbox(
                value=val,
                label=None,
                show_label=False,
                lines=3 if area else 1,
                interactive=True,
            )
    _all_widgets[key] = w


def _save_section(section_key, keys):
    """为指定分区创建保存按钮和状态显示"""
    import gradio as gr

    with gr.Row():
        save_btn = gr.Button(
            tr("Save {}", ADVANCED_SECTION_TITLES.get(section_key, section_key)),
            variant="primary",
            size="sm",
        )
        status = gr.Markdown("", visible=False)

    def _make_handler(k_list):
        def handler(*values):
            data = {}
            for k, v in zip(k_list, values):
                data[k] = str(v)
            _save_settings(data)
            return gr.Markdown(tr("Saved"), visible=True)

        return handler

    save_btn.click(
        fn=_make_handler(keys), inputs=[_all_widgets[k] for k in keys], outputs=[status]
    )


# ---------------------------------------------------------------------------
# 高级选项设置面板（紧凑网格布局）
# ---------------------------------------------------------------------------
ADVANCED_SECTION_TITLES = {
    "common": tr("General Settings"),
    "video": tr("Video Output Control"),
    "whisper": tr("ASR Parameters"),
    "trans": tr("Translation Settings"),
    "dubbing": tr("Dubbing Settings"),
    "justify": tr("Alignment Settings"),
    "prompt_init": tr("Whisper Model Prompts"),
}


def build_advanced_settings():
    import gradio as gr

    gr.Markdown(
        tr(
            "Configure global advanced parameters. **Saved settings are shared with desktop version (sp.exe)** in `videotrans/cfg.json`.\nNote: Some parameters require restarting software to take effect."
        )
    )

    # ---- 通用设置 ----
    with gr.Accordion(tr("General Settings Panel"), open=True):
        with gr.Row():
            _w("lang", tr("UI Language"), tr("Restart required after change"))
            _w("countdown_sec", tr("Single Video Pause Countdown"), tr("Set to 0 to skip edit window"))
            _w("retry_nums", tr("Retry Count on Failure"), "")
        with gr.Row():
            _w("llm_chunk_size", tr("LLM Sentence Split Batch Size"), tr("Default 20"))
            _w("llm_ai_type", tr("LLM Sentence Split AI Channel"), "chatgpt/deepseek")
            _w("batch_nums", tr("Batch Processing Count"), tr("0 = Unlimited"))
        with gr.Row():
            _w("dont_notify", tr("Disable Desktop Notifications"), "")
            _w("show_more_settings", tr("Show All Parameters on Main UI?"), "")
            _w("homedir", tr("Output Directory for Standalone Tools"), "")
        with gr.Row():
            _w("process_max", tr("CPU Tasks [Restart]"), tr("Do not exceed CPU cores"))
            _w("process_max_gpu", tr("GPU Tasks [Restart]"), tr(">1 only for multi-GPU or VRAM > 24G"))
            _w("multi_gpus", tr("Multi-GPU Mode [Restart]"), "")
        _save_section(
            "common",
            [
                "lang",
                "countdown_sec",
                "retry_nums",
                "llm_chunk_size",
                "llm_ai_type",
                "batch_nums",
                "dont_notify",
                "show_more_settings",
                "homedir",
                "process_max",
                "process_max_gpu",
                "multi_gpus",
            ],
        )

    # ---- 视频输出控制 ----
    with gr.Accordion(tr("Video Output Control Panel"), open=False):
        with gr.Row():
            _w("crf", tr("Video Quality (0=lossless, 51=worst)"), "")
            _w("preset", tr("Preset Compression"), "ultrafast→veryslow")
            _w("video_codec", tr("H.264/H.265 Codec"), "")
        with gr.Row():
            _w("out_video_ext", tr("Output Format"), "mp4/mkv")
            _w("fps_mode", tr("Frame Rate Mode"), "vfr/cfr")
            _w("force_lib", tr("Force Software Encoding?"), "")
        with gr.Row():
            _w("hw_decode", tr("CUDA Hardware Decoding"), "")
            _w("ffmpeg_cmd", tr("Custom FFmpeg Parameters"), "")
        _save_section(
            "video",
            [
                "crf",
                "preset",
                "video_codec",
                "out_video_ext",
                "fps_mode",
                "force_lib",
                "hw_decode",
                "ffmpeg_cmd",
            ],
        )

    # ---- 语音识别参数 ----
    with gr.Accordion(tr("ASR Parameters Panel"), open=False):
        with gr.Row():
            _w("vad_type", tr("Select VAD"), "tenvad/silero")
            _w("threshold", tr("Speech Threshold"), "")
            _w("no_speech_threshold", tr("Non-speech Threshold"), "")
        with gr.Row():
            _w("max_speech_duration_s", tr("Max Speech Duration (s)"), "")
            _w("min_speech_duration_ms", tr("Min Speech Duration (ms)"), "")
            _w("min_silence_duration_ms", tr("Silence Split (ms)"), "")
        with gr.Row():
            _w("max_speech_duration_s2", tr("Second Pass Max Duration (s)"), "")
            _w("min_speech_duration_ms2", tr("Second Pass Min Duration (ms)"), "")
            _w("merge_short_sub", tr("Merge Short Subtitles"), "")
        with gr.Row():
            _w("whisper_prepare", tr("Whisper Pre-segmentation?"), tr("Check when cloning voice"))
            _w("speaker_type", tr("Speaker Diarization Model"), tr("Built-in / pyannote"))
            _w("hf_token", "Huggingface token", tr("Required for pyannote"))
        with gr.Row():
            _w("cuda_com_type", tr("Compute Data Type"), "int8/float16/float32")
            _w("beam_size", "beam_size", "1-5")
            _w("best_of", "best_of", "1-5")
        with gr.Row():
            _w("condition_on_previous_text", tr("Condition on Previous Text"), "")
            _w("repetition_penalty", tr("Repetition Penalty"), "")
            _w("compression_ratio_threshold", tr("Compression Ratio Threshold"), "")
        with gr.Row():
            _w("temperature", tr("Sampling Temperature"), "")
            _w("hotwords", tr("Hotwords"), tr("Comma-separated"))
            _w("gemini_recogn_chunk", tr("Gemini Chunk Count"), "")
        with gr.Row():
            _w("zh_hant_s", tr("Traditional to Simplified Chinese"), "")
            _w("del_end_punc", tr("Remove Trailing Punctuation"), "")
        with gr.Row():
            _w("model_list", tr("faster-whisper Models"), tr("Comma-separated"), area=True)
        with gr.Row():
            _w("Whisper_cpp_models", tr("whisper.cpp Models"), tr("Comma-separated"), area=True)
        _save_section(
            "whisper",
            [
                "vad_type",
                "threshold",
                "no_speech_threshold",
                "max_speech_duration_s",
                "min_speech_duration_ms",
                "max_speech_duration_s2",
                "min_speech_duration_ms2",
                "min_silence_duration_ms",
                "merge_short_sub",
                "whisper_prepare",
                "speaker_type",
                "hf_token",
                "cuda_com_type",
                "beam_size",
                "best_of",
                "condition_on_previous_text",
                "repetition_penalty",
                "compression_ratio_threshold",
                "temperature",
                "hotwords",
                "gemini_recogn_chunk",
                "zh_hant_s",
                "del_end_punc",
                "model_list",
                "Whisper_cpp_models",
            ],
        )

    # ---- 字幕翻译调整 ----
    with gr.Accordion(tr("Translation Settings Panel"), open=False):
        with gr.Row():
            _w("trans_thread", tr("Standard Translation Batch Lines"), "")
            _w("aitrans_thread", tr("AI Translation Batch Lines"), "")
            _w("aitrans_temperature", tr("AI Temperature"), tr("Default 1.0"))
        with gr.Row():
            _w("translation_wait", tr("Pause Seconds After Translation"), "")
            _w("aisendsrt", tr("Send Full Subtitles"), "")
            _w("aitrans_context", tr("Translate All Lines at Once"), tr("Requires ultra-long context model"))
        _save_section(
            "trans",
            [
                "trans_thread",
                "aitrans_thread",
                "aitrans_temperature",
                "translation_wait",
                "aisendsrt",
                "aitrans_context",
            ],
        )

    # ---- 字幕配音调整 ----
    with gr.Accordion(tr("Dubbing Settings Panel"), open=False):
        with gr.Row():
            _w("dubbing_thread", tr("Concurrent Dubbing Threads"), "")
            _w("dubbing_wait", tr("Pause Seconds After Dubbing"), "")
            _w("remove_dubb_silence", tr("Remove Silence Around Dubbing"), "")
        with gr.Row():
            _w("save_segment_audio", tr("Keep Segment Audio Files"), "")
            _w("normal_text", tr("Text Normalization"), "")
            _w("chattts_voice", tr("ChatTTS Voice Timbre"), "")
        with gr.Row():
            _w(
                "edgetts_max_concurrent_tasks",
                tr("EdgeTTS Concurrency"),
                tr("Higher is faster but may rate-limit"),
            )
            _w("edgetts_retry_nums", tr("EdgeTTS Retries"), "")
            _w("noise_separate_nums", tr("Vocal Separation Threads"), "")
        with gr.Row():
            _w("uvr_models", tr("Vocal Separation Model"), "")
        _save_section(
            "dubbing",
            [
                "dubbing_thread",
                "dubbing_wait",
                "remove_dubb_silence",
                "save_segment_audio",
                "normal_text",
                "chattts_voice",
                "edgetts_max_concurrent_tasks",
                "edgetts_retry_nums",
                "noise_separate_nums",
                "uvr_models",
            ],
        )

    # ---- 字幕声音画面对齐 ----
    with gr.Accordion(tr("Alignment Settings Panel"), open=False):
        with gr.Row():
            _w("max_audio_speed_rate", tr("Max Audio Speedup Rate"), tr("Default 100"))
            _w("max_video_pts_rate", tr("Max Video Slowdown Rate"), tr("Default 10, <=10"))
        with gr.Row():
            _w("cjk_len", tr("CJK Max Characters Per Line"), "")
            _w("other_len", tr("Other Languages Max Characters Per Line"), "")
        _save_section(
            "justify",
            ["max_audio_speed_rate", "max_video_pts_rate", "cjk_len", "other_len"],
        )

    # ---- Whisper模型提示词 ----
    with gr.Accordion(tr("Whisper Model Prompts Panel"), open=False):
        for i in range(0, len(_prompt_keys_list), 3):
            with gr.Row():
                for k in _prompt_keys_list[i : i + 3]:
                    _w(k, _prompt_labels.get(k, k), "")
        _save_section("prompt_init", _prompt_keys_list)


# ---------------------------------------------------------------------------
# UI 构建
# ---------------------------------------------------------------------------
def build_ui():
    import gradio as gr

    with gr.Blocks(title="pyVideoTrans WebUI") as app:
        gr.Markdown(
            tr("""
# pyVideoTrans Video Translation WebUI
> [This interface only implements partial features. For full features, please use the desktop app (sp.exe or sp.py)](https://pyvideotrans.com)
>
>  [Documentation](https://pyvideotrans.com) |
>  [Open Source](https://github.com/jianchang512/pyvideotrans) |
>  [Help & Issues](https://bbs.pyvideotrans.com)
----
        """)
        )

        with gr.Tabs():
            # === Tab 1: 视频翻译 ===
            with gr.Tab(tr("Video Translation"), id="translate"):
                prev_recogn = gr.State(value=RECOGN_NAMES[DEFAULT_RECOGN])
                prev_translate = gr.State(value=TRANSLATE_NAMES[DEFAULT_TRANSLATE])
                prev_tts = gr.State(value=TTS_NAMES[DEFAULT_TTS])

                with gr.Row():
                    with gr.Column(scale=3):
                        input_file = gr.Video(
                            label=tr("Select Video File"), interactive=True
                        )

                        recogn_choice = gr.Dropdown(
                            choices=RECOGN_NAMES,
                            value=RECOGN_NAMES[
                                int(_user_params.get("recogn_type", DEFAULT_RECOGN))
                                if str(_user_params.get("recogn_type", "")).isdigit()
                                else DEFAULT_RECOGN
                            ],
                            label=tr("ASR Channel"),
                            interactive=True,
                        )
                        model_choice = gr.Dropdown(
                            choices=FASTER_MODEL_NAMES,
                            value=_user_params.get("model_name", DEFAULT_MODEL),
                            label=tr("Model"),
                            interactive=True,
                        )

                        translate_choice = gr.Dropdown(
                            choices=TRANSLATE_NAMES,
                            value=TRANSLATE_NAMES[
                                int(
                                    _user_params.get(
                                        "translate_type", DEFAULT_TRANSLATE
                                    )
                                )
                                if str(_user_params.get("translate_type", "")).isdigit()
                                else DEFAULT_TRANSLATE
                            ],
                            label=tr("Translation Channel"),
                            interactive=True,
                        )
                        source_lang = gr.Dropdown(
                            choices=LANG_CHOICES,
                            value=_lang_code_from_display(
                                _user_params.get("source_language", DEFAULT_SOURCE_LANG)
                            ),
                            label=tr("Source Language"),
                            interactive=True,
                        )
                        target_lang = gr.Dropdown(
                            choices=[("-", "-")] + LANG_CHOICES,
                            value=_lang_code_from_display(
                                _user_params.get("target_language", DEFAULT_TARGET_LANG)
                            ),
                            label=tr("Target Language"),
                            interactive=True,
                        )

                        tts_choice = gr.Dropdown(
                            choices=TTS_NAMES,
                            value=TTS_NAMES[
                                int(_user_params.get("tts_type", DEFAULT_TTS))
                                if str(_user_params.get("tts_type", "")).isdigit()
                                else DEFAULT_TTS
                            ],
                            label=tr("TTS Channel"),
                            interactive=True,
                        )
                        # 根据已加载的TTS渠道和目标语言预填充角色列表
                        _init_tts_idx = (
                            int(_user_params.get("tts_type", DEFAULT_TTS))
                            if str(_user_params.get("tts_type", "")).isdigit()
                            else DEFAULT_TTS
                        )
                        _init_target = _user_params.get(
                            "target_language", DEFAULT_TARGET_LANG
                        )
                        _init_langcode = (
                            _lang_code_from_display(_init_target)
                            if _init_target and _init_target != "-"
                            else None
                        )
                        try:
                            _init_roles = role_menu(
                                _init_tts_idx, langcode=_init_langcode
                            )
                            if not _init_roles:
                                _init_roles = ["No"]
                        except Exception:
                            _init_roles = ["No"]
                        _saved_role = _user_params.get("voice_role", "No")
                        _init_role_val = (
                            _saved_role
                            if _saved_role in _init_roles
                            else _init_roles[0]
                        )
                        voice_role = gr.Dropdown(
                            choices=_init_roles,
                            value=_init_role_val,
                            label=tr("Voice Role"),
                            interactive=True,
                        )

                        with gr.Row():
                            voice_autorate = gr.Checkbox(
                                label=tr("Audio Speedup"), value=True
                            )
                            video_autorate = gr.Checkbox(
                                label=tr("Video Slowdown"), value=False
                            )
                        with gr.Row():
                            voice_rate = gr.Slider(
                                minimum=-50,
                                maximum=50,
                                value=int(
                                    str(_user_params.get("voice_rate", "0")).replace(
                                        "%", ""
                                    )
                                ),
                                step=1,
                                label=tr("Voice Speed (%)"),
                            )
                            volume_rate = gr.Slider(
                                minimum=-95,
                                maximum=100,
                                value=int(
                                    str(_user_params.get("volume", "0")).replace(
                                        "%", ""
                                    )
                                ),
                                step=1,
                                label=tr("Volume (%)"),
                            )
                            pitch_rate = gr.Slider(
                                minimum=-100,
                                maximum=100,
                                value=int(
                                    str(_user_params.get("pitch", "0")).replace(
                                        "Hz", ""
                                    )
                                ),
                                step=1,
                                label=tr("Pitch (Hz)"),
                            )
                        subtitle_type = gr.Dropdown(
                            choices=list(SUBTITLE_TYPES.keys()),
                            value=list(SUBTITLE_TYPES.keys())[
                                int(_user_params.get("subtitle_type", 1))
                                if str(_user_params.get("subtitle_type", "")).isdigit()
                                and int(_user_params.get("subtitle_type", 1))
                                < len(SUBTITLE_TYPES)
                                else 1
                            ],
                            label=tr("Subtitle Embedding Type"),
                            interactive=True,
                        )
                        build_ass_editor()

                        with gr.Accordion(tr("More Settings"), open=False):
                            with gr.Row():
                                remove_noise = gr.Checkbox(
                                    label=tr("Noise Reduction"), value=False
                                )
                                fix_punc = gr.Dropdown(
                                    choices=list(PUNC_OPTIONS.keys()),
                                    value=tr("Default punctuation"),
                                    label=tr("Punctuation Processing"),
                                    interactive=True,
                                )
                            with gr.Row():
                                is_separate = gr.Checkbox(
                                    label=tr("Separate Vocals and BGM"), value=False
                                )
                                embed_bgm = gr.Checkbox(
                                    label=tr("Re-embed Background Audio"), value=True
                                )
                            with gr.Row():
                                loop_bgm = gr.Dropdown(
                                    choices=list(LOOP_BGM_OPTIONS.keys()),
                                    value=tr("Truncate background audio"),
                                    label=tr("Background Audio Processing"),
                                    interactive=True,
                                )
                                backaudio_volume = gr.Slider(
                                    minimum=0.0,
                                    maximum=2.0,
                                    value=float(
                                        _user_params.get(
                                            "backaudio_volume",
                                            settings.get("backaudio_volume", 0.8),
                                        )
                                    ),
                                    step=0.1,
                                    label=tr("Background Audio Volume"),
                                )

                        cuda_accel = gr.Checkbox(
                            label=tr("Enable CUDA Acceleration"), value=False
                        )
                        channel_warning = gr.Markdown("", visible=False)

                        start_btn = gr.Button(
                            tr("Start"), variant="primary", size="lg"
                        )

                    with gr.Column(scale=2):
                        log_output = gr.Textbox(
                            label=tr("Execution Log"), lines=20, interactive=False
                        )
                        video_preview = gr.Video(
                            label=tr("Video Preview"), interactive=False
                        )
                        result_files = gr.File(
                            label=tr("Output Files (Click to Download)"), interactive=False
                        )

                # 渠道验证并更新模型列表
                def validate_recogn(choice, prev):
                    idx = _recogn_index_from_display(choice)

                    _rs = recognition.is_input_api(recogn_type=idx, return_str=True)
                    if _rs is not True:
                        msg = tr("Channel '{}' is currently unavailable and has been rolled back").format(choice)
                        gr.Warning(msg)
                        return prev, f"⚠️ {msg}", gr.update()

                    # 根据渠道更新模型下拉框
                    models = []
                    disabled = False
                    print(f'{idx=}')
                    print(f'{recognition.Whisper_CPP=}')
                    if idx in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL, recognition.WHISPERX_API]:
                        models = settings.WHISPER_MODELS
                    elif idx == recognition.OPENAI_WHISPER:
                        models = OPENAI_WHISPER_MODELS.split(',')
                    elif idx == recognition.Deepgram:
                        models = DEEPGRAM_ASR_MODELS
                    elif idx == recognition.Whisper_CPP:
                        models = settings.WHISPER_CPP_MODELS
                    elif idx == recognition.WHISPER_NET:
                        models = settings.WHISPER_NET_MODELS
                    elif idx == recognition.QWENASR:
                        models = ["1.7B", "0.6B"]
                    elif idx == recognition.HUGGINGFACE_ASR:
                        models = list(recognition.HUGGINGFACE_ASR_MODELS.keys())
                    elif idx == recognition.FUNASR_CN:
                        models = FUN_ASR_MODELS
                    else:
                        models = FASTER_MODEL_NAMES
                        disabled = True

                    if models:
                        default_val = models[0] if models else ""
                        return (
                            choice,
                            "",
                            gr.update(
                                choices=models,
                                value=default_val,
                                interactive=not disabled,
                            ),
                        )
                    return choice, "", gr.update(interactive=False)

                def validate_translate(choice, prev):
                    idx = _translate_index_from_display(choice)
                    _rs = translator.is_allow_translate(
                        translate_type=idx, return_str=True
                    )
                    if _rs is not True:
                        msg = tr("Channel '{}' is currently unavailable and has been rolled back").format(choice)
                        gr.Warning(msg)
                        return prev, f"⚠️ {msg}"
                    return choice, ""

                def tts_change_handler(choice, prev, target_display):
                    idx = _tts_index_from_display(choice)
                    warning = ""
                    _rs = tts.is_input_api(tts_type=idx, return_str=True)
                    if _rs is not True:
                        msg = tr("Channel '{}' is currently unavailable and has been rolled back").format(choice)
                        gr.Warning(msg)
                        choice = prev
                        warning = f"⚠️ {msg}"
                    tts_idx = _tts_index_from_display(choice)
                    lang_code = _lang_code_from_display(target_display)
                    try:
                        roles = role_menu(tts_idx, langcode=lang_code)
                        if not roles:
                            roles = ["No"]
                    except Exception:
                        roles = ["No"]
                    return (
                        choice,
                        gr.update(choices=roles, value=roles[0] if roles else "No"),
                        warning,
                    )

                recogn_choice.change(
                    fn=validate_recogn,
                    inputs=[recogn_choice, prev_recogn],
                    outputs=[recogn_choice, channel_warning, model_choice],
                )
                translate_choice.change(
                    fn=validate_translate,
                    inputs=[translate_choice, prev_translate],
                    outputs=[translate_choice, channel_warning],
                )
                tts_choice.change(
                    fn=tts_change_handler,
                    inputs=[tts_choice, prev_tts, target_lang],
                    outputs=[tts_choice, voice_role, channel_warning],
                )

                def update_voice_roles(tts_display, target_display):
                    tts_idx = _tts_index_from_display(tts_display)
                    lang_code = _lang_code_from_display(target_display)
                    try:
                        roles = role_menu(tts_idx, langcode=lang_code)
                        if not roles:
                            roles = ["No"]
                    except Exception:
                        roles = ["No"]
                    return gr.update(choices=roles, value=roles[0] if roles else "No")

                target_lang.change(
                    fn=update_voice_roles,
                    inputs=[tts_choice, target_lang],
                    outputs=[voice_role],
                )

                # 执行翻译
                _BTN_RUNNING = gr.update(value=tr("Processing..."), interactive=False)
                _BTN_IDLE = gr.update(value=tr("Start"), interactive=True)

                def run_translation(
                    file_path,
                    recogn_display,
                    model_name,
                    translate_display,
                    source_display,
                    target_display,
                    tts_display,
                    voice_role_name,
                    voice_autorate_val,
                    video_autorate_val,
                    voice_rate_val,
                    volume_rate_val,
                    pitch_rate_val,
                    subtitle_type_name,
                    remove_noise_val,
                    fix_punc_name,
                    is_separate_val,
                    embed_bgm_val,
                    loop_bgm_name,
                    backaudio_volume_val,
                    cuda_val,
                ):
                    print(f"{file_path=}")
                    if not file_path:
                        yield tr("Please select a video or audio file first"), None, [], _BTN_IDLE
                        return
                    app_cfg.current_status = "ing"
                    # 清空上次的日志、预览和输出，显示执行中状态
                    yield "", None, [], _BTN_RUNNING

                    log_lines = []

                    def log(msg):
                        log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
                        return "\n".join(log_lines)

                    recogn_idx = _recogn_index_from_display(recogn_display)
                    translate_idx = _translate_index_from_display(translate_display)
                    tts_idx = _tts_index_from_display(tts_display)
                    source_code = _lang_code_from_display(source_display)
                    target_code = _lang_code_from_display(target_display)
                    subtitle_val = SUBTITLE_TYPES.get(subtitle_type_name, 1)
                    fix_punc_val = PUNC_OPTIONS.get(fix_punc_name, 0)
                    loop_bgm_val = LOOP_BGM_OPTIONS.get(loop_bgm_name, 0)

                    try:
                        app_cfg.exit_soft = False
                        app_cfg.exec_mode = "cli"

                        getset_gpu()
                        _file_obj = tools.format_video(
                            Path(file_path).absolute().as_posix()
                        )
                        _nospacebasename = (
                            _file_obj["basename"].replace(" ", "-").replace(".", "-")
                        )
                        _cache_folder = f"{TEMP_DIR}/{_file_obj['uuid']}"
                        app_cfg.rm_uuid(_file_obj["uuid"])
                        _target_dir = f"{ROOT_DIR}/output/{_nospacebasename}"
                        _file_obj["target_dir"] = _target_dir
                        Path(_cache_folder).mkdir(parents=True, exist_ok=True)
                        target_path = Path(_target_dir)
                        if target_path.exists():
                            for f in sorted(target_path.rglob("*")):
                                if f.is_file():
                                    if f.suffix.lower() in [".mp4", ".mkv"]:
                                        f.unlink(missing_ok=True)
                        Path(_target_dir).mkdir(parents=True, exist_ok=True)

                        from dataclasses import asdict

                        common_params = {
                            "name": file_path,
                            "cache_folder": _cache_folder,
                        }
                        common_params.update(asdict(_file_obj))
                        yield (
                            log(tr("Source File: {}", Path(file_path).name)),
                            None,
                            [],
                            _BTN_RUNNING,
                        )

                        vtv_params = {
                            "source_language_code": source_code,
                            "target_language_code": target_code,
                            "recogn_type": recogn_idx,
                            "model_name": model_name,
                            "is_cuda": cuda_val,
                            "remove_noise": remove_noise_val,
                            "enable_diariz": False,
                            "nums_diariz": -1,
                            "detect_language": source_code,
                            "rephrase": 0,
                            "fix_punc": fix_punc_val,
                            "tts_type": tts_idx,
                            "voice_role": voice_role_name,
                            "voice_rate": _format_rate(int(voice_rate_val)),
                            "volume": _format_rate(int(volume_rate_val)),
                            "pitch": _format_pitch(int(pitch_rate_val)),
                            "voice_autorate": voice_autorate_val,
                            "video_autorate": video_autorate_val,
                            "align_sub_audio": True,
                            "translate_type": translate_idx,
                            "is_separate": is_separate_val,
                            "recogn2pass": False,
                            "subtitle_type": subtitle_val,
                            "clear_cache": True,
                            "embed_bgm": embed_bgm_val,
                            "loop_backaudio": loop_bgm_val,
                            "backaudio_volume": backaudio_volume_val,
                            "background_music": "",
                        }
                        params_dict = {**common_params, **vtv_params}

                        yield (
                            log(
                                tr(
                                    "ASR: {}  Translation: {}  TTS: {}",
                                    RECOGN_NAMES[recogn_idx],
                                    TRANSLATE_NAMES[translate_idx],
                                    TTS_NAMES[tts_idx],
                                )
                            ),
                            None,
                            [],
                            _BTN_RUNNING,
                        )
                        yield (
                            log(
                                tr(
                                    "Language: {} -> {}  Role: {}",
                                    source_code,
                                    target_code,
                                    voice_role_name,
                                )
                            ),
                            None,
                            [],
                            _BTN_RUNNING,
                        )
                        yield log(""), None, [], _BTN_RUNNING

                        yield log(tr("Starting video translation...")), None, [], _BTN_RUNNING
                        from videotrans.task.trans_create import TransCreate
                        from videotrans.task.taskcfg import TaskCfgVTT

                        trk = TransCreate(cfg=TaskCfgVTT(**params_dict))

                        stages = [
                            (tr("Stage 1/8: Preprocessing..."), "prepare", tr("Preprocessing completed")),
                            (tr("Stage 2/8: Speech recognition..."), "recogn", tr("Speech recognition completed")),
                            (
                                tr("Stage 3/8: Speaker diarization..."),
                                "diariz",
                                tr("Speaker diarization completed"),
                            ),
                            (tr("Stage 4/8: Subtitle translation..."), "trans", tr("Subtitle translation completed")),
                            (
                                tr("Stage 5/8: Dubbing generation..."),
                                "dubbing",
                                tr("Dubbing generation completed"),
                            ),
                            (tr("Stage 6/8: Audio-video alignment..."), "align", tr("Audio-video alignment completed")),
                            (
                                tr("Stage 7/8: Second-pass recognition..."),
                                "recogn2pass",
                                tr("Second-pass recognition completed"),
                            ),
                            (
                                tr("Stage 8/8: Final assembly..."),
                                "assembling",
                                tr("Final assembly completed"),
                            ),
                        ]
                        for stage_name, method, done_msg in stages:
                            yield log(stage_name), None, [], _BTN_RUNNING
                            getattr(trk, method)()
                            if method != "assembling":
                                yield log(f"✓ {done_msg}"), None, [], _BTN_RUNNING

                        trk.task_done()
                        yield log(tr("Video synthesis completed")), None, [], _BTN_RUNNING
                        yield log(tr("All tasks completed!")), None, [], _BTN_RUNNING

                        output_files, video_preview_path = [], None

                        if target_path.exists():
                            for f in sorted(target_path.rglob("*")):
                                if f.is_file():
                                    if (
                                        f.suffix.lower() == ".mp4"
                                        and video_preview_path is None
                                    ):
                                        video_preview_path = str(f)
                                    else:
                                        output_files.append(str(f))
                        if not output_files and video_preview_path is None:
                            for f in sorted(Path(_cache_folder).rglob("*")):
                                if f.is_file():
                                    if (
                                        f.suffix.lower() == ".mp4"
                                        and video_preview_path is None
                                    ):
                                        video_preview_path = str(f)
                                    elif f.suffix.lower() in (
                                        ".mkv",
                                        ".wav",
                                        ".srt",
                                        ".txt",
                                        ".mp3",
                                    ):
                                        output_files.append(str(f))
                        # 添加当天日志文件到输出列表
                        import datetime

                        log_file = (
                            Path(ROOT_DIR)
                            / "logs"
                            / f"{datetime.datetime.now().strftime('%Y%m%d')}.log"
                        )
                        if log_file.exists():
                            output_files.append(str(log_file))

                        yield (
                            log(tr("Output Directory: {}", _target_dir)),
                            video_preview_path,
                            output_files,
                            _BTN_IDLE,
                        )

                    except Exception as e:
                        tb = traceback.format_exc()
                        yield (
                            log(tr("Execution error: {}\n\n{}", str(e), tb)),
                            None,
                            [],
                            _BTN_IDLE,
                        )

                start_btn.click(
                    fn=run_translation,
                    inputs=[
                        input_file,
                        recogn_choice,
                        model_choice,
                        translate_choice,
                        source_lang,
                        target_lang,
                        tts_choice,
                        voice_role,
                        voice_autorate,
                        video_autorate,
                        voice_rate,
                        volume_rate,
                        pitch_rate,
                        subtitle_type,
                        remove_noise,
                        fix_punc,
                        is_separate,
                        embed_bgm,
                        loop_bgm,
                        backaudio_volume,
                        cuda_accel,
                    ],
                    outputs=[log_output, video_preview, result_files, start_btn],
                )

            # === Tab 2: 渠道设置 ===
            with gr.Tab(tr("Channel Settings"), id="settings"):
                build_channel_settings()

            # === Tab 3: 高级选项 ===
            with gr.Tab(tr("Advanced Options"), id="advanced"):
                build_advanced_settings()

    return app


if __name__ == "__main__":
    try:
        import argparse
        import gradio as gr

        parser = argparse.ArgumentParser(description="pyVideoTrans WebUI")
        parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
        parser.add_argument("--port", type=int, default=7860, help="Port number")
        parser.add_argument(
            "--share", action="store_true", help="Create a public Gradio link"
        )
        args = parser.parse_args()
        app = build_ui()
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            inbrowser=True,
            theme=gr.themes.Soft(),
            css="""
        /* 默认字体：微软雅黑 > 苹果方黑 > 系统无衬线字体 */
        *, *::before, *::after {
            font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Source Han Sans SC", "SimHei", sans-serif !important;
        }
        h1{text-align:center}
        /* 输入框和按钮的字体也统一 */
        input, textarea, select, button, label, .gr-textbox, .gr-dropdown, .gr-checkbox {
            font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Source Han Sans SC", "SimHei", sans-serif !important;
        }
    """,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(tr("\nLaunch failed: {}", e))
