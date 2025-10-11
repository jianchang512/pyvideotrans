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

IS_FROZEN = True if getattr(sys, 'frozen', False) else False


# 获取程序执行目录
def _get_executable_path():
    if IS_FROZEN:
        # 如果程序是被"冻结"打包的，使用这个路径
        os.environ['TQDM_DISABLE'] = '1'
        return Path(sys.executable).parent.as_posix()
    else:
        return Path(__file__).parent.parent.parent.as_posix()


_tmpname = f'tmp{os.getpid()}'

SYS_TMP = Path(tempfile.gettempdir()).as_posix()
# 程序根目录
ROOT_DIR = _get_executable_path()
# 程序根下临时目录tmp
TEMP_DIR = f'{ROOT_DIR}/{_tmpname}'
# 家目录
HOME_DIR = ROOT_DIR + "/output"

Path(TEMP_DIR + '/dubbing_cache').mkdir(exist_ok=True, parents=True)
Path(TEMP_DIR + '/translate_cache').mkdir(exist_ok=True, parents=True)
# 日志目录 logs
Path(f"{ROOT_DIR}/logs").mkdir(parents=True, exist_ok=True)

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

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"
# ffmpeg
if sys.platform == 'win32':
    os.environ['PATH'] = ROOT_DIR + f';{ROOT_DIR}/ffmpeg;' + os.environ['PATH']
    if IS_FROZEN:
        os.environ['PATH'] = os.environ['PATH'] + f';{ROOT_DIR}/_internal/torch/lib'

os.environ['QT_API'] = 'pyside6'
os.environ['SOFT_NAME'] = 'pyvideotrans'
os.environ['MODELSCOPE_CACHE'] = ROOT_DIR + "/models"
os.environ['HF_HOME'] = ROOT_DIR + "/models"
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = 'true'
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = 'true'
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = "1200"

# 语言
# _env_lang =   # 新增：读取环境变量
if _env_lang := os.environ.get('PYVIDEOTRANS_LANG'):  # 新增：如果环境变量存在，则使用它
    defaulelang = _env_lang
else:  # 原有逻辑
    try:
        defaulelang = locale.getdefaultlocale()[0][:2].lower()
    except Exception:
        defaulelang = "zh"

# 中文系统，设置镜像
if defaulelang == 'zh' and not Path(ROOT_DIR + "/huggingface.lock").exists():
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    os.environ["HF_HUB_DISABLE_XET"] = "1"

####################################
# 存储已停止/暂停的任务 uuid
stoped_uuid_set = set()
# 存储所有任务的进度队列，以uuid为键
# 根据uuid将日志进度等信息存入队列，如果不存在则创建
uuid_logs_queue = {}


def push_queue(uuid, jsondata):
    if exit_soft or uuid in stoped_uuid_set:
        return
    if uuid not in uuid_logs_queue:
        uuid_logs_queue[uuid] = Queue()
    try:
        # 暂停时会重设为字符串 stop
        if isinstance(uuid_logs_queue[uuid], Queue):
            uuid_logs_queue[uuid].put_nowait(jsondata)
    except Exception:
        pass


# 确保同时只能一个 faster-whisper进程在执行
model_process = None

# 全局消息，不存在uuid，用于控制软件
global_msg = []
# 软件退出
exit_soft = False
# 所有设置窗口和子窗口
child_forms = {}
# info form
INFO_WIN = {"data": {}, "win": None}

# 存放视频分离为无声视频进度，noextname为key，用于判断某个视频是否是否已预先创建好 novice_mp4, "ing"=需等待，end=成功完成，error=出错了
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
# 最终完成结束任务队列
taskdone_queue = []

# 执行模式 gui 或 api
exec_mode = "gui"
# funasr模型
FUNASR_MODEL = ['paraformer-zh', 'SenseVoiceSmall']

