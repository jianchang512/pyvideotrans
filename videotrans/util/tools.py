# -*- coding: utf-8 -*-
import copy
import datetime
import hashlib
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import timedelta
from pathlib import Path

import requests

from videotrans.configure import config


# 根据 gptsovits config.params['gptsovits_role'] 返回以参考音频为key的dict
def get_gptsovits_role():
    if not config.params['gptsovits_role'].strip():
        return None
    rolelist = {}
    for it in config.params['gptsovits_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 3:
            continue
        rolelist[tmp[0]] = {"refer_wav_path": tmp[0], "prompt_text": tmp[1], "prompt_language": tmp[2]}
    return rolelist

def get_chatterbox_role():
    rolelist = ['chatterbox','clone']
    if not config.params['chatterbox_role'].strip():
        return rolelist
    for it in config.params['chatterbox_role'].strip().split("\n"):
        rolelist.append(it.strip())
    return rolelist


def get_cosyvoice_role():
    rolelist = {
        "clone": 'clone'
    }
    if config.defaulelang == 'zh':
        rolelist['中文男'] = '中文男'
        rolelist['中文女'] = '中文女'
        rolelist['英文男'] = '英文男'
        rolelist['英文女'] = '英文女'
        rolelist['日语男'] = '日语男'
        rolelist['韩语女'] = '韩语女'
        rolelist['粤语女'] = '粤语女'
    else:
        rolelist['Chinese Male'] = '中文男'
        rolelist['Chinese Female'] = '中文女'
        rolelist['English Male'] = '英文男'
        rolelist['English Female'] = '英文女'
        rolelist['Japanese Male'] = '日语男'
        rolelist['Korean Female'] = '韩语女'
        rolelist['Cantonese Female'] = '粤语女'
    if not config.params['cosyvoice_role'].strip():
        return rolelist
    for it in config.params['cosyvoice_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"reference_audio": tmp[0], "reference_text": tmp[1]}
    return rolelist


def get_fishtts_role():
    if not config.params['fishtts_role'].strip():
        return None
    rolelist = {}
    for it in config.params['fishtts_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"reference_audio": tmp[0], "reference_text": tmp[1]}
    return rolelist


def get_f5tts_role():
    if not config.params['f5tts_role'].strip():
        return
    rolelist = {}
    for it in config.params['f5tts_role'].strip().split("\n"):
        tmp = it.strip().split('#')
        if len(tmp) != 2:
            continue
        rolelist[tmp[0]] = {"ref_audio": tmp[0], "ref_text": tmp[1]}
    return rolelist


def pygameaudio(filepath):
    from videotrans.util.playmp3 import AudioPlayer
    player = AudioPlayer(filepath)
    player.start()


# 获取 elenevlabs 的角色列表
def get_elevenlabs_role(force=False, raise_exception=False):
    jsonfile = os.path.join(config.ROOT_DIR, 'elevenlabs.json')
    namelist = ["clone"]
    if vail_file(jsonfile):
        with open(jsonfile, 'r', encoding='utf-8') as f:
            cache = json.loads(f.read())
            for it in cache.values():
                namelist.append(it['name'])
    if not force and len(namelist) > 0:
        config.params['elevenlabstts_role'] = namelist
        return namelist
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=config.params["elevenlabstts_key"])
        voiceslist = client.voices.get_all()
        result = {}
        for it in voiceslist.voices:
            n = re.sub(r'[^a-zA-Z0-9_ -]+', '', it.name).strip()
            result[n] = {"name": n, "voice_id": it.voice_id}
            namelist.append(n)
        with open(jsonfile, 'w', encoding="utf-8") as f:
            f.write(json.dumps(result))
        config.params['elevenlabstts_role'] = namelist
        return namelist
    except Exception as e:
        if raise_exception:
            raise
    return []


def set_proxy(set_val=''):
    if set_val == 'del':
        config.proxy = None
        # 删除代理
        if os.environ.get('http_proxy'):
            os.environ.pop('http_proxy')
        if os.environ.get('https_proxy'):
            os.environ.pop('https_proxy')
        return None
    if set_val:
        # 设置代理
        if not set_val.startswith("http") and not set_val.startswith('sock'):
            set_val = f"http://{set_val}"
        config.proxy = set_val
        os.environ['http_proxy'] = set_val
        os.environ['https_proxy'] = set_val
        os.environ['all_proxy'] = set_val
        return set_val

    # 获取代理
    http_proxy = config.proxy or os.environ.get('http_proxy') or os.environ.get('https_proxy')
    if http_proxy:
        if not http_proxy.startswith("http") and not http_proxy.startswith('sock'):
            http_proxy = f"http://{http_proxy}"
        return http_proxy
    if sys.platform != 'win32':
        return None
    try:
        import winreg
        # 打开 Windows 注册表
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            # 读取代理设置
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
            if proxy_server:
                # 是否需要设置代理
                if not proxy_server.startswith("http") and not proxy_server.startswith('sock'):
                    proxy_server = "http://" + proxy_server
                try:
                    requests.head(proxy_server, proxies={"http": "", "https": ""})
                except Exception:
                    return None
                return proxy_server
    except Exception as e:
        pass
    return None


def get_302ai(role_name=None):
    from videotrans import tts
    role_dict = get_azure_rolelist()
    role_dict['zh'].extend(list(tts.DOUBAO_302AI.keys()))
    return role_dict


# 字节火山语音合成角色
def get_volcenginetts_rolelist(role_name=None, langcode="zh"):
    zh = {
        "灿灿2.0": "BV700_V2_streaming",
        "炀炀": "BV705_streaming",
        "擎苍2.0": "BV701_V2_streaming",
        "通用女声 2.0": "BV001_V2_streaming",
        "灿灿": "BV700_streaming",
        "超自然音色-梓梓2.0": "BV406_V2_streaming",
        "超自然音色-梓梓": "BV406_streaming",
        "超自然音色-燃燃2.0": "BV407_V2_streaming",
        "超自然音色-燃燃": "BV407_streaming",
        "通用女声": "BV001_streaming",
        "通用男声": "BV002_streaming",
        "擎苍": "BV701_streaming",
        "阳光青年": "BV123_streaming",
        "通用赘婿": "BV119_streaming",
        "古风少御": "BV115_streaming",
        "霸气青叔": "BV107_streaming",
        "质朴青年": "BV100_streaming",
        "温柔淑女": "BV104_streaming",
        "开朗青年": "BV004_streaming",
        "甜宠少御": "BV113_streaming",
        "儒雅青年": "BV102_streaming",
        "甜美小源": "BV405_streaming",
        "亲切女声": "BV007_streaming",
        "知性女声": "BV009_streaming",
        "诚诚": "BV419_streaming",
        "童童": "BV415_streaming",
        "亲切男声": "BV008_streaming",
        "译制片男声": "BV408_streaming",
        "懒小羊": "BV426_streaming",
        "清新文艺女声": "BV428_streaming",
        "鸡汤女声": "BV403_streaming",
        "智慧老者": "BV158_streaming",
        "慈爱姥姥": "BV157_streaming",
        "说唱小哥": "BR001_streaming",
        "活力解说男": "BV410_streaming",
        "影视解说小帅": "BV411_streaming",
        "解说小帅多情感": "BV437_streaming",
        "影视解说小美": "BV412_streaming",
        "纨绔青年": "BV159_streaming",
        "直播一姐": "BV418_streaming",
        "反卷青年": "BV120_streaming",
        "沉稳解说男": "BV142_streaming",
        "潇洒青年": "BV143_streaming",
        "阳光男声": "BV056_streaming",
        "活泼女声": "BV005_streaming",
        "小萝莉": "BV064_streaming",
        "奶气萌娃": "BV051_streaming",
        "动漫海绵": "BV063_streaming",
        "动漫海星": "BV417_streaming",
        "动漫小新": "BV050_streaming",
        "天才童声": "BV061_streaming",
        "促销男声": "BV401_streaming",
        "促销女声": "BV402_streaming",
        "磁性男声": "BV006_streaming",
        "新闻女声": "BV011_streaming",
        "新闻男声": "BV012_streaming",
        "知性姐姐": "BV034_streaming",
        "温柔小哥": "BV033_streaming",

        "东北老铁": "BV021_streaming",
        "东北丫头": "BV020_streaming",
        "东北灿灿": "BV704_streaming",

        "西安佟掌柜": "BV210_streaming",

        "上海阿姐": "BV217_streaming",

        "广西表哥": "BV213_streaming",
        "广西灿灿": "BV704_streaming",

        "甜美台妹": "BV025_streaming",
        "台普男声": "BV227_streaming",
        "台湾灿灿": "BV704_streaming",

        "港剧男神": "BV026_streaming",
        "广东女仔": "BV424_streaming",
        "粤语灿灿": "BV704_streaming",

        "相声演员": "BV212_streaming",

        "重庆小伙": "BV019_streaming",
        "四川甜妹儿": "BV221_streaming",
        "重庆幺妹儿": "BV423_streaming",
        "成都灿灿": "BV704_streaming",

        "郑州乡村企业家": "BV214_streaming",
        "湖南妹坨": "BV226_streaming",
        "长沙靓女": "BV216_streaming"
    }
    en = {
        "慵懒女声-Ava": "BV511_streaming",
        "议论女声-Alicia": "BV505_streaming",
        "情感女声-Lawrence": "BV138_streaming",
        "美式女声-Amelia": "BV027_streaming",
        "讲述女声-Amanda": "BV502_streaming",
        "活力女声-Ariana": "BV503_streaming",
        "活力男声-Jackson": "BV504_streaming",
        "天才少女": "BV421_streaming",
        "Stefan": "BV702_streaming",
        "天真萌娃-Lily": "BV506_streaming",
        "亲切女声-Anna": "BV040_streaming",
        "澳洲男声-Henry": "BV516_streaming"
    }
    ja = {
        "元气少女": "BV520_streaming",
        "萌系少女": "BV521_streaming",
        "天才少女": "BV421_streaming",
        "气质女声": "BV522_streaming",
        "Stefan": "BV702_streaming",
        "灿灿": "BV700_streaming",
        "日语男声": "BV524_streaming",
    }
    pt = {
        "活力男声Carlos": "BV531_streaming",
        "活力女声": "BV530_streaming",
        "天才少女": "BV421_streaming",
        "Stefan": "BV702_streaming",
        "灿灿": "BV700_streaming",
    }
    es = {
        "气质御姐": "BV065_streaming",
        "天才少女": "BV421_streaming",
        "Stefan": "BV702_streaming",
        "灿灿": "BV700_streaming",
    }
    th = {
        "天才少女": "BV421_streaming"
    }
    vi = {
        "天才少女": "BV421_streaming"
    }
    id = {
        "天才少女": "BV421_streaming",
        "Stefan": "BV702_streaming",
        "灿灿": "BV700_streaming",
    }
    if role_name and langcode[:2] == 'zh':
        return zh.get(role_name, zh[list(zh.keys())[0]])
    if role_name and langcode[:2] == 'en':
        return en.get(role_name, en[list(en.keys())[0]])
    if role_name and langcode[:2] == 'ja':
        return ja.get(role_name, ja[list(ja.keys())[0]])
    if role_name and langcode[:2] == 'pt':
        return pt.get(role_name, pt[list(pt.keys())[0]])
    if role_name and langcode[:2] == 'es':
        return es.get(role_name, es[list(es.keys())[0]])
    if role_name and langcode[:2] == 'th':
        return th.get(role_name, th[list(th.keys())[0]])
    if role_name and langcode[:2] == 'vi':
        return vi.get(role_name, vi[list(vi.keys())[0]])
    if role_name and langcode[:2] == 'id':
        return id.get(role_name, id[list(id.keys())[0]])
    if role_name:
        raise

    return {
        "zh": list(zh.keys()),
        "ja": list(ja.keys()),
        "en": list(en.keys()),
        "pt": list(pt.keys()),
        "es": list(es.keys()),
        "th": list(th.keys()),
        "id": list(id.keys()),
        "vi": list(vi.keys())
    }


#  get role by edge tts
def get_edge_rolelist():
    voice_list = {}
    if vail_file(config.ROOT_DIR + "/voice_list.json"):
        try:
            voice_list = json.load(open(config.ROOT_DIR + "/voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                config.edgeTTS_rolelist = voice_list
                return voice_list
        except:
            pass
    try:
        import edge_tts
        import asyncio
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        else:
            asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        v = asyncio.run(edge_tts.list_voices())
        for it in v:
            name = it['ShortName']
            prefix = name.split('-')[0].lower()
            if prefix not in voice_list:
                voice_list[prefix] = ["No", name]
            else:
                voice_list[prefix].append(name)
        with open(config.ROOT_DIR + "/voice_list.json", "w", encoding='utf-8') as f:
            f.write(json.dumps(voice_list))
        config.edgeTTS_rolelist = voice_list
        return voice_list
    except Exception as e:
        config.logger.error('获取edgeTTS角色失败' + str(e))


def get_azure_rolelist():
    voice_list = {}
    if vail_file(config.ROOT_DIR + "/azure_voice_list.json"):
        try:
            voice_list = json.load(open(config.ROOT_DIR + "/azure_voice_list.json", "r", encoding="utf-8"))
            if len(voice_list) > 0:
                config.AzureTTS_rolelist = voice_list
                return voice_list
        except:
            pass
    return voice_list


def get_kokoro_rolelist():
    voice_list = {
        "en": [
            "No",
            "af_alloy",
            "af_aoede",
            "af_bella",
            "af_jessica",
            "af_kore",
            "af_nicole",
            "af_nova",
            "af_river",
            "af_sarah",
            "af_sky",
            "am_adam",
            "am_echo",
            "am_eric",
            "am_fenrir",
            "am_liam",
            "am_michael",
            "am_onyx",
            "am_puck",
            "am_santa",
            "bf_alice",
            "bf_emma",
            "bf_isabella",
            "bf_lily",
            "bm_daniel",
            "bm_fable",
            "bm_george",
            "bm_lewis"
        ],
        "zh": ["No","zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi", "zm_yunjian", "zm_yunxi", "zm_yunxia",
               "zm_yunyang"],
        "ja": ["No","jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"],
        "fr": ["No","ff_siwis"],
        "it": ["No","if_sara", "im_nicola"],
        "hi": ["No","hf_alpha", "hf_beta", "hm_omega", "hm_psi"],
        "es": ["No","ef_dora", "em_alex", "em_santa"],
        "pt": ["No","pf_dora", "pm_alex", "pm_santa"]
    }

    return voice_list




def extract_concise_error(stderr_text: str, max_lines=3, max_length=250) -> str:
    """
    Tries to extract a concise, relevant error message from stderr,
    often focusing on the last few lines or lines with error keywords.

    Args:
        stderr_text: The full stderr output string.
        max_lines: How many lines from the end to primarily consider.
        max_length: Max length of the returned string snippet.

    Returns:
        A concise string representing the likely error.
    """
    if not stderr_text:
        return "Unknown error (empty stderr)"

    lines = stderr_text.strip().splitlines()
    if not lines:
        return "Unknown error (empty stderr lines)"

    # Look for lines with common error keywords in the last few lines
    error_keywords = ["error", "invalid", "fail", "could not", "no such",
                      "denied", "unsupported", "unable", "can't open", "conversion failed"]

    relevant_lines_indices = range(max(0, len(lines) - max_lines), len(lines))

    found_error_lines = []
    for i in reversed(relevant_lines_indices):
        line = lines[i].strip()
        if not line: # Skip empty lines
             continue

        # Check if the line contains any of the keywords (case-insensitive)
        if any(keyword in line.lower() for keyword in error_keywords):
            # Prepend the previous line if it exists and isn't empty, might add context
            context_line = ""
            if i > 0 and lines[i-1].strip():
                 context_line = lines[i-1].strip() + "\n" # Add newline for clarity

            found_error_lines.append(context_line + line)
            # Often, the first keyword line found (reading backwards) is the most specific
            break

    if found_error_lines:
        # Take the first one found (which was likely the last 'errorry' line in the output)
        concise_error = found_error_lines[0]
    else:
        # Fallback: take the last non-empty line if no keywords found
        last_non_empty_line = ""
        for line in reversed(lines):
            stripped_line = line.strip()
            if stripped_line:
                last_non_empty_line = stripped_line
                break
        concise_error = last_non_empty_line or "Unknown error (no specific error line found)"

    # Limit the total length
    if len(concise_error) > max_length:
        return concise_error[:max_length] + "..."
    return concise_error


def _get_preset_classification(preset: str) -> str:
    """将 libx264/x265 的 preset 归类为 'fast', 'medium', 'slow'。"""
    SOFTWARE_PRESET_CLASSIFICATION = {
        'ultrafast': 'fast', 'superfast': 'fast', 'veryfast': 'fast',
        'faster': 'fast', 'fast': 'fast',
        'medium': 'medium',
        'slow': 'slow', 'slower': 'slow', 'veryslow': 'slow',
    }
    return SOFTWARE_PRESET_CLASSIFICATION.get(preset, 'medium') # 默认为 medium

def _translate_crf_to_hw_quality(crf_value: str, encoder_family: str) -> int | None:
    """
    将 CRF 值近似转换为不同硬件编码器的质量值。
    这是一个经验性转换，并非精确等效。
    """
    try:
        crf = int(crf_value)
        # 经验范围：CRF 越低，质量越高。
        # NVENC CQ/QP, QSV global_quality 范围 ~1-51，推荐 20-28，其值与CRF的体感接近。
        if encoder_family in ['nvenc', 'qsv', 'vaapi']:
            # 对于这些编码器，质量值与 CRF 值大致在同一数量级
            # 简单地将值限制在合理范围内
            return max(1, min(crf, 51))
        # 其他编码器（如 AMF）的质量参数不同，后续再说
        # videotoolbox 使用 -q:v 0-100，暂不转换
    except (ValueError, TypeError):
        return None
    return None


def _build_hw_command(args: list, hw_codec: str):
    """
    根据选择的硬件编码器，构建 ffmpeg 命令参数列表和硬件解码选项

    此函数是纯粹的，它不修改输入列表，而是返回一个新的列表。
    """
    if not hw_codec or 'libx' in hw_codec:
        return args, []

    encoder_family = hw_codec.split('_')[-1]

    # --- 参数映射表 ---
    PRESET_MAP = {
        'nvenc': {'fast': 'p1', 'medium': 'p4', 'slow': 'p7'}, # p1-p7: fastest to slowest
        'qsv': {'fast': 'veryfast', 'medium': 'medium', 'slow': 'veryslow'},
        'vaapi': {'fast': 'veryfast', 'medium': 'medium', 'slow': 'veryslow'},
        'amf': {'fast': 'speed', 'medium': 'balanced', 'slow': 'quality'},
    }
    
    # 定义硬件质量参数的名称
    QUALITY_PARAM_MAP = {
        'nvenc': '-cq',
        'qsv': '-global_quality',
        'vaapi': '-global_quality',
    }

    new_args = []
    hw_decode_opts = []
    
    i = 0
    main_input_file = ""
    while i < len(args):
        arg = args[i]

        if arg == '-i' and not main_input_file and i + 1 < len(args):
            main_input_file = args[i + 1]

        # 1. 替换视频编码器
        if arg == '-c:v' and i + 1 < len(args):
            if args[i + 1] != 'copy':
                new_args.extend(['-c:v', hw_codec])
            else:
                new_args.extend(['-c:v', 'copy'])
            i += 2
            continue

        # 2. 调整 preset 参数 (使用分类)
        if arg == '-preset' and i + 1 < len(args):
            family_presets = PRESET_MAP.get(encoder_family)
            if family_presets:
                classification = _get_preset_classification(args[i + 1])
                new_preset = family_presets.get(classification)
                if new_preset:
                    new_args.extend(['-preset', new_preset])
            i += 2
            continue
            
        # 3. 替换 -crf 参数
        if arg == '-crf' and i + 1 < len(args):
            hw_quality_param = QUALITY_PARAM_MAP.get(encoder_family)
            if hw_quality_param:
                crf_value = args[i+1]
                hw_quality_value = _translate_crf_to_hw_quality(crf_value, encoder_family)
                if hw_quality_value is not None:
                    # config.logger.info(f"将 -crf {crf_value} 替换为硬件参数 {hw_quality_param} {hw_quality_value}")
                    new_args.extend([hw_quality_param, str(hw_quality_value)])
                else:
                    config.logger.error(f"无法转换 -crf {crf_value} 的值，将忽略此质量参数。")
            else:
                 config.logger.error(f"编码器 {encoder_family} 不支持CRF到硬件质量参数的自动替换，将忽略 -crf。")
            i += 2
            continue

        new_args.append(arg)
        i += 1
    
    # --- 硬件解码逻辑 ---
    output_file = new_args[-1] if new_args else ""
    is_output_mp4 = isinstance(output_file, str) and output_file.lower().endswith('.mp4')
    is_input_media = isinstance(main_input_file, str) and main_input_file.lower().endswith(('.mp4', '.mkv', '.mov', '.ts', '.txt'))
    
    # 无字幕嵌入时可尝试硬件解码
    # 有字幕或 -vf 滤镜时不使用，容易出错且需要上传下载数据
    if  "-c:s" not in new_args and "-vf" not in new_args  and   is_input_media and is_output_mp4 and config.settings.get('cuda_decode', False):
        if encoder_family == 'nvenc':
            hw_decode_opts = ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
            # config.logger.info("启用 CUDA 硬件解码。")
        elif encoder_family == 'qsv':
            hw_decode_opts = ['-hwaccel', 'qsv', '-hwaccel_output_format', 'qsv']
            # config.logger.info("启用 QSV 硬件解码。")
        elif encoder_family == 'videotoolbox':
            hw_decode_opts = ['-hwaccel', 'videotoolbox']
            # config.logger.info("启用 VideoToolbox 硬件解码。")
    
    return new_args, hw_decode_opts



def runffmpeg(arg, *, noextname=None, uuid=None, force_cpu=False):
    """
    执行 ffmpeg 命令，智能应用硬件加速并处理平台兼容性。

    如果硬件加速失败，会自动回退到 CPU 编码重试。

    Args:
        arg (list): ffmpeg 参数列表。
        noextname (str, optional): 用于任务队列跟踪的标识符。
        uuid (str, optional): 用于进度更新的 UUID。
        force_cpu (bool): 如果为 True，则强制使用 CPU 编码，不尝试硬件加速。
    """
    arg_copy = copy.deepcopy(arg)
    
    default_codec = f"libx{config.settings.get('video_codec', '264')}"
    
    final_args = arg
    hw_decode_opts = []
    
    # 如果 crf < 10 则直接强制使用软编码
    if "-crf" in final_args and final_args[-1].endswith(".mp4"):
        crf_index=final_args.index("-crf")
        if int(final_args[crf_index+1])<=10:
            force_cpu=True
            if "-preset" in final_args:
                preset_index=final_args.index("-preset")
                final_args[preset_index+1]='ultrafast'
            else:
                final_args.insert(-1,"-preset")
                final_args.insert(-1,"ultrafast")
                
                

    if not force_cpu:
        if not hasattr(config, 'video_codec') or not config.video_codec:
            config.video_codec = get_video_codec() 
            
        if config.video_codec and 'libx' not in config.video_codec:
            # config.logger.info(f"检测到硬件编码器 {config.video_codec}，正在调整参数...")
            final_args, hw_decode_opts = _build_hw_command(arg, config.video_codec)
        else:
            config.logger.info("未找到或未选择硬件编码器，将使用软件编码。")
    
    
    cmd = [config.FFMPEG_BIN, "-hide_banner", "-ignore_unknown"]
    if "-y" not in final_args:
        cmd.append("-y")
    cmd.extend(hw_decode_opts)
    cmd.extend(final_args)

    if cmd and Path(cmd[-1]).suffix:
        try:
            cmd[-1] = Path(cmd[-1]).as_posix()
        except Exception:
            pass

    if config.settings.get('ffmpeg_cmd'):
        custom_params = [p for p in config.settings['ffmpeg_cmd'].split(' ') if p]
        cmd = cmd[:-1] + custom_params + cmd[-1:]

    if noextname:
        config.queue_novice[noextname] = 'ing'

    try:
        # config.logger.info(f"执行 FFmpeg 命令 (force_cpu={force_cpu}): {' '.join(cmd)}")
        
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
            
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors='replace',
            check=True,
            text=True,
            creationflags=creationflags
        )
        if noextname:
            config.queue_novice[noextname] = "end"
        return True

    except FileNotFoundError:
        config.logger.error(f"命令未找到: {cmd[0]}。请确保 ffmpeg 已安装并在系统 PATH 中。")
        if noextname: config.queue_novice[noextname] = "error"
        raise
        
    except subprocess.CalledProcessError as e:
        error_message = e.stderr or "(无 stderr 输出)"
        config.logger.error(f"FFmpeg 命令执行失败 (force_cpu={force_cpu})。\n命令: {' '.join(cmd)}\n错误: {error_message}")
        
        is_video_output = cmd[-1].lower().endswith('.mp4')
        if not force_cpu and is_video_output:
            config.logger.warning("硬件加速失败，将自动回退到 CPU 编码重试...")
            if uuid: set_process(text=config.transobj['huituicpu'], uuid=uuid)
            
            fallback_args = []
            i = 0
            while i < len(arg_copy):
                if arg_copy[i] == '-c:v' and i + 1 < len(arg_copy) and arg_copy[i+1] != 'copy':
                    fallback_args.extend(['-c:v', default_codec])
                    i += 2
                else:
                    fallback_args.append(arg_copy[i])
                    i += 1

            return runffmpeg(fallback_args, noextname=noextname, uuid=uuid, force_cpu=True)
        
        if noextname: config.queue_novice[noextname] = "error"
        raise Exception(extract_concise_error(e.stderr))

    except Exception as e:
        if noextname: config.queue_novice[noextname] = "error"
        config.logger.exception(f"执行 ffmpeg 时发生未知错误 (force_cpu={force_cpu})。")
        raise




def hide_show_element(wrap_layout, show_status):
    def hide_recursive(layout, show_status):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                if not show_status:
                    item.widget().hide()
                else:
                    item.widget().show()
            elif item.layout():
                hide_recursive(item.layout(), show_status)

    hide_recursive(wrap_layout, show_status)



class _FFprobeInternalError(Exception):
    """用于内部错误传递的自定义异常。"""
    pass

def _run_ffprobe_internal(cmd: list[str]) -> str:
    """
    (内部函数) 执行 ffprobe 命令并返回其标准输出。
    """
    # 确保文件路径参数已转换为 POSIX 风格字符串，以获得更好的兼容性
    if Path(cmd[-1]).is_file():
        cmd[-1] = Path(cmd[-1]).as_posix()

    command = [config.FFPROBE_BIN] + [str(arg) for arg in cmd]
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

    try:
        p = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors='replace',
            check=True,
            creationflags=creationflags
        )
        return p.stdout.strip()
    except FileNotFoundError as e:
        msg = f"Command not found: '{config.FFPROBE_BIN}'. Ensure FFmpeg is installed and in your PATH."
        config.logger.error(msg)
        raise _FFprobeInternalError(msg) from e
    except subprocess.CalledProcessError as e:
        concise_error = extract_concise_error(e.stderr)
        config.logger.error(f"ffprobe command failed: {concise_error}")
        raise _FFprobeInternalError(concise_error) from e
    except (PermissionError, OSError) as e:
        msg = f"OS error running ffprobe: {e}"
        config.logger.error(msg, exc_info=True)
        raise _FFprobeInternalError(msg) from e



def runffprobe(cmd):
    """
    (兼容性接口) 运行 ffprobe。
    """
    try:
        stdout_result = _run_ffprobe_internal(cmd)
        if stdout_result:
            return stdout_result
        
        # 如果 stdout 为空，但进程没有出错（不常见），则模拟旧的错误路径
        #  _run_ffprobe_internal 中，如果 stderr 有内容且返回码非0，
        # 会直接抛出异常，所以这段逻辑主要为了覆盖极端的边缘情况。
        config.logger.error("ffprobe ran successfully but produced no output.")
        raise Exception("ffprobe ran successfully but produced no output.")

    except _FFprobeInternalError as e:
        # 将内部异常转换为旧代码期望的通用 Exception
        raise
    except Exception as e:
        # 捕获其他意料之外的错误并重新引发，保持行为一致
        config.logger.error(f"An unexpected error occurred in runffprobe: {e}", exc_info=True)
        raise

def get_video_info(mp4_file, *, video_fps=False, video_scale=False, video_time=False, get_codec=False):
    """
    (兼容性接口) 获取视频信息。
    """
    if not Path(mp4_file).exists():
        raise Exception(f'{mp4_file} is not exists')
    try:
        out_json = runffprobe(
            ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mp4_file]
        )
        if not out_json:
            raise Exception('ffprobe error: dont get video information')
    except Exception as e:
        # 确保抛出的异常与旧版本一致
        raise Exception(f'ffprobe error: {e}. {mp4_file=}') from e

    # 解析 JSON 并填充结果字典
    try:
        out = json.loads(out_json)
    except json.JSONDecodeError as e:
        raise Exception('ffprobe error: failed to parse JSON output') from e
        
    result = {
        "video_fps": 30,
        "video_codec_name": "",
        "audio_codec_name": "",
        "width": 0,
        "height": 0,
        "time": 0,
        "streams_len": 0,
        "streams_audio": 0,
        "color": "yuv420p"
    }

    if "streams" not in out or not out["streams"]:
        raise Exception('ffprobe error: streams is 0')


    if "format" in out and out['format'].get('duration'):
        try:
            # 保持返回整数毫秒的逻辑
            result['time'] = int(float(out['format']['duration']) * 1000)
        except (ValueError, TypeError):
            config.logger.warning(f"Could not parse duration: {out['format'].get('duration')}")

    result['streams_len'] = len(out['streams'])
    
    video_stream = next((s for s in out['streams'] if s.get('codec_type') == 'video'), None)
    audio_streams = [s for s in out['streams'] if s.get('codec_type') == 'audio']
    
    result['streams_audio'] = len(audio_streams)
    if audio_streams:
        result['audio_codec_name'] = audio_streams[0].get('codec_name', "")

    if video_stream:
        result['video_codec_name'] = video_stream.get('codec_name', "")
        result['width'] = int(video_stream.get('width', 0))
        result['height'] = int(video_stream.get('height', 0))
        result['color'] = video_stream.get('pix_fmt', 'yuv420p').lower()

        # FPS 计算逻辑
        def parse_fps(rate_str):
            try:
                num, den = map(int, rate_str.split('/'))
                return num / den if den != 0 else 0
            except (ValueError, ZeroDivisionError, AttributeError):
                return 0

        fps1 = parse_fps(video_stream.get('r_frame_rate'))
        fps_avg = parse_fps(video_stream.get('avg_frame_rate'))
        
        # 优先使用 avg_frame_rate
        final_fps = fps_avg if fps_avg != 0 else fps1
        
        # 保持旧的帧率范围限制
        result['video_fps'] = final_fps if 1 <= final_fps <= 60 else 30

    # 确保向后兼容
    if video_time:
        return result['time']
    if video_fps:
        return result['video_fps']
    if video_scale:
        return result['width'], result['height']
    if get_codec:
        return result['video_codec_name'], result['audio_codec_name']
    
    return result

# 获取某个视频的时长 ms
def get_video_duration(file_path):
    return get_video_info(file_path, video_time=True)



# 获取某个视频的fps
def get_video_fps(file_path):
    return get_video_info(file_path, video_fps=True)


# 获取宽高分辨率
def get_video_resolution(file_path):
    return get_video_info(file_path, video_scale=True)


# 获取视频编码和
def get_codec_name(file_path):
    return get_video_info(file_path, video_scale=True)


# 从原始视频分离出 无声视频 cuda + h264_cuvid
def split_novoice_byraw(source_mp4, novoice_mp4, noextname, lib="copy"):
    cmd = [
        "-y",
        "-i",
        Path(source_mp4).as_posix(),
        "-an",
        "-c:v",
        lib
    ]
    if lib != 'copy':
        cmd += ["-crf", f'{config.settings["crf"]}']
    cmd += [f'{novoice_mp4}']
    return runffmpeg(cmd, noextname=noextname)


# 从原始视频中分离出音频 cuda + h264_cuvid
def split_audio_byraw(source_mp4, targe_audio, is_separate=False, uuid=None):
    source_mp4 = Path(source_mp4).as_posix()
    targe_audio = Path(targe_audio).as_posix()
    cmd = [
        "-y",
        "-i",
        source_mp4,
        "-vn",
        "-ac",
        "1",
        "-b:a",
        "128k",
        "-c:a",
        "aac",
        targe_audio
    ]
    rs = runffmpeg(cmd)
    if not is_separate:
        return rs
    # 继续人声分离
    tmpdir = config.TEMP_DIR + f"/{time.time()}"
    os.makedirs(tmpdir, exist_ok=True)
    tmpfile = tmpdir + "/raw.wav"
    runffmpeg([
        "-y",
        "-i",
        source_mp4,
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-c:a",
        "pcm_s16le",
        tmpfile
    ])
    from videotrans.separate import st
    try:
        path = Path(targe_audio).parent.as_posix()
        vocal_file = path + '/vocal.wav'
        if not vail_file(vocal_file):
            set_process(text=config.transobj['Separating vocals and background music, which may take a longer time'],
                        uuid=uuid)
            try:
                st.start(audio=tmpfile, path=path, uuid=uuid)
            except Exception as e:
                msg = f"separate vocal and background music:{str(e)}"
                set_process(text=msg, uuid=uuid)
                raise Exception(msg)
        if not vail_file(vocal_file):
            return False
    except Exception as e:
        msg = f"separate vocal and background music:{str(e)}"
        set_process(text=msg, uuid=uuid)
        raise


# 将字符串做 md5 hash处理
def get_md5(input_string: str):
    md5 = hashlib.md5()
    md5.update(input_string.encode('utf-8'))
    return md5.hexdigest()


def conver_to_16k(audio, target_audio):
    return runffmpeg([
        "-y",
        "-i",
        Path(audio).as_posix(),
        "-ac",
        "1",
        "-ar",
        "16000",
        Path(target_audio).as_posix(),
    ])


#  背景音乐是wav,配音人声是m4a，都在目标文件夹下，合并后最后文件仍为 人声文件，时长需要等于人声
def backandvocal(backwav, peiyinm4a):
    import tempfile
    backwav = Path(backwav).as_posix()
    peiyinm4a = Path(peiyinm4a).as_posix()
    tmpdir = tempfile.gettempdir()
    tmpwav = Path(tmpdir + f'/{time.time()}-1.m4a').as_posix()
    tmpm4a = Path(tmpdir + f'/{time.time()}.m4a').as_posix()
    # 背景转为m4a文件,音量降低为0.8
    wav2m4a(backwav, tmpm4a, ["-filter:a", f"volume={config.settings['backaudio_volume']}"])
    runffmpeg(['-y', '-i', peiyinm4a, '-i', tmpm4a, '-filter_complex',
               "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', "-b:a", "128k", '-c:a', 'aac',
               tmpwav])
    shutil.copy2(tmpwav, peiyinm4a)
    # 转为 m4a


# wav转为 m4a cuda + h264_cuvid
def wav2m4a(wavfile, m4afile, extra=None):
    cmd = [
        "-y",
        "-i",
        Path(wavfile).as_posix(),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        Path(m4afile).as_posix()
    ]
    if extra:
        cmd = cmd[:3] + extra + cmd[3:]
    return runffmpeg(cmd)


# wav转为 mp3 cuda + h264_cuvid
def wav2mp3(wavfile, mp3file, extra=None):
    if not wavfile or not Path(wavfile).exists():
        raise Exception(f'No Exists: {wavfile}')
    cmd = [
        "-y",
        "-i",
        Path(wavfile).as_posix(),
        "-b:a",
        "128k",
        Path(mp3file).as_posix()
    ]
    if extra:
        cmd = cmd[:3] + extra + cmd[3:]
    return runffmpeg(cmd)


# m4a 转为 wav cuda + h264_cuvid
def m4a2wav(m4afile, wavfile):
    cmd = [
        "-y",
        "-i",
        Path(m4afile).as_posix(),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "128k",
        "-c:a",
        "pcm_s16le",
        Path(wavfile).as_posix()
    ]
    return runffmpeg(cmd)


# 创建 多个连接文件
def create_concat_txt(filelist, concat_txt=None):
    txt = []
    for it in filelist:
        if not Path(it).exists() or Path(it).stat().st_size == 0:
            continue
        txt.append(f"file '{os.path.basename(it)}'")
    if len(txt) < 1:
        raise Exception(f'file list no vail')
    with Path(concat_txt).open('w', encoding='utf-8') as f:
        f.write("\n".join(txt))
        f.flush()
    return concat_txt


# 多个视频片段连接 cuda + h264_cuvid
def concat_multi_mp4(*, out=None, concat_txt=None):
    video_codec = config.settings['video_codec']
    if out:
        out = Path(out).as_posix()
    os.chdir(os.path.dirname(concat_txt))
    runffmpeg(
        ['-y', '-f', 'concat', '-i', concat_txt, '-c:v', f"libx{video_codec}", '-an', '-crf',
         f'{config.settings["crf"]}', '-preset', config.settings['preset'], out])
    os.chdir(config.ROOT_DIR)
    return True


# 多个音频片段连接 
def concat_multi_audio(*, out=None, concat_txt=None):
    if out:
        out = Path(out).as_posix()

    os.chdir(os.path.dirname(concat_txt))
    cmd = ['-y', '-f', 'concat', '-i', concat_txt, "-b:a", "128k"]
    if out.endswith('.m4a'):
        cmd += ['-c:a', 'aac']
    elif out.endswith('.wav'):
        cmd += ['-c:a', 'pcm_s16le']
    runffmpeg(cmd + [out])
    os.chdir(config.TEMP_DIR)
    return True

def precise_speed_up_audio(*, file_path=None, out=None, target_duration_ms=None, max_rate=100):
    from pydub import AudioSegment
    ext=file_path[-3:]
    audio = AudioSegment.from_file(file_path,format='mp4' if ext=='m4a' else ext)

    # 首先确保原时长和目标时长单位一致（毫秒）
    current_duration_ms = len(audio)
    if target_duration_ms <= 0 or current_duration_ms<=0 or current_duration_ms>=target_duration_ms:
        return True
    temp_file = config.SYS_TMP+f'/{time.time_ns()}.{ext}'
    atempo=target_duration_ms/current_duration_ms
    runffmpeg(["-i",file_path, "-filter:a",f"atempo={atempo}",temp_file])
    audio=AudioSegment.from_file(temp_file,format='mp4' if ext=='m4a' else ext)
    diff = len(audio)-target_duration_ms
    if diff > 0:
        audio = audio[:-diff]
    if out:
        audio.export(out, format=ext)
        return True
    audio.export(file_path,format=ext)
    return True


def show_popup(title, text, parent=None):
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox

    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
    msg.setText(text)
    msg.addButton(QMessageBox.Yes)
    msg.addButton(QMessageBox.Cancel)
    msg.setWindowModality(Qt.ApplicationModal)  # 设置为应用模态
    msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)  # 置于顶层
    msg.setIcon(QMessageBox.Information)
    x = msg.exec()  # 显示消息框
    return x


