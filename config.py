import os
import queue

# 语言 三字母语言用于软嵌入字幕时 language=
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
#当前执行目录
rootdir = os.getcwd()
#添加环境变量 ffmpeg
os.environ['PATH'] = rootdir + ';' + os.environ['PATH']
# 日志队列
qu = queue.Queue(100)

## You can find all the possible languages here:
# https://cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages
## You can find all the possible language here:
# https://py-googletrans.readthedocs.io/en/latest/#googletrans-languages
# https://realpython.com/python-speech-recognition/#how-speech-recognition-works-an-overview
# https://stackoverflow.com/questions/14257598/what-are-language-codes-in-chromes-implementation-of-the-html5-speech-recogniti

# 存放所有视频名字键值对，值存放按钮上显示文字，完成后存放视频地址
videolist = {}
# 存放每个视频处理的时间
timelist = {}
# 存放线程list
tc = []
# 开始按钮状态
current_status = "stop"
# 是否已执行过
ishastart = False
# 配置
video_config = {
    "target_dir": "",
    "source_dir": "",
    "detect_language": "en",
    "source_language": "en",
    "target_language": "zh-cn",
    "subtitle_language": "chi",
    "subtitle_type": "soft",
    "subtitle_out":"目标语言字幕",
    "savesubtitle":"保留"
}
task_nums=[1,1]
task_threads=[]

# proxy = {"https": httpcore.SyncHTTPProxy((b'http',b'127.0.0.1',10809,b''))}
# proxy = {"https": httpcore.SyncHTTPProxy(proxy_url="http://127.0.0.1:10809")}
# os.environ['http_proxy']="http://127.0.0.1:10809"
# os.environ['https_proxy']="http://127.0.0.1:10809"
# translator = Translator(service_urls=['translate.googleapis.com'])
# translation = translator.translate("Der Himmel ist blau und ich mag Bananen", dest='zh-cn')
# print(translation.text)
# print(os.environ['path'])
# exit()
# 当前目录