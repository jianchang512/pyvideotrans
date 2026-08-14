"""
pyVideoTrans WebUI — Gradio-based web interface for video translation.

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
# 初始化 videotrans 环境
# ---------------------------------------------------------------------------
import json
import gradio as gr

from videotrans.configure import config
config.init_run()

from videotrans.configure.config import ROOT_DIR, TEMP_DIR, app_cfg, params, settings, _get_langjson_list
from videotrans.configure.contants import FASTER_MODELS_DICT, DEEPGRAM_MODEL, Openai_Whisper_Models, FUNASR_MODEL
from videotrans import recognition, translator, tts
from videotrans.util import tools
from videotrans.util.gpus import getset_gpu
from videotrans.util.help_role import role_menu


def _init_gradio_i18n() -> gr.I18n:
    """Load all language JSON files in videotrans/language/ into Gradio's native i18n engine"""
    translations = {}
    for lang_code, file_path in _get_langjson_list().items():
        try:
            data = json.loads(Path(file_path).read_text(encoding="utf-8"))
            cleaned = {}
            for k, v in data.items():
                if isinstance(v, str) and "{}" in v:
                    parts = v.split("{}")
                    new_v = parts[0]
                    for i, p in enumerate(parts[1:]):
                        new_v += f"{{{i}}}" + p
                    cleaned[k] = new_v
                else:
                    cleaned[k] = v
            translations[lang_code] = cleaned
        except Exception:
            pass
    return gr.I18n(**translations)


i18n = _init_gradio_i18n()



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
    current = _load_params()
    current.update(data)
    PARAMS_JSON.parent.mkdir(parents=True, exist_ok=True)
    PARAMS_JSON.write_text(json.dumps(current, indent=4, ensure_ascii=False), encoding="utf-8")
    params.getset_params(current)
    _user_params.update(data)


def _load_settings() -> dict:
    try:
        if SETTINGS_JSON.exists():
            return json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_settings(data: dict):
    current = _load_settings()
    current.update(data)
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_JSON.write_text(json.dumps(current, indent=4, ensure_ascii=False), encoding="utf-8")
    settings.parse_init(current)
    _user_settings.update(data)
    if "lang" in data:
        from videotrans.configure.config import _init_language
        _init_language(settings)


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
DEFAULT_MODEL = "large-v3-turbo" if "large-v3-turbo" in FASTER_MODEL_NAMES else FASTER_MODEL_NAMES[0]

LANG_DISPLAY_NAMES = list(LANGNAME_DICT.values())
DEFAULT_SOURCE_LANG = LANG_DISPLAY_NAMES[0]
DEFAULT_TARGET_LANG = '-'

SUBTITLE_TYPES = {
    i18n("No Subtitles"): 0,
    i18n("Embed Hard Subtitles"): 1,
    i18n("Embed Soft Subtitles"): 2,
    i18n("Embed Hard Subtitles (Bilingual)"): 3,
    i18n("Embed Soft Subtitles (Bilingual)"): 4,
}
DEFAULT_SUBTITLE_TYPE = i18n("Embed Hard Subtitles")
PUNC_OPTIONS = {
    i18n("Default Punctuation"): 0,
    i18n("Restore Punctuation"): 1,
    i18n("Remove Punctuation"): 2,
}
LOOP_BGM_OPTIONS = {
    i18n("Truncate BGM"): 0,
    i18n("Loop BGM"): 1,
}

# ---------------------------------------------------------------------------
# ASS 字幕样式
# ---------------------------------------------------------------------------
ASS_JSON_FILE = f'{ROOT_DIR}/videotrans/ass.json'

DEFAULT_ASS_STYLE = {
    'Name': 'Default', 'Fontname': 'Arial', 'Bottom_Fontname': 'Arial',
    'Fontsize': 16, 'Bottom_Fontsize': 16,
    'PrimaryColour': '&H00FFFFFF&', 'Bottom_PrimaryColour': '&H00FFFFFF&',
    'SecondaryColour': '&H00FFFFFF&', 'OutlineColour': '&H00000000&', 'BackColour': '&H00000000&',
    'Bold': 0, 'Italic': 0,
    'Bottom_SecondaryColour': '&H00FFFFFF&', 'Bottom_OutlineColour': '&H00000000&',
    'Bottom_BackColour': '&H00000000&', 'Bottom_Bold': 0, 'Bottom_Italic': 0,
    'Underline': 0, 'StrikeOut': 0, 'ScaleX': 100, 'ScaleY': 100,
    'Spacing': 0, 'Angle': 0, 'BorderStyle': 1, 'Outline': 0.5, 'Shadow': 0.5,
    'Alignment': 2, 'MarginL': 10, 'MarginR': 10, 'MarginV': 10, 'Encoding': 1,
}


def _parse_ass_color(c):
    if not c.startswith('&H') or not c.endswith('&'):
        return '#ffffff'
    h = c[2:-1].upper()
    if len(h) == 6:
        return f'#{int(h[4:6],16):02x}{int(h[2:4],16):02x}{int(h[0:2],16):02x}'
    elif len(h) == 8:
        return f'#{int(h[6:8],16):02x}{int(h[4:6],16):02x}{int(h[2:4],16):02x}'
    return '#ffffff'


def _to_ass_color(h):
    h = h.lstrip('#')
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f'&H00{b:02X}{g:02X}{r:02X}&'
    return '&H00FFFFFF&'


def _load_ass_style():
    try:
        if Path(ASS_JSON_FILE).exists():
            return json.loads(Path(ASS_JSON_FILE).read_text(encoding='utf-8'))
    except Exception:
        pass
    return DEFAULT_ASS_STYLE.copy()