'''
格式化毫秒或秒为符合srt格式的 2位小时:2位分:2位秒,3位毫秒 形式
print(ms_to_time_string(ms=12030))
-> 00:00:12,030
'''


def ms_to_time_string(*, ms=0, seconds=None,sepflag=','):
    # 计算小时、分钟、秒和毫秒
    if seconds is None:
        td = timedelta(milliseconds=ms)
    else:
        td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000

    time_string = f"{hours}:{minutes}:{seconds},{milliseconds}"
    return format_time(time_string, f'{sepflag}')


# 将不规范的 时:分:秒,|.毫秒格式为  aa:bb:cc,ddd形式
# eg  001:01:2,4500  01:54,14 等做处理
def format_time(s_time="", separate=','):
    if not s_time.strip():
        return f'00:00:00{separate}000'
    hou, min, sec, ms = 0, 0, 0, 0

    tmp = s_time.strip().split(':')
    if len(tmp) >= 3:
        hou, min, sec = tmp[-3].strip(), tmp[-2].strip(), tmp[-1].strip()
    elif len(tmp) == 2:
        min, sec = tmp[0].strip(), tmp[1].strip()
    elif len(tmp) == 1:
        sec = tmp[0].strip()

    if re.search(r',|\.', str(sec)):
        t = re.split(r',|\.', str(sec))
        sec = t[0].strip()
        ms = t[1].strip()
    else:
        ms = 0
    hou = f'{int(hou):02}'[-2:]
    min = f'{int(min):02}'[-2:]
    sec = f'{int(sec):02}'
    ms = f'{int(ms):03}'[-3:]
    return f"{hou}:{min}:{sec}{separate}{ms}"


