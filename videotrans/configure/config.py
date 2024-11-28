# -*- coding: utf-8 -*-
import datetime
import json
import locale
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from queue import Queue

MAINWIN=None

# 获取程序执行目录
def _get_executable_path():
    if getattr(sys, 'frozen', False):
        # 如果程序是被“冻结”打包的，使用这个路径
        return Path(sys.executable).parent.as_posix()
    else:
        return Path(__file__).parent.parent.parent.as_posix()

SYS_TMP=Path(tempfile.gettempdir()).as_posix()

# 程序根目录
ROOT_DIR = _get_executable_path()

_root_path = Path(ROOT_DIR)

_tmpname = f'tmp'
# 程序根下临时目录tmp
_temp_path = _root_path / _tmpname
_temp_path.mkdir(parents=True, exist_ok=True)

TEMP_DIR = _temp_path.as_posix()
Path(TEMP_DIR+'/dubbing_cache').mkdir(exist_ok=True)

# 日志目录 logs
_logs_path = _root_path / "logs"
_logs_path.mkdir(parents=True, exist_ok=True)
LOGS_DIR = _logs_path.as_posix()

# 确保同时只能一个 faster-whisper进程在执行
model_process = None

# 模型下载地址
MODELS_DOWNLOAD = {
    "openai": {
        "tiny.en": "https://openaipublic.azureedge.net/main/whisper/models/d3dd57d32accea0b295c96e26691aa14d8822fac7d9d27d5dc00b4ca2826dd03/tiny.en.pt",
        "tiny": "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
        "base.en": "https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt",
        "base": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
        "small.en": "https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt",
        "small": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
        "medium.en": "https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt",
        "medium": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
        "large-v1": "https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt",
        "large-v2": "https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt",
        "large-v3": "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
        "large-v3-turbo": "https://openaipublic.azureedge.net/main/whisper/models/aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a/large-v3-turbo.pt",
    },
    "faster": {
        "tiny": "https://github.com/jianchang512/stt/releases/download/0.0/faster-tiny.7z",
        "tiny.en": "https://github.com/jianchang512/stt/releases/download/0.0/faster-tiny.en.7z",
        "base": "https://github.com/jianchang512/stt/releases/download/0.0/faster-base.7z",
        "base.en": "https://github.com/jianchang512/stt/releases/download/0.0/faster-base.en.7z",

        "small": "https://github.com/jianchang512/stt/releases/download/0.0/faster-small.7z",
        "small.en": "https://github.com/jianchang512/stt/releases/download/0.0/faster-small.en.7z",

        "medium": "https://github.com/jianchang512/stt/releases/download/0.0/faster-medium.7z",
        "medium.en": "https://github.com/jianchang512/stt/releases/download/0.0/faster-medium.en.7z",

        "large-v1": "https://huggingface.co/spaces/mortimerme/s4/resolve/main/faster-large-v1.7z?download=true",

        "large-v2": "https://huggingface.co/spaces/mortimerme/s4/resolve/main/largev2-jieyao-dao-models.7z",

        "large-v3": "https://huggingface.co/spaces/mortimerme/s4/resolve/main/faster-largev3.7z?download=true",
        "large-v3-turbo": "https://github.com/jianchang512/stt/releases/download/0.0/faster-large-v3-turbo.7z",

        "distil-whisper-small.en": "https://github.com/jianchang512/stt/releases/download/0.0/distil-whisper-small.en.7z",

        "distil-whisper-medium.en": "https://github.com/jianchang512/stt/releases/download/0.0/distil-whisper-medium.en.7z",

        "distil-whisper-large-v2": "https://github.com/jianchang512/stt/releases/download/0.0/distil-whisper-large-v2.7z",

        "distil-whisper-large-v3": "https://github.com/jianchang512/stt/releases/download/0.0/distil-whisper-large-v3.7z"
    }
}

###################################

logger = logging.getLogger('VideoTrans')
logger.setLevel(logging.INFO)
# 创建文件处理器，并设置级别G
_file_handler = logging.FileHandler(f'{ROOT_DIR}/logs/{datetime.datetime.now().strftime("%Y%m%d")}.log',
                                    encoding='utf-8')
_file_handler.setLevel(logging.INFO)
# 创建控制台处理器，并设置级别
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.WARNING)
# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_file_handler.setFormatter(formatter)
_console_handler.setFormatter(formatter)
# 添加处理器到日志记录器
logger.addHandler(_file_handler)
logger.addHandler(_console_handler)


# 捕获所有未处理的异常
def _log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # 允许键盘中断（Ctrl+C）退出
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


# 安装自定义异常钩子
sys.excepthook = _log_uncaught_exceptions

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"
# ffmpeg
if sys.platform == 'win32':
    os.environ['PATH'] = ROOT_DIR + f';{ROOT_DIR}/ffmpeg;' + os.environ['PATH']
else:
    os.environ['PATH'] = ROOT_DIR + f':{ROOT_DIR}/ffmpeg:' + os.environ['PATH']