def _save_ass_style(s):
    Path(ASS_JSON_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(ASS_JSON_FILE).write_text(json.dumps(s, indent=4, ensure_ascii=False), encoding='utf-8')


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
LANG_CODE_TO_DISPLAY = LANGNAME_DICT
LANG_DISPLAY_TO_CODE = {name: code for code, name in LANGNAME_DICT.items()}


def _lang_code_from_display(val: str) -> str:
    """Resolve language code from display name, or return code as-is."""
    if not val or val == '-':
        return val
    return LANG_DISPLAY_TO_CODE.get(val, val)


def _lang_display_from_code(val: str, default: str) -> str:
    """Resolve display name from language code, or return display name as-is."""
    if not val or val == '-':
        return default
    if val in LANG_CODE_TO_DISPLAY:
        return LANG_CODE_TO_DISPLAY[val]
    if val in LANG_DISPLAY_TO_CODE:
        return val
    return default


def get_supported_target_languages(translate_idx: int) -> List[str]:
    """Get list of supported target language display names for the given translation channel."""
    index_map = {
        16: 2,   # Baidu
        17: 3,   # DeepL
        18: 3,   # DeepLX
        15: 4,   # Tencent
        1: 6,    # Microsoft
        19: 8,   # Alibaba
        2: 10,   # M2M100
    }
    from videotrans.translator._lang_codes import LANG_CODE
    col = index_map.get(translate_idx)
    unsupported_codes = set()
    if col is not None:
        for code, code_list in LANG_CODE.items():
            if len(code_list) > col and code_list[col] == 'No':
                unsupported_codes.add(code)

    choices = ['-']
    for code, display_name in LANG_CODE_TO_DISPLAY.items():
        if code not in unsupported_codes:
            choices.append(display_name)
    return choices


def _tts_index_from_display(d: str) -> int:
    try:
        return TTS_NAMES.index(d)
    except (ValueError, IndexError):
        return 0


def _recogn_index_from_display(d: str) -> int:
    try:
        return RECOGN_NAMES.index(d)
    except (ValueError, IndexError):
        return 0


def _translate_index_from_display(d: str) -> int:
    try:
        return TRANSLATE_NAMES.index(d)
    except (ValueError, IndexError):
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
    # === Subtitle Translation Channels ===
    "ChatGPT Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "chatgpt_api", "label": "API URL", "type": "text", "default": "", "placeholder": "Leave blank for official API"},
            {"key": "chatgpt_key", "label": "SK Key", "type": "text", "default": "", "placeholder": "API Key"},
            {"key": "chatgpt_max_token", "label": "Max Output Tokens", "type": "text", "default": "8192"},
            {"key": "chatgpt_model", "label": "Model", "type": "text", "default": "gpt-4o-mini", "placeholder": "Enter model name"},
        ],
    },
    "DeepSeek Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "deepseek_key", "label": "SK Key", "type": "text", "default": "", "placeholder": "API Key"},
            {"key": "deepseek_model", "label": "Model", "type": "text", "default": "deepseek-chat", "placeholder": "Enter model name"},
            {"key": "deepseek_max_token", "label": "Max Output Tokens", "type": "text", "default": "8192"},
        ],
    },
    "Gemini Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "gemini_key", "label": "Gemini Key", "type": "text", "default": ""},
            {"key": "gemini_model", "label": "Model", "type": "text", "default": "gemini-2.5-flash", "placeholder": "Enter model name"},
            {"key": "gemini_maxtoken", "label": "Max Tokens", "type": "text", "default": "8192"},
        ],
    },
    "AzureGPT Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "azure_api", "label": "API URL", "type": "text", "default": ""},
            {"key": "azure_key", "label": "SK Key", "type": "text", "default": ""},
            {"key": "azure_model", "label": "Model", "type": "text", "default": "gpt-4o-mini", "placeholder": "Enter model name"},
        ],
    },
    "Local LLM": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "localllm_api", "label": "API URL", "type": "text", "default": "http://127.0.0.1:11434/v1", "placeholder": "e.g. http://127.0.0.1:11434/v1"},
            {"key": "localllm_key", "label": "SK Key", "type": "text", "default": "no-key", "placeholder": "Usually fill no-key"},
            {"key": "localllm_max_token", "label": "Max Output Tokens", "type": "text", "default": "8192"},
            {"key": "localllm_model", "label": "Model", "type": "text", "default": "", "placeholder": "Enter model name"},
        ],
    },
    "DeepL Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "deepl_authkey", "label": "AUTH KEY", "type": "text", "default": ""},
            {"key": "deepl_api", "label": "API URL (Third-party)", "type": "text", "default": "", "placeholder": "Leave blank for official API"},
            {"key": "deepl_gid", "label": "Glossary ID", "type": "text", "default": ""},
        ],
    },
    "Baidu Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "baidu_appid", "label": "App ID", "type": "text", "default": ""},
            {"key": "baidu_miyue", "label": "SK Key", "type": "text", "default": ""},
        ],
    },
    "Tencent Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "tencent_SecretId", "label": "SecretId", "type": "text", "default": ""},
            {"key": "tencent_SecretKey", "label": "SecretKey", "type": "text", "default": ""},
        ],
    },
    "QwenMT Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "qwenmt_key", "label": "Bailian SK", "type": "text", "default": ""},
            {"key": "qwenmt_model", "label": "Translation Model", "type": "text", "default": "qwen-mt-plus", "placeholder": "Must start with qwen-mt"},
            {"key": "qwenmt_asr_model", "label": "Speech Recognition Model", "type": "text", "default": "qwen3-asr-flash", "placeholder": "Must start with qwen3-asr"},
        ],
    },
    "ByteDance VolcEngine": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "zijiehuoshan_key", "label": "SK Key", "type": "text", "default": ""},
            {"key": "zijiehuoshan_model", "label": "Endpoint Name", "type": "text", "default": "", "placeholder": "Enter endpoint name"},
        ],
    },
    "MiniMax Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "minimax_key", "label": "SK Key", "type": "text", "default": ""},
            {"key": "minimax_api", "label": "API URL", "type": "text", "default": "api.minimax.io"},
            {"key": "minimax_model", "label": "Model", "type": "text", "default": "MiniMax-M3", "placeholder": "Enter model name"},
            {"key": "minimax_max_tokens", "label": "Max Output Tokens", "type": "text", "default": "8192"},
        ],
    },
    "Zhipu AI Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "zhipu_key", "label": "SK Key", "type": "text", "default": ""},
            {"key": "zhipu_model", "label": "Model", "type": "text", "default": "glm-4-flash", "placeholder": "Enter model name"},
            {"key": "zhipu_max_token", "label": "Max Output Tokens", "type": "text", "default": "8192"},
        ],
    },
    "SiliconFlow Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "guiji_key", "label": "SK Key", "type": "text", "default": ""},
            {"key": "guiji_model", "label": "Model", "type": "text", "default": "Qwen/Qwen3-32B", "placeholder": "Enter model name"},
            {"key": "guiji_max_token", "label": "Max Output Tokens", "type": "text", "default": "8192"},
        ],
    },
    "OpenRouter Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "openrouter_key", "label": "SK Key", "type": "text", "default": ""},
            {"key": "openrouter_model", "label": "Model", "type": "text", "default": "", "placeholder": "Enter model name"},
            {"key": "openrouter_max_token", "label": "Max Output Tokens", "type": "text", "default": "8192"},
        ],
    },
    "Xiaomi AI Translation": {
        "category": "Subtitle Translation Channels",
        "fields": [
            {"key": "xiaomi_key", "label": "Xiaomi Key", "type": "text", "default": ""},
            {"key": "xiaomi_model", "label": "Model", "type": "text", "default": "mimo-v2.5-pro", "placeholder": "Enter model name"},
            {"key": "xiaomi_maxtoken", "label": "Max Tokens", "type": "text", "default": "8192"},
        ],
    },

    # === Speech Recognition Channels ===
    "OpenAI ASR": {
        "category": "Speech Recognition Channels",
        "fields": [
            {"key": "openairecognapi_url", "label": "API URL", "type": "text", "default": "", "placeholder": "Leave blank for official API"},
            {"key": "openairecognapi_key", "label": "SK Key", "type": "text", "default": ""},
            {"key": "openairecognapi_model", "label": "Model", "type": "text", "default": "whisper-1", "placeholder": "Enter model name"},
        ],
    },
    "Deepgram ASR": {
        "category": "Speech Recognition Channels",
        "fields": [
            {"key": "deepgram_apikey", "label": "API Key", "type": "text", "default": ""},
        ],
    },
    "Parakeet ASR": {
        "category": "Speech Recognition Channels",
        "fields": [
            {"key": "parakeet_address", "label": "API URL", "type": "text", "default": "http://127.0.0.1:8080"},
        ],
    },
    "ByteDance ASR": {
        "category": "Speech Recognition Channels",
        "fields": [
            {"key": "zijierecognmodel_appid", "label": "AppID", "type": "text", "default": ""},
            {"key": "zijierecognmodel_token", "label": "Access Token", "type": "text", "default": ""},
        ],
    },

    # === Dubbing Channels ===
    "OpenAI TTS": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "openaitts_api", "label": "API URL", "type": "text", "default": "", "placeholder": "Leave blank for official API"},
            {"key": "openaitts_key", "label": "SK Key", "type": "text", "default": ""},
            {"key": "openaitts_model", "label": "Model", "type": "text", "default": "tts-1", "placeholder": "Enter model name"},
        ],
    },
    "Azure TTS": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "azure_speech_key", "label": "SPEECH KEY", "type": "text", "default": ""},
            {"key": "azure_speech_region", "label": "Region / URL", "type": "text", "default": "eastasia", "placeholder": "e.g. eastasia or full URL"},
        ],
    },
    "ElevenLabs TTS": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "elevenlabstts_key", "label": "API Key", "type": "text", "default": ""},
        ],
    },
    "GPT-SoVITS": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "gptsovits_url", "label": "API URL", "type": "text", "default": "http://127.0.0.1:9880"},
        ],
    },
    "Spark / Index / VoxCPM": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "sparktts_url", "label": "Spark-TTS URL", "type": "text", "default": "http://127.0.0.1:7860"},
            {"key": "indextts_url", "label": "Index-TTS URL", "type": "text", "default": "http://127.0.0.1:7860"},
            {"key": "voxcpmtts_url", "label": "VoxCPM URL", "type": "text", "default": "http://127.0.0.1:7860"},
        ],
    },
    "CosyVoice TTS": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "cosyvoice_url", "label": "WebUI URL", "type": "text", "default": "http://127.0.0.1:8000"},
            {"key": "cosyvoice_instruct_text", "label": "Prompt Text", "type": "text", "default": ""},
        ],
    },
    "Qwen-TTS (Bailian)": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "qwentts_key", "label": "Bailian SK", "type": "text", "default": ""},
            {"key": "qwentts_model", "label": "Model", "type": "text", "default": "qwen3-tts-flash", "placeholder": "Enter model name"},
        ],
    },
    "Qwen-TTS Local": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "qwenttslocal_prompt", "label": "Custom Voice Prompt", "type": "text", "default": ""},
        ],
    },
    "Doubao TTS 2.0": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "doubao2_appid", "label": "App ID", "type": "text", "default": ""},
            {"key": "doubao2_access", "label": "Access Token", "type": "text", "default": ""},
        ],
    },
    "Minimaxi TTS": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "minimaxi_apikey", "label": "SK Key", "type": "text", "default": ""},
            {"key": "minimaxi_apiurl", "label": "API URL", "type": "text", "default": "api.minimaxi.com"},
        ],
    },
    "X.AI TTS": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "xaitts_key", "label": "SK Key", "type": "text", "default": ""},
        ],
    },
    "Xiaomi TTS": {
        "category": "Dubbing Channels",
        "fields": [
            {"key": "xiaomi_key", "label": "Xiaomi Key", "type": "text", "default": ""},
        ],
    },
}