# 将 datetime.timedelta 对象的秒和微妙转为毫秒整数值
def toms(td):
    return (td.seconds * 1000) + int(td.microseconds / 1000)


# 将 时:分:秒,毫秒 转为毫秒整数值
def get_ms_from_hmsm(time_str):
    time_str=time_str.replace('.',',')
    h, m, sec2ms = 0, 0, '00,000'
    tmp0 = time_str.split(":")
    if len(tmp0) == 3:
        h, m, sec2ms = tmp0[0], tmp0[1], tmp0[2]
    elif len(tmp0) == 2:
        m, sec2ms = tmp0[0], tmp0[1]

    tmp = sec2ms.split(',')
    ms = tmp[1] if len(tmp) == 2 else 0
    sec = tmp[0]

    return int(int(h) * 3600000 + int(m) * 60000 + int(sec) * 1000 + int(ms))


def srt_str_to_listdict(srt_string):
    """解析 SRT 字幕字符串，更精确地处理数字行和时间行之间的关系"""
    srt_list = []
    time_pattern = r'\s?(\d+):(\d+):(\d+)([,.]\d+)?\s*?-{1,2}>\s*?(\d+):(\d+):(\d+)([,.]\d+)?\n?'
    lines = srt_string.splitlines()
    i = 0

    while i < len(lines):
        time_match = re.match(time_pattern, lines[i].strip())
        if time_match:
            # 解析时间戳
            start_time_groups = time_match.groups()[0:4]
            end_time_groups = time_match.groups()[4:8]

            def parse_time(time_groups):
                h, m, s, ms = time_groups
                ms = ms.replace(',', '').replace('.', '') if ms else "0"
                try:
                    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
                except (ValueError, TypeError):
                    return None

            start_time = parse_time(start_time_groups)
            end_time = parse_time(end_time_groups)

            if start_time is None or end_time is None:
                i += 1
                continue

            i += 1
            text_lines = []
            while i < len(lines):
                current_line = lines[i].strip()
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""  # 获取下一行，如果没有则为空字符串

                if re.match(time_pattern, next_line):  # 判断下一行是否为时间行
                    if re.fullmatch(r'\d+', current_line):  # 如果当前行为纯数字，则跳过
                        i += 1
                        break
                    else:
                        if current_line:
                            text_lines.append(current_line)
                        i += 1
                        break

                if current_line:
                    text_lines.append(current_line)
                    i += 1
                else:
                    i += 1

            text = ('\n'.join(text_lines)).strip()
            text = re.sub(r'</?[a-zA-Z]+>', '', text.replace("\r", '').strip())
            text = re.sub(r'\n{2,}', '\n', text).strip()
            if text and text[0] in ['-']:
                text=text[1:]
            if text and len(text)>0 and text[-1] in ['-',']']:
                text=text[:-1]
            it = {
                "line": len(srt_list) + 1,  # 字幕索引，转换为整数
                "start_time": int(start_time),
                "end_time": int(end_time),  # 起始和结束时间
                "text": text if text else "",  # 字幕文本
            }
            it['startraw'] = ms_to_time_string(ms=it['start_time'])
            it['endraw'] = ms_to_time_string(ms=it['end_time'])
            it["time"] = f"{it['startraw']} --> {it['endraw']}"
            srt_list.append(it)


        else:
            i += 1  # 跳过非时间行

    return srt_list


