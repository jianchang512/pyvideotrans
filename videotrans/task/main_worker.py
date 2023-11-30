
# task process thread
import copy
import json
import os
import shutil
import threading

from PyQt5.QtCore import QThread, pyqtSignal
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import logger
from videotrans.task.trans_create import TransCreate
from videotrans.util.tools import set_process, delete_temp, get_subtitle_from_srt, text_to_speech, \
    ms_to_time_string, speed_change


class Worker(QThread):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self) -> None:
        task_nums=len(config.queue_task)
        num=0
        while len(config.queue_task)>0:
            num+=1
            it=config.queue_task.pop(0)
            set_process(f"<br><strong>:::开始处理第{num}个视频(共{task_nums}个):【{it['source_mp4']}】</strong>")
            set_process(f"正在处理第{num}个视频(共{task_nums}个):【{it['source_mp4']}】",'statusbar')
            self.video=TransCreate(it)
            self.video.run()
        set_process(f"<br><strong>本次任务全部结束</strong><br>",'end')

# 仅有字幕输入进行配音，没有视频输入
class WorkerOnlyDubbing(QThread):
    update_ui = pyqtSignal(str)
    def __init__(self, obj,parent=None):
        super().__init__(parent=parent)
        self.obj=obj
        self.noextname=obj['noextname']
        self.target_dir=obj['target_dir']+f"/{self.noextname}"
        self.cache_folder=f"{config.rootdir}/tmp/{self.noextname}"
        self.sub_name=self.cache_folder+f"/{self.noextname}.srt"
        self.tts_wav=self.cache_folder+f"/{self.noextname}.wav"
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir,exist_ok=True)
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder,exist_ok=True)

    # 执行入口
    def run(self):
        # 创建临时文件目录
        try:
            set_process(f"开始配音前数据处理操作:{self.obj['tts_type']}", 'logs')
            # 只创建配音
            res=self.before_tts()
            if not res:
                return set_process(f"[error]:配音前处理数据时出错:", "error")
            # 检测是否还有
        except Exception as e:
            logger.error("error:" + str(e))
            set_process(f"[error]:配音时出错:" + str(e), "error")
            return False

        try:
            set_process(f"开始配音操作:{self.obj['tts_type']}", 'logs')
            # 只创建配音
            self.exec_tts(res)
            set_process(f"配音完毕,清理临时文件", 'logs')
            delete_temp(self.noextname)
            # 检测是否还有
            set_process("任务结束", "end")
        except Exception as e:
            logger.error("error:" + str(e))
            set_process(f"[error]:配音时出错:" + str(e), "error")
    # noextname，无后缀的mp4文件名字
    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
        # 如果仅仅生成配音，则不限制时长
        # 整合一个队列到 exec_tts 执行
        queue_tts = []
        # 获取字幕
        subs = get_subtitle_from_srt(self.sub_name)
        logger.info(f"Creating TTS wav {self.tts_wav}")
        rate = int(str(self.obj['voice_rate']).replace('%', ''))
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for it in subs:
            if config.current_status != 'ing':
                set_process('停止了', 'stop')
                return False
            queue_tts.append({
                "text": it['text'],
                "role": self.obj['voice_role'],
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "rate": rate,
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "filename": f"{self.cache_folder}/tts-{it['start_time']}.mp3"})
        return queue_tts

    # 执行 tts配音，配音后根据条件进行视频降速或配音加速处理
    def exec_tts(self, queue_tts):
        queue_copy = copy.deepcopy(queue_tts)
        logger.info(f'{queue_copy=}')
        set_process(f"准备进行 {self.obj['tts_type']} 语音合成，角色:{self.obj['voice_role']}", 'logs')
        def get_item(q):
            return {"text": q['text'], "role": q['role'], "rate": q['rate'], "filename": q["filename"],
                    "tts_type": self.obj['tts_type']}

        # 需要并行的数量3
        while len(queue_tts) > 0:
            if config.current_status != 'ing':
                return False
            try:
                tolist = [threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0)))]
                if len(queue_tts) > 0:
                    tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))
                if len(queue_tts) > 0:
                    tolist.append(threading.Thread(target=text_to_speech, kwargs=get_item(queue_tts.pop(0))))

                for t in tolist:
                    t.start()
                for t in tolist:
                    t.join()
            except Exception as e:
                config.current_status = 'stop'
                set_process(f'[error]语音识别出错了:{str(e)}', 'error')
                return False
        segments = []
        start_times = []
        # 如果设置了视频自动降速 并且有原音频，需要视频自动降速
        if len(queue_copy) < 1:
            return set_process(f'出错了，{queue_copy=}', 'error')
        try:
            # 偏移时间，用于每个 start_time 增减
            offset = 0
            # 将配音和字幕时间对其，修改字幕时间
            logger.info(f'{queue_copy=}')
            srtmeta=[]
            for (idx, it) in enumerate(queue_copy):
                srtmeta_item={
                    'dubbing_time':-1,
                    'source_time':-1,
                    'speed_up':-1,
                }
                logger.info(f'\n\n{idx=},{it=}')
                set_process(f"<br>befor: {it['startraw']=},{it['endraw']=}")
                it['start_time'] += offset
                it['end_time'] += offset
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                if not os.path.exists(it['filename']) or os.path.getsize(it['filename']) == 0:
                    start_times.append(it['start_time'])
                    segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                    set_process(f"[error]: 此 {it['startraw']} - {it['endraw']} 时间段内字幕合成语音失败", 'logs')

                    queue_copy[idx] = it
                    continue
                audio_data = AudioSegment.from_file(it['filename'], format="mp3")
                mp3len = len(audio_data)

                # 原字幕发音时间段长度
                wavlen = it['end_time'] - it['start_time']

                if wavlen == 0:
                    queue_copy[idx] = it
                    continue
                # 新配音时长
                srtmeta_item['dubbing_time'] = mp3len
                srtmeta_item['source_time'] = wavlen
                srtmeta_item['speed_up'] = 0
                # 新配音大于原字幕里设定时长
                diff = mp3len - wavlen
                set_process(f"{diff=},{mp3len=},{wavlen=}")
                if diff > 0 and self.obj['voice_autorate']:
                    speed = mp3len / wavlen
                    speed = 1.8 if speed > 1.8 else speed
                    srtmeta_item['speed_up'] = speed
                    # 新的长度
                    mp3len = mp3len / speed
                    diff = mp3len - wavlen
                    if diff < 0:
                        diff = 0
                    set_process(f"自动加速配音 {speed} 倍<br>")
                    # 音频加速 最大加速2倍
                    audio_data = speed_change(audio_data, speed)
                    # 增加新的偏移
                    offset += diff
                elif diff > 0:
                    offset += diff
                set_process(f"newoffset={offset}")
                it['end_time'] = it['start_time'] + mp3len
                it['startraw'] = ms_to_time_string(ms=it['start_time'])
                it['endraw'] = ms_to_time_string(ms=it['end_time'])
                queue_copy[idx] = it
                set_process(f"after: {it['startraw']=},{it['endraw']=}")
                start_times.append(it['start_time'])
                segments.append(audio_data)
                srtmeta.append(srtmeta_item)

            # 更新字幕
            srt = ""
            for (idx, it) in enumerate(queue_copy):
                srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
            with open(self.sub_name, 'w', encoding="utf-8") as f:
                f.write(srt.strip())
            # 字幕保存到目标文件夹一份
            with open(f'{self.target_dir}/{self.noextname}.srt', 'w', encoding="utf-8") as f:
                f.write(srt.strip())
            # 保存字幕元信息
            with open(f"{self.target_dir}/srt.json", 'w', encoding="utf-8") as f:
                f.write("dubbing_time=配音时长，source_time=原时长,speed_up=配音加速为原来的倍数\n-1表示无效，0代表未变化，无该字段表示跳过\n" + json.dumps(
                    srtmeta))
            # 原 total_length==0，说明没有上传视频，仅对已有字幕进行处理，不需要裁切音频
            self.merge_audio_segments(segments, start_times)
        except Exception as e:
            set_process(f"[error] exec_tts 合成语音有出错:" + str(e),'error')
            return False
        return True

    # join all short audio to one ,eg name.mp4  name.mp4.wav
    def merge_audio_segments(self, segments, start_times):
        merged_audio = AudioSegment.empty()
        # start is not 0
        if start_times[0] != 0:
            silence_duration = start_times[0]
            silence = AudioSegment.silent(duration=silence_duration)
            merged_audio += silence

        # join
        for i in range(len(segments)):
            segment = segments[i]
            start_time = start_times[i]
            # add silence
            if i > 0:
                previous_end_time = start_times[i - 1] + len(segments[i - 1])
                silence_duration = start_time - previous_end_time
                # 前面一个和当前之间存在静音区间
                if silence_duration > 0:
                    silence = AudioSegment.silent(duration=silence_duration)
                    merged_audio += silence

            merged_audio += segment
        # 创建配音后的文件
        merged_audio.export(self.tts_wav, format="wav")
        shutil.copy(
            self.tts_wav,
            f"{self.target_dir}/{self.noextname}.wav"
        )
        return merged_audio
