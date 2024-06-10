# import os
# import re
# import sys
# from pathlib import Path
# import torch
# import torch._dynamo
# torch._dynamo.config.suppress_errors = True
# torch._dynamo.config.cache_size_limit = 64
# torch._dynamo.config.suppress_errors = True
# torch.set_float32_matmul_precision('high')
# os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

# import soundfile as sf
# # import ChatTTS
# import datetime
# from dotenv import load_dotenv
# from flask import Flask, request, render_template, jsonify,  send_from_directory
# import logging
# from logging.handlers import RotatingFileHandler
# from waitress import serve
# load_dotenv()


# from random import random
# from modelscope import snapshot_download
# import numpy as np
# import time
# import threading
# from uilib.cfg import WEB_ADDRESS, SPEAKER_DIR, LOGS_DIR, WAVS_DIR, MODEL_DIR, ROOT_DIR
# from uilib import utils,VERSION

# CHATTTS_DIR= MODEL_DIR+'/pzc163/chatTTS'
# 默认从 modelscope 下载模型,如果想从huggingface下载模型，请将以下代码注释掉
# 如果已存在则不再下载和检测更新，便于离线内网使用
# if not os.path.exists(CHATTTS_DIR+"/config/path.yaml"):
#     snapshot_download('pzc163/chatTTS',cache_dir=MODEL_DIR)
# chat = ChatTTS.Chat()
# device=os.getenv('device','default')
# chat.load_models(source="local",local_path=CHATTTS_DIR, device=None if device=='default' else device,compile=True if os.getenv('compile','true').lower()!='false' else False)

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
# log = logging.getLogger('werkzeug')
# log.handlers[:] = []
# log.setLevel(logging.WARNING)

# app = Flask(__name__, 
#     static_folder=ROOT_DIR+'/static', 
#     static_url_path='/static',
#     template_folder=ROOT_DIR+'/templates')

# root_log = logging.getLogger()  # Flask的根日志记录器
# root_log.handlers = []
# root_log.setLevel(logging.WARNING)
# app.logger.setLevel(logging.WARNING) 
# # 创建 RotatingFileHandler 对象，设置写入的文件路径和大小限制
# file_handler = RotatingFileHandler(LOGS_DIR+f'/{datetime.datetime.now().strftime("%Y%m%d")}.log', maxBytes=1024 * 1024, backupCount=5)
# # 创建日志的格式
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# # 设置文件处理器的级别和格式
# file_handler.setLevel(logging.WARNING)
# file_handler.setFormatter(formatter)
# # 将文件处理器添加到日志记录器中
# app.logger.addHandler(file_handler)
# app.jinja_env.globals.update(enumerate=enumerate)

# @app.route('/static/<path:filename>')
# def static_files(filename):
#     return send_from_directory(app.config['STATIC_FOLDER'], filename)


# @app.route('/')
# def index():
#     return render_template("index.html",weburl=WEB_ADDRESS,version=VERSION)


# # 根据文本返回tts结果，返回 filename=文件名 url=可下载地址
# # 请求端根据需要自行选择使用哪个
# # params:
# #
# # text:待合成文字
# # prompt：
# # voice：音色
# # custom_voice：自定义音色值
# # skip_refine: 1=跳过refine_text阶段，0=不跳过
# # is_split: 1=启用中英分词，同时将数字转为对应语言发音，0=不启用
# # temperature
# # top_p
# # top_k
# # speed
# # text_seed
# # refine_max_new_token
# # infer_max_new_token
# @app.route('/tts', methods=['GET', 'POST'])
# def tts():
#     # 原始字符串
#     text = request.args.get("text","").strip() or request.form.get("text","").strip()
#     prompt = request.args.get("prompt","").strip() or request.form.get("prompt",'')

#     # 默认值
#     defaults = {
#         "custom_voice": 0,
#         "voice": 2222,
#         "temperature": 0.3,
#         "top_p": 0.7,
#         "top_k": 20,
#         "skip_refine": 0,
#         "speed":5,
#         "text_seed":42,
#         "is_split": 0,
#         "refine_max_new_token": 384,
#         "infer_max_new_token": 2048,
#     }

