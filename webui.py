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
# 语言常量
# ---------------------------------------------------------------------------
CLI_LANG = "zh"
os.environ['PYVIDEOTRANS_LANG'] = CLI_LANG

# ---------------------------------------------------------------------------
# 初始化 videotrans 环境
# ---------------------------------------------------------------------------
from videotrans.configure import config
config.init_run()

from videotrans.configure.config import ROOT_DIR, TEMP_DIR, app_cfg, params, settings
from videotrans.configure.contants import FASTER_MODELS_DICT
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
    PARAMS_JSON.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    # 同步更新内存中的 params
    params.update(data)


def _load_settings() -> dict:
    try:
        if SETTINGS_JSON.exists():
            return json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_settings(data: dict):
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_JSON.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    settings.update(data)


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
DEFAULT_TARGET_LANG = ['-']

SUBTITLE_TYPES = {"不嵌入字幕": 0, "嵌入硬字幕": 1, "嵌入软字幕": 2, "嵌入硬字幕(双语)": 3, "嵌入软字幕(双语)": 4}
DEFAULT_SUBTITLE_TYPE = "嵌入硬字幕"
PUNC_OPTIONS = {"默认标点": 0, "恢复标点": 1, "删除标点": 2}
LOOP_BGM_OPTIONS = {"背景音截断": 0, "背景音循环": 1}

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
    "ChatGPT 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "chatgpt_api", "label": "API URL", "type": "text", "default": "", "placeholder": "留空使用官方API"},
            {"key": "chatgpt_key", "label": "SK 密钥", "type": "text", "default": "", "placeholder": "API Key"},
            {"key": "chatgpt_max_token", "label": "最大输出 Token", "type": "text", "default": "8192"},
            {"key": "chatgpt_model", "label": "模型", "type": "text", "default": "gpt-4o-mini", "placeholder": "输入模型名称"},
        ],
    },
    "DeepSeek 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "deepseek_key", "label": "SK 密钥", "type": "text", "default": "", "placeholder": "API Key"},
            {"key": "deepseek_model", "label": "模型", "type": "text", "default": "deepseek-chat", "placeholder": "输入模型名称"},
            {"key": "deepseek_max_token", "label": "最大输出 Token", "type": "text", "default": "8192"},
        ],
    },
    "Gemini 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "gemini_key", "label": "Gemini Key", "type": "text", "default": ""},
            {"key": "gemini_model", "label": "模型", "type": "text", "default": "gemini-2.5-flash", "placeholder": "输入模型名称"},
            {"key": "gemini_maxtoken", "label": "最大 Token", "type": "text", "default": "8192"},
        ],
    },
    "AzureGPT 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "azure_api", "label": "API URL", "type": "text", "default": ""},
            {"key": "azure_key", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "azure_model", "label": "模型", "type": "text", "default": "gpt-4o-mini", "placeholder": "输入模型名称"},
        ],
    },
    "本地大模型 (LocalLLM)": {
        "category": "翻译",
        "fields": [
            {"key": "localllm_api", "label": "API URL", "type": "text", "default": "http://127.0.0.1:11434/v1", "placeholder": "如 http://127.0.0.1:11434/v1"},
            {"key": "localllm_key", "label": "SK 密钥", "type": "text", "default": "no-key", "placeholder": "通常填 no-key"},
            {"key": "localllm_max_token", "label": "最大输出 Token", "type": "text", "default": "8192"},
            {"key": "localllm_model", "label": "模型", "type": "text", "default": "", "placeholder": "输入模型名称"},
        ],
    },
    "DeepL 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "deepl_authkey", "label": "AUTH KEY", "type": "text", "default": ""},
            {"key": "deepl_api", "label": "API URL (第三方)", "type": "text", "default": "", "placeholder": "留空使用官方API"},
            {"key": "deepl_gid", "label": "术语表 ID", "type": "text", "default": ""},
        ],
    },
    "百度翻译": {
        "category": "翻译",
        "fields": [
            {"key": "baidu_appid", "label": "App ID", "type": "text", "default": ""},
            {"key": "baidu_miyue", "label": "密钥", "type": "text", "default": ""},
        ],
    },
    "腾讯翻译": {
        "category": "翻译",
        "fields": [
            {"key": "tencent_SecretId", "label": "SecretId", "type": "text", "default": ""},
            {"key": "tencent_SecretKey", "label": "SecretKey", "type": "text", "default": ""},
        ],
    },
    "阿里百炼 (QwenMT)": {
        "category": "翻译",
        "fields": [
            {"key": "qwenmt_key", "label": "百炼 SK", "type": "text", "default": ""},
            {"key": "qwenmt_model", "label": "翻译模型", "type": "text", "default": "qwen-mt-plus", "placeholder": "需以 qwen-mt 开头"},
            {"key": "qwenmt_asr_model", "label": "语音识别模型", "type": "text", "default": "qwen3-asr-flash", "placeholder": "需以 qwen3-asr 开头"},
        ],
    },
    "字节火山 (VolcEngine)": {
        "category": "翻译",
        "fields": [
            {"key": "zijiehuoshan_key", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "zijiehuoshan_model", "label": "推理接入点", "type": "text", "default": "", "placeholder": "输入接入点名称"},
        ],
    },
    "MiniMax 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "minimax_key", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "minimax_api", "label": "API URL", "type": "text", "default": "api.minimax.io"},
            {"key": "minimax_model", "label": "模型", "type": "text", "default": "MiniMax-M3", "placeholder": "输入模型名称"},
            {"key": "minimax_max_tokens", "label": "最大输出 Token", "type": "text", "default": "8192"},
        ],
    },
    "智谱 AI 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "zhipu_key", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "zhipu_model", "label": "模型", "type": "text", "default": "glm-4-flash", "placeholder": "输入模型名称"},
            {"key": "zhipu_max_token", "label": "最大输出 Token", "type": "text", "default": "8192"},
        ],
    },
    "硅基流动 (SiliconFlow)": {
        "category": "翻译",
        "fields": [
            {"key": "guiji_key", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "guiji_model", "label": "模型", "type": "text", "default": "Qwen/Qwen3-32B", "placeholder": "输入模型名称"},
            {"key": "guiji_max_token", "label": "最大输出 Token", "type": "text", "default": "8192"},
        ],
    },
    "OpenRouter 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "openrouter_key", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "openrouter_model", "label": "模型", "type": "text", "default": "", "placeholder": "输入模型名称"},
            {"key": "openrouter_max_token", "label": "最大输出 Token", "type": "text", "default": "8192"},
        ],
    },
    "小米 AI 翻译": {
        "category": "翻译",
        "fields": [
            {"key": "xiaomi_key", "label": "小米 Key", "type": "text", "default": ""},
            {"key": "xiaomi_model", "label": "模型", "type": "text", "default": "mimo-v2.5-pro", "placeholder": "输入模型名称"},
            {"key": "xiaomi_maxtoken", "label": "最大 Token", "type": "text", "default": "8192"},
        ],
    },

    # === 语音识别渠道 ===
    "OpenAI ASR": {
        "category": "语音识别",
        "fields": [
            {"key": "openairecognapi_url", "label": "API URL", "type": "text", "default": "", "placeholder": "留空使用官方API"},
            {"key": "openairecognapi_key", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "openairecognapi_model", "label": "模型", "type": "text", "default": "whisper-1", "placeholder": "输入模型名称"},
        ],
    },
    "Deepgram ASR": {
        "category": "语音识别",
        "fields": [
            {"key": "deepgram_apikey", "label": "API Key", "type": "text", "default": ""},
        ],
    },
    "Parakeet ASR": {
        "category": "语音识别",
        "fields": [
            {"key": "parakeet_address", "label": "API URL", "type": "text", "default": "http://127.0.0.1:8080"},
        ],
    },
    "字节语音识别": {
        "category": "语音识别",
        "fields": [
            {"key": "zijierecognmodel_appid", "label": "AppID", "type": "text", "default": ""},
            {"key": "zijierecognmodel_token", "label": "Access Token", "type": "text", "default": ""},
        ],
    },

    # === 配音渠道 ===
    "OpenAI TTS": {
        "category": "配音",
        "fields": [
            {"key": "openaitts_api", "label": "API URL", "type": "text", "default": "", "placeholder": "留空使用官方API"},
            {"key": "openaitts_key", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "openaitts_model", "label": "模型", "type": "text", "default": "tts-1", "placeholder": "输入模型名称"},
        ],
    },
    "Azure TTS": {
        "category": "配音",
        "fields": [
            {"key": "azure_speech_key", "label": "SPEECH KEY", "type": "text", "default": ""},
            {"key": "azure_speech_region", "label": "Region / URL", "type": "text", "default": "eastasia", "placeholder": "如 eastasia 或完整URL"},
        ],
    },
    "ElevenLabs TTS": {
        "category": "配音",
        "fields": [
            {"key": "elevenlabstts_key", "label": "API Key", "type": "text", "default": ""},
        ],
    },
    "GPT-SoVITS": {
        "category": "配音",
        "fields": [
            {"key": "gptsovits_url", "label": "API URL", "type": "text", "default": "http://127.0.0.1:9880"},
        ],
    },
    "F5-TTS / Spark / Index / Dia / VoxCPM": {
        "category": "配音",
        "fields": [
            {"key": "f5tts_url", "label": "F5-TTS URL", "type": "text", "default": "http://127.0.0.1:7860"},
            {"key": "sparktts_url", "label": "Spark-TTS URL", "type": "text", "default": "http://127.0.0.1:7860"},
            {"key": "indextts_url", "label": "Index-TTS URL", "type": "text", "default": "http://127.0.0.1:7860"},
            {"key": "diatts_url", "label": "Dia-TTS URL", "type": "text", "default": "http://127.0.0.1:7860"},
            {"key": "voxcpmtts_url", "label": "VoxCPM URL", "type": "text", "default": "http://127.0.0.1:7860"},
            {"key": "confuciustts_url", "label": "Confucius URL", "type": "text", "default": "http://127.0.0.1:7860"},
        ],
    },
    "CosyVoice TTS": {
        "category": "配音",
        "fields": [
            {"key": "cosyvoice_url", "label": "WebUI URL", "type": "text", "default": "http://127.0.0.1:8000"},
            {"key": "cosyvoice_instruct_text", "label": "Prompt 提示词", "type": "text", "default": ""},
        ],
    },
    "OmniVoice TTS": {
        "category": "配音",
        "fields": [
            {"key": "omnivoice_url", "label": "URL", "type": "text", "default": "http://127.0.0.1:8081"},
        ],
    },
    "阿里百炼 TTS (Qwen-TTS)": {
        "category": "配音",
        "fields": [
            {"key": "qwentts_key", "label": "百炼 SK", "type": "text", "default": ""},
            {"key": "qwentts_model", "label": "模型", "type": "text", "default": "qwen3-tts-flash", "placeholder": "输入模型名称"},
        ],
    },
    "Qwen-TTS 本地": {
        "category": "配音",
        "fields": [
            {"key": "qwenttslocal_prompt", "label": "自定义语音提示词", "type": "text", "default": ""},
        ],
    },
    "豆包语音合成 2.0": {
        "category": "配音",
        "fields": [
            {"key": "doubao2_appid", "label": "App ID", "type": "text", "default": ""},
            {"key": "doubao2_access", "label": "Access Token", "type": "text", "default": ""},
        ],
    },
    "Minimaxi TTS": {
        "category": "配音",
        "fields": [
            {"key": "minimaxi_apikey", "label": "SK 密钥", "type": "text", "default": ""},
            {"key": "minimaxi_apiurl", "label": "API URL", "type": "text", "default": "api.minimaxi.com"},
        ],
    },
    "X.AI TTS": {
        "category": "配音",
        "fields": [
            {"key": "xaitts_key", "label": "SK 密钥", "type": "text", "default": ""},
        ],
    },
    "小米 TTS": {
        "category": "配音",
        "fields": [
            {"key": "xiaomi_key", "label": "小米 Key", "type": "text", "default": ""},
        ],
    },
}