# ---------------------------------------------------------------------------
# ASS 样式编辑器（纯 Gradio）
# ---------------------------------------------------------------------------
def build_ass_editor():
    import gradio as gr

    style = _load_ass_style()

    align_map = {
        1: i18n("Bottom Left"), 2: i18n("Bottom Center"), 3: i18n("Bottom Right"),
        4: i18n("Middle Left"), 5: i18n("Center"), 6: i18n("Middle Right"),
        7: i18n("Top Left"), 8: i18n("Top Center"), 9: i18n("Top Right")
    }
    border_choices = [i18n("Outline"), i18n("Opaque Box")]

    with gr.Accordion(f"🎨 {i18n('Hard Subtitle Style Editor')}", open=False):
        gr.Markdown(i18n("Click Save Style after modifying. Style will apply to all hard subtitle tasks."))
        with gr.Tabs():
            with gr.Tab(i18n("Main Subtitle")):
                with gr.Row():
                    ass_fontname = gr.Textbox(label=i18n("Font Name"), value=style.get('Fontname', 'Arial'))
                    ass_fontsize = gr.Slider(label=i18n("Font Size"), minimum=1, maximum=200, value=style.get('Fontsize', 16), step=1)
                with gr.Row():
                    ass_primary_color = gr.ColorPicker(label=i18n("Primary Color"), value=_parse_ass_color(style.get('PrimaryColour', '&H00FFFFFF&')))
                    ass_outline_color = gr.ColorPicker(label=i18n("Outline Color"), value=_parse_ass_color(style.get('OutlineColour', '&H00000000&')))
                    ass_back_color = gr.ColorPicker(label=i18n("Background Color"), value=_parse_ass_color(style.get('BackColour', '&H00000000&')))
                with gr.Row():
                    ass_bold = gr.Checkbox(label=i18n("Bold"), value=bool(style.get('Bold', 0)))
                    ass_italic = gr.Checkbox(label=i18n("Italic"), value=bool(style.get('Italic', 0)))
                    ass_underline = gr.Checkbox(label=i18n("Underline"), value=bool(style.get('Underline', 0)))
                    ass_strikeout = gr.Checkbox(label=i18n("Strikeout"), value=bool(style.get('StrikeOut', 0)))
            with gr.Tab(i18n("Bottom Subtitle (Bilingual)")):
                with gr.Row():
                    ass_bottom_fontname = gr.Textbox(label=i18n("Font Name"), value=style.get('Bottom_Fontname', 'Arial'))
                    ass_bottom_fontsize = gr.Slider(label=i18n("Font Size"), minimum=1, maximum=200, value=style.get('Bottom_Fontsize', 16), step=1)
                with gr.Row():
                    ass_bottom_primary_color = gr.ColorPicker(label=i18n("Primary Color"), value=_parse_ass_color(style.get('Bottom_PrimaryColour', '&H00FFFFFF&')))
                    ass_bottom_outline_color = gr.ColorPicker(label=i18n("Outline Color"), value=_parse_ass_color(style.get('Bottom_OutlineColour', '&H00000000&')))
                    ass_bottom_back_color = gr.ColorPicker(label=i18n("Background Color"), value=_parse_ass_color(style.get('Bottom_BackColour', '&H00000000&')))
                with gr.Row():
                    ass_bottom_bold = gr.Checkbox(label=i18n("Bold"), value=bool(style.get('Bottom_Bold', 0)))
                    ass_bottom_italic = gr.Checkbox(label=i18n("Italic"), value=bool(style.get('Bottom_Italic', 0)))
            with gr.Tab(i18n("Global Style")):
                with gr.Row():
                    ass_border_style = gr.Dropdown(label=i18n("Border Style"), choices=border_choices, value=border_choices[0] if style.get('BorderStyle', 1) == 1 else border_choices[1])
                    ass_outline = gr.Slider(label=i18n("Outline Width"), minimum=0.0, maximum=10.0, value=style.get('Outline', 0.5), step=0.1)
                    ass_shadow = gr.Slider(label=i18n("Shadow Depth"), minimum=0.0, maximum=10.0, value=style.get('Shadow', 0.5), step=0.1)
                with gr.Row():
                    ass_scale_x = gr.Slider(label=i18n("Horizontal Scale %"), minimum=1, maximum=1000, value=style.get('ScaleX', 100), step=1)
                    ass_scale_y = gr.Slider(label=i18n("Vertical Scale %"), minimum=1, maximum=1000, value=style.get('ScaleY', 100), step=1)
                    ass_spacing = gr.Slider(label=i18n("Letter Spacing"), minimum=-100, maximum=100, value=style.get('Spacing', 0), step=1)
                    ass_angle = gr.Slider(label=i18n("Rotation Angle"), minimum=-360, maximum=360, value=style.get('Angle', 0), step=1)
                with gr.Row():
                    ass_margin_l = gr.Slider(label=i18n("Left Margin"), minimum=0, maximum=1000, value=style.get('MarginL', 10), step=1)
                    ass_margin_r = gr.Slider(label=i18n("Right Margin"), minimum=0, maximum=1000, value=style.get('MarginR', 10), step=1)
                    ass_margin_v = gr.Slider(label=i18n("Vertical Margin"), minimum=0, maximum=1000, value=style.get('MarginV', 10), step=1)
                ass_alignment = gr.Dropdown(label=i18n("Alignment"), choices=list(align_map.values()),
                    value=align_map.get(style.get('Alignment', 2), align_map[2]))
        with gr.Row():
            ass_save_btn = gr.Button(f"💾 {i18n('Save Style')}", variant="primary")
            ass_reset_btn = gr.Button(f"🔄 {i18n('Reset to Default')}")
            ass_status = gr.Textbox(label=i18n("Status"), interactive=False, visible=True)

        def save_ass_style(fontname, fontsize, primary_color, outline_color, back_color, bold, italic, underline, strikeout,
                           bottom_fontname, bottom_fontsize, bottom_primary_color, bottom_outline_color, bottom_back_color,
                           bottom_bold, bottom_italic, border_style, outline, shadow, scale_x, scale_y, spacing, angle,
                           margin_l, margin_r, margin_v, alignment):
            rev_align = {v: k for k, v in align_map.items()}
            _save_ass_style({
                'Name': 'Default', 'Fontname': fontname, 'Bottom_Fontname': bottom_fontname,
                'Fontsize': int(fontsize), 'Bottom_Fontsize': int(bottom_fontsize),
                'PrimaryColour': _to_ass_color(primary_color), 'Bottom_PrimaryColour': _to_ass_color(bottom_primary_color),
                'SecondaryColour': '&H00FFFFFF&', 'OutlineColour': _to_ass_color(outline_color),
                'BackColour': _to_ass_color(back_color), 'Bold': 1 if bold else 0, 'Italic': 1 if italic else 0,
                'Bottom_SecondaryColour': '&H00FFFFFF&', 'Bottom_OutlineColour': _to_ass_color(bottom_outline_color),
                'Bottom_BackColour': _to_ass_color(bottom_back_color), 'Bottom_Bold': 1 if bottom_bold else 0,
                'Bottom_Italic': 1 if bottom_italic else 0, 'Underline': 1 if underline else 0, 'StrikeOut': 1 if strikeout else 0,
                'ScaleX': int(scale_x), 'ScaleY': int(scale_y), 'Spacing': int(spacing), 'Angle': int(angle),
                'BorderStyle': 1 if border_style == border_choices[0] else 3, 'Outline': float(outline), 'Shadow': float(shadow),
                'Alignment': rev_align.get(alignment, 2), 'MarginL': int(margin_l), 'MarginR': int(margin_r),
                'MarginV': int(margin_v), 'Encoding': 1,
            })
            return f"✅ {i18n('Style saved successfully')}"

        def reset_ass_style():
            _save_ass_style(DEFAULT_ASS_STYLE.copy())
            s = DEFAULT_ASS_STYLE
            return (s['Fontname'], s['Fontsize'], _parse_ass_color(s['PrimaryColour']), _parse_ass_color(s['OutlineColour']),
                    _parse_ass_color(s['BackColour']), bool(s['Bold']), bool(s['Italic']), bool(s['Underline']), bool(s['StrikeOut']),
                    s['Bottom_Fontname'], s['Bottom_Fontsize'], _parse_ass_color(s['Bottom_PrimaryColour']),
                    _parse_ass_color(s['Bottom_OutlineColour']), _parse_ass_color(s['Bottom_BackColour']),
                    bool(s['Bottom_Bold']), bool(s['Bottom_Italic']),
                    border_choices[0] if s['BorderStyle'] == 1 else border_choices[1],
                    s['Outline'], s['Shadow'], s['ScaleX'], s['ScaleY'], s['Spacing'], s['Angle'],
                    s['MarginL'], s['MarginR'], s['MarginV'],
                    align_map.get(s['Alignment'], align_map[2]),
                    f"✅ {i18n('Style reset to default')}")

        ass_save_btn.click(fn=save_ass_style,
            inputs=[ass_fontname, ass_fontsize, ass_primary_color, ass_outline_color, ass_back_color,
                    ass_bold, ass_italic, ass_underline, ass_strikeout, ass_bottom_fontname, ass_bottom_fontsize,
                    ass_bottom_primary_color, ass_bottom_outline_color, ass_bottom_back_color,
                    ass_bottom_bold, ass_bottom_italic, ass_border_style, ass_outline, ass_shadow,
                    ass_scale_x, ass_scale_y, ass_spacing, ass_angle, ass_margin_l, ass_margin_r, ass_margin_v, ass_alignment],
            outputs=[ass_status])

        ass_reset_btn.click(fn=reset_ass_style, inputs=[],
            outputs=[ass_fontname, ass_fontsize, ass_primary_color, ass_outline_color, ass_back_color,
                     ass_bold, ass_italic, ass_underline, ass_strikeout, ass_bottom_fontname, ass_bottom_fontsize,
                     ass_bottom_primary_color, ass_bottom_outline_color, ass_bottom_back_color,
                     ass_bottom_bold, ass_bottom_italic, ass_border_style, ass_outline, ass_shadow,
                     ass_scale_x, ass_scale_y, ass_spacing, ass_angle, ass_margin_l, ass_margin_r, ass_margin_v,
                     ass_alignment, ass_status])


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

    gr.Markdown(f"### {i18n('Channel Settings')}")
    gr.Markdown(i18n("Channel Settings Description"))

    with gr.Tabs():
        for cat_name, channels in categories.items():
            with gr.Tab(i18n(cat_name)):
                for ch_name, ch_cfg in channels:
                    with gr.Accordion(i18n(ch_name), open=False):
                        fields = []
                        for f in ch_cfg["fields"]:
                            val = str(_safe_get(f["key"], f.get("default", "")))
                            tb = gr.Textbox(
                                label=i18n(f["label"]),
                                value=val,
                                placeholder=i18n(f["placeholder"]) if f.get("placeholder") else None,
                                interactive=True,
                            )
                            fields.append((f["key"], tb))

                        save_btn = gr.Button(f"💾 {i18n('Save')}", size="sm")
                        status = gr.Textbox(label="", interactive=False, visible=True, show_label=False)

                        # 使用闭包捕获当前值
                        def make_save_handler(field_keys, field_widgets):
                            def handler(*values):
                                data = {}
                                for k, v in zip(field_keys, values):
                                    data[k] = v
                                _save_params(data)
                                return f"✅ {i18n('Saved successfully')}"
                            return handler

                        save_btn.click(
                            fn=make_save_handler([f[0] for f in fields], [f[1] for f in fields]),
                            inputs=[f[1] for f in fields],
                            outputs=[status],
                        )

        # === 参考音频 Tab ===
        with gr.Tab(i18n("Reference Audio Settings")):
            gr.Markdown(i18n("Reference Audio Description"))

            ref_audio_text = gr.Textbox(
                label=i18n("Reference Audio List"),
                value=str(_safe_get("f5tts_role", "")),
                placeholder="myaudio1.wav#Sample reference text\nmyaudio2.wav#Hello, this is a test audio",
                lines=8,
                interactive=True,
            )

            ref_audio_save = gr.Button(f"💾 {i18n('Save Reference Audio')}", variant="primary")
            ref_audio_status = gr.Markdown("", visible=False)

            def save_ref_audio(text):
                text = text.strip()
                if not text:
                    return gr.Markdown(f"⚠️ {i18n('Please enter reference audio information')}", visible=True)

                lines = text.split("\n")
                errors = []
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("#")
                    if len(parts) != 2:
                        errors.append(f"Line {i + 1} format error: filename and text must be separated by #")
                        continue

                    filename = parts[0].strip()
                    f5tts_dir = Path(ROOT_DIR) / "f5-tts"

                    # 检查文件是否存在（支持带/不带 .wav 后缀）
                    if not (f5tts_dir / filename).exists() and not (f5tts_dir / f"{filename}.wav").exists():
                        errors.append(f"Line {i + 1}: file `{filename}` not found in f5-tts/ directory")
                        continue

                    # 自动补全 .wav 后缀
                    if not filename.endswith(".wav") and (f5tts_dir / f"{filename}.wav").exists():
                        lines[i] = f"{filename}.wav#{parts[1].strip()}"

                if errors:
                    return gr.Markdown(f"⚠️ {i18n('Save failed')}:\n" + "\n".join(errors), visible=True)

                role_text = "\n".join(line for line in lines if line.strip())
                _save_params({"f5tts_role": role_text})
                return gr.Markdown(f"✅ {i18n('Reference audio saved')}", visible=True)

            ref_audio_save.click(
                fn=save_ref_audio,
                inputs=[ref_audio_text],
                outputs=[ref_audio_status],
            )


