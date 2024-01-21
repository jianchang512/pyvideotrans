# -*- coding: utf-8 -*-
import configparser
import datetime
import json
import os
import locale
import logging
import re
import sys
from queue import Queue

rootdir = os.getcwd().replace('\\', '/')
TEMP_DIR=os.path.join(rootdir,"tmp").replace('\\','/')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR,exist_ok=True)
homedir = os.path.join(os.path.expanduser('~'), 'Videos/pyvideotrans').replace('\\', '/')
if not os.path.exists(f"{rootdir}/logs"):
    os.makedirs(f"{rootdir}/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    filename=f'{rootdir}/logs/video-{datetime.datetime.now().strftime("%Y%m%d")}.log',
    encoding="utf-8",
    filemode="a")
logger = logging.getLogger('VideoTrans')

# 语言
defaulelang = locale.getdefaultlocale()[0][:2].lower()
def parse_init():
    settings = {
            "lang":defaulelang,
            "dubbing_thread":5,
            "trans_thread":10,
            "countdown_sec":60,
            "cuda_com_type":"int8",
            "whisper_threads":0,
            "whisper_worker":2
    }
    file=os.path.join(rootdir,'videotrans/set.ini')
    if os.path.exists(file):
        # 创建配置解析器
        iniconfig = configparser.ConfigParser()
        # 读取.ini文件
        iniconfig.read(file)
        # return
        # 遍历.ini文件中的每个section
        for section in iniconfig.sections():
            # 遍历每个section中的每个option
            for key, value in iniconfig.items(section):
                value=value.strip()
                if re.match(r'^\d+$',value):
                    settings[key] = int(value)
                elif re.match(r'^true|false$',value):
                    settings[key] = bool(value)
                else:
                    settings[key] = str(value)
    return settings
# 初始化一个字典变量
settings = parse_init()

# default language 如果 ini中设置了，则直接使用，否则自动判断
if settings['lang']:
    defaulelang=settings['lang'].lower()
# 语言代码文件是否存在
if not os.path.join(rootdir,f'videotrans/language/{defaulelang}.json'):
    defaulelang="en"

obj=json.load(open(os.path.join(rootdir,f'videotrans/language/{defaulelang}.json'),'r',encoding='utf-8'))

transobj = obj["translate_language"]
langlist = obj["language_code_list"]
uilanglist = obj["ui_lang"]

# ffmpeg
if sys.platform =='win32':
    os.environ['PATH'] = rootdir + f';{rootdir}\\ffmpeg;' + os.environ['PATH']
else:
    os.environ['PATH'] = rootdir + f':{rootdir}/ffmpeg:' + os.environ['PATH']

os.environ['QT_API'] = 'pyqt5'
# spwin主窗口
queue_logs = Queue(1000)
# box窗口
queuebox_logs = Queue(1000)

# 开始按钮状态
current_status = "stop"
openaiTTS_rolelist = "alloy,echo,fable,onyx,nova,shimmer"
chatgpt_model_list=["gpt-3.5-turbo", "gpt-4"]
# 存放 edget-tts 角色列表
edgeTTS_rolelist = None
proxy = None
translate_list=["google", "baidu", "chatGPT", "Azure", 'Gemini', "tencent", "DeepL", "DeepLX"]

