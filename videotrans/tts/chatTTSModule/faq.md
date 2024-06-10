# 常见问题与报错

**0.** 执行app.py报错 FileNotFoundError: [Errno 2] No such file or directory: '../ChatTTS-ui/models/pzc163/chatTTS/config/path.yaml

答：模型不完整，重新下载模型或者 打开 https://www.modelscope.cn/models/pzc163/chatTTS/files 下载 path.yaml 、复制到报错里显示的文件夹内 ChatTTS-ui/models/pzc163/chatTTS/config/



**1.**  MacOS 报错 `Initializing libomp.dylib, but found libiomp5.dylib already initialized`

> 答：在app.py的 `import os` 的下一行，添加代码
>   
> `os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'`


**2.**  MacOS 无报错但进度条一直百分之0 卡住不动

> 答：app.py 中 
> 
> `chat.load_models(source="local",local_path=CHATTTS_DIR)` 
> 
> 改为
> 
> `chat.load_models(source="local",local_path=CHATTTS_DIR,compile=False)`

**3.**  MacOS 报 `libomp` 相关错误

> 答：执行  `brew install libomp`

**4.**  报https相关错误 `ProxyError: HTTPSConnectionPool(host='www.modelscope.cn', port=443)`

> 答：从 modelscope 魔塔下载模型时不可使用代理，请关闭代理


**5.**  报错丢失文件 `Missing spk_stat.pt`

> 答：本项目(ChatTTS-ui)默认从 modelscope 即魔塔社区下载模型，但该库里的模型缺少 spk_stat.pt文件
> 
>   请科学上网后从
>
>   https://huggingface.co/2Noise/ChatTTS/blob/main/asset/spk_stat.pt    
> 
>  下载 spk_stat.pt， 然后复制 spk_stat.pt  到报错提示的目录下，以本项目为例，需要复制到  `models/pzc163/chatTTS/asset`  文件夹内


**6.**  报错 `Dynamo is not supported on Python 3.12`

> 答：不支持python3.12+版本，降级到 python3.10


**7.**  MacOS报错 `NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+`

> 答：执行  `brew install openssl@1.1`  
> 
>  执行   `pip install urllib3==1.26.15



**8.**  Windows上报错：`Windows not yet supported for torch.compile`

> 答：`chat.load_models(compile=False)`  改为   `chat.load_models(compile=False,device="cpu")`


**9.**   Windows上可以运行有GPU，但很慢

> 答：如果是英伟达显卡，请将cuda升级到11.8+


**10**. 下载模型时出现 proxy 类型错误

答：默认会从 modelscope 下载模型，但 modelscope 仅允许中国大陆ip下载，如果遇到 proxy 类错误，请关闭代理。如果你希望从 huggingface.co 下载模型，请打开 `app.py` 查看大约第50行-60行的代码注释。


**11.** 中英分词是怎么回事

答：如果选中中英分词，那么将会把文字中的中文和英文分离出来单独合成，同时将对应的数字 转为相应语言的文字，比如 中文下123转为一二三，英文下123转为 one two three


**12.** Runtime Error:cannot find a working triton installation 

打开 .env  将 compile=true 改为 compile=false

**13.** MacOS下无法安装 soundfile

答：打开终端，执行 `brew install libsndfile` 然后再安装 soundfile


**14.** 如何离线使用

答：

1. 使用源码部署
2. 先运行一次，确保模型下载完毕
3. 打开 app.py 大约35行， `CHATTTS_DIR = snapshot_download('pzc163/chatTTS',cache_dir=MODEL_DIR)` 改为 `CHATTTS_DIR = MODEL_DIR+"/pzc163/chatTTS"`

**15.** ChatTTS原始项目新版本有兼容问题，可能会报错 “报错 Normalizer pynini WeTextProcessing nemo_text_processing ”

解决方法：
新版使用了 nemo_text_processing  和  pynini 来处理中文，但遗憾的是，pynini压根无法在windows平台安装和使用，要使用，也只能安装在WSL子系统上。

不管给出的什么安装方式， 比如 

```
pip install pynini==2.1.5 Cython   WeTextProcessing

```

都是无法在Windows上正确安装的

![image](https://github.com/2noise/ChatTTS/assets/3378335/e32c50d1-492c-4b72-958b-78af0575e662)


----

解决方法:
打开 ChatTTS/core.py, 大约143行，注释掉接下来的7行，

![image](https://github.com/2noise/ChatTTS/assets/3378335/5bdd3dc8-0c7c-485f-b5dc-613f14917319)


问题解决

或者 chat.infer() 添加参数 do_text_normalization=False， chat.infer(do_text_normalization=False)