os.environ['QT_API'] = 'pyside6'
os.environ['SOFT_NAME'] = 'pyvideotrans'
os.environ['MODELSCOPE_CACHE'] = ROOT_DIR + "/models"
os.environ['HF_HOME'] = ROOT_DIR + "/models"
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = 'true'
####################################
# 存储所有任务的进度队列，以uuid为键
# 根据uuid将日志进度等信息存入队列，如果不存在则创建
uuid_logs_queue = {}


def push_queue(uuid, jsondata):
    if uuid in stoped_uuid_set:
        return
    if uuid not in uuid_logs_queue:
        uuid_logs_queue[uuid] = Queue()
    try:
        # 暂停时会重设为字符串 stop
        if isinstance(uuid_logs_queue[uuid], Queue):
            uuid_logs_queue[uuid].put_nowait(jsondata)
    except Exception:
        pass


# 存储已停止/暂停的任务
stoped_uuid_set = set()

# 全局消息，不存在uuid，用于控制软件
global_msg = []

# 软件退出
exit_soft = False

# 所有设置窗口和子窗口
child_forms = {}

# info form
INFO_WIN={"data":{},"win":None}

# 存放视频分离为无声视频进度，noextname为key，用于判断某个视频是否是否已预先创建好 novice_mp4, “ing”=需等待，end=成功完成，error=出错了
queue_novice = {}

#################################################

# 主界面完整流程状态标识：开始按钮状态 ing 执行中，stop手动停止 end 正常结束
current_status = "stop"
# 工具箱翻译进行状态,ing进行中，其他停止
box_trans = "stop"
# 工具箱tts状态
box_tts = "stop"
# 工具箱识别状态
box_recogn = 'stop'

# 倒计时数秒
task_countdown = 0

#####################################
# 预先处理队列
prepare_queue = []
# 识别队列
regcon_queue = []
# 翻译队列
trans_queue = []
# 配音队列
dubb_queue = []
# 音视频画面对齐
align_queue = []
# 合成队列
assemb_queue = []


# 执行模式 gui 或 api
exec_mode="gui"

# funasr模型
FUNASR_MODEL=['paraformer-zh','SenseVoiceSmall']
DEEPGRAM_MODEL=[
            "whisper-large",
            "whisper-medium",
            "whisper-small",
            "whisper-base",
            "whisper-tiny",
            "nova-2-general",
            "enhanced-2-general",
            "base-2-general",

        ]


# 支持的视频格式
VIDEO_EXTS = ["mp4", "mkv", "mpeg", "avi", "mov","mts"]
# 支持的音频格式
AUDIO_EXITS = ["mp3", "wav", "aac", "flac", "m4a"]

# 设置当前可用视频编码  libx264 h264_qsv h264_nvenc 等
video_codec = None

#######################################
# openai角色
openaiTTS_rolelist = "alloy,echo,fable,onyx,nova,shimmer"
# 存放 edget-tts 角色列表
edgeTTS_rolelist = None
AzureTTS_rolelist = None

line_roles={}

# 语言
try:
    defaulelang = locale.getdefaultlocale()[0][:2].lower()
except Exception:
    defaulelang = "zh"


