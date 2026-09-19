- 优化模型下载失败处理，失败后将自动重试
- 优化 whisper 模型识别后重断句算法
- 硅基流动、Minimax、OpenRouter 完善 语音识别/字幕翻译/语音合成 模型支持
- 豆包语音合成2.0 新增配音角色
- 重构 设置窗口、菜单架构，简化新增渠道
- Qwen-TTS/Higgs等本地配音渠道放弃8位量化，避免某些环境下兼容问题
- 修复其他已知bug



新增 语音识别渠道、字幕翻译渠道、文字配音渠道的方法

- 源码目录 `videotrans/recognition` 是语音识别渠道代码，在此新增，`_base.py`是所有语音识别渠道的基类
- 源码目录 `videotrans/translator`  是字幕翻译渠道代码，在此新增，`_base.py`是所有字幕翻译渠道的基类
- 源码目录 `videotrans/tts`  是文字配音渠道代码，在此新增，`_base.py`是所有文字配音渠道的基类

每个目录下的 `_constants.py `是渠道ID和名字定义文件，打开后在已有定义常量后边为新渠道新增一个常量，值递增，如 `NEWAI_API=32`
```
Deepgram = 24
CAMB_ASR = 25
STT_API = 26
# .net
WHISPER_NET = 27
# 自定义API
CUSTOM_API = 28
SILICONFLOW_API = 29
OPENROUTER_API = 30
MINIMAX_API = 31

```


为此渠道起一个 `{name}`，必须以英文字母开头，并且仅可包含 英文字母、数字、下划线，然后在该包内创建一个py文件，名称为`_{name}.py`,此即为该渠道的所有实现代码，可直接复制已有渠道的代码进行修改

然后在 `ID_NAME_DICT` 对象末尾新增一组设置，key为新增的常量，值为 ChannelProvider 实例，该实例第一个参数是该渠道在软件中的显示名称，`imp`参数是`._{name}.py`，即该渠道的代码文件.

例如 `NEWAI_API: ChannelProvider('NEWAI渠道', key_name="{name}_key", win="{name}", imp="._{name}"),
`

如果该渠道需配置 `SK/API URL`,即需要一个设置界面
	- 需传入参数`key_name={必须填写的参数名，例如api url 或 SK}`，参数名同样仅包含`字母、数字、下划线`，例如`newai_key`, 无论实际定义多少个，这里仅需要填写一个必填参数，例如参数可能有 SK、模型名、max_token、api地址等多个，这里仅填写 sk 即必须填写的。在实际调用该渠道时，软件会判断该值是否已填写，若否将报错提示。
	- 需传入参数`win="{name}"`,即该渠道的设置界面窗口名
	- 在 `videotrans/ui` 内定义一个文件`{name}.py`，这是界面设置文件，同样可直接复制已有的文件进行修改
	- 在 `videotrans/winform` 内定义一个文件`{name}.py`，这是调用ui文件并实现各参数填写、测试的控制代码
	- 在 `videotrans/configure/_app_params.py` 中，`_get_defaults` 方法中，设置默认参数，此步也可省略
	- 在 `videotrans/ui/menu_list.py` 中，新增一个菜单，如果该渠道是 字幕翻译设置，添加到变量`MENU_CFG_TRANS`中，若是TTS渠道，则添加到`MENU_CFG_TTS`，若是语音识别渠道，则添加到`MENU_CFG_STT` 中，菜单是一个元组，有3个元素组成
		0. 元素0填写 `{name}`
		1. 元素1填写菜单显示名称
		2. 元素2填写`None`，代表点击时打开`videotrans/winform/{name}.py`
	例如`("{name}","newai设置菜单",None)`

## 字幕翻译渠道子类
假设定义的`name=newai_route`
创建文件 `videotrans/translator/_newai_route.py`,如果该渠道是api请求并且兼容OpenAI格式，可直接复制`_deepseek.py`修改实现，若否，则可复制 `_google.py` 或 `_hymt2.py` 等实现

必须实现的函数只有一个`def _item_task(self, data: str) -> str:`
参数data：
	当是AI翻译渠道并且选中了`发送完整字幕`：data是  SRT格式字幕字符串
    当传统翻译渠道或未选`发送完整字幕`：data是 多行字幕文本字符串

