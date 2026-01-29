# -*- coding: utf-8 -*-
import datetime
import json
from PySide6.QtCore import QLocale
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from queue import Queue
from videotrans.util.contants import no_proxy, FUNASR_MODEL, DEEPGRAM_MODEL, VIDEO_EXTS, AUDIO_EXITS, \
    DEFAULT_GEMINI_MODEL, OPENAITTS_ROLES, GEMINITTS_ROLES

IS_FROZEN = True if getattr(sys, 'frozen', False) else False
SYS_TMP = Path(tempfile.gettempdir()).as_posix()
# 程序根目录
ROOT_DIR = Path(sys.executable).parent.as_posix() if IS_FROZEN else Path(__file__).parent.parent.parent.as_posix()
if IS_FROZEN:
    # 如果程序是被"冻结"打包的，使用这个路径
    os.environ['TQDM_DISABLE'] = '1'
os.environ['no_proxy'] = no_proxy
os.environ['NO_PROXY'] = no_proxy  # 某些系统或库可能检查大写
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ['QT_API'] = 'pyside6'
os.environ['SOFT_NAME'] = 'pyvideotrans'
os.environ['MODELSCOPE_CACHE'] = ROOT_DIR + "/models"
os.environ['HF_HOME'] = ROOT_DIR + "/models"
os.environ['HF_HUB_CACHE'] = ROOT_DIR + "/models"
os.environ['HF_TOKEN_PATH'] = ROOT_DIR + "/models/hf_token.txt"
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = 'true'
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = 'true'
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = "3600"
os.environ["HF_HUB_DISABLE_XET"] = "1"
# ffmpeg
FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"
os.environ['PATH'] = ROOT_DIR + os.pathsep + f'{ROOT_DIR}/ffmpeg' + os.pathsep + os.environ.get("PATH", "")
if sys.platform == 'win32' and IS_FROZEN:
    os.environ['PATH'] = f'{ROOT_DIR}/_internal/torch/lib;' + os.environ['PATH']
    if Path(f'{ROOT_DIR}/ffmpeg/ffmpeg.exe').is_file():
        FFMPEG_BIN = f'{ROOT_DIR}/ffmpeg/ffmpeg.exe'
    if Path(f'{ROOT_DIR}/ffmpeg/ffprobe.exe').is_file():
        FFPROBE_BIN = f'{ROOT_DIR}/ffmpeg/ffprobe.exe'

# 程序根下临时目录tmp
TEMP_ROOT = f'{ROOT_DIR}/tmp'
TEMP_DIR = f'{TEMP_ROOT}/{os.getpid()}'
# 家目录
HOME_DIR = ROOT_DIR + "/output"

Path(f"{ROOT_DIR}/logs").mkdir(parents=True, exist_ok=True)
Path(f'{TEMP_ROOT}/translate_cache').mkdir(exist_ok=True, parents=True)

# 日志
logger = logging.getLogger('VideoTrans')
logger.setLevel(logging.DEBUG)
# 设置日志格式
formatter = logging.Formatter('[%(levelname)s] %(message)s')
_file_handler = logging.FileHandler(f'{ROOT_DIR}/logs/{datetime.datetime.now().strftime("%Y%m%d")}.log',
                                    encoding='utf-8')
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(formatter)
# 创建控制台处理器，并设置级别
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.WARNING)
_console_handler.setFormatter(formatter)
# 添加处理器到日志记录器
logger.addHandler(_file_handler)
logger.addHandler(_console_handler)

logging.getLogger("transformers").setLevel(logging.DEBUG)
logging.getLogger("filelock").setLevel(logging.DEBUG)
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)
# fw_logger = logging.getLogger("faster_whisper")
# fw_logger.setLevel(logging.DEBUG)
# fw_logger.addHandler(_file_handler)

## nvidia 显卡数量, -1未检测或cpu模式
## 0=无可用显卡
## >0显卡数量

NVIDIA_GPU_NUMS=-1


# 队列
# 存储已停止/暂停的任务 uuid
stoped_uuid_set = set()
# 存储所有任务的进度队列，以uuid为键
# 根据uuid将日志进度等信息存入队列，如果不存在则创建
uuid_logs_queue = {}

