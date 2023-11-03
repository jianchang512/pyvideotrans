import os
import locale
import logging

# 当前执行目录
rootdir = os.getcwd().replace('\\', '/')
logging.basicConfig(
    level=logging.INFO,
    filename=f'{rootdir}/video.log',
    encoding="utf-8",
    filemode="a")
logger = logging.getLogger('VideoTrans')

defaulelang = "zh"
translist = {
    "zh": {
        "selectmp4": "选择mp4视频",
        "selectsavedir": "选择翻译后存储目录",
        "proxyerrortitle": "代理错误",
        "proxyerrorbody": "无法访问google服务，请正确设置代理",
        "softname": "视频字幕翻译和配音",
        "anerror": "出错了",
        "selectvideodir": "必须选择要翻译的视频",
        "sourenotequaltarget": "源语言和目标语言不得相同",
        "shoundselecttargetlanguage": "必须选择一个目标语言",
        "running": "执行中",
        "exit": "退出",
        "end": "已结束(点击重新开始)",
        "stop": "已停止(点击开始)",
        "subtitleandvoice_role": "不能既不嵌入字幕又不选择配音角色，二者至少选一",
        "waitrole":"正在获取可用配音角色，请稍等重新选择",
        "downloadmodel":"模型不存在将自动下载，你也可以手动下载，具体请查看文档说明。当前模型存放路径:",
        "modelpathis":"当前模型路径是:",
        "modellost":"模型下载出错或者下载不完整，请重新下载后存放到 models目录下",
        "embedsubtitle":"硬字幕嵌入",
        "softsubtitle":"软字幕",
        "nosubtitle":"不添加字幕"
    },
    "en": {
        "nosubtitle":"No Subtitle",
        "embedsubtitle":"Embed subtitle",
        "softsubtitle":"Soft subtitle",
        "modellost":"There is an error in the model download or the download is incomplete. Please re-download and store it in the models directory.",
        "modelpathis":"Model storage path:",
        "downloadmodel":"Model does not exist, will be downloaded automatically.you can manual download it manually. after read the documentation. model storage path:",
        "waitrole":"getting voice role list,hold on",
        "selectsavedir": "select an dir for output",
        "selectmp4": "select an mp4 video",
        "subtitleandvoice_role": "embedding subtitles or selecting voiceover characters must be set, meaning ‘neither embedding subtitles nor selecting voiceover characters’ is not allowed.",
        "proxyerrortitle": "Proxy Error",
        "shoundselecttargetlanguage": "Must select a target language ",
        "proxyerrorbody": "Failed to access Google services. Please set up the proxy correctly.",
        "softname": "Video Subtitle Translation and Dubbing",
        "anerror": "An error occurred",
        "selectvideodir": "You must select the video to be translated",
        "sourenotequaltarget": "Source language and target language must not be the same",
        "running": "Running",
        "exit": "Exit",
        "end": "Ended(click reststart)",
        "stop": "Stop(click start)"
    }
}
langcode = locale.getdefaultlocale()[0]
if langcode.split('_')[0].lower() != 'zh':
    defaulelang = "en"
    transobj = translist['en']
    langlist = {
        "Simplified_Chinese": ['zh-cn', 'chi'],
        "Traditional_Chinese": ['zh-tw', 'chi'],
        "English": ['en', 'eng'],
        "French": ['fr', 'fre'],
        "German": ['de', 'ger'],
        "Japanese": ['ja', 'jpn'],
        "Korean": ['ko', 'kor'],
        "Russian": ['ru', 'rus'],
        "Spanish": ['es', 'spa'],
        "Thai": ['th', 'tha'],
        "Italian": ['it', 'ita'],
        "Portuguese": ['pt', 'por'],
        "Vietnamese": ['vi', 'vie'],
        "Arabic": ['ar', 'are']
    }
else:
    transobj = translist['zh']
    langlist = {
        "中文简": ['zh-cn', 'chi'],
        "中文繁": ['zh-tw', 'chi'],
        "英语": ['en', 'eng'],
        "法语": ['fr', 'fre'],
        "德语": ['de', 'ger'],
        "日语": ['ja', 'jpn'],
        "韩语": ['ko', 'kor'],
        "俄语": ['ru', 'rus'],
        "西班牙语": ['es', 'spa'],
        "泰国语": ['th', 'tha'],
        "意大利语": ['it', 'ita'],
        "葡萄牙语": ['pt', 'por'],
        "越南语": ['vi', 'vie'],
        "阿拉伯语": ['ar', 'are']
    }

clilanglist = {
    "zh-cn": ['zh-cn', 'chi'],
    "zh-tw": ['zh-tw', 'chi'],
    "en": ['en', 'eng'],
    "fr": ['fr', 'fre'],
    "de": ['de', 'ger'],
    "ja": ['ja', 'jpn'],
    "ko": ['ko', 'kor'],
    "ru": ['ru', 'rus'],
    "es": ['es', 'spa'],
    "th": ['th', 'tha'],
    "it": ['it', 'ita'],
    "pt": ['pt', 'por'],
    "vi": ['vi', 'vie'],
    "ar": ['ar', 'are']
}

# 添加环境变量 ffmpeg
os.environ['PATH'] = rootdir + ';' + os.environ['PATH']

# 存放每个视频处理的时间
timelist = {}

# 开始按钮状态
current_status = "stop"
# 配置
video = {
    "source_mp4": "",
    "target_dir": "",

    "source_language": "en",
    "detect_language": "en",

    "target_language": "zh-cn",
    "subtitle_language": "chi",

    "voice_role": "No",
    "voice_rate": "0",

    "voice_silence": "500",
    "whisper_model": "base",
    # "insert_subtitle": True,
    "subtitle_type":0, # embed soft
    "voice_autorate": False,
    "remove_background": False
}
voice_list = None