如果该渠道需要下载模型到本地，还需实现 `def _download(self):`方法，模型下载到`{ROOT_DIR}/models` 目录下，`{ROOT_DIR}`变量来自 `videotrans.configure.config`，具体可参考 `_hymt2.py`文件

例如代码示例
```
@dataclass
class NewAITrans(BaseTrans):
	# 必须实现
    def _item_task(self, data: str) -> str:
	# 当是AI翻译渠道并且选中了`发送完整字幕`：data是  SRT格式字幕字符串
    # 当传统翻译渠道或未选`发送完整字幕`：data是 多行字幕文本字符串
	
	
	# 若需下载模型，子类应实现，下载到 ｛ROOT_DIR｝/models 目录内
    def _download(self):
        pass
```


## 语音识别渠道子类
假设定义的`name=newai_route`
创建文件 `videotrans/recognition/_newai_route.py`,如果该渠道是api请求，可直接复制`_openrouter.py`修改实现，若否，本地模型则可复制 `_fireredasr.py` 等实现.
如果是较大模型，比较吃内存和显存，可考虑独立进程运行，可参考 `_whisper.py` 实现


必须实现的函数只有一个`def _exec(self) -> Union[List[SrtItem], None]:`
可调用`raws = self.cut_audio()`直接返回使用VAD切好片的数据：`List[SrtItem]`
其中 `filename`字段即是需要识别转文字的一条字幕语音。


如果该渠道需要下载模型到本地，还需实现 `def _download(self):`方法，模型下载到`{ROOT_DIR}/models` 目录下，`{ROOT_DIR}`变量来自 `videotrans.configure.config`，具体可参考 `_whisper.py`文件

例如代码
```
@dataclass
class NewaiRecogn(BaseRecogn):

	def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        # 发送请求
        raws = self.cut_audio()
		for i, it in enumerate(raws):
			it['text']=`转录函数(it['filename'])`
			
		return raws
	
	
	def _download(self):
		pass
```

## 文字配音渠道子类

假设定义的`name=newai_route`
创建文件 `videotrans/tts/_newai_route.py`,如果该渠道是api请求，可直接复制`_openrouter.py/_xiaomi.py`等修改实现，若否，本地模型，则可复制 `_zipvoice.py` 等实现.
如果是较大模型，比较吃内存和显存，可考虑独立进程运行，可参考 `_omnivoice.py` 实现

1. 如果是 api请求，则必须实现的函数只有一个`def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:`

`data_item` 是一条字幕的数据字典，`{filename:配音文件最终需生成该名,role:界面中显示的配音角色名称,text:需配音的文字}`
可参考`_openrouter.py`的实现

```
@dataclass
class NewAITTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_key = params.get('newai_key')
        self.speed=self.get_speed()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
	
	def _download(self):
```

2. 如果是本地模型，则必须实现的函数只有一个`def _exec(self):`,所有需要配音的字幕列表字典存在在
self.queue_tts中，具体可参考`_omnivoice.py实现`
```
@dataclass
class NewAiTTS(BaseTTS):
	def _exec(self):
        for it in self.queue_tts:
	def _download(self):
```

如果该渠道需要下载模型到本地，还需实现 `def _download(self):`方法，模型下载到`{ROOT_DIR}/models` 目录下，`{ROOT_DIR}`变量来自 `videotrans.configure.config`，具体可参考 `_omnivoice.py`文件


如果所有配音角色，不因语言变化而不同，可直接定义在`videotrans/configure/constant.py`中，在 `videotrans/util/help_role.py` 的`def role_menu()`方法中，返回配音角色名的list。
```
#configure/constant.py
OPENAITTS_ROLES = "alloy,ash,ballad,coral,echo,fable,onyx,nova,sage,shimmer,verse"

```


为减少复杂性，角色名建议直接使用api请求时的实际声音id(例如有的渠道配音角色显示为描述性的自然语言名称，而实际却需要传递英文id，则需要再次映射转换)

如果角色因语言不同而变化，建议编制一个json文件，key是语言代码，参考`videotrans/voicejson/kokoro.json`，
```
{
	"en":["voice_id1","voice_id2"],
	...
}

```
语言代码参考 `videotrans/configure/_languages_dict.py`的`EDGE_LANGUANGES_CODE`变量