# ---------------------------------------------------------------------------
# 高级选项设置面板
# ---------------------------------------------------------------------------
COMBO_BOX_KEYS = {
    'cuda_com_type', 'llm_ai_type', 'vad_type', 'speaker_type',
    'video_codec', 'preset', 'lang', 'uvr_models', 'out_video_ext', 'fps_mode',
}
COMBO_BOX_OPTIONS = {
    "cuda_com_type": ['default', 'auto', 'int8', 'int16', 'float16', 'float32', 'bfloat16', 'int8_float16', 'int8_float32', 'int8_bfloat16'],
    "fps_mode": ["vfr", "cfr"],
    "llm_ai_type": ['chatgpt', 'deepseek'],
    "vad_type": ['tenvad', 'silero'],
    "speaker_type": ['built', 'ali_CAM', 'pyannote', 'reverb'],
    "video_codec": ['264', '265'],
    "preset": ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'],
    "uvr_models": ['spleeter', 'UVR-MDX-NET-Inst_HQ_4', 'UVR-MDX-NET-Inst_HQ_1', 'UVR-MDX-NET-Inst_HQ_2', 'UVR-MDX-NET-Inst_HQ_3', 'UVR-MDX-NET-Inst_HQ_5', 'UVR-MDX-NET-Inst_Main', 'UVR-MDX-NET-Inst_1', 'UVR-MDX-NET-Inst_2', 'UVR-MDX-NET-Inst_3'],
    "out_video_ext": ['.mp4', '.mkv'],
    "lang": list(_get_langjson_list().keys()),
}

