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

from videotrans.configure.config import ROOT_DIR, TEMP_DIR, app_cfg, tr
from videotrans.configure.contants import FASTER_MODELS_DICT
from videotrans import recognition, translator, tts
from videotrans.util import tools
from videotrans.util.gpus import getset_gpu
from videotrans.util.help_role import role_menu

# ---------------------------------------------------------------------------
# 渠道名称列表（使用 tr() 获取中文名称）
# ---------------------------------------------------------------------------
RECOGN_NAMES: List[str] = recognition.RECOGN_NAME_LIST
TRANSLATE_NAMES: List[str] = translator.TRANSLASTE_NAME_LIST
TTS_NAMES: List[str] = tts.TTS_NAME_LIST
LANGNAME_DICT: dict = translator.LANGNAME_DICT

# ---------------------------------------------------------------------------
# 可选渠道索引（整数 ID）
# ---------------------------------------------------------------------------
SELECTABLE_RECOGN = {0, 1}
DEFAULT_RECOGN = 0

SELECTABLE_TRANSLATE = {0, 1, 2, 3}
DEFAULT_TRANSLATE = 0

SELECTABLE_TTS = {0, 1, 3, 4, 5, 6, 7}
DEFAULT_TTS = 0

# faster-whisper 模型列表
FASTER_MODEL_NAMES = list(FASTER_MODELS_DICT.keys())
DEFAULT_MODEL = "large-v3-turbo" if "large-v3-turbo" in FASTER_MODEL_NAMES else FASTER_MODEL_NAMES[0]

# 语言列表
LANG_DISPLAY_NAMES = list(LANGNAME_DICT.values())
DEFAULT_SOURCE_LANG = "英语"
DEFAULT_TARGET_LANG = "简体中文"

# 字幕类型选项
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
# 辅助函数
# ---------------------------------------------------------------------------
def _lang_code_from_display(display_name: str) -> str:
    """从中文语言名反推语言代码"""
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
    """将数值格式化为 '+N%' 或 '-N%'"""
    if value >= 0:
        return f"+{value}%"
    return f"{value}%"


def _format_pitch(value: int) -> str:
    """将数值格式化为 '+NHz' 或 '-NHz'"""
    if value >= 0:
        return f"+{value}Hz"
    return f"{value}Hz"


def open_ass_style_dialog():
    """打开 ASS 字幕样式编辑对话框（使用 PySide6）"""
    try:
        from PySide6.QtWidgets import QApplication
        from videotrans.component.set_ass import ASSStyleDialog

        # 确保有 QApplication 实例
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        dialog = ASSStyleDialog()
        dialog.exec()
        return "✅ 字幕样式已保存"
    except Exception as e:
        return f"❌ 打开字幕样式编辑器失败: {str(e)}"


