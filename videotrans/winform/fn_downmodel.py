import json
import os
from pathlib import Path

import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox
from py7zr import SevenZipFile

from videotrans.configure import config
from videotrans.recognition import OPENAI_WHISPER, FASTER_WHISPER
from videotrans.util import tools

# 分块下载
class DownloadPartThread(QThread):
    uito = Signal(str)

    def __init__(self, url, save_dir, local_filename, start_range, end_range, part_num, proxy=None):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self.local_filename = local_filename
        self.start_range = start_range
        self.end_range = end_range
        self.part_num = part_num
        self.proxy = proxy

    def run(self):
        try:
            headers = {'Range': f'bytes={self.start_range}-{self.end_range}'}
            response = requests.get(self.url, headers=headers, stream=True, proxies=self.proxy)
            progress = 0
            part_filename = f"{self.local_filename}.part{self.part_num}"
            with open(part_filename, 'wb') as part_file:
                for data in response.iter_content(1024):  # 每次下载 1KB
                    part_file.write(data)
                    progress += len(data)
                    self.uito.emit(f'jindu:{self.part_num}:{progress}')
        except Exception as e:
            self.uito.emit(json.dumps({
                "type": "error",
                "text": f"Part {self.part_num} : {str(e)}"
            }))
# 下载线程，在此分块 4个线程下载
class Down(QThread):
    uito = Signal(str)

    def __init__(self, url, save_dir, proxy=None, parent=None):
        super().__init__(parent=parent)
        self.url = url
        self.save_dir = save_dir
        self.proxy = {"http": proxy, 'https': proxy} if proxy else None
        self.total_size = 0
        self.progress_size = 0
        self.part_nums = {"0": 0, "1": 0, "2": 0, "3": 0}

    def post(self, d):
        # 获取总进度
        if d.startswith("jindu:"):
            d_split = d.split(':')
            self.part_nums[d_split[1]] = int(d_split[2])
            if self.total_size > 0:
                self.uito.emit(json.dumps({
                    "type": "progress",
                    "text": f"{sum(self.part_nums.values()) / self.total_size * 100:.2f}%"
                }))
            return
        self.uito.emit(d)

    def run(self):
        try:
            # 获取文件名
            local_filename = os.path.join(self.save_dir, self.url.split('/')[-1])
            local_filename=local_filename.split('?')[0]
            # 获取文件大小
            # 通过 Range 请求来获取文件大小
            response = requests.get(self.url, headers={'Range': 'bytes=0-1'}, stream=True, proxies=self.proxy)
            if 'Content-Range' not in response.headers:
                self.post(json.dumps({"type":"error","text":"无法通过 Range 请求获取文件大小，服务器可能不支持" if config.defaulelang=='zh' else "Failed to get file size via Range request, server may not support"}))
                return
            total_size = int(response.headers['Content-Range'].split('/')[1])
            self.total_size = total_size

            # 计算每个线程下载的块大小
            num_threads = 4
            block_size = total_size // num_threads

            # 启动多个线程下载不同的部分
            threads = []
            for i in range(num_threads):
                start_range = i * block_size
                # 最后一块可能比其他块稍大
                end_range = (i + 1) * block_size - 1 if i < num_threads - 1 else total_size - 1
                thread = DownloadPartThread(self.url, self.save_dir, local_filename, start_range, end_range, i, self.proxy)
                self.part_nums[str(i)] = 0
                thread.uito.connect(self.post)
                threads.append(thread)
                thread.start()

            # 等待所有线程下载完成
            for thread in threads:
                thread.wait()
            self.post(json.dumps({"type": 'progress', "text": '下载完毕，合并中' if config.defaulelang=='zh' else 'Download complete & Merger in progress'}))
            # 合并所有下载的部分
            with open(local_filename, 'wb') as final_file:
                for i in range(num_threads):
                    part_file = f"{local_filename}.part{i}"
                    with open(part_file, 'rb') as pf:
                        final_file.write(pf.read())
                    try:
                        os.remove(part_file)  # 删除部分文件
                    except:
                        pass


            # 下载完成后判断是否为 .7z 文件并解压
            if local_filename.endswith('.7z'):
                self.post(
                    json.dumps({"type": 'extract', "text": ''}))
                with SevenZipFile(local_filename, 'r') as archive:
                    archive.extractall(path=self.save_dir)
                Path(local_filename).unlink(missing_ok=True)

            self.post(json.dumps({"type": 'end', "text": ''}))
        except Exception as e:
            self.post(json.dumps({"type": 'error', "text": str(e)}))