# 将字符串或者字幕文件内容，格式化为有效字幕数组对象
# 格式化为有效的srt格式
def format_srt(content):
    result = []
    try:
        result = srt_str_to_listdict(content)
    except Exception as e:
        config.logger.error(e)
        result = srt_str_to_listdict(process_text_to_srt_str(content))
    return result


# 将srt文件或合法srt字符串转为字典对象
def get_subtitle_from_srt(srtfile, *, is_file=True):
    def _readfile(file):
        content = ""
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        except Exception as e:
            try:
                with open(file, 'r', encoding='gbk') as f:
                    content = f.read().strip()
            except Exception as e:
                config.logger.exception(e, exc_info=True)
        return content

    content = ''
    if is_file:
        content = _readfile(srtfile)
    else:
        content = srtfile.strip()

    if len(content) < 1:
        raise Exception(f"srt is empty:{srtfile=},{content=}")
    result = format_srt(copy.copy(content))


    # txt 文件转为一条字幕
    if len(result) < 1:
        result = [
            {"line": 1, "time": "00:00:00,000 --> 00:00:02,000", "text": "\n".join(content)}
        ]
    return result


# 将字幕字典列表写入srt文件
def save_srt(srt_list, srt_file):
    txt = get_srt_from_list(srt_list)
    with open(srt_file, "w", encoding="utf-8") as f:
        f.write(txt)
    return True