# ---------------------------------------------------------------------------
# UI 构建
# ---------------------------------------------------------------------------
def build_ui():
    import gradio as gr

    with gr.Blocks(title="pyVideoTrans WebUI") as app:
        gr.Markdown("# pyVideoTrans 视频翻译 WebUI")

        # 状态变量
        prev_recogn = gr.State(value=RECOGN_NAMES[DEFAULT_RECOGN])
        prev_translate = gr.State(value=TRANSLATE_NAMES[DEFAULT_TRANSLATE])
        prev_tts = gr.State(value=TTS_NAMES[DEFAULT_TTS])

        with gr.Row():
            # ---- 左列：输入与参数 ----
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
                gr.Markdown("### 翻译")
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
                gr.Markdown("### 配音")
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
                    voice_rate = gr.Slider(
                        minimum=-50, maximum=50, value=0, step=1,
                        label="配音语速 (%)",
                    )
                    volume_rate = gr.Slider(
                        minimum=-95, maximum=100, value=0, step=1,
                        label="音量调整 (%)",
                    )
                    pitch_rate = gr.Slider(
                        minimum=-100, maximum=100, value=0, step=1,
                        label="音调 (Hz)",
                    )
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
                    fix_punc = gr.Dropdown(
                        choices=list(PUNC_OPTIONS.keys()),
                        value="默认标点",
                        label="标点处理",
                        interactive=True,
                    )

                with gr.Row():
                    is_separate = gr.Checkbox(label="分离人声背景声", value=False)
                    embed_bgm = gr.Checkbox(label="重新嵌入背景声", value=True)

                with gr.Row():
                    loop_bgm = gr.Dropdown(
                        choices=list(LOOP_BGM_OPTIONS.keys()),
                        value="背景音截断",
                        label="背景音处理方式",
                        interactive=True,
                    )
                    backaudio_volume = gr.Slider(
                        minimum=0.0, maximum=2.0, value=0.8, step=0.1,
                        label="背景音量",
                    )

                # === 其他 ===
                gr.Markdown("### 其他")
                with gr.Row():
                    cuda_accel = gr.Checkbox(label="启用 CUDA 加速", value=False)
                    ass_style_btn = gr.Button("🎨 修改硬字幕样式", size="sm")
                    ass_style_output = gr.Textbox(label="样式编辑器状态", interactive=False, visible=True)

                ass_style_btn.click(
                    fn=open_ass_style_dialog,
                    inputs=[],
                    outputs=[ass_style_output],
                )

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

        # ---- 渠道选择验证 ----
        def validate_recogn(choice, prev):
            idx = _recogn_index_from_display(choice)
            if idx not in SELECTABLE_RECOGN:
                return prev, f"⚠️ 渠道「{choice}」暂不可用，请选择 faster-whisper 或 openai-whisper"
            return choice, ""

        def validate_translate(choice, prev):
            idx = _translate_index_from_display(choice)
            if idx not in SELECTABLE_TRANSLATE:
                return prev, f"⚠️ 渠道「{choice}」暂不可用，请选择前4个渠道之一"
            return choice, ""

        def validate_tts(choice, prev):
            idx = _tts_index_from_display(choice)
            if idx not in SELECTABLE_TTS:
                return prev, f"⚠️ 渠道「{choice}」暂不可用，请选择 Edge-TTS 或本地内置渠道"
            return choice, ""

        recogn_choice.change(
            fn=validate_recogn,
            inputs=[recogn_choice, prev_recogn],
            outputs=[recogn_choice, log_output],
        )
        translate_choice.change(
            fn=validate_translate,
            inputs=[translate_choice, prev_translate],
            outputs=[translate_choice, log_output],
        )
        tts_choice.change(
            fn=validate_tts,
            inputs=[tts_choice, prev_tts],
            outputs=[tts_choice, log_output],
        )

        # ---- 动态更新配音角色 ----
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
            if not file_path:
                yield "❌ 请先选择一个视频或音频文件", []
                return

            # 解析参数
            recogn_idx = _recogn_index_from_display(recogn_display)
            translate_idx = _translate_index_from_display(translate_display)
            tts_idx = _tts_index_from_display(tts_display)
            source_code = _lang_code_from_display(source_display)
            target_code = _lang_code_from_display(target_display)
            subtitle_val = SUBTITLE_TYPES.get(subtitle_type_name, 1)
            fix_punc_val = PUNC_OPTIONS.get(fix_punc_name, 0)
            loop_bgm_val = LOOP_BGM_OPTIONS.get(loop_bgm_name, 0)

            log_lines = []
            def log(msg):
                log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
                return "\n".join(log_lines)

            yield log("初始化环境..."), []

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

                yield log(f"源文件: {Path(file_path).name}"), []

                vtv_params = {
                    "source_language_code": source_code,
                    "target_language_code": target_code,
                    # STT
                    "recogn_type": recogn_idx,
                    "model_name": model_name,
                    "is_cuda": cuda_val,
                    "remove_noise": remove_noise_val,
                    "enable_diariz": False,
                    "nums_diariz": -1,
                    "detect_language": source_code,
                    "rephrase": 0,
                    "fix_punc": fix_punc_val,
                    # TTS
                    "tts_type": tts_idx,
                    "voice_role": voice_role_name,
                    "voice_rate": _format_rate(int(voice_rate_val)),
                    "volume": _format_rate(int(volume_rate_val)),
                    "pitch": _format_pitch(int(pitch_rate_val)),
                    "voice_autorate": voice_autorate_val,
                    "video_autorate": video_autorate_val,
                    "align_sub_audio": True,
                    # Translation
                    "translate_type": translate_idx,
                    # VTV extra
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

                yield log(f"识别渠道: {RECOGN_NAMES[recogn_idx]} (ID={recogn_idx})"), []
                yield log(f"翻译渠道: {TRANSLATE_NAMES[translate_idx]} (ID={translate_idx})"), []
                yield log(f"配音渠道: {TTS_NAMES[tts_idx]} (ID={tts_idx})"), []
                yield log(f"配音角色: {voice_role_name}"), []
                yield log(f"语言: {source_code} → {target_code}"), []
                yield log(f"字幕类型: {subtitle_type_name} (ID={subtitle_val})"), []
                yield log(f"语速: {_format_rate(int(voice_rate_val))}  音量: {_format_rate(int(volume_rate_val))}  音调: {_format_pitch(int(pitch_rate_val))}"), []
                yield log(f"降噪: {'开' if remove_noise_val else '关'}  标点: {fix_punc_name}  分离人声: {'开' if is_separate_val else '关'}"), []
                yield log(f"嵌入背景: {'开' if embed_bgm_val else '关'}  背景处理: {loop_bgm_name}  背景音量: {backaudio_volume_val}"), []
                yield log(f"CUDA: {'启用' if cuda_val else '关闭'}"), []
                yield log(""), []

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
