import re
from multiprocessing import freeze_support
from pathlib import Path
from videotrans import recognition, translator, tts
from videotrans.task._speech2text import SpeechToText
from videotrans.task._translate_srt import TranslateSrt
from videotrans.task.trans_create import TransCreate
from videotrans.configure import config
from videotrans.task._dubbing import DubbingSrt
from videotrans.task.taskcfg import TaskCfg
from videotrans.util import gpus,tools
import argparse
import sys
import os
config.exit_soft=False

# ==========================================
# 1. 模拟业务处理函数 (根据需求只需实现调度，这里做打印演示)
# ==========================================


def stt_fun(params):
    print(f"\n[执行任务] 语音转录 (STT)")
    print(f"[处理文件] {params.get('name')}")
    print(f"[参数列表] {params}")
    trk = SpeechToText(cfg=TaskCfg(**params),out_format='srt')
    trk.prepare()
    trk.recogn()
    trk.diariz()
    trk.task_done()

def tts_fun(params):
    print(f"\n[执行任务] 语音合成 (TTS)")
    print(f"[处理文件] {params.get('name')}")
    print(f"[参数列表] {params}")
    trk = DubbingSrt(cfg=TaskCfg(**params),out_ext='wav')
    trk.dubbing()
    trk.align()
    trk.task_done()

def sts_fun(params):
    print(f"\n[执行任务] 字幕翻译 (STS)")
    print(f"[处理文件] {params.get('name')}")
    print(f"[参数列表] {params}")
    trk = TranslateSrt(cfg=TaskCfg(**params),out_format=0)
    trk.trans()
    trk.task_done()

def vtv_fun(params):
    config.current_status='ing'
    print(f"\n[执行任务] 视频翻译 (VTV)")
    print(f"[处理文件] {params.get('name')}")
    print(f"[参数列表] {params}")
    trk = TransCreate(cfg=TaskCfg(**params))
    trk.prepare()
    trk.recogn()
    trk.trans()
    trk.dubbing()
    trk.align()
    trk.assembling()
    trk.task_done()

# ==========================================
# 2. 参数解析与调度逻辑
# ==========================================