# 设置默认高级参数值
def parse_init():
    _defaulthomedir = (Path.home() / 'Videos/pyvideotrans').as_posix()
    try:
        Path(_defaulthomedir).mkdir(parents=True, exist_ok=True)
    except:
        _defaulthomedir=ROOT_DIR+'/hometemp'
        Path(_defaulthomedir).mkdir(parents=True, exist_ok=True)
        
    default = {
        "ai302_models": "gpt-4o-mini,gpt-4o,gpt-4,gpt-4-turbo-preview,ernie-4.0-8k,qwen-max,glm-4,moonshot-v1-8k,"
                        "yi-large,deepseek-chat,doubao-pro-128k,generalv3.5,gemini-1.5-pro,baichuan2-53b,sensechat-5,"
                        "llama3-70b-8192,qwen2-72b-instruct",
        "ai302tts_models": "tts-1,tts-1-hd,azure,doubao",
        "homedir": _defaulthomedir,
        "lang": "",
        "is_queue":False,

        "crf": 23,
        "cuda_qp": False,
        "cuda_decode":False,
        "preset": "fast",
        "ffmpeg_cmd": "",
        "aisendsrt":False,
        "video_codec": 264,
        "openaitts_model": "tts-1,tts-1-hd",
        "openairecognapi_model": "whisper-1",
        "chatgpt_model": "gpt-4o-mini,gpt-4o,gpt-4,gpt-4-turbo,gpt-4-turbo-preview,qwen,moonshot-v1-8k,deepseek-chat",
        "claude_model":"claude-3-5-sonnet-latest,claude-3-5-sonnet-20241022,claude-3-opus-latest,claude-3-sonnet-20240229,claude-3-haiku-20240307",
        "azure_model": "gpt-4o,gpt-4,gpt-35-turbo",
        "localllm_model": "qwen:7b,qwen:1.8b-chat-v1.5-q2_k,moonshot-v1-8k,deepseek-chat",
        "zijiehuoshan_model": "",
        "model_list": "tiny,tiny.en,base,base.en,small,small.en,medium,medium.en,large-v1,large-v2,large-v3,large-v3-turbo,distil-whisper-small.en,distil-whisper-medium.en,distil-whisper-large-v2,distil-whisper-large-v3",
        "audio_rate": 3,
        "video_rate": 20,
        "video_goback":1,
        "remove_silence": False,
        "remove_srt_silence": False,
        "remove_white_ms": 0,
        "force_edit_srt": True,
        "vad": True,

        "threshold":0.5,
        "min_speech_duration_ms":250,
        "max_speech_duration_s":0,
        "min_silence_duration_ms":250,
        "speech_pad_ms":150,


        "overall_maxsecs":12000,

        "rephrase":False,

        "voice_silence": 200,
        "interval_split": 10,
        "bgm_split_time": 300,
        "trans_thread": 20,
        "retries": 2,
        "translation_wait": 0,
        "dubbing_wait": 0,
        "dubbing_thread": 5,
        "countdown_sec": 120,
        "backaudio_volume": 0.8,
        "separate_sec": 600,
        "loop_backaudio": True,
        "cuda_com_type": "float32",  # int8 int8_float16 int8_float32
        "initial_prompt_zh-cn": "在每行末尾添加标点符号，在每个句子末尾添加标点符号。",
        "initial_prompt_zh-tw": "在每行末尾添加標點符號，在每個句子末尾添加標點符號。",
        "initial_prompt_en": "Add punctuation at the end of each line, and punctuation at the end of each sentence.",
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
        "whisper_threads": 4,
        "whisper_worker": 1,
        "beam_size": 5,
        "best_of": 5,
        "temperature": 0,
        "condition_on_previous_text": False,
        "fontsize": 16,
        "fontname": "黑体",
        "fontcolor": "&hffffff",
        "fontbordercolor": "&h000000",
        "subtitle_bottom": 10,
        "cjk_len": 20,
        "other_len": 60,
        "gemini_model": "gemini-1.5-pro,gemini-pro,gemini-1.5-flash",
        "zh_hant_s": True,
        "azure_lines": 150,
        "chattts_voice": "11,12,16,2222,4444,6653,7869,9999,5,13,14,1111,3333,4099,5099,5555,8888,6666,7777",
        "google_trans_newadd": "",
        "proxy":"",
        "refine3":False      
        
    }
    if not os.path.exists(ROOT_DIR + "/videotrans/cfg.json"):        
        with open(ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(default , ensure_ascii=False))
        return default
    try:
        temp_json = json.loads(Path(ROOT_DIR + "/videotrans/cfg.json").read_text(encoding='utf-8'))
    except Exception as e:
        raise
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
            else:
                _settings[key] = value.lower() if value else ""
        if _settings['model_list'].find('large-v3-turbo') == -1:
            _settings['model_list']=_settings['model_list'].replace(',large-v3,',',large-v3,large-v3-turbo,')
        if _settings['gemini_model'].find('gemini') == -1:
            _settings["gemini_model"] = "gemini-pro,gemini-1.5-pro,gemini-1.5-flash"
        default.update(_settings)
        default["ai302tts_models"] = "tts-1,tts-1-hd,azure,doubao"
        if not default['homedir']:
            default['homedir'] = _defaulthomedir
        Path(default['homedir']).mkdir(parents=True, exist_ok=True)
        with open(ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(default,ensure_ascii=False))
        return default


# 高级选项信息
settings = parse_init()
# 家目录
HOME_DIR = settings['homedir']
# 家目录下的临时文件存储目录
TEMP_HOME = settings['homedir'] + f"/{_tmpname}"
Path(TEMP_HOME).mkdir(parents=True, exist_ok=True)

# default language 如果 ini中设置了，则直接使用，否则自动判断
if settings['lang']:
    defaulelang = settings['lang'].lower()

# 语言代码文件是否存在##############################
_lang_path = _root_path / f'videotrans/language/{defaulelang}.json'
if not _lang_path.exists():
    defaulelang = "en"
    _lang_path = _root_path / f'videotrans/language/{defaulelang}.json'

_obj = json.loads(_lang_path.read_text(encoding='utf-8'))
# 交互语言代码
transobj = _obj["translate_language"]
# 软件界面
uilanglist = _obj["ui_lang"]
# 语言代码:语言显示名称
langlist: dict = _obj["language_code_list"]
# 语言显示名称：语言代码
rev_langlist = {code_alias: code for code, code_alias in langlist.items()}
# 语言显示名称 list
langnamelist = list(langlist.values())
# 工具箱语言
box_lang = _obj['toolbox_lang']
proxy=settings.get('proxy','')
#############################################
# openai  faster-whisper 识别模型
WHISPER_MODEL_LIST = re.split(r'[,，]', settings['model_list'])

