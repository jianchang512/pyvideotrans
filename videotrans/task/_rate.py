import os
import shutil
import time
from pathlib import Path

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from videotrans.configure import config
from videotrans.util import tools
import concurrent.futures


'''
对配音进行音频加速
对视频进行慢速
实现对齐操作
'''


def process_audio(item):
    """处理单个音频文件"""
    try:
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
        input_file_path=item['filename']
        target_duration_ms=item["target_duration_ms"]
        
        if not Path(input_file_path).exists():
            return input_file_path,target_duration_ms,""
        
        format = input_file_path.split('.')[-1].lower()
        audio = AudioSegment.from_file(input_file_path,format=format)
        
        current_duration_ms=len(audio)

        if target_duration_ms <= 0 or current_duration_ms <= target_duration_ms:
            return input_file_path,current_duration_ms,""


        # Detect non-silent chunks
        nonsilent_chunks = detect_nonsilent(
            audio,
            min_silence_len=10,
            silence_thresh=50.0
        )

        # If we have nonsilent chunks, get the start and end of the last nonsilent chunk
        if nonsilent_chunks:
            start_index, end_index = nonsilent_chunks[-1]

            # Remove the silence from the end by slicing the audio segment
            trimmed_audio = audio[:end_index]
            if is_start and nonsilent_chunks[0] and nonsilent_chunks[0][0] > 0:
                trimmed_audio = audio[nonsilent_chunks[0][0]:end_index]
            current_duration_ms=len(trimmed_audio)
            if current_duration_ms <= target_duration_ms:
                audio.export(input_file_path, format=format)
                return input_file_path,current_duration_ms,""
            audio=trimmed_audio
            
            


        

        # 计算速度变化率
        speedup_ratio = current_duration_ms / target_duration_ms

        if speedup_ratio <= 1:
            return input_file_path,current_duration_ms,""
        rate = min(100, speedup_ratio)
        # 变速处理
        try:
            fast_audio = audio.speedup(playback_speed=rate)
            # 如果处理后的音频时长稍长于目标时长，进行剪裁
            if len(fast_audio) > target_duration_ms:
                fast_audio = fast_audio[:target_duration_ms]
        except Exception:
            fast_audio = audio[:target_duration_ms]

        fast_audio.export(input_file_path, format=format)
        return input_file_path, len(fast_audio), ""  # 文件名, 成功标志, 错误信息
    except Exception as e:
        return input_file_path, False, str(e) # 文件名, 成功标志, 错误信息



def process_video(item,codenum,crf,preset,video_hard,stop_file=None):

    try:
        if stop_file and Path(stop_file).exists():
            return
        tools.cut_from_video(ss=item['ss'],to=item['to'],source=item['rawmp4'],out=item['out'])
        if item['pts']==0:
            print(f"该片段只截取不延长:{item['out']}")
            return True,None,0,item.get('idx',-1)
        current_duration=tools.get_video_duration(item['out'])
        if current_duration<=0:
            return False,"durtion is 0",0,item.get('idx',-1)
        cmd = [
            '-y',  #覆盖输出文件
            '-i', item['out'],
            '-filter:v', f'setpts={round(0.1+(item["pts"]/current_duration),2)}*PTS',
            '-c:v', f'libx{codenum}', 
            '-crf',f'{crf}',
            '-preset',preset,
            item['out']+'-pts.mp4'
        ]
        # 使用 concat demuxer 将帧重新编码成视频片段
        tools.runffmpeg(cmd,force_cpu=not video_hard)
        shutil.copy2(item['out']+'-pts.mp4',item['out'])
        end_time=tools.get_video_duration(item['out'])
        print(f"该片段延长:{item['out']}")
        return True,None,end_time-current_duration,item.get('idx',-1)
    except Exception as e:
        print(e)
        return False,str(e),0,item.get('idx',-1)