DEEPGRAM_MODEL = [
    "nova-3",
    "whisper-large",
    "whisper-medium",
    "whisper-small",
    "whisper-base",
    "whisper-tiny",
    "nova-2",
    "enhanced",
    "base",
]
# 支持的视频格式
VIDEO_EXTS = ["mp4", "mkv", "mpeg", "avi", "mov", "mts", "webm", "ogg", "ts","flv"]
# 支持的音频格式
AUDIO_EXITS = ["mp3", "wav", "aac", "flac", "m4a"]
# 设置当前可用视频编码  libx264 h264_qsv h264_nvenc 等
video_codec = None
codec_cache = {}
# 字幕按行赋予角色
line_roles = {}
# 字幕多角色配音
dubbing_role = {}
#######################################
DEFAULT_GEMINI_MODEL = "gemini-2.5-pro,gemini-2.5-flash,gemini-2.5-flash-preview-04-17,gemini-2.5-flash-preview-05-20,gemini-2.5-pro-preview-05-06,gemini-2.0-flash,gemini-2.0-flash-lite,gemini-1.5-flash,gemini-1.5-pro,gemini-1.5-flash-8b"
ELEVENLABS_CLONE = ['zh', 'en', 'fr', 'de', 'hi', 'pt', 'es', 'ja', 'ko', 'ar', 'ru', 'id', 'it', 'tr', 'pl', 'sv',
                    'ms', 'uk', 'cs', 'tl']
OPENAITTS_ROLES = "alloy,ash,ballad,coral,echo,fable,onyx,nova,sage,shimmer,verse"
QWEN_TTS_ROLES = 'Cherry,Serena,Ethan,Chelsie,Sunny,Jada,Dylan'
QWEN3_TTS_ROLES = 'Cherry,Ethan,Nofish,Jennifer,Ryan,Katerina,Elias,Jada,Dylan,Sunny,li,Marcus,Roy,Peter,Rocky,Kiki,Eric'