# 全局消息，不存在uuid，用于控制软件
global_msg = []
# 软件退出
exit_soft = False
# 所有设置窗口和子窗口
child_forms = {}
# 存储各个子窗口的唯一实例
INFO_WIN = {"data": {}, "win": None}

# 存放视频分离为无声视频进度，noextname为key，用于判断某个视频是否是否已预先创建好 novice_mp4, "ing"=需等待，end=成功完成，error=出错了
queue_novice = {}

# 主界面完整流程状态标识：开始按钮状态 ing 执行中，stop手动停止 end 正常结束
current_status = "stop"
# 倒计时数秒
task_countdown = 0

# 预先处理队列
prepare_queue = Queue(maxsize=0)
# 识别队列
regcon_queue = Queue(maxsize=0)
# 说话人队列
diariz_queue = Queue(maxsize=0)
# 翻译队列
trans_queue = Queue(maxsize=0)
# 配音队列
dubb_queue = Queue(maxsize=0)
# 音视频画面对齐
align_queue = Queue(maxsize=0)
# 合成队列
assemb_queue = Queue(maxsize=0)
# 最终完成结束任务队列
taskdone_queue = Queue(maxsize=0)

# 执行模式 gui 或 api
exec_mode = "gui"
# 设置当前可用视频编码  libx264 h264_qsv h264_nvenc 等
video_codec = None
codec_cache = {}

# 字幕按行赋予角色
line_roles = {}
# 原始语言字幕路径
onlyone_source_sub = None
# 目标语言字幕路径
onlyone_target_sub = None
# 是否需要翻译，仅在需要翻译时，才需传递做参考的对比原始字幕
onlyone_trans = False

# 字幕多角色配音
dubbing_role = {}
SUPPORT_LANG = {}