def get_current_time_as_yymmddhhmmss(format='hms'):
    """将当前时间转换为 YYMMDDHHmmss 格式的字符串。"""
    now = datetime.datetime.now()
    return now.strftime("%y%m%d%H%M%S" if format != 'hms' else "%H%M%S")


# 从 字幕 对象中获取 srt 字幕串
def get_srt_from_list(srt_list):
    txt = ""
    line = 0
    # it中可能含有完整时间戳 it['time']   00:00:01,123 --> 00:00:12,345
    # 开始和结束时间戳  it['startraw']=00:00:01,123  it['endraw']=00:00:12,345
    # 开始和结束毫秒数值  it['start_time']=126 it['end_time']=678
    for it in srt_list:
        line += 1
        if "startraw" not in it:
            # 存在完整开始和结束时间戳字符串 时:分:秒,毫秒 --> 时:分:秒,毫秒
            if 'time' in it:
                startraw, endraw = it['time'].strip().split(" --> ")
                startraw = format_time(startraw.strip().replace('.', ','), ',')
                endraw = format_time(endraw.strip().replace('.', ','), ',')
            elif 'start_time' in it and 'end_time' in it:
                # 存在开始结束毫秒数值
                startraw = ms_to_time_string(ms=it['start_time'])
                endraw = ms_to_time_string(ms=it['end_time'])
            else:
                raise Exception(
                    f'字幕中不存在 time/startraw/start_time 任何有效时间戳形式' if config.defaulelang == 'zh' else 'There is no time/startraw/start_time in the subtitle in any valid timestamp form.')
        else:
            # 存在单独开始和结束  时:分:秒,毫秒 字符串
            startraw = it['startraw']
            endraw = it['endraw']

        
        txt += f"{line}\n{startraw} --> {endraw}\n{it['text']}\n\n"
    return txt


# 将srt字幕转为 ass字幕
def srt2ass(srt_file, ass_file, maxlen=40):
    srt_list = get_subtitle_from_srt(srt_file)
    text = ""
    for i, it in enumerate(srt_list):
        it['text'] = textwrap.fill(it['text'], maxlen, replace_whitespace=False).strip()
        text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}\n\n"
    tmp_srt = config.TEMP_DIR + f"/{time.time()}.srt"
    with open(tmp_srt, 'w', encoding='utf-8', errors='ignore') as f:
        f.write(text)

    runffmpeg(['-y', '-i', tmp_srt, ass_file])
    with open(ass_file, 'r', encoding='utf-8') as f:
        ass_str = f.readlines()

    for i, it in enumerate(ass_str):
        if it.find('Style: ') == 0:
            ass_str[i] = 'Style: Default,{fontname},{fontsize},{fontcolor},&HFFFFFF,{fontbordercolor},{fontbackcolor},0,0,0,0,100,100,0,0,1,1,0,{subtitle_position},10,10,{marginV},1'.format(
                fontname=config.settings['fontname'], fontsize=config.settings['fontsize'],
                fontcolor=config.settings['fontcolor'],
                fontbordercolor=config.settings['fontbordercolor'],
                fontbackcolor=config.settings['fontbordercolor'],
                subtitle_position=int(config.settings.get('subtitle_position',2)),
                marginV=int(config.settings.get('marginV',10))
                )
            break

    with open(ass_file, 'w', encoding='utf-8') as f:
        f.write("".join(ass_str))

    
    
# 判断 novoice.mp4是否创建好
def is_novoice_mp4(novoice_mp4, noextname, uuid=None):
    # 预先创建好的
    # 判断novoice_mp4是否完成
    t = 0
    if noextname not in config.queue_novice and vail_file(novoice_mp4):
        return True
    if noextname in config.queue_novice and config.queue_novice[noextname] == 'end':
        return True
    last_size = 0
    while True:
        if config.current_status != 'ing' or config.exit_soft:
            return False
        if vail_file(novoice_mp4):
            current_size = os.path.getsize(novoice_mp4)
            if last_size > 0 and current_size == last_size and t > 1200:
                return True
            last_size = current_size

        if noextname not in config.queue_novice:
            msg = f"{noextname} split no voice videoerror:{config.queue_novice=}"
            raise Exception(msg)
        if config.queue_novice[noextname] == 'error':
            msg = f"{noextname} split no voice videoerror"
            raise Exception(msg)

        if config.queue_novice[noextname] == 'ing':
            size = f'{round(last_size / 1024 / 1024, 2)}MB' if last_size > 0 else ""
            set_process(
                text=f"{noextname} {'分离音频和画面' if config.defaulelang == 'zh' else 'spilt audio and video'} {size}",
                uuid=uuid)
            time.sleep(3)
            t += 3
            continue
        return True


def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


# 从音频中截取一个片段
def cut_from_audio(*, ss, to, audio_file, out_file):
    cmd = [
        "-y",
        "-i",
        audio_file,
        "-ss",
        format_time(ss, '.'),
        "-to",
        format_time(to, '.'),
        "-ar",
        "16000",
        out_file
    ]
    return runffmpeg(cmd)


# 获取clone-voice的角色列表
def get_clone_role(set_p=False):
    if not config.params['clone_api']:
        if set_p:
            raise Exception(config.transobj['bixutianxiecloneapi'])
        return False
    try:
        url = config.params['clone_api'].strip().rstrip('/') + "/init"
        res = requests.get('http://' + url.replace('http://', ''), proxies={"http": "", "https": ""})
        if res.status_code == 200:
            config.params["clone_voicelist"] = ["clone"] + res.json()
            set_process(type='set_clone_role')
            return True
        raise Exception(
            f"code={res.status_code},{config.transobj['You must deploy and start the clone-voice service']}")
    except Exception as e:
        if set_p:
            raise
    return False


