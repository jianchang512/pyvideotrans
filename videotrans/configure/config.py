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
TEMP_DIR = os.path.join(rootdir, "tmp").replace('\\', '/')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR, exist_ok=True)
homedir = os.path.join(os.path.expanduser('~'), 'Videos/pyvideotrans').replace('\\', '/')
if not os.path.exists(f"{rootdir}/logs"):
    os.makedirs(f"{rootdir}/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    filename=f'{rootdir}/logs/video-{datetime.datetime.now().strftime("%Y%m%d")}.log',
    encoding="utf-8",
    filemode="a")
logger = logging.getLogger('VideoTrans')


class Myexcept(Exception):
    pass


def parse_init():
    settings = {
        "lang": defaulelang,
        "dubbing_thread": 5,
        "trans_thread": 15,
        "countdown_sec": 30,
        "cuda_com_type": "int8",
        "whisper_threads": 4,
        "whisper_worker": 1,
        "beam_size": 1,
        "best_of": 1,
        "vad":True,
        "temperature":0,
        "condition_on_previous_text":False,
        "crf":13,
        "retries":5,
        "chatgpt_model":"gpt-3.5-turbo,gpt-4",
        "separate_sec":1800,
        "audio_rate":0,
        "video_rate":0,
        "initial_prompt_zh":"",
        "fontsize":14,
        "voice_silence":200,
        "interval_split":10,
        "cjk_len":24,
        "other_len":36,
        "backaudio_volume":0.8,
        "overall_silence":100,
        "overall_maxsecs":4
    }
    file = os.path.join(rootdir, 'videotrans/set.ini')
    if os.path.exists(file):
        with open(file, 'r', encoding="utf-8") as f:
            # 遍历.ini文件中的每个section
            for it in f.readlines():
                it = it.strip()
                if not it or it.startswith(';') or it.startswith('['):
                    continue
                key,value = it.split('=', 1)
                # 遍历每个section中的每个option
                key = key.strip()
                value = value.strip()
                if re.match(r'^\d+$', value):
                    settings[key] = int(value)
                elif re.match(r'^\d+\.\d$', value):
                    settings[key] = round(float(value),1)
                elif value.lower() == 'true':
                    settings[key] = True
                elif value.lower() == 'false':
                    settings[key] = False
                else:
                    settings[key] = str(value.lower()) if value else None
        if isinstance(settings['fontsize'],str) and settings['fontsize'].find('px')>0:
            settings['fontsize']=int(settings['fontsize'].replace('px',''))
    return settings


# 语言
defaulelang = locale.getdefaultlocale()[0][:2].lower()
# 初始化一个字典变量
settings = parse_init()
# default language 如果 ini中设置了，则直接使用，否则自动判断
if settings['lang']:
    defaulelang = settings['lang'].lower()
# 语言代码文件是否存在
if not os.path.exists(os.path.join(rootdir, f'videotrans/language/{defaulelang}.json')):
    defaulelang = "en"

obj = json.load(open(os.path.join(rootdir, f'videotrans/language/{defaulelang}.json'), 'r', encoding='utf-8'))

# 交互语言代码
transobj = obj["translate_language"]
# 软件界面
uilanglist = obj["ui_lang"]
# 语言代码:语言显示名称
langlist = obj["language_code_list"]
# 语言显示名称：语言代码
rev_langlist = {val: key for key, val in langlist.items()}
# 语言显示名称 list
langnamelist = list(langlist.values())
# 工具箱语言
box_lang = obj['toolbox_lang']

# ffmpeg
if sys.platform == 'win32':
    os.environ['PATH'] = rootdir + f';{rootdir}\\ffmpeg;' + os.environ['PATH']
else:
    os.environ['PATH'] = rootdir + f':{rootdir}/ffmpeg:' + os.environ['PATH']

os.environ['QT_API'] = 'pyside6'
# spwin主窗口
queue_logs = Queue(1000)
# box窗口
queuebox_logs = Queue(1000)

# 开始按钮状态
current_status = "stop"
# video toolbox 状态
box_status = "stop"
# 工具箱 需格式化的文件数量
geshi_num = 0

clone_voicelist=["clone"]

openaiTTS_rolelist = "alloy,echo,fable,onyx,nova,shimmer"
chatgpt_model_list = [ it.strip() for it in settings['chatgpt_model'].split(',')]
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
    "is_separate":False,

    "voice_role": "No",
    "voice_rate": "+0%",

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

    "tts_type": "edgeTTS",  # 所选的tts==edge-tts:openaiTTS|coquiTTS|elevenlabsTTS
    "tts_type_list": ["edgeTTS", "GPT-SoVITS","clone-voice","openaiTTS", "elevenlabsTTS","TTS-API"],

    "whisper_type": "all",
    "whisper_model": "base",
    "model_type":"faster",
    "only_video":False,
    "translate_type": "google",
    "subtitle_type": 0,  # embed soft
    "voice_autorate": False,
    "video_autorate": False,

    "deepl_authkey": "",
    "deepl_api":"",
    "deeplx_address": "",
    "ott_address": "",

    "tencent_SecretId": "",
    "tencent_SecretKey": "",

    "baidu_appid": "",
    "baidu_miyue": "",

    "coquitts_role": "",
    "coquitts_key": "",

    "elevenlabstts_role": [],
    "elevenlabstts_key": "",

    "clone_api": "",

    "chatgpt_api": "",
    "chatgpt_key": "",
    "chatgpt_model":chatgpt_model_list[0],
    "chatgpt_template": "",
    "azure_api": "",
    "azure_key": "",
    "azure_model": "gpt-3.5-turbo",
    "azure_template": "",
    "openaitts_role": openaiTTS_rolelist,
    "gemini_key": "",
    "gemini_template": "",

    "ttsapi_url":"",
    "ttsapi_voice_role":"",
    "ttsapi_extra":"pyvideotrans",

    "gptsovits_url":"",
    "gptsovits_role":"",
    "gptsovits_extra":"pyvideotrans"


}

with open(os.path.join(rootdir,'videotrans/chatgpt.txt'),'r',encoding='utf-8') as f:
    params['chatgpt_template']=f.read().strip()+"\n"
with open(os.path.join(rootdir,'videotrans/azure.txt'),'r',encoding='utf-8') as f:
    params['azure_template']=f.read().strip()+"\n"
with open(os.path.join(rootdir,'videotrans/gemini.txt'),'r',encoding='utf-8') as f:
    params['gemini_template']=f.read().strip()+"\n"

# 存放一次性多选的视频
queue_mp4 = []
# 存放视频分离为无声视频进度，noextname为key，用于判断某个视频是否是否已预先创建好 novice_mp4, “ing”=需等待，end=成功完成，error=出错了
queue_novice = {}

# 任务队列
queue_task = []
# 倒计时
task_countdown = 60
# 全局错误信息
errors = ""
# 获取的视频信息
video_cache = {}
# 软件界面当前正在执行的进度条key
btnkey = ""

# 临时全局变量
temp = []
#youtube是否取消了下载
canceldown=False
#工具箱翻译进行状态,ing进行中，其他停止
box_trans="stop"
#工具箱tts状态
box_tts="stop"
#工具箱识别状态
box_recogn='stop'
# 中断win背景分离
separate_status='stop'
# 最后一次打开的目录
last_opendir=homedir if not os.path.exists(homedir+"/Videos") else homedir+"/Videos"
exit_ffmpeg=False