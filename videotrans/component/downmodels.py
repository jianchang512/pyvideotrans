from videotrans.configure import config
import os
if config.proxy:
    os.environ['HTTPS_PROXY']=config.proxy
import sys
import tempfile
import zipfile
import shutil
from pathlib import Path

from PySide6.QtWidgets import (QApplication,QWidget, QVBoxLayout, QPushButton, 
                               QProgressBar, QLabel, QMessageBox, QHBoxLayout, 
                               QFrame, QScrollArea)
from PySide6.QtCore import Qt, QThread, Signal, Slot,QTimer
from PySide6.QtGui import QIcon,QShowEvent
import platform
from urllib.parse import urlparse

MODEL_DIR=f'{config.ROOT_DIR}/models/'



CN_LANGDICT = {
    "app_title": "模型下载",
    "header_title": "可在此手动下载所需模型",
    "header_tips": "vits/piper/m2m100渠道模型需在使用前手动点击下载，其他模型使用时自动下载\n可从 https://pvt9.com/huggingface  页面查看模型下载地址",
    
    "section_tts": "vits/piper/M2M100渠道模型(需使用前下载)",
    "section_openai": "语音识别openai-whisper渠道模型(使用时自动下载)",
    "section_faster": "语音识别faster-whisper渠道模型(使用时自动下载)",

    # 按钮与状态
    "btn_start": "开始下载",
    "btn_redownload": "重新下载",
    "btn_download_model": "下载模型",
    "btn_stop": "停止 ⏹",
    "btn_stopping": "停止中...",
    
    "status_not_downloaded": "未下载",
    "status_installed": "✔ 已下载",
    "status_connecting": "连接中: {}...",
    "status_downloading": "下载中: {} ({})", # 文件名, 进度
    "status_extracting": "正在解压...",
    "status_cancelled": "已取消",
    "status_failed": "❌ 失败",
    "status_success": "✔ 完成",
    "status_multi_progress": "文件 [{}/{}]", # 第几个/共几个
    
    "msg_success_title": "成功",
    "msg_error_title": "下载出错了",
    "msg_install_success": "全部处理完成",
    "msg_user_stopped": "用户已停止下载",
    "msg_task_finished": "[{}] 下载部署完成！",
    "msg_task_failed": "模型 [{}] 下载失败:\n{}",
    
    "err_no_py7zr": "需要解压.7z文件但未安装 py7zr",
    "err_format": "文件格式错误",
    
    
    "task_m2m":"m2m100翻译模型(1.0G)",
    "task_realtime":"实时语音识别模型(0.9G)",
    "task_piper":"piper TTS配音模型(6.4G)",
    "task_vits":"vits 配音模型(540M)",
    
    "xiazaishibai_shoudong":"请手动打开以下网址(已复制到剪贴板)\n{}\n将.json/.txt/.bin 等文件下载到目录：\n{} ",
    "zip_xiazaishibai_shoudong":"请手动打开以下网址(已复制到剪贴板)\n{}\n下载后解压zip压缩包得到 [{}] 文件夹，将该文件夹复制到目录：\n{} ",
    "pt_xiazaishibai_shoudong":"请手动打开以下网址(已复制到剪贴板)\n{}\n将下载的 [{}] 文件复制到目录：\n{} "
}

