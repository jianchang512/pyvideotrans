# -*- coding: utf-8 -*-
# primary ui
import copy
import hashlib
import json
import os
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import homedir
from videotrans.tts import run as run_tts
from videotrans.util import tools
from videotrans.util.tools import get_subtitle_from_srt, ms_to_time_string


# 合成
class WorkerTTS(QThread):
    uito = Signal(str)

    def __init__(self, *,
                 files=None,
                 role=None,
                 rate=None,
                 volume="+0%",
                 pitch="+0Hz",
                 wavname=None,
                 tts_type=None,
                 voice_autorate=False,
                 langcode=None,
                 parent=None):
        super(WorkerTTS, self).__init__(parent)
        self.volume = volume
        self.pitch = pitch
        self.all_text = []
        self.files = files
        self.role = role
        self.rate = rate
        self.wavname = wavname
        self.tts_type = tts_type
        self.langcode = langcode
        self.voice_autorate = voice_autorate
        self.tmpdir = f'{homedir}/tmp'
        Path(self.tmpdir).mkdir(parents=True,exist_ok=True)
        md5_hash = hashlib.md5()
        md5_hash.update(f"{time.time()}{role}{rate}{volume}{pitch}{voice_autorate}{len(files)}{tts_type}{langcode}".encode('utf-8'))
        self.uuid = md5_hash.hexdigest()
        self.end=False

    def run(self):
        config.box_tts = 'ing'
        def getqueulog(uuid):
            while 1:
                if self.end or config.exit_soft:
                    return
                q = config.queue_dict.get(uuid)
                if not q:
                    continue
                try:
                    data = q.get(True, 0.5)
                    if data:
                        print(f'@@@@@@@@@@@@@@@@@@@@@@@@@@@@{data=}')
                        self.post(data)
                except Exception:
                    pass

        threading.Thread(target=getqueulog, args=(self.uuid,)).start()
        # 字幕格式
        self.all_text = []
        for it in self.files:
            content = ""
            try:
                with open(it, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            except:
                with open(it, 'r', encoding='gbk') as f:
                    content = f.read().strip()
            finally:
                if content:
                    self.all_text.append({"text": content, "file": os.path.basename(it)})
        try:
            errs, success = self.before_tts()
            config.box_tts = 'stop'
            if success == 0:
                self.post({"type":"error","text":'全部失败了请打开输出目录中txt文件查看失败记录'})
            elif errs > 0:
                self.post({"type":"error","text":f"error:失败{errs}个，成功{success}个，请查看输出目录中txt文件查看失败记录"})
        except Exception as e:
            self.post({"type":"error","text":f'error:{str(e)}'})


        config.box_tts = 'stop'
        self.post({"type":"ok","text":""})

    def post(self,jsondata):
        self.uito.emit(json.dumps(jsondata))
    # 1. 将每个配音的实际长度加入 dubb_time
    #
    def _add_dubb_time(self, queue_tts):
        for i, it in enumerate(queue_tts):
            # 防止开始时间比上个结束时间还小
            if i > 0 and it['start_time'] < queue_tts[i - 1]['end_time']:
                it['start_time'] = queue_tts[i - 1]['end_time']
            # 防止结束时间小于开始时间
            if it['end_time'] < it['start_time']:
                it['end_time'] = it['start_time']
            # 保存原始
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']
            # 记录原字母区间时长
            it['raw_duration'] = it['end_time'] - it['start_time']

            if tools.vail_file(it['filename']):
                the_ext = it['filename'].split('.')[-1]
                it['dubb_time'] = len(
                    AudioSegment.from_file(it['filename'], format="mp4" if the_ext == 'm4a' else the_ext))
            else:
                # 不存在配音
                it['dubb_time'] = 0
            queue_tts[i] = it

        return queue_tts

    # 2.  移除原字幕多于配音的时长，实际是字幕结束时间向前移动，和下一条之间的空白更加多了
    def _remove_srt_silence(self, queue_tts):
        # 如果需要移除多出来的静音
        for i, it in enumerate(queue_tts):
            # 配音小于 原时长，移除默认静音
            if it['dubb_time'] > 0 and it['dubb_time'] < it['raw_duration']:
                diff = it['raw_duration'] - it['dubb_time']
                it['end_time'] -= diff
                it['raw_duration'] = it['dubb_time']
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
            queue_tts[i] = it
        return queue_tts

    #   移除2个字幕间的间隔 config.settings[remove_white_ms] ms
    def _remove_white_ms(self, queue_tts):
        config.settings['remove_white_ms'] = int(config.settings['remove_white_ms'])
        offset = 0
        for i, it in enumerate(queue_tts):
            if i > 0:
                it['start_time'] -= offset
                it['end_time'] -= offset
                # 配音小于 原时长，移除默认静音
                dt = it['start_time'] - queue_tts[i - 1]['end_time']
                if dt > config.settings['remove_white_ms']:
                    diff = config.settings['remove_white_ms'] if config.settings['remove_white_ms'] > -1 else dt
                    it['end_time'] -= diff
                    it['start_time'] -= diff
                    offset += diff
                it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                queue_tts[i] = it
        return queue_tts

    # 2. 先对配音加速，每条字幕信息中写入加速倍数 speed和延长的时间 add_time
    def _ajust_audio(self, queue_tts):
        # 遍历所有字幕条， 计算应该的配音加速倍数和延长的时间
        # 设置加速倍数
        for i, it in enumerate(queue_tts):
            it['speed'] = False
            # 存在配音时进行处理 没有配音
            if it['dubb_time'] <= 0:
                queue_tts[i] = it
                continue
            # 字幕可用时长
            # 经过移除空白等处理后的字幕时长
            it['raw_duration'] = it['end_time'] - it['start_time']
            # 配音时长 不大于 原时长，不处理
            if it['raw_duration'] <= 0 or it['dubb_time'] <= it['raw_duration']:
                queue_tts[i] = it
                continue

            it['speed'] = True
            queue_tts[i] = it

        # 再次遍历，调整字幕开始结束时间对齐实际音频时长
        # 每次 start_time 和 end_time 需要添加的长度 offset 为当前所有 add_time 之和
        for i, it in enumerate(queue_tts):
            # 需要音频加速，否则跳过
            if not it['speed'] or config.settings['audio_rate'] <= 1:
                it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                queue_tts[i] = it
                continue

            if tools.vail_file(it['filename']):
                # 调整音频
                tmp_mp3 = os.path.join(self.tmpdir, f'{it["filename"]}-speed.mp3')
                # 需要加速的倍数如果大于2，并且大于1s才需要判断是否视频慢速，否则不慢速，以避免过差效果
                speed = it['dubb_time'] / it['raw_duration']
                # 确定变化后的配音时长，如果倍数低于 audio_rate 限制，则设为原字幕时长，否则设定 配音时长/最大倍数
                audio_extend = it['raw_duration'] if speed <= float(config.settings['audio_rate']) else int(
                    it['dubb_time'] / float(config.settings['audio_rate']))
                tools.precise_speed_up_audio(file_path=it['filename'], out=tmp_mp3,
                                             target_duration_ms=audio_extend,
                                             max_rate=100)

                # 获取实际加速完毕后的真实配音时长，因为精确度原因，未必和上述计算出的一致
                # 如果视频需要变化，更新视频时长需要变化的长度
                if tools.vail_file(tmp_mp3):
                    mp3_len = len(AudioSegment.from_file(tmp_mp3, format="mp3"))
                    it['dubb_time'] = mp3_len
                    it['filename'] = tmp_mp3

            # 更改时间戳
            it['startraw'] = ms_to_time_string(ms=it['start_time'])
            it['endraw'] = ms_to_time_string(ms=it['end_time'])
            queue_tts[i] = it
        return queue_tts

    # 配音预处理，去掉无效字符，整理开始时间
    def before_tts(self):
        # 所有临时文件均产生在 tmp/无后缀mp4名文件夹
        # 如果仅仅生成配音，则不限制时长
        # 整合一个队列到 exec_tts 执行
        length = len(self.all_text)
        errs = 0
        config.settings['remove_white_ms'] = int(config.settings['remove_white_ms'])
        jd=0
        for n, item in enumerate(self.all_text):
            jd+=(n/length)
            queue_tts = []
            # 获取字幕
            self.post({"type":"replace","text":item["text"]})
            subs = get_subtitle_from_srt(item["text"], is_file=False)

            # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
            sub_len=len(subs)
            self.post({"type":"jd","text":f'{round(jd*100,2)}%'})
            for k,it in enumerate(subs):
                queue_tts.append({
                    "text": it['text'],
                    "role": self.role,
                    "start_time": it['start_time'],
                    "end_time": it['end_time'],
                    "rate": self.rate,
                    "startraw": it['startraw'],
                    "endraw": it['endraw'],
                    "tts_type": self.tts_type,
                    "language": self.langcode,
                    "pitch": self.pitch,
                    "volume": self.volume,
                    "filename": f"{self.tmpdir}/tts-{time.time()}-{it['start_time']}.mp3"})
            try:
                run_tts(queue_tts=copy.deepcopy(queue_tts), language=self.langcode, set_p=True,uuid=self.uuid)

                # 1.首先添加配音时间
                queue_tts = self._add_dubb_time(queue_tts)

                # 2.移除字幕多于配音的时间，实际上是字幕结束时间前移，和下一条字幕空白更多
                if config.settings['remove_srt_silence']:
                    queue_tts = self._remove_srt_silence(queue_tts)

                # 4. 如果需要配音加速
                if self.voice_autorate:
                    queue_tts = self._ajust_audio(queue_tts)

                # 5.从字幕间隔移除多余的毫秒数
                if config.settings['remove_white_ms'] > 0:
                    queue_tts = self._remove_white_ms(queue_tts)
                # 开始合并音频
                segments = []
                for i, it in enumerate(queue_tts):
                    if os.path.exists(it['filename']) and os.path.getsize(it['filename']) > 0:
                        segments.append(AudioSegment.from_file(it['filename'], format="mp3"))
                    else:
                        segments.append(AudioSegment.silent(duration=it['end_time'] - it['start_time']))
                self.merge_audio_segments(segments=segments, video_time=0, queue_tts=copy.deepcopy(queue_tts), out=f'{self.wavname}-{item["file"]}.wav')

            except Exception as e:
                errs += 1
                with open(f'{self.wavname}-error.txt', 'w', encoding='utf-8') as f:
                    f.write(f'srt文件 {item["file"]} 合成失败，原因为:{str(e)}\n\n原字幕内容为\n\n{item["text"]}')
                self.post({"type":"logs","text":f'srt文件 {item["file"]} 合成失败，原因为:{str(e)}\n\n原字幕内容为\n\n{item["text"]}'})
        return errs, length - errs

    def merge_audio_segments(self, *, segments=None, queue_tts=None, video_time=0, out=None):
        merged_audio = AudioSegment.empty()
        # start is not 0
        if queue_tts[0]['start_time'] > 0:
            silence_duration = queue_tts[0]['start_time']
            silence = AudioSegment.silent(duration=silence_duration)
            merged_audio += silence
        # join
        offset = 0
        for i, it in enumerate(queue_tts):
            segment = segments[i]
            the_dur = len(segment)
            # 字幕可用时间
            raw_dur = it['raw_duration']
            it['start_time'] += offset
            it['end_time'] += offset

            diff = the_dur - raw_dur
            # 配音大于字幕时长，后延，延长时间
            if diff >= 0:
                it['end_time'] += diff
                offset += diff

            if i > 0:
                silence_duration = it['start_time'] - queue_tts[i - 1]['end_time']
                # 前面一个和当前之间存在静音区间
                if silence_duration > 0:
                    silence = AudioSegment.silent(duration=silence_duration)
                    merged_audio += silence
            it['startraw'] = ms_to_time_string(ms=it['start_time'])
            it['endraw'] = ms_to_time_string(ms=it['end_time'])
            queue_tts[i] = it
            merged_audio += segment

        # 创建配音后的文件
        try:
            merged_audio.export(out, format="wav")
        except Exception as e:
            raise Exception(f'merge_audio:{str(e)}')
        return len(merged_audio), queue_tts