# Whisper 提示词 keys 和中文标签
_prompt_keys_list = [
    "initial_prompt_zh-cn", "initial_prompt_zh-tw", "initial_prompt_en",
    "initial_prompt_ja", "initial_prompt_ko", "initial_prompt_fr",
    "initial_prompt_de", "initial_prompt_ru", "initial_prompt_es",
    "initial_prompt_pt", "initial_prompt_it", "initial_prompt_ar",
    "initial_prompt_vi", "initial_prompt_th", "initial_prompt_tr",
    "initial_prompt_hi",
]
_prompt_labels = {k: f"whisper {k.replace('initial_prompt_', '')} 提示词" for k in _prompt_keys_list}

def _get_ui_language_options():
    supported = _get_langjson_list()
    # Return (display_label, code) pairs exclusively for supported language JSON files
    return [(f"{LANGNAME_DICT.get(code, code)} ({code})", code) for code in sorted(supported.keys())]


# 全局 widget 注册表
_all_widgets = {}


def _w(key, label, tip="", area=False):
    """创建一个设置项：直接将 label 与 info 传给 Gradio 组件以支持响应式 i18n"""
    import gradio as gr
    val = str(_user_settings.get(key, ""))
    with gr.Column():
        if key == "lang":
            options = _get_ui_language_options()
            valid_codes = [opt[1] for opt in options]
            cur_val = val if val in valid_codes else valid_codes[0]
            w = gr.Dropdown(choices=options, value=cur_val, label=label, info=tip if tip else None, interactive=True)
        elif key in COMBO_BOX_KEYS:
            options = COMBO_BOX_OPTIONS.get(key, [val])
            w = gr.Dropdown(choices=options, value=val if val in options else options[0],
                            label=label, info=tip if tip else None, interactive=True)
        elif val.lower() in ('true', 'false'):
            w = gr.Checkbox(value=val.lower() == 'true', label=label, info=tip if tip else None, interactive=True)
        else:
            w = gr.Textbox(value=val, label=label, info=tip if tip else None, lines=3 if area else 1, interactive=True)
    _all_widgets[key] = w


def _save_section(section_key, keys):
    """为指定分区创建保存按钮和状态显示"""
    import gradio as gr
    with gr.Row():
        save_btn = gr.Button(i18n("Save"), variant="primary", size="sm")
        status = gr.Markdown("", visible=False)

    def _make_handler(k_list):
        def handler(*values):
            data = {}
            for k, v in zip(k_list, values):
                data[k] = str(v)
            _save_settings(data)
            if "lang" in k_list:
                return gr.Markdown(f"✅ {i18n('Saved successfully. Please restart or refresh the page to apply language changes.')}", visible=True)
            return gr.Markdown(f"✅ {i18n('Saved successfully')}", visible=True)
        return handler

    save_btn.click(fn=_make_handler(keys), inputs=[_all_widgets[k] for k in keys], outputs=[status])


def build_advanced_settings():
    import gradio as gr
    gr.Markdown(i18n("Advanced Settings Description"))

    # ---- 通用设置 ----
    with gr.Accordion(i18n("General Settings"), open=True):
        with gr.Row():
            _w("lang", i18n("Interface Language"), i18n("Requires restart after setting"))
            _w("countdown_sec", i18n("Single Video Countdown"), i18n("Set to 0 to skip edit window"))
            _w("retry_nums", i18n("Retry Count on Failure"), "")
        with gr.Row():
            _w("llm_chunk_size", i18n("LLM Subtitle Lines per Batch"), i18n("Default: 20"))
            _w("llm_ai_type", i18n("LLM AI Provider"), "chatgpt/deepseek")
            _w("batch_nums", i18n("Batch Processing Limit"), i18n("0 = unlimited"))
        with gr.Row():
            _w("dont_notify", i18n("Disable Desktop Notifications"), "")
            _w("show_more_settings", i18n("Show All Parameters on Main UI"), "")
            _w("homedir", i18n("Standalone Output Directory"), "")
        with gr.Row():
            _w("process_max", i18n("CPU Tasks [Restart]"), i18n("Not exceeding CPU cores"))
            _w("process_max_gpu", i18n("GPU Tasks [Restart]"), i18n("Only >1 for multi-GPU or VRAM >24G"))
            _w("multi_gpus", i18n("Multi-GPU Mode [Restart]"), "")
        _save_section("common", ["lang", "countdown_sec", "retry_nums", "llm_chunk_size", "llm_ai_type",
                                  "batch_nums", "dont_notify", "show_more_settings", "homedir",
                                  "process_max", "process_max_gpu", "multi_gpus"])

    # ---- 视频输出控制 ----
    with gr.Accordion(i18n("Video Output Control"), open=False):
        with gr.Row():
            _w("crf", i18n("Video Quality (0=Lossless, 51=Poor)"), "")
            _w("preset", i18n("Compression Preset"), "ultrafast→veryslow")
            _w("video_codec", i18n("Video Codec (264/265)"), "")
        with gr.Row():
            _w("out_video_ext", i18n("Output Format"), "mp4/mkv")
            _w("fps_mode", i18n("Frame Rate Mode"), "vfr/cfr")
            _w("force_lib", i18n("Force Software Encoding?"), "")
        with gr.Row():
            _w("hw_decode", i18n("CUDA Hardware Decoding"), "")
            _w("ffmpeg_cmd", i18n("Custom FFmpeg Parameters"), "")
        _save_section("video", ["crf", "preset", "video_codec", "out_video_ext", "fps_mode",
                                 "force_lib", "hw_decode", "ffmpeg_cmd"])

    # ---- 语音识别参数 ----
    with gr.Accordion(i18n("Speech Recognition Parameters"), open=False):
        with gr.Row():
            _w("vad_type", i18n("Select VAD"), "tenvad/silero")
            _w("threshold", i18n("Voice Threshold"), "")
            _w("no_speech_threshold", i18n("No-speech Threshold"), "")
        with gr.Row():
            _w("max_speech_duration_s", i18n("Max Speech Duration (s)"), "")
            _w("min_speech_duration_ms", i18n("Min Speech Duration (ms)"), "")
            _w("min_silence_duration_ms", i18n("Min Silence Duration (ms)"), "")
        with gr.Row():
            _w("max_speech_duration_s2", i18n("2nd Pass Max Duration (s)"), "")
            _w("min_speech_duration_ms2", i18n("2nd Pass Min Duration (ms)"), "")
            _w("merge_short_sub", i18n("Merge Short Subtitles"), "")
        with gr.Row():
            _w("whisper_prepare", i18n("Whisper Pre-segmentation?"), i18n("Check when using clone dubbing"))
            _w("speaker_type", i18n("Speaker Diarization Model"), "built/pyannote")
            _w("hf_token", i18n("HuggingFace Token"), i18n("Required for pyannote"))
        with gr.Row():
            _w("cuda_com_type", i18n("Compute Data Type"), "int8/float16/float32")
            _w("beam_size", "beam_size", "1-5")
            _w("best_of", "best_of", "1-5")
        with gr.Row():
            _w("condition_on_previous_text", i18n("Context Awareness"), "")
            _w("repetition_penalty", i18n("Repetition Penalty"), "")
            _w("compression_ratio_threshold", i18n("Compression Ratio Threshold"), "")
        with gr.Row():
            _w("temperature", i18n("Sampling Temperature"), "")
            _w("hotwords", i18n("Hotwords"), i18n("Comma separated"))
            _w("gemini_recogn_chunk", i18n("Gemini Chunk Size"), "")
        with gr.Row():
            _w("zh_hant_s", i18n("Traditional to Simplified Chinese"), "")
            _w("del_end_punc", i18n("Delete Trailing Punctuation"), "")
        with gr.Row():
            _w("model_list", i18n("faster-whisper Models"), i18n("Comma separated"), area=True)
        with gr.Row():
            _w("Whisper_cpp_models", i18n("whisper.cpp Models"), i18n("Comma separated"), area=True)
        _save_section("whisper", ["vad_type", "threshold", "no_speech_threshold",
                                   "max_speech_duration_s", "min_speech_duration_ms",
                                   "max_speech_duration_s2", "min_speech_duration_ms2",
                                   "min_silence_duration_ms", "merge_short_sub",
                                   "whisper_prepare", "speaker_type", "hf_token",
                                   "cuda_com_type", "beam_size", "best_of",
                                   "condition_on_previous_text", "repetition_penalty",
                                   "compression_ratio_threshold", "temperature", "hotwords",
                                   "gemini_recogn_chunk", "zh_hant_s", "del_end_punc",
                                   "model_list", "Whisper_cpp_models"])

    # ---- 字幕翻译调整 ----
    with gr.Accordion(i18n("Subtitle Translation Adjustments"), open=False):
        with gr.Row():
            _w("trans_thread", i18n("Traditional Translation Batch Lines"), "")
            _w("aitrans_thread", i18n("AI Translation Batch Lines"), "")
            _w("aitrans_temperature", i18n("AI Temperature"), i18n("Default 1.0"))
        with gr.Row():
            _w("translation_wait", i18n("Pause Seconds After Translation"), "")
            _w("aisendsrt", i18n("Send Complete Subtitles"), "")
            _w("aitrans_context", i18n("Translate All Lines at Once"), i18n("Requires ultra-long context model"))
        _save_section("trans", ["trans_thread", "aitrans_thread", "aitrans_temperature",
                                 "translation_wait", "aisendsrt", "aitrans_context"])

    # ---- 字幕配音调整 ----
    with gr.Accordion(i18n("Subtitle Dubbing Adjustments"), open=False):
        with gr.Row():
            _w("dubbing_thread", i18n("Concurrent Dubbing Threads"), "")
            _w("dubbing_wait", i18n("Pause Seconds After Dubbing"), "")
            _w("remove_dubb_silence", i18n("Remove Silence Before/After Dubbing"), "")
        with gr.Row():
            _w("save_segment_audio", i18n("Keep Segment Audio Files"), "")
            _w("normal_text", i18n("Text Normalization"), "")
            _w("chattts_voice", i18n("ChatTTS Voice Value"), "")
        with gr.Row():
            _w("edgetts_max_concurrent_tasks", i18n("EdgeTTS Max Concurrency"), i18n("Faster but may be rate-limited"))
            _w("edgetts_retry_nums", i18n("EdgeTTS Retry Count"), "")
            _w("noise_separate_nums", i18n("Vocal Separation Threads"), "")
        with gr.Row():
            _w("uvr_models", i18n("Vocal Separation Model"), "")
        _save_section("dubbing", ["dubbing_thread", "dubbing_wait", "remove_dubb_silence",
                                   "save_segment_audio", "normal_text", "chattts_voice",
                                   "edgetts_max_concurrent_tasks", "edgetts_retry_nums",
                                   "noise_separate_nums", "uvr_models"])

    # ---- 字幕声音画面对齐 ----
    with gr.Accordion(i18n("Subtitle Video Audio Alignment"), open=False):
        with gr.Row():
            _w("max_audio_speed_rate", i18n("Max Audio Speedup Multiplier"), i18n("Default 100"))
            _w("max_video_pts_rate", i18n("Max Video Slowdown Multiplier"), i18n("Default 10 (<=10)"))
        with gr.Row():
            _w("cjk_len", i18n("CJK Subtitle Max Characters Per Line"), "")
            _w("other_len", i18n("Other Language Max Characters Per Line"), "")
        _save_section("justify", ["max_audio_speed_rate", "max_video_pts_rate", "cjk_len", "other_len"])

    # ---- Whisper模型提示词 ----
    with gr.Accordion(i18n("Whisper Model Initial Prompts"), open=False):
        for i in range(0, len(_prompt_keys_list), 3):
            with gr.Row():
                for k in _prompt_keys_list[i:i+3]:
                    _w(k, f"whisper {k.replace('initial_prompt_', '')} {i18n('Prompt')}", "")
        _save_section("prompt_init", _prompt_keys_list)