def main():
    config.exec_mode='cli'
    recogn_help=", ".join([f'{i}={it}' for i,it in enumerate(recognition.RECOGN_NAME_LIST)])
    trans_help=", ".join([f'{i}={it}' for i,it in enumerate(translator.TRANSLASTE_NAME_LIST)])
    tts_help=", ".join([f'{i}={it}' for i,it in enumerate(tts.TTS_NAME_LIST)])
    target_language_help=', '.join(translator.LANGNAME_DICT.keys())
    model_help='tiny, small, base, medium, large-v3-turbo, large-v1, large-v2, large-v3'
    parser = argparse.ArgumentParser(
        description="pyVideoTrans视频翻译功能命令行模式",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --- 核心参数 ---
    parser.add_argument('--task', type=str, required=True, choices=['stt', 'tts', 'sts', 'vtv'],
                        help="任务类型: stt(语音转录), tts(文字配音), sts(字幕翻译), vtv(视频翻译)")
    parser.add_argument('--name', type=str, required=True,
                        help="待处理文件的绝对路径,请使用英文双引号包含")

    # --- STT 相关参数组 ---
    stt_group = parser.add_argument_group('STT (语音转录) 参数')
    stt_group.add_argument('--recogn_type', type=int, default=0, help=f"语音识别渠道\n{recogn_help}")
    stt_group.add_argument('--detect_language', type=str, default='auto', help="音频视频发音语言")
    stt_group.add_argument('--model_name', type=str, default='tiny', help=f"语音识别模型名称\nfaster-whisper渠道(0)和openai-whisper渠道(1) 可选模型为 {model_help} ,其他渠道请从软件界面中查看")
    stt_group.add_argument('--cuda', action='store_true', help="是否使用CUDA加速")
    stt_group.add_argument('--remove_noise', action='store_true', help="是否降噪")
    stt_group.add_argument('--enable_diariz', action='store_true', help="是否启用说话人识别")
    stt_group.add_argument('--nums_diariz', type=int, default=-1, help="指定说话人数量")
    stt_group.add_argument('--rephrase', type=int, default=0, help="是否重新断句 (0=无特殊, 1=LLM断句)")
    stt_group.add_argument('--fix_punc', action='store_true', help="是否恢复标点符号")

    # --- TTS 相关参数组 ---
    tts_group = parser.add_argument_group('TTS (文字配音) 参数')
    tts_group.add_argument('--tts_type', type=int, default=0, help=f"配音渠道\n{tts_help}")
    # 注意：voice_role 在 TTS 必选，VTV 可选，故在此设为 None，由逻辑层校验
    tts_group.add_argument('--voice_role', type=str, default=None, help="音色名 (TTS模式必选)，具体音色名称请在软件界面中选中对应配音渠道后查看")
    tts_group.add_argument('--voice_rate', type=str, default='+0%', help="语速")
    tts_group.add_argument('--volume', type=str, default='+0%', help="音量")
    tts_group.add_argument('--pitch', type=str, default='+0Hz', help="音调")
    tts_group.add_argument('--voice_autorate', action='store_true', help="是否自动加速音频以对齐字幕")
    tts_group.add_argument('--align_sub_audio', action='store_true', help="是否强制修改字幕以便对齐字幕")

    # --- 翻译/语言 相关参数组 ---
    trans_group = parser.add_argument_group('Translation (翻译) 参数')
    trans_group.add_argument('--translate_type', type=int, default=0, help=f"翻译渠道\n{trans_help}")
    # 注意：source/target 在不同模式下要求不同，设为 None 由逻辑层校验
    trans_group.add_argument('--source_language_code', type=str, default=None, help=f"原始语言代码 (STS默认auto, VTV必选且不可为auto)\n{target_language_help}")
    trans_group.add_argument('--target_language_code', type=str, default=None, help=f"目标语言代码 (必选)\n{target_language_help}")

    # --- VTV 独有参数组 ---
    vtv_group = parser.add_argument_group('VTV (视频翻译) 额外参数')
    vtv_group.add_argument('--video_autorate', action='store_true', help="是否自动慢速处理视频以对齐字幕")
    vtv_group.add_argument('--is_separate', action='store_true', help="是否分离人声背景声")
    vtv_group.add_argument('--recogn2pass', action='store_true', help="是否二次语音识别")
    vtv_group.add_argument('--subtitle_type', type=int, default=1, help="字幕嵌入类型 (0=无, 1=硬, 2=软,3=硬双，4=软双)")
    # clear_cache 默认为 True，为了方便命令行控制，增加 --no-clear-cache 选项
    vtv_group.add_argument('--clear_cache', action='store_true', default=True, help="是否清理缓存 (默认True)")
    vtv_group.add_argument('--no-clear-cache', dest='clear_cache', action='store_false', help="不清理缓存")

    # 解析参数
    args = parser.parse_args()

    # ==========================================
    # 3. 任务调度与参数校验构建
    # ==========================================

    task = args.task
    if not task:
        parser.error(f"缺少--task参数，请根据任务类型选择"
                     f"视频翻译 --task vtv"
                     f"语音转录 --task stt"
                     f"文字合成 --task tts"
                     f"字幕翻译 --task sts"
                     )
        return

    if not Path(args.name).exists():
        parser.error(f'待处理的文件[ {args.name} ]不存在\n请确保文件存在并输入完整的绝对路径，\n如果路径或名称中带有空格，请使用英文双引号包裹\n例如 "D:/my videos/001.mp4"  "E:/how are you/my 001.srt"')
        return
    # 公共参数

    _file_obj=tools.format_video(args.name)
    _nospacebasename=re.sub(r'[\s\. #*?!:"]','-',_file_obj["basename"])
    _cache_folder=f'{config.TEMP_DIR}/{_file_obj["uuid"]}'
    _target_dir=f'{config.ROOT_DIR}/output/{_nospacebasename}'
    common_params = {'name': args.name,"cache_folder":_cache_folder,"target_dir":_target_dir}
    common_params.update(_file_obj)
    Path(_cache_folder).mkdir(parents=True,exist_ok=True)
    Path(_target_dir).mkdir(parents=True,exist_ok=True)

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
            parser.error(f"在 --task tts 文字配音模式下，--voice_role 音色是必选参数。")
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
            "target_language_code":args.target_language_code

        }
        tts_fun({**common_params, **tts_params})

    elif task == 'sts':
        # 校验必选参数
        if not args.target_language_code:
            parser.error(f"在 --task sts 字幕翻译模式下，--target_language_code 目标语言是必选参数。")

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
        if not args.source_language_code: missing.append('--source_language_code 发音语言')
        if not args.target_language_code: missing.append('--target_language_code 目标语言')

        if missing:
            parser.error(f"在 --task vtv 视频翻译模式下，以下参数必选: {', '.join(missing)}")

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
            "voice_role": voice_role, # 使用处理后的默认值
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
    freeze_support()
    main()

