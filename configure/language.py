translate_language = {
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
        "downloadmodel":"模型不存在，请去下载后存放到:",
        "modelpathis":"当前模型路径是:",
        "modellost":"模型下载出错或者下载不完整，请重新下载后存放到 models目录下",
        "embedsubtitle":"硬字幕嵌入",
        "softsubtitle":"软字幕",
        "nosubtitle":"不添加字幕",
        "baikeymust":"你必须填写百度key",
        "chatgptkeymust":"你必须填写chatGPT key",
        "waitsubtitle":"等待编辑字幕(点击继续合成)",
        "waitforend":"正在合成视频",
        "createdirerror":"创建目录失败"
    },
    "en": {
        "createdirerror":"create dir error",
        "waitforend":"Composing video",
        "waitsubtitle":"Wait edit subtitle(click for continue)",
        "baikeymust":"input your baidu key",
        "chatgptkeymust":"input your chatgpt key",
        "nosubtitle":"No Subtitle",
        "embedsubtitle":"Embed subtitle",
        "softsubtitle":"Soft subtitle",
        "modellost":"There is an error in the model download or the download is incomplete. Please re-download and store it in the models directory.",
        "modelpathis":"Model storage path:",
        "downloadmodel":"Model does not exist, download it and save to:",
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


#  名称:google翻译，字幕语言，百度翻译
language_code_list={
    "zh":{
        "中文简": ['zh-cn', 'chi','zh'],
        "中文繁": ['zh-tw', 'chi','zh'],
        "英语": ['en', 'eng','en'],
        "法语": ['fr', 'fre','fra'],
        "德语": ['de', 'ger','de'],
        "日语": ['ja', 'jpn','jp'],
        "韩语": ['ko', 'kor','kor'],
        "俄语": ['ru', 'rus','ru'],
        "西班牙语": ['es', 'spa','spa'],
        "泰国语": ['th', 'tha','th'],
        "意大利语": ['it', 'ita','it'],
        "葡萄牙语": ['pt', 'por','pt'],
        "越南语": ['vi', 'vie','vie'],
        "阿拉伯语": ['ar', 'are','ara']
    },
    "en":{
        "Simplified_Chinese": ['zh-cn', 'chi','zh'],
        "Traditional_Chinese": ['zh-tw', 'chi','zh'],
        "English": ['en', 'eng','en'],
        "French": ['fr', 'fre','fra'],
        "German": ['de', 'ger','de'],
        "Japanese": ['ja', 'jpn','jp'],
        "Korean": ['ko', 'kor','kor'],
        "Russian": ['ru', 'rus','ru'],
        "Spanish": ['es', 'spa','spa'],
        "Thai": ['th', 'tha','th'],
        "Italian": ['it', 'ita','it'],
        "Portuguese": ['pt', 'por','pt'],
        "Vietnamese": ['vi', 'vie','vie'],
        "Arabic": ['ar', 'are','ara']
    }
}

# cli language ccode
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
english_code_bygpt=list(language_code_list['en'].keys())