# 综合写入日志，默认sp界面
# type=logs|error|subtitle|end|stop|succeed|set_precent|replace_subtitle|.... 末尾显示类型，
# uuid 任务的唯一id，用于确定插入哪个子队列
# nologs=False不写入日志
def set_process(*, text="", type="logs", uuid=None, nologs=False):
    try:
        if text:
            # 移除html
            if type == 'error':
                text = text.replace('\\n', ' ').strip()
        log = {"text": text, "type": type, "uuid": uuid}
        if uuid:
            config.push_queue(uuid, log)
        else:
            config.global_msg.append(log)
    except Exception:
        pass


def send_notification(title, message):
    if config.exec_mode == 'api' or config.exit_soft:
        return
    from plyer import notification
    try:
        notification.notify(
            title=title[:60],
            message=message[:120],
            ticker="pyVideoTrans",
            app_name="pyVideoTrans",  # config.uilanglist['SP-video Translate Dubbing'],
            app_icon=config.ROOT_DIR + '/videotrans/styles/icon.ico',
            timeout=10  # Display duration in seconds
        )
    except:
        pass


# 获取音频时长
def get_audio_time(audio_file):
    # 如果存在缓存并且没有禁用缓存
    out = runffprobe(['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', audio_file])
    if out is False:
        raise Exception(f'ffprobe error:dont get video information')
    out = json.loads(out)
    return float(out['format']['duration'])


def kill_ffmpeg_processes():
    import platform
    import signal
    import getpass
    try:
        system_platform = platform.system()
        current_user = getpass.getuser()

        if system_platform == "Windows":
            subprocess.call(f"taskkill /F /FI \"USERNAME eq {current_user}\" /IM ffmpeg.exe", shell=True)
        elif system_platform == "Linux" or system_platform == "Darwin":
            process = subprocess.Popen(['ps', '-U', current_user], stdout=subprocess.PIPE)
            out, err = process.communicate()

            for line in out.splitlines():
                if b'ffmpeg' in line:
                    pid = int(line.split(None, 1)[0])
                    os.kill(pid, signal.SIGKILL)
    except:
        pass



# input_file_path 可能是字符串：文件路径，也可能是音频数据
def remove_silence_from_end(input_file_path, silence_threshold=-50.0, chunk_size=10, is_start=True):
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    """
    Removes silence from the end of an audio file.

    :param input_file_path: path to the input mp3 file
    :param silence_threshold: the threshold in dBFS considered as silence
    :param chunk_size: the chunk size to use in silence detection (in milliseconds)
    :return: an AudioSegment without silence at the end
    """
    # Load the audio file
    format = "wav"
    if isinstance(input_file_path, str):
        format = input_file_path.split('.')[-1].lower()
        if format in ['wav', 'mp3', 'm4a']:
            audio = AudioSegment.from_file(input_file_path, format=format if format in ['wav', 'mp3'] else 'mp4')
        else:
            # 转为mp3
            try:
                runffmpeg(['-y', '-i', input_file_path, input_file_path + ".mp3"])
                audio = AudioSegment.from_file(input_file_path + ".mp3", format="mp3")
            except Exception:
                return input_file_path

    else:
        audio = input_file_path

    # Detect non-silent chunks
    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=chunk_size,
        silence_thresh=silence_threshold
    )

    # If we have nonsilent chunks, get the start and end of the last nonsilent chunk
    if nonsilent_chunks:
        start_index, end_index = nonsilent_chunks[-1]
    else:
        # If the whole audio is silent, just return it as is
        return input_file_path

    # Remove the silence from the end by slicing the audio segment
    trimmed_audio = audio[:end_index]
    if is_start and nonsilent_chunks[0] and nonsilent_chunks[0][0] > 0:
        trimmed_audio = audio[nonsilent_chunks[0][0]:end_index]
    if isinstance(input_file_path, str):
        if format in ['wav', 'mp3', 'm4a']:
            trimmed_audio.export(input_file_path, format=format if format in ['wav', 'mp3'] else 'mp4')
            return input_file_path
        try:
            trimmed_audio.export(input_file_path + ".mp3", format="mp3")
            runffmpeg(['-y', '-i', input_file_path + ".mp3", input_file_path])
        except Exception:
            pass
        return input_file_path
    return trimmed_audio


def remove_silence_from_file(input_file_path, silence_threshold=-50.0, chunk_size=10, is_start=True):
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    # Load the audio file
    format = input_file_path.split('.')[-1].lower()
    length = 0
    if format in ['wav', 'mp3', 'm4a']:
        audio = AudioSegment.from_file(input_file_path, format=format if format in ['wav', 'mp3'] else 'mp4')
        length = len(audio)
    else:
        # 转为mp3
        try:
            runffmpeg(['-y', '-i', input_file_path, input_file_path + ".mp3"])
            audio = AudioSegment.from_file(input_file_path + ".mp3", format="mp3")
            length = len(audio)
        except Exception:
            return input_file_path, length

    # Detect non-silent chunks
    nonsilent_chunks = detect_nonsilent(
        audio,
        min_silence_len=chunk_size,
        silence_thresh=silence_threshold
    )

    # If we have nonsilent chunks, get the start and end of the last nonsilent chunk
    if not nonsilent_chunks:
        return input_file_path, length

    start_index, end_index = nonsilent_chunks[-1]

    # Remove the silence from the end by slicing the audio segment
    trimmed_audio = audio[:end_index]
    if is_start and nonsilent_chunks[0] and nonsilent_chunks[0][0] > 0:
        trimmed_audio = audio[nonsilent_chunks[0][0]:end_index]
    length = len(trimmed_audio)
    if format in ['wav', 'mp3', 'm4a']:
        trimmed_audio.export(input_file_path, format=format if format in ['wav', 'mp3'] else 'mp4')
        return input_file_path, length
    trimmed_audio.export(input_file_path + ".mp3", format="mp3")
    runffmpeg(['-y', '-i', input_file_path + ".mp3", input_file_path])
    return input_file_path, len(AudioSegment.from_file(input_file_path , format=format))


def remove_qsettings_data():
    try:
        Path(config.ROOT_DIR + "/videotrans/params.json").unlink(missing_ok=True)
        Path(config.ROOT_DIR + "/videotrans/cfg.json").unlink(missing_ok=True)
    except Exception:
        pass


def open_url(url=None, title: str = None):
    import webbrowser
    if url:
        return webbrowser.open_new_tab(url)
    title_url_dict = {
        'blog': "https://bbs.pyvideotrans.com",
        'ffmpeg': "https://www.ffmpeg.org/download.html",
        'git': "https://github.com/jianchang512/pyvideotrans",
        'issue': "https://github.com/jianchang512/pyvideotrans/issues",
        'discord': "https://discord.gg/7ZWbwKGMcx",
        'models': "https://github.com/jianchang512/stt/releases/tag/0.0",
        'stt': "https://github.com/jianchang512/stt/",

        'gtrans': "https://pvt9.com/aiocr",
        'cuda': "https://pvt9.com/gpu.html",
        'website': "https://pvt9.com",
        'help': "https://pvt9.com",
        'xinshou': "https://pvt9.com/getstart",
        "about": "https://pvt9.com/about",
        'download': "https://github.com/jianchang512/pyvideotrans/releases",
        'openvoice': "https://github.com/kungful/openvoice-api"
    }
    if title and title in title_url_dict:
        return webbrowser.open_new_tab(title_url_dict[title])


def open_dir(dirname=None):
    if not dirname:
        return
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    dirname = dirname.strip()
    if not os.path.isdir(dirname):
        dirname = os.path.dirname(dirname)
    if not dirname or not os.path.isdir(dirname):
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(dirname))


def vail_file(file=None):
    if not file:
        return False
    p = Path(file)
    if not p.exists() or not p.is_file():
        return False
    if p.stat().st_size == 0:
        return False
    return True