# 设置默认高级参数值
def parse_init(update_data=None):
    if update_data:
        with  open(ROOT_DIR + "/videotrans/cfg.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(update_data, ensure_ascii=False))
        return update_data
    _defaulthomedir = HOME_DIR
    default = {
        "homedir": _defaulthomedir,
        "lang": "",
        "Faster_Whisper_XXL": "",
        "crf": 25,
        "cuda_decode": False,
        "preset": "fast",
        "ffmpeg_cmd": "",
        "aisendsrt": False,
        "dont_notify": False,
        "video_codec": 264,

        "ai302_models": "gpt-4o-mini,gpt-4o,qwen-max,glm-4,yi-large,deepseek-chat,doubao-pro-128k,gemini-2.0-flash",
        'qwenmt_model': "qwen-mt-turbo,qwen-mt-plus,qwen3-asr-flash,qwen-plus,qwen-turbo,qwen-plus-latest,qwen-turbo-latest",
        "openaitts_model": "tts-1,tts-1-hd,gpt-4o-mini-tts",
        "openairecognapi_model": "whisper-1,gpt-4o-transcribe,gpt-4o-mini-transcribe",
        "chatgpt_model": "gpt-4.1,gpt-4o-mini,gpt-4o,gpt-4,gpt-4-turbo,gpt-4.5,o1,o1-pro,o3-mini,moonshot-v1-8k,deepseek-chat,deepseek-reasoner",
        "claude_model": "claude-3-5-sonnet-latest,claude-3-7-sonnet-latest,claude-3-5-haiku-latest",
        "azure_model": "gpt-4.1,gpt-4o,gpt-4o-mini,gpt-4,gpt-4.5-preview,o3-mini,o1,o1-mini",
        "localllm_model": "qwen:7b,moonshot-v1-8k,deepseek-chat",
        "zhipuai_model": "glm-4-flash",
        "deepseek_model": "deepseek-chat,deepseek-reasoner",
        "openrouter_model": "moonshotai/kimi-k2:free,tngtech/deepseek-r1t2-chimera:free,deepseek/deepseek-r1-0528:free",
        "guiji_model": "Qwen/Qwen3-8B,Qwen/Qwen2.5-7B-Instruct,Qwen/Qwen2-7B-Instruct",
        "zijiehuoshan_model": "",
        "model_list": "tiny,tiny.en,base,base.en,small,small.en,medium,medium.en,large-v1,large-v2,large-v3,large-v3-turbo,distil-small.en,distil-medium.en,distil-large-v2,distil-large-v3",

        "remove_silence": False,
        "vad": True,
        "threshold": 0.45,
        "min_speech_duration_ms": 0,
        "max_speech_duration_s": 5,
        "min_silence_duration_ms": 140,
        "speech_pad_ms": 0,
        "rephrase": False,
        "rephrase_local": False,
        "voice_silence": 140,
        "interval_split": 5,
        "bgm_split_time": 300,
        "trans_thread": 20,
        "aitrans_thread": 50,
        "translation_wait": 0,
        "dubbing_wait": 1,
        "dubbing_thread": 6,
        "save_segment_audio": False,
        "countdown_sec": 90,
        "backaudio_volume": 0.8,
        "separate_sec": 600,
        "loop_backaudio": True,
        "cuda_com_type": "default",  # int8 int8_float16 int8_float32
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
        "initial_prompt_he": "",
        "initial_prompt_bn": "",
        "initial_prompt_fil": "",
        "initial_prompt_fa": "",
        "initial_prompt_ur": "",
        "initial_prompt_yue": "",
        "beam_size": 5,
        "best_of": 5,
        "condition_on_previous_text": True,
        "fontsize": 14,
        "fontname": "黑体",
        "fontcolor": "&hffffff",
        "fontbordercolor": "&h000000",
        "backgroundcolor": "&h000000",
        "subtitle_position": 2,  # 对应 1到9 位置

        "qwentts_role": QWEN3_TTS_ROLES,
        "qwentts_models": 'qwen3-tts-flash,qwen-tts-latest,qwen-tts',

        "marginV": 10,
        "marginL": 0,
        "marginR": 0,
        "outline": 1,
        "shadow": 1,
        "borderStyle": 1,  # 1或3， 轮廓描边风格对应 BorderStyle=1， 背景色块风格对应 BorderStyle=3

        "cjk_len": 15,
        "other_len": 60,
        "gemini_model": DEFAULT_GEMINI_MODEL,
        "llm_chunk_size": 500,
        "llm_ai_type": "openai",
        "gemini_recogn_chunk": 50,
        "zh_hant_s": True,
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
        default.update(_settings)
        # 旧版本模型写法 distil-whisper- 改为 distil-
        default['model_list'] = default['model_list'].replace('distil-whisper-', 'distil-')
        with open(ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(default, ensure_ascii=False))
        return default


# 高级选项信息
settings = parse_init()
# 根据已保存的配置更新 HOME_DIR
HOME_DIR = settings.get('homedir', HOME_DIR)

# 获取已有的语言文件
if not _env_lang:
    _env_lang= settings.get('lang','').lower().strip()
defaulelang=_env_lang if _env_lang else defaulelang
SUPPORT_LANG = {}
for it in Path(f'{ROOT_DIR}/videotrans/language').glob('*.json'):
    if it.stat().st_size > 0:
        SUPPORT_LANG[it.stem] = it.as_posix()
if defaulelang not in SUPPORT_LANG:
    defaulelang = "en"


# 家目录下的临时文件存储目录
TEMP_HOME = f"{HOME_DIR}/{_tmpname}"
Path(TEMP_HOME).mkdir(parents=True, exist_ok=True)

# 代理地址
proxy = settings.get('proxy', '')

#############################################

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
        "paraformer_spk": False,
        "line_roles": {},
        "only_video": False,
        "is_separate": False,
        "remove_noise": False,
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
        "listen_text_fil": "Hello, kaibigan ko",
        "listen_text_fa": "سلام دوستای گلم امیدوارم هر روز از زندگیتون عالی و شاد باشه.",
        "listen_text_ur": "ہیلو پیارے دوست، مجھے امید ہے کہ آپ آج خوش ہوں گے۔",
        "listen_text_yue": "你好啊親愛嘅朋友，希望你今日好開心",
        "tts_type": 0,  # 所选的tts顺序
        "split_type": "all",
        "model_name": "large-v3-turbo",  # 模型名
        "recogn_type": 0,  # 语音识别方式，数字代表显示顺序
        "voice_autorate": True,
        "voice_role": "No",
        "voice_rate": "0",
        "video_autorate": True,
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
        "chatgpt_temperature": "1.0",
        "chatgpt_top_p": "1.0",
        "claude_api": "",
        "claude_key": "",
        "claude_model": _claude_model_list[0],
        "azure_api": "",
        "azure_key": "",
        "azure_version": "2025-04-01-preview",
        "azure_model": _azure_model_list[0],
        "gemini_key": "",
        "gemini_model": "gemini-2.5-flash",
        "gemini_maxtoken":18192,
        "gemini_ttsrole": "Zephyr,Puck,Charon,Kore,Fenrir,Leda,Orus,Aoede,Callirrhoe,Autonoe,Enceladus,Iapetus,Umbriel,Algieba,Despina,Erinome,Algenib,Rasalgethi,Laomedeia,Achernar,Alnilam,Schedar,Gacrux,Pulcherrima,Achird,Zubenelgenubi,Vindemiatrix,Sadachbia,Sadaltager,Sulafat",
        "gemini_ttsstyle": "",
        "gemini_ttsmodel": "gemini-2.5-flash-preview-tts",
        "localllm_api": "",
        "localllm_key": "",
        "localllm_model": _localllm_model_list[0],
        "localllm_max_token": "4096",
        "localllm_temperature": "1.0",
        "localllm_top_p": "1.0",
        "zhipu_key": "",
        "zhipu_model": _zhipuai_model_list[0],
        "zhipu_max_token": "4096",
        "guiji_key": "",
        "guiji_model": _guiji_model_list[0],
        "guiji_max_token": "4096",
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

        "ai302_key": "",
        "ai302_model": "",
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
        "openaitts_role": OPENAITTS_ROLES,
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
        "chattts_api": "",
        "app_mode": "biaozhun",
        "stt_source_language": 0,
        "stt_recogn_type": 0,
        "stt_model_name": "",
        "stt_remove_noise": False,

        "subtitlecover_outformat": "srt",

        "deepgram_apikey": "",
        "deepgram_utt": 200,
        "trans_translate_type": 0,
        "trans_source_language": 0,
        "trans_target_language": 1,
        "trans_out_format": 0,
        "dubb_source_language": 0,
        "dubb_tts_type": 0,
        "dubb_role": 0,
        "dubb_out_format": 0,
        "dubb_voice_autorate": True,
        "dubb_hecheng_rate": 0,
        "dubb_pitch_rate": 0,
        "dubb_volume_rate": 0,
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
settings['qwentts_role'] = QWEN3_TTS_ROLES if params.get("qwentts_model", '').startswith(
    'qwen3-tts') else QWEN_TTS_ROLES
# 更新 settings配置
parse_init(settings)

# 硬字幕字幕位置
POSTION_ASS_KV = {
    7: "left-top",
    8: "top",
    9: "right-top",
    4: "left-center",
    5: "center",
    6: "right-center",
    1: "left-bottom",
    2: "bottom",
    3: "right-bottom"
}
POSTION_ASS_INDEX = list(POSTION_ASS_KV.keys())
POSTION_ASS_VK = {v: k for k, v in POSTION_ASS_KV.items()}

############ F5-TTS 面板多渠道共用
# F5-TTS 设置窗口 5个类型通用
F5_TTS_WINFORM_NAMES = ['F5-TTS', 'Spark-TTS', 'Index-TTS', 'Dia-TTS', 'VoxCPM-TTS']


#  F5-TTS 渠道名字获取对应url
def get_url_byf5tts(name):
    params = getset_params()
    TTS_URL_LIST = {
        F5_TTS_WINFORM_NAMES[0]: params.get('f5tts_url', ''),
        F5_TTS_WINFORM_NAMES[1]: params.get('sparktts_url', ''),
        F5_TTS_WINFORM_NAMES[2]: params.get('indextts_url', ''),
        F5_TTS_WINFORM_NAMES[3]: params.get('diatts_url', ''),
        F5_TTS_WINFORM_NAMES[4]: params.get('voxcpmtts_url', ''),
    }
    return TTS_URL_LIST.get(name, '')


# F5-TTS 根据 name 获取对应的url值键名
def get_key_byf5tts(name):
    return {
        F5_TTS_WINFORM_NAMES[0]: 'f5tts_url',
        F5_TTS_WINFORM_NAMES[1]: 'sparktts_url',
        F5_TTS_WINFORM_NAMES[2]: 'indextts_url',
        F5_TTS_WINFORM_NAMES[3]: 'diatts_url',
        F5_TTS_WINFORM_NAMES[4]: 'voxcpmtts_url',
    }.get(name, 'f5tts_url')


## 翻译,lang_key对应 transobj中键名，kw多个位置参数，对应替换 lang_key中 {}
# tr("xxxxx",root_dir,length)
try:
    transobj = json.loads(Path(SUPPORT_LANG[defaulelang]).read_text(encoding='utf-8'))
except json.JSONDecodeError:
    raise RuntimeError(f'语言文件语法错误:{SUPPORT_LANG[defaulelang]}')
except OSError as e:
    raise RuntimeError(f'语言文件不存在或不可读:{SUPPORT_LANG[defaulelang]}')

def tr(lang_key, *kw):
    lang = transobj.get(lang_key)
    if not lang:
        return lang_key
    if not kw:
        return lang
    try:
        return lang.format(*kw)
    except IndexError:
        return lang
