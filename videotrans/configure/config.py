# -*- coding: utf-8 -*-
import configparser
import datetime
import os
import locale
import logging
import re
import sys
from queue import Queue
from videotrans.configure.language import translate_language, language_code_list, clilanglist

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
defaulelang = "en" if locale.getdefaultlocale()[0].split('_')[0].lower() != 'zh' else "zh"


def parse_init():
    settings = {
            "lang":defaulelang,
            "dubbing_thread":5,
            "trans_thread":10,
            "countdown_sec":60
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
if settings['lang'].lower() in ["en", 'zh', 'zh-cn']:
    defaulelang=settings['lang'].lower()

if defaulelang == 'en':
    transobj = translate_language['en']
    langlist = language_code_list['en']
else:
    transobj = translate_language['zh']
    langlist = language_code_list['zh']

english_code_bygpt=list(language_code_list[defaulelang].keys())

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



class Myexcept(Exception):
    pass