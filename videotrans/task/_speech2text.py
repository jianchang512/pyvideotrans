import json,os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from videotrans import recognition
from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.recognition import run, Faster_Whisper_XXL, Whisper_CPP
from videotrans.task._base import BaseTask

from videotrans.util import tools

"""
仅语音识别
"""


@dataclass
class SpeechToText(BaseTask):
    # 识别后输出的字幕格式，srt txt 等
    out_format: str = field(init=True, default='srt')
    # 在这个子类中，shoud_recogn 总是 True。
    shoud_recogn: bool = field(default=True, init=False)
    # 是否需要将生成的字幕复制到原始视频所在目录下，并重命名为视频同名，以方便视频自动加载软字幕
    copysrt_rawvideo: bool = field(default=False, init=True)
    # 存放原始语言字幕
    source_srt_list: List = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        # -1=不启用说话人，0=启用并且不限制说话人数量，>0+1是最大说话人数量
        self.max_speakers=self.cfg.nums_diariz if self.cfg.enable_diariz else -1
        if self.max_speakers>0:
            self.max_speakers+=1
        # 存放目标文件夹
        if not self.cfg.target_dir:
            self.cfg.target_dir = config.HOME_DIR + f"/recogn"
        # 转录后的目标字幕文件，先统一转为srt，然后再使用ffmpeg转为其他格式字幕
        self.cfg.target_sub = self.cfg.target_dir + '/' + self.cfg.noextname + '.srt'
        # 临时文件夹
        self.cfg.cache_folder = config.TEMP_DIR + f'/{self.uuid}'
        Path(self.cfg.target_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
        # 处理为 16k 的wav单通道音频，供模型识别用
        self.cfg.shibie_audio = self.cfg.cache_folder + f'/{self.cfg.noextname}-{time.time()}.wav'
        self._signal(text=tr("Speech Recognition to Word Processing"))

    # 预先处理
    def prepare(self):
        if self._exit():
            return
        tools.conver_to_16k(self.cfg.name, self.cfg.shibie_audio)

    def recogn(self):
        if self._exit(): return
        while 1:
            # 尚未生成
            if Path(self.cfg.shibie_audio).exists():
                break
            time.sleep(0.5)
        try:
            # 需要降噪
            if self.cfg.remove_noise:
                title=tr("Starting to process speech noise reduction, which may take a long time, please be patient")
                from videotrans.process.prepare_audio import remove_noise
                kw={
                    "input_file":self.cfg.shibie_audio,
                    "output_file":f"{self.cfg.cache_folder}/removed_noise_{time.time()}.wav",
                    "TEMP_DIR":config.TEMP_DIR,
                    "is_cuda":self.cfg.cuda
                }
                # 静默失败，不处理
                try:
                    _rs = self._new_process(callback=remove_noise,title=title,kwargs=kw)
                    if _rs:
                        self.cfg.shibie_audio=_rs
                except:
                    pass
            if self._exit(): return
            # faster_xxl.exe 单独处理
            if self.cfg.recogn_type == Faster_Whisper_XXL:
                cmd = [
                    config.settings.get('Faster_Whisper_XXL', ''),
                    self.cfg.shibie_audio,
                    "-pp",
                    "-f", "srt"
                ]
                if self.cfg.detect_language != 'auto':
                    cmd.extend(['-l', self.cfg.detect_language.split('-')[0]])

                prompt = None
                if self.cfg.detect_language != 'auto':
                    prompt = config.settings.get(f'initial_prompt_{self.cfg.detect_language}')
                if prompt:
                    cmd += ['--initial_prompt', prompt]

                cmd.extend(['--model', self.cfg.model_name, '--output_dir', self.cfg.target_dir])
                txt_file = Path(config.settings.get('Faster_Whisper_XXL', '')).parent.as_posix() + '/pyvideotrans.txt'
                if Path(txt_file).exists():
                    cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))

                outsrt_file = self.cfg.target_dir + '/' + Path(self.cfg.shibie_audio).stem + ".srt"
                cmdstr = " ".join(cmd)
                config.logger.debug(f'Faster_Whisper_XXL: {cmdstr=}\n{outsrt_file=}\n{self.cfg.target_sub=}')

                self._external_cmd_with_wrapper(cmd)

                try:
                    shutil.copy2(outsrt_file, self.cfg.target_sub)
                except shutil.SameFileError:
                    pass
                self.source_srt_list = tools.get_subtitle_from_srt(self.cfg.target_sub, is_file=True)
                # return
            elif self.cfg.recogn_type == Whisper_CPP:

                cpp_path = config.settings.get('Whisper.cpp', 'whisper-cli')
                cmd = [
                    cpp_path,
                    "-f",
                    self.cfg.shibie_audio,
                    "-osrt",
                    "-np"
                ]
                cmd += ["-l", self.cfg.detect_language.split('-')[0]]
                prompt = None
                if self.cfg.detect_language != 'auto':
                    prompt = config.settings.get(f'initial_prompt_{self.cfg.detect_language}')
                if prompt:
                    cmd += ['--prompt', prompt]
                cpp_folder = Path(cpp_path).parent.resolve().as_posix()
                if not Path(f'{cpp_folder}/models/{self.cfg.model_name}').is_file():
                    raise RuntimeError(
                        tr('The model does not exist. Please download the model to the {} directory first.',
                           f'{cpp_folder}/models'))
                txt_file = cpp_folder + '/pyvideotrans.txt'
                if Path(txt_file).exists():
                    cmd.extend(Path(txt_file).read_text(encoding='utf-8').strip().split(' '))

                cmd.extend(['-m', f'models/{self.cfg.model_name}', '-of', self.cfg.target_sub[:-4]])

                config.logger.debug(f'Whipser.cpp: {cmd=}')

                self._external_cmd_with_wrapper(cmd)

                self.source_srt_list = tools.get_subtitle_from_srt(self.cfg.target_sub, is_file=True)
                # return
            else:
                # 其他识别渠道
                raw_subtitles = run(
                    recogn_type=self.cfg.recogn_type,
                    uuid=self.uuid,
                    model_name=self.cfg.model_name,
                    audio_file=self.cfg.shibie_audio,
                    detect_language=self.cfg.detect_language,
                    cache_folder=self.cfg.cache_folder,
                    is_cuda=self.cfg.cuda,
                    subtitle_type=0,
                    max_speakers=self.max_speakers,
                    llm_post=self.cfg.rephrase == 1
                )
                self.source_srt_list = raw_subtitles
                self._save_srt_target(self.source_srt_list, self.cfg.target_sub)
                if not raw_subtitles or len(raw_subtitles) < 1:
                    raise RuntimeError(self.cfg.basename + tr('recogn result is empty'))
            if self._exit() or self.cfg.detect_language == 'auto': return
            
            
            # 中英恢复标点符号
            if self.cfg.fix_punc and self.cfg.detect_language[:2] in ['zh','en']:
                text_dict={f'{it["line"]}':re.sub(r'[,.?!，。？！]',' ',it["text"]) for it in self.source_srt_list}
                from videotrans.process.prepare_audio import fix_punc
                kw={"text_dict":text_dict,"TEMP_DIR":config.TEMP_DIR,"is_cuda":self.cfg.cuda}
                try:
                    _rs=self._new_process(callback=fix_punc,title=tr("Restoring punct"),kwargs=kw)
                    if _rs:
                        for it in self.source_srt_list:
                            it['text']=_rs.get(f'{it["line"]}',it['text'])
                            if self.cfg.detect_language[:2]=='en':
                                it['text']=it['text'].replace('，',',').replace('。','. ').replace('？','?').replace('！','!')
                        self._save_srt_target(self.source_srt_list, self.cfg.target_sub)
                except:
                    pass

            
            # whisperx-api
            # openairecogn并且模型是gpt-4o-transcribe-diarize
            # funasr并且模型是paraformer-zh
            # deepgram
            # 以上这些本身已有说话人识别，如果以有说话人，就不再重新断句
            self._signal(text=Path(self.cfg.target_sub).read_text(encoding='utf-8'), type='replace_subtitle')
            if Path(self.cfg.cache_folder+"/speaker.json").exists():
                return


            if self.cfg.rephrase == 1:
                # LLM重新断句
                try:
                    from videotrans.translator._chatgpt import ChatGPT

                    ob = ChatGPT(uuid=self.uuid)
                    self._signal(text=tr("Re-segmenting..."))
                    srt_list = ob.llm_segment(self.source_srt_list, config.settings.get('llm_ai_type', 'openai'))
                    if srt_list and len(srt_list) > len(self.source_srt_list) / 2:
                        self.source_srt_list = srt_list
                        self._save_srt_target(self.source_srt_list, self.cfg.target_sub)
                    else:
                        raise
                except Exception as e:
                    self._signal(text=tr("Re-segmenting Error"))
                    config.logger.warning(f"重新断句失败[except]，已恢复原样 {e}")
        except Exception:
            raise


    def diariz(self):
        if self._exit()  or not self.cfg.enable_diariz or Path(self.cfg.cache_folder + "/speaker.json").exists():
            return
            
        # built pyannote reverb ali_CAM
        speaker_type=config.settings.get('speaker_type','built')
        hf_token= config.settings.get('hf_token')
        if speaker_type=='built' and self.cfg.detect_language[:2] not in ['zh','en']:
            config.logger.error(f'当前选择 built 说话人分离模型，但不支持当前语言:{self.cfg.detect_language}')
            return
        if speaker_type in ['pyannote','reverb'] and not hf_token:
            config.logger.error(f'当前选择 pyannote 说话人分离模型，但未设置 huggingface.co 的token: {self.cfg.detect_language}')
            return
        if speaker_type in ['pyannote','reverb']:
            # 判断是否可访问 huggingface.co
            # 先测试能否连接 huggingface.co, 中国大陆地区不可访问，除非使用VPN
            try:
                import requests
                requests.head('https://huggingface.co',timeout=5)
            except Exception:
                config.logger.error(f'当前选择 {speaker_type} 说话人分离模型，但无法连接到 https://huggingface.co,可能会失败')

        self.precent += 3
        title=tr(f'Begin separating the speakers')+f':{speaker_type=}'
        spk_list=None
        kw={
                "input_file":self.cfg.shibie_audio,
                "subtitles":[ [it['start_time'],it['end_time']] for it in self.source_srt_list],
                "num_speakers":self.max_speakers,
                "TEMP_DIR":config.TEMP_DIR,
                "is_cuda":self.cfg.cuda
        }
        if speaker_type=='built':
            from videotrans.process.prepare_audio import built_speakers as _run_speakers
            del kw['is_cuda']
            kw['num_speakers']=-1 if self.max_speakers<1 else self.max_speakers
            kw['language']=self.cfg.detect_language
        elif speaker_type=='ali_CAM':
            from videotrans.process.prepare_audio import cam_speakers as _run_speakers
        elif speaker_type=='pyannote':
            from videotrans.process.prepare_audio import pyannote_speakers as _run_speakers
        elif speaker_type=='reverb':
            from videotrans.process.prepare_audio import reverb_speakers as _run_speakers
        else:
            config.logger.error(f'当前所选说话人分离模型不支持:{speaker_type=}')
            return
        try:
            spk_list=self._new_process(callback=_run_speakers,title=title,kwargs=kw)
            if spk_list:
                Path(self.cfg.cache_folder+"/speaker.json").write_text(json.dumps(spk_list),encoding='utf-8')
                config.logger.debug('分离说话人成功完成')
        except:
            pass
        self._signal(text=tr('separating speakers end'))



    def task_done(self):
        if self._exit(): return
        if self.cfg.enable_diariz and config.params.get("stt_spk_insert") and Path(self.cfg.cache_folder + "/speaker.json").exists():
            speakers = json.loads(Path(self.cfg.cache_folder + "/speaker.json").read_text(encoding='utf-8'))
            if speakers:
                speakers_len = len(speakers)
                for i, it in enumerate(self.source_srt_list):
                    if i < speakers_len and speakers[i]:
                        it['text'] = f'[{speakers[i]}]{it["text"]}'
        self._save_srt_target(self.source_srt_list, self.cfg.target_sub)
        self._signal(text=f"{self.cfg.name}", type='succeed')
        if self.out_format == 'txt':
            import re
            content = Path(self.cfg.target_sub).read_text(encoding='utf-8')
            content = re.sub(r"(\r\n|\r|\n|\s|^)\d+(\r\n|\r|\n)", "\n", content,flags=re.I | re.S)
            content = re.sub(r'\n\d+:\d+:\d+(\,\d+)\s*-->\s*\d+:\d+:\d+(\,\d+)?\n?', '', content,flags=re.I | re.S)
            with open(self.cfg.target_sub[:-3] + 'txt', 'w', encoding='utf-8') as f:
                f.write(content)
            self.cfg.target_sub = self.cfg.target_sub[:-3] + 'txt'
        elif self.out_format != 'srt':
            tools.runffmpeg(['-y', '-i', self.cfg.target_sub, self.cfg.target_sub[:-3] + self.out_format])
            Path(self.cfg.target_sub).unlink(missing_ok=True)
            self.cfg.target_sub = self.cfg.target_sub[:-3] + self.out_format

        if self.copysrt_rawvideo:
            p = Path(self.cfg.name)
            try:
                shutil.copy2(self.cfg.target_sub, f'{p.parent.as_posix()}/{p.stem}.{self.out_format}')
            except shutil.SameFileError:
                pass
        try:
            if self.cfg.shound_del_name:
                Path(self.cfg.shound_del_name).unlink(missing_ok=True)
        except Exception:
            pass
        tools.send_notification(tr('Succeed'), f"{self.cfg.basename}")

    def _exit(self):
        if config.exit_soft or config.box_recogn != 'ing':
            self.hasend = True
            return True
        return False
