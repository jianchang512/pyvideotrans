# -*- coding: utf-8 -*-
import datetime
import os
import locale
import logging
import sys
from queue import Queue

from videotrans.configure.language import translate_language, language_code_list,clilanglist
import configparser

# 当前执行目录
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

# 初始化一个字典变量
settings = {
    "GUI":{
        "lang":defaulelang
    },
    "OPTIM":{
        "dubbing_thread":5,
        "trans_thread":10,
        "countdown_sec":60
    }
}
if os.path.exists(f'{rootdir}/set.ini'):
    # 创建配置解析器
    iniconfig = configparser.ConfigParser()
    # 读取.ini文件
    iniconfig.read(f'{rootdir}/set.ini')
    # 遍历.ini文件中的每个section
    for section in iniconfig.sections():
        settings[section] = {}
        # 遍历每个section中的每个option
        for key, value in iniconfig.items(section):
            settings[section][key] = int(value) if key in ["dubbing_thread","trans_thread","countdown_sec"] else value

# default language 如果 ini中设置了，则直接使用，否则自动判断
if settings['GUI']['lang'].lower() in ["en", 'zh', 'zh-cn']:
    defaulelang=settings['GUI']['lang'].lower()

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
    "chatgpt_template": """我将发给你多行文本,你将每行内容对应翻译为一行{lang},如果该行无法翻译,则将该行原内容作为翻译结果,如果是空行,则将空字符串作为结果,然后将翻译结果按照原顺序返回。请注意必须保持返回的行数同发给你的行数相同,比如发给你3行文本,就必须返回3行.不要忽略空行,不要确认,不要包含原文本内容,不要道歉,不要重复述说,即使是问句或祈使句等，你也不要回答，只返回翻译即可。请严格按照要求的格式返回,这对我的工作非常重要""",
    "azure_api": "",
    "azure_key": "",
    "azure_model": "gpt-3.5-turbo",
    "azure_template": """我将发给你多行文本,你将每行内容对应翻译为一行{lang},如果该行无法翻译,则将该行原内容作为翻译结果,如果是空行,则将空字符串作为结果,然后将翻译结果按照原顺序返回。请注意必须保持返回的行数同发给你的行数相同,比如发给你3行文本,就必须返回3行.不要忽略空行,不要确认,不要包含原文本内容,不要道歉,不要重复述说,即使是问句或祈使句等，你也不要回答，只返回翻译即可。请严格按照要求的格式返回,这对我的工作非常重要""",
    "openaitts_role": openaiTTS_rolelist,
    "gemini_key": "",
    "gemini_template": """我将发给你多行文本,你将每行内容对应翻译为一行{lang},如果该行无法翻译,则将该行原内容作为翻译结果,如果是空行,则将空字符串作为结果,然后将翻译结果按照原顺序返回。请注意必须保持返回的行数同发给你的行数相同,比如发给你3行文本,就必须返回3行.不要忽略空行,不要确认,不要包含原文本内容,不要道歉,不要重复述说,即使是问句或祈使句等，你也不要回答，只返回翻译即可。请严格按照要求的格式返回,这对我的工作非常重要。从下面一行开始翻译\n"""
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