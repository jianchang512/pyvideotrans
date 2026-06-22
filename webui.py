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
import time
import shutil
import asyncio
import tempfile
import traceback
from pathlib import Path
from typing import List, Tuple, Optional

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
LANGNAME_DICT_REV: dict = translator.LANGNAME_DICT_REV

# ---------------------------------------------------------------------------
# 可选渠道索引
# ---------------------------------------------------------------------------
# 语音识别：只可选 faster-whisper(0) 和 openai-whisper(1)
SELECTABLE_RECOGN = {0, 1}
DEFAULT_RECOGN = 0

# 翻译：只可选前 4 个 (Google, Microsoft, M2M100, ChatGPT)
SELECTABLE_TRANSLATE = {0, 1, 2, 3}
DEFAULT_TRANSLATE = 0

# 配音：Edge-TTS(0) + 标有"本地内置"的渠道
# 根据 TTS_NAME_LIST: 0=Edge, 1=Qwen3-TTS(Local), 3=MOSS(Local), 4=Piper(Local),
# 5=VITS(Local), 6=Supertonic(Local), 7=ChatterBox(Local)
SELECTABLE_TTS = {0, 1, 3, 4, 5, 6, 7}
DEFAULT_TTS = 0

# faster-whisper 模型列表
FASTER_MODEL_NAMES = list(FASTER_MODELS_DICT.keys())
DEFAULT_MODEL = "large-v3-turbo" if "large-v3-turbo" in FASTER_MODEL_NAMES else FASTER_MODEL_NAMES[0]

# 语言列表
LANG_OPTIONS = [f"{v} ({k})" for k, v in LANGNAME_DICT.items()]
DEFAULT_SOURCE_LANG = "en"
DEFAULT_TARGET_LANG = "zh-cn"

# 字幕类型选项
SUBTITLE_TYPES = {
    "不嵌入字幕": 0,
    "嵌入硬字幕": 1,
    "嵌入软字幕": 2,
    "嵌入硬字幕(双语)": 3,
    "嵌入软字幕(双语)": 4,
}
DEFAULT_SUBTITLE_TYPE = "嵌入硬字幕"


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _parse_lang_code(display: str) -> str:
    """从 'English (en)' 格式中提取语言代码 'en'"""
    if "(" in display and display.endswith(")"):
        return display.split("(")[-1].rstrip(")")
    return display


def _get_selectable_names(all_names: List[str], selectable: set) -> List[str]:
    """返回带标记的名称列表：可选的正常显示，不可选的加 [不可选] 前缀"""
    result = []
    for i, name in enumerate(all_names):
        if i in selectable:
            result.append(name)
        else:
            result.append(f"【不可选】{name}")
    return result


def _tts_type_from_display(display_name: str) -> int:
    """从显示名称反推 TTS 渠道索引"""
    clean = display_name.replace("【不可选】", "")
    for i, name in enumerate(TTS_NAMES):
        if name == clean:
            return i
    return 0