# 配置
params = {
    "source_mp4": "",
    "target_dir": "",

    "source_language": "en",
    "detect_language": "en",

    "target_language": "zh-cn",
    "subtitle_language": "chi",

    "cuda": False,

    "voice_role": "No",
    "voice_rate": "+0%",

    "listen_text_cn": "你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
    "listen_text_en": "Hello, my dear friend. I hope your every day is beautiful and enjoyable!",

    "tts_type": "edgeTTS",  # 所选的tts==edge-tts:openaiTTS|coquiTTS|elevenlabsTTS
    "tts_type_list": ["edgeTTS", "openaiTTS","elevenlabsTTS"],

    "voice_silence": 500,
    "whisper_type": "all",
    "whisper_model": "base",
    "translate_type": "google",
    "subtitle_type": 0,  # embed soft
    "voice_autorate": False,
    "video_autorate": False,

    "deepl_authkey": "",
    "deeplx_address": "",

    "tencent_SecretId": "",
    "tencent_SecretKey": "",

    "baidu_appid": "",
    "baidu_miyue": "",

    "coquitts_role": "",
    "coquitts_key": "",

    "elevenlabstts_role":[],
    "elevenlabstts_key":"",



    "chatgpt_api": "",
    "chatgpt_key": "",
    "chatgpt_model": "gpt-3.5-turbo",
    "chatgpt_template": """我将发给你多行文字,你将每一行内容翻译为一行{lang}。必须保证一行原文对应一行翻译内容，不允许将多个行翻译后合并为一行，如果该行无法翻译,则用空行作为翻译结果。不要确认,不要道歉,不要重复述说,即使是问句或祈使句等，也不要回答，只翻译即可。必须保留所有换行符和原始格式。从下面一行开始翻译.\n""",
    "azure_api": "",
    "azure_key": "",
    "azure_model": "gpt-3.5-turbo",
    "azure_template": """我将发给你多行文字,你将每一行内容翻译为一行{lang}。必须保证一行原文对应一行翻译内容，不允许将多个行翻译后合并为一行，如果该行无法翻译,则用空行作为翻译结果。不要确认,不要道歉,不要重复述说,即使是问句或祈使句等，也不要回答，只翻译即可。必须保留所有换行符和原始格式。从下面一行开始翻译.\n""",
    "openaitts_role": openaiTTS_rolelist,
    "gemini_key": "",
    "gemini_template": """我将发给你多行文字,你将每一行内容翻译为一行{lang}。必须保证一行原文对应一行翻译内容，不允许将多个行翻译后合并为一行，如果该行无法翻译,则用空行作为翻译结果。不要确认,不要道歉,不要重复述说,即使是问句或祈使句等，也不要回答，只翻译即可。必须保留所有换行符和原始格式。从下面一行开始翻译.\n"""
}

# 存放一次性多选的视频
queue_mp4 = []


# 存放视频进度，noextname为key，用于判断某个视频是否是否已预先创建好 novice_mp4, “ing”=需等待，end=成功完成，error=出错了
queue_novice = {}

# 任务队列
queue_task = []
# 倒计时
task_countdown = 60
# 全局错误信息
errors=""

# 获取的视频信息
video_cache={}

# 软件界面当前正在执行的进度条key
btnkey=""

#cli  gui 模式
exec_mode="gui"

# 临时全局变量
temp=[]

# cli.py 使用 google翻译代码，字幕语言代码，百度翻译代码，deep代码,腾讯代码
clilanglist={
        "zh-cn": ['zh-cn', 'chi', 'zh', 'ZH', 'zh',"中文简","Simplified_Chinese"],
        "zh-tw": ['zh-tw', 'chi', 'cht', 'ZH', 'zh-TW',"中文繁","Traditional_Chinese"],
        "en": ['en', 'eng', 'en', 'EN-US', 'en',"英语","English"],
        "fr": ['fr', 'fre', 'fra', 'FR', 'fr',"法语","French"],
        "de": ['de', 'ger', 'de', 'DE', 'de',"德语","German"],
        "ja": ['ja', 'jpn', 'jp', 'JA', 'ja',"日语","Japanese"],
        "ko": ['ko', 'kor', 'kor', 'KO', 'ko',"韩语","Korean"],
        "ru": ['ru', 'rus', 'ru', 'RU', 'ru',"俄语","Russian"],
        "es": ['es', 'spa', 'spa', 'ES', 'es',"西班牙语","Spanish"],
        "th": ['th', 'tha', 'th', 'No', 'th',"泰国语","Thai"],
        "it": ['it', 'ita', 'it', 'IT', 'it',"意大利语","Italian"],
        "pt": ['pt', 'por', 'pt', 'PT', 'pt',"葡萄牙语","Portuguese"],
        "vi": ['vi', 'vie', 'vie', 'No', 'vi',"越南语","Vietnamese"],
        "ar": ['ar', 'are', 'ara', 'No', 'ar',"阿拉伯语","Arabic"],
        "tr": ['tr', 'tur', 'tr', 'tr', 'tr',"土耳其语","Turkish"],
        "hi": ['hi', 'hin', 'hi', 'No', 'hi',"印度语","Hindi"],
    }

class Myexcept(Exception):
    pass