import os
import torch
import torch._dynamo
torch._dynamo.config.suppress_errors = True
torch._dynamo.config.cache_size_limit = 64
torch._dynamo.config.suppress_errors = True
torch.set_float32_matmul_precision('high')
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

import datetime
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
load_dotenv()


from modelscope import snapshot_download
from videotrans.tts.chatTTSModule import ChatTTS
from videotrans.tts.chatTTSModule.uilib.cfg import LOGS_DIR, MODEL_DIR, ROOT_DIR

CHATTTS_DIR= MODEL_DIR+'/pzc163/chatTTS'
# 默认从 modelscope 下载模型,如果想从huggingface下载模型，请将以下代码注释掉
# 如果已存在则不再下载和检测更新，便于离线内网使用
if not os.path.exists(CHATTTS_DIR+"/config/path.yaml"):
    snapshot_download('pzc163/chatTTS',cache_dir=MODEL_DIR)
chat = ChatTTS.Chat()
device=os.getenv('device','default')
chat.load_models(source="local",local_path=CHATTTS_DIR, device=None if device=='default' else device,compile=True if os.getenv('compile','true').lower()!='false' else False)

# 如果希望从 huggingface.co下载模型，将以下注释删掉。将上方3行内容注释掉
# 如果已存在则不再下载和检测更新，便于离线内网使用
#CHATTTS_DIR=MODEL_DIR+'/models--2Noise--ChatTTS'
#if not os.path.exists(CHATTTS_DIR):
    #import huggingface_hub
    #os.environ['HF_HUB_CACHE']=MODEL_DIR
    #os.environ['HF_ASSETS_CACHE']=MODEL_DIR
    #huggingface_hub.snapshot_download(cache_dir=MODEL_DIR,repo_id="2Noise/ChatTTS", allow_patterns=["*.pt", "*.yaml"])
    # chat = ChatTTS.Chat()
    # chat.load_models(source="local",local_path=CHATTTS_DIR, compile=True if os.getenv('compile','true').lower()!='false' else False)


# 配置日志
# 禁用 Werkzeug 默认的日志处理器
log = logging.getLogger('werkzeug')
log.handlers[:] = []
log.setLevel(logging.WARNING)

root_log = logging.getLogger()  # Flask的根日志记录器
root_log.handlers = []
root_log.setLevel(logging.WARNING)
# 创建 RotatingFileHandler 对象，设置写入的文件路径和大小限制
file_handler = RotatingFileHandler(LOGS_DIR+f'/{datetime.datetime.now().strftime("%Y%m%d")}.log', maxBytes=1024 * 1024, backupCount=5)
# 创建日志的格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 设置文件处理器的级别和格式
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(formatter)