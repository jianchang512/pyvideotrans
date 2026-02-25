from dataclasses import dataclass

# 视频翻译流程使用全部属性
@dataclass
class TaskCfgBase:
    # 通用区域
    is_cuda:bool=False#是否使用cuda加速
    uuid:str=None # 默认唯一任务id
    cache_folder: str=None  # 当前文件的临时文件夹,用于存放临时过程文件
    target_dir: str=None  # 输出文件夹，目标视频输出文件夹
    source_language: str=None  # 原始语言名称或代码
    source_language_code: str=None  # 原始语言代码
    source_sub: str=None  # 原始字幕文件绝对路径
    source_wav: str=None  # 原始语言音频，存在于临时文件夹下
    source_wav_output: str=None  # 原始语言音频输出，存在于目标文件夹下
    target_language: str=None  # 目标语言名称或代码
    target_language_code: str=None  # 目标语言代码
    target_sub: str=None  # 目标字幕文件绝对路径
    target_wav: str=None  # 目标语言音频，存在于临时文件夹下
    target_wav_output: str=None  # 目标语言音频输出，存在于目标文件夹下
    name:str=None # 规范化处理的原始文件绝对路径 D:/XXX/1.MP4
    noextname: str=None  # 去掉扩展名的原始视频名
    basename:str=None # noextname + ext 名 1.mp4
    ext:str=None # 扩展名 mp4
    dirname:str=None # 原始文件所在目录 D:/XXX
    shound_del_name:str=None # 如果规范化后移动了，则需要删除的临时文件绝对路径

    '''
    ############## 视频翻译特有
    subtitle_language: str=None  # 软字幕嵌入语言代码，3位
    app_mode: str="biaozhun"  # 工作模式 biaohzun tiqu
    subtitles: str=""  # 已存在的字幕文本，例如预先导入的
    targetdir_mp4: str=None  # 最终输出合成后的mp4
    novoice_mp4: str=None  # 从原始视频分离出的无声视频
    is_separate: bool=False  # 是否进行人声、背景音分离
    instrument: str=None  # 分离出的背景音频
    vocal: str=None  # 分离出的人声音频
    back_audio: str=None  # 手动添加的原始背景音音频
    clear_cache:bool=False # 是否清理已存在的文件
    background_music: str=None  # 手动添加的背景音频，整理后的完整路径
    subtitle_type: int=0  # 软硬字幕嵌入类型 0=不嵌入，1=硬字幕，2=软字幕，3=双硬，4=双软
    only_out_mp4:bool=False# 是否仅仅输出mp4,仅视频翻译使用
    recogn2pass:bool=False# 对配音音频再次识别
    output_srt:int=0# 转录并翻译 模式输出字幕类似，0=单字幕，1=目标语言在线双字幕，2=目标语言在上双字幕
    copysrt_rawvideo:bool=False# 是否将生成的字幕复制到视频目录下

    ####### 语音识别相关
    detect_language: str=None  # 字幕检测语言代码
    recogn_type:int=None #语音识别渠道
    model_name:str=None #模型名字
    shibie_audio: str=None  # 转为 pcm_s16le  16k 作为语音识别的音频文件
    remove_noise: bool=False  # 是否移除噪声
    enable_diariz:bool=False # 是否进行说话人识别
    nums_diariz:int=0 # 是否进行说话人识别
    rephrase:int=2 #0 默认断句不处理 1=LLM重新断句 2=自动修正
    fix_punc:bool=False# 是否恢复标点符号


    ######## 配音相关
    tts_type:int=None # 语音合成渠道
    volume: str="+0%"  # 音量
    pitch: str="+0Hz"  # 音调
    voice_rate: str="+0%"  # 语速
    voice_role: str=None  # 配音角色
    voice_autorate:bool=False #是否音频自动加速
    video_autorate:bool=False #是否视频自动慢速
    remove_silent_mid:bool=False # 是否移除字幕间的空隙
    align_sub_audio:bool=True # 是否强制对齐字幕和声音

    ######## 字幕翻译相关
    translate_type:int=None # 字幕翻译渠道
    '''



# 语音识别
@dataclass
class TaskCfgSTT(TaskCfgBase):
    ####### 语音识别相关
    detect_language: str = None  # 字幕检测语言代码
    recogn_type: int = None  # 语音识别渠道
    model_name: str = None  # 模型名字
    shibie_audio: str = None  # 转为 pcm_s16le  16k 作为语音识别的音频文件
    remove_noise: bool = False  # 是否移除噪声
    enable_diariz: bool = False  # 是否进行说话人识别
    nums_diariz: int = 0  # 是否进行说话人识别
    rephrase: int = 2  # 0 默认断句不处理 1=LLM重新断句 2=自动修正
    fix_punc: bool = False  # 是否恢复标点符号

# 配音
@dataclass
class TaskCfgTTS(TaskCfgBase):
    ######## 配音相关
    tts_type:int=None # 语音合成渠道
    volume: str="+0%"  # 音量
    pitch: str="+0Hz"  # 音调
    voice_rate: str="+0%"  # 语速
    voice_role: str=None  # 配音角色
    voice_autorate:bool=False #是否音频自动加速
    video_autorate:bool=False #是否视频自动慢速
    remove_silent_mid:bool=False # 是否移除字幕间的空隙
    align_sub_audio:bool=True # 是否强制对齐字幕和声音

# 字幕翻译
@dataclass
class TaskCfgSTS(TaskCfgBase):
    ######## 字幕翻译相关
    translate_type:int=None # 字幕翻译渠道

# 视频翻译所有
@dataclass
class TaskCfgVTT(TaskCfgSTT,TaskCfgTTS,TaskCfgSTS):
    ############## 视频翻译特有
    subtitle_language: str=None  # 软字幕嵌入语言代码，3位
    app_mode: str="biaozhun"  # 工作模式 biaohzun tiqu
    subtitles: str=""  # 已存在的字幕文本，例如预先导入的
    targetdir_mp4: str=None  # 最终输出合成后的mp4
    novoice_mp4: str=None  # 从原始视频分离出的无声视频
    is_separate: bool=False  # 是否进行人声、背景音分离
    instrument: str=None  # 分离出的背景音频
    vocal: str=None  # 分离出的人声音频
    back_audio: str=None  # 手动添加的原始背景音音频
    clear_cache:bool=False # 是否清理已存在的文件
    background_music: str=None  # 手动添加的背景音频，整理后的完整路径
    subtitle_type: int=0  # 软硬字幕嵌入类型 0=不嵌入，1=硬字幕，2=软字幕，3=双硬，4=双软
    only_out_mp4:bool=False# 是否仅仅输出mp4,仅视频翻译使用
    recogn2pass:bool=False# 对配音音频再次识别
    output_srt:int=0# 转录并翻译 模式输出字幕类似，0=单字幕，1=目标语言在线双字幕，2=目标语言在上双字幕
    copysrt_rawvideo:bool=False# 是否将生成的字幕复制到视频目录下