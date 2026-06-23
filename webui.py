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
# 语言常量 —— 修改此处可切换 UI 语言
# ---------------------------------------------------------------------------
CLI_LANG = "zh"
os.environ['PYVIDEOTRANS_LANG']=CLI_LANG

# ---------------------------------------------------------------------------
# 初始化 videotrans 环境
# ---------------------------------------------------------------------------
from videotrans.configure import config
config.init_run()

from videotrans.configure.config import ROOT_DIR, TEMP_DIR, app_cfg
from videotrans.configure.contants import FASTER_MODELS_DICT
from videotrans import recognition, translator, tts
from videotrans.util import tools
from videotrans.util.gpus import getset_gpu
from videotrans.util.help_role import role_menu

# ---------------------------------------------------------------------------
# 渠道名称列表
# ---------------------------------------------------------------------------
RECOGN_NAMES: List[str] = recognition.RECOGN_NAME_LIST
TRANSLATE_NAMES: List[str] = translator.TRANSLASTE_NAME_LIST
TTS_NAMES: List[str] = tts.TTS_NAME_LIST
LANGNAME_DICT: dict = translator.LANGNAME_DICT

# ---------------------------------------------------------------------------
# 可选渠道索引（整数 ID）
# ---------------------------------------------------------------------------
SELECTABLE_RECOGN = {0, 1,2,3,4}
DEFAULT_RECOGN = 0

SELECTABLE_TRANSLATE = {0, 1, 2}
DEFAULT_TRANSLATE = 0

SELECTABLE_TTS = {0, 1, 3, 4, 5, 6, 7,31}
DEFAULT_TTS = 0

# faster-whisper 模型列表
FASTER_MODEL_NAMES = list(FASTER_MODELS_DICT.keys())
DEFAULT_MODEL = "large-v3-turbo" if "large-v3-turbo" in FASTER_MODEL_NAMES else FASTER_MODEL_NAMES[0]

# 语言列表
LANG_DISPLAY_NAMES = list(LANGNAME_DICT.values())
DEFAULT_SOURCE_LANG = LANG_DISPLAY_NAMES[0]
DEFAULT_TARGET_LANG = "-"

# 字幕类型
SUBTITLE_TYPES = {
    "不嵌入字幕": 0,
    "嵌入硬字幕": 1,
    "嵌入软字幕": 2,
    "嵌入硬字幕(双语)": 3,
    "嵌入软字幕(双语)": 4,
}
DEFAULT_SUBTITLE_TYPE = "嵌入硬字幕"

# 标点选项
PUNC_OPTIONS = {
    "默认标点": 0,
    "恢复标点": 1,
    "删除标点": 2,
}

# 背景循环选项
LOOP_BGM_OPTIONS = {
    "背景音截断": 0,
    "背景音循环": 1,
}

# ---------------------------------------------------------------------------
# ASS 字幕样式
# ---------------------------------------------------------------------------
ASS_JSON_FILE = f'{ROOT_DIR}/videotrans/ass.json'

DEFAULT_ASS_STYLE = {
    'Name': 'Default',
    'Fontname': 'Arial',
    'Bottom_Fontname': 'Arial',
    'Fontsize': 16,
    'Bottom_Fontsize': 16,
    'PrimaryColour': '&H00FFFFFF&',
    'Bottom_PrimaryColour': '&H00FFFFFF&',
    'SecondaryColour': '&H00FFFFFF&',
    'OutlineColour': '&H00000000&',
    'BackColour': '&H00000000&',
    'Bold': 0,
    'Italic': 0,
    'Bottom_SecondaryColour': '&H00FFFFFF&',
    'Bottom_OutlineColour': '&H00000000&',
    'Bottom_BackColour': '&H00000000&',
    'Bottom_Bold': 0,
    'Bottom_Italic': 0,
    'Underline': 0,
    'StrikeOut': 0,
    'ScaleX': 100,
    'ScaleY': 100,
    'Spacing': 0,
    'Angle': 0,
    'BorderStyle': 1,
    'Outline': 0.5,
    'Shadow': 0.5,
    'Alignment': 2,
    'MarginL': 10,
    'MarginR': 10,
    'MarginV': 10,
    'Encoding': 1,
}