ChatTTS_voicelist = re.split(r'[,，]', str(settings['chattts_voice']))
_chatgpt_model_list = [it.strip() for it in settings['chatgpt_model'].split(',') if it.strip()]
_claude_model_list = [it.strip() for it in settings['claude_model'].split(',') if it.strip()]
_azure_model_list = [it.strip() for it in settings['azure_model'].split(',') if it.strip()]
_localllm_model_list = [it.strip() for it in settings['localllm_model'].split(',') if it.strip()]
_zijiehuoshan_model_list = [it.strip() for it in settings['zijiehuoshan_model'].split(',') if it.strip()]
if len(_chatgpt_model_list) < 1:
    _chatgpt_model_list = ['']
if len(_claude_model_list) < 1:
    _claude_model_list = ['']
if len(_localllm_model_list) < 1:
    _localllm_model_list = ['']
if len(_zijiehuoshan_model_list) < 1:
    _zijiehuoshan_model_list = ['']


# 设置或获取 config.params
def getset_params(obj=None):
    prompt_zh = """请将<source>中的原文内容按字面意思翻译到{lang}，然后只输出译文，不要添加任何说明或引导词。

**格式要求：**
- 按行翻译原文，并生成该行对应的译文，确保原文行和译文行中的每个单词相互对应。
- 有几行原文，必须生成几行译文。

**内容要求：**
- 翻译必须精简短小，避免长句。
- 如果原文无法翻译，请返回空行，不得添加“无意义语句或不可翻译”等任何提示语。
- 只输出译文即可，禁止输出任何原文。

**执行细节：**
- 如果某行原文很短，在翻译后也仍然要保留该行，不得与上一行或下一行合并。
- 原文换行处字符相对应的译文字符也必须换行。
- 严格按照字面意思翻译，不要解释或回答原文内容。

**最终目标：**
- 提供格式与原文完全一致的高质量翻译结果。

<source>[TEXT]</source>

译文:

"""
    prompt_en = """Please translate the original text in <source> literally to {lang}, and then output only the 
    translated text without adding any notes or leading words. 

**Format Requirements:**
- Translate the original text line by line and generate the translation corresponding to that line, making sure that each word in the original line and the translated line corresponds to each other.
- If there are several lines of original text, several lines of translation must be generated.

**Content requirements:**
- Translations must be concise and short, avoiding long sentences.
- If the original text cannot be translated, please return to an empty line, and do not add any hints such as "meaningless statement or untranslatable", etc. Only the translated text can be output, and it is forbidden to output the translated text.
- Only the translation can be output, and it is forbidden to output any original text.

**Execution details:**
- If a line is very short in the original text, it should be retained after translation, and should not be merged with the previous or next line.
- The characters corresponding to the characters in the translation at the line breaks in the original text must also be line breaks.
- Translate strictly literally, without interpreting or answering the content of the original text.

**End goal:**
- Provide high-quality translations that are formatted exactly like the original.

<source>[TEXT]</source>

Translation:

"""
    prompt_zh_srt="""请将<source>中的srt字幕格式内容翻译到{lang}，然后只输出译文，不要添加任何说明或引导词：

注意以下要求：
1. **只翻译**字幕文本内容，不翻译字幕的行号和时间戳。
2. **必须保证**翻译后的译文格式为有效的 srt字幕。
3. **确保**翻译后的字幕数量和原始字幕完全一致，每一条字幕对应原始字幕中的一条。
4. **保持时间戳的原样**，只翻译幕文本内容。
5. 如果遇到无法翻译的情况，直接将原文本内容返回，不要报错，不要道歉。

以下是需要翻译的 srt 字幕内容：

<source>[TEXT]</source>

译文:
"""
    prompt_en_srt="""Please translate the content of srt subtitle format in <source> to {lang}, and then output only the translated text without adding any description or guide words:

Note the following requirements:
1. **Translate **subtitle text content only, do not translate subtitle line numbers and timestamps.
2. **Must ensure that **the translated translation format is a valid srt subtitle.
3. **Must ensure that the number of **translated subtitles is exactly the same as the original subtitles, and that each subtitle corresponds to one of the original subtitles.
4. **Keep the timestamps as they are** and translate only the content of the subtitles.
5. If you can't translate the subtitle, you can return the original text directly without reporting any error.

The following is the content of the srt subtitle to be translated:

<source>[TEXT]</source>

Translation:"""
    # 保存到json
    if obj is not None:
        with open(ROOT_DIR + "/videotrans/params.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False))
        return obj
    #获取
    default = {
        "last_opendir": HOME_DIR,
        "cuda": False,

        "line_roles":{},

        "only_video": False,
        "is_separate": False,
        "remove_noise":True,

        "target_dir": "",

        "source_language": "en",
        "target_language": "zh-cn",
        "subtitle_language": "chi",
        "translate_type": 0,
        "subtitle_type": 0,  # embed soft

        "listen_text_zh-cn": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
        "listen_text_zh-tw": "你好啊，我親愛的朋友，希望你的每一天都是美好愉快的！",
        "listen_text_en": "Hello, my dear friend. I hope your every day is beautiful and enjoyable!",
        "listen_text_fr": "Bonjour mon cher ami. J'espère que votre quotidien est beau et agréable !",
        "listen_text_de": "Hallo mein lieber Freund. Ich hoffe, dass Ihr Tag schön und angenehm ist!",
        "listen_text_ja": "こんにちは私の親愛なる友人。 あなたの毎日が美しく楽しいものでありますように！",
        "listen_text_ko": "안녕, 내 사랑하는 친구. 당신의 매일이 아름답고 즐겁기를 바랍니다!",
        "listen_text_ru": "Привет, мой дорогой друг. Желаю, чтобы каждый твой день был прекрасен и приятен!",
        "listen_text_es": "Hola mi querido amigo. ¡Espero que cada día sea hermoso y agradable!",
        "listen_text_th": "สวัสดีเพื่อนรัก. ฉันหวังว่าทุกวันของคุณจะสวยงามและสนุกสนาน!",
        "listen_text_it": "Ciao caro amico mio. Spero che ogni tuo giorno sia bello e divertente!",
        "listen_text_pt": "Olá meu querido amigo. Espero que todos os seus dias sejam lindos e agradáveis!",
        "listen_text_vi": "Xin chào người bạn thân yêu của tôi. Tôi hy vọng mỗi ngày của bạn đều đẹp và thú vị!",
        "listen_text_ar": "مرحبا صديقي العزيز. أتمنى أن يكون كل يوم جميلاً وممتعًا!",
        "listen_text_tr": "Merhaba sevgili arkadaşım. Umarım her gününüz güzel ve keyifli geçer!",
        "listen_text_hi": "नमस्ते मेरे प्यारे दोस्त। मुझे आशा है कि आपका हर दिन सुंदर और आनंददायक हो!!",
        "listen_text_hu": "Helló kedves barátom. Remélem minden napod szép és kellemes!",
        "listen_text_uk": "Привіт, мій дорогий друже, сподіваюся, ти щодня прекрасна!",
        "listen_text_id": "Halo, temanku, semoga kamu cantik setiap hari!",
        "listen_text_ms": "Helo, sahabat saya, saya harap anda cantik setiap hari!",
        "listen_text_kk": "Сәлеметсіз бе, менің қымбатты досым, сендер күн сайын әдемісің деп үміттенемін!",
        "listen_text_cs": "Ahoj, můj drahý příteli, doufám, že jsi každý den krásná!",
        "listen_text_pl": "Witam, mój drogi przyjacielu, mam nadzieję, że jesteś piękna każdego dnia!",
        "listen_text_nl": "Hallo mijn lieve vriend, ik hoop dat elke dag goed en fijn voor je is!!",
        "listen_text_sv": "Hej min kära vän, jag hoppas att varje dag är en bra och trevlig dag för dig!",
        
        "listen_text_he": "שלום, ידידי היקר, אני מקווה שכל יום בחייך יהיה נפלא ומאושר!",
        "listen_text_bn": "হ্যালো, আমার প্রিয় বন্ধু, আমি আশা করি আপনার জীবনের প্রতিটি দিন চমৎকার এবং সুখী হোক!",

        "tts_type": 0,  # 所选的tts顺序
        "split_type": "all",
        "model_name": "medium" if Path(ROOT_DIR+"/models/models--Systran--faster-whisper-medium/snapshots").is_dir() else "tiny",  # 模型名
        "recogn_type": 0,  # 语音识别方式，数字代表显示顺序

        "voice_autorate": False,
        "voice_role": "No",
        "voice_rate": "0",
        "video_autorate": False,
        "append_video": True,

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
        
        "ali_id":"",
        "ali_key":"",
    
        "baidu_appid": "",
        "baidu_miyue": "",

        "chatgpt_api": "",
        "chatgpt_key": "",
        "chatgpt_model": _chatgpt_model_list[0],
        "chatgpt_template": "",

        "claude_api": "",
        "claude_key": "",
        "claude_model": _claude_model_list[0],
        "claude_template": "",

        "azure_api": "",
        "azure_key": "",
        "azure_version": "2024-06-01",
        "azure_model": _azure_model_list[0],
        "azure_template": "",

        "gemini_key": "",
        "gemini_model": "gemini-1.5-pro",
        "gemini_template": "",
        "gemini_cut_audio":False,
        "gemini_min_silence_duration_ms":200,
        "gemini_speech_pad_ms":100, 
        "gemini_onset":0.5,
        "gemini_offset":0.35,
        "gemini_srtprompt":"请将我上传的音频转录为符合SRT格式的字幕，请注意时间戳要精确到字级别，转录后返回合法的SRT字幕内容，禁止附带任何提示说明或解释,也不要添加任何辅助标记、html标记，每条字幕最多2行，时长在1秒到12s之间" if defaulelang=='zh' else "Please transcribe the audio I uploaded into subtitles in SRT format. Please note that the timestamp must be accurate to the level of a word, and return the legal SRT subtitle content after the transcription. Do not add any auxiliary marks or HTML tags, and each subtitle can have up to 2 lines, and the duration should be between 1 second and 12 seconds.",
        
        "gemini_srtprompt_cut":'Please transcribe the audio that was sent to you into text, then return the transcribed text without any explanations, hints, instructions or any other superfluous information attached to the returned text.',


        "localllm_api": "",
        "localllm_key": "",
        "localllm_model": _localllm_model_list[0],
        "localllm_template": "",

        "zijiehuoshan_key": "",
        "zijiehuoshan_model": _zijiehuoshan_model_list[0],
        "zijiehuoshan_template": "",

        "ai302_key": "",
        "ai302_model": "",
        "ai302_template": "",

        "trans_api_url": "",
        "trans_secret": "",

        "coquitts_role": "",
        "coquitts_key": "",

        "elevenlabstts_role": [],
        "elevenlabstts_key": "",

        "openaitts_api": "",
        "openaitts_key": "",
        "openaitts_model": "tts-1",
        "openaitts_role": openaiTTS_rolelist,

        "openairecognapi_url": "",
        "openairecognapi_key": "",
        "openairecognapi_prompt": "",
        "openairecognapi_model": "whisper-1",

        "clone_api": "",
        "clone_voicelist": ["clone"],

        "zh_recogn_api": "",

        "recognapi_url": "",
        "recognapi_key": "",
        "stt_url": "",
        "stt_model": "tiny",

        "sense_url":"",

        "ttsapi_url": "",
        "ttsapi_voice_role": "",
        "ttsapi_extra": "pyvideotrans",

        "ai302tts_key": "",
        "ai302tts_model": "",
        "ai302tts_role": openaiTTS_rolelist,

        "azure_speech_region": "",
        "azure_speech_key": "",

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
        "f5tts_role": "",

        "doubao_appid": "",
        "doubao_access": "",

        "volcenginetts_appid":"",
        "volcenginetts_access":"",
        "volcenginetts_cluster":"",

        "chattts_api": "",

        "app_mode": "biaozhun",

        "stt_source_language":0,
        "stt_recogn_type":0,
        "stt_model_name":"",
        "stt_remove_noise":True,

        "deepgram_apikey":"",
        "deepgram_utt":200,

        "trans_translate_type":0,
        "trans_source_language":0,
        "trans_target_language":1,
        "trans_out_format":0,

        "dubb_source_language":0,
        "dubb_tts_type":0,
        "dubb_role":0,
        "dubb_out_format":0,
        "dubb_voice_autorate":False,
        "dubb_hecheng_rate":0,
        "dubb_pitch_rate":0,
        "dubb_volume_rate":0,


    }
    # 创建默认提示词文件
    if Path(ROOT_DIR+'/videotrans/prompts/srt').exists():
        Path(ROOT_DIR+'/videotrans/prompts/srt').mkdir(parents=True,exist_ok=True)
    def _create_default_promot():
        prompt_langcode = '' if defaulelang == "zh" else "-en"
        _root_path = Path(ROOT_DIR)
        for ainame in ['chatgpt','azure','gemini','localllm','ai302','zijie']:
            chatgpt_path = _root_path / f'videotrans/{ainame}{prompt_langcode}.txt'
            if not chatgpt_path.exists():
                with chatgpt_path.open('w',encoding='utf-8') as f:
                    f.write(prompt_zh if defaulelang=='zh' else prompt_en)
            chatgpt_path = _root_path / f'videotrans/prompts/srt/{ainame}{prompt_langcode}.txt'
            if not chatgpt_path.exists():
                with chatgpt_path.open('w', encoding='utf-8') as f:
                    f.write(prompt_zh_srt if defaulelang=='zh' else prompt_en_srt)
    try:
        _create_default_promot()
        if os.path.exists(ROOT_DIR + "/videotrans/params.json"):
            default.update(json.loads(Path(ROOT_DIR + "/videotrans/params.json").read_text(encoding='utf-8')))
        else:
            with open(ROOT_DIR + "/videotrans/params.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(default, ensure_ascii=False))
    except Exception:
        pass
    return default

# api key 翻译配置等信息，每次执行任务均有变化
params = getset_params()


explames={
    "zh-cn":"""1
00:00:01,950 --> 00:00:04,410
古老星系中发现了有机分子.

2
00:00:04,880 --> 00:00:06,780
我们离第三类接触还有多远。

3
00:00:07,260 --> 00:00:09,880
韦伯正式展开拍摄任务已经届满周年。""",
    "zh-tw":"""1
00:00:01,950 --> 00:00:04,410
在古代星系中發現的有機分子。

2
00:00:04,880 --> 00:00:06,780
我們距離 III 型接觸還有多遠。

3
00:00:07,260 --> 00:00:09,880
韋伯正式啟動拍攝任務的周年紀念日已過。""",
    "en":"""1
00:00:01,950 --> 00:00:04,410
Organic Molecules Found in Ancient Galaxies.

2
00:00:04,880 --> 00:00:06,780
How far we are from Type III contact.

3
00:00:07,260 --> 00:00:09,880
The anniversary of Webb's official launch of his filming mission has expired.""",
    "ja":"""1
00:00:01,950 --> 00:00:04,410
古代の銀河で発見された有機分子。

2
00:00:04,880 --> 00:00:06,780
未知との遭遇からどれくらい離れていますか?

3
00:00:07,260 --> 00:00:09,880
ウェーバーが正式に撮影を開始してから記念日となった。""",
    "ko":"""1
00:00:01,950 --> 00:00:04,410
고대 은하계에서 발견된 유기분자.

2
00:00:04,880 --> 00:00:06,780
우리는 제3종 근접 조우로부터 얼마나 멀리 떨어져 있나요?

3
00:00:07,260 --> 00:00:09,880
웨버가 정식으로 촬영을 시작한 지 1주년이 되는 날이다.""",
    "ru":"""1
00:00:01,950 --> 00:00:04,410
Органические молекулы обнаружены в древних галактиках.

2
00:00:04,880 --> 00:00:06,780
Насколько мы далеки от близких контактов третьего рода?

3
00:00:07,260 --> 00:00:09,880
Это была годовщина с тех пор, как Вебер официально начал съемки.""",
    "es":"""1
00:00:01,950 --> 00:00:04,410
Moléculas orgánicas descubiertas en galaxias antiguas.

2
00:00:04,880 --> 00:00:06,780
¿Qué tan lejos estamos de Encuentros Cercanos del Tercer Tipo?

3
00:00:07,260 --> 00:00:09,880
Ha sido el aniversario desde que Weber comenzó oficialmente a filmar.""",
    "pt":"""1
00:00:01.950 --> 00:00:04.410
Moléculas orgânicas descobertas em galáxias antigas.

2
00:00:04.880 --> 00:00:06.780
A que distância estamos dos Encontros Imediatos de Terceiro Grau?

3
00:00:07.260 --> 00:00:09.880
Já faz anos desde que Weber começou oficialmente a filmar.""",
    "it":"""1
00:00:01,950 --> 00:00:04,410
Molecole organiche scoperte nelle galassie antiche.

2
00:00:04,880 --> 00:00:06,780
Quanto siamo lontani dagli Incontri Ravvicinati del Terzo Tipo?

3
00:00:07,260 --> 00:00:09,880
È l'anniversario da quando Weber ha iniziato ufficialmente le riprese.""",
    "fr":"""1
00:00:01,950 --> 00:00:04,410
Molécules organiques découvertes dans les galaxies anciennes.

2
00:00:04,880 --> 00:00:06,780
Où sommes-nous des rencontres rapprochées du troisième type ?

3
00:00:07,260 --> 00:00:09,880
C'est l'anniversaire du début officiel du tournage de Weber.""",
    "de":"""1
00:00:01.950 --> 00:00:04.410
Organische Moleküle in alten Galaxien entdeckt.

2
00:00:04.880 --> 00:00:06.780
Wie weit sind wir von Unheimlichen Begegnungen der Dritten Art entfernt?

3
00:00:07.260 --> 00:00:09.880
Es ist der Jahrestag, seit Weber offiziell mit den Dreharbeiten begonnen hat.""",
    "th":"""1
00:00:01,950 --> 00:00:04,410
โมเลกุลอินทรีย์ที่ค้นพบในกาแลคซีโบราณ

2
00:00:04,880 --> 00:00:06,780
เราอยู่ห่างจากการเผชิญหน้าอย่างใกล้ชิดของประเภทที่สามมากแค่ไหน?

3
00:00:07,260 --> 00:00:09,880
ถือเป็นวันครบรอบที่เวเบอร์เริ่มถ่ายทำอย่างเป็นทางการ""",
    "tr":"""1
00:00:01,950 --> 00:00:04,410
Antik galaksilerde keşfedilen organik moleküller.

2
00:00:04,880 --> 00:00:06,780
Üçüncü Türden Yakın Karşılaşmalardan ne kadar uzaktayız?

3
00:00:07,260 --> 00:00:09,880
Weber'in resmi olarak çekime başlamasının yıldönümü oldu.""",
    "vi":"""1
00:00:01,950 --> 00:00:04,410
Các phân tử hữu cơ được phát hiện trong các thiên hà cổ đại

2
00:00:04,880 --> 00:00:06,780
Chúng ta còn cách Close Encounters of the Third Kind bao xa?

3
00:00:07,260 --> 00:00:09,880
Đã là ngày kỷ niệm Weber chính thức bắt đầu quay phim.""",
    "ar":"""1
00:00:01,950 --> 00:00:04,410
الجزيئات العضوية المكتشفة في المجرات القديمة

2
00:00:04,880 --> 00:00:06,780
إلى أي مدى نحن بعيدون عن اللقاءات القريبة من النوع الثالث؟

3
00:00:07,260 --> 00:00:09,880
لقد كانت الذكرى السنوية منذ أن بدأ ويبر التصوير رسميًا.""",
    "hu":"""1
00:00:01,950 --> 00:00:04,410
Az ősi galaxisokban felfedezett szerves molekulák.

2
00:00:04,880 --> 00:00:06,780
Milyen messze vagyunk a Harmadik típusú közeli találkozásoktól?

3
00:00:07,260 --> 00:00:09,880
Eltelt az évforduló, hogy Weber hivatalosan is elkezdte a forgatást.""",
    "hi":"""1
00:00:01,950 --> 00:00:04,410
प्राचीन आकाशगंगाओं में कार्बनिक अणुओं की खोज की गई।

2
00:00:04,880 --> 00:00:06,780
हम तीसरी तरह की करीबी मुठभेड़ों से कितनी दूर हैं?

3
00:00:07,260 --> 00:00:09,880
वेबर द्वारा आधिकारिक तौर पर फिल्मांकन शुरू करने की यह सालगिरह है।""",
    "id":"""1
00:00:01,950 --> 00:00:04,410
Molekul organik ditemukan di galaksi kuno.

2
00:00:04,880 --> 00:00:06,780
Seberapa jauh kita dari Close Encounters of the Third Kind?

3
00:00:07,260 --> 00:00:09,880
Ini adalah hari jadi sejak Weber secara resmi mulai syuting.""",
    "uk":"""1
00:00:01,950 --> 00:00:04,410
Органічні молекули, виявлені в стародавніх галактиках.

2
00:00:04,880 --> 00:00:06,780
Наскільки ми далекі від близьких зустрічей третього роду?

3
00:00:07,260 --> 00:00:09,880
Це був ювілей, відколи Вебер офіційно почав зніматися.""",
    "ms":"""1
00:00:01,950 --> 00:00:04,410
Molekul organik ditemui dalam galaksi purba.

2
00:00:04,880 --> 00:00:06,780
Berapa jauhkah kita dari Pertemuan Dekat Jenis Ketiga?

3
00:00:07,260 --> 00:00:09,880
Ia telah menjadi ulang tahun sejak Weber secara rasmi memulakan penggambaran.""",
    "kk":"""1
00:00:01,950 --> 00:00:04,410
Ежелгі галактикаларда табылған органикалық молекулалар.

2
00:00:04,880 --> 00:00:06,780
Үшінші түрдегі жақын кездесулерден қаншалықты алыспыз?

3
00:00:07,260 --> 00:00:09,880
Вебер ресми түрде түсірілімді бастағанына бір мерейтой болды.""",
    "cs":"""1
00:00:01,950 --> 00:00:04,410
Organické molekuly objevené ve starověkých galaxiích.

2
00:00:04,880 --> 00:00:06,780
Jak daleko jsme od Blízkých setkání třetího druhu?

3
00:00:07,260 --> 00:00:09,880
Je to výročí, kdy Weber oficiálně začal natáčet.""",
    "pl":"""1
00:00:01,950 --> 00:00:04,410
Cząsteczki organiczne odkryte w starożytnych galaktykach.

2
00:00:04,880 --> 00:00:06,780
Jak daleko jesteśmy od Bliskich Spotkań Trzeciego Stopnia?

3
00:00:07,260 --> 00:00:09,880
Minęła rocznica oficjalnego rozpoczęcia zdjęć przez Webera.""",
    "nl":"""1
00:00:01,950 --> 00:00:04,410
Organische moleculen ontdekt in oude sterrenstelsels.

2
00:00:04,880 --> 00:00:06,780
Hoe ver zijn we verwijderd van Close Encounters of the Third Kind?

3
00:00:07,260 --> 00:00:09,880
Het is de verjaardag sinds Weber officieel begon met filmen.""",
    "sv":"""1
00:00:01,950 --> 00:00:04,410
Organiska molekyler upptäckta i antika galaxer.

2
00:00:04,880 --> 00:00:06,780
Hur långt är vi från Close Encounters of the Third Kind?

3
00:00:07,260 --> 00:00:09,880
Det är jubileum sedan Weber officiellt började filma.""",
    "he":"""1
00:00:01,950 --> 00:00:04,410
מולקולות אורגניות שהתגלו בגלקסיות עתיקות.

2
00:00:04,880 --> 00:00:06,780
כמה אנחנו רחוקים ממפגשים קרובים מהסוג השלישי?

3
00:00:07,260 --> 00:00:09,880
זה היה יום השנה מאז ובר החל לצלם באופן רשמי.""",
    "bn":"""1
00:00:01,950 --> 00:00:04,410
প্রাচীন ছায়াপথে আবিষ্কৃত জৈব অণু।

2
00:00:04,880 --> 00:00:06,780
আমরা তৃতীয় ধরণের ক্লোজ এনকাউন্টার থেকে কত দূরে?

3
00:00:07,260 --> 00:00:09,880
ওয়েবার আনুষ্ঠানিকভাবে চিত্রগ্রহণ শুরু করার পর থেকে এটি বার্ষিকী।"""
}


ELEVENLABS_CLONE=['zh','en','fr','de','hi','pt','es','ja','ko','ar','ru','id','it','tr','pl','sv','ms','uk','cs']