def get_video_codec(force_test: bool = False) -> str:
    """
    通过测试确定最佳可用的硬件加速 H.264/H.265 编码器（优化版）。

    根据平台优先选择硬件编码器。如果硬件测试失败，则回退到软件编码。
    结果会被缓存。此版本通过数据驱动设计和提前检查来优化结构和效率。

    依赖 'config' 模块获取设置和路径。假设 'ffmpeg' 在系统 PATH 中，
    测试输入文件存在，并且 TEMP_DIR 可写。

    Args:
        force_test (bool): 如果为 True，则忽略缓存并重新运行测试。默认为 False。

    Returns:
        str: 推荐的 ffmpeg 视频编码器名称 (例如 'h264_nvenc', 'libx264')。
    """
    _codec_cache = config.codec_cache  # 使用 config 中的缓存

    plat = platform.system()
    try:
        video_codec_pref = int(config.settings.get('video_codec', 264))
    except (ValueError, TypeError):
        config.logger.warning("配置中 'video_codec' 无效。将默认使用 H.264 (264)。")
        video_codec_pref = 264

    cache_key = (plat, video_codec_pref)
    if not force_test and cache_key in _codec_cache:
        config.logger.info(f"返回缓存的编解码器 {cache_key}: {_codec_cache[cache_key]}")
        return _codec_cache[cache_key]

    h_prefix, default_codec = ('hevc', 'libx265') if video_codec_pref == 265 else ('h264', 'libx264')
    if video_codec_pref not in [264, 265]:
        config.logger.warning(f"未预期的 video_codec 值 '{video_codec_pref}'。将视为 H.264 处理。")

    # --- 优化点 1: 数据驱动设计 ---
    # 定义各平台硬件编码器的检测优先级
    ENCODER_PRIORITY = {
        'Darwin': ['videotoolbox'],
        'Windows': ['nvenc', 'qsv', 'amf'],
        'Linux': ['nvenc', 'vaapi', 'qsv']
    }

    # --- 定义路径和内部测试函数 (与原版基本相同，但做微小调整) ---
    try:
        test_input_file = Path(config.ROOT_DIR) / "videotrans/styles/no-remove.mp4"
        temp_dir = Path(config.TEMP_DIR)
    except Exception as e:
        config.logger.error(f"从配置构建路径时出错: {e}。将回退到 {default_codec}。")
        _codec_cache[cache_key] = default_codec
        return default_codec

    def test_encoder_internal(encoder_to_test: str, timeout: int = 20) -> bool:
        # 这个内部函数的设计已经很好了，几乎不需要修改
        timestamp = int(time.time() * 1000)
        output_file = temp_dir / f"test_{encoder_to_test}_{timestamp}.mp4"
        command = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-t", "1", "-i", str(test_input_file),
            "-c:v", encoder_to_test, "-f", "mp4", str(output_file)
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

        config.logger.info(f"正在尝试测试编码器: {encoder_to_test}...")
        success = False
        try:
            process = subprocess.run(
                command, check=True, capture_output=True, text=True,
                encoding='utf-8', errors='ignore', creationflags=creationflags, timeout=timeout
            )
            config.logger.info(f"成功: 编码器 '{encoder_to_test}' 测试通过。")
            success = True
        except FileNotFoundError:
            config.logger.error("'ffmpeg' 命令在 PATH 中未找到。无法进行编码器测试。")
            raise  # 重新抛出异常，让上层逻辑捕获并终止测试
        except subprocess.CalledProcessError as e:
            config.logger.warning(f"失败: 编码器 '{encoder_to_test}' 测试失败。FFmpeg 返回码: {e.returncode}")
            # 只在有 stderr 时记录，避免日志混乱
            if e.stderr and e.stderr.strip():
                config.logger.warning(f"FFmpeg stderr:\n{e.stderr.strip()}")
        except PermissionError:
            config.logger.error(f"失败: 写入 {output_file} 时权限被拒绝。")
        except subprocess.TimeoutExpired:
            config.logger.warning(f"失败: 编码器 '{encoder_to_test}' 测试在 {timeout} 秒后超时。")
        except Exception as e:
            config.logger.error(f"失败: 测试编码器 {encoder_to_test} 时发生意外错误: {e}", exc_info=True)
        finally:
            if output_file.exists():
                output_file.unlink(missing_ok=True)
            return success

    # --- 优化点 2: 统一的、数据驱动的测试流程 ---
    selected_codec = default_codec # 初始化为回退选项
    
    encoders_to_test = ENCODER_PRIORITY.get(plat, [])
    if not encoders_to_test:
        config.logger.info(f"不支持的平台: {plat}。将使用软件编码器 {default_codec}。")
    else:
        config.logger.info(f"平台: {plat}。正在按优先级检测最佳的 '{h_prefix}' 编码器: {encoders_to_test}")
        try:
            for encoder_suffix in encoders_to_test:
                # --- 优化点 3: 简化的 nvenc 预检查 ---
                if encoder_suffix == 'nvenc':
                    try:
                        import torch
                        if not torch.cuda.is_available():
                            config.logger.info("PyTorch 报告 CUDA 不可用，跳过 nvenc 测试。")
                            continue # 跳过当前循环，测试下一个编码器
                    except ImportError:
                        # torch 未安装是正常情况，继续尝试测试 nvenc
                        config.logger.info("未找到 torch 模块，将直接尝试 nvenc 测试。")
                
                full_encoder_name = f"{h_prefix}_{encoder_suffix}"
                if test_encoder_internal(full_encoder_name):
                    selected_codec = full_encoder_name
                    config.logger.info(f"已选择硬件编码器: {selected_codec}")
                    break # 找到第一个可用的，立即停止测试
            else: # for-else 循环正常结束 (没有 break)
                config.logger.info(f"所有硬件加速器测试均失败。将使用软件编码器: {selected_codec}")

        except FileNotFoundError:
            # --- 优化点 2 的实现: 如果 ffmpeg 未找到，直接回退 ---
            config.logger.error(f"由于 'ffmpeg' 未找到，所有硬件加速测试已中止。")
            selected_codec = default_codec # 确保回退
        except Exception as e:
            config.logger.error(f"在编码器测试期间发生意外错误: {e}", exc_info=True)
            selected_codec = default_codec

    # --- 最终结果 ---
    _codec_cache[cache_key] = selected_codec
    config.logger.info(f"最终确定的编码器: {selected_codec}")
    return selected_codec
# 设置ass字体格式
def set_ass_font(srtfile=None):
    if not os.path.exists(srtfile) or os.path.getsize(srtfile) == 0:
        return os.path.basename(srtfile)
    runffmpeg(['-y', '-i', srtfile, f'{srtfile}.ass'])
    assfile = f'{srtfile}.ass'
    
    with open(assfile, 'r', encoding='utf-8') as f:
        ass_str = f.readlines()

    for i, it in enumerate(ass_str):
        if it.find('Style: ') == 0:
            ass_str[
                i] = 'Style: Default,{fontname},{fontsize},{fontcolor},&HFFFFFF,{fontbordercolor},&H0,0,0,0,0,100,100,0,0,1,1,0,{subtitle_position},10,10,{marginV},1'.format(
                fontname=config.settings['fontname'], fontsize=config.settings['fontsize'],
                fontcolor=config.settings['fontcolor'], fontbordercolor=config.settings['fontbordercolor'],
                subtitle_position=int(config.settings.get('subtitle_position',2)),
                marginV=int(config.settings.get('marginV',10))
                )
        elif it.find('Dialogue: ') == 0:
            ass_str[i] = it.replace('  ', '\\N')

    with open(assfile, 'w', encoding='utf-8') as f:
        f.write("".join(ass_str))
    #shutil.copy(assfile,'c:/users/c1/videos/ceshi.ass')
    return assfile


# 删除翻译结果的特殊字符
def cleartext(text: str, remove_start_end=True):
    res_text = text.replace('&#39;', "'").replace('&quot;', '"').replace("\u200b", " ").strip()
    # 删掉连续的多个标点符号，只保留一个
    res_text = re.sub(r'([，。！？,.?]\s?){2,}', ',', res_text)
    if not res_text or not remove_start_end:
        return res_text
    if res_text[-1] in ['，', ',']:
        res_text = res_text[:-1]
    if res_text and res_text[0] in ['，', ',']:
        res_text = res_text[1:]
    return res_text



# 删除临时文件
def _unlink_tmp():
    try:
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
    except Exception as e:
        print(f'删除文件失败 {e}')
        pass
    try:
        shutil.rmtree(config.TEMP_HOME, ignore_errors=True)
    except Exception as e:
        print(f'删除文件失败 {e}')
        pass


# 启动删除未使用的 临时文件夹，处理关闭时未能正确删除而遗留的
def del_unused_tmp():
    remain = Path(config.TEMP_DIR).name

    def get_tmplist(pathdir):
        dirs = []
        for p in Path(pathdir).iterdir():
            if p.is_dir() and re.match(r'tmp\d{4}', p.name) and p.name != remain:
                dirs.append(p.resolve().as_posix())
        return dirs

    wait_remove = [*get_tmplist(config.ROOT_DIR), *get_tmplist(config.HOME_DIR)]

    try:
        for p in wait_remove:
            shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass


def shutdown_system():
    # 获取当前操作系统类型
    system = platform.system()

    if system == "Windows":
        # Windows 下的关机命令
        subprocess.call("shutdown /s /t 1")
    elif system == "Linux":
        # Linux 下的关机命令
        subprocess.call("poweroff")
    elif system == "Darwin":
        # macOS 下的关机命令
        subprocess.call("sudo shutdown -h now", shell=True)
    else:
        print(f"Unsupported system: {system}")


def format_video(name, target_dir=None):
    raw_pathlib = Path(name)
    raw_basename = raw_pathlib.name
    raw_noextname = raw_pathlib.stem
    ext = raw_pathlib.suffix
    raw_dirname = raw_pathlib.parent.resolve().as_posix()

    obj = {
        "name": name,
        # 处理后 移动后符合规范的目录名
        "dirname": raw_dirname,
        # 符合规范的基本名带后缀
        "basename": raw_basename,
        # 符合规范的不带后缀
        "noextname": raw_noextname,
        # 扩展名
        "ext": ext[1:]
        # 最终存放目标位置，直接存到这里
    }
    rule = r'[\[\]\*\?\"\|\'\:]'
    if re.search(rule, raw_noextname) or re.search(r'[\s\.]$', raw_noextname):
        # 规范化名字
        raw_noextname = re.sub(rule, f'', raw_noextname)
        raw_noextname = re.sub(r'[\.\s]$', f'', raw_noextname)
        raw_noextname = raw_noextname.strip()

        if Path(f'{config.TEMP_DIR}/{raw_noextname}{ext}').exists():
            raw_noextname += f'{chr(random.randint(97, 122))}'

        new_name = f'{config.TEMP_DIR}/{raw_noextname}{ext}'
        shutil.copy2(name, new_name)
        obj['name'] = new_name
        obj['noextname'] = raw_noextname
        obj['basename'] = f'{raw_noextname}{ext}'
        obj['shound_del_name'] = new_name

    if target_dir:
        obj['target_dir'] = Path(f'{target_dir}/{raw_noextname}').as_posix()

    obj['uuid'] = get_md5(f'{name}-{time.time()}')[:10]
    return obj


# 获取 prompt提示词
def get_prompt(ainame, is_srt=True):
    prompt_file = get_prompt_file(ainame=ainame, is_srt=is_srt)
    content = Path(prompt_file).read_text(encoding='utf-8')
    glossary = ''
    if Path(config.ROOT_DIR + '/videotrans/glossary.txt').exists():
        glossary = Path(config.ROOT_DIR + '/videotrans/glossary.txt').read_text(encoding='utf-8').strip()
    if glossary:
        glossary = "\n".join(["|" + it.replace("=", '|') + "|" for it in glossary.split('\n')])
        glossary_prompt = """## 术语表\n严格按照以下术语表进行翻译,如果句子中出现术语,必须使用对应的翻译,而不能自由翻译：\n| 术语  | 翻译  |\n| --------- | ----- |\n""" if config.defaulelang == 'zh' else """## Glossary of terms\nTranslations are made strictly according to the following glossary. If a term appears in a sentence, the corresponding translation must be used, not a free translation:\n| Glossary | Translation |\n| --------- | ----- |\n"""
        content = content.replace('<INPUT></INPUT>', f"""{glossary_prompt}{glossary}\n\n<INPUT></INPUT>""")
    return content


