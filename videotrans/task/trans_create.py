import re
import shutil
import threading
import time
from pathlib import Path

from videotrans.configure import config
from videotrans.task.step import Runstep
from videotrans.translator import get_audio_code
from videotrans.util import tools


class TransCreate():
    def __init__(self, config_params: dict = None, obj=None):
        # 视频原始路径 名称等信息
        # self.obj = obj
        # 配置信息
        self.config_params = config_params

        # 进度
        self.step_inst = None
        self.hasend = False
        self.video_codec = int(config.settings['video_codec'])
        self.status_text = config.transobj['ing']

        # 是否需要语音识别
        self.shoud_recogn = False
        # 是否需要字幕翻译
        self.shoud_trans = False
        # 是否需要配音
        self.shoud_dubbing = False
        # 是否需要嵌入配音或字幕
        self.shoud_hebing = False
        # 是否需要人声分离
        self.shoud_separate = False

        # 初始化后的信息
        self.init = {
            'background_music': None,
            'detect_language': None,
            'subtitle_language': None,
            "name": obj['name'],
            "dirname": obj['dirname'],
            "basename": obj['basename'],
            "noextname": obj['noextname'],
            "ext": obj['ext'],
            "target_dir": obj['target_dir'],
            "uuid": obj['uuid']
        }
        self.uuid = obj['uuid']

        # 视频信息
        self.init['video_info'] = {}
        # 是否是标准264，无需重新编码
        self.init['h264'] = False
        # 缓存目录
        self.init['cache_folder'] = None

        # 原始语言代码
        self.init['source_language_code'] = None
        # 目标语言代码
        self.init['target_language_code'] = None
        # 字幕检测语言
        self.init['detect_language'] = None

        # 拆分后的无声mp4
        self.init['novoice_mp4'] = None
        # 原语言字幕
        self.init['source_sub'] = None
        # 目标语言字幕
        self.init['target_sub'] = None
        # 原音频
        self.init['source_wav'] = None
        # 目标语言音频
        self.init['target_wav'] = None
        # 最终目标生成mp4
        self.init['targetdir_mp4'] = None
        # 分离出的背景音频
        self.init['instrument'] = None
        # 分离出的人声
        self.init['vocal'] = None
        # 识别音频
        self.init['shibie_audio'] = None

        # 视频信息
        '''
        result={
            "video_fps":0,
            "video_codec_name":"h264",
            "audio_codec_name":"aac",
            "width":0,
            "height":0,
            "time":0
        }
        '''

        # 存在添加的背景音乐
        if tools.vail_file(self.config_params['back_audio']):
            self.init['background_music'] = Path(self.config_params['back_audio']).as_posix()

        # 如果不是仅提取，则获取视频信息
        if self.config_params['app_mode'] not in ['tiqu']:
            # 获取视频信息
            try:
                tools.set_process("分析视频数据，用时可能较久请稍等.." if config.defaulelang == 'zh' else "Hold on a monment",
                                  type="logs", uuid=self.uuid)
                self.init['video_info'] = tools.get_video_info(self.init['name'])
            except Exception as e:
                raise Exception(f"{config.transobj['get video_info error']}:{str(e)}")

            if not self.init['video_info']:
                raise Exception(config.transobj['get video_info error'])
            video_codec = 'h264' if self.video_codec == 264 else 'hevc'
            if self.init['video_info']['video_codec_name'] == video_codec and self.init['ext'].lower() == 'mp4':
                self.init['h264'] = True

        # 临时文件夹
        self.init['cache_folder'] = f"{config.TEMP_DIR}/{self.init['noextname']}"
        self.init['target_dir'] = Path(self.init['target_dir']).as_posix()
        # 创建文件夹
        Path(self.init['target_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.init['cache_folder']).mkdir(parents=True, exist_ok=True)

        # 原始语言代码
        source_code = self.config_params['source_language'] if self.config_params[
                                                                   'source_language'] in config.langlist else config.rev_langlist.get(
            self.config_params['source_language'], None)
        if source_code:
            self.init['source_language_code'] = source_code
        # 目标语言代码
        target_code = self.config_params['target_language'] if self.config_params[
                                                                   'target_language'] in config.langlist else config.rev_langlist.get(
            self.config_params['target_language'], None)
        if target_code:
            self.init['target_language_code'] = target_code

        # 检测字幕原始语言
        self.init['detect_language'] = get_audio_code(show_source=self.init['source_language_code'])

        # 存放分离后的无声音mp4
        self.init['novoice_mp4'] = f"{self.init['target_dir']}/novoice.mp4"
        # 原始语言一定存在
        self.init['source_sub'] = f"{self.init['target_dir']}/{self.init['source_language_code']}.srt"
        self._unlink_size0(self.init['source_sub'])

        # 原始语言wav
        self.init['source_wav'] = f"{self.init['target_dir']}/{self.init['source_language_code']}.m4a"
        self._unlink_size0(self.init['source_wav'])

        # 目标语言字幕文件
        if self.init['target_language_code']:
            self.init['target_sub'] = f"{self.init['target_dir']}/{self.init['target_language_code']}.srt"
            self._unlink_size0(self.init['target_sub'])
            # 配音后的目标语言音频文件
            self.init['target_wav'] = f"{self.init['target_dir']}/{self.init['target_language_code']}.m4a"
            self._unlink_size0(self.init['target_wav'])

        # 是否需要语音识别:只要不存在原始语言字幕文件就需要识别
        if not Path(self.init['source_sub']).exists():
            self.shoud_recogn = True
            # 作为识别音频
            self.init['shibie_audio'] = f"{self.init['target_dir']}/shibie.wav"
            self._unlink_size0(self.init['shibie_audio'])

        # 是否需要翻译:存在目标语言代码并且不等于原始语言，并且不存在目标字幕文件，则需要翻译
        if self.init['target_language_code'] and self.init['target_language_code'] != self.init[
            'source_language_code'] and not Path(self.init['target_sub']).exists():
            self.shoud_trans = True

        # 如果原语言和目标语言相等，并且存在配音角色，则替换配音
        if self.config_params['voice_role'] != 'No' and self.init['source_language_code'] == self.init[
            'target_language_code']:
            self.init['target_wav'] = f"{self.init['target_dir']}/{self.init['target_language_code']}-dubbing.m4a"
            self._unlink_size0(self.init['target_wav'])
        # 如果配音角色不是No 并且不存在目标音频，则需要配音
        if self.config_params['voice_role'] != 'No':
            self.shoud_dubbing = True

        # 如果不是tiqu，则均需要合并
        if self.config_params['app_mode'] != 'tiqu':
            self.shoud_hebing = True

        # 最终需要输出的mp4视频
        self.init['targetdir_mp4'] = f"{self.init['target_dir']}/{self.init['noextname']}.mp4"
        self._unlink_size0(self.init['targetdir_mp4'])
        # 是否需要背景音分离：分离出的原始音频文件
        if self.config_params['is_separate']:
            # 背景音乐
            self.init['instrument'] = f"{self.init['target_dir']}/instrument.wav"
            # 转为8k采样率，降低文件
            self.init['vocal'] = f"{self.init['target_dir']}/vocal.wav"
            self.shoud_separate = True
            self._unlink_size0(self.init['instrument'])
            self._unlink_size0(self.init['vocal'])

        # 如果存在字幕，则视为原始语言字幕，不再识别
        if "subtitles" in self.config_params and self.config_params['subtitles'].strip():
            # 如果不存在目标语言，则视为原始语言字幕
            sub_file = self.init['source_sub']
            with open(sub_file, 'w', encoding="utf-8", errors="ignore") as f:
                txt = re.sub(r':\d+\.\d+', lambda m: m.group().replace('.', ','),
                             self.config_params['subtitles'].strip(), re.S | re.M)
                f.write(txt)
            self.shoud_recogn = False
        config.logger.info(f"{self.init=}")

    # 删掉尺寸为0的无效文件
    def _unlink_size0(self, file):
        p = Path(file)
        if p.exists() and p.stat().st_size == 0:
            p.unlink(missing_ok=True)

    # 启动执行入口
    def prepare(self):
        # 获取set.ini配置
        config.settings = config.parse_init()
        # 禁止修改字幕
        tools.set_process("forbid" if self.config_params['is_batch'] else "no", type="disabled_edit", uuid=self.uuid)

        self.step_inst = Runstep(init=self.init, config_params=self.config_params, parent=self)

        # 开启一个线程读秒
        def runing():
            t = 0
            while not self.hasend:
                time.sleep(2)
                t += 2
                tools.set_process(f"{self.status_text} {t}s???{self.step_inst.precent}", type="set_precent",
                                  uuid=self.uuid, nologs=True)

        threading.Thread(target=runing).start()
        # 将原始视频分离为无声视频和音频
        self._split_wav_novicemp4()
        return True

    def __getattr__(self, precent):
        return self.step_inst.precent if self.step_inst else 0

    # 分离音频 和 novoice.mp4
    def _split_wav_novicemp4(self):
        # 不是 提取字幕时，需要分离出视频
        if self.config_params['app_mode'] not in ['tiqu']:
            config.queue_novice[self.init['noextname']] = 'ing'
            threading.Thread(
                target=tools.split_novoice_byraw,
                args=(self.init['name'],
                      self.init['novoice_mp4'],
                      self.init['noextname'],
                      "copy" if self.init['h264'] else f"libx{self.video_codec}")).start()
            if not self.init['h264']:
                self.status_text = '视频需要转码，耗时可能较久..' if config.defaulelang == 'zh' else 'Video needs transcoded and take a long time..'
        else:
            config.queue_novice[self.init['noextname']] = 'end'

        # 添加是否保留背景选项
        if self.config_params['is_separate']:
            try:
                tools.set_process(config.transobj['Separating background music'], type="logs", uuid=self.uuid)
                self.status_text = config.transobj['Separating background music']
                tools.split_audio_byraw(
                    self.init['name'],
                    self.init['source_wav'],
                    True,
                    uuid=self.uuid)
            except Exception as e:
                pass
            finally:
                if not tools.vail_file(self.init['vocal']):
                    # 分离失败
                    self.init['instrument'] = None
                    self.init['vocal'] = None
                    self.config_params['is_separate'] = False
                    self.shoud_separate = False
                elif self.shoud_recogn:
                    # 需要识别时
                    # 分离成功后转为16k待识别音频
                    tools.conver_to_16k(self.init['vocal'], self.init['shibie_audio'])
        # 不分离，或分离失败
        if not self.config_params['is_separate']:
            try:
                self.status_text = config.transobj['kaishitiquyinpin']
                tools.split_audio_byraw(self.init['name'], self.init['source_wav'])
                # 需要识别
                if self.shoud_recogn:
                    tools.conver_to_16k(self.init['source_wav'], self.init['shibie_audio'])
            except Exception as e:
                raise Exception(
                    '从视频中提取声音失败，请检查视频中是否含有音轨，或该视频是否存在编码问题' if config.defaulelang == 'zh' else 'Failed to extract sound from video, please check if the video contains an audio track or if there is an encoding problem with that video')
        self.status_text = config.transobj['endfenliyinpin']
        return True

    # 开始识别
    def recogn(self):
        if not self.shoud_recogn:
            return True
        self.status_text = config.transobj['kaishitiquzimu']
        try:
            self.step_inst.recogn()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.init["basename"]}')
            raise
        if self.config_params['app_mode'] == 'tiqu' and not self.shoud_trans:
            self.hasend = True
            self.step_inst.precent = 100
        self.status_text = config.transobj['endtiquzimu']
        return True

    def trans(self):
        if not self.shoud_trans:
            return True
        self.status_text = config.transobj['starttrans']
        try:
            self.step_inst.trans()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.init["basename"]}')
            raise
        if self.config_params['app_mode'] == 'tiqu':
            self.hasend = True
            self.step_inst.precent = 100
        self.status_text = config.transobj['endtrans']
        return True

    def dubbing(self):
        if self.config_params['app_mode'] == 'tiqu':
            self.step_inst.precent = 100
            return True
        if not self.shoud_dubbing:
            return True
        self.status_text = config.transobj['kaishipeiyin']

        try:
            self.step_inst.dubbing()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.init["basename"]}')
            raise
        if self.config_params['app_mode'] in ['tiqu']:
            self.step_inst.precent = 100
        return True

    def align(self):
        if self.config_params['app_mode'] == 'tiqu':
            self.step_inst.precent = 100
            return True

        if not self.shoud_dubbing:
            return True
        self.status_text = config.transobj['duiqicaozuo']
        try:
            self.step_inst.align()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.init["basename"]}')
            raise
        return True

    def hebing(self):
        if not self.shoud_hebing:
            self.step_inst.precent = 100
            return True
        self.status_text = config.transobj['kaishihebing']
        try:
            self.step_inst.hebing()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.init["basename"]}')
            raise
        self.step_inst.precent = 100
        return True

    # 收尾，根据 output和 linshi_output是否相同，不相同，则移动
    def move_at_end(self):
        self.hasend = True
        self.step_inst.precent = 100

        # 提取时，删除
        if self.config_params['app_mode'] == 'tiqu':
            Path(f"{self.init['target_dir']}/{self.init['source_language_code']}.srt").unlink(missing_ok=True)
            Path(f"{self.init['target_dir']}/{self.init['target_language_code']}.srt").unlink(missing_ok=True)
        # 仅保存视频
        elif self.config_params['only_video']:
            outputpath = Path(self.init['target_dir'])
            for it in outputpath.iterdir():
                ext = it.suffix.lower()
                if ext != '.mp4':
                    it.unlink(missing_ok=True)
                else:
                    try:
                        shutil.copy2(Path(it).as_posix(),(it.parent / "../" / f'{it.name}').resolve().as_posix())
                    except Exception:
                        pass
            try:
                self.init['target_dir'] = outputpath.parent.resolve().as_posix()
                shutil.rmtree(outputpath.as_posix(), ignore_errors=True)
            except Exception:
                pass

        tools.set_process(
            f"{self.init['name']}",
            type='succeed',
            uuid=self.uuid
        )
        tools.send_notification("Succeed", f"{self.init['basename']}")
        return True