# ---------------------------------------------------------------------------
# ASS 样式编辑器（纯 Gradio）
# ---------------------------------------------------------------------------
def build_ass_editor():
    import gradio as gr

    style = _load_ass_style()

    with gr.Accordion("🎨 硬字幕样式编辑", open=False):
        gr.Markdown("修改后点击「保存样式」，样式将应用于所有嵌入硬字幕的任务。")
        with gr.Tabs():
            with gr.Tab("主字幕"):
                with gr.Row():
                    ass_fontname = gr.Textbox(label="字体名称", value=style.get('Fontname', 'Arial'))
                    ass_fontsize = gr.Slider(label="字体大小", minimum=1, maximum=200, value=style.get('Fontsize', 16), step=1)
                with gr.Row():
                    ass_primary_color = gr.ColorPicker(label="主颜色", value=_parse_ass_color(style.get('PrimaryColour', '&H00FFFFFF&')))
                    ass_outline_color = gr.ColorPicker(label="描边颜色", value=_parse_ass_color(style.get('OutlineColour', '&H00000000&')))
                    ass_back_color = gr.ColorPicker(label="背景颜色", value=_parse_ass_color(style.get('BackColour', '&H00000000&')))
                with gr.Row():
                    ass_bold = gr.Checkbox(label="粗体", value=bool(style.get('Bold', 0)))
                    ass_italic = gr.Checkbox(label="斜体", value=bool(style.get('Italic', 0)))
                    ass_underline = gr.Checkbox(label="下划线", value=bool(style.get('Underline', 0)))
                    ass_strikeout = gr.Checkbox(label="删除线", value=bool(style.get('StrikeOut', 0)))
            with gr.Tab("底部字幕（双语时）"):
                with gr.Row():
                    ass_bottom_fontname = gr.Textbox(label="字体名称", value=style.get('Bottom_Fontname', 'Arial'))
                    ass_bottom_fontsize = gr.Slider(label="字体大小", minimum=1, maximum=200, value=style.get('Bottom_Fontsize', 16), step=1)
                with gr.Row():
                    ass_bottom_primary_color = gr.ColorPicker(label="主颜色", value=_parse_ass_color(style.get('Bottom_PrimaryColour', '&H00FFFFFF&')))
                    ass_bottom_outline_color = gr.ColorPicker(label="描边颜色", value=_parse_ass_color(style.get('Bottom_OutlineColour', '&H00000000&')))
                    ass_bottom_back_color = gr.ColorPicker(label="背景颜色", value=_parse_ass_color(style.get('Bottom_BackColour', '&H00000000&')))
                with gr.Row():
                    ass_bottom_bold = gr.Checkbox(label="粗体", value=bool(style.get('Bottom_Bold', 0)))
                    ass_bottom_italic = gr.Checkbox(label="斜体", value=bool(style.get('Bottom_Italic', 0)))
            with gr.Tab("全局样式"):
                with gr.Row():
                    ass_border_style = gr.Dropdown(label="边框样式", choices=["描边", "不透明背景"], value="描边" if style.get('BorderStyle', 1) == 1 else "不透明背景")
                    ass_outline = gr.Slider(label="描边粗细", minimum=0.0, maximum=10.0, value=style.get('Outline', 0.5), step=0.1)
                    ass_shadow = gr.Slider(label="阴影", minimum=0.0, maximum=10.0, value=style.get('Shadow', 0.5), step=0.1)
                with gr.Row():
                    ass_scale_x = gr.Slider(label="水平缩放 %", minimum=1, maximum=1000, value=style.get('ScaleX', 100), step=1)
                    ass_scale_y = gr.Slider(label="垂直缩放 %", minimum=1, maximum=1000, value=style.get('ScaleY', 100), step=1)
                    ass_spacing = gr.Slider(label="字间距", minimum=-100, maximum=100, value=style.get('Spacing', 0), step=1)
                    ass_angle = gr.Slider(label="旋转角度", minimum=-360, maximum=360, value=style.get('Angle', 0), step=1)
                with gr.Row():
                    ass_margin_l = gr.Slider(label="左边距", minimum=0, maximum=1000, value=style.get('MarginL', 10), step=1)
                    ass_margin_r = gr.Slider(label="右边距", minimum=0, maximum=1000, value=style.get('MarginR', 10), step=1)
                    ass_margin_v = gr.Slider(label="垂直边距", minimum=0, maximum=1000, value=style.get('MarginV', 10), step=1)
                ass_alignment = gr.Dropdown(label="对齐位置", choices=["左下", "中下", "右下", "左中", "正中", "右中", "左上", "中上", "右上"],
                    value={1: "左下", 2: "中下", 3: "右下", 4: "左中", 5: "正中", 6: "右中", 7: "左上", 8: "中上", 9: "右上"}.get(style.get('Alignment', 2), "中下"))
        with gr.Row():
            ass_save_btn = gr.Button("💾 保存样式", variant="primary")
            ass_reset_btn = gr.Button("🔄 恢复默认")
            ass_status = gr.Textbox(label="状态", interactive=False, visible=True)

        def save_ass_style(fontname, fontsize, primary_color, outline_color, back_color, bold, italic, underline, strikeout,
                           bottom_fontname, bottom_fontsize, bottom_primary_color, bottom_outline_color, bottom_back_color,
                           bottom_bold, bottom_italic, border_style, outline, shadow, scale_x, scale_y, spacing, angle,
                           margin_l, margin_r, margin_v, alignment):
            am = {"左下": 1, "中下": 2, "右下": 3, "左中": 4, "正中": 5, "右中": 6, "左上": 7, "中上": 8, "右上": 9}
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
                'BorderStyle': 1 if border_style == "描边" else 3, 'Outline': float(outline), 'Shadow': float(shadow),
                'Alignment': am.get(alignment, 2), 'MarginL': int(margin_l), 'MarginR': int(margin_r),
                'MarginV': int(margin_v), 'Encoding': 1,
            })
            return "✅ 样式已保存"

        def reset_ass_style():
            _save_ass_style(DEFAULT_ASS_STYLE.copy())
            s = DEFAULT_ASS_STYLE
            return (s['Fontname'], s['Fontsize'], _parse_ass_color(s['PrimaryColour']), _parse_ass_color(s['OutlineColour']),
                    _parse_ass_color(s['BackColour']), bool(s['Bold']), bool(s['Italic']), bool(s['Underline']), bool(s['StrikeOut']),
                    s['Bottom_Fontname'], s['Bottom_Fontsize'], _parse_ass_color(s['Bottom_PrimaryColour']),
                    _parse_ass_color(s['Bottom_OutlineColour']), _parse_ass_color(s['Bottom_BackColour']),
                    bool(s['Bottom_Bold']), bool(s['Bottom_Italic']),
                    "描边" if s['BorderStyle'] == 1 else "不透明背景",
                    s['Outline'], s['Shadow'], s['ScaleX'], s['ScaleY'], s['Spacing'], s['Angle'],
                    s['MarginL'], s['MarginR'], s['MarginV'],
                    {1: "左下", 2: "中下", 3: "右下", 4: "左中", 5: "正中", 6: "右中", 7: "左上", 8: "中上", 9: "右上"}.get(s['Alignment'], "中下"),
                    "✅ 已恢复默认样式")

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

    gr.Markdown("### 渠道设置")
    gr.Markdown("配置各渠道的 API 地址、SK 密钥等信息。**保存后与桌面版 (sp.exe) 通用**，配置文件存储在 `videotrans/params.json` 中。")

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

                        save_btn = gr.Button("💾 保存", size="sm")
                        status = gr.Textbox(label="", interactive=False, visible=True)

                        # 使用闭包捕获当前值
                        def make_save_handler(field_keys, field_widgets):
                            def handler(*values):
                                data = {}
                                for k, v in zip(field_keys, values):
                                    data[k] = v
                                _save_params(data)
                                return "✅ 已保存"
                            return handler

                        save_btn.click(
                            fn=make_save_handler([f[0] for f in fields], [f[1] for f in fields]),
                            inputs=[f[1] for f in fields],
                            outputs=[status],
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
            w = gr.Dropdown(choices=options, value=val if val in options else options[0],
                            label="", interactive=True)
        elif val.lower() in ('true', 'false'):
            w = gr.Checkbox(value=val.lower() == 'true', label="", interactive=True)
        else:
            w = gr.Textbox(value=val, label="", lines=3 if area else 1, interactive=True)
    _all_widgets[key] = w


def _save_section(section_key, keys):
    """为指定分区创建保存按钮和状态显示"""
    import gradio as gr
    with gr.Row():
        save_btn = gr.Button(f"💾 保存 {ADVANCED_SECTION_TITLES.get(section_key, section_key)}", variant="primary", size="sm")
        status = gr.Markdown("", visible=False)

    def _make_handler(k_list):
        def handler(*values):
            data = {}
            for k, v in zip(k_list, values):
                data[k] = str(v)
            _save_settings(data)
            return gr.Markdown(f"✅ 已保存", visible=True)
        return handler

    save_btn.click(fn=_make_handler(keys), inputs=[_all_widgets[k] for k in keys], outputs=[status])


# ---------------------------------------------------------------------------
# 高级选项设置面板（紧凑网格布局）
# ---------------------------------------------------------------------------
ADVANCED_SECTION_TITLES = {
    "common": "通用设置", "video": "视频输出控制", "whisper": "语音识别参数",
    "trans": "字幕翻译调整", "dubbing": "字幕配音调整",
    "justify": "字幕声音画面对齐", "prompt_init": "Whisper模型提示词",
}


def build_advanced_settings():
    import gradio as gr
    gr.Markdown("配置全局高级参数。**保存后与桌面版 (sp.exe) 通用**，配置文件存储在 `videotrans/cfg.json` 中。\n⚠️ 部分参数修改后需要**重启软件**才能生效。")

    # ---- 通用设置 ----
    with gr.Accordion("📋 通用设置", open=True):
        with gr.Row():
            _w("lang", "软件界面语言", "设置后需重启")
            _w("countdown_sec", "单视频暂停倒计时", "设为0跳过编辑窗口")
            _w("retry_nums", "失败后重试次数", "")
        with gr.Row():
            _w("llm_chunk_size", "LLM断句每批字幕行数", "默认20")
            _w("llm_ai_type", "LLM断句AI渠道", "chatgpt/deepseek")
            _w("batch_nums", "批量每批数量", "0=不限制")
        with gr.Row():
            _w("dont_notify", "禁用桌面通知", "")
            _w("show_more_settings", "主界面显示所有参数?", "")
            _w("homedir", "独立功能输出目录", "")
        with gr.Row():
            _w("process_max", "CPU任务数[重启]", "不超过cpu核数")
            _w("process_max_gpu", "GPU任务数[重启]", "多卡或显存>24G才>1")
            _w("multi_gpus", "多显卡模式[重启]", "")
        _save_section("common", ["lang", "countdown_sec", "retry_nums", "llm_chunk_size", "llm_ai_type",
                                  "batch_nums", "dont_notify", "show_more_settings", "homedir",
                                  "process_max", "process_max_gpu", "multi_gpus"])

    # ---- 视频输出控制 ----
    with gr.Accordion("📋 视频输出控制", open=False):
        with gr.Row():
            _w("crf", "视频质量(0=无损,51=差)", "")
            _w("preset", "压缩率", "ultrafast→veryslow")
            _w("video_codec", "264/265编码", "")
        with gr.Row():
            _w("out_video_ext", "输出格式", "mp4/mkv")
            _w("fps_mode", "帧率模式", "vfr/cfr")
            _w("force_lib", "强制软编码?", "")
        with gr.Row():
            _w("hw_decode", "cuda硬解码", "")
            _w("ffmpeg_cmd", "自定义ffmpeg参数", "")
        _save_section("video", ["crf", "preset", "video_codec", "out_video_ext", "fps_mode",
                                 "force_lib", "hw_decode", "ffmpeg_cmd"])

    # ---- 语音识别参数 ----
    with gr.Accordion("📋 语音识别参数", open=False):
        with gr.Row():
            _w("vad_type", "选择VAD", "tenvad/silero")
            _w("threshold", "语音阈值", "")
            _w("no_speech_threshold", "非语音阈值", "")
        with gr.Row():
            _w("max_speech_duration_s", "最长语音(秒)", "")
            _w("min_speech_duration_ms", "最短语音(毫秒)", "")
            _w("min_silence_duration_ms", "静音分割(毫秒)", "")
        with gr.Row():
            _w("max_speech_duration_s2", "二次识别最长(秒)", "")
            _w("min_speech_duration_ms2", "二次识别最短(毫秒)", "")
            _w("merge_short_sub", "合并过短字幕", "")
        with gr.Row():
            _w("whisper_prepare", "Whisper预分割?", "clone配音时选中")
            _w("speaker_type", "说话人分离模型", "内置/pyannote")
            _w("hf_token", "Huggingface token", "pyannote需要")
        with gr.Row():
            _w("cuda_com_type", "计算数据类型", "int8/float16/float32")
            _w("beam_size", "beam_size", "1-5")
            _w("best_of", "best_of", "1-5")
        with gr.Row():
            _w("condition_on_previous_text", "上下文感知", "")
            _w("repetition_penalty", "重复惩罚", "")
            _w("compression_ratio_threshold", "文本压缩率", "")
        with gr.Row():
            _w("temperature", "采样温度", "")
            _w("hotwords", "热词", "逗号分隔")
            _w("gemini_recogn_chunk", "Gemini切片数", "")
        with gr.Row():
            _w("zh_hant_s", "繁体转简体", "")
            _w("del_end_punc", "删除末尾标点", "")
        with gr.Row():
            _w("model_list", "faster-whisper模型", "逗号分隔", area=True)
        with gr.Row():
            _w("Whisper_cpp_models", "whisper.cpp模型", "逗号分隔", area=True)
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
    with gr.Accordion("📋 字幕翻译调整", open=False):
        with gr.Row():
            _w("trans_thread", "传统翻译每批行数", "")
            _w("aitrans_thread", "AI翻译每批行数", "")
            _w("aitrans_temperature", "AI温度值", "默认1.0")
        with gr.Row():
            _w("translation_wait", "翻译后暂停秒", "")
            _w("aisendsrt", "发送完整字幕", "")
            _w("aitrans_context", "一次性翻译所有行", "需超长上下文模型")
        _save_section("trans", ["trans_thread", "aitrans_thread", "aitrans_temperature",
                                 "translation_wait", "aisendsrt", "aitrans_context"])

    # ---- 字幕配音调整 ----
    with gr.Accordion("📋 字幕配音调整", open=False):
        with gr.Row():
            _w("dubbing_thread", "并发配音线程数", "")
            _w("dubbing_wait", "配音后暂停秒", "")
            _w("remove_dubb_silence", "移除配音前后静音", "")
        with gr.Row():
            _w("save_segment_audio", "保留每行配音文件", "")
            _w("normal_text", "文本规范化", "")
            _w("chattts_voice", "ChatTTS音色值", "")
        with gr.Row():
            _w("edgetts_max_concurrent_tasks", "EdgeTTS并发数", "越大越快但可能限流")
            _w("edgetts_retry_nums", "EdgeTTS重试次数", "")
            _w("noise_separate_nums", "人声分离线程数", "")
        with gr.Row():
            _w("uvr_models", "分离背景声模型", "")
        _save_section("dubbing", ["dubbing_thread", "dubbing_wait", "remove_dubb_silence",
                                   "save_segment_audio", "normal_text", "chattts_voice",
                                   "edgetts_max_concurrent_tasks", "edgetts_retry_nums",
                                   "noise_separate_nums", "uvr_models"])

    # ---- 字幕声音画面对齐 ----
    with gr.Accordion("📋 字幕声音画面对齐", open=False):
        with gr.Row():
            _w("max_audio_speed_rate", "音频加速最大倍数", "默认100")
            _w("max_video_pts_rate", "视频慢放最大倍数", "默认10，≤10")
        with gr.Row():
            _w("cjk_len", "中日韩字幕单行字符数", "")
            _w("other_len", "其他语言字幕单行字符数", "")
        _save_section("justify", ["max_audio_speed_rate", "max_video_pts_rate", "cjk_len", "other_len"])

    # ---- Whisper模型提示词 ----
    with gr.Accordion("📋 Whisper模型提示词", open=False):
        for i in range(0, len(_prompt_keys_list), 3):
            with gr.Row():
                for k in _prompt_keys_list[i:i+3]:
                    _w(k, _prompt_labels.get(k, k), "")
        _save_section("prompt_init", _prompt_keys_list)


# ---------------------------------------------------------------------------
# UI 构建
# ---------------------------------------------------------------------------
def build_ui():
    import gradio as gr

    with gr.Blocks(title="pyVideoTrans WebUI") as app:
        gr.Markdown("""
# pyVideoTrans 视频翻译 WebUI
*该界面仅实现部分功能，完整功能请使用桌面软件版(sp.exe 或 sp.py)*

> 📖 **文档站**：[https://pyvideotrans.com](https://pyvideotrans.com) ｜
> 💻 **开源地址**：[https://github.com/jianchang512/pyvideotrans](https://github.com/jianchang512/pyvideotrans)
        """)

        with gr.Tabs():
            # === Tab 1: 视频翻译 ===
            with gr.Tab("🎬 视频翻译", id="translate"):
                prev_recogn = gr.State(value=RECOGN_NAMES[DEFAULT_RECOGN])
                prev_translate = gr.State(value=TRANSLATE_NAMES[DEFAULT_TRANSLATE])
                prev_tts = gr.State(value=TTS_NAMES[DEFAULT_TTS])

                with gr.Row():
                    with gr.Column(scale=3):
                        input_file = gr.File(label="选择视频/音频文件", file_types=["video", "audio"], type="filepath")
                        gr.Markdown("### 语音识别")
                        recogn_choice = gr.Dropdown(choices=RECOGN_NAMES, value=RECOGN_NAMES[DEFAULT_RECOGN], label="识别渠道", interactive=True)
                        model_choice = gr.Dropdown(choices=FASTER_MODEL_NAMES, value=DEFAULT_MODEL, label="模型", interactive=True)
                        gr.Markdown("### 字幕翻译")
                        translate_choice = gr.Dropdown(choices=TRANSLATE_NAMES, value=TRANSLATE_NAMES[DEFAULT_TRANSLATE], label="翻译渠道", interactive=True)
                        source_lang = gr.Dropdown(choices=LANG_DISPLAY_NAMES, value=DEFAULT_SOURCE_LANG, label="发音语言（源语言）", interactive=True)
                        target_lang = gr.Dropdown(choices=LANG_DISPLAY_NAMES, value=DEFAULT_TARGET_LANG, label="目标语言", interactive=True)
                        gr.Markdown("### 字幕配音")
                        tts_choice = gr.Dropdown(choices=TTS_NAMES, value=TTS_NAMES[DEFAULT_TTS], label="配音渠道", interactive=True)
                        voice_role = gr.Dropdown(choices=["No"], value="No", label="配音角色", interactive=True)
                        gr.Markdown("### 对齐与字幕")
                        with gr.Row():
                            voice_autorate = gr.Checkbox(label="配音加速", value=True)
                            video_autorate = gr.Checkbox(label="视频慢速", value=False)
                        with gr.Row():
                            voice_rate = gr.Slider(minimum=-50, maximum=50, value=0, step=1, label="配音语速 (%)")
                            volume_rate = gr.Slider(minimum=-95, maximum=100, value=0, step=1, label="音量调整 (%)")
                            pitch_rate = gr.Slider(minimum=-100, maximum=100, value=0, step=1, label="音调 (Hz)")
                        subtitle_type = gr.Dropdown(choices=list(SUBTITLE_TYPES.keys()), value=DEFAULT_SUBTITLE_TYPE, label="字幕嵌入类型", interactive=True)
                        gr.Markdown("### 更多设置")
                        with gr.Row():
                            remove_noise = gr.Checkbox(label="降噪", value=False)
                            fix_punc = gr.Dropdown(choices=list(PUNC_OPTIONS.keys()), value="默认标点", label="标点处理", interactive=True)
                        with gr.Row():
                            is_separate = gr.Checkbox(label="分离人声背景声", value=False)
                            embed_bgm = gr.Checkbox(label="重新嵌入背景声", value=True)
                        with gr.Row():
                            loop_bgm = gr.Dropdown(choices=list(LOOP_BGM_OPTIONS.keys()), value="背景音截断", label="背景音处理", interactive=True)
                            backaudio_volume = gr.Slider(minimum=0.0, maximum=2.0, value=0.8, step=0.1, label="背景音量")
                        gr.Markdown("### 其他")
                        cuda_accel = gr.Checkbox(label="启用 CUDA 加速", value=False)
                        channel_warning = gr.Markdown("", visible=False)
                        build_ass_editor()
                        start_btn = gr.Button("🚀 开始执行", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        log_output = gr.Textbox(label="执行日志", lines=20, interactive=False)
                        video_preview = gr.Video(label="视频预览", interactive=False)
                        result_files = gr.File(label="输出文件（点击下载）", interactive=False)

                # 渠道验证
                def validate_recogn(choice, prev):
                    idx = _recogn_index_from_display(choice)
                    
                    _rs=recognition.is_input_api(recogn_type=idx, return_str=True)
                    if _rs is not True:
                        msg = "渠道「{}」暂不可用，已自动回退".format(choice)
                        gr.Warning(msg)
                        return prev, f"⚠️ {msg}"
                    return choice, ""

                def validate_translate(choice, prev):
                    idx = _translate_index_from_display(choice)
                    _rs=translator.is_allow_translate(translate_type=idx, return_str=True)
                    if _rs is not True:
                        msg = "渠道「{}」暂不可用，已自动回退".format(choice)
                        gr.Warning(msg)
                        return prev, f"⚠️ {msg}"
                    return choice, ""

                def tts_change_handler(choice, prev, target_display):
                    idx = _tts_index_from_display(choice)
                    warning = ""
                    _rs=tts.is_input_api(tts_type=idx, return_str=True)
                    if _rs is not True:
                        msg = "渠道「{}」暂不可用，已自动回退".format(choice)
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

                recogn_choice.change(fn=validate_recogn, inputs=[recogn_choice, prev_recogn], outputs=[recogn_choice, channel_warning])
                translate_choice.change(fn=validate_translate, inputs=[translate_choice, prev_translate], outputs=[translate_choice, channel_warning])
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
                _BTN_RUNNING = gr.update(value="⏳ 执行中...", interactive=False)
                _BTN_IDLE = gr.update(value="🚀 开始执行", interactive=True)

                def run_translation(file_path, recogn_display, model_name, translate_display,
                                    source_display, target_display, tts_display, voice_role_name,
                                    voice_autorate_val, video_autorate_val,
                                    voice_rate_val, volume_rate_val, pitch_rate_val,
                                    subtitle_type_name, remove_noise_val, fix_punc_name,
                                    is_separate_val, embed_bgm_val, loop_bgm_name, backaudio_volume_val,
                                    cuda_val):
                    if not file_path:
                        yield "❌ 请先选择一个视频或音频文件", None, [], _BTN_IDLE
                        return
                    log_lines = []
                    def log(msg):
                        log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
                        return "\n".join(log_lines)
                    yield log("初始化环境..."), None, [], _BTN_RUNNING

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
                        _target_dir = f'{ROOT_DIR}/output/{_nospacebasename}'
                        _file_obj['target_dir'] = _target_dir
                        Path(_cache_folder).mkdir(parents=True, exist_ok=True)
                        Path(_target_dir).mkdir(parents=True, exist_ok=True)
                        from dataclasses import asdict
                        common_params = {'name': file_path, "cache_folder": _cache_folder}
                        common_params.update(asdict(_file_obj))
                        yield log(f"源文件: {Path(file_path).name}"), None, [], _BTN_RUNNING

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
                            "subtitle_type": subtitle_val, "clear_cache": True,
                            "embed_bgm": embed_bgm_val, "loop_backaudio": loop_bgm_val,
                            "backaudio_volume": backaudio_volume_val, "background_music": "",
                        }
                        params_dict = {**common_params, **vtv_params}

                        yield log(f"识别: {RECOGN_NAMES[recogn_idx]}  翻译: {TRANSLATE_NAMES[translate_idx]}  配音: {TTS_NAMES[tts_idx]}"), None, [], _BTN_RUNNING
                        yield log(f"语言: {source_code} → {target_code}  角色: {voice_role_name}"), None, [], _BTN_RUNNING
                        yield log(""), None, [], _BTN_RUNNING

                        yield log("▶ 开始执行视频翻译..."), None, [], _BTN_RUNNING
                        from videotrans.task.trans_create import TransCreate
                        from videotrans.task.taskcfg import TaskCfgVTT
                        trk = TransCreate(cfg=TaskCfgVTT(**params_dict))

                        stages = [
                            ("阶段 1/8: 预处理...", "prepare", "预处理完成"),
                            ("阶段 2/8: 语音识别...", "recogn", "语音识别完成"),
                            ("阶段 3/8: 说话人分离...", "diariz", "说话人分离完成"),
                            ("阶段 4/8: 字幕翻译...", "trans", "字幕翻译完成"),
                            ("阶段 5/8: 配音生成...", "dubbing", "配音生成完成"),
                            ("阶段 6/8: 音画对齐...", "align", "音画对齐完成"),
                            ("阶段 7/8: 二次识别...", "recogn2pass", "二次识别完成"),
                            ("阶段 8/8: 最终合成...", "assembling", "最终合成完成"),
                        ]
                        for stage_name, method, done_msg in stages:
                            yield log(stage_name), None, [], _BTN_RUNNING
                            getattr(trk, method)()
                            if method != "assembling":
                                yield log(f"✓ {done_msg}"), None, [], _BTN_RUNNING

                        trk.task_done()
                        yield log("✓ 视频合成完成"), None, [], _BTN_RUNNING
                        yield log("✅ 全部任务执行完毕！"), None, [], _BTN_RUNNING

                        output_files, video_preview_path = [], None
                        target_path = Path(_target_dir)
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
                        yield log(f"输出目录: {_target_dir}"), video_preview_path, output_files, _BTN_IDLE

                    except Exception as e:
                        tb = traceback.format_exc()
                        yield log(f"❌ 执行出错: {str(e)}\n\n{tb}"), None, [], _BTN_IDLE

                start_btn.click(fn=run_translation,
                    inputs=[input_file, recogn_choice, model_choice, translate_choice,
                            source_lang, target_lang, tts_choice, voice_role,
                            voice_autorate, video_autorate, voice_rate, volume_rate, pitch_rate,
                            subtitle_type, remove_noise, fix_punc,
                            is_separate, embed_bgm, loop_bgm, backaudio_volume, cuda_accel],
                    outputs=[log_output, video_preview, result_files, start_btn])

            # === Tab 2: 渠道设置 ===
            with gr.Tab("⚙️ 渠道设置", id="settings"):
                build_channel_settings()

            # === Tab 3: 高级选项 ===
            with gr.Tab("🔧 高级选项", id="advanced"):
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
        app.launch(server_name=args.host, server_port=args.port, share=args.share, inbrowser=True, theme=gr.themes.Soft())
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ 启动失败: {e}")
