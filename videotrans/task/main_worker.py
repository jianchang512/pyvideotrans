
# task process thread
import os
import shutil
import threading
import time

from PyQt5.QtCore import QThread, pyqtSignal

from videotrans.configure import config
from videotrans.configure.config import transobj, logger
from videotrans.util.tools import set_process, runffmpeg, recognition_all, recognition_split, \
    delete_temp, dubbing, compos_video, delete_files, srt_translation_srt


class Worker(QThread):
    update_ui = pyqtSignal(str)
    timeid = 0

    def __init__(self, mp4path, parent=None):
        super().__init__(parent=parent)
        self.mp4path = mp4path.replace('\\', '/')
        # 是否仅仅创建字幕，既不嵌入字幕也不配音，仅仅将字幕提取出来，并翻译
        self.only_srt= config.video['subtitle_type']<1 and config.video['voice_role']=='No'
        if not self.mp4path:
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

    # 分离音频 和 novoice.mp4
    def split_wav_novicemp4(self):
        # 单独提前分离出 novice.mp4
        # 要么需要嵌入字幕 要么需要配音，才需要分离
        if not self.only_srt and not os.path.exists(self.novoice_mp4):
            print("@@@@@@@@@@@")
            ffmpegars = [
                "-y",
                "-i",
                f'"{self.mp4path}"',
                "-an",
                f'"{self.novoice_mp4}"'
            ]
            threading.Thread(target=runffmpeg, args=(ffmpegars,), kwargs={"noextname": self.noextname}).start()

        # 如果不存在音频，则分离出音频
        if not os.path.exists(self.a_name) or os.path.getsize(self.a_name) == 0:
            print('##########')
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

    # 执行入口
    def run(self):
        # 分离出音频 和无声视频
        self.split_wav_novicemp4()
        # 识别字幕，如果出错则停止,如果存在，则不需要识别
        if os.path.exists(self.sub_name) and os.path.getsize(self.sub_name) > 1:
            set_process(f"{self.noextname} 等待编辑字幕", "edit_subtitle")
            config.subtitle_end = True
        elif not self.recongn():
            return False

        # 翻译字幕，如果设置了目标语言，则翻译字幕,翻译出错则停止。未设置目标语言则不翻译并继续
        if config.video['target_language'] not in ['', '-', 'No', 'no']:
            if not self.trans():
                config.current_status = 'end'
                return
            else:
                set_process("翻译完成")
        else:
            set_process("没有选择目标语言，无需翻译")

        # 如果仅仅需要提取字幕，到此返回
        if self.only_srt:
            delete_temp(self.noextname)
            config.subtitle_end = False
            # 检测是否还有
            set_process("检测是否存在写一个任务", "check_queue")
            return
        # 生成字幕后  等待是否执行后续 配音 合并 操作 等待倒计时
        self.timeid = 0
        config.subtitle_end=True
        print(f"while 之前 {config.current_status=}")
        set_process(f"{self.noextname} 等待编辑字幕", "edit_subtitle")
        while True:
            # 检查中断请求
            if self.isInterruptionRequested() or config.current_status != 'ing':
                print(f"Interruption requested. Stopping thread......{config.current_status=}.....")
                set_process("已停止", 'stop')
                return
            # 点击了合成按钮，已触发合成命令， 已核对无误，开始合成
            if config.exec_compos:
                return self.dubbing_compos()
            # 是None 说明已修改了字幕或者点击了停止倒计时
            # 或字幕没有完成
            if self.timeid is None or not config.subtitle_end:
                time.sleep(1)
                continue

            #  self.timeid >60,超时自动合并 没有进行合成指令
            if self.timeid is not None and self.timeid >= 60:
                # 字幕已完成，则自动执行，否则重置倒计时
                if config.subtitle_end:
                    config.exec_compos = True
                    #  自动超时，先去更新字幕文件，检测条件，符合后然后设置 config.exec_compos=True,等下下轮循环
                    set_process("超时未修改字母，先去检测字幕条件，符合后，自动合成视频", 'update_subtitle')
                else:
                    self.timeid=0
                continue

            # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
            time.sleep(1)
            # 倒计时中
            if self.timeid is not None and self.timeid<60:
                self.timeid += 1
                set_process(f"{60 - self.timeid}秒后自动合并")
    # 识别出字幕
    def recongn(self):
        try:
            # 识别、创建字幕文件 删除已存在的
            if os.path.exists(self.sub_name):
                os.unlink(self.sub_name)
            # 识别为字幕
            if config.video['whisper_type'] == 'all':
                recognition_all(self.noextname)
            else:
                recognition_split(self.noextname)
            return True
        except Exception as e:
            set_process(f"语音识别出错:" + str(e),'error')
            set_process("已停止", 'stop')
        return False
    # 翻译字幕
    def trans(self):
        try:
            # 如果存在 tmp/下字幕并且源语言和目标语言相同，则不翻译
            sub_name=f"{config.rootdir}/tmp/{self.noextname}/{self.noextname}.srt"
            target_sub_name=f"{config.video['target_dir']}/{self.noextname}/{config.video['target_language']}.srt"
            print(f"{sub_name=},{config.video['source_language']=},{config.video['target_language']=}")
            if os.path.exists(sub_name) and config.video['source_language']==config.video['target_language']:
                if not os.path.exists(target_sub_name):
                    shutil.copy(sub_name,target_sub_name)
                print(f"需要返回true==============")
                return True
            # 如果不存在源语言字幕，无需翻译
            if not os.path.exists(f"{config.video['target_dir']}/{self.noextname}/{config.video['source_language']}.srt"):
                return True
            set_process("开始翻译字幕文件")
            srt_translation_srt(self.noextname)
            if config.current_status != 'ing':
                set_process("已停止", 'stop')
            return True
        except Exception as e:
            set_process(f"文字翻译出错:" + str(e), 'error')
            set_process("已停止", 'stop')
        return False

    # 执行配音、合成
    def dubbing_compos(self):
        # 如果需要配音
        if config.video['voice_role'] not in ['No','no','-']:
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
                delete_files(self.folder,'.png')
                return
        # 不需要配音，不需要嵌入字幕，则不进行合并
        if config.video['subtitle_type']<1 and config.video['voice_role'] in ['','-','No','no']:
            return False
        # 最后一步合成
        try:
            set_process(f"开始将视频、音频、字幕合并", 'logs')
            compos_video(self.noextname)
            # 检测是否还有
            set_process("检测是否存在写一个任务", "check_queue")
            delete_temp(self.noextname)
            set_process(f"<strong style='color:#00a67d;font-size:16px'>[{self.noextname}]合并结束:相关素材可在目标文件夹内查看，含字幕文件、配音文件等</strong>", 'logs')
        except Exception as e:
            set_process(f"[error]:进行最终合并时出错:" + str(e), "error")
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
            set_process(f"配音完毕,清理临时文件", 'logs')
            delete_temp(self.noextname)
            # 检测是否还有
            set_process("任务结束", "end")
        except Exception as e:
            logger.error("error:" + str(e))
            set_process(f"[error]:配音时出错:" + str(e), "error")