#     # 获取
#     custom_voice = utils.get_parameter(request, "custom_voice", defaults["custom_voice"], int)
#     voice = custom_voice if custom_voice > 0 else utils.get_parameter(request, "voice", defaults["voice"], int)
#     temperature = utils.get_parameter(request, "temperature", defaults["temperature"], float)
#     top_p = utils.get_parameter(request, "top_p", defaults["top_p"], float)
#     top_k = utils.get_parameter(request, "top_k", defaults["top_k"], int)
#     skip_refine = utils.get_parameter(request, "skip_refine", defaults["skip_refine"], int)
#     is_split = utils.get_parameter(request, "is_split", defaults["is_split"], int)
#     speed = utils.get_parameter(request, "speed", defaults["speed"], int)
#     text_seed = utils.get_parameter(request, "text_seed", defaults["text_seed"], int)
#     refine_max_new_token = utils.get_parameter(request, "refine_max_new_token", defaults["refine_max_new_token"], int)
#     infer_max_new_token = utils.get_parameter(request, "infer_max_new_token", defaults["infer_max_new_token"], int)
        
        
    
#     app.logger.info(f"[tts]{text=}\n{voice=},{skip_refine=}\n")
#     if not text:
#         return jsonify({"code": 1, "msg": "text params lost"})
#     # 固定音色
#     rand_spk=utils.load_speaker(voice)
#     if rand_spk is None:    
#         print(f'根据seed={voice}获取随机音色')
#         torch.manual_seed(voice)
#         std, mean = torch.load(f'{CHATTTS_DIR}/asset/spk_stat.pt').chunk(2)
#         #rand_spk = chat.sample_random_speaker()        
#         rand_spk = torch.randn(768) * std + mean
#         # 保存音色
#         utils.save_speaker(voice,rand_spk)
#     else:
#         print(f'固定音色 seed={voice}')

#     audio_files = []
    

#     start_time = time.time()
    
#     # 中英按语言分行
#     text_list=[t.strip() for t in text.split("\n") if t.strip()]
#     new_text=text_list if is_split==0 else utils.split_text(text_list)
#     if text_seed>0:
#         torch.manual_seed(text_seed)
#     print(f'{text_seed=}')
#     print(f'[speed_{speed}]')
#     wavs = chat.infer(new_text, use_decoder=True, skip_refine_text=True if int(skip_refine)==1 else False,params_infer_code={
#         'spk_emb': rand_spk,
#         'prompt':f'[speed_{speed}]',
#         'temperature':temperature,
#         'top_P':top_p,
#         'top_K':top_k,
#         'max_new_token':infer_max_new_token
#     }, params_refine_text= {'prompt': prompt,'max_new_token':refine_max_new_token},do_text_normalization=False)

#     end_time = time.time()
#     inference_time = end_time - start_time
#     inference_time_rounded = round(inference_time, 2)
#     print(f"推理时长: {inference_time_rounded} 秒")

#     # 初始化一个空的numpy数组用于之后的合并
#     combined_wavdata = np.array([], dtype=wavs[0][0].dtype)  # 确保dtype与你的wav数据类型匹配

#     for wavdata in wavs:
#         combined_wavdata = np.concatenate((combined_wavdata, wavdata[0]))

#     sample_rate = 24000  # Assuming 24kHz sample rate
#     audio_duration = len(combined_wavdata) / sample_rate
#     audio_duration_rounded = round(audio_duration, 2)
#     print(f"音频时长: {audio_duration_rounded} 秒")
    
    
#     filename = datetime.datetime.now().strftime('%H%M%S_')+f"use{inference_time_rounded}s-audio{audio_duration_rounded}s-seed{voice}-te{temperature}-tp{top_p}-tk{top_k}-textlen{len(text)}-{str(random())[2:7]}" + ".wav"
#     sf.write(WAVS_DIR+'/'+filename, combined_wavdata, 24000)

#     audio_files.append({
#         "filename": WAVS_DIR + '/' + filename,
#         "url": f"http://{request.host}/static/wavs/{filename}",
#         "inference_time": inference_time_rounded,
#         "audio_duration": audio_duration_rounded
#     })
#     result_dict={"code": 0, "msg": "ok", "audio_files": audio_files}
#     try:
#         if torch.cuda.is_available():
#             torch.cuda.empty_cache()
#     except Exception:
#         pass
#     # 兼容pyVideoTrans接口调用
#     if len(audio_files)==1:
#         result_dict["filename"]=audio_files[0]['filename']
#         result_dict["url"]=audio_files[0]['url']

#     return jsonify(result_dict)




# @app.route('/clear_wavs', methods=['POST'])
# def clear_wavs():
#     dir_path = 'static/wavs'  # wav音频文件存储目录
#     success, message = utils.ClearWav(dir_path)
#     if success:
#         return jsonify({"code": 0, "msg": message})
#     else:
#         return jsonify({"code": 1, "msg": message})

# try:
#     host = WEB_ADDRESS.split(':')
#     print(f'启动:{WEB_ADDRESS}')
#     threading.Thread(target=utils.openweb,args=(f'http://{WEB_ADDRESS}',)).start()
#     serve(app,host=host[0], port=int(host[1]))
# except Exception as e:
#     print(e)

