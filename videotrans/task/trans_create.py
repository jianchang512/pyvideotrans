import datetime
import shutil
import threading
import time
from videotrans.configure import config
from videotrans.task.step import Runstep
from videotrans.translator import get_audio_code
from videotrans.util import tools
from pathlib import Path


class TransCreate():
    '''

    obj={
        "raw_name":name,
        # 原始视频所在原始目录
        "raw_dirname":raw_dirname,
        # 原始视频原始名字带后缀
        "raw_basename":raw_basename,
        # 原始视频名字不带后缀
        "raw_noextname":raw_noextname,
        # 原始后缀不带 .
        "raw_ext":ext[1:],
        # 处理后 移动后符合规范的目录名
        "dirname":"",
        # 符合规范的基本名带后缀
        "basename":"",
        # 符合规范的不带后缀
        "noextname":"",
        # 扩展名
        "ext":ext[1:],
        # 最终存放目标位置，直接存到这里
        "output": f'{out}/{raw_noextname}' if out else f'{raw_dirname}/{raw_noextname}',
        "unid":"",
        "source_mp4":name
    }

    '''

    def __init__(self, config_params: dict = None, obj=None):
        # 视频原始路径 名称等信息
        self.obj = obj
        # 配置信息
        self.config_params = config_params

        # 进度
        self.step_inst = None
        self.hasend = False
        self.video_codec = int(config.settings['video_codec'])
        self.status_text = config.transobj['ing']

        # 初始化后的信息
        self.init = {
            'background_music': None,
            'detect_language': None,
            'subtitle_language': None,
        }
        # 目标目标。 linshi_out
        self.init['target_dir'] = None
        self.init['btnkey'] = None
        self.init['noextname'] = None

        # 视频信息
        self.init['video_info'] = {}
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
        # 最终目标生成mp4，在linshioutput下
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

        # 如果是字幕创建配音模式
        if self.config_params['app_mode'] == 'peiyin':
            self.init['noextname'] = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.init['target_dir'] = self.config_params['target_dir'] if self.config_params[
                'target_dir'] else f"{config.homedir}/only_dubbing"
            self.init['btnkey'] = "srt2wav"
        else:
            # 不带后缀的视频名字
            self.init['noextname'] = self.obj['noextname']
            # 进度按钮
            self.init['btnkey'] = self.obj['unid']
            # 临时作为目标目录，最后再根据条件移动
            self.init['target_dir'] = self.obj['linshi_output']
            # 如果不是仅提取，则获取视频信息
            if self.config_params['app_mode'] not in ['tiqu', 'peiyin']:
                # 获取视频信息
                try:
                    tools.set_process("分析视频数据，用时可能较久请稍等.." if config.defaulelang == 'zh' else "Hold on a monment",
                                      btnkey=self.init['btnkey'])
                    self.init['video_info'] = tools.get_video_info(self.obj['source_mp4'])
                except Exception as e:
                    raise Exception(f"{config.transobj['get video_info error']}:{str(e)}")

                if not self.init['video_info']:
                    raise Exception(config.transobj['get video_info error'])
                video_codec = 'h264' if self.video_codec == 264 else 'hevc'
                if self.init['video_info']['video_codec_name'] == video_codec and self.obj['ext'].lower() == 'mp4':
                    self.init['h264'] = True

        # 临时文件夹
        self.init['cache_folder'] = f"{config.TEMP_DIR}/{self.init['noextname']}"
        self.init['target_dir'] = Path(self.init['target_dir']).as_posix()
        # 创建文件夹
        Path(self.init['target_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.init['cache_folder']).mkdir(parents=True, exist_ok=True)

        # 获取原语言代码和目标语言代码
        if "mode" in self.config_params and self.config_params['mode'] == "cli":
            self.init['source_language_code'] = self.config_params['source_language']
            self.init['target_language_code'] = self.config_params['target_language']
        elif self.config_params['app_mode'] != 'hebing':
            # 仅作为文件名标识
            var_a = config.rev_langlist.get(self.config_params['source_language'])
            var_b = config.langlist.get(self.config_params['source_language'])
            var_c = var_a if var_a is not None else var_b
            self.init['source_language_code'] = var_c if var_c != '-' else '-'
            var_a = config.rev_langlist.get(self.config_params['target_language'])
            var_b = config.langlist.get(self.config_params['target_language'])
            var_c = var_a if var_a is not None else var_b
            self.init['target_language_code'] = var_c if var_c != '-' else '-'
        else:
            self.init['target_language_code']=None
            self.init['source_language_code'] = '-'

        # 检测字幕原始语言
        if self.config_params['source_language'] != '-':
            self.init['detect_language'] = get_audio_code(show_source=self.config_params['source_language'])

        self.init['novoice_mp4'] = f"{self.init['target_dir']}/novoice.mp4"
        self.init['source_sub'] = f"{self.init['target_dir']}/{self.init['source_language_code']}.srt"
        self.init['target_sub'] = f"{self.init['target_dir']}/{self.init['target_language_code']}.srt"
        # 原wav
        self.init['source_wav'] = f"{self.init['target_dir']}/{self.init['source_language_code']}.m4a"
        # 配音后的音频文件
        self.init['target_wav'] = f"{self.init['target_dir']}/{self.init['target_language_code']}.m4a"
        # 如果是配音操作
        if self.config_params['app_mode'] == 'peiyin':
            self.init[
                'target_wav'] = f"{self.init['target_dir']}/{self.init['target_language_code']}-{self.init['noextname']}.m4a"
            if self.config_params['clear_cache']:
                Path(self.init['target_wav']).unlink(missing_ok=True)

        # 如果原语言和目标语言相等，并且存在配音角色，则替换配音
        if self.config_params['voice_role'] != 'No' and self.init['source_language_code'] == self.init[
            'target_language_code']:
            self.init['target_wav'] = f"{self.init['target_dir']}/{self.init['target_language_code']}-dubbing.m4a"
        # 最终的mp4视频
        self.init['targetdir_mp4'] = f"{self.init['target_dir']}/{self.init['noextname']}.mp4"

        # 分离出的原始音频文件
        if self.config_params['is_separate']:
            # 背景音乐
            self.init['instrument'] = f"{self.init['target_dir']}/instrument.wav"
            # 转为8k采样率，降低文件
            self.init['vocal'] = f"{self.init['target_dir']}/vocal.wav"
        else:
            self.init['vocal'] = None
            self.init['instrument'] = None

        # 作为识别音频
        self.init['shibie_audio'] = f"{self.init['target_dir']}/shibie.wav"
        # 如果存在字幕，则视为目标字幕，直接生成，不再识别和翻译
        if "subtitles" in self.config_params and self.config_params['subtitles'].strip():
            sub_file = self.init['target_sub']
            if self.config_params['app_mode']=='hebing':
                sub_file=self.init['source_sub']
            elif self.init['source_language_code'] and self.init['target_language_code'] and self.init['source_language_code'] != self.init['target_language_code']:
                # 原始和目标语言都存在，并且不相等，需要翻译，作为待翻译字幕
                sub_file = self.init['source_sub']
            with open(sub_file, 'w', encoding="utf-8", errors="ignore") as f:
                f.write(self.config_params['subtitles'].strip())
        # 如何名字不合规迁移了，并且存在原语言或目标语言字幕
        if self.config_params['app_mode'] not in ['peiyin', 'hebing']:
            # 判断是否存在原始视频同名同目录的srt字幕文件
            raw_source_srt = self.obj['output'] + f"/{self.init['source_language_code']}.srt"
            raw_srt = self.obj['raw_dirname'] + f"/{self.obj['raw_noextname']}.srt"
            if Path(raw_srt).is_file() and Path(raw_srt).stat().st_size > 0:
                config.logger.info(f'{raw_srt=},{raw_source_srt=}使用原始视频同目录下同名字幕文件')
                shutil.copy2(raw_srt, raw_source_srt)


            raw_source_srt_path = Path(raw_source_srt)
            if raw_source_srt_path.is_file():
                if raw_source_srt_path.stat().st_size == 0:
                    print('删除吗')
                    raw_source_srt_path.unlink(missing_ok=True)
                elif self.obj['output'] != self.obj['linshi_output']:
                    config.logger.info(f'使用已放置到目标文件夹下的原语言字幕:{raw_source_srt}')
                    shutil.copy2(raw_source_srt, self.init['source_sub'])
            # 原始目标语言不同时
            raw_target_srt = self.obj['output'] + f"/{self.init['target_language_code']}.srt"
            if raw_source_srt !=raw_target_srt:
                raw_target_srt_path = Path(raw_target_srt)
                if Path(raw_target_srt).is_file():
                    if raw_target_srt_path.stat().st_size == 0:
                        raw_target_srt_path.unlink(missing_ok=True)
                    elif self.obj['output'] != self.obj['linshi_output']:
                        config.logger.info(f'使用已放置到目标文件夹下的目标语言字幕:{raw_target_srt}')
                        shutil.copy2(raw_target_srt, self.init['target_sub'])


    # 启动执行入口
    def prepare(self):
        # 获取set.ini配置
        config.settings = config.parse_init()
        if self.config_params['tts_type'] == 'clone-voice':
            tools.set_process(config.transobj['test clone voice'], btnkey=self.init['btnkey'])
            try:
                tools.get_clone_role(True)
            except Exception as e:
                raise Exception(str(e))
        # 禁止修改字幕
        tools.set_process("forbid" if self.config_params['is_batch'] else "no", "disabled_edit",
                          btnkey=self.init['btnkey'])

        def runing():
            t = 0
            while not self.hasend:
                time.sleep(2)
                t += 2
                tools.set_process(f"{self.status_text} {t}s", btnkey=self.init['btnkey'], nologs=True)

        if self.config_params['app_mode'] not in ['peiyin']:
            threading.Thread(target=runing).start()

        self._split_wav_novicemp4()
        self.step_inst = Runstep(init=self.init, obj=self.obj, config_params=self.config_params, parent=self)
        return True

    def __getattr__(self, precent):
        return self.step_inst.precent if self.step_inst else 0

    # 分离音频 和 novoice.mp4
    def _split_wav_novicemp4(self):
        # 存在视频 不是peiyin
        if self.config_params['app_mode'] == 'peiyin':
            return True

        # 合并字幕时不分离，直接复制
        if self.config_params['app_mode'] == 'hebing':
            shutil.copy2(self.obj['source_mp4'], self.init['novoice_mp4'])
            config.queue_novice[self.init['noextname']] = 'end'
            return True

        # 不是 提取字幕时，需要分离出视频
        if self.config_params['app_mode'] not in ['tiqu']:
            config.queue_novice[self.init['noextname']] = 'ing'
            threading.Thread(target=tools.split_novoice_byraw,
                             args=(self.obj['source_mp4'],
                                   self.init['novoice_mp4'],
                                   self.init['noextname'],
                                   "copy" if self.init['h264'] else f"libx{self.video_codec}")) \
                .start()
        else:
            config.queue_novice[self.init['noextname']] = 'end'

        # 添加是否保留背景选项
        if self.config_params['is_separate'] and not tools.vail_file(self.init['vocal']):
            # 背景分离音
            try:
                tools.set_process(config.transobj['Separating background music'], btnkey=self.init['btnkey'])
                self.status_text = config.transobj['Separating background music']
                tools.split_audio_byraw(self.obj['source_mp4'], self.init['source_wav'], True,
                                        btnkey=self.init['btnkey'])
            except Exception as e:
                pass
            finally:
                if not tools.vail_file(self.init['vocal']):
                    self.init['instrument'] = None
                    self.init['vocal'] = None
                    self.config_params['is_separate'] = False
                else:
                    # 分离成功后转为8k待识别音频
                    tools.conver_to_8k(self.init['vocal'], self.init['shibie_audio'])
        # 不分离，或分离失败
        if not self.config_params['is_separate']:
            try:
                self.status_text = config.transobj['kaishitiquyinpin']
                tools.split_audio_byraw(self.obj['source_mp4'], self.init['source_wav'])
                tools.conver_to_8k(self.init['source_wav'], self.init['shibie_audio'])
            except Exception as e:
                raise Exception(
                    '从视频中提取声音失败，请检查视频中是否含有音轨，或该视频是否存在编码问题' if config.defaulelang == 'zh' else 'Failed to extract sound from video, please check if the video contains an audio track or if there is an encoding problem with that video')
        if self.obj and self.obj['output'] != self.obj['linshi_output'] and tools.vail_file(self.init['source_wav']):
            shutil.copy2(self.init['source_wav'], f"{self.obj['output']}/{Path(self.init['source_wav']).name}")
        return True

    def _unlink(self, file):
        try:
            Path(file).unlink(missing_ok=True)
        except Exception:
            pass

    def recogn(self):
        self.status_text = config.transobj['kaishitiquzimu']
        try:
            print('开始识别')
            self.step_inst.recogn()
            print('结束识别')
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.obj["raw_basename"]}')
            print("识别出错")
            raise Exception(e)
        if self.config_params['app_mode'] == 'tiqu' and (
                self.config_params['source_language'] == self.config_params['target_language'] or self.config_params[
            'target_language'] == '-'):
            print('提取不翻译结束')
            self.step_inst.precent = 100
        return True

    def trans(self):
        self.status_text = config.transobj['starttrans']
        try:
            self.step_inst.trans()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.obj["raw_basename"]}')
            raise Exception(e)
        if self.config_params['app_mode'] == 'tiqu':
            self.step_inst.precent = 100
        return True

    def dubbing(self):
        if self.config_params['app_mode'] == 'tiqu':
            self.step_inst.precent = 100
            return True
        self.status_text = config.transobj['kaishipeiyin']

        try:
            self.step_inst.dubbing()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.obj["raw_basename"]}')
            raise Exception(e)
        if self.config_params['app_mode'] in ['peiyin','tiqu']:
            self.step_inst.precent = 100
        return True

    def hebing(self):
        if self.config_params['app_mode'] in ['tiqu','peiyin']:
            self.step_inst.precent = 100
            return True
        self.status_text = config.transobj['kaishihebing']
        try:
            self.step_inst.hebing()
        except Exception as e:
            self.hasend = True
            tools.send_notification(str(e), f'{self.obj["raw_basename"]}')
            raise Exception(e)
        self.step_inst.precent = 100
        return True

    # 收尾，根据 output和 linshi_output是否相同，不相同，则移动
    def move_at_end(self):
        self.hasend = True
        self.step_inst.precent = 100
        if self.config_params['app_mode'] in ['peiyin']:
            return

        wait_deldir = None
        linshi_deldir = None
        # 需要移动 linshi移动到 output
        if self.obj and self.obj['output'] != self.obj['linshi_output']:
            target_mp4 = Path(self.init['targetdir_mp4'])
            if target_mp4.exists() and target_mp4.stat().st_size > 0:
                target_mp4.rename(Path(self.obj['linshi_output'] + f'/{self.obj["raw_noextname"]}.mp4'))
            shutil.copytree(self.obj['linshi_output'], self.obj['output'], dirs_exist_ok=True)
            linshi_deldir = self.obj['linshi_output']

        # 提取时，删除
        if self.config_params['app_mode'] == 'tiqu':
            self._unlink(f"{self.obj['output']}/{self.init['source_language_code']}.srt")
            self._unlink(f"{self.obj['output']}/{self.init['target_language_code']}.srt")
        # 仅保存视频
        elif self.config_params['only_video']:
            outputpath = Path(self.obj['output'])
            for it in outputpath.iterdir():
                ext = it.suffix.lower()
                # 软字幕时也需要保存字幕, 仅删除非 mp4非srt文件
                if int(self.config_params['subtitle_type']) in [2, 4]:
                    if ext not in ['.mp4', '.srt']:
                        it.unlink(missing_ok=True)
                else:
                    # 其他情况 移动视频到上一级
                    if ext != '.mp4':
                        it.unlink(missing_ok=True)
                    else:
                        try:
                            it.rename(it.parent / "../" / f'{it.name}')
                        except Exception:
                            pass
            # 不是软字幕则删除文件夹
            if int(self.config_params['subtitle_type']) not in [2, 4]:
                try:
                    self.obj['output'] = outputpath.parent.resolve().as_posix()
                    #wait_deldir = outputpath.resolve().as_posix()
                except Exception:
                    pass

        # 批量不允许编辑字幕
        if not self.config_params['is_batch']:
            tools.set_process('', 'allow_edit', btnkey=self.init['btnkey'])

        tools.set_process(
            f"{self.obj['output']}##{self.obj['raw_basename']}",
            'succeed',
            btnkey=self.init['btnkey']
        )
        tools.send_notification("Succeed", f"{self.obj['raw_basename']}")

        # 删除临时文件
        #shutil.rmtree(self.init['cache_folder'], ignore_errors=True)
        #if linshi_deldir:
        #    shutil.rmtree(linshi_deldir)
        #if wait_deldir:
        #    shutil.rmtree(wait_deldir, ignore_errors=True)
        return True