# ---------------------------------------------------------------------------
# UI 构建
# ---------------------------------------------------------------------------
def build_ui():
    import gradio as gr

    selectable_recogn = _get_selectable_names(RECOGN_NAMES, SELECTABLE_RECOGN)
    selectable_translate = _get_selectable_names(TRANSLATE_NAMES, SELECTABLE_TRANSLATE)
    selectable_tts = _get_selectable_names(TTS_NAMES, SELECTABLE_TTS)

    with gr.Blocks(title="pyVideoTrans WebUI") as app:
        gr.Markdown("# pyVideoTrans 视频翻译 WebUI")

        with gr.Row():
            # ---- 左列：输入与参数 ----
            with gr.Column(scale=3):
                input_file = gr.File(
                    label="选择视频/音频文件",
                    file_types=["video", "audio"],
                    type="filepath",
                )

                gr.Markdown("### 语音识别")
                recogn_choice = gr.Dropdown(
                    choices=selectable_recogn,
                    value=selectable_recogn[DEFAULT_RECOGN],
                    label="识别渠道",
                    interactive=True,
                )
                model_choice = gr.Dropdown(
                    choices=FASTER_MODEL_NAMES,
                    value=DEFAULT_MODEL,
                    label="模型 (faster-whisper / openai-whisper)",
                    interactive=True,
                )

                gr.Markdown("### 翻译")
                translate_choice = gr.Dropdown(
                    choices=selectable_translate,
                    value=selectable_translate[DEFAULT_TRANSLATE],
                    label="翻译渠道",
                    interactive=True,
                )
                source_lang = gr.Dropdown(
                    choices=LANG_OPTIONS,
                    value=f"{LANGNAME_DICT[DEFAULT_SOURCE_LANG]} ({DEFAULT_SOURCE_LANG})",
                    label="发音语言（源语言）",
                    interactive=True,
                )
                target_lang = gr.Dropdown(
                    choices=LANG_OPTIONS,
                    value=f"{LANGNAME_DICT[DEFAULT_TARGET_LANG]} ({DEFAULT_TARGET_LANG})",
                    label="目标语言",
                    interactive=True,
                )

                gr.Markdown("### 配音")
                tts_choice = gr.Dropdown(
                    choices=selectable_tts,
                    value=selectable_tts[0],
                    label="配音渠道",
                    interactive=True,
                )
                voice_role = gr.Dropdown(
                    choices=["No"],
                    value="No",
                    label="配音角色",
                    interactive=True,
                )

                gr.Markdown("### 对齐与字幕")
                with gr.Row():
                    voice_autorate = gr.Checkbox(label="配音加速（音频加速对齐）", value=True)
                    video_autorate = gr.Checkbox(label="视频慢速", value=False)
                subtitle_type = gr.Dropdown(
                    choices=list(SUBTITLE_TYPES.keys()),
                    value=DEFAULT_SUBTITLE_TYPE,
                    label="字幕嵌入类型",
                    interactive=True,
                )

                gr.Markdown("### 其他")
                cuda_accel = gr.Checkbox(label="启用 CUDA 加速", value=False)

                start_btn = gr.Button("🚀 开始执行", variant="primary", size="lg")

            # ---- 右列：日志与结果 ----
            with gr.Column(scale=2):
                log_output = gr.Textbox(
                    label="执行日志",
                    lines=20,
                    interactive=False,
                )
                result_files = gr.File(
                    label="输出文件（点击下载）",
                    interactive=False,
                )

        # ---- 动态更新配音角色 ----
        def update_voice_roles(tts_display: str, target_display: str):
            """当配音渠道或目标语言变化时，更新配音角色列表"""
            tts_idx = _tts_type_from_display(tts_display)
            lang_code = _parse_lang_code(target_display)
            try:
                roles = role_menu(tts_idx, langcode=lang_code)
                if not roles:
                    roles = ["No"]
            except Exception:
                roles = ["No"]
            return gr.update(choices=roles, value=roles[0] if roles else "No")

        tts_choice.change(
            fn=update_voice_roles,
            inputs=[tts_choice, target_lang],
            outputs=[voice_role],
        )
        target_lang.change(
            fn=update_voice_roles,
            inputs=[tts_choice, target_lang],
            outputs=[voice_role],
        )

        # ---- 执行翻译 ----
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
            subtitle_type_name,
            cuda_val,
        ):
            if not file_path:
                yield "❌ 请先选择一个视频或音频文件", []
                return

            # 解析参数
            recogn_idx = 0
            for i, name in enumerate(RECOGN_NAMES):
                if name in recogn_display:
                    recogn_idx = i
                    break

            translate_idx = 0
            for i, name in enumerate(TRANSLATE_NAMES):
                if name in translate_display:
                    translate_idx = i
                    break

            tts_idx = _tts_type_from_display(tts_display)
            source_code = _parse_lang_code(source_display)
            target_code = _parse_lang_code(target_display)
            subtitle_val = SUBTITLE_TYPES.get(subtitle_type_name, 1)

            log_lines = []
            def log(msg):
                log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
                return "\n".join(log_lines)

            yield log("初始化环境..."), []

            try:
                # 设置运行时状态
                app_cfg.exit_soft = False
                app_cfg.exec_mode = 'cli'
                getset_gpu()

                # 构建参数
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

                yield log(f"源文件: {Path(file_path).name}"), []

                vtv_params = {
                    "source_language_code": source_code,
                    "target_language_code": target_code,
                    # STT
                    "recogn_type": recogn_idx,
                    "model_name": model_name,
                    "is_cuda": cuda_val,
                    "remove_noise": False,
                    "enable_diariz": False,
                    "nums_diariz": -1,
                    "detect_language": source_code,
                    "rephrase": 0,
                    "fix_punc": False,
                    # TTS
                    "tts_type": tts_idx,
                    "voice_role": voice_role_name,
                    "voice_rate": "+0%",
                    "volume": "+0%",
                    "pitch": "+0Hz",
                    "voice_autorate": voice_autorate_val,
                    "video_autorate": video_autorate_val,
                    "align_sub_audio": True,
                    # Translation
                    "translate_type": translate_idx,
                    # VTV extra
                    "is_separate": False,
                    "recogn2pass": False,
                    "subtitle_type": subtitle_val,
                    "clear_cache": True,
                }

                params = {**common_params, **vtv_params}

                yield log(f"识别渠道: {RECOGN_NAMES[recogn_idx]}"), []
                yield log(f"翻译渠道: {TRANSLATE_NAMES[translate_idx]}"), []
                yield log(f"配音渠道: {TTS_NAMES[tts_idx]}"), []
                yield log(f"配音角色: {voice_role_name}"), []
                yield log(f"语言: {source_code} → {target_code}"), []
                yield log(f"字幕类型: {subtitle_type_name}"), []
                yield log(f"CUDA: {'启用' if cuda_val else '关闭'}"), []
                yield log(""), []

                # 执行 VTV 流水线
                yield log("▶ 开始执行视频翻译..."), []

                from videotrans.task.trans_create import TransCreate
                from videotrans.task.taskcfg import TaskCfgVTT

                trk = TransCreate(cfg=TaskCfgVTT(**params))

                yield log("阶段 1/8: 预处理（分离音视频）..."), []
                trk.prepare()
                yield log("✓ 预处理完成"), []

                yield log("阶段 2/8: 语音识别..."), []
                trk.recogn()
                yield log("✓ 语音识别完成"), []

                yield log("阶段 3/8: 说话人分离..."), []
                trk.diariz()
                yield log("✓ 说话人分离完成"), []

                yield log("阶段 4/8: 字幕翻译..."), []
                trk.trans()
                yield log("✓ 字幕翻译完成"), []

                yield log("阶段 5/8: 配音生成..."), []
                trk.dubbing()
                yield log("✓ 配音生成完成"), []

                yield log("阶段 6/8: 音画对齐..."), []
                trk.align()
                yield log("✓ 音画对齐完成"), []

                yield log("阶段 7/8: 二次识别..."), []
                trk.recogn2pass()
                yield log("✓ 二次识别完成"), []

                yield log("阶段 8/8: 最终合成..."), []
                trk.assembling()
                trk.task_done()
                yield log("✓ 视频合成完成"), []

                yield log(""), []
                yield log("✅ 全部任务执行完毕！"), []

                # 收集输出文件
                output_files = []
                target_path = Path(_target_dir)
                if target_path.exists():
                    for f in sorted(target_path.rglob("*")):
                        if f.is_file():
                            output_files.append(str(f))

                if not output_files:
                    # 尝试从缓存目录查找
                    cache_path = Path(_cache_folder)
                    if cache_path.exists():
                        for f in sorted(cache_path.rglob("*")):
                            if f.is_file() and f.suffix.lower() in ('.mp4', '.mkv', '.wav', '.srt', '.txt', '.mp3'):
                                output_files.append(str(f))

                yield log(f"输出目录: {_target_dir}"), output_files

            except Exception as e:
                tb = traceback.format_exc()
                yield log(f"❌ 执行出错: {str(e)}\n\n{tb}"), []

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
                subtitle_type,
                cuda_accel,
            ],
            outputs=[log_output, result_files],
        )

    return app


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import gradio as gr
    parser = argparse.ArgumentParser(description="pyVideoTrans WebUI")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address")
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