# 获取当前需要操作的prompt txt文件
def get_prompt_file(ainame, is_srt=True):
    prompt_path = f'{config.ROOT_DIR}/videotrans/'
    prompt_name = f'{ainame}{"" if config.defaulelang == "zh" else "-en"}.txt'
    if is_srt and config.settings.get('aisendsrt', False):
        prompt_path += 'prompts/srt/'
    return f'{prompt_path}{prompt_name}'


# 将普通文本转为合法的srt字符串
def process_text_to_srt_str(input_text: str):
    if is_srt_string(input_text):
        return input_text

    # 将文本按换行符切割成列表
    text_lines = [line.strip() for line in input_text.replace("\r", "").splitlines() if line.strip()]

    # 分割大于50个字符的行
    text_str_list = []
    for line in text_lines:
        if len(line) > 50:
            # 按标点符号分割为多个字符串
            split_lines = re.split(r'[,.，。]', line)
            text_str_list.extend([l.strip() for l in split_lines if l.strip()])
        else:
            text_str_list.append(line)
    # 创建字幕字典对象列表
    dict_list = []
    start_time_in_seconds = 0  # 初始时间，单位秒

    for i, text in enumerate(text_str_list, start=1):
        # 计算开始时间和结束时间（每次增加1s）
        start_time = ms_to_time_string(seconds=start_time_in_seconds)
        end_time = ms_to_time_string(seconds=start_time_in_seconds + 1)
        start_time_in_seconds += 1

        # 创建字幕字典对象
        srt = f"{i}\n{start_time} --> {end_time}\n{text}"
        dict_list.append(srt)

    return "\n\n".join(dict_list)


# 判断是否是srt字符串
def is_srt_string(input_text):
    input_text = input_text.strip()
    if not input_text:
        return False

    # 将文本按换行符切割成列表
    text_lines = input_text.replace("\r", "").splitlines()
    if len(text_lines) < 3:
        return False

    # 正则表达式：第一行应为1到2个纯数字
    first_line_pattern = r'^\d{1,2}$'

    # 正则表达式：第二行符合时间格式
    second_line_pattern = r'^\s*?\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*$'

    # 如果前两行符合条件，返回原字符串
    if not re.match(first_line_pattern, text_lines[0].strip()) or not re.match(second_line_pattern,
                                                                               text_lines[1].strip()):
        return False
    return True


def clean_srt(srt):
    # 替换特殊符号
    srt = re.sub(r'&gt;', '>', srt)
    # ：: 换成 :
    srt = re.sub(r'([：:])\s*', ':', srt)
    # ,， 换成 ,
    srt = re.sub(r'([,，])\s*', ',', srt)
    srt = re.sub(r'([`’\'\"])\s*', '', srt)

    # 秒和毫秒间的.换成,
    srt = re.sub(r'(:\d+)\.\s*?(\d+)', r'\1,\2', srt)
    # 时间行前后加空格
    time_line = r'(\s?\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s?)'
    srt = re.sub(time_line, r"\n\1 --> \2\n", srt)
    # twenty one\n00:01:18,560 --> 00:01:22,000\n
    srt = re.sub(r'\s?[a-zA-Z ]{3,}\s*?\n?(\d{2}:\d{2}:\d{2}\,\d{3}\s*?\-\->\s*?\d{2}:\d{2}:\d{2}\,\d{3})\s?\n?',
                 "\n" + r'1\n\1\n', srt)
    # 去除多余的空行
    srt = "\n".join([it.strip() for it in srt.splitlines() if it.strip()])

    # 删掉以空格或换行连接的多个时间行
    time_line2 = r'(\s\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s)(?:\s*\d+:\d+:\d+(?:,\d+)?)\s*?-->\s*?(\d+:\d+:\d+(?:,\d+)?\s*)'
    srt = re.sub(time_line2, r'\n\1 --> \2\n', srt)
    srt_list = [it.strip() for it in srt.splitlines() if it.strip()]

    remove_list = []
    for it in srt_list:
        if len(remove_list) > 0 and str(it) == str(remove_list[-1]):
            if re.match(r'^\d{1,4}$', it):
                continue
            if re.match(r'\d+:\d+:\d+([,.]\d+)? --> \d+:\d+:\d+([,.]\d+)?'):
                continue
        remove_list.append(it)

    srt = "\n".join(remove_list)

    # 行号前添加换行符
    srt = re.sub(r'\s?(\d+)\s+?(\d+:\d+:\d+)', r"\n\n\1\n\2", srt)
    return srt.strip().replace('&#39;', '"').replace('&quot;', "'")


def check_local_api(api):
    from PySide6 import QtWidgets, QtGui
    # 创建消息框
    msg_box = QtWidgets.QMessageBox()
    msg_box.setIcon(QtWidgets.QMessageBox.Critical)
    msg_box.setText("API url error:")
    msg_box.setWindowTitle(config.transobj['anerror'])

    # 设置窗口图标
    icon = QtGui.QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico")  # 替换为你的图标路径
    msg_box.setWindowIcon(icon)

    # 显示消息框

    if not api:
        msg_box.setInformativeText('必须填写http地址' if config.defaulelang == 'zh' else 'Must fill in the http address')
        msg_box.exec()
        return False
    if api.find('0.0.0.0:') > -1:
        msg_box.setInformativeText(
            '请将 0.0.0.0 改为 127.0.0.1 ' if config.defaulelang == 'zh' else 'Please change 0.0.0.0 to 127.0.0.1. ')
        msg_box.exec()
        return False
    return True


def format_milliseconds(milliseconds):
    """
    将毫秒数转换为 HH:mm:ss.zz 格式的字符串。

    Args:
        milliseconds (int): 毫秒数。

    Returns:
        str: 格式化后的字符串，格式为 HH:mm:ss.zz。
    """
    if not isinstance(milliseconds, int):
        raise TypeError("毫秒数必须是整数")
    if milliseconds < 0:
        raise ValueError("毫秒数必须是非负整数")

    seconds = milliseconds / 1000

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    milliseconds_part = int((seconds * 1000) % 1000) // 10  # 保留两位

    # 格式化为两位数字字符串
    formatted_hours = f"{int(hours):02}"
    formatted_minutes = f"{int(minutes):02}"
    formatted_seconds = f"{int(seconds):02}"
    formatted_milliseconds = f"{milliseconds_part:02}"


    return f"{formatted_hours}:{formatted_minutes}:{formatted_seconds}.{formatted_milliseconds}"


def show_glossary_editor(parent):
    from PySide6.QtWidgets import (QVBoxLayout, QTextEdit, QDialog,
                                   QDialogButtonBox)
    from PySide6.QtCore import Qt
    """
    弹出一个窗口，包含一个文本框和保存按钮，并处理文本的读取和保存。

    Args:
        parent: 父窗口 (QWidget)
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle("在此填写术语对照表，格式： 术语=翻译" if config.defaulelang == 'zh' else '')
    dialog.setMinimumSize(600, 400)

    layout = QVBoxLayout(dialog)

    text_edit = QTextEdit()
    text_edit.setPlaceholderText(
        "请按照 术语=翻译 的格式，一行一组来填写，例如\n\n首席执行官=CEO\n人工智能=AI\n\n在原文中如果遇到以上左侧文字，则翻译结果使用右侧文字" if config.defaulelang == 'zh' else "Please fill in one line at a time, following the term on the left and the translation on the right, e.g. \nBallistic Missile Defense=BMD\nChief Executive Officer=CEO")
    layout.addWidget(text_edit)

    button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    layout.addWidget(button_box)

    # 读取文件内容，并设置为文本框默认值
    file_path = config.ROOT_DIR + "/videotrans/glossary.txt"
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                text_edit.setText(content)
    except Exception as e:
        print(f"读取文件失败: {e}")

    def save_text():
        """
        点击保存按钮，将文本框内容写回文件。
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_edit.toPlainText())  # toPlainText 获取纯文本
            dialog.accept()
        except Exception as e:
            print(f"写入文件失败: {e}")

    button_box.accepted.connect(save_text)
    button_box.rejected.connect(dialog.reject)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # 设置模态窗口
    dialog.exec()  # 显示模态窗口


def is_writable(directory_path: str):
    import uuid
    import stat # 虽然主要用EAFP，但保留os模块用于路径操作

    """
    跨平台检查一个目录是否对当前用户可写。

    采用 EAFP (Easier to Ask Forgiveness than Permission) 方法：
    尝试在目录中创建并删除一个临时文件来判断实际的写权限。

    Args:
        directory_path: 要检查的目录路径。

    Returns:
        如果目录存在且可写，则返回 True；否则返回 False。
    """
    # 1. 首先检查路径是否存在且确实是一个目录
    if not os.path.isdir(directory_path):
        # 如果路径不存在，或者存在但不是一个目录，则它不是一个可写的目录
        return False

    # 2. 尝试在目录中创建一个唯一的临时文件 (EAFP)
    # 生成一个非常不可能冲突的临时文件名
    # 使用点开头通常使其在类Unix系统上隐藏
    temp_filename = f".permission_test_{uuid.uuid4()}.tmp"
    temp_file_path = os.path.join(directory_path, temp_filename)

    write_successful = False
    try:
        # 尝试以写模式('w')打开（并创建）文件
        # 'with' 语句确保文件句柄在使用后会被关闭
        with open(temp_file_path, 'w') as f:
            # 实际上不需要写入任何内容，只要能成功打开即可证明有写权限
            pass
        # 如果代码执行到这里，说明文件创建成功
        write_successful = True

    except OSError as e:
        # 捕获所有与OS相关的错误，最常见的是 PermissionError，
        # 但也可能包括其他问题（如磁盘满、无效路径字符等），这些都意味着无法写入。
        # print(f"Debug: Caught OSError trying to write to {temp_file_path}: {e}") # 可选的调试输出
        write_successful = False

    finally:
        # 3. 清理：无论成功与否，都尝试删除创建的临时文件（如果它存在）
        # 检查文件是否确实被创建了（可能在open之前就失败了）
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError as e:
                # 在某些边缘情况下，即使创建成功，删除也可能失败
                # (例如，权限在创建和删除之间被更改了)。
                # 我们不应让清理失败影响函数的主要结果（是否可写）。
                # 可以选择记录这个警告。
                # print(f"Warning: Could not remove temp file {temp_file_path}: {e}")
                pass

    return write_successful