CUSTOM_CSS = """
/* 默认字体：微软雅黑 > 苹果方黑 > 系统无衬线字体 */
*, *::before, *::after {
    font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Source Han Sans SC", "SimHei", sans-serif !important;
}
h1 { text-align: center; }
/* 输入框和按钮的字体统一 */
input, textarea, select, button, label, .gr-textbox, .gr-dropdown, .gr-checkbox {
    font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Source Han Sans SC", "SimHei", sans-serif !important;
}

/* 纯 CSS 过滤：隐藏 Gradio 内置设置弹窗中 pyVideoTrans 不支持的语言项 */
li[data-testid="dropdown-option"][aria-label="العربية"],
li[data-testid="dropdown-option"][aria-label="Català"],
li[data-testid="dropdown-option"][aria-label="کوردی"],
li[data-testid="dropdown-option"][aria-label="Deutsch"],
li[data-testid="dropdown-option"][aria-label="Español"],
li[data-testid="dropdown-option"][aria-label="Euskara"],
li[data-testid="dropdown-option"][aria-label="فارسی"],
li[data-testid="dropdown-option"][aria-label="Suomi"],
li[data-testid="dropdown-option"][aria-label="Français"],
li[data-testid="dropdown-option"][aria-label="עברית"],
li[data-testid="dropdown-option"][aria-label="हिंदी"],
li[data-testid="dropdown-option"][aria-label="日本語"],
li[data-testid="dropdown-option"][aria-label="한국어"],
li[data-testid="dropdown-option"][aria-label="Lietuvių"],
li[data-testid="dropdown-option"][aria-label="Norsk bokmål"],
li[data-testid="dropdown-option"][aria-label="Nederlands"],
li[data-testid="dropdown-option"][aria-label="Polski"],
li[data-testid="dropdown-option"][aria-label="Português do Brasil"],
li[data-testid="dropdown-option"][aria-label="Português"],
li[data-testid="dropdown-option"][aria-label="Română"],
li[data-testid="dropdown-option"][aria-label="Русский"],
li[data-testid="dropdown-option"][aria-label="Svenska"],
li[data-testid="dropdown-option"][aria-label="தமிழ்"],
li[data-testid="dropdown-option"][aria-label="ภาษาไทย"],
li[data-testid="dropdown-option"][aria-label="Türkçe"],
li[data-testid="dropdown-option"][aria-label="Українська"],
li[data-testid="dropdown-option"][aria-label="اردو"],
li[data-testid="dropdown-option"][aria-label="O'zbek"],
li[data-testid="dropdown-option"][aria-label="id"],
li[data-testid="dropdown-option"][aria-label="Indonesian"],
li[data-testid="dropdown-option"][aria-label="繁體中文"] {
    display: none !important;
}
"""





