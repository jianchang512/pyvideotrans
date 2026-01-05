import copy,json,threading
import math
import os
import re
import shutil
import time
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict


from videotrans import translator
from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.recognition import run as run_recogn, Faster_Whisper_XXL,Whisper_CPP
from videotrans.translator import run as run_trans, get_audio_code
from videotrans.tts import run as run_tts, CLONE_VOICE_TTS, CHATTERBOX_TTS, COSYVOICE_TTS, F5_TTS, EDGE_TTS, AZURE_TTS, \
    INDEX_TTS, VOXCPM_TTS, SPARK_TTS, DIA_TTS, GPTSOVITS_TTS
from videotrans.task.simple_runnable_qt import run_in_threadpool
from videotrans.util import tools
from ._base import BaseTask




@dataclass
class TransCreate(BaseTask):
    # 存放原始语言字幕
    source_srt_list: List = field(default_factory=list)
    # 存放目标语言字幕
    target_srt_list: List = field(default_factory=list)
    # 原始视频时长  在慢速处理合并后，时长更新至此
    video_time: float = 0.0
    # 视频信息
    """
    {
        "video_fps":0,
        "video_codec_name":"h264",
        "audio_codec_name":"aac",
        "width":0,
        "height":0,
        "time":0
    }
    """
    video_info: Dict = field(default_factory=dict, repr=False)
    # 对视频是否执行 c:v copy 操作
    is_copy_video: bool = False
    # mp4编码类型 264 265
    video_codec_num: int = 265
    # 是否忽略音频和视频对齐
    ignore_align: bool = False

    # 是否是音频翻译任务，如果是，则到配音完毕即结束，无需合并
    is_audio_trans:bool=False
    queue_tts:List=field(default_factory=list, repr=False)


    def __post_init__(self):
        # 首先，处理本类的默认配置
        super().__post_init__()
        self._signal(text=tr('kaishichuli'))
        # -1=不启用说话人，0=启用并且不限制说话人数量，>0+1 为最大说话人数量
        self.max_speakers=self.cfg.nums_diariz if self.cfg.enable_diariz else -1
        if self.max_speakers>0:
            self.max_speakers+=1
        self.shoud_recogn = True
        # 输出编码，  264 或 265
        self.video_codec_num = int(config.settings.get('video_codec', 264))
        # 是否存在手动添加的背景音频
        if tools.vail_file(self.cfg.back_audio):
            self.cfg.background_music = Path(self.cfg.back_audio).as_posix()

        # 临时文件夹
        if not self.cfg.cache_folder:
            self.cfg.cache_folder = f"{config.TEMP_DIR}/{self.uuid}"
        # 输出文件夹，去掉可能存在的双斜线
        self.cfg.target_dir = re.sub(r'/{2,}', '/', self.cfg.target_dir,flags=re.I | re.S)
        # 检测字幕原始语言
        self.cfg.detect_language = get_audio_code(show_source=self.cfg.source_language_code)

        # 存放分离后的无声mp4到临时文件夹
        self.cfg.novoice_mp4 = f"{self.cfg.cache_folder}/novoice.mp4"


        # 原始语言字幕文件：输出文件夹
        self.cfg.source_sub = f"{self.cfg.target_dir}/{self.cfg.source_language_code}.srt"
        # 原始语言音频文件：输出文件夹
        self.cfg.source_wav_output = f"{self.cfg.target_dir}/{self.cfg.source_language_code}.m4a"
        # 原始语言音频文件：临时文件夹
        self.cfg.source_wav = f"{self.cfg.cache_folder}/{self.cfg.source_language_code}.wav"

        # 目标语言字幕：输出文件夹
        self.cfg.target_sub = f"{self.cfg.target_dir}/{self.cfg.target_language_code}.srt"
        # 配音后的目标音频文件：输出文件夹
        self.cfg.target_wav_output = f"{self.cfg.target_dir}/{self.cfg.target_language_code}.m4a"
        # 配音后的目标音频文件：临时文件夹
        self.cfg.target_wav = f"{self.cfg.cache_folder}/target.wav"

        # 最终需要输出的mp4视频
        self.cfg.targetdir_mp4 = f"{self.cfg.target_dir}/{self.cfg.noextname}.mp4"


        # 如果配音角色不是No 则需要配音
        if self.cfg.voice_role and self.cfg.voice_role != 'No' and self.cfg.target_language_code:
            self.shoud_dubbing = True

        # 如果不是 tiqu，则均需要合并视频音频字幕
        if self.cfg.app_mode != 'tiqu' and (self.shoud_dubbing or self.cfg.subtitle_type > 0):
            self.shoud_hebing = True
        
        # 是否需要翻译:存在目标语言代码并且不等于原始语言，则需要翻译
        if self.cfg.target_language_code and  self.cfg.target_language_code != self.cfg.source_language_code:
            self.shoud_trans = True

        # 如果原语言和目标语言相等，并且存在配音角色，则替换配音
        if self.cfg.voice_role and self.cfg.voice_role != 'No' and self.cfg.source_language_code == self.cfg.target_language_code:
            self.cfg.target_wav_output = f"{self.cfg.target_dir}/{self.cfg.target_language_code}-dubbing.m4a"
            self.cfg.target_wav = f"{self.cfg.cache_folder}/target-dubbing.wav"
            self.shoud_dubbing=True


        # 判断如果是音频，则到生成音频结束，无需合并，并且无需分离视频、无需背景音处理
        if self.cfg.ext in config.AUDIO_EXITS:
            self.is_audio_trans=True
            self.cfg.is_separate=False
            self.shoud_hebing = False

        # 没有设置目标语言，不配音不翻译
        if not self.cfg.target_language_code:
            self.shoud_dubbing=False
            self.shoud_trans=False

        if self.cfg.voice_role=='No':
            self.shoud_dubbing=False

        if self.cfg.app_mode == 'tiqu':
            self.cfg.is_separate=False
            self.cfg.enable_diariz=False
            self.shoud_dubbing=False

        Path(self.cfg.cache_folder).mkdir(parents=True,exist_ok=True)
        Path(self.cfg.target_dir).mkdir(parents=True,exist_ok=True)
        # 记录最终使用的配置信息
        config.logger.debug(f"最终配置信息：{self.cfg=}")
        # 删掉可能存在的无效文件
        self._unlink_size0(self.cfg.source_sub)
        self._unlink_size0(self.cfg.target_sub)
        self._unlink_size0(self.cfg.targetdir_mp4)

        # 获取高级设置选项
        config.settings = config.parse_init()
        # 禁止修改字幕
        self._signal(text="forbid", type="disabled_edit")
        # 开启一个线程显示进度
        def runing():
            t = time.time()
            while not self.hasend:
                if self._exit(): return
                time.sleep(1)
                self._signal(text=f"{int(time.time() - t)}???{self.precent}", type="set_precent")
        threading.Thread(target=runing).start()

    # 1. 预处理，分离音视频、分离人声等
    def prepare(self) -> None:
        if self._exit(): return

        # 如果存在字幕文本，则视为原始语言字幕，不再识别
        if self.cfg.subtitles.strip():
            with open(self.cfg.source_sub, 'w', encoding="utf-8", errors="ignore") as f:
                txt = re.sub(r':\d+\.\d+', lambda m: m.group().replace('.', ','),
                             self.cfg.subtitles.strip(), flags=re.I | re.S)
                f.write(txt)
            self.shoud_recogn = False
        try:
            # 删掉已存在的，可能会失败
            Path(self.cfg.source_wav).unlink(missing_ok=True)
            Path(self.cfg.source_wav_output).unlink(missing_ok=True)
            Path(self.cfg.target_wav).unlink(missing_ok=True)
            Path(self.cfg.target_wav_output).unlink(missing_ok=True)
        except Exception as e:
            config.logger.exception(f'删除已存在的文件时失败:{e}',exc_info=True)

        # 是否需要背景音分离：分离出的原始音频文件
        if self.cfg.is_separate:
            self.cfg.vocal = f"{self.cfg.cache_folder}/vocal.wav"
            self.cfg.instrument = f"{self.cfg.cache_folder}/instrument.wav"

            # 判断是否已存在
            raw_instrument = f"{self.cfg.target_dir}/instrument.wav"
            raw_vocal = f"{self.cfg.target_dir}/vocal.wav"
            if tools.vail_file(raw_instrument) and tools.vail_file(raw_vocal):
                try:
                    shutil.copy2(raw_instrument, self.cfg.instrument)
                    shutil.copy2(raw_vocal, self.cfg.vocal)
                except shutil.SameFileError:
                    pass
            self._unlink_size0(self.cfg.instrument)
            self._unlink_size0(self.cfg.vocal)
            self.shoud_separate = True
        # 获取视频信息
        self._signal(text=tr("Hold on a monment..."))
        self.video_info = tools.get_video_info(self.cfg.name)
        # 毫秒
        self.video_time = self.video_info['time']

        # 如果获得原始视频编码格式是 h264，并且色素 yuv420p, 则直接复制视频流 is_copy_video=True
        if self.video_info['video_codec_name'] == 'h264' and self.video_info['color'] == 'yuv420p':
            self.is_copy_video = True

        # 无视频流，不是音频，并且不是提取，报错
        if self.video_info.get('video_streams',0)<1 and not self.is_audio_trans and self.cfg.app_mode != 'tiqu':
            self.hasend=True
            raise RuntimeError(tr('The video file {} does not contain valid video data and cannot be processed.',self.cfg.name))
        
        # 无音频流，不存在原语言字幕，报错。存在则是无声视频流
        if self.video_info.get('streams_audio',0)<1 and not tools.vail_file(self.cfg.source_sub):
            self.hasend=True
            raise RuntimeError(tr('There is no valid audio in the file {} and it cannot be processed. Please play it manually to confirm that there is sound.',self.cfg.name))

        # 将原始视频分离为无声视频
        if not self.is_audio_trans and self.cfg.app_mode != 'tiqu':
            config.queue_novice[self.uuid] = 'ing'
            if not self.is_copy_video:
                self._signal(text= tr("Video needs transcoded and take a long time.."))
            run_in_threadpool(self._split_novoice_byraw)
        else:
            config.queue_novice[self.uuid] = 'end'

        # 需要人声背景声分离，并且不存在已分离好的文件
        if self.video_info.get('streams_audio',0)>0 and self.cfg.is_separate and ( not tools.vail_file(self.cfg.vocal) or not tools.vail_file(self.cfg.instrument)):
            try:
                self._signal(text=tr('Separating background music'))
                self._split_audio_byraw(True)
            except Exception as e:
                config.logger.exception(f'分离人声背景声失败',exc_info=True)
            finally:
                if not tools.vail_file(self.cfg.vocal) or not tools.vail_file(self.cfg.instrument):
                    # 分离失败
                    self.cfg.instrument = None
                    self.cfg.vocal = None
                    self.cfg.is_separate = False
                    self.shoud_separate = False
        
        # 如果还不存在原音频 self.cfg.source_wav,可能原因上一步分离人声背景声失败
        if self.video_info.get('streams_audio',0)>0 and not tools.vail_file(self.cfg.source_wav):
            self._split_audio_byraw()
            print(f'{self.cfg.source_wav=}')
        

        self._signal(text=tr('endfenliyinpin'))


    def _recogn_succeed(self) -> None:
        self.precent += 5
        if self.cfg.app_mode == 'tiqu':
            dest_name = f"{self.cfg.target_dir}/{self.cfg.noextname}"
            if not self.shoud_trans:
                self.hasend = True
                self.precent = 100
                dest_name += '.srt'
                shutil.copy2(self.cfg.source_sub, dest_name)
                Path(self.cfg.source_sub).unlink(missing_ok=True)
            else:
                dest_name += f"-{self.cfg.source_language_code}.srt"
                shutil.copy2(self.cfg.source_sub, dest_name)
        self._signal(text=tr('endtiquzimu'))



    # 开始识别
    def recogn(self) -> None:
        if self._exit(): return
        if not self.shoud_recogn: return
        self.precent += 3
        self._signal(text=tr("kaishishibie"))
        if tools.vail_file(self.cfg.source_sub):
            self.source_srt_list = tools.get_subtitle_from_srt(self.cfg.source_sub,is_file=True)
            if Path(self.cfg.target_dir+"/speaker.json").exists():
                shutil.copy2(self.cfg.target_dir+"/speaker.json",self.cfg.cache_folder+"/speaker.json")
            self._recogn_succeed()
            return

        if not tools.vail_file(self.cfg.source_wav):
            error = tr("Failed to separate audio, please check the log or retry")
            self.hasend = True
            raise RuntimeError(error)


        if self.cfg.remove_noise:
            self._signal(text=tr("Starting to process speech noise reduction, which may take a long time, please be patient"))
            from ._remove_noise import run_remove
            self.cfg.source_wav = run_remove(
                self.cfg.source_wav,
                f"{self.cfg.cache_folder}/remove_noise.wav",
                int(config.settings.get('noise_separate_nums',4))
            )
        self._signal(text=tr("Speech Recognition to Word Processing"))

        if self.cfg.recogn_type == Faster_Whisper_XXL:
            xxl_path=config.settings.get('Faster_Whisper_XXL', 'Faster_Whisper_XXL.exe')
            cmd = [
                xxl_path,
                self.cfg.source_wav,
                "-pp",
                "-f", "srt"
            ]
            cmd.extend(['-l', self.cfg.detect_language.split('-')[0]])
            prompt=None
            prompt = config.settings.get(f'initial_prompt_{self.cfg.detect_language}')
            if prompt:
                cmd+=['--initial_prompt',prompt]
            cmd.extend(['--model', self.cfg.model_name, '--output_dir', self.cfg.target_dir])
            
            txt_file = Path(xxl_path).parent.resolve().as_posix() + '/pyvideotrans.txt'
            
            if Path(txt_file).exists():
                cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))

            cmdstr = " ".join(cmd)
            outsrt_file = self.cfg.target_dir + '/' + Path(self.cfg.source_wav).stem + ".srt"
            config.logger.debug(f'Faster_Whisper_XXL: {cmdstr=}\n{outsrt_file=}\n{self.cfg.source_sub=}')

            self._external_cmd_with_wrapper(cmd)

            try:
                shutil.copy2(outsrt_file, self.cfg.source_sub)
            except shutil.SameFileError:
                pass
            self.source_srt_list = tools.get_subtitle_from_srt(self.cfg.source_sub,is_file=True)
        elif self.cfg.recogn_type == Whisper_CPP:
            cpp_path=config.settings.get('Whisper.cpp', 'whisper-cli')
            cmd = [
                cpp_path,
                "-f",
                self.cfg.source_wav,
                "-osrt",
                "-np"
                                
            ]
            cmd+=["-l",self.cfg.detect_language.split('-')[0]]
            prompt=None
            prompt = config.settings.get(f'initial_prompt_{self.cfg.detect_language}')
            if prompt:
                cmd+=['--prompt',prompt]
            cpp_folder=Path(cpp_path).parent.resolve().as_posix()
            if not Path(f'{cpp_folder}/models/{self.cfg.model_name}').is_file():
                raise RuntimeError(tr('The model does not exist. Please download the model to the {} directory first.',f'{cpp_folder}/models'))
            txt_file =  cpp_folder+ '/pyvideotrans.txt'

            if Path(txt_file).exists():
                cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))
            
            cmd.extend(['-m', f'models/{self.cfg.model_name}', '-of', self.cfg.source_sub[:-4]])
                
            config.logger.debug(f'Whisper.cpp: {cmd=}')

            self._external_cmd_with_wrapper(cmd)
            self.source_srt_list = tools.get_subtitle_from_srt(self.cfg.source_sub,is_file=True)
        else:
            #-1不启用，0不限制数量，>0加1为指定的说话人数量

            raw_subtitles = run_recogn(
                recogn_type=self.cfg.recogn_type,
                uuid=self.uuid,
                model_name=self.cfg.model_name,
                audio_file=self.cfg.source_wav,
                detect_language=self.cfg.detect_language,
                cache_folder=self.cfg.cache_folder,
                is_cuda=self.cfg.cuda,
                subtitle_type=self.cfg.subtitle_type,
                max_speakers=self.max_speakers,
                llm_post=self.cfg.rephrase == 1
            )
            if self._exit(): return
            if not raw_subtitles:
                raise RuntimeError(self.cfg.basename + tr('recogn result is empty'))
            self._save_srt_target(raw_subtitles, self.cfg.source_sub)
            self.source_srt_list = raw_subtitles
        self._signal(text=Path(self.cfg.source_sub).read_text(encoding='utf-8'), type='replace_subtitle')
        # whisperx-api
        # openairecogn并且模型是gpt-4o-transcribe-diarize
        # funasr并且模型是paraformer-zh
        # deepgram
        # 以上这些本身已有说话人识别，如果已有说话人识别结果，就不再重新断句
        if Path(self.cfg.cache_folder+"/speaker.json").exists():
            self._recogn_succeed()
            self._signal(text=tr('endtiquzimu'))
            return

        if self.cfg.rephrase==1:
            #LLM重新断句
            try:
                from videotrans.translator._chatgpt import ChatGPT

                ob = ChatGPT(uuid=self.uuid)
                self._signal(text=tr("Re-segmenting..."))
                srt_list = ob.llm_segment(self.source_srt_list, config.settings.get('llm_ai_type', 'openai'))
                if srt_list and len(srt_list)>len(self.source_srt_list)/2:
                    self.source_srt_list=srt_list
                    shutil.copy2(self.cfg.source_sub,f'{self.cfg.source_sub}-No-{tr("LLM Rephrase")}.srt')
                    self._save_srt_target(self.source_srt_list, self.cfg.source_sub)
                else:
                    raise
            except Exception as e:
                self._signal(text=tr("Re-segmenting Error"))
                config.logger.warning(f"重新断句失败[except]，已恢复原样 {e}")

        self._recogn_succeed()
        self._signal(text=tr('endtiquzimu'))


    def diariz(self):
        if self._exit() or not self.cfg.enable_diariz or Path(self.cfg.cache_folder+"/speaker.json").exists():
            return
        speaker_type=config.settings.get('speaker_type','built')
        hf_token= config.settings.get('hf_token')
        if speaker_type=='built' and self.cfg.detect_language[:2] not in ['zh','en']:
            config.logger.error(f'当前选择 built 说话人分离模型，但不支持当前语言:{self.cfg.detect_language}')
            return
        if speaker_type=='pyannote' and not hf_token:
            config.logger.error(f'当前选择 pyannote 说话人分离模型，但未设置 huggingface.co 的token: {self.cfg.detect_language}')
            return
        if speaker_type=='pyannote':
            # 判断是否可访问 huggingface.co
            # 先测试能否连接 huggingface.co, 中国大陆地区不可访问，除非使用VPN
            try:
                import requests
                requests.head('https://huggingface.co',timeout=5)
            except Exception:
                config.logger.error(f'当前选择 pyannote 说话人分离模型，但无法连接到 https://huggingface.co')

                
        
        try:
            self.precent += 3
            self._signal(text=tr('Begin separating the speakers'))
            from videotrans.diarization import assign_speakers
            spk_list=assign_speakers(
                self.cfg.source_wav,
                self.cfg.detect_language,
                [ [it['start_time'],it['end_time']] for it in self.source_srt_list],
                -1 if self.max_speakers<1 else self.max_speakers,
                self.uuid,
                speaker_type
            )
            Path(self.cfg.cache_folder+"/speaker.json").write_text(json.dumps(spk_list),encoding='utf-8')            
            config.logger.debug('分离说话人成功完成')
            shutil.copy2(self.cfg.cache_folder+"/speaker.json",self.cfg.target_dir+"/speaker.json")
            self._signal(text=tr('separating speakers end'))
        except Exception as e:
            config.logger.exception(f'分离说话人失败，静默跳过{e}',exc_info=True)
            self._signal(text=tr('Speaker separation failed, silent skip.'))

    # 翻译字幕文件
    def trans(self) -> None:
        if self._exit(): return
        if not self.shoud_trans: return
        self.precent += 3
        self._signal(text=tr('starttrans'))

        # 如果存在目标语言字幕，无需继续翻译，前台直接使用该字幕替换
        if self._srt_vail(self.cfg.target_sub):
            self._signal(
                text=Path(self.cfg.target_sub).read_text(encoding="utf-8", errors="ignore"),
                type='replace_subtitle'
            )
            return
        try:
            rawsrt = tools.get_subtitle_from_srt(self.cfg.source_sub, is_file=True)
            self._signal(text=tr('kaishitiquhefanyi'))

            target_srt = run_trans(
                translate_type=self.cfg.translate_type,
                text_list=copy.deepcopy(rawsrt),
                uuid=self.uuid,
                source_code=self.cfg.source_language_code,
                target_code=self.cfg.target_language_code
            )
            if self._exit():
                return
            self._save_srt_target(self._check_target_sub(rawsrt, target_srt), self.cfg.target_sub)

            # 仅提取，该名字删原
            if self.cfg.app_mode == 'tiqu':
                shutil.copy2(self.cfg.target_sub,f"{self.cfg.target_dir}/{self.cfg.noextname}.srt")

                if self.cfg.copysrt_rawvideo:
                    p = Path(self.cfg.name)
                    shutil.copy2(self.cfg.target_sub, f'{p.parent.as_posix()}/{p.stem}.srt')
                self.hasend = True
                self.precent = 100
                try:
                    Path(self.cfg.source_sub).unlink(missing_ok=True)
                    Path(self.cfg.target_sub).unlink(missing_ok=True)
                except:
                    pass
        except Exception as e:
            self.hasend = True
            raise
        self._signal(text=tr('endtrans'))    

    # 对字幕进行配音
    def dubbing(self) -> None:
        if self._exit():
            return
        if self.cfg.app_mode == 'tiqu' or not self.shoud_dubbing:
            return

        self._signal(text=tr('kaishipeiyin'))
        self.precent += 3
        try:
            self._tts()
            # 判断下一步重新调整字幕
        except Exception as e:
            self.hasend = True
            raise
        self._signal(text=tr('The dubbing is finished'))

    
    

    # 音画字幕对齐
    def align(self) -> None:
        if self._exit():
            return
        if self.cfg.app_mode == 'tiqu' or not self.shoud_dubbing or self.ignore_align:
            return

        self._signal(text=tr('duiqicaozuo'))
        self.precent += 3
        if self.cfg.voice_autorate or self.cfg.video_autorate:
            self._signal(text=tr("Sound & video speed alignment stage"))
        try:
            # 需要视频慢速，则判断无声视频是否已分离完毕
            if self.cfg.video_autorate:
                tools.is_novoice_mp4(self.cfg.novoice_mp4, self.uuid)
            # 存在视频，则以视频长度为准
            if tools.vail_file(self.cfg.novoice_mp4):
                self.video_time = tools.get_video_duration(self.cfg.novoice_mp4)

            from videotrans.task._rate import SpeedRate
            rate_inst = SpeedRate(
                queue_tts=self.queue_tts,
                uuid=self.uuid,
                shoud_audiorate=self.cfg.voice_autorate,
                # 视频是否需慢速，需要时对 novoice_mp4进行处理
                shoud_videorate=self.cfg.video_autorate if not self.is_audio_trans else False,
                novoice_mp4=self.cfg.novoice_mp4 if not self.is_audio_trans else None,
                # 原始总时长
                raw_total_time=self.video_time,

                target_audio=self.cfg.target_wav,
                cache_folder=self.cfg.cache_folder,
                align_sub_audio=self.cfg.align_sub_audio, # 均在未启用音频加速和视频慢速时才起作用
                remove_silent_mid=self.cfg.remove_silent_mid # 均在未启用音频加速和视频慢速时才起作用
            )
            self.queue_tts = rate_inst.run()
            # 慢速处理后，更新新视频总时长，用于音视频对齐
            if tools.vail_file(self.cfg.novoice_mp4):
                self.video_time = tools.get_video_duration(self.cfg.novoice_mp4)

            # 对齐字幕
            if self.cfg.voice_autorate or self.cfg.video_autorate or self.cfg.align_sub_audio:
                srt = ""
                for (idx, it) in enumerate(self.queue_tts):
                    startraw=tools.ms_to_time_string(ms=it['start_time'])
                    endraw=tools.ms_to_time_string(ms=it['end_time'])
                    srt += f"{idx + 1}\n{startraw} --> {endraw}\n{it['text']}\n\n"
                # 字幕保存到目标文件夹
                with  Path(self.cfg.target_sub).open('w', encoding="utf-8") as f:
                    f.write(srt.strip())
        except Exception as e:
            self.hasend = True
            raise

        # 成功后，如果存在 音量，则调节音量
        if self.cfg.tts_type not in [EDGE_TTS, AZURE_TTS] and self.cfg.volume != '+0%' and tools.vail_file(
                self.cfg.target_wav):
            volume = self.cfg.volume.replace('%', '').strip()
            try:
                volume = 1 + float(volume) / 100
                if volume != 1.0:
                    tmp_name = self.cfg.cache_folder + f'/volume-{volume}-{Path(self.cfg.target_wav).name}'
                    tools.runffmpeg(['-y', '-i', self.cfg.target_wav, '-af', f"volume={volume}", tmp_name])
                    shutil.copy2(tmp_name, self.cfg.target_wav)
            except:
                pass
        
        self._signal(text=tr('Alignment phase complete, awaiting the next step'))
        
    # 将 视频、音频、字幕合成
    def assembling(self) -> None:
        if self._exit(): return
        # 音频翻译， 提取模式 无需合并
        if self.is_audio_trans or self.cfg.app_mode == 'tiqu' or not self.shoud_hebing:
            return
        if self.precent < 95:
            self.precent += 3
        self._signal(text=config.tr('kaishihebing'))
        try:
            self._join_video_audio_srt()
        except Exception as e:
            self.hasend = True
            raise


    # 收尾，根据 output和 linshi_output是否相同，不相同，则移动
    def task_done(self) -> None:
        # 正常完成仍是 ing，手动停止变为 stop
        if self._exit(): return
        self.precent = 99

        # 提取时，删除
        if self.cfg.app_mode == 'tiqu':
            try:
                Path(f"{self.cfg.target_dir}/{self.cfg.source_language_code}.srt").unlink(
                    missing_ok=True)
                Path(f"{self.cfg.target_dir}/{self.cfg.target_language_code}.srt").unlink(
                    missing_ok=True)
            except:
                pass  # 忽略删除失败


        self.hasend = True
        self.precent = 100
        

        if self.is_audio_trans and tools.vail_file(self.cfg.target_wav):
            try:
                shutil.copy2(self.cfg.target_wav, f"{self.cfg.target_dir}/{self.cfg.target_language_code}-{self.cfg.noextname}.wav")
            except shutil.SameFileError:
                pass

        try:
            if self.cfg.shound_del_name:
                Path(self.cfg.shound_del_name).unlink(missing_ok=True)
            if self.cfg.only_out_mp4:
                shutil.move(self.cfg.targetdir_mp4,Path(self.cfg.target_dir).parent / f'{self.cfg.noextname}.mp4')
                shutil.rmtree(self.cfg.target_dir,ignore_errors=True)
        except Exception as e:
            config.logger.exception(e, exc_info=True)
        self._signal(text=f"{self.cfg.name}", type='succeed')
        tools.send_notification(tr('Succeed'), f"{self.cfg.basename}")
        
        
    # 从原始视频分离出 无声视频
    def _split_novoice_byraw(self):
        cmd = [
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            self.cfg.name,
            "-an",
            "-c:v",
            "copy" if self.is_copy_video else f"libx264"
        ]
        if not self.is_copy_video:
            cmd += ["-crf", '20','-preset','veryfast']
        cmd += [self.cfg.novoice_mp4]
        return tools.runffmpeg(cmd, noextname=self.uuid)

    # 从原始视频中分离出音频
    def _split_audio_byraw(self, is_separate=False):
        cmd = [
            "-y",
            "-i",
            self.cfg.name,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            '-af', 
            "volume=2.0,alimiter=limit=1.0",
            self.cfg.source_wav
        ]
        rs = tools.runffmpeg(cmd)
        if not is_separate:
            return rs

        # 继续人声分离
        tmpfile = config.TEMP_DIR + "/441000_ac2_raw.wav"
        tools.runffmpeg([
            "-y",
            "-i",
            self.cfg.name,
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            tmpfile
        ])
        from videotrans.separate import run_sep
        vocal_file = self.cfg.cache_folder + '/vocal.wav'
        if not tools.vail_file(vocal_file):
            self._signal(
                text=config.tr('Separating vocals and background music, which may take a longer time'))
            run_sep(tmpfile,self.cfg.vocal,self.cfg.instrument,int(config.settings.get('noise_separate_nums',4)))
            if tools.vail_file(self.cfg.vocal):
                shutil.copy2(self.cfg.vocal,f'{self.cfg.target_dir}/vocal.wav')
                cmd = [
                    "-y",
                    "-i",
                    f'{self.cfg.target_dir}/vocal.wav',
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    '-af', 
                    "volume=2.0,alimiter=limit=1.0",
                    self.cfg.source_wav
                ]
                tools.runffmpeg(cmd)
            if tools.vail_file(self.cfg.instrument):
                shutil.copy2(self.cfg.instrument,f'{self.cfg.target_dir}/instrument.wav')



    # 配音预处理，去掉无效字符，整理开始时间
    def _tts(self,daz_json=None) -> None:
        queue_tts = []
        subs = tools.get_subtitle_from_srt(self.cfg.target_sub)
        source_subs = tools.get_subtitle_from_srt(self.cfg.source_sub)
        if len(subs) < 1:
            raise RuntimeError(f"SRT file error:{self.cfg.target_sub}")
        try:
            rate = int(str(self.cfg.voice_rate).replace('%', ''))
        except:
            rate = 0
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出设置的每行角色
        line_roles = config.line_roles
        voice_role = self.cfg.voice_role

        # 如果未 音频加速、未视频慢速、未强制对齐、选中了移除字幕间静音，并且音色只有一个，则拼接为纯文本配音
        # 如果渠道是 edge-tts,并且非多角色配音 
        _enter_edgetts_single=self.cfg.tts_type == EDGE_TTS and not line_roles
        if _enter_edgetts_single:
            if not self.cfg.voice_autorate and not self.cfg.video_autorate and not self.cfg.align_sub_audio and self.cfg.remove_silent_mid:
                # 或者未自动加速 未视频慢速 未强制对齐  并且移除了字幕间静音
                _enter_edgetts_single=True
            else:
                _enter_edgetts_single=False

        if _enter_edgetts_single:
            self.ignore_align=True
            text=""
            for it in subs:
                text+=it["text"]+"\n"
            tmp_name=f'{self.cfg.cache_folder}/edge-tts-single.mp3'
            asyncio.run(self._edgetts_single(
                tmp_name,
                dict(text=text,
                    voice=tools.get_edge_rolelist(voice_role,locale=self.cfg.target_language_code),
                    rate=rate,
                    volume=self.cfg.volume,
                    pitch=self.cfg.pitch
                )
            ))
            tools.runffmpeg(['-y', '-i', tmp_name, '-b:a', '128k', self.cfg.target_wav])
            config.logger.debug(f'edge-tts配音，未音频加速，未视频慢速，未强制对齐，已删字幕间静音，使用单独文本配音')
            return

        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            if it['end_time'] <= it['start_time'] or not it['text'].strip():
                continue
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice = line_roles.get(f'{it["line"]}',voice_role)

            tmp_dict = {
                "text": it['text'],
                "line": it['line'],
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "ref_text": source_subs[i]['text'] if source_subs and i < len(source_subs) else '',
                "start_time_source": source_subs[i]['start_time'] if source_subs and i < len(source_subs) else it['start_time'],
                "end_time_source": source_subs[i]['end_time'] if source_subs and i < len(source_subs) else it['end_time'],
                "role": voice,
                "rate": rate,
                "volume": self.cfg.volume,
                "pitch": self.cfg.pitch,
                "tts_type": self.cfg.tts_type,
                "filename": f"{self.cfg.cache_folder}/dubb-{i}-{time.time()}.wav"
            }
            # 如果是clone-voice类型， 需要截取对应片段
            # 是克隆
            if voice == 'clone' and self.cfg.tts_type in [COSYVOICE_TTS, CLONE_VOICE_TTS, F5_TTS,INDEX_TTS,VOXCPM_TTS,SPARK_TTS,DIA_TTS,CHATTERBOX_TTS,GPTSOVITS_TTS]:
                tmp_dict['ref_wav'] = f"{self.cfg.cache_folder}/clone-{i}-{time.time()}.wav"
                tmp_dict['ref_language']=self.cfg.detect_language[:2]
            queue_tts.append(tmp_dict)

        self.queue_tts = copy.deepcopy(queue_tts)

        if not self.queue_tts or len(self.queue_tts) < 1:
            raise RuntimeError(f'Queue tts length is 0')

        # 如果存在有 ref_wav 即需要clone，存在参考音频的
        if len([it.get("ref_wav") for it in self.queue_tts if it.get("ref_wav")])>0:
            self._create_ref_from_vocal()

        # 具体配音操作
        run_tts(
            queue_tts=copy.deepcopy(self.queue_tts),
            language=self.cfg.target_language_code,
            uuid=self.uuid,
            tts_type=self.cfg.tts_type
        )
        if config.settings.get('save_segment_audio', False):
            outname = self.cfg.target_dir + f'/segment_audio_{self.cfg.noextname}'
            Path(outname).mkdir(parents=True, exist_ok=True)
            for it in self.queue_tts:
                text = re.sub(r'["\'*?\\/\|:<>\r\n\t]+', '', it['text'],flags=re.I | re.S)
                name = f'{outname}/{it["line"]}-{text[:60]}.wav'
                if Path(it['filename']).exists():
                    shutil.copy2(it['filename'], name)


    # 多线程实现裁剪参考音频
    def _create_ref_from_vocal(self):
        # 背景分离人声如果失败则直接使用原始音频
        vocal=self.cfg.vocal if tools.vail_file(self.cfg.vocal) else self.cfg.source_wav
        # 裁切对应片段为参考音频
        def _cutaudio_from_vocal(it):
            try:
                tools.cut_from_audio(
                    audio_file=vocal,
                    ss=it['startraw'],
                    to=it['endraw'],
                    out_file=it['ref_wav']
                )
            except Exception:
                pass
        all_task = []
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(12,len(self.queue_tts),os.cpu_count())) as pool:
            for item in self.queue_tts:
                if item.get('ref_wav'):
                    all_task.append(pool.submit(_cutaudio_from_vocal, item))
            if len(all_task)>0:
                _ = [i.result() for i in all_task]

    # 添加背景音乐
    def _back_music(self) -> None:
        if self._exit() or not self.shoud_dubbing:
            return

        if not tools.vail_file(self.cfg.target_wav) or not  tools.vail_file(self.cfg.background_music):
            return
        try:
            self._signal(text=config.tr("Adding background audio"))
            # 获取视频长度
            vtime = tools.get_audio_time(self.cfg.target_wav)
            # 获取背景音频长度
            atime = tools.get_audio_time(self.cfg.background_music)
            bgm_file = self.cfg.cache_folder + f'/bgm_file.wav'
            self.convert_to_wav(self.cfg.background_music, bgm_file)
            self.cfg.background_music = bgm_file
            beishu = math.ceil(vtime / atime)
            if config.settings.get('loop_backaudio') and beishu > 1 and vtime - 1000 > atime:
                # 获取延长片段
                file_list = [self.cfg.background_music for n in range(beishu + 1)]
                concat_txt = self.cfg.cache_folder + f'/{time.time()}.txt'
                tools.create_concat_txt(file_list, concat_txt=concat_txt)
                tools.concat_multi_audio(
                    concat_txt=concat_txt,
                    out=self.cfg.cache_folder + "/bgm_file_extend.wav")
                self.cfg.background_music = self.cfg.cache_folder + "/bgm_file_extend.wav"
            # 背景音频降低音量
            tools.runffmpeg(
                ['-y',
                 '-i', self.cfg.background_music,
                 "-filter:a", f"volume={config.settings.get('backaudio_volume',0.8)}",
                 '-c:a', 'pcm_s16le',
                 self.cfg.cache_folder + f"/bgm_file_extend_volume.wav"
                 ])
            # 背景音频和配音合并
            cmd = ['-y',
                   '-i', self.cfg.target_wav,
                   '-i', self.cfg.cache_folder + f"/bgm_file_extend_volume.wav",
                   '-filter_complex', "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2",
                   '-ac', '2',
                   '-c:a', 'pcm_s16le',
                   self.cfg.cache_folder + f"/lastend.wav"
                   ]
            tools.runffmpeg(cmd)
            self.cfg.target_wav = self.cfg.cache_folder + f"/lastend.wav"
        except Exception as e:
            config.logger.exception(f'添加背景音乐失败:{str(e)}', exc_info=True)

    def _separate(self) -> None:
        if self._exit() or not self.shoud_separate:
            return
        # 如果背景音频分离失败，则静默返回
        if not tools.vail_file(self.cfg.instrument):
            return
        if not tools.vail_file(self.cfg.target_wav):
            return
        try:
            self._signal(text=config.tr("Re-embedded background sounds"))
            vtime = tools.get_audio_time(self.cfg.target_wav)
            atime = tools.get_audio_time(self.cfg.instrument)
            beishu = math.ceil(vtime / atime)

            instrument_file = self.cfg.instrument
            config.logger.debug(f'合并背景音 {beishu=},{atime=},{vtime=}')
            if config.settings.get('loop_backaudio') and atime+1000 < vtime:
                # 背景音连接延长片段
                file_list = [instrument_file for n in range(beishu + 1)]
                concat_txt = self.cfg.cache_folder + f'/{time.time()}.txt'
                tools.create_concat_txt(file_list, concat_txt=concat_txt)
                tools.concat_multi_audio(concat_txt=concat_txt,
                                         out=self.cfg.cache_folder + "/instrument-concat.wav")
                instrument_file = self.cfg.cache_folder + f"/instrument-concat.wav"
            # 背景音合并配音
            self._backandvocal(self.cfg.instrument, self.cfg.target_wav)
        except Exception as e:
            config.logger.exception(e, exc_info=True)

    # 合并后最后文件仍为 人声文件，时长需要等于人声
    def _backandvocal(self, backwav, peiyinm4a):
        import tempfile
        backwav = Path(backwav).as_posix()
        peiyinm4a = Path(peiyinm4a).as_posix()
        tmpdir = tempfile.gettempdir()
        tmpwav = Path(tmpdir + f'/{time.time()}-1.wav').as_posix()
        tmpm4a = Path(tmpdir + f'/{time.time()}.wav').as_posix()
        # 背景转为m4a文件,音量降低为0.8
        self.convert_to_wav(backwav, tmpm4a, ["-filter:a", f"volume={config.settings.get('backaudio_volume',0.8)}"])
        tools.runffmpeg(['-y', '-i', peiyinm4a, '-i', tmpm4a, '-filter_complex',
                         "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', "-b:a", "128k",
                         '-c:a', 'pcm_s16le', tmpwav])
        shutil.copy2(tmpwav, peiyinm4a)

    # 处理所需字幕
    def _process_subtitles(self) -> tuple[str, str]:
        config.logger.debug(f"\n======准备要嵌入的字幕:{self.cfg.subtitle_type=}=====")
        if not Path(self.cfg.target_sub).exists():
            raise RuntimeError( config.tr("No valid subtitle file exists"))
    
        # 如果原始语言和目标语言相同，或不存原始语言字幕，则强制单字幕
        if not Path(self.cfg.source_sub).exists() or (self.cfg.source_language_code == self.cfg.target_language_code) :
            if self.cfg.subtitle_type == 3:
                self.cfg.subtitle_type = 1
            elif self.cfg.subtitle_type == 4:
                self.cfg.subtitle_type = 2
        
        
        # 最终处理后需要嵌入视频的字幕
        process_end_subtitle = self.cfg.cache_folder + f'/end.srt'
        # 硬字幕时单行字符数
        maxlen = int(
            config.settings.get('cjk_len',15) if self.cfg.target_language_code[:2] in ["zh", "ja", "jp", "ko", 'yu'] else
            config.settings.get('other_len',60))
        target_sub_list = tools.get_subtitle_from_srt(self.cfg.target_sub)

        # 双硬 双软字幕组装
        if self.cfg.subtitle_type in [3, 4]:
            maxlen_source = int(
                config.settings.get('cjk_len',15) if self.cfg.source_language_code[:2] in ["zh", "ja", "jp", "ko",
                                                                                       'yu'] else
                config.settings.get('other_len',60))
            source_sub_list = tools.get_subtitle_from_srt(self.cfg.source_sub)
            source_length = len(source_sub_list)

            srt_string = ""
            # 双语字幕，目标字幕在上，原字幕在下
            for i, it in enumerate(target_sub_list):
                # 硬字幕换行，软字幕无需处理
                tmp = tools.textwrap(it['text'].strip(), maxlen)
                srt_string += f"{it['line']}\n{it['time']}\n{tmp}"
                if source_length > 0 and i < source_length:
                    srt_string += "\n" + tools.textwrap(source_sub_list[i]['text'], maxlen_source).strip()
                srt_string += "\n\n"
            process_end_subtitle = f"{self.cfg.cache_folder}/shuang.srt"
            with Path(process_end_subtitle).open('w', encoding='utf-8') as f:
                f.write(srt_string.strip())
            shutil.copy2(process_end_subtitle, self.cfg.target_dir + "/shuang.srt")
        #elif self.cfg.subtitle_type == 1:
        else:
            # 单字幕，需处理字符数换行
            srt_string = ""
            for i, it in enumerate(target_sub_list):
                tmp = tools.textwrap(it['text'].strip(), maxlen)
                srt_string += f"{it['line']}\n{it['time']}\n{tmp.strip()}\n\n"
            with Path(process_end_subtitle).open('w', encoding='utf-8') as f:
                f.write(srt_string)
        #else:
        #    # 单软字幕
        #    basename = os.path.basename(self.cfg.target_sub)
        #    process_end_subtitle = self.cfg.cache_folder + f"/{basename}"
        #    shutil.copy2(self.cfg.target_sub, process_end_subtitle)

        # 目标字幕语言
        subtitle_langcode = translator.get_subtitle_code(show_target=self.cfg.target_language)

        config.logger.debug(            f'最终确定字幕嵌入类型:{self.cfg.subtitle_type} ,目标字幕语言:{subtitle_langcode}, 字幕文件:{process_end_subtitle}\n')
        # 单软 或双软
        if self.cfg.subtitle_type in [2, 4]:
            return os.path.basename(process_end_subtitle), subtitle_langcode

        # 硬字幕转为ass格式 并设置样式
        process_end_subtitle_ass = tools.set_ass_font(process_end_subtitle)
        basename = os.path.basename(process_end_subtitle_ass)
        return basename, subtitle_langcode


    # 视频定格最后一帧
    def _video_extend(self, duration_ms=1000):
        sec=duration_ms / 1000.0
        final_video_path = Path(f'{self.cfg.cache_folder}/final_video_with_freeze_lastend.mp4').as_posix()
        cmd = ['-y', '-i', self.cfg.novoice_mp4,
               '-vf', f'tpad=stop_mode=clone:stop_duration={sec:.3f}',
               '-c:v', 'libx264',
               '-crf', f'{config.settings.get("crf",23)}',
               '-preset', config.settings.get('preset','veryfast'),
               '-an', final_video_path]

        if tools.runffmpeg(cmd, force_cpu=True) and Path(final_video_path).exists():
            shutil.copy2(final_video_path, self.cfg.novoice_mp4)
            config.logger.debug(f"视频定格应延长{duration_ms}ms，实际向上取整秒延长{sec}s,操作成功。")
        else:
            config.logger.warning("视频定格延长操作失败！")

    def _audio_extend(self, duration_diff,output_ma4):
        # 音频末尾添加静音延长
        padded_audio_path = Path(f'{self.cfg.cache_folder}/last_end_com.m4a').as_posix()
        pad_dur_sec = duration_diff / 1000.0
        config.logger.debug(f'音频末尾应增加{duration_diff}ms静音')

        cmd = ['-y', '-i', output_ma4, '-af', f'apad=pad_dur={pad_dur_sec:.4f}',"-c:a", "aac",padded_audio_path]

        if tools.runffmpeg(cmd) and tools.vail_file(padded_audio_path):
            # Path(output_ma4).unlink(missing_ok=True)
            shutil.move(padded_audio_path,output_ma4)
            config.logger.debug("音频补齐静音并重新导出完成。")
        else:
            config.logger.warning("使用apad滤镜填充静音失败！")

    # 最终合成视频
    def _join_video_audio_srt(self) -> None:
        if self._exit():
            return
        if not self.shoud_hebing:
            return True

        # 判断novoice_mp4是否完成
        tools.is_novoice_mp4(self.cfg.novoice_mp4, self.uuid)
        if not Path(self.cfg.novoice_mp4).exists():
            raise RuntimeError(f'{self.cfg.novoice_mp4} 不存在')
        # 需要配音但没有配音文件
        if self.shoud_dubbing and not tools.vail_file(self.cfg.target_wav):
            raise RuntimeError(f"{config.tr('Dubbing')}{config.tr('anerror')}:{self.cfg.target_wav}")

        subtitles_file, subtitle_langcode = None, None
        if self.cfg.subtitle_type > 0:
            subtitles_file, subtitle_langcode = self._process_subtitles()

        self.precent = min(max(90, self.precent), 95)
        
        # 无配音且不嵌入字幕，是仅提取模式，进行不到这里
        # 无配音但嵌入字幕，使用原始音频
        target_m4a=self.cfg.cache_folder+"/origin_audio.m4a"
        # 用于判断输出原始音频是否结束，is True是结束，
        output_source_output=True
        if not self.shoud_dubbing:
            self._get_origin_audio(target_m4a)
        else:
            try:
                output_source_output=False
                # 高质量 原始音频输出到目标目录，单独线程执行，不影响继续运行
                cmd=[
                    "-y",
                    "-i",
                    self.cfg.name,
                    "-vn",
                    "-b:a","128k",
                    "-c:a",
                    "aac",                    
                    self.cfg.source_wav_output
                ]
                def _output():
                    nonlocal output_source_output
                    try:
                        tools.runffmpeg(cmd)
                    except Exception:
                        pass
                    finally:
                        output_source_output=True
                threading.Thread(target=_output).start()
            except Exception:
                pass
            # 添加背景音乐
            self._back_music()
            # 重新嵌入分离出的背景音
            self._separate()
            protxt = config.TEMP_DIR + f"/wav-m4a-{time.time()}.txt"
            threading.Thread(target=self._hebing_pro,args=(protxt,self.video_time)).start()
            tools.runffmpeg([
                "-y",
                "-progress",
                protxt,
                "-i",
                self.cfg.target_wav,
                "-ac","2","-b:a","128k","-c:a","aac",target_m4a
            ])

        self.precent = min(max(95, self.precent), 98)
        shutil.copy2(target_m4a,self.cfg.target_wav_output)

        # 字幕嵌入时进入视频目录下
        os.chdir(Path(self.cfg.novoice_mp4).parent.resolve())

        # 末尾对齐
        duration_ms = int(tools.get_video_duration(self.cfg.novoice_mp4))
        duration_s=f'{duration_ms/1000.0:.6f}'
        audio_ms=tools.get_audio_time(target_m4a)
        if duration_ms<audio_ms:
            self._video_extend(audio_ms-duration_ms)
            duration_ms = int(tools.get_video_duration(self.cfg.novoice_mp4))
            duration_s=f'{duration_ms/1000.0:.6f}'
       

        try:
            #先导出到临时目录，防止包含各种奇怪符号的targetdir_mp4导致ffmpeg失败
            tmp_target_mp4=self.cfg.cache_folder+f"/laste_target.mp4"
            protxt = self.cfg.cache_folder + f"/compose{time.time()}.txt"
            threading.Thread(target=self._hebing_pro,args=(protxt,self.video_time)).start()
            self._signal(text=config.tr("Video + Subtitles + Dubbing in merge"))
            cmd = []
            is_copy_mode = (str(self.video_codec_num) == '264')
            v_codec = "copy" if is_copy_mode else f'libx{self.video_codec_num}'



            # 有字幕有配音
            if self.cfg.voice_role != 'No' and self.cfg.subtitle_type > 0:
                # 硬字幕有配音 必须重编码
                if self.cfg.subtitle_type in [1, 3]:
                    self._signal(text=config.tr('peiyin-yingzimu'))
                    cmd = [
                        "-y",
                        "-progress",
                        protxt,
                        "-i",
                        self.cfg.novoice_mp4,
                        "-i",
                        target_m4a,
                        '-map', '0:v',
                        '-map', '1:a',
                        "-c:v",
                        f'libx{self.video_codec_num}',
                        "-c:a",
                        "copy",
                        "-vf",
                        f"subtitles={subtitles_file}",
                        "-movflags",
                        "+faststart",
                        '-crf', str(config.settings.get("crf", 23)),
                        '-preset', config.settings.get('preset', 'fast')                        
                    ]
                    if self.cfg.video_autorate:
                        cmd.extend(["-fps_mode", "vfr"])

                    cmd.extend(["-t", str(duration_s),tmp_target_mp4])
                # 软字幕有配音 无需重编码
                else:
                    self._signal(text=config.tr('peiyin-ruanzimu'))
                    cmd = [
                        "-y",
                        "-progress",
                        protxt,
                        "-i",
                        self.cfg.novoice_mp4,
                        "-i",
                        target_m4a,
                        "-i",
                        subtitles_file,
                        "-map", "0:v",  # 取第1个输入的视频流
                        "-map", "1:a",  # 取第2个输入的音频流
                        "-map", "2:s",  # 取第3个输入的字幕流

                        "-c:v",
                        v_codec,
                        "-c:a",
                        "copy",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={subtitle_langcode}",
                        "-movflags",
                        "+faststart"                        
                    ]
                    if not is_copy_mode:
                        cmd.extend([
                            '-crf',
                            f'{config.settings.get("crf",23)}',
                            '-preset',
                            config.settings.get('preset','fast')
                        ])                        
                        # 处理 VFR (仅在重新编码时有效)
                        if self.cfg.video_autorate:
                            cmd.extend(["-fps_mode", "vfr"])
                    cmd.extend(["-t",str(duration_s),tmp_target_mp4])

            # 无字幕有配音 无需重编码
            elif self.cfg.voice_role != 'No':                
                self._signal(text=config.tr('onlypeiyin'))
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.cfg.novoice_mp4,
                    "-i",
                    target_m4a,
                    '-map', '0:v',
                    '-map', '1:a',
                    "-c:v",
                    v_codec,
                    "-c:a",
                    "copy",
                    "-movflags",
                    "+faststart"
                ]
                if not is_copy_mode:
                    cmd.extend([
                        '-crf',
                        f'{config.settings.get("crf",23)}',
                        '-preset',
                        config.settings.get('preset','fast')
                    ])
                    if self.cfg.video_autorate:
                        cmd.extend(["-fps_mode", "vfr"])

                cmd.extend(["-t",str(duration_s), tmp_target_mp4])
            # 硬字幕无配音  原始 wav 合并  必须重编码
            elif self.cfg.subtitle_type in [1, 3]:
                self._signal(text=config.tr('onlyyingzimu'))
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.cfg.novoice_mp4
                ]
                if tools.vail_file(target_m4a):
                    cmd.extend(['-i',Path(target_m4a).as_posix(),'-map', '0:v','-map', '1:a'])

                cmd.append('-c:v')
                cmd.append(f'libx{self.video_codec_num}')
                if tools.vail_file(target_m4a):
                    cmd.append('-c:a')
                    cmd.append('copy')
                cmd += [
                    "-vf",
                    f"subtitles={subtitles_file}",
                    "-movflags",
                    "+faststart",
                    '-crf',
                    f'{config.settings.get("crf",23)}',
                    '-preset',
                    config.settings.get('preset','fast')
                ]
                if self.cfg.video_autorate:
                    cmd.extend(["-fps_mode", "vfr"])
                cmd.extend(["-t",str(duration_s),tmp_target_mp4])
            # 软字幕无配音 无需重编码
            elif self.cfg.subtitle_type in [2, 4]:
                self._signal(text=config.tr('onlyruanzimu'))
                # 原视频
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    self.cfg.novoice_mp4
                ]
                # 原配音流
                if tools.vail_file(target_m4a):
                    cmd.extend(['-i',Path(target_m4a).as_posix()])
                # 目标字幕流
                cmd += [
                    "-i",
                    subtitles_file,
                ]
                if tools.vail_file(target_m4a):
                    cmd.extend(['-map', '0:v','-map', '1:a','-map','2:s'])
                else:
                    cmd.extend(['-map', '0:v','-map', '1:s',])
                
                cmd+=[
                    "-c:v",
                    v_codec
                ]
                if tools.vail_file(target_m4a):
                    cmd.append('-c:a')
                    cmd.append('copy')
                cmd += [
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={subtitle_langcode}",
                    "-movflags",
                    "+faststart"                    
                ]
                if not is_copy_mode:
                    cmd.extend([
                        '-crf',
                        f'{config.settings.get("crf",23)}',
                        '-preset',
                        config.settings.get('preset','fast')
                    ])
                    if self.cfg.video_autorate:
                        cmd.extend(["-fps_mode", "vfr"])
                cmd.extend([
                    "-t",str(duration_s),
                    tmp_target_mp4
                ])
            if cmd:
                tools.runffmpeg(cmd,cmd_dir=self.cfg.cache_folder,force_cpu=False)
            shutil.move(tmp_target_mp4,self.cfg.targetdir_mp4)
            os.chdir(config.ROOT_DIR)
        except Exception as e:
            msg =tr('Error in embedding the final step of the subtitle dubbing')
            raise RuntimeError(msg)
        
        
        try:
            shutil.rmtree(self.cfg.cache_folder,ignore_errors=True)        
        except:
            pass
        
        self._create_txt()
        self.precent = 100
        time.sleep(1)
        self.hasend = True
        # 有可能输出原始音频到目标文件夹的程序仍在执行，但不影响
        while output_source_output is not True:
            print(f'{output_source_output=}')
            time.sleep(1)
        return True

    def _get_origin_audio(self,output):
        # 无需配音的场景下取出原始音频
        if self.video_info.get('streams_audio',0)==0:
            # 无音频流
            return
        cmd=[
            "-y",
            "-i",
            self.cfg.name,
            "-vn"
        ]
        if self.video_info['audio_codec_name']=='aac':
            cmd.extend(['-c:a','copy'])
        else:
            cmd.extend(['-c:a','aac','-b:a','128k'])
        cmd.append(output)
        return tools.runffmpeg(cmd)
        

    # ffmpeg进度日志
    def _hebing_pro(self, protxt,video_time=0) -> None:
        while 1:
            if config.exit_soft or self.hasend or self.precent >= 100:return

            content = tools.read_last_n_lines(protxt)
            if not content:
                time.sleep(0.5)
                continue

            if content[-1] == 'progress=end':
                return
            idx = len(content) - 1
            end_time = "00:00:00"
            while idx > 0:
                if content[idx].startswith('out_time='):
                    end_time = content[idx].split('=')[1].strip()
                    break
                idx -= 1
            self._signal(text=config.tr('kaishihebing') + f' {end_time}')
            time.sleep(0.5)


    # 创建说明txt
    def _create_txt(self) -> None:
        try:

            with open(self.cfg.target_dir + f'/{config.tr("readme")}.txt',
                        'w', encoding="utf-8", errors="ignore") as f:
                f.write(f"""以下是可能生成的全部文件, 根据执行时配置的选项不同, 某些文件可能不会生成, 之所以生成这些文件和素材，是为了方便有需要的用户, 进一步使用其他软件进行处理, 而不必再进行语音导出、音视频分离、字幕识别等重复工作

        *.mp4 = 最终完成的目标视频文件
        {self.cfg.source_language_code}.m4a = 原始视频中的音频文件
        {self.cfg.target_language_code}.m4a = 配音后的音频文件
        {self.cfg.source_language_code}.srt = 原始视频中根据声音识别出的字幕文件
        {self.cfg.target_language_code}.srt = 翻译为目标语言后字幕文件
        speaker.json = 说话人标志
        -Noxxx.srt = 未进行重新断句之前的字幕
        shuang.srt = 双语字幕
        vocal.wav = 原始视频中分离出的人声音频文件
        instrument.wav = 原始视频中分离出的背景音乐音频文件


        如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，欢迎各位小额赞助，有了一定资金支持，我将能够持续投入更多时间和精力
        捐助地址：https://pvt9.com/about

        ====

        Here are the descriptions of all possible files that might exist. Depending on the configuration options when executing, some files may not be generated.

        *.mp4 = The final completed target video file
        {self.cfg.source_language_code}.m4a = The audio file in the original video
        {self.cfg.target_language_code}.m4a = dubbing audio
        {self.cfg.source_language_code}.srt = Subtitles recognized in the original video
        {self.cfg.target_language_code}.srt = Subtitles translated into the target language
        shuang.srt = Source language and target language subtitles srt 
        vocal.wav = The vocal audio file separated from the original video
        instrument.wav = The background music audio file separated from the original video


        If you feel that this project is valuable to you and hope that it can be maintained consistently, we welcome small sponsorships. With some financial support, I will be able to continue to invest more time and energy
        Donation address: https://ko-fi.com/jianchang512


        ====

        Github: https://github.com/jianchang512/pyvideotrans
        Docs: https://pvt9.com

                        """)
        except:
            pass