def openwin(model_name=None, recogn_type=None):
    if recogn_type not in [OPENAI_WHISPER, FASTER_WHISPER]:
        return

    from videotrans.component import DownloadModelForm

    def feed(info):
        info = json.loads(info)
        if info['type'] == 'end':
            winobj.online_btn.setText("下载完毕" if config.defaulelang == 'zh' else 'Download Complete')
            winobj.online_btn.setDisabled(False)
        elif info['type'] == 'error':
            QMessageBox.critical(winobj, config.transobj['anerror'], info['text'])
            winobj.online_btn.setText("下载失败" if config.defaulelang == 'zh' else 'Download fail')
            winobj.online_btn.setDisabled(False)
        elif info['type'] == 'extract':
            winobj.online_btn.setText('正在解压' if config.defaulelang == 'zh' else 'Extracting')
        else:
            winobj.online_btn.setText(info['text'])

    def start_down():
        url = winobj.url.text()
        winobj.online_btn.setDisabled(True)
        winobj.online_btn.setText('开始下载模型...' if config.defaulelang=='zh' else 'Start downloading model...')
        proxy = winobj.proxy.text().strip()
        task = Down(url, config.ROOT_DIR + '/models', proxy if proxy else None, winobj)
        task.uito.connect(feed)
        task.start()

    try:
        winobj = DownloadModelForm()
        config.child_forms['down_win'] = winobj
        if recogn_type == OPENAI_WHISPER:
            name = f'OpenAI Whisper:  {model_name} {"模型" if config.defaulelang=="zh" else "Model" }'
            url = config.MODELS_DOWNLOAD['openai'][model_name]
            text_help = f'请下载  {model_name}.pt 后将该文件复制到 {config.ROOT_DIR}/models 文件夹内' if config.defaulelang == 'zh' else f'Please download {model_name}.pt and copy the file to {config.ROOT_DIR}/models folder.'
        else:
            name = f'Faster Whisper:  {model_name} {"模型" if config.defaulelang=="zh" else "Model" }'
            url = config.MODELS_DOWNLOAD['faster'][model_name]
            zipname = url.split('/')[-1].replace('?download=true', '')
            folder_name = f'models--Systran--faster-whisper-{model_name}'
            if model_name=='large-v3-turbo': 
                folder_name = f'models--mobiuslabsgmbh--faster-whisper-{model_name}'
            elif model_name.startswith('distil'):
                folder_name = f'models--Systran--faster-{model_name}'
            text_help = f'如果在线下载失败，请点击打开浏览器下载，下载 {zipname} 后将该压缩包内的文件夹 {folder_name} 复制到 {config.ROOT_DIR}/models 文件夹内' if config.defaulelang == 'zh' else f'Please download {zipname}, open the zip file, and copy the folder {folder_name} into {config.ROOT_DIR}/models folder.'

        winobj.label_name.setText(name)
        winobj.url.setText(url)
        winobj.text_help.setPlainText(text_help)
        winobj.down_btn.clicked.connect(lambda: tools.open_url(url=url))
        winobj.online_btn.clicked.connect(start_down)
        if 'proxy' in config.params and config.params['proxy']:
            winobj.proxy.setText(config.params['proxy'])
        winobj.show()
    except Exception as e:
        print(e)