EN_LANGDICT = {
    "app_title": "Models Downloader",
    "header_title": "Manually download the required models here",

    "header_tips": "Download vits/piper/m2m100 before use; other models will be automatically downloaded upon use\nThe model download link can be found at https://pvt9.com/huggingface",

    "section_tts": "vits/piper/M2M100 models (required for download before use)",

    "section_openai": "Models required for the openai-whisper channel (will be automatically downloaded upon use)",

    "section_faster": "Models required for the faster-whisper channel (will be automatically downloaded upon use)",

    "btn_start": "Download",
    "btn_redownload": "Redownload",
    "btn_download_model": "Download",
    "btn_stop": "Stop ⏹",
    "btn_stopping": "Stopping...",
    
    "status_not_downloaded": "Not Downloaded",
    "status_installed": "✔ Installed",
    "status_connecting": "Connecting: {}...",
    "status_downloading": "Downloading: {} ({})",
    "status_extracting": "Extracting...",
    "status_cancelled": "Cancelled",
    "status_failed": "❌ Failed",
    "status_success": "✔ Done",
    "status_multi_progress": "File [{}/{}]",
    
    "msg_success_title": "Success",
    "msg_error_title": "Download Error",
    "msg_install_success": "All Done",
    "msg_user_stopped": "User Stopped",
    "msg_task_finished": "[{}] Finished!",
    "msg_task_failed": "[{}] model download Failed:\n{}",
    
    "err_no_py7zr": "py7zr not installed for .7z files",
    "err_format": "File format error",
    
    "task_m2m":"m2m100 translation model(1.0G)",
    "task_realtime":"Realtime STT model(0.9G)",
    "task_piper":"Piper TTS model(6.4G)",
    "task_vits":"VITS TTS model(540M)",
    
    "xiazaishibai_shoudong":"Download failed. Please manually open the following URL (already copied to clipboard)\n{}\nDownload the .json/.txt/.bin files to the directory:\n{} ",

    "zip_xiazaishibai_shoudong":"Download failed. Please manually open the following URL (already copied to clipboard)\n{}\nAfter downloading, unzip the zip archive to get the [{}] folder. Copy this folder to the directory:\n{} ",

    "pt_xiazaishibai_shoudong":"Download failed. Please manually open the following URL (already copied to clipboard)\n{}\nCopy the downloaded [{}] file to the directory:\n{} "
}

LANG_CODE = config.defaulelang 
TRANS = CN_LANGDICT if LANG_CODE == 'zh' else EN_LANGDICT

# ==========================================
# 1. 核心逻辑
# ==========================================
HAS_7Z = False