# 设置默认高级参数值
def parse_init(update_data=None):
    if update_data:
        with  open(ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(update_data, ensure_ascii=False))
        return update_data
    default = {
        "homedir": HOME_DIR,
        "lang": "",
        "Faster_Whisper_XXL": "",
        "Whisper.cpp": "",
        "Whisper.cpp.models": "ggml-tiny.bin,ggml-base.bin,ggml-small.bin,ggml-medium.bin,ggml-large-v1.bin,ggml-large-v2.bin,ggml-large-v3.bin,ggml-large-v3-turbo.bin",
        "crf": 24,
        "edgetts_max_concurrent_tasks": 10,
        "edgetts_retry_nums": 3,
        "force_lib": False,
        "preset": "veryfast",
        "ffmpeg_cmd": "",
        "aisendsrt": True,
        "dont_notify": False,
        "video_codec": 265,

        "noise_separate_nums": 4,
        
        "aitrans_temperature":0.2,
        "aitrans_context":False,

        "batch_single": False,

        # 默认显示模型
        "ai302_models": "deepseek-chat,gemini-2.5-flash",
        'qwenmt_model': "qwen3-max,qwen-mt-turbo,qwen-mt-plus,qwen-mt-flash,qwen3-asr-flash",
        "openaitts_model": "tts-1,tts-1-hd,gpt-4o-mini-tts",
        "openairecognapi_model": "whisper-1,gpt-4o-transcribe,gpt-4o-mini-transcribe,gpt-4o-transcribe-diarize",
        "chatgpt_model": "gpt-5.2,gpt-5.2-pro,gpt-5,gpt-5-mini,gpt-5-nano,gpt-4.1",
        "claude_model": "claude-sonnet-4-5,claude-haiku-4-5,claude-opus-4-5",
        "azure_model": "gpt-5.2,gpt-5.2-pro,gpt-5,gpt-5-mini,gpt-5-nano,gpt-4.1",
        "localllm_model": "qwen:7b,deepseek-chat",
        "zhipuai_model": "glm-4.5-flash",
        "deepseek_model": "deepseek-chat,deepseek-reasoner",
        "openrouter_model": "moonshotai/kimi-k2:free,tngtech/deepseek-r1t2-chimera:free,deepseek/deepseek-r1-0528:free",
        "guiji_model": "Qwen/Qwen3-8B,Qwen/Qwen2.5-7B-Instruct,Qwen/Qwen2-7B-Instruct",
        "zijiehuoshan_model": "",

        # 默认 faster_whisper和openai-whisper模型
        "model_list": "tiny,tiny.en,base,base.en,small,small.en,medium,medium.en,large-v3-turbo,large-v1,large-v2,large-v3,distil-large-v3.5",

        "max_audio_speed_rate": 100,
        "max_video_pts_rate": 10,

        "threshold": 0.5,
        "min_speech_duration_ms": 2000,
        "max_speech_duration_s": 6,
        "min_silence_duration_ms": 600,
        "no_speech_threshold": 0.5,

        "batch_size": 4,
        "merge_short_sub": True,

        "vad_type": "tenvad",  # tenvad silero

        "trans_thread": 20,
        "aitrans_thread": 50,
        "translation_wait": 0,
        "dubbing_wait": 1,
        "dubbing_thread": 1,
        "save_segment_audio": False,
        "countdown_sec": 30,
        "backaudio_volume": 0.8,
        "loop_backaudio": True,
        "cuda_com_type": "default",  # int8 int8_float16 int8_float32
        "initial_prompt_zh-cn": "",
        "initial_prompt_zh-tw": "",
        "initial_prompt_en": "",
        "initial_prompt_fr": "",
        "initial_prompt_de": "",
        "initial_prompt_ja": "",
        "initial_prompt_ko": "",
        "initial_prompt_ru": "",
        "initial_prompt_es": "",
        "initial_prompt_th": "",
        "initial_prompt_it": "",
        "initial_prompt_pt": "",
        "initial_prompt_vi": "",
        "initial_prompt_ar": "",
        "initial_prompt_tr": "",
        "initial_prompt_hi": "",
        "initial_prompt_hu": "",
        "initial_prompt_uk": "",
        "initial_prompt_id": "",
        "initial_prompt_ms": "",
        "initial_prompt_kk": "",
        "initial_prompt_cs": "",
        "initial_prompt_pl": "",
        "initial_prompt_nl": "",
        "initial_prompt_sv": "",
        "initial_prompt_he": "",
        "initial_prompt_bn": "",
        "initial_prompt_fil": "",
        "initial_prompt_fa": "",
        "initial_prompt_ur": "",
        "initial_prompt_yue": "",
        "beam_size": 5,
        "best_of": 5,
        "condition_on_previous_text": False,
        "temperature":"0.0",
        "repetition_penalty":1.0,
        "compression_ratio_threshold":2.2,

        "qwentts_role": '',
        "qwentts_models": 'qwen3-tts-flash-2025-11-27,qwen3-tts-flash',

        "show_more_settings": False,

        "speaker_type": "built",  # built=内置 支持中英，pyannote=私库, ali_CAM=阿里中英, reverb=私库类似pyannote
        "hf_token": "",  # 使用 pyannote需要huggingface.co的token

        "cjk_len": 22,
        "other_len": 46,
        "gemini_model": DEFAULT_GEMINI_MODEL,
        "llm_chunk_size": 50,
        "llm_ai_type": "openai",
        "gemini_recogn_chunk": 50,
        "zh_hant_s": True,
        "process_max":0,
        "process_max_gpu":0,
        "multi_gpus":False,# 多显卡模式
        "azure_lines": 1,
        "chattts_voice": "11,12,16,2222,4444,6653,7869,9999,5,13,14,1111,3333,4099,5099,5555,8888,6666,7777",
        "proxy": ""
    }
    if not Path(ROOT_DIR + "/videotrans/cfg.json").exists():
        with open(ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(default, ensure_ascii=False))
        return default
    try:
        temp_json = json.loads(Path(ROOT_DIR + "/videotrans/cfg.json").read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return default
    else:
        _settings = {}
        for key, val in temp_json.items():
            if key not in default:
                continue
            value = str(val).strip()
            if re.match(r'^\d+$', value):
                _settings[key] = int(value)
            elif re.match(r'^\d*\.\d+$', value):
                _settings[key] = float(value)
            elif value.lower() == 'true':
                _settings[key] = True
            elif value.lower() == 'false':
                _settings[key] = False
            elif value:
                _settings[key] = value
        # 补充新增的模型到 缓存
        _de = default['model_list'].split(',')
        _ca = _settings['model_list'].split(',')
        _new = [it for it in _de if it not in _ca]
        _ca.extend(_new)
        _settings['model_list'] = ",".join(_ca)
        default.update(_settings)
        with open(ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(default, ensure_ascii=False))
        p = Path(ROOT_DIR + "/models/hf_token.txt")
        if p.is_file():
            tk = p.read_text().strip()
            if tk:
                default['hf_token'] = tk
            else:
                p.unlink(missing_ok=True)

        if not p.is_file() and default.get('hf_token'):
            p.write_text(default['hf_token'])
        return default

# 高级选项信息
settings = parse_init()
# 代理地址
proxy = settings.get('proxy', os.environ.get('HTTPS_PROXY', ''))
if proxy:
    os.environ['HTTPS_PROXY'] = proxy
    os.environ['HTTP_PROXY'] = proxy

# 根据已保存的配置更新 HOME_DIR
HOME_DIR = settings.get('homedir', HOME_DIR)

# 语言界面
try:
    defaulelang = os.environ.get('PYVIDEOTRANS_LANG',settings.get('lang'))
    if not defaulelang:
        defaulelang=QLocale.system().name()[:2].lower()
except:
    defaulelang = "zh"


for it in Path(f'{ROOT_DIR}/videotrans/language').glob('*.json'):
    if it.stat().st_size > 0:
        SUPPORT_LANG[it.stem] = it.as_posix()
if defaulelang not in SUPPORT_LANG:
    defaulelang = "en"

# 任务配置
WHISPER_MODEL_LIST = re.split(r'[,，]', settings.get('model_list', ''))
ChatTTS_voicelist = re.split(r'[,，]', str(settings.get('chattts_voice', '')))

_chatgpt_model_list = str(settings.get('chatgpt_model', '-')).strip().split(',')
_claude_model_list = str(settings.get('claude_model', '-')).strip().split(',')
_azure_model_list = str(settings.get('azure_model', '-')).strip().split(',')
_localllm_model_list = str(settings.get('localllm_model', '-')).strip().split(',')
_zijiehuoshan_model_list = str(settings.get('zijiehuoshan_model', '-')).strip().split(',')
_zhipuai_model_list = str(settings.get('zhipuai_model', '-')).strip().split(',')
_guiji_model_list = str(settings.get('guiji_model', '-')).strip().split(',')
_deepseek_model_list = str(settings.get('deepseek_model', '-')).strip().split(',')
_openrouter_model_list = str(settings.get('openrouter_model', '-')).strip().split(',')
Whisper_CPP_MODEL_LIST = str(settings.get('Whisper.cpp.models', 'ggml-tiny')).strip().split(',')


# 设置或获取 config.params
def getset_params(obj=None):
    # 保存到json
    if obj is not None:
        with open(ROOT_DIR + "/videotrans/params.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False))
        return obj
    # 获取
    default = {
        "last_opendir": os.path.expanduser("~"),
        "cuda": False,
        "line_roles": {},
        "rephrase": 0,
        "is_separate": False,
        "remove_noise": False,
        "enable_diariz": False,
        "nums_diariz": 0,
        "target_dir": "",
        "source_language": "en",
        "target_language": "zh-cn",
        "subtitle_language": "chi",
        "translate_type": 0,
        "subtitle_type": 1,  # embed hard
        "tts_type": 0,  # 所选的tts顺序
        "model_name": "large-v3-turbo",  # 模型名
        "recogn_type": 0,  # 语音识别方式，数字代表显示顺序
        "fix_punc": False,
        "stt_fix_punc": False,
        "voice_autorate": True,
        "video_autorate": False,

        "align_sub_audio": True,

        "voice_role": "No",
        "voice_rate": "0",
        "deepl_authkey": "",
        "deepl_api": "",
        "deepl_gid": "",
        "deeplx_address": "",
        "deeplx_key": "",
        "libre_address": "",
        "libre_key": "",
        "ott_address": "",
        "tencent_SecretId": "",
        "tencent_SecretKey": "",
        "tencent_termlist": "",
        "gcloud_credential_json": "",
        "gcloud_language_code": "",
        "gcloud_voice_name": "",
        "gcloud_audio_encoding": "",
        "gcloud_ssml_gender": "",
        "ali_id": "",
        "ali_key": "",
        "baidu_appid": "",
        "baidu_miyue": "",
        "chatgpt_api": "",
        "chatgpt_key": "",
        "chatgpt_max_token": "8192",
        "chatgpt_model": _chatgpt_model_list[0],
        "claude_api": "",
        "claude_key": "",
        "claude_model": _claude_model_list[0],
        "azure_api": "",
        "azure_key": "",
        "azure_version": "2025-04-01-preview",
        "azure_model": _azure_model_list[0],
        "gemini_key": "",
        "gemini_model": "gemini-2.5-flash",
        "gemini_maxtoken": 18192,
        "gemini_thinking_budget": 24576,
        "gemini_ttsstyle": "",
        "gemini_ttsmodel": "gemini-2.5-flash-preview-tts",
        "localllm_api": "",
        "localllm_key": "",
        "localllm_model": _localllm_model_list[0],
        "localllm_max_token": "4096",
        "zhipu_key": "",
        "zhipu_model": _zhipuai_model_list[0],
        "zhipu_max_token": "98304",
        "guiji_key": "",
        "guiji_model": _guiji_model_list[0],
        "guiji_max_token": "8192",
        "deepseek_key": "",
        "deepseek_model": _deepseek_model_list[0],
        "deepseek_max_token": "8192",
        "openrouter_key": "",
        "openrouter_model": _openrouter_model_list[0],
        "openrouter_max_token": "8192",
        "zijiehuoshan_key": "",
        "zijiehuoshan_model": _zijiehuoshan_model_list[0],

        "qwenmt_key": "",
        "qwenmt_domains": "",
        "qwenmt_model": "qwen-mt-turbo",
        "qwenmt_asr_model": "qwen3-asr-flash",

        "qwenttslocal_refaudio":"",
        "qwenttslocal_url":"",
        "qwenttslocal_prompt":"",

        "ai302_key": "",
        "ai302_model": "",
        "ai302_model_recogn": "whisper-1",
        
        

        "whipserx_api": "http://127.0.0.1:9092",

        "trans_api_url": "",
        "trans_secret": "",
        "coquitts_role": "",
        "coquitts_key": "",
        "elevenlabstts_role": [],
        "elevenlabstts_key": "",
        "elevenlabstts_models": "eleven_flash_v2_5",
        "openaitts_api": "",
        "openaitts_key": "",
        "openaitts_model": "tts-1",
        "openaitts_instructions": "",
        "qwentts_key": "",
        "qwentts_model": "qwen-tts-latest",
        "qwentts_role": "Chelsie",
        "kokoro_api": "",
        "openairecognapi_url": "",
        "openairecognapi_key": "",
        "openairecognapi_prompt": "",
        "openairecognapi_model": "whisper-1",
        "parakeet_address": "",
        "clone_api": "",
        "clone_voicelist": ["clone"],
        "zh_recogn_api": "",
        "recognapi_url": "",
        "recognapi_key": "",
        "stt_url": "",
        "stt_model": "tiny",
        "sense_url": "",
        "ttsapi_url": "",
        "ttsapi_voice_role": "",
        "ttsapi_extra": "pyvideotrans",
        "ttsapi_language_boost": "auto",
        "ttsapi_emotion": "happy",

        "minimaxi_apikey": "",
        "minimaxi_emotion": "",
        "minimaxi_apiurl": "api.minimaxi.com",
        "minimaxi_model": "speech-02-turbo",

        "ai302tts_key": "",
        "ai302tts_model": "",
        "ai302tts_role": OPENAITTS_ROLES,
        "azure_speech_region": "",
        "azure_speech_key": "",
        "chatterbox_url": "",
        "chatterbox_role": "",
        "chatterbox_cfg_weight": 0.5,
        "chatterbox_exaggeration": 0.5,
        "gptsovits_url": "",
        "gptsovits_role": "",
        "gptsovits_isv2": True,
        "gptsovits_extra": "pyvideotrans",
        "cosyvoice_url": "",
        "cosyvoice_role": "",
        "fishtts_url": "",
        "fishtts_role": "",
        "f5tts_url": "",
        "f5tts_model": "",
        "f5tts_ttstype": "F5-TTS",
        "f5tts_role": "",
        "index_tts_version": 1,
        "f5tts_is_whisper": False,

        "indextts_url": "",
        "voxcpmtts_url": "",
        "sparktts_url": "",
        "diatts_url": "",

        "doubao_appid": "",
        "doubao_access": "",

        "volcenginetts_appid": "",
        "volcenginetts_access": "",
        "volcenginetts_cluster": "",

        "doubao2_appid": "",
        "doubao2_access": "",

        "zijierecognmodel_appid": "",
        "zijierecognmodel_token": "",

        "chattts_api": "",
        "app_mode": "biaozhun",
        "stt_source_language": 0,
        "stt_recogn_type": 0,
        "stt_model_name": "",
        "stt_remove_noise": False,
        "stt_enable_diariz": False,
        "stt_rephrase": 0,
        "stt_nums_diariz": 0,

        "subtitlecover_outformat": "srt",

        "deepgram_apikey": "",

        "trans_translate_type": 0,
        "trans_source_language": 0,
        "trans_target_language": 1,
        "trans_out_format": 0,
        "dubb_source_language": 0,
        "dubb_tts_type": 0,
        "dubb_role": 0,
        "dubb_out_format": 0,
        "dubb_voice_autorate": False,
        "dubb_hecheng_rate": 0,
        "dubb_pitch_rate": 0,
        "dubb_volume_rate": 0,
        "recogn2pass":True
    }
    try:
        if Path(ROOT_DIR + "/videotrans/params.json").exists():
            default.update(json.loads(Path(ROOT_DIR + "/videotrans/params.json").read_text(encoding='utf-8')))
        else:
            with open(ROOT_DIR + "/videotrans/params.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(default, ensure_ascii=False))
    except (OSError, json.JSONDecodeError):
        pass
    return default


params = getset_params()

if not settings.get('lang'):
    settings['lang']=defaulelang
    settings = parse_init(settings)
    

def push_queue(uuid, jsondata):
    if exit_soft or uuid in stoped_uuid_set:
        return
    if uuid not in uuid_logs_queue:
        uuid_logs_queue[uuid] = Queue(maxsize=0)
    try:
        # 暂停时会重设为字符串 stop
        if isinstance(uuid_logs_queue[uuid], Queue):
            uuid_logs_queue[uuid].put_nowait(jsondata)
    except Exception as e:
        logger.exception(f'push_queue错误：{e}', exc_info=True)

# 翻译
## 翻译,lang_key对应 transobj中键名，kw多个位置参数，对应替换 lang_key中 {}
# tr("xxxxx",root_dir,length)
try:
    transobj = json.loads(Path(SUPPORT_LANG[defaulelang]).read_text(encoding='utf-8'))
except json.JSONDecodeError:
    raise RuntimeError(f'语言文件语法错误:{SUPPORT_LANG[defaulelang]}')
except OSError as e:
    raise RuntimeError(f'语言文件不存在或不可读:{SUPPORT_LANG[defaulelang]}')


def tr(lang_key, *kw):
    if isinstance(lang_key,list):
        str_list=[t for t in [transobj.get(it) for it in lang_key] if t]
        return  ",".join(str_list)
    lang = transobj.get(lang_key)
    if not lang:
        return lang_key
    if not kw:
        return lang
    try:
        return lang.format(*kw)
    except IndexError:
        return lang

def update_logging_level(new_level_str):
    """
    动态修改日志等级
    :param new_level_str: 字符串，例如 "DEBUG", "INFO", "WARNING", "ERROR"
    """
    new_level = getattr(logging, new_level_str.upper(), logging.INFO)
    logger = logging.getLogger('VideoTrans')
    logger.setLevel(new_level)
    # 同时修改 Handler 的等级
    # 如果不修改 Handler，即使 Logger 设为 DEBUG，Handler 如果还是 WARNING，依然不会输出 DEBUG 信息
    for handler in logger.handlers:
        # 根据 Handler 类型来决定是否修改
        if isinstance(handler, logging.StreamHandler): # 控制台
            handler.setLevel(new_level)

        if isinstance(handler, logging.FileHandler): # 文件
            handler.setLevel(new_level)

    # 第三方库的等级
    # third_party_libs = ["transformers", "filelock", "faster_whisper"]
    # for lib_name in third_party_libs:
    #     lib_logger = logging.getLogger(lib_name)
    #     lib_logger.setLevel(new_level)

    print(f"系统日志等级已动态切换为: {new_level_str}")