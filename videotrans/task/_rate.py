import os
import shutil
import time
from pathlib import Path

from pydub import AudioSegment

from videotrans.configure import config
from videotrans.util import tools

'''
对配音进行音频加速
对视频进行慢速
实现对齐操作
'''


class SpeedRate:

    def __init__(self,
                 *,
                 queue_tts=None,
                 shoud_videorate=False,
                 shoud_audiorate=False,
                 uuid=None,
                 novoice_mp4=None,
                 noextname=None,
                 # 处理后的配音文件
                 target_audio=None,
                 cache_folder=None
                 ):
        self.novoice_mp4 = novoice_mp4
        self.queue_tts = queue_tts
        self.shoud_videorate = shoud_videorate
        self.shoud_audiorate = shoud_audiorate
        config.logger.info(f'SpeedRate1:{noextname=}')
        self.noextname = noextname
        self.uuid = uuid
        self.target_audio = target_audio
        self.cache_folder = cache_folder if cache_folder else config.TEMP_DIR + f'/{uuid if uuid else time.time()}'
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)
        config.logger.info(f'SpeedRate2:{self.cache_folder=},{self.noextname=}')

    def run(self):
        self._add_dubb_time()
        if config.settings['remove_srt_silence']:
            self._remove_srt_silence()
        config.settings['remove_white_ms'] = int(config.settings['remove_white_ms'])
        if config.settings['remove_white_ms'] > 0:
            self._remove_white_ms()
        # 4. 如果需要配音加速
        if self.shoud_audiorate and int(config.settings['audio_rate']) > 1:
            self._ajust_audio()
        if self.shoud_videorate:
            self._ajust_video()
        self._merge_audio_segments()
        return self.queue_tts

    # 1. 将每个配音的实际长度加入 dubb_time
    def _add_dubb_time(self):
        length = len(self.queue_tts)
        for i, it in enumerate(self.queue_tts):
            if it is None:
                continue
            tools.set_process(text=f"audio:{i + 1}/{length}", uuid=self.uuid)
            # 防止开始时间比上个结束时间还小
            if i > 0 and it['start_time'] < self.queue_tts[i - 1]['end_time']:
                it['start_time'] = self.queue_tts[i - 1]['end_time']
            # 防止结束时间小于开始时间
            if it['end_time'] < it['start_time']:
                it['end_time'] = it['start_time']
            # 保存原始字幕时间戳
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']
            # 记录原始字幕区间时长,不随去除字幕间空白、加速等变化，永远固定
            it['raw_duration_source'] = it['end_time'] - it['start_time']

            # 会随去除字幕间空白、加速等变化
            it['raw_duration'] = it['end_time'] - it['start_time']

            # -1代表未经过音频加速，仅仅进行视频慢速处理
            # 0 代表经过了音频慢速，但是视频无需加速
            # >0 需要视频慢放到的实际时长
            it['video_extend'] = -1

            # 记录实际配音后，未经任何处理的真实配音时长
            if tools.vail_file(it['filename']):
                the_ext = it['filename'].split('.')[-1]
                it['dubb_time'] = len(
                    AudioSegment.from_file(it['filename'], format="mp4" if the_ext == 'm4a' else the_ext))
            else:
                # 不存在配音
                it['dubb_time'] = 0
                it['video_extend'] = 0
            self.queue_tts[i] = it

    # 2.  移除原字幕多于配音的时长，实际是字幕结束时间向前移动，和下一条之间的空白更加多了
    # 配音时长不变， end_time 时间戳变化， raw_duration变化
    def _remove_srt_silence(self):
        # 如果需要移除多出来的静音
        for i, it in enumerate(self.queue_tts):
            # 配音小于 原时长，移除默认静音
            if it['dubb_time'] > 0 and it['dubb_time'] < it['raw_duration']:
                diff = it['raw_duration'] - it['dubb_time']
                it['end_time'] -= diff
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                it['raw_duration'] = it['dubb_time']
            self.queue_tts[i] = it

    #   移除2个字幕间的空白间隔 config.settings[remove_white_ms] ms
    # 配音时长不变。raw_duration不变
    def _remove_white_ms(self):
        config.settings['remove_white_ms'] = int(config.settings['remove_white_ms'])
        offset = 0
        for i, it in enumerate(self.queue_tts):
            if i > 0:
                it['start_time'] -= offset
                it['end_time'] -= offset
                # 配音小于 原时长，移除默认静音
                dt = it['start_time'] - self.queue_tts[i - 1]['end_time']
                if dt > config.settings['remove_white_ms']:
                    diff = config.settings['remove_white_ms'] if config.settings['remove_white_ms'] > -1 else dt
                    it['end_time'] -= diff
                    it['start_time'] -= diff
                    offset += diff
                it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                self.queue_tts[i] = it

    # 2. 先对配音加速，每条字幕信息中写入加速倍数 speed和延长的时间 add_time
    def _ajust_audio(self):
        # 遍历所有字幕条， 计算应该的配音加速倍数和延长的时间
        length = len(self.queue_tts)
        if self.novoice_mp4 and os.path.exists(self.novoice_mp4):
            video_time = tools.get_video_duration(self.novoice_mp4)
        else:
            video_time = self.queue_tts[-1]['end_time']
        for i, it in enumerate(self.queue_tts):
            # 是否需要音频加速
            it['speed'] = False
            # 存在配音时进行处理 没有配音
            if it['dubb_time'] <= 0 or it['end_time'] == it['start_time']:
                self.queue_tts[i] = it
                continue

            # 可用时长，从本片段开始到下一个片段开始
            able_time = self.queue_tts[i + 1]['start_time'] - it['start_time'] if i < length - 1 else video_time - it[
                'start_time']
            # 配音时长小于等于可用时长，无需加速
            if it['dubb_time'] <= able_time:
                self.queue_tts[i] = it
                continue

            it['speed'] = True
            self.queue_tts[i] = it
        # 允许最大音频加速倍数
        max_speed = float(config.settings['audio_rate'])
        for i, it in enumerate(self.queue_tts):
            # 不需要或不存在配音文件 跳过
            if not it['speed'] or not tools.vail_file(it['filename']):
                continue

            tools.set_process(text=f"{config.transobj['dubbing speed up']}  {i + 1}/{length}",
                              uuid=self.uuid)

            # 可用时长
            able_time = self.queue_tts[i + 1]['start_time'] - it['start_time'] if i < length - 1 else video_time - it[
                'start_time']
            if able_time<=0 or it['dubb_time'] <= able_time:
                continue

            # 配音大于可用时长毫秒数
            diff = it['dubb_time'] - able_time

            # 如果加速到恰好等于 able_time 时长，需要加速的倍数
            shound_speed = round(it['dubb_time'] / able_time, 2)

            # 仅当开启视频慢速，shound_speed大于1.5，diff大于1s，才考虑视频慢速
            if self.shoud_videorate and int(config.settings['video_rate']) > 1 and diff > 500 and shound_speed > 1.2:
                # 开启了视频慢速，音频加速一半
                # 音频加速一半后实际时长应该变为
                audio_extend = it['dubb_time'] - int(diff / 2)
                # 如果音频加速一半后仍然大于设定，则重新设定加速后音频时长
                if max_speed>0 and round(it['dubb_time'] / audio_extend, 2) > max_speed:
                    audio_extend = int(it['dubb_time'] / max_speed)
            else:
                # 仅处理音频加速
                if shound_speed <= max_speed:
                    audio_extend = able_time
                elif max_speed>0:
                    audio_extend = int(it['dubb_time'] / max_speed)

            # # 调整音频
            tmp_mp3 = f'{it["filename"]}-speed.mp3'
            tools.precise_speed_up_audio(file_path=it['filename'],
                                         out=tmp_mp3,
                                         target_duration_ms=audio_extend,
                                         max_rate=100)

            # 获取实际加速完毕后的真实配音时长，因为精确度原因，未必和上述计算出的一致
            # 如果视频需要变化，更新视频时长需要变化的长度
            if tools.vail_file(tmp_mp3):
                mp3_len = len(AudioSegment.from_file(tmp_mp3, format="mp3"))
                it['filename'] = tmp_mp3
                it['dubb_time'] = mp3_len
            self.queue_tts[i] = it

    # 视频慢速 在配音加速调整后，根据字幕实际开始结束时间，裁剪视频，慢速播放实现对齐
    def _ajust_video(self):
        if not self.shoud_videorate or int(config.settings['video_rate']) <= 1:
            return
        concat_txt_arr = []
        if not tools.is_novoice_mp4(self.novoice_mp4, self.noextname):
            raise Exception("not novoice mp4")
        # 获取视频时长
        last_time = tools.get_video_duration(self.novoice_mp4)
        length = len(self.queue_tts)
        max_pts = int(config.settings['video_rate'])
        # 按照原始字幕截取
        for i, it in enumerate(self.queue_tts):
            jindu = f'{i + 1}/{length}'

            # 可用的时长
            able_time = it['end_time_source'] - it['start_time_source']
            # 视频需要和配音对齐，video_extend是需要增加的时长
            it['video_extend'] = it['dubb_time'] - able_time
            self.queue_tts[i] = it

            # 如果i==0即第一个视频，前面若是还有片段，需要截取
            if i == 0:
                # 如果前面有大于 0 的片段，需截取
                if it['start_time_source'] > 0:
                    before_dst = self.cache_folder + f'/{i}-before.mp4'
                    # 下一片段起始时间
                    st_time = it['start_time_source']
                    try:
                        tools.cut_from_video(ss='00:00:00.000',
                                             to=tools.ms_to_time_string(ms=it['start_time_source']),
                                             source=self.novoice_mp4,
                                             out=before_dst)
                        concat_txt_arr.append(before_dst)
                    except Exception:
                        pass
                else:
                    # 下一片段起始时间,从视频开始处
                    st_time = 0

                # 当前视频实际时长
                duration = it['end_time_source'] - st_time
                # 是否需要延长视频
                pts = ""
                if it['video_extend'] > 0 and duration>0:
                    pts = round((it['video_extend'] + duration) / duration, 2)
                    if pts > max_pts:
                        pts = max_pts
                        it['video_extend'] = duration * max_pts - duration
                pts_text = '' if not pts or pts <= 1 else f'{pts=}'
                tools.set_process(text=f"{config.transobj['videodown..']} {pts_text} {jindu}", uuid=self.uuid)
                before_dst = self.cache_folder + f'/{i}-current.mp4'
                try:
                    tools.cut_from_video(
                        ss='00:00:00.000' if st_time == 0 else tools.ms_to_time_string(ms=st_time),
                        to=tools.ms_to_time_string(ms=it['end_time_source']),
                        source=self.novoice_mp4,
                        pts=pts,
                        out=before_dst
                    )
                    concat_txt_arr.append(before_dst)
                    it['video_extend'] = tools.get_video_duration(before_dst) - duration
                except Exception:
                    pass
            else:
                # 距离前面一个的时长
                diff = it['start_time_source'] - self.queue_tts[i - 1]['end_time_source']
                if diff > 0:
                    before_dst = self.cache_folder + f'/{i}-before.mp4'
                    st_time = it['start_time_source']
                    try:
                        tools.cut_from_video(
                            ss=tools.ms_to_time_string(ms=self.queue_tts[i - 1]['end_time_source']),
                            to=tools.ms_to_time_string(ms=it['start_time_source']),
                            source=self.novoice_mp4,
                            out=before_dst
                        )
                        concat_txt_arr.append(before_dst)
                    except Exception:
                        pass
                else:
                    st_time = self.queue_tts[i - 1]['end_time_source']

                # 是否需要延长视频
                pts = ""
                duration = it['end_time_source'] - st_time
                if it['video_extend'] > 0 and duration>0:
                    pts = round((it['video_extend'] + duration) / duration, 2)
                    if pts > max_pts:
                        pts = max_pts
                        it['video_extend'] = duration * max_pts - duration
                tools.set_process(text=f"{config.transobj['videodown..']} {pts=} {jindu}", uuid=self.uuid)
                before_dst = self.cache_folder + f'/{i}-current.mp4'

                try:
                    tools.cut_from_video(ss=tools.ms_to_time_string(ms=st_time),
                                         to=tools.ms_to_time_string(ms=it['end_time_source']),
                                         source=self.novoice_mp4,
                                         pts=pts,
                                         out=before_dst)
                    concat_txt_arr.append(before_dst)
                    it['video_extend'] = tools.get_video_duration(before_dst) - duration

                except Exception:
                    pass
                # 是最后一个，并且未到视频末尾
                if i == length - 1 and it['end_time_source'] < last_time:
                    # 最后一个
                    before_dst = self.cache_folder + f'/{i}-after.mp4'
                    try:
                        tools.cut_from_video(ss=tools.ms_to_time_string(ms=it['end_time_source']),
                                             source=self.novoice_mp4,
                                             out=before_dst)
                        concat_txt_arr.append(before_dst)
                    except Exception:
                        pass

        # 需要调整 原字幕时长，延长视频相当于延长了原字幕时长
        offset = 0
        for i, it in enumerate(self.queue_tts):
            it['start_time_source'] += offset
            it['end_time_source'] += offset
            if it['video_extend'] > 0:
                it['end_time_source'] += it['video_extend']
                offset += it['video_extend']
            self.queue_tts[i] = it

        # 将所有视频片段连接起来
        new_arr = []
        for it in concat_txt_arr:
            if tools.vail_file(it):
                new_arr.append(it)
        if len(new_arr) > 0:
            tools.set_process(text=f"连接视频片段..." if config.defaulelang == 'zh' else 'concat multi mp4 ...',
                              uuid=self.uuid)
            config.logger.info(f'视频片段:{concat_txt_arr=}')
            concat_txt = self.cache_folder + f'/{time.time()}.txt'
            tools.create_concat_txt(concat_txt_arr, concat_txt=concat_txt)
            tools.concat_multi_mp4(out=self.novoice_mp4, concat_txt=concat_txt)

    def _merge_audio_segments(self):
        video_time = 0
        if self.novoice_mp4 and Path(self.novoice_mp4).exists():
            video_time = tools.get_video_duration(self.novoice_mp4)
        merged_audio = AudioSegment.empty()
        if len(self.queue_tts) == 1:
            the_ext = self.queue_tts[0]['filename'].split('.')[-1]
            merged_audio += AudioSegment.from_file(self.queue_tts[0]['filename'],
                                                   format="mp4" if the_ext == 'm4a' else the_ext)
        else:
            # start is not 0
            if self.queue_tts[0]['start_time_source'] > 0:
                silence = AudioSegment.silent(duration=self.queue_tts[0]['start_time_source'])
                merged_audio += silence

            # 开始时间
            cur = self.queue_tts[0]['start_time_source']
            length = len(self.queue_tts)
            for i, it in enumerate(self.queue_tts):
                # 存在有效配音文件则加入，否则配音时长大于0则加入静音
                segment = None
                the_ext = it['filename'].split('.')[-1]

                # 原始字幕时长
                raw_source = it['end_time_source'] - it['start_time_source']
                if raw_source == 0:
                    continue
                # 存在配音文件
                if tools.vail_file(it['filename']):
                    segment = AudioSegment.from_file(it['filename'], format="mp4" if the_ext == 'm4a' else the_ext)
                    it['dubb_time'] = len(segment)
                else:
                    # 不存在配音文件
                    segment = AudioSegment.silent(duration=raw_source)
                    it['dubb_time'] = raw_source

                if i == 0:
                    it['start_time'] = it['start_time_source']
                    it['end_time'] = it['start_time_source'] + it['dubb_time']
                    cur = it['end_time']
                    merged_audio += segment
                else:
                    if it['start_time_source'] < cur:
                        # 如果开始时间和上一个结束片段重合
                        it['start_time'] = cur
                        it['end_time'] = it['start_time'] + it['dubb_time']
                        cur = it['end_time']
                        merged_audio += segment
                    elif it['start_time_source'] >= cur:
                        # 如果当前开始时间和上一个结束时间之间有间隔，则添加静音
                        if it['start_time_source'] > cur:
                            merged_audio += AudioSegment.silent(duration=it['start_time_source'] - cur)
                        it['start_time'] = it['start_time_source']
                        it['end_time'] = it['start_time'] + it['dubb_time']
                        merged_audio += segment
                        cur = it['end_time']

                if cur < it['end_time_source']:
                    merged_audio += AudioSegment.silent(duration=it['end_time_source'] - cur)
                    cur = it['end_time_source']
                    it['end_time'] = cur

                it['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                self.queue_tts[i] = it
                tools.set_process(text=f"{config.transobj['audio_concat']}:{i + 1}/{length}", uuid=self.uuid)

            if not self.shoud_videorate and video_time > 0 and merged_audio and (len(merged_audio) < video_time):
                # 末尾补静音
                silence = AudioSegment.silent(duration=video_time - len(merged_audio))
                merged_audio += silence

        # 创建配音后的文件
        try:
            wavfile = self.cache_folder + "/target.wav"
            merged_audio.export(wavfile, format="wav")
            ext = Path(self.target_audio).suffix.lower()
            if ext == '.wav':
                shutil.copy2(wavfile, self.target_audio)
            elif ext == '.m4a':
                tools.wav2m4a(wavfile, self.target_audio)
            else:
                cmd = [
                    "-y",
                    "-i",
                    Path(wavfile).as_posix(),
                    "-ar",
                    "48000",
                    self.target_audio
                ]
                tools.runffmpeg(cmd)

        except Exception as e:
            raise Exception(f'[error]merged_audio:{str(e)}')
