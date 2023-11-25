
# task process thread
import os
import shutil
import threading
import time

from PyQt5.QtCore import QThread, pyqtSignal

from videotrans.configure import config
from videotrans.configure.config import transobj, logger
from videotrans.util.tools import set_process, runffmpeg, recognition_translation_all, recognition_translation_split, \
    delete_temp, dubbing, compos_video, delete_files


class Worker(QThread):
    update_ui = pyqtSignal(str)
    timeid = 0

    def __init__(self, mp4path, parent=None):
        super().__init__(parent=parent)
        self.mp4path = mp4path.replace('\\', '/')
        # 是否仅仅创建字幕，既不嵌入字幕也不配音
        self.only_srt=config.video['subtitle_type']<1 and config.video['voice_role']=='No'

    # 执行入口
    def run(self):
        if not self.mp4path:
            # 如果存在字幕
            set_process(transobj['selectvideodir'], "stop")
            return
        # 无扩展视频名，视频后缀(mp4,MP4)
        self.noextname = os.path.splitext(os.path.basename(self.mp4path))[0]
        # 创建临时文件目录
        self.folder=f"{config.rootdir}/tmp/{self.noextname}"
        if not os.path.exists(self.folder):
            os.makedirs(self.folder, exist_ok=True)
        # 分离出的音频文件
        self.a_name = f"{self.folder}/{self.noextname}.wav"
        self.tts_wav = f"{self.folder}/tts-{self.noextname}.wav"
        # 字幕文件
        self.sub_name = f"{self.folder}/{self.noextname}.srt"
        self.novoice_mp4=f"{self.folder}/novoice.mp4"
        # 如果不存在音频，则分离出音频
        if not os.path.exists(self.a_name) or os.path.getsize(self.a_name) == 0:
            set_process(f"{self.noextname} 分析视频数据", "logs")
            runffmpeg([
                "-y",
                "-i",
                f'"{self.mp4path}"',
                "-ac",
                "1",
                f'"{self.a_name}"'
            ])
            shutil.copy(self.a_name,f"{config.video['target_dir']}/{self.noextname}/{config.video['source_language']}.wav")
        # 单独提前分离出 novice.mp4
        # 并非仅仅创建字幕，才需要分离
        if not self.only_srt and not os.path.exists(self.novoice_mp4):
            ffmpegars = [
                "-y",
                "-i",
                f'"{self.mp4path}"',
                "-an",
                f'"{self.novoice_mp4}"'
            ]
            threading.Thread(target=runffmpeg, args=(ffmpegars,), kwargs={"noextname": self.noextname}).start()
        try:
            # 识别、创建字幕文件、翻译
            if os.path.exists(self.sub_name) and os.path.getsize(self.sub_name) > 1:
                set_process(f"{self.noextname} 等待编辑字幕", "edit_subtitle")
                config.subtitle_end = True
            else:
                if os.path.exists(self.sub_name):
                    os.unlink(self.sub_name)
                if config.video['whisper_type'] == 'all':
                    recognition_translation_all(self.noextname)
                else:
                    recognition_translation_split(self.noextname)
                if config.current_status == 'ing':
                    set_process(f"{self.noextname} wait subtitle edit", "edit_subtitle")
                    config.subtitle_end = True
        except Exception as e:
            logger.error("error:" + str(e))
            set_process(f"文字识别和翻译出错:" + str(e),'error')
            set_process("已停止", 'stop')
            return
        # 仅仅创建字幕，到此返回
        if self.only_srt:
            delete_temp(self.noextname)
            # 检测是否还有
            set_process("检测是否存在写一个任务", "check_queue")
            return
        # 生成字幕后  等待是否执行后续合并操作 等待倒计时
        self.timeid = 0
        while True:
            # 检查中断请求
            if self.isInterruptionRequested() or config.current_status != 'ing':
                set_process("已停止", 'stop')
                print("Interruption requested. Stopping thread.")
                return
            # 点击了合成按钮，已触发合成命令， 已核对无误，开始合成
            if config.exec_compos:
                self.wait_subtitle()
                return
            # 是None 说明已修改了字幕或者点击了停止倒计时
            # 或字幕没有完成
            if self.timeid is None or not config.subtitle_end:
                time.sleep(1)
                continue

            #  self.timeid >60,超时自动合并 没有进行合成指令
            if self.timeid is not None and self.timeid >= 60:
                config.exec_compos = True
                #  自动超时，先去更新字幕文件，检测条件，符合后然后设置 config.exec_compos=True,等下下轮循环
                set_process("超时未修改字母，先去检测字幕条件，符合后，自动合成视频", 'update_subtitle')
                continue

            # 字幕处理完毕，未超时，等待1s，继续倒计时
            time.sleep(1)
            # 倒计时中
            if self.timeid is not None and self.timeid<60:
                self.timeid += 1
                set_process(f"{60 - self.timeid}秒后自动合并")
                continue

    # 执行配音、合成
    def wait_subtitle(self):
        try:
            set_process(f"开始配音操作:{config.video['tts_type']}", 'logs')
            dubbing(self.noextname)
        except Exception as e:
            config.current_status='stop'
            config.exec_compos = False
            set_process("[error]配音操作时出错:"+str(e), "error")
            if os.path.exists(self.tts_wav):
                os.unlink(self.tts_wav)
            delete_files(self.folder,'.mp3')
            delete_files(self.folder,'.mp4')
            return
        # 最后一步合成
        try:
            set_process(f"配音完毕，开始将视频、音频、字幕合并", 'logs')
            compos_video(self.mp4path, self.noextname)
            set_process(f"<strong style='color:#00a67d;font-size:16px'>[{self.noextname}]合并结束:相关素材可在目标文件夹内查看，含字幕文件、配音文件等</strong>", 'logs')
            # 检测是否还有
            set_process("检测是否存在写一个任务", "check_queue")
            delete_temp(self.noextname)
        except Exception as e:
            set_process(f"[error]:最终合并时出错:" + str(e), "error")
            delete_files(self.folder,'.mp3')
            delete_files(self.folder,'.mp4')
            delete_files(self.folder,'.png')



# 仅有字幕输入进行配音，没有视频输入
class WorkerOnlyDubbing(QThread):
    update_ui = pyqtSignal(str)
    def __init__(self, noextname, parent=None):
        super().__init__(parent=parent)
        self.noextname=noextname

    # 执行入口
    def run(self):
        # 创建临时文件目录
        try:
            set_process(f"开始配音操作:{config.video['tts_type']}", 'logs')
            # 只创建配音
            dubbing(self.noextname,True)
            set_process(f"配音完毕", 'logs')
            set_process(f"任务处理结束,清理临时文件", 'logs')
            delete_temp(self.noextname)
            # 检测是否还有
            set_process("任务结束", "end")
        except Exception as e:
            logger.error("error:" + str(e))
            set_process(f"[error]:配音时出错:" + str(e), "error")