def _parse_ass_color(color_str: str) -> str:
    """将 ASS 颜色格式 &HAABBGGRR& 转为 #RRGGBB 供 Gradio ColorPicker 使用"""
    if not color_str.startswith('&H') or not color_str.endswith('&'):
        return '#ffffff'
    hex_str = color_str[2:-1].upper()
    if len(hex_str) == 6:
        b = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        r = int(hex_str[4:6], 16)
        return f'#{r:02x}{g:02x}{b:02x}'
    elif len(hex_str) == 8:
        a = int(hex_str[0:2], 16)
        b = int(hex_str[2:4], 16)
        g = int(hex_str[4:6], 16)
        r = int(hex_str[6:8], 16)
        return f'#{r:02x}{g:02x}{b:02x}'
    return '#ffffff'


def _to_ass_color(hex_color: str) -> str:
    """将 #RRGGBB 转为 ASS 颜色格式 &H00BBGGRR&"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f'&H00{b:02X}{g:02X}{r:02X}&'
    return '&H00FFFFFF&'


def _load_ass_style() -> dict:
    """从 ass.json 加载样式，不存在则用默认值"""
    try:
        if Path(ASS_JSON_FILE).exists():
            with open(ASS_JSON_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_ASS_STYLE.copy()


def _save_ass_style(style: dict):
    """保存样式到 ass.json"""
    Path(ASS_JSON_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(ASS_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(style, f, indent=4, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _lang_code_from_display(display_name: str) -> str:
    for code, name in LANGNAME_DICT.items():
        if name == display_name:
            return code
    return display_name


def _tts_index_from_display(display_name: str) -> int:
    for i, name in enumerate(TTS_NAMES):
        if name == display_name:
            return i
    return 0


def _recogn_index_from_display(display_name: str) -> int:
    for i, name in enumerate(RECOGN_NAMES):
        if name == display_name:
            return i
    return 0


def _translate_index_from_display(display_name: str) -> int:
    for i, name in enumerate(TRANSLATE_NAMES):
        if name == display_name:
            return i
    return 0


def _format_rate(value: int) -> str:
    return f"+{value}%" if value >= 0 else f"{value}%"


def _format_pitch(value: int) -> str:
    return f"+{value}Hz" if value >= 0 else f"{value}Hz"


# ---------------------------------------------------------------------------
# ASS 样式编辑器（纯 Gradio）
# ---------------------------------------------------------------------------
def build_ass_editor():
    """构建 ASS 字幕样式编辑界面，返回 Gradio Blocks"""
    import gradio as gr

    style = _load_ass_style()

    with gr.Accordion("🎨 硬字幕样式编辑", open=False):
        gr.Markdown("修改后点击「保存样式」，样式将应用于所有嵌入硬字幕的任务。")

        with gr.Tabs():
            # === 主字幕样式 ===
            with gr.Tab("主字幕"):
                with gr.Row():
                    ass_fontname = gr.Textbox(label="字体名称", value=style.get('Fontname', 'Arial'))
                    ass_fontsize = gr.Slider(label="字体大小", minimum=1, maximum=200,
                                             value=style.get('Fontsize', 16), step=1)
                with gr.Row():
                    ass_primary_color = gr.ColorPicker(label="主颜色", value=_parse_ass_color(style.get('PrimaryColour', '&H00FFFFFF&')))
                    ass_outline_color = gr.ColorPicker(label="描边颜色", value=_parse_ass_color(style.get('OutlineColour', '&H00000000&')))
                    ass_back_color = gr.ColorPicker(label="背景颜色", value=_parse_ass_color(style.get('BackColour', '&H00000000&')))
                with gr.Row():
                    ass_bold = gr.Checkbox(label="粗体", value=bool(style.get('Bold', 0)))
                    ass_italic = gr.Checkbox(label="斜体", value=bool(style.get('Italic', 0)))
                    ass_underline = gr.Checkbox(label="下划线", value=bool(style.get('Underline', 0)))
                    ass_strikeout = gr.Checkbox(label="删除线", value=bool(style.get('StrikeOut', 0)))

            # === 底部副字幕样式 ===
            with gr.Tab("底部字幕（双语时）"):
                with gr.Row():
                    ass_bottom_fontname = gr.Textbox(label="字体名称", value=style.get('Bottom_Fontname', 'Arial'))
                    ass_bottom_fontsize = gr.Slider(label="字体大小", minimum=1, maximum=200,
                                                    value=style.get('Bottom_Fontsize', 16), step=1)
                with gr.Row():
                    ass_bottom_primary_color = gr.ColorPicker(label="主颜色", value=_parse_ass_color(style.get('Bottom_PrimaryColour', '&H00FFFFFF&')))
                    ass_bottom_outline_color = gr.ColorPicker(label="描边颜色", value=_parse_ass_color(style.get('Bottom_OutlineColour', '&H00000000&')))
                    ass_bottom_back_color = gr.ColorPicker(label="背景颜色", value=_parse_ass_color(style.get('Bottom_BackColour', '&H00000000&')))
                with gr.Row():
                    ass_bottom_bold = gr.Checkbox(label="粗体", value=bool(style.get('Bottom_Bold', 0)))
                    ass_bottom_italic = gr.Checkbox(label="斜体", value=bool(style.get('Bottom_Italic', 0)))

            # === 全局样式 ===
            with gr.Tab("全局样式"):
                with gr.Row():
                    ass_border_style = gr.Dropdown(label="边框样式", choices=["描边", "不透明背景"],
                                                  value="描边" if style.get('BorderStyle', 1) == 1 else "不透明背景")
                    ass_outline = gr.Slider(label="描边粗细", minimum=0.0, maximum=10.0,
                                            value=style.get('Outline', 0.5), step=0.1)
                    ass_shadow = gr.Slider(label="阴影", minimum=0.0, maximum=10.0,
                                           value=style.get('Shadow', 0.5), step=0.1)
                with gr.Row():
                    ass_scale_x = gr.Slider(label="水平缩放 %", minimum=1, maximum=1000,
                                            value=style.get('ScaleX', 100), step=1)
                    ass_scale_y = gr.Slider(label="垂直缩放 %", minimum=1, maximum=1000,
                                            value=style.get('ScaleY', 100), step=1)
                    ass_spacing = gr.Slider(label="字间距", minimum=-100, maximum=100,
                                            value=style.get('Spacing', 0), step=1)
                    ass_angle = gr.Slider(label="旋转角度", minimum=-360, maximum=360,
                                          value=style.get('Angle', 0), step=1)
                with gr.Row():
                    ass_margin_l = gr.Slider(label="左边距", minimum=0, maximum=1000,
                                             value=style.get('MarginL', 10), step=1)
                    ass_margin_r = gr.Slider(label="右边距", minimum=0, maximum=1000,
                                             value=style.get('MarginR', 10), step=1)
                    ass_margin_v = gr.Slider(label="垂直边距", minimum=0, maximum=1000,
                                             value=style.get('MarginV', 10), step=1)
                ass_alignment = gr.Dropdown(
                    label="对齐位置",
                    choices=["左下", "中下", "右下", "左中", "正中", "右中", "左上", "中上", "右上"],
                    value={1: "左下", 2: "中下", 3: "右下", 4: "左中", 5: "正中", 6: "右中", 7: "左上", 8: "中上", 9: "右上"}.get(
                        style.get('Alignment', 2), "中下"
                    ),
                )

        # 按钮行
        with gr.Row():
            ass_save_btn = gr.Button("💾 保存样式", variant="primary")
            ass_reset_btn = gr.Button("🔄 恢复默认")
            ass_status = gr.Textbox(label="状态", interactive=False, visible=True)

        # 保存逻辑
        def save_ass_style(
            fontname, fontsize, primary_color, outline_color, back_color,
            bold, italic, underline, strikeout,
            bottom_fontname, bottom_fontsize, bottom_primary_color, bottom_outline_color,
            bottom_back_color, bottom_bold, bottom_italic,
            border_style, outline, shadow, scale_x, scale_y, spacing, angle,
            margin_l, margin_r, margin_v, alignment,
        ):
            alignment_map = {"左下": 1, "中下": 2, "右下": 3, "左中": 4, "正中": 5,
                             "右中": 6, "左上": 7, "中上": 8, "右上": 9}
            new_style = {
                'Name': 'Default',
                'Fontname': fontname,
                'Bottom_Fontname': bottom_fontname,
                'Fontsize': int(fontsize),
                'Bottom_Fontsize': int(bottom_fontsize),
                'PrimaryColour': _to_ass_color(primary_color),
                'Bottom_PrimaryColour': _to_ass_color(bottom_primary_color),
                'SecondaryColour': '&H00FFFFFF&',
                'OutlineColour': _to_ass_color(outline_color),
                'BackColour': _to_ass_color(back_color),
                'Bold': 1 if bold else 0,
                'Italic': 1 if italic else 0,
                'Bottom_SecondaryColour': '&H00FFFFFF&',
                'Bottom_OutlineColour': _to_ass_color(bottom_outline_color),
                'Bottom_BackColour': _to_ass_color(bottom_back_color),
                'Bottom_Bold': 1 if bottom_bold else 0,
                'Bottom_Italic': 1 if bottom_italic else 0,
                'Underline': 1 if underline else 0,
                'StrikeOut': 1 if strikeout else 0,
                'ScaleX': int(scale_x),
                'ScaleY': int(scale_y),
                'Spacing': int(spacing),
                'Angle': int(angle),
                'BorderStyle': 1 if border_style == "描边" else 3,
                'Outline': float(outline),
                'Shadow': float(shadow),
                'Alignment': alignment_map.get(alignment, 2),
                'MarginL': int(margin_l),
                'MarginR': int(margin_r),
                'MarginV': int(margin_v),
                'Encoding': 1,
            }
            _save_ass_style(new_style)
            return "✅ 样式已保存"

        def reset_ass_style():
            _save_ass_style(DEFAULT_ASS_STYLE.copy())
            s = DEFAULT_ASS_STYLE
            return (
                s['Fontname'], s['Fontsize'],
                _parse_ass_color(s['PrimaryColour']),
                _parse_ass_color(s['OutlineColour']),
                _parse_ass_color(s['BackColour']),
                bool(s['Bold']), bool(s['Italic']), bool(s['Underline']), bool(s['StrikeOut']),
                s['Bottom_Fontname'], s['Bottom_Fontsize'],
                _parse_ass_color(s['Bottom_PrimaryColour']),
                _parse_ass_color(s['Bottom_OutlineColour']),
                _parse_ass_color(s['Bottom_BackColour']),
                bool(s['Bottom_Bold']), bool(s['Bottom_Italic']),
                "描边" if s['BorderStyle'] == 1 else "不透明背景",
                s['Outline'], s['Shadow'], s['ScaleX'], s['ScaleY'], s['Spacing'], s['Angle'],
                s['MarginL'], s['MarginR'], s['MarginV'],
                {1: "左下", 2: "中下", 3: "右下", 4: "左中", 5: "正中", 6: "右中", 7: "左上", 8: "中上", 9: "右上"}.get(s['Alignment'], "中下"),
                "✅ 已恢复默认样式",
            )

        ass_save_btn.click(
            fn=save_ass_style,
            inputs=[
                ass_fontname, ass_fontsize, ass_primary_color, ass_outline_color, ass_back_color,
                ass_bold, ass_italic, ass_underline, ass_strikeout,
                ass_bottom_fontname, ass_bottom_fontsize, ass_bottom_primary_color, ass_bottom_outline_color,
                ass_bottom_back_color, ass_bottom_bold, ass_bottom_italic,
                ass_border_style, ass_outline, ass_shadow, ass_scale_x, ass_scale_y, ass_spacing, ass_angle,
                ass_margin_l, ass_margin_r, ass_margin_v, ass_alignment,
            ],
            outputs=[ass_status],
        )

        ass_reset_btn.click(
            fn=reset_ass_style,
            inputs=[],
            outputs=[
                ass_fontname, ass_fontsize, ass_primary_color, ass_outline_color, ass_back_color,
                ass_bold, ass_italic, ass_underline, ass_strikeout,
                ass_bottom_fontname, ass_bottom_fontsize, ass_bottom_primary_color, ass_bottom_outline_color,
                ass_bottom_back_color, ass_bottom_bold, ass_bottom_italic,
                ass_border_style, ass_outline, ass_shadow, ass_scale_x, ass_scale_y, ass_spacing, ass_angle,
                ass_margin_l, ass_margin_r, ass_margin_v, ass_alignment,
                ass_status,
            ],
        )


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

> ⚠️ **渠道说明**：下拉框中显示了所有可用渠道，但出于简洁考虑，**仅免费渠道和本地内置渠道可选**。其他需要 API或需要SK的渠道因未实现设置窗口界面而暂不可用。如需使用这些渠道，请先通过桌面客户端（sp.exe）进行配置。
        """)

        prev_recogn = gr.State(value=RECOGN_NAMES[DEFAULT_RECOGN])
        prev_translate = gr.State(value=TRANSLATE_NAMES[DEFAULT_TRANSLATE])
        prev_tts = gr.State(value=TTS_NAMES[DEFAULT_TTS])

        with gr.Row():
            # ---- 左列 ----
            with gr.Column(scale=3):
                input_file = gr.File(
                    label="选择视频/音频文件",
                    file_types=["video", "audio"],
                    type="filepath",
                )

                # === 语音识别 ===
                gr.Markdown("### 语音识别")
                recogn_choice = gr.Dropdown(
                    choices=RECOGN_NAMES,
                    value=RECOGN_NAMES[DEFAULT_RECOGN],
                    label="识别渠道",
                    interactive=True,
                )
                model_choice = gr.Dropdown(
                    choices=FASTER_MODEL_NAMES,
                    value=DEFAULT_MODEL,
                    label="模型 (faster-whisper / openai-whisper)",
                    interactive=True,
                )

                # === 翻译 ===
                gr.Markdown("### 字幕翻译")
                translate_choice = gr.Dropdown(
                    choices=TRANSLATE_NAMES,
                    value=TRANSLATE_NAMES[DEFAULT_TRANSLATE],
                    label="翻译渠道",
                    interactive=True,
                )
                source_lang = gr.Dropdown(
                    choices=LANG_DISPLAY_NAMES,
                    value=DEFAULT_SOURCE_LANG,
                    label="发音语言（源语言）",
                    interactive=True,
                )
                target_lang = gr.Dropdown(
                    choices=LANG_DISPLAY_NAMES,
                    value=DEFAULT_TARGET_LANG,
                    label="目标语言",
                    interactive=True,
                )

                # === 配音 ===
                gr.Markdown("### 字幕配音")
                tts_choice = gr.Dropdown(
                    choices=TTS_NAMES,
                    value=TTS_NAMES[DEFAULT_TTS],
                    label="配音渠道",
                    interactive=True,
                )
                voice_role = gr.Dropdown(
                    choices=["No"],
                    value="No",
                    label="配音角色",
                    interactive=True,
                )

                # === 对齐与字幕 ===
                gr.Markdown("### 对齐与字幕")
                with gr.Row():
                    voice_autorate = gr.Checkbox(label="配音加速（音频加速对齐）", value=True)
                    video_autorate = gr.Checkbox(label="视频慢速", value=False)
                with gr.Row():
                    voice_rate = gr.Slider(minimum=-50, maximum=50, value=0, step=1, label="配音语速 (%)")
                    volume_rate = gr.Slider(minimum=-95, maximum=100, value=0, step=1, label="音量调整 (%)")
                    pitch_rate = gr.Slider(minimum=-100, maximum=100, value=0, step=1, label="音调 (Hz)")
                subtitle_type = gr.Dropdown(
                    choices=list(SUBTITLE_TYPES.keys()),
                    value=DEFAULT_SUBTITLE_TYPE,
                    label="字幕嵌入类型",
                    interactive=True,
                )

                # === 更多设置 ===
                gr.Markdown("### 更多设置")
                with gr.Row():
                    remove_noise = gr.Checkbox(label="降噪", value=False)
                    fix_punc = gr.Dropdown(choices=list(PUNC_OPTIONS.keys()), value="默认标点", label="标点处理", interactive=True)
                with gr.Row():
                    is_separate = gr.Checkbox(label="分离人声背景声", value=False)
                    embed_bgm = gr.Checkbox(label="重新嵌入背景声", value=True)
                with gr.Row():
                    loop_bgm = gr.Dropdown(choices=list(LOOP_BGM_OPTIONS.keys()), value="背景音截断", label="背景音处理方式", interactive=True)
                    backaudio_volume = gr.Slider(minimum=0.0, maximum=2.0, value=0.8, step=0.1, label="背景音量")

                # === 其他 ===
                gr.Markdown("### 其他")
                cuda_accel = gr.Checkbox(label="启用 CUDA 加速", value=False)

                # 警告提示（gr.Warning 弹窗 + 日志双重显示）
                channel_warning = gr.Markdown("", visible=False)

                # === 硬字幕样式编辑器（纯 Gradio）===
                build_ass_editor()

                start_btn = gr.Button("🚀 开始执行", variant="primary", size="lg")

            # ---- 右列 ----
            with gr.Column(scale=2):
                log_output = gr.Textbox(label="执行日志", lines=20, interactive=False)
                video_preview = gr.Video(label="视频预览", interactive=False,autoplay=True)
                result_files = gr.File(label="输出文件（点击下载）", interactive=False)

        # ---- 渠道验证 + 配音角色更新 ----
        def validate_recogn(choice, prev):
            idx = _recogn_index_from_display(choice)
            # 判断是否填写自定义识别 api openai-api识别
            _rs=recognition.is_input_api(recogn_type=idx,return_str=True)
            if _rs is not True:
                msg = f"渠道「{choice}」暂不可用，已自动回退\n{_rs}"
                gr.Warning(msg)
                return prev, f"⚠️ {msg}"
            return choice, ""

        def validate_translate(choice, prev):
            idx = _translate_index_from_display(choice)
            _rs=translator.is_allow_translate(translate_type=idx,only_key=True, return_str=True)
            if _rs is not True:
                msg = f"渠道「{choice}」暂不可用，已自动回退\n{_rs}"
                gr.Warning(msg)
                return prev, f"⚠️ {msg}"
            return choice, ""

        def tts_change_handler(choice, prev, target_display):
            """合并：验证渠道 + 更新配音角色"""
            idx = _tts_index_from_display(choice)
            _rs=tts.is_input_api(tts_type=idx,return_str=True)
            warning = ""
            if _rs is not True:
                display_name = choice.split("【不可选】")[-1] if "【不可选】" in choice else choice
                msg = f"渠道「{choice}」暂不可用，已自动回退\n{_rs}"
                gr.Warning(msg)
                choice = prev
                warning = f"⚠️ {msg}"

            # 更新配音角色
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

        # 目标语言变化时也更新配音角色
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

        # ---- 执行翻译 ----
        _BTN_RUNNING = gr.update(value="⏳ 执行中...", interactive=False)
        _BTN_IDLE = gr.update(value="🚀 开始执行", interactive=True)

        def run_translation(
            file_path, recogn_display, model_name, translate_display,
            source_display, target_display, tts_display, voice_role_name,
            voice_autorate_val, video_autorate_val,
            voice_rate_val, volume_rate_val, pitch_rate_val,
            subtitle_type_name, remove_noise_val, fix_punc_name,
            is_separate_val, embed_bgm_val, loop_bgm_name, backaudio_volume_val,
            cuda_val,
        ):
            log_lines = []
            def log(msg):
                log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
                return "\n".join(log_lines)
            if not file_path:
                yield "❌ 请先选择一个视频或音频文件", None, [], _BTN_IDLE
                return

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

                params = {**common_params, **vtv_params}

                yield log(f"识别渠道: {RECOGN_NAMES[recogn_idx]} (ID={recogn_idx})"), None, [], _BTN_RUNNING
                yield log(f"翻译渠道: {TRANSLATE_NAMES[translate_idx]} (ID={translate_idx})"), None, [], _BTN_RUNNING
                yield log(f"配音渠道: {TTS_NAMES[tts_idx]} (ID={tts_idx})"), None, [], _BTN_RUNNING
                yield log(f"配音角色: {voice_role_name}"), None, [], _BTN_RUNNING
                yield log(f"语言: {source_code} → {target_code}"), None, [], _BTN_RUNNING
                yield log(f"字幕类型: {subtitle_type_name} (ID={subtitle_val})"), None, [], _BTN_RUNNING
                yield log(f"语速: {_format_rate(int(voice_rate_val))}  音量: {_format_rate(int(volume_rate_val))}  音调: {_format_pitch(int(pitch_rate_val))}"), None, [], _BTN_RUNNING
                yield log(f"降噪: {'开' if remove_noise_val else '关'}  标点: {fix_punc_name}  分离人声: {'开' if is_separate_val else '关'}"), None, [], _BTN_RUNNING
                yield log(f"嵌入背景: {'开' if embed_bgm_val else '关'}  背景处理: {loop_bgm_name}  背景音量: {backaudio_volume_val}"), None, [], _BTN_RUNNING
                yield log(f"CUDA: {'启用' if cuda_val else '关闭'}"), None, [], _BTN_RUNNING
                yield log(""), None, [], _BTN_RUNNING

                yield log("▶ 开始执行视频翻译..."), None, [], _BTN_RUNNING

                from videotrans.task.trans_create import TransCreate
                from videotrans.task.taskcfg import TaskCfgVTT

                trk = TransCreate(cfg=TaskCfgVTT(**params))

                yield log("阶段 1/8: 预处理（分离音视频）..."), None, [], _BTN_RUNNING
                trk.prepare()
                yield log("✓ 预处理完成"), None, [], _BTN_RUNNING

                yield log("阶段 2/8: 语音识别..."), None, [], _BTN_RUNNING
                trk.recogn()
                yield log("✓ 语音识别完成"), None, [], _BTN_RUNNING

                yield log("阶段 3/8: 说话人分离..."), None, [], _BTN_RUNNING
                trk.diariz()
                yield log("✓ 说话人分离完成"), None, [], _BTN_RUNNING

                yield log("阶段 4/8: 字幕翻译..."), None, [], _BTN_RUNNING
                trk.trans()
                yield log("✓ 字幕翻译完成"), None, [], _BTN_RUNNING

                yield log("阶段 5/8: 配音生成..."), None, [], _BTN_RUNNING
                trk.dubbing()
                yield log("✓ 配音生成完成"), None, [], _BTN_RUNNING

                yield log("阶段 6/8: 音画对齐..."), None, [], _BTN_RUNNING
                trk.align()
                yield log("✓ 音画对齐完成"), None, [], _BTN_RUNNING

                yield log("阶段 7/8: 二次识别..."), None, [], _BTN_RUNNING
                trk.recogn2pass()
                yield log("✓ 二次识别完成"), None, [], _BTN_RUNNING

                yield log("阶段 8/8: 最终合成..."), None, [], _BTN_RUNNING
                trk.assembling()
                trk.task_done()
                yield log("✓ 视频合成完成"), None, [], _BTN_RUNNING

                yield log(""), None, [], _BTN_RUNNING
                yield log("✅ 全部任务执行完毕！"), None, [], _BTN_RUNNING

                output_files = []
                video_preview_path = None
                target_path = Path(_target_dir)
                if target_path.exists():
                    for f in sorted(target_path.rglob("*")):
                        if f.is_file():
                            if f.suffix.lower() == '.mp4' and video_preview_path is None:
                                video_preview_path = str(f)
                            else:
                                output_files.append(str(f))

                if not output_files and video_preview_path is None:
                    cache_path = Path(_cache_folder)
                    if cache_path.exists():
                        for f in sorted(cache_path.rglob("*")):
                            if f.is_file():
                                if f.suffix.lower() == '.mp4' and video_preview_path is None:
                                    video_preview_path = str(f)
                                elif f.suffix.lower() in ('.mkv', '.wav', '.srt', '.txt', '.mp3'):
                                    output_files.append(str(f))

                yield log(f"输出目录: {_target_dir}"), video_preview_path, output_files, _BTN_IDLE

            except Exception as e:
                tb = traceback.format_exc()
                yield log(f"❌ 执行出错: {str(e)}\n\n{tb}"), None, [], _BTN_IDLE

        start_btn.click(
            fn=run_translation,
            inputs=[
                input_file, recogn_choice, model_choice, translate_choice,
                source_lang, target_lang, tts_choice, voice_role,
                voice_autorate, video_autorate,
                voice_rate, volume_rate, pitch_rate,
                subtitle_type, remove_noise, fix_punc,
                is_separate, embed_bgm, loop_bgm, backaudio_volume,
                cuda_accel,
            ],
            outputs=[log_output, video_preview, result_files, start_btn],
        )

    return app


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
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
    )