class DownloadWorker(QThread):
    progress_signal = Signal(int)       
    status_signal = Signal(str)         
    finished_signal = Signal(bool, str) 

    def __init__(self, task_data):
        super().__init__()
        self.task = task_data

    def get_filename_from_url(self, url):
        """解析URL获取纯净文件名 (去除 ?query)"""
        parsed = urlparse(url)
        return os.path.basename(parsed.path)

    def run(self):
        try:
            if config.proxy:
                os.environ['HTTPS_PROXY']=config.proxy
            import requests

            # 1. 解析任务类型
            target_dir = Path(self.task["dir"])
            target_dir.mkdir(parents=True, exist_ok=True)

            urls_to_process = [] # List of (url, save_path, is_archive)

            # 情况 A: Faster Whisper (多个 URL)
            if "urls" in self.task:
                # 判断能否联通 huggingface.co，如果不能，则使用镜像 hf-mirror.com 替换
                hf_mirror=False
                if 'huggingface.co' in self.task['urls'][0]:
                    self.status_signal.emit(f"check huggingface.co ...")
                    try:
                        requests.head('https://huggingface.co',timeout=5)
                    except Exception:
                        print(f'无法联通 huggingface.co, 使用镜像 hf-mirror.com 替换')
                        self.status_signal.emit(f"use hf-mirror.com")
                        hf_mirror=True
                    else:
                        print('可以使用 huggingface.co')
                        
                for url in self.task["urls"]:
                    if hf_mirror:
                        url=url.replace('https://huggingface.co','https://hf-mirror.com')
                    fname = self.get_filename_from_url(url)
                    # Faster Whisper 的文件直接保存到 target_dir
                    urls_to_process.append({
                        "url": url,
                        "path": target_dir / fname,
                        "extract": False
                    })
            
            # 情况 B: 单个 URL (VITS/OpenAI 等)
            elif "url" in self.task:
                url = self.task["url"]
                fname = self.get_filename_from_url(url)
                
                is_archive = fname.lower().endswith(('.zip', '.7z'))
                
                # 如果是压缩包，暂存到临时文件，否则直接保存到目标
                if is_archive:
                    # 压缩包逻辑：保存路径不重要，重要的是解压逻辑
                    urls_to_process.append({
                        "url": url, 
                        "path": None, # 临时处理
                        "extract": True,
                        "fname": fname
                    })
                else:
                    # 单文件逻辑 (OpenAI pt): 直接保存
                    urls_to_process.append({
                        "url": url,
                        "path": target_dir / fname,
                        "extract": False
                    })

            total_files = len(urls_to_process)
            
            # 2. 开始遍历下载
            for index, item in enumerate(urls_to_process):
                if self.isInterruptionRequested(): raise UserWarning(TRANS["msg_user_stopped"])

                url = item["url"]
                display_name = item.get("fname", item["path"].name if item["path"] else "Archive")
                
                # 更新大状态
                prefix_status = ""
                if total_files > 1:
                    prefix_status = TRANS["status_multi_progress"].format(index + 1, total_files) + " "

                self.status_signal.emit(f"{prefix_status}{TRANS['status_connecting'].format(display_name)}")

                # --- 下载过程 ---
                with requests.get(url, stream=True, timeout=60) as response:
                    response.raise_for_status()
                    total_length = response.headers.get('content-length')
                    
                    # 决定写入目标：如果是需要解压的，写入临时文件；否则直接写入目标文件
                    if item["extract"]:
                        dest_file_obj = tempfile.TemporaryFile() # 内存/临时磁盘，自动删除
                    else:
                        dest_file_obj = open(item["path"], 'wb')

                    try:
                        if total_length is None:
                            dest_file_obj.write(response.content)
                        else:
                            total_length = int(total_length)
                            downloaded = 0
                            for chunk in response.iter_content(chunk_size=8192):
                                if self.isInterruptionRequested(): raise UserWarning(TRANS["msg_user_stopped"])
                                if chunk:
                                    dest_file_obj.write(chunk)
                                    downloaded += len(chunk)
                                    
                                    # 计算进度
                                    # 单文件进度 0-100
                                    file_percent = (downloaded / total_length)
                                    
                                    # 总进度： (当前文件索引 + 当前文件进度) / 总文件数 * 100
                                    # 如果是解压任务，预留 20% 给解压过程
                                    if item["extract"]:
                                        current_p = (index + file_percent * 0.8) / total_files * 100
                                    else:
                                        current_p = (index + file_percent) / total_files * 100
                                    
                                    self.progress_signal.emit(int(current_p))
                    finally:
                        if not item["extract"]:
                            dest_file_obj.close() # 关闭实体文件句柄

                    # --- 解压过程 (如果需要) ---
                    if item["extract"]:
                        self.status_signal.emit(TRANS["status_extracting"])
                        dest_file_obj.seek(0) # 回到文件头
                        
                        fname = item["fname"]
                        if fname.endswith('.7z'):
                            if not HAS_7Z: raise ImportError(TRANS["err_no_py7zr"])
                        else:
                            with zipfile.ZipFile(dest_file_obj) as zf:
                                zf.extractall(path=target_dir)
                        
                        # 解压完成，补齐进度
                        self.progress_signal.emit(int((index + 1) / total_files * 100))
                        dest_file_obj.close() # 显式关闭触发删除

            if not self.isInterruptionRequested():
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, TRANS["msg_install_success"])

        except UserWarning:
            self.finished_signal.emit(False, "STOPPED")
        except Exception as e:
            msg=str(e)
            # faster-whisper 模型 多个文件
            if 'hf-mirror.com' in urls_to_process[0]['url'] or 'huggingface.co' in urls_to_process[0]['url']:
                downurl=urls_to_process[0]['url'].split('/resolve/main')[0]+"/tree/main"
                msg=f'{TRANS["xiazaishibai_shoudong"].format(downurl,self.task["dir"])}\n\n{msg}'
                QApplication.clipboard().setText(downurl)
            elif urls_to_process[0]['url'].endswith('.zip'):
                # zip 文件
                msg=TRANS['zip_xiazaishibai_shoudong'].format(urls_to_process[0]['url'],self.task.get('zip_folder',''),self.task['dir'])
                QApplication.clipboard().setText(urls_to_process[0]['url'])
            else:
                # openai-whisper 模型，单个pt文件
                msg=TRANS['pt_xiazaishibai_shoudong'].format(urls_to_process[0]['url'],self.task['name'],self.task['dir'])
                QApplication.clipboard().setText(urls_to_process[0]['url'])
            
            self.finished_signal.emit(False, msg)