# ---------------------------------------------------------------------------
# UI 构建
# ---------------------------------------------------------------------------
def build_ui():
    import gradio as gr

    with gr.Blocks(title="pyVideoTrans WebUI") as app:
        with gr.Tabs():
            # === Tab 1: 视频翻译 ===
            with gr.Tab(i18n("Video Translation"), id="translate"):
                prev_recogn = gr.State(value=RECOGN_NAMES[DEFAULT_RECOGN])
                prev_translate = gr.State(value=TRANSLATE_NAMES[DEFAULT_TRANSLATE])
                prev_tts = gr.State(value=TTS_NAMES[DEFAULT_TTS])

                with gr.Row():
                    with gr.Column(scale=3):
                        input_file = gr.Video(label=i18n("Select Video File"), interactive=True)

                        recogn_choice = gr.Dropdown(choices=RECOGN_NAMES, value=RECOGN_NAMES[int(_user_params.get('recogn_type', DEFAULT_RECOGN)) if str(_user_params.get('recogn_type', '')).isdigit() else DEFAULT_RECOGN], label=i18n("Recognition Channel"), interactive=True)
                        model_choice = gr.Dropdown(choices=FASTER_MODEL_NAMES, value=_user_params.get('model_name', DEFAULT_MODEL), label=i18n("Model"), interactive=True)

                        init_translate_idx = int(_user_params.get('translate_type', DEFAULT_TRANSLATE)) if str(_user_params.get('translate_type', '')).isdigit() else DEFAULT_TRANSLATE
                        translate_choice = gr.Dropdown(choices=TRANSLATE_NAMES, value=TRANSLATE_NAMES[init_translate_idx if init_translate_idx < len(TRANSLATE_NAMES) else DEFAULT_TRANSLATE], label=i18n("Translation Channel"), interactive=True)
                        _init_source = _lang_display_from_code(_user_params.get('source_language'), default=DEFAULT_SOURCE_LANG)
                        _init_target = _lang_display_from_code(_user_params.get('target_language'), default=DEFAULT_TARGET_LANG)
                        supported_targets = get_supported_target_languages(init_translate_idx)
                        source_lang = gr.Dropdown(choices=LANG_DISPLAY_NAMES, value=_init_source, label=i18n("Source Language (Spoken)"), interactive=True)
                        target_lang = gr.Dropdown(choices=supported_targets, value=_init_target if _init_target in supported_targets else supported_targets[0], label=i18n("Target Language"), interactive=True)

                        tts_choice = gr.Dropdown(choices=TTS_NAMES, value=TTS_NAMES[int(_user_params.get('tts_type', DEFAULT_TTS)) if str(_user_params.get('tts_type', '')).isdigit() else DEFAULT_TTS], label=i18n("TTS Channel"), interactive=True)
                        # 根据已加载的TTS渠道和目标语言预填充角色列表
                        _init_tts_idx = int(_user_params.get('tts_type', DEFAULT_TTS)) if str(_user_params.get('tts_type', '')).isdigit() else DEFAULT_TTS
                        _init_target_code = _lang_code_from_display(_init_target) if _init_target and _init_target != '-' else None
                        try:
                            _init_roles = role_menu(_init_tts_idx, langcode=_init_target_code)
                            if not _init_roles:
                                _init_roles = ["No"]
                        except Exception:
                            _init_roles = ["No"]
                        _saved_role = _user_params.get('voice_role', 'No')
                        _init_role_val = _saved_role if _saved_role in _init_roles else _init_roles[0]
                        voice_role = gr.Dropdown(choices=_init_roles, value=_init_role_val, label=i18n("Voice Role"), interactive=True)

                        with gr.Row():
                            voice_autorate = gr.Checkbox(label=i18n("Voice Speedup"), value=True)
                            video_autorate = gr.Checkbox(label=i18n("Video Slowdown"), value=False)
                        with gr.Row():
                            voice_rate = gr.Slider(minimum=-50, maximum=50, value=int(str(_user_params.get("voice_rate", "0")).replace("%","")), step=1, label=i18n("Voice Rate (%)"))
                            volume_rate = gr.Slider(minimum=-95, maximum=100, value=int(str(_user_params.get("volume", "0")).replace("%","")), step=1, label=i18n("Volume Adjustment (%)"))
                            pitch_rate = gr.Slider(minimum=-100, maximum=100, value=int(str(_user_params.get("pitch", "0")).replace("Hz","")), step=1, label=i18n("Pitch (Hz)"))
                        subtitle_type = gr.Dropdown(choices=list(SUBTITLE_TYPES.keys()), value=list(SUBTITLE_TYPES.keys())[int(_user_params.get('subtitle_type', 1)) if str(_user_params.get('subtitle_type', '')).isdigit() and int(_user_params.get('subtitle_type', 1)) < len(SUBTITLE_TYPES) else 1], label=i18n("Subtitle Embedding Type"), interactive=True)
                        build_ass_editor()

                        with gr.Accordion(f"📋 {i18n('More Settings')}", open=False):
                            with gr.Row():
                                remove_noise = gr.Checkbox(label=i18n("Noise Reduction"), value=False)
                                fix_punc = gr.Dropdown(choices=list(PUNC_OPTIONS.keys()), value=list(PUNC_OPTIONS.keys())[0], label=i18n("Punctuation Processing"), interactive=True)
                            with gr.Row():
                                is_separate = gr.Checkbox(label=i18n("Separate Vocals/BGM"), value=False)
                                embed_bgm = gr.Checkbox(label=i18n("Re-embed Background Audio"), value=True)
                            with gr.Row():
                                loop_bgm = gr.Dropdown(choices=list(LOOP_BGM_OPTIONS.keys()), value=list(LOOP_BGM_OPTIONS.keys())[0], label=i18n("BGM Processing"), interactive=True)
                                backaudio_volume = gr.Slider(minimum=0.0, maximum=2.0, value=float(_user_params.get("backaudio_volume", settings.get("backaudio_volume", 0.8))), step=0.1, label=i18n("Background Volume"))

                        cuda_accel = gr.Checkbox(label=i18n("Enable CUDA Acceleration"), value=False)
                        channel_warning = gr.Markdown("", visible=False)
                        
                        start_btn = gr.Button(f"🚀 {i18n('Start Execution')}", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        log_output = gr.Textbox(label=i18n("Execution Logs"), lines=20, interactive=False)
                        video_preview = gr.Video(label=i18n("Video Preview"), interactive=False)
                        result_files = gr.File(label=i18n("Output Files (Click to Download)"), interactive=False)

                # 渠道验证并更新模型列表
                def validate_recogn(choice, prev):
                    idx = _recogn_index_from_display(choice)

                    _rs=recognition.is_input_api(recogn_type=idx, return_str=True)
                    if _rs is not True:
                        msg = f"Channel '{choice}' is currently unavailable, reverted."
                        gr.Warning(msg)
                        return prev, f"⚠️ {msg}", gr.update()

                    # 根据渠道更新模型下拉框
                    models = []
                    disabled = False
                    print(f'{idx=}')
                    print(f'{recognition.Whisper_CPP=}')
                    if idx in [recognition.FASTER_WHISPER, recognition.Faster_Whisper_XXL, recognition.WHISPERX_API]:
                        models = settings.WHISPER_MODEL_LIST
                    elif idx == recognition.OPENAI_WHISPER:
                        models = Openai_Whisper_Models.split(',')
                    elif idx == recognition.Deepgram:
                        models = DEEPGRAM_MODEL
                    elif idx == recognition.Whisper_CPP:
                        models = settings.Whisper_CPP_MODEL_LIST
                    elif idx == recognition.WHISPER_NET:
                        models = settings.Whisper_NET_MODEL_LIST
                    elif idx == recognition.QWENASR:
                        models = ['1.7B', '0.6B']
                    elif idx == recognition.HUGGINGFACE_ASR:
                        models = list(recognition.HUGGINGFACE_ASR_MODELS.keys())
                    elif idx == recognition.FUNASR_CN:
                        models = FUNASR_MODEL
                    else:
                        models = FASTER_MODEL_NAMES
                        disabled = True

                    if models:
                        default_val = models[0] if models else ""
                        return choice, "", gr.update(choices=models, value=default_val, interactive=not disabled)
                    return choice, "", gr.update(interactive=False)

                def validate_translate(choice, prev, current_target_display):
                    idx = _translate_index_from_display(choice)
                    warning = ""
                    _rs=translator.is_allow_translate(translate_type=idx, return_str=True)
                    if _rs is not True:
                        msg = f"Channel '{choice}' is currently unavailable, reverted."
                        gr.Warning(msg)
                        choice = prev
                        idx = _translate_index_from_display(choice)
                        warning = f"⚠️ {msg}"

                    supported_choices = get_supported_target_languages(idx)
                    new_target = current_target_display if current_target_display in supported_choices else supported_choices[0]
                    if current_target_display not in supported_choices and current_target_display != '-':
                        gr.Info(f"Target language reset because '{current_target_display}' is not supported by this channel.")

                    return choice, warning, gr.update(choices=supported_choices, value=new_target)

                def tts_change_handler(choice, prev, target_display):
                    idx = _tts_index_from_display(choice)
                    warning = ""
                    _rs=tts.is_input_api(tts_type=idx, return_str=True)
                    if _rs is not True:
                        msg = f"Channel '{choice}' is currently unavailable, reverted."
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
                    return choice, gr.update(choices=roles, value=roles[0] if roles else "No"), warning

                recogn_choice.change(fn=validate_recogn, inputs=[recogn_choice, prev_recogn], outputs=[recogn_choice, channel_warning, model_choice])
                translate_choice.change(fn=validate_translate, inputs=[translate_choice, prev_translate, target_lang], outputs=[translate_choice, channel_warning, target_lang])
                tts_choice.change(fn=tts_change_handler, inputs=[tts_choice, prev_tts, target_lang], outputs=[tts_choice, voice_role, channel_warning])

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

                target_lang.change(fn=update_voice_roles, inputs=[tts_choice, target_lang], outputs=[voice_role])

                # 执行翻译
                _BTN_RUNNING = gr.update(value=f"⏳ {i18n('Executing...')}", interactive=False)
                _BTN_IDLE = gr.update(value=f"🚀 {i18n('Start Execution')}", interactive=True)
                
                def run_translation(file_path, recogn_display, model_name, translate_display,
                                    source_display, target_display, tts_display, voice_role_name,
                                    voice_autorate_val, video_autorate_val,
                                    voice_rate_val, volume_rate_val, pitch_rate_val,
                                    subtitle_type_name, remove_noise_val, fix_punc_name,
                                    is_separate_val, embed_bgm_val, loop_bgm_name, backaudio_volume_val,
                                    cuda_val):
                    print(f'{file_path=}')
                    if not file_path:
                        yield f"❌ {i18n('Please select a video or audio file first')}", None, [], _BTN_IDLE
                        return
                    app_cfg.current_status = 'ing'
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
                        app_cfg.exec_mode = 'cli'
                        
                        getset_gpu()
                        _file_obj = tools.format_video(Path(file_path).absolute().as_posix())
                        _nospacebasename = _file_obj["basename"].replace(" ", "-").replace(".", "-")
                        _cache_folder = f'{TEMP_DIR}/{_file_obj["uuid"]}'
                        app_cfg.rm_uuid(_file_obj['uuid'])
                        _target_dir = f'{ROOT_DIR}/output/{_nospacebasename}'
                        _file_obj['target_dir'] = _target_dir
                        Path(_cache_folder).mkdir(parents=True, exist_ok=True)
                        target_path = Path(_target_dir)
                        if target_path.exists():
                            for f in sorted(target_path.rglob("*")):
                                if f.is_file():
                                    if f.suffix.lower() in ['.mp4','.mkv']:
                                        f.unlink(missing_ok=True)
                        Path(_target_dir).mkdir(parents=True, exist_ok=True)
                        
                        from dataclasses import asdict
                        common_params = {'name': file_path, "cache_folder": _cache_folder}
                        common_params.update(asdict(_file_obj))
                        yield log(f"Source file: {Path(file_path).name}"), None, [], _BTN_RUNNING

                        vtv_params = {
                            "source_language_code": source_code, "target_language_code": target_code,
                            "recogn_type": recogn_idx, "model_name": model_name, "is_cuda": cuda_val,
                            "remove_noise": remove_noise_val, "enable_diariz": False, "nums_diariz": -1,
                            "detect_language": source_code, "rephrase": 0, "fix_punc": fix_punc_val,
                            "tts_type": tts_idx, "voice_role": voice_role_name,
                            "voice_rate": _format_rate(int(voice_rate_val)),
                            "volume": _format_rate(int(volume_rate_val)),
                            "pitch": _format_pitch(int(pitch_rate_val)),
                            "voice_autorate": voice_autorate_val, "video_autorate": video_autorate_val,
                            "align_sub_audio": True, "translate_type": translate_idx,
                            "is_separate": is_separate_val, "recogn2pass": False,
                            "subtitle_type": subtitle_val, 
                            "clear_cache": True,
                            "embed_bgm": embed_bgm_val, "loop_backaudio": loop_bgm_val,
                            "backaudio_volume": backaudio_volume_val, "background_music": "",
                        }
                        params_dict = {**common_params, **vtv_params}

                        yield log(f"Recognition: {RECOGN_NAMES[recogn_idx]}  Translation: {TRANSLATE_NAMES[translate_idx]}  Dubbing: {TTS_NAMES[tts_idx]}"), None, [], _BTN_RUNNING
                        yield log(f"Language: {source_code} → {target_code}  Role: {voice_role_name}"), None, [], _BTN_RUNNING
                        yield log(""), None, [], _BTN_RUNNING

                        yield log(f"▶ {i18n('Starting video translation...')}"), None, [], _BTN_RUNNING
                        from videotrans.task.trans_create import TransCreate
                        from videotrans.task.taskcfg import TaskCfgVTT
                        trk = TransCreate(cfg=TaskCfgVTT(**params_dict))

                        stages = [
                            (i18n("Stage 1/8: Preprocessing..."), "prepare", i18n("Preprocessing completed")),
                            (i18n("Stage 2/8: Speech recognition..."), "recogn", i18n("Speech recognition completed")),
                            (i18n("Stage 3/8: Speaker diarization..."), "diariz", i18n("Speaker diarization completed")),
                            (i18n("Stage 4/8: Subtitle translation..."), "trans", i18n("Subtitle translation completed")),
                            (i18n("Stage 5/8: Dubbing generation..."), "dubbing", i18n("Dubbing generation completed")),
                            (i18n("Stage 6/8: Audio video alignment..."), "align", i18n("Audio video alignment completed")),
                            (i18n("Stage 7/8: Secondary recognition..."), "recogn2pass", i18n("Secondary recognition completed")),
                            (i18n("Stage 8/8: Final synthesis..."), "assembling", i18n("Final synthesis completed")),
                        ]
                        for stage_name, method, done_msg in stages:
                            yield log(stage_name), None, [], _BTN_RUNNING
                            getattr(trk, method)()
                            if method != "assembling":
                                yield log(f"✓ {done_msg}"), None, [], _BTN_RUNNING

                        trk.task_done()
                        yield log(f"✓ {i18n('Video synthesis completed')}"), None, [], _BTN_RUNNING
                        yield log(f"✅ {i18n('All tasks completed!')}"), None, [], _BTN_RUNNING

                        output_files, video_preview_path = [], None
                        
                        if target_path.exists():
                            for f in sorted(target_path.rglob("*")):
                                if f.is_file():
                                    if f.suffix.lower() == '.mp4' and video_preview_path is None:
                                        video_preview_path = str(f)
                                    else:
                                        output_files.append(str(f))
                        if not output_files and video_preview_path is None:
                            for f in sorted(Path(_cache_folder).rglob("*")):
                                if f.is_file():
                                    if f.suffix.lower() == '.mp4' and video_preview_path is None:
                                        video_preview_path = str(f)
                                    elif f.suffix.lower() in ('.mkv', '.wav', '.srt', '.txt', '.mp3'):
                                        output_files.append(str(f))
                        # 添加当天日志文件到输出列表
                        import datetime
                        log_file = Path(ROOT_DIR) / "logs" / f"{datetime.datetime.now().strftime('%Y%m%d')}.log"
                        if log_file.exists():
                            output_files.append(str(log_file))

                        yield log(f"Output directory: {_target_dir}"), video_preview_path, output_files, _BTN_IDLE

                    except Exception as e:
                        tb = traceback.format_exc()
                        yield log(f"❌ {i18n('Execution error')}: {str(e)}\n\n{tb}"), None, [], _BTN_IDLE
                start_btn.click(fn=run_translation,
                    inputs=[input_file, recogn_choice, model_choice, translate_choice,
                            source_lang, target_lang, tts_choice, voice_role,
                            voice_autorate, video_autorate, voice_rate, volume_rate, pitch_rate,
                            subtitle_type, remove_noise, fix_punc,
                            is_separate, embed_bgm, loop_bgm, backaudio_volume, cuda_accel],
                    outputs=[log_output, video_preview, result_files, start_btn])

            # === Tab 2: 渠道设置 ===
            with gr.Tab(i18n("Channel Settings"), id="settings"):
                build_channel_settings()

            # === Tab 3: 高级选项 ===
            with gr.Tab(i18n("Advanced Options"), id="advanced"):
                build_advanced_settings()

    return app


if __name__ == "__main__":
    try:
        import argparse
        import gradio as gr
        parser = argparse.ArgumentParser(description="pyVideoTrans WebUI")
        parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
        parser.add_argument("--port", type=int, default=7860, help="Port number")
        parser.add_argument("--share", action="store_true", help="Create a public Gradio link")
        args = parser.parse_args()
        app = build_ui()
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            inbrowser=True,
            theme=gr.themes.Soft(),
            css=CUSTOM_CSS,
            i18n=i18n,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ 启动失败: {e}")