class SpeedRate:

    def __init__(self,
                 *,
                 queue_tts=None,
                 # 是否需要视频慢速
                 shoud_videorate=False,
                 shoud_audiorate=False,
                 uuid=None,
                 novoice_mp4=None,
                 raw_total_time=0,
                 noextname=None,
                 target_audio=None,
                 cache_folder=None
                 ):
        # 原始视频时长，或用字幕配音时最后一个字幕的结束时长
        self.raw_total_time=raw_total_time
        # 如果需要视频慢速时，作为处理目标
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
        config.settings['remove_white_ms'] = int(float(config.settings.get('remove_white_ms',0)))
        if config.settings['remove_white_ms'] > 0:
            self._remove_white_ms()
        # 4. 如果需要配音加速
        if self.shoud_audiorate and int(config.settings.get('audio_rate',1)) > 1:
            self._ajust_audio()
        # 如果需要视频慢速
        if self.shoud_videorate:
            self._ajust_video()
        # 合并
        self._merge_audio_segments()
        return self.queue_tts

    # 1. 将每个配音的实际长度加入 dubb_time
    def _add_dubb_time(self):
        length = len(self.queue_tts)
        # 最后一次

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
                try:
                    it['dubb_time'] = len(AudioSegment.from_file(it['filename'], format="mp4" if the_ext == 'm4a' else the_ext))
                except CouldntDecodeError:
                    config.logger.exception(f'添加配音时长失败')
                    it['dubb_time'] = 0
                    it['video_extend'] = 0
            else:
                # 不存在配音
                it['dubb_time'] = 0
                it['video_extend'] = 0
            self.queue_tts[i] = it
        if int(config.settings.get('video_goback',1))>0:
            left_move= 0
            last_time=0
            for i, it in enumerate(self.queue_tts):
                if it is None:
                    continue
                # 每3分钟后，在第一个与前一条字幕存在空白大于50ms处，将视频向左移动该空白，防止随着时间延迟配音越来越后移
                #if i>0 and it['start_time']-last_time>=180000 and (it['start_time']-self.queue_tts[i-1]['start_time']>50):
                #    left_move+=min(it['start_time']-self.queue_tts[i-1]['start_time'],500)
                #    last_time=it['start_time']
                it['start_time']-=left_move
                it['end_time']-=left_move
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
        config.settings['remove_white_ms'] = int(float(config.settings.get('remove_white_ms',0)))
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
        raw_total_time=self.raw_total_time
        for i, it in enumerate(self.queue_tts):
            # 是否需要音频加速
            it['speed'] = False
            # 存在配音时进行处理 没有配音
            if it['dubb_time'] <= 0 or it['end_time'] == it['start_time']:
                self.queue_tts[i] = it
                continue

            # 可用时长，从本片段开始到下一个片段开始
            able_time = self.queue_tts[i + 1]['start_time'] - it['start_time'] if i < length - 1 else raw_total_time - it['start_time']
            # 配音时长小于等于可用时长，无需加速
            if it['dubb_time'] <= able_time:
                self.queue_tts[i] = it
                continue

            it['speed'] = True
            self.queue_tts[i] = it
        # 允许最大音频加速倍数
        max_speed = float(config.settings['audio_rate'])
        # 需要加速的数据
        should_speed=[]
        for i, it in enumerate(self.queue_tts):
            # 不需要或不存在配音文件 跳过
            if not it['speed'] or not tools.vail_file(it['filename']):
                continue

            

            # 可用时长
            able_time = self.queue_tts[i + 1]['start_time'] - it['start_time'] if i < length - 1 else raw_total_time - it[
                'start_time']
            if able_time<=0 or it['dubb_time'] <= able_time:
                continue

            # 配音大于可用时长毫秒数
            diff = it['dubb_time'] - able_time
            if diff<=50:
                continue

            # 如果加速到恰好等于 able_time 时长，需要加速的倍数
            shound_speed = round(it['dubb_time'] / able_time, 2)
            audio_extend=0

            # 仅当开启视频慢速，shound_speed大于1.5，diff大于1s，才考虑视频慢速
            if self.shoud_videorate and int(float(config.settings.get('video_rate',0))) > 1 and diff >= 1000 and shound_speed > 1.2:
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
            if audio_extend<=0:
                continue
            should_speed.append({"filename":it['filename'],'target_duration_ms':audio_extend})

        
        total_files = len(should_speed)
        if total_files<1:
            return
        results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(2,total_files)  ) as executor:
            futures = [executor.submit(process_audio, item.copy()) for item in should_speed]
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                if config.exit_soft:
                    return
                filename, success, error_message = future.result()
                progress = (i + 1) / total_files * 100
                tools.set_process(text=f"{config.transobj['dubbing speed up']}  {i + 1}/{total_files}",uuid=self.uuid)
                print(f"进度: {progress:.2f}%, 状态: {'成功' if success else '失败'}")
                if success is False or success is None:
                    print(f"错误信息: {error_message}")
                else:
                    results.append({filename:success})

        for i, it in enumerate(self.queue_tts):
            # 获取实际加速完毕后的真实配音时长，因为精确度原因，未必和上述计算出的一致
            # 如果视频需要变化，更新视频时长需要变化的长度
            if tools.vail_file(it['filename']) and it['filename'] in results:
                it['dubb_time'] = int(results.get(it['filename']))
            self.queue_tts[i] = it


    # 视频慢速 在配音加速调整后，根据字幕实际开始结束时间，裁剪视频，慢速播放实现对齐
    def _ajust_video(self):
        if not self.shoud_videorate or int(float(config.settings.get('video_rate',0))) <= 1:
            return
        # 获取视频时长
        length = len(self.queue_tts)
        max_pts = int(float(config.settings.get('video_rate',1)))

        # 按照原始字幕截取
        concat_txt_arr = []
        should_speed=[]
        for i, it in enumerate(self.queue_tts):
            jindu = f'{i + 1}/{length}'

            # 可用的时长
            able_time = it['end_time_source'] - it['start_time_source']
            # 视频需要和配音对齐，video_extend是需要增加的时长
            it['video_extend'] = it['dubb_time'] - able_time
            print(f"{it['video_extend']=}")
            self.queue_tts[i] = it
            sp_speed={"rawmp4":self.novoice_mp4,'pts':0}
            # 如果i==0即第一个视频，前面若是还有片段，需要截取
            if i == 0:
                # 如果前面有大于 0 的片段，需截取
                if it['start_time_source'] >= 500:
                    before_dst = self.cache_folder + f'/{i}-before.mp4'
                    # 下一片段起始时间
                    st_time = it['start_time_source']
                    try:
                        sp_speed['ss']='00:00:00.000'
                        sp_speed['to']=tools.ms_to_time_string(ms=it['start_time_source'])
                        sp_speed['out']=before_dst
                        should_speed.append(sp_speed)
                        concat_txt_arr.append(before_dst)
                        sp_speed={"rawmp4":self.novoice_mp4,'pts':0}
                    except Exception:
                        pass
                else:
                    # 下一片段起始时间,从视频开始处
                    st_time = 0

                # 当前视频实际时长
                duration = it['end_time_source'] - st_time
                # 是否需要延长视频
                if it['video_extend'] > 0 and duration>0:
                    sp_speed['pts']=it['dubb_time']
                
                before_dst = self.cache_folder + f'/{i}-current.mp4'
                sp_speed['ss']='00:00:00.000' if st_time == 0 else tools.ms_to_time_string(ms=st_time)
                sp_speed['to']=tools.ms_to_time_string(ms=it['end_time_source'])
                sp_speed['out']=before_dst
                sp_speed['idx']=i
                try:
                    concat_txt_arr.append(before_dst)
                    should_speed.append(sp_speed)
                    sp_speed={"rawmp4":self.novoice_mp4,'pts':0}
                except Exception:
                    pass
            else:
                # 距离前面一个的时长
                diff = it['start_time_source'] - self.queue_tts[i - 1]['end_time_source']
                if diff >= 500:
                    before_dst = self.cache_folder + f'/{i}-before.mp4'
                    st_time = it['start_time_source']
                    sp_speed['ss']=tools.ms_to_time_string(ms=self.queue_tts[i - 1]['end_time_source'])
                    sp_speed['to']=tools.ms_to_time_string(ms=it['start_time_source'])
                    sp_speed['out']=before_dst
                    try:
                        concat_txt_arr.append(before_dst)
                        should_speed.append(sp_speed)
                        sp_speed={"rawmp4":self.novoice_mp4,'pts':0}
                    except Exception:
                        pass
                else:
                    st_time = self.queue_tts[i - 1]['end_time_source']

                # 是否需要延长视频
                duration = it['end_time_source'] - st_time
                if it['video_extend'] > 0 and duration>0:
                    sp_speed['pts'] = it['dubb_time']
                    sp_speed['idx'] = i

                before_dst = self.cache_folder + f'/{i}-current.mp4'

                sp_speed['out']=before_dst
                sp_speed['ss']=tools.ms_to_time_string(ms=st_time)
                sp_speed['to']=tools.ms_to_time_string(ms=it['end_time_source'])
                try:
                    concat_txt_arr.append(before_dst)
                    should_speed.append(sp_speed)
                    sp_speed={"rawmp4":self.novoice_mp4,'pts':0}
                except Exception:
                    pass
                # 是最后一个，并且未到视频末尾
                if i == length - 1 and it['end_time_source'] < self.raw_total_time:
                    # 最后一个
                    before_dst = self.cache_folder + f'/{i}-after.mp4'
                    sp_speed['out']=before_dst
                    sp_speed['ss']=tools.ms_to_time_string(ms=it['end_time_source'])
                    sp_speed['to']=''
                    try:
                        concat_txt_arr.append(before_dst)
                        should_speed.append(sp_speed)
                    except Exception:
                        pass

        # 开始切片和延长
        total_files = len(should_speed)
        if total_files<1:
            return


        config.logger.info(should_speed)
        worker_nums=1
        with concurrent.futures.ProcessPoolExecutor(max_workers=worker_nums  ) as executor:
            futures = [executor.submit(process_video, item.copy(),config.settings.get('video_codec',264),config.settings.get('crf',10),config.settings.get('preset','fast'),config.settings.get('videoslow_hard',False),stop_file=config.TEMP_DIR+'/stop_porcess.txt') for item in should_speed]
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                if config.exit_soft or config.current_status!='ing':
                    return
                success,error,extend_time,idx = future.result()
                print(f"sp进度: {i+1}/{total_files}, 状态: {'成功' if success else '失败'}")
                tools.set_process(text=f"{config.transobj['videodown..']} {i+1}/{total_files}", uuid=self.uuid)
                if success is False or success is None:
                    config.logger.error(f'[错误信息] {error}')
                    print(f"错误信息 {error}")
                elif extend_time>0 and idx>-1:
                   self.queue_tts[idx]['video_extend']=extend_time
                   print(f'视频延长了 {extend_time} 毫秒')

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
        config.logger.info(f'所有待连接视频片段:{concat_txt_arr=}')
        for it in concat_txt_arr:
            if Path(it).exists():
                new_arr.append(it)
        if len(new_arr) > 0:
            tools.set_process(text=f"连接视频片段..." if config.defaulelang == 'zh' else 'concat multi mp4 ...',
                              uuid=self.uuid)
            config.logger.info(f'实际需要连接的视频片段:{concat_txt_arr=}')
            concat_txt = self.cache_folder + f'/{time.time()}.txt'
            tools.create_concat_txt(concat_txt_arr, concat_txt=concat_txt)
            tools.concat_multi_mp4(out=self.novoice_mp4, concat_txt=concat_txt)


    def _merge_audio_segments(self):
        merged_audio = AudioSegment.empty()
        if len(self.queue_tts) == 1:
            the_ext = self.queue_tts[0]['filename'].split('.')[-1]
            try:
                merged_audio += AudioSegment.from_file(self.queue_tts[0]['filename'],format="mp4" if the_ext == 'm4a' else the_ext)
            except CouldntDecodeError:
                merged_audio+=AudioSegment.silent(duration=3000)
            except Exception:
                merged_audio+=AudioSegment.silent(duration=3000)
        else:
            # start is not 0
            if self.queue_tts[0]['start_time_source'] > 0:
                silence = AudioSegment.silent(duration=self.queue_tts[0]['start_time_source'])
                merged_audio += silence

            # 开始时间
            cur = self.queue_tts[0]['start_time_source']
            length = len(self.queue_tts)
            for i, it in enumerate(self.queue_tts):
                if config.exit_soft:
                    return
                # 存在有效配音文件则加入，否则配音时长大于0则加入静音
                segment = None
                the_ext = it['filename'].split('.')[-1]

                # 原始字幕时长
                raw_source = it['end_time_source'] - it['start_time_source']
                if raw_source == 0:
                    continue
                # 存在配音文件
                if tools.vail_file(it['filename']):
                    try:
                        segment = AudioSegment.from_file(it['filename'], format="mp4" if the_ext == 'm4a' else the_ext)
                        it['dubb_time'] = len(segment)
                    except CouldntDecodeError:
                        segment = AudioSegment.silent(duration=raw_source)
                        it['dubb_time'] = raw_source
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
                    "-b:a",
                    "192k",
                    self.target_audio
                ]
                tools.runffmpeg(cmd)

        except Exception as e:
            raise Exception(f'[error]merged_audio:{str(e)}')