# ==========================================
# 2. 任务组件
# ==========================================
class TaskWidget(QFrame):
    def __init__(self, task_info):
        super().__init__()
        self.task = task_info
        self.worker = None
        self.setFrameShape(QFrame.StyledPanel)
        # 稍微调整样式，使其在列表中紧凑一些
        self.setStyleSheet(".TaskWidget { border-radius: 6px; border: 1px solid #666; margin-bottom: 2px; }")
        
        self.init_ui()
        self.check_status()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 第一行
        header_layout = QHBoxLayout()
        self.title_label = QLabel(self.task["name"])

        
        self.status_label = QLabel(TRANS["status_not_downloaded"])
        self.status_label.setStyleSheet("color: #999; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header_layout.addWidget(self.title_label, 1) # 权重1
        header_layout.addWidget(self.status_label, 0)
        
        # 第二行：进度条
        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setStyleSheet("QProgressBar { height: 6px; border-radius: 3px; background: #666; } QProgressBar::chunk { background: #0078d7; border-radius: 3px; }")

        # 第三行：按钮
        self.action_btn = QPushButton(TRANS["btn_start"])
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.clicked.connect(self.toggle_download)
        self.style_btn_normal()

        self.layout.addLayout(header_layout)
        self.layout.addWidget(self.pbar)
        self.layout.addWidget(self.action_btn)

    def check_status(self):
        path = Path(self.task["check"])
        if path.exists():
            self.status_label.setText(TRANS["status_installed"])
            self.status_label.setStyleSheet("color: green;")
            self.action_btn.setText(TRANS["btn_redownload"])
        else:
            self.status_label.setText(TRANS["status_not_downloaded"])
            self.status_label.setStyleSheet("color: #999;")
            self.action_btn.setText(TRANS["btn_download_model"])

    def update_status(self):
        path = Path(self.task["check"])
        if path.exists():
            self.status_label.setText(TRANS["status_installed"])
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText(TRANS["status_not_downloaded"])
            self.status_label.setStyleSheet("color: #999;")

    def toggle_download(self,is_auto=False):
        if self.worker and self.worker.isRunning():
            if is_auto:
                return
            self.worker.requestInterruption()
            self.action_btn.setEnabled(False)
            self.action_btn.setText(TRANS["btn_stopping"])
        else:
            self.start_download()

    def start_download(self):
        self.pbar.setValue(0)
        self.pbar.setVisible(True)
        self.style_btn_stop()
        self.status_label.setStyleSheet("color: #ff0;")
        
        self.worker = DownloadWorker(self.task)
        self.worker.progress_signal.connect(self.pbar.setValue)
        self.worker.status_signal.connect(self.status_label.setText)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, msg):
        # 【关键修复】: 必须先等待线程安全退出，才能清理引用
        if self.worker:
            self.worker.wait() # 阻塞等待线程 run 方法完全返回
            self.worker = None
            
        self.style_btn_normal()
        
        if success:
            self.status_label.setText(TRANS["status_success"])
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.pbar.setVisible(False)
            self.check_status()
            
        elif msg == "STOPPED":
            self.status_label.setText(TRANS["status_cancelled"])
            self.status_label.setStyleSheet("color: #999;")
            self.pbar.setVisible(False)
            self.check_status()
        else:
            self.status_label.setText(TRANS["status_failed"])
            self.status_label.setStyleSheet("color: red;")
            self.pbar.setVisible(False)
            QMessageBox.critical(self, TRANS["msg_error_title"], TRANS["msg_task_failed"].format(self.task['name'], msg))

    def style_btn_normal(self):
        self.action_btn.setEnabled(True)
        # 稍微缩小一点按钮高度
        self.action_btn.setFixedHeight(30)
        self.action_btn.setStyleSheet("""
            QPushButton { background-color: #0078d7; color: white; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #0063b1; }
        """)
        # 文字由 check_status 决定

    def style_btn_stop(self):
        self.action_btn.setText(TRANS["btn_stop"])
        self.action_btn.setStyleSheet("""
            QPushButton { background-color: #e81123; color: white; border-radius: 4px; border: none;}
            QPushButton:hover { background-color: #c50f1f; }
        """)

