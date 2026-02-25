import asyncio
import multiprocessing
import sys
import os
import re
import argparse
from multiprocessing import freeze_support
from pathlib import Path
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# 将这个工厂函数注册给 huggingface_hub
from videotrans.util.req_fac import custom_session_factory
import huggingface_hub
huggingface_hub.configure_http_backend(backend_factory=custom_session_factory)



# 调度函数 避免子进程重复执行
def main():
    TEXT_DB = {
        # --- 日志与标题 ---
        "exec_stt_task": {
            "zh": "[执行任务] 语音转录 (STT)",
            "en": "[Task] Speech Transcription (STT)"
        },
        "exec_tts_task": {
            "zh": "[执行任务] 语音合成 (TTS)",
            "en": "[Task] Text-to-Speech (TTS)"
        },
        "exec_sts_task": {
            "zh": "[执行任务] 字幕翻译 (STS)",
            "en": "[Task] Subtitle Translation (STS)"
        },
        "exec_vtv_task": {
            "zh": "[执行任务] 视频翻译 (VTV)",
            "en": "[Task] Video Translation (VTV)"
        },
        "process_file": {
            "zh": "[处理文件] {}",
            "en": "[File] {}"
        },
        "param_list": {
            "zh": "[参数列表] {}",
            "en": "[Params] {}"
        },

        # --- Argparse 描述 ---
        "cli_desc": {
            "zh": "pyVideoTrans视频翻译功能命令行模式",
            "en": "pyVideoTrans CLI Mode for Video Translation"
        },
        "help_task": {
            "zh": "任务类型: stt(语音转录), tts(文字配音), sts(字幕翻译), vtv(视频翻译)",
            "en": "Task type: stt(Speech to Text), tts(Text to Speech), sts(Subtitle Trans), vtv(Video Trans)"
        },
        "help_name": {
            "zh": "待处理文件的绝对路径,请使用英文双引号包含",
            "en": "Absolute path of the file to process, please wrap in double quotes"
        },

        # --- STT 参数 ---
        "group_stt": {
            "zh": "STT (语音转录) 参数",
            "en": "STT (Speech Transcription) Parameters"
        },
        "help_recogn_type": {
            "zh": "语音识别渠道",
            "en": "Speech recognition provider"
        },
        "help_detect_lang": {
            "zh": "音频视频发音语言",
            "en": "Source language of audio/video"
        },
        "help_model_name": {
            "zh": "语音识别模型名称\nfaster-whisper渠道(0)和openai-whisper渠道(1) 可选模型为 {} ,其他渠道请从软件界面中查看",
            "en": "ASR Model Name\nFor faster-whisper(0) and openai-whisper(1), available models: {}, others see GUI"
        },
        "help_cuda": {
            "zh": "是否使用CUDA加速",
            "en": "Enable CUDA acceleration"
        },
        "help_remove_noise": {
            "zh": "是否降噪",
            "en": "Enable noise reduction"
        },
        "help_enable_diariz": {
            "zh": "是否启用说话人识别",
            "en": "Enable Speaker Diarization"
        },
        "help_nums_diariz": {
            "zh": "指定说话人数量",
            "en": "Specify number of speakers"
        },
        "help_rephrase": {
            "zh": "是否重新断句 (0=无特殊, 1=LLM断句)",
            "en": "Rephrase segmentation (0=None, 1=LLM Split)"
        },
        "help_fix_punc": {
            "zh": "是否恢复标点符号",
            "en": "Restore punctuation"
        },

        # --- TTS 参数 ---
        "group_tts": {
            "zh": "TTS (文字配音) 参数",
            "en": "TTS (Text-to-Speech) Parameters"
        },
        "help_tts_type": {
            "zh": "配音渠道",
            "en": "TTS provider"
        },
        "help_voice_role": {
            "zh": "音色名 (TTS模式必选)，具体音色名称请在软件界面中选中对应配音渠道后查看",
            "en": "Voice Role (Required for TTS), check GUI for specific names under selected provider"
        },
        "help_voice_rate": {
            "zh": "语速",
            "en": "Speech rate"
        },
        "help_volume": {
            "zh": "音量",
            "en": "Volume"
        },
        "help_pitch": {
            "zh": "音调",
            "en": "Pitch"
        },
        "help_voice_autorate": {
            "zh": "是否自动加速音频以对齐字幕",
            "en": "Auto-speed audio to match subtitle duration"
        },
        "help_align_sub_audio": {
            "zh": "是否强制修改字幕以便对齐字幕",
            "en": "Force subtitle adjustment to align with audio"
        },

        # --- Translation 参数 ---
        "group_trans": {
            "zh": "Translation (翻译) 参数",
            "en": "Translation Parameters"
        },
        "help_translate_type": {
            "zh": "翻译渠道",
            "en": "Translation provider"
        },
        "help_source_lang": {
            "zh": "原始语言代码 (STS默认auto, VTV必选且不可为auto)",
            "en": "Source Language Code (STS defaults auto, VTV required & no auto)"
        },
        "help_target_lang": {
            "zh": "目标语言代码 (必选)",
            "en": "Target Language Code (Required)"
        },

        # --- VTV 参数 ---
        "group_vtv": {
            "zh": "VTV (视频翻译) 额外参数",
            "en": "VTV (Video Translation) Extra Parameters"
        },
        "help_video_autorate": {
            "zh": "是否自动慢速处理视频以对齐字幕",
            "en": "Auto-slow video to match subtitle duration"
        },
        "help_is_separate": {
            "zh": "是否分离人声背景声",
            "en": "Separate vocals and background music"
        },
        "help_recogn2pass": {
            "zh": "是否二次语音识别",
            "en": "Enable 2-pass speech recognition"
        },
        "help_subtitle_type": {
            "zh": "字幕嵌入类型 (0=无, 1=硬, 2=软,3=硬双，4=软双)",
            "en": "Subtitle embed type (0=No, 1=Hard, 2=Soft, 3=Hard Dual, 4=Soft Dual)"
        },
        "help_clear_cache": {
            "zh": "是否清理缓存 (默认True)",
            "en": "Clear cache after finish (Default: True)"
        },
        "help_no_clear_cache": {
            "zh": "不清理缓存",
            "en": "Do not clear cache"
        },

        # --- 错误提示 ---
        "err_missing_task": {
            "zh": "缺少--task参数，请根据任务类型选择\n视频翻译 --task vtv\n语音转录 --task stt\n文字合成 --task tts\n字幕翻译 --task sts",
            "en": "Missing --task parameter. Choose from:\nVideo Trans --task vtv\nSpeech Trans --task stt\nText Dubbing --task tts\nSub Trans --task sts"
        },
        "err_file_not_found": {
            "zh": "待处理的文件[ {} ]不存在\n请确保文件存在并输入完整的绝对路径，\n如果路径或名称中带有空格，请使用英文双引号包裹\n例如 \"D:/my videos/001.mp4\"  \"E:/how are you/my 001.srt\"",
            "en": "File [ {} ] not found.\nPlease ensure the file exists and use absolute path.\nWrap path in double quotes if it contains spaces.\nEx: \"D:/my videos/001.mp4\""
        },
        "err_tts_role_required": {
            "zh": "在 --task tts 文字配音模式下，--voice_role 音色是必选参数。",
            "en": "In --task tts mode, --voice_role is required."
        },
        "err_sts_target_required": {
            "zh": "在 --task sts 字幕翻译模式下，--target_language_code 目标语言是必选参数。",
            "en": "In --task sts mode, --target_language_code is required."
        },
        "err_vtv_missing": {
            "zh": "在 --task vtv 视频翻译模式下，以下参数必选: {}",
            "en": "In --task vtv mode, the following parameters are required: {}"
        },
        "miss_source_lang": {
            "zh": "--source_language_code 发音语言",
            "en": "--source_language_code"
        },
        "miss_target_lang": {
            "zh": "--target_language_code 目标语言",
            "en": "--target_language_code"
        }
    }
    from videotrans.configure import config
    config.init_run()

    from videotrans import recognition, translator, tts
    from videotrans.task._speech2text import SpeechToText
    from videotrans.task._translate_srt import TranslateSrt
    from videotrans.task.trans_create import TransCreate
    from videotrans.task._dubbing import DubbingSrt
    from videotrans.task.taskcfg import TaskCfgSTT, TaskCfgTTS, TaskCfgSTS, TaskCfgVTT
    from videotrans.util import tools
    from videotrans.util.gpus import getset_gpu

    def tr(key, *args)-> str:
        """翻译辅助函数"""
        lang_dict = TEXT_DB.get(key, {})
        text = lang_dict.get(config.defaulelang, key)  # 默认回退到key本身
        if args:
            return text.format(*args)
        return text


    # 语音转录 speech to text
    def stt_fun(params):
        print(f"\n{tr('exec_stt_task')}")
        print(tr('process_file', params.get('name')))
        print(tr('param_list', params))
        trk = SpeechToText(cfg=TaskCfgSTT(**params), out_format='srt')
        trk.prepare()
        trk.recogn()
        trk.diariz()
        trk.task_done()


    # 语音合成 text to speech
    def tts_fun(params):
        print(f"\n{tr('exec_tts_task')}")
        print(tr('process_file', params.get('name')))
        print(tr('param_list', params))
        trk = DubbingSrt(cfg=TaskCfgTTS(**params), out_ext='wav')
        trk.dubbing()
        trk.align()
        trk.task_done()


    # 字幕翻译 subtitles to subtitles
    def sts_fun(params):
        print(f"\n{tr('exec_sts_task')}")
        print(tr('process_file', params.get('name')))
        print(tr('param_list', params))
        trk = TranslateSrt(cfg=TaskCfgSTS(**params), out_format=0)
        trk.trans()
        trk.task_done()


    # 视频翻译  video to video
    def vtv_fun(params):
        config.current_status = 'ing'
        print(f"\n{tr('exec_vtv_task')}")
        print(tr('process_file', params.get('name')))
        print(tr('param_list', params))
        trk = TransCreate(cfg=TaskCfgVTT(**params))
        trk.prepare()
        trk.recogn()
        trk.trans()
        trk.dubbing()
        trk.align()
        trk.assembling()
        trk.task_done()

    # True 为软件退出，不执行任何动作
    config.exit_soft = False
    config.exec_mode = 'cli'
    recogn_help = ", ".join([f'{i}={it}' for i, it in enumerate(recognition.RECOGN_NAME_LIST)])
    trans_help = ", ".join([f'{i}={it}' for i, it in enumerate(translator.TRANSLASTE_NAME_LIST)])
    tts_help = ", ".join([f'{i}={it}' for i, it in enumerate(tts.TTS_NAME_LIST)])
    target_language_help = ', '.join(translator.LANGNAME_DICT.keys())
    model_help_list = 'tiny, small, base, medium, large-v3-turbo, large-v1, large-v2, large-v3'

    parser = argparse.ArgumentParser(
        description=tr("cli_desc"),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --- 核心参数 ---
    parser.add_argument('--task', type=str, required=True, choices=['stt', 'tts', 'sts', 'vtv'],
                        help=tr("help_task"))
    parser.add_argument('--name', type=str, required=True,
                        help=tr("help_name"))

    # --- STT 相关参数组 ---
    stt_group = parser.add_argument_group(tr("group_stt"))
    stt_group.add_argument('--recogn_type', type=int, default=0,
                           help=f"{tr('help_recogn_type')}\n{recogn_help}")
    stt_group.add_argument('--detect_language', type=str, default='auto',
                           help=tr("help_detect_lang"))
    stt_group.add_argument('--model_name', type=str, default='tiny',
                           help=tr("help_model_name", model_help_list))
    stt_group.add_argument('--cuda', action='store_true', help=tr("help_cuda"))
    stt_group.add_argument('--remove_noise', action='store_true', help=tr("help_remove_noise"))
    stt_group.add_argument('--enable_diariz', action='store_true', help=tr("help_enable_diariz"))
    stt_group.add_argument('--nums_diariz', type=int, default=-1, help=tr("help_nums_diariz"))
    stt_group.add_argument('--rephrase', type=int, default=0, help=tr("help_rephrase"))
    stt_group.add_argument('--fix_punc', action='store_true', help=tr("help_fix_punc"))

    # --- TTS 相关参数组 ---
    tts_group = parser.add_argument_group(tr("group_tts"))
    tts_group.add_argument('--tts_type', type=int, default=0,
                           help=f"{tr('help_tts_type')}\n{tts_help}")
    # 注意：voice_role 在 TTS 必选，VTV 可选，故在此设为 None，由逻辑层校验
    tts_group.add_argument('--voice_role', type=str, default=None,
                           help=tr("help_voice_role"))
    tts_group.add_argument('--voice_rate', type=str, default='+0%', help=tr("help_voice_rate"))
    tts_group.add_argument('--volume', type=str, default='+0%', help=tr("help_volume"))
    tts_group.add_argument('--pitch', type=str, default='+0Hz', help=tr("help_pitch"))
    tts_group.add_argument('--voice_autorate', action='store_true', help=tr("help_voice_autorate"))
    tts_group.add_argument('--align_sub_audio', action='store_true', help=tr("help_align_sub_audio"))

    # --- 翻译/语言 相关参数组 ---
    trans_group = parser.add_argument_group(tr("group_trans"))
    trans_group.add_argument('--translate_type', type=int, default=0,
                             help=f"{tr('help_translate_type')}\n{trans_help}")
    # 注意：source/target 在不同模式下要求不同，设为 None 由逻辑层校验
    trans_group.add_argument('--source_language_code', type=str, default=None,
                             help=f"{tr('help_source_lang')}\n{target_language_help}")
    trans_group.add_argument('--target_language_code', type=str, default=None,
                             help=f"{tr('help_target_lang')}\n{target_language_help}")

    # --- VTV 独有参数组 ---
    vtv_group = parser.add_argument_group(tr("group_vtv"))
    vtv_group.add_argument('--video_autorate', action='store_true', help=tr("help_video_autorate"))
    vtv_group.add_argument('--is_separate', action='store_true', help=tr("help_is_separate"))
    vtv_group.add_argument('--recogn2pass', action='store_true', help=tr("help_recogn2pass"))
    vtv_group.add_argument('--subtitle_type', type=int, default=1, help=tr("help_subtitle_type"))
    # clear_cache 默认为 True，为了方便命令行控制，增加 --no-clear-cache 选项
    vtv_group.add_argument('--clear_cache', action='store_true', default=True, help=tr("help_clear_cache"))
    vtv_group.add_argument('--no-clear-cache', dest='clear_cache', action='store_false', help=tr("help_no_clear_cache"))

    # 解析参数
    args = parser.parse_args()

    # ==========================================
    # 任务调度与参数校验构建
    # ==========================================

    task = args.task
    if not task:
        parser.error(tr("err_missing_task"))
        return

    if not Path(args.name).exists():
        parser.error(tr("err_file_not_found", args.name))
        return
    # 公共参数

    _file_obj = tools.format_video(args.name)
    _nospacebasename = re.sub(r'[\s\. #*?!:"]', '-', _file_obj["basename"])
    _cache_folder = f'{config.TEMP_DIR}/{_file_obj["uuid"]}'
    _target_dir = f'{config.ROOT_DIR}/output/{_nospacebasename}'
    common_params = {'name': args.name, "cache_folder": _cache_folder, "target_dir": _target_dir}
    common_params.update(_file_obj)
    Path(_cache_folder).mkdir(parents=True, exist_ok=True)
    Path(_target_dir).mkdir(parents=True, exist_ok=True)

    print('Checking GPUs...')
    getset_gpu()

    if task == 'stt':
        # 构建 STT 字典
        stt_params = {
            "recogn_type": args.recogn_type,
            "detect_language": args.detect_language,
            "model_name": args.model_name,
            "cuda": args.cuda,
            "remove_noise": args.remove_noise,
            "enable_diariz": args.enable_diariz,
            "nums_diariz": args.nums_diariz,
            "rephrase": args.rephrase,
            "fix_punc": args.fix_punc
        }
        # 合并公共参数并调用
        stt_fun({**common_params, **stt_params})

    elif task == 'tts':
        # 校验必选参数
        if not args.voice_role:
            parser.error(tr("err_tts_role_required"))
            return

        # 构建 TTS 字典
        tts_params = {
            "tts_type": args.tts_type,
            "voice_role": args.voice_role,
            "voice_rate": args.voice_rate,
            "volume": args.volume,
            "pitch": args.pitch,
            "voice_autorate": args.voice_autorate,
            "align_sub_audio": args.align_sub_audio,
            "target_language_code": args.target_language_code

        }
        tts_fun({**common_params, **tts_params})

    elif task == 'sts':
        # 校验必选参数
        if not args.target_language_code:
            parser.error(tr("err_sts_target_required"))

        # 处理默认值 (STS模式下 source 默认为 auto)
        source_lang = args.source_language_code if args.source_language_code else "auto"

        sts_params = {
            "translate_type": args.translate_type,
            "source_language_code": source_lang,
            "target_language_code": args.target_language_code
        }
        sts_fun({**common_params, **sts_params})

    elif task == 'vtv':
        # 校验必选参数
        missing = []
        if not args.source_language_code: missing.append(tr("miss_source_lang"))
        if not args.target_language_code: missing.append(tr("miss_target_lang"))

        if missing:
            parser.error(tr("err_vtv_missing", ', '.join(missing)))

        # 处理默认值 (VTV 模式下 voice_role 默认为 'No')
        voice_role = args.voice_role if args.voice_role else "No"

        vtv_params = {
            # 语言参数
            "source_language_code": args.source_language_code,
            "target_language_code": args.target_language_code,

            # STT 部分
            "recogn_type": args.recogn_type,
            "model_name": args.model_name,
            "cuda": args.cuda,
            "remove_noise": args.remove_noise,
            "enable_diariz": args.enable_diariz,
            "nums_diariz": args.nums_diariz,
            "rephrase": args.rephrase,
            "fix_punc": args.fix_punc,

            # TTS 部分
            "tts_type": args.tts_type,
            "voice_role": voice_role,  # 使用处理后的默认值
            "voice_rate": args.voice_rate,
            "volume": args.volume,
            "pitch": args.pitch,
            "voice_autorate": args.voice_autorate,
            "video_autorate": args.video_autorate,
            "align_sub_audio": args.align_sub_audio,

            # 翻译与通用部分
            "translate_type": args.translate_type,
            "is_separate": args.is_separate,
            "recogn2pass": args.recogn2pass,
            "subtitle_type": args.subtitle_type,
            "clear_cache": args.clear_cache
        }
        vtv_fun({**common_params, **vtv_params})


if __name__ == "__main__":
    # window
    freeze_support()
    try:
        multiprocessing.set_start_method('spawn',force=True)
    except RuntimeError:
        # 有时候环境已经设定好了，再次设定会报错，可以忽略
        pass
    main()