# ==========================================
# 3. 主窗口
# ==========================================
class DownmodelsWindow(QWidget):
    def __init__(self,init_name=None):
        super().__init__()
        self.setWindowTitle(TRANS["app_title"])
        self.resize(550, 650) # 增加高度
        self.setWindowIcon(QIcon(f"{config.ROOT_DIR}/videotrans/styles/icon.ico"))
        self.task_obj={}
        self.show_num=0
        # 数据定义
        self.init_data()
        self.init_ui()

    def init_data(self):
        # 1. 原始 ZIP/7Z 任务
        self.tasks_zip = [
            {
                "name": TRANS.get("task_vits"),
                "zip_folder":"vits",
                "url": "https://modelscope.cn/models/himyworld/videotrans/resolve/master/vits-tts.zip",
                "dir": MODEL_DIR,
                "check": f"{MODEL_DIR}vits/zh_en/model.onnx"
            },
            {
                "name": TRANS.get("task_piper"),
                "zip_folder":"piper",
                "url": "https://modelscope.cn/models/himyworld/videotrans/resolve/master/piper-tts.zip",
                "dir": MODEL_DIR,
                "check": f"{MODEL_DIR}piper/zh"
            },
            {
                "name": TRANS.get("task_m2m"),
                "zip_folder":"m2m100_12b",
                "url": "https://modelscope.cn/models/himyworld/videotrans/resolve/master/m2m100_12b_model.zip",
                "dir": MODEL_DIR,
                "check": f"{MODEL_DIR}m2m100_12b/model.bin"
            },
            {
                "name": TRANS.get("task_realtime"),
                "zip_folder":"onnx",                
                "url": "https://modelscope.cn/models/himyworld/videotrans/resolve/master/realtimestt.zip",
                "dir": f"{MODEL_DIR}",
                "check": f"{MODEL_DIR}onnx/encoder.onnx"
            }
        ]
        
        # 2. OpenAI Whisper (单文件 PT)
        self.tasks_openai = [
             {
            "name":"tiny.en.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/d3dd57d32accea0b295c96e26691aa14d8822fac7d9d27d5dc00b4ca2826dd03/tiny.en.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}tiny.en.pt"
            },
            {
            "name":"tiny.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}tiny.pt"
            },
            {
            "name":"base.en.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}base.en.pt"
            },
            {
            "name":"base.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}base.pt"
            },
            {
            "name":"small.en.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}small.en.pt"
            },
            {
            "name":"small.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}small.pt"
            },
            {
            "name":"medium.en.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}medium.en.pt"
            },
            {
            "name":"medium.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}medium.pt"
            },
            {
            "name":"large-v1.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}large-v1.pt"
            },
            {
            "name":"large-v2.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}large-v2.pt"
            },
            {
            "name":"large-v3.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}large-v3.pt"
            },
            {
            "name":"large-v3-turbo.pt", "url":"https://openaipublic.azureedge.net/main/whisper/models/aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a/large-v3-turbo.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}large-v3-turbo.pt"
            },
        ]

        # 3. Faster Whisper (多文件列表)
        self.tasks_faster = [
            {
                "name":"tiny.en",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-tiny.en",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-tiny.en/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"tiny",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-tiny",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-tiny/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"base.en",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-base.en",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-base.en/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-base.en/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base.en/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base.en/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base.en/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"base",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-base",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-base/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-base/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"small.en",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-small.en",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-small.en/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-small.en/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small.en/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small.en/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small.en/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"small",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-small",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-small/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"medium.en",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-medium.en",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-medium.en/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-medium.en/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium.en/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium.en/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium.en/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"medium",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-medium",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-medium/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-medium/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"large-v1",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-large-v1",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-large-v1/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-large-v1/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v1/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v1/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v1/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"large-v2",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-large-v2",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-large-v2/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-large-v2/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v2/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v2/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v2/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"large-v3",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-large-v3",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-large-v3/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/preprocessor_config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/vocabulary.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"large-v3-turbo",
                "dir":f"{MODEL_DIR}models--mobiuslabsgmbh--faster-whisper-large-v3-turbo",
                "check":f"{MODEL_DIR}models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/model.bin",
                "urls": [
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/config.json?download=true',
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/preprocessor_config.json?download=true',
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/vocabulary.json?download=true',
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"distil-large-v3.5",
                "dir":  f"{MODEL_DIR}models--distil-whisper--distil-large-v3.5-ct2",
                "check":f"{MODEL_DIR}models--distil-whisper--distil-large-v3.5-ct2/model.bin",
                "urls":[
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/config.json?download=true',
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/preprocessor_config.json?download=true',
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/tokenizer.json?download=true',
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/vocabulary.json?download=true',
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/model.bin?download=true',
                ]
            }
        ]
        

    def init_ui(self):
        # 外层布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # 1. 顶部固定区域
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        title = QLabel(TRANS["header_title"])
        title.setStyleSheet("color: #fff; font-size: 16px;")
        
        title.setAlignment(Qt.AlignCenter)
        
        tips = QLabel(TRANS["header_tips"])
        tips.setWordWrap(True)
        tips.setStyleSheet("color: #eee; font-size: 12px;")
        tips.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(tips)
        outer_layout.addWidget(header_widget)

        # 2. 滚动区域 (核心修改点)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True) # 关键：让内部 widget 自适应宽度
        scroll.setFrameShape(QFrame.NoFrame)
        
        # 滚动区域的内容容器
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(5)


        # 添加第一组：TTS & ZIP
        self._add_section_header(TRANS["section_tts"])
        for task in self.tasks_zip:
            t=TaskWidget(task)
            self.task_obj[task['zip_folder']]=t
            self.content_layout.addWidget(t)

        self._add_section_header(TRANS["section_openai"])
        scroll.setWidget(content_widget)
        outer_layout.addWidget(scroll)
        self.show()
        QTimer.singleShot(500,self._second_init)

    def _second_init(self):
        for task in self.tasks_openai:
            t=TaskWidget(task)
            self.task_obj[task['name']]=t
            self.content_layout.addWidget(t)

        self._add_section_header(TRANS["section_faster"])
        for task in self.tasks_faster:
            t=TaskWidget(task)
            self.task_obj[task['name']]=t
            self.content_layout.addWidget(t)

            self.content_layout.addStretch() # 底部弹簧

    def auto_start(self,zip_folder=None):
        if zip_folder and zip_folder in self.task_obj and hasattr(self.task_obj[zip_folder],'toggle_download'):
            print(f'{zip_folder=}')
            self.task_obj[zip_folder].toggle_download(True)
    
    def refresh_data(self):
        if self.task_obj:
            for k,v in self.task_obj.items():
                v.update_status()
    
    def _add_section_header(self,text):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("padding: 8px; font-weight: bold; font-size:14px; color: #fff; margin-top: 10px; border-radius: 4px;")
        self.content_layout.addWidget(lbl)
    
    def showEvent(self, event: QShowEvent):
        self.show_num+=1
        """
        当窗口显示时（包括第一次显示和从隐藏恢复显示），会自动调用此方法
        """
        super().showEvent(event)
        
        if self.show_num>1:
            self.refresh_data()

    
    def closeEvent(self, event):
        self.hide()
        event.ignore()
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 

    window = DownmodelsWindow()
    window.show()
    sys.exit(app.exec())