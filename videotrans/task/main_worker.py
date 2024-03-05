# -*- coding: utf-8 -*-
import os
import time
from PySide6.QtCore import QThread
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.task.trans_create import TransCreate
from videotrans.tts import text_to_speech
from videotrans.util.tools import set_process, delete_temp, get_subtitle_from_srt, pygameaudio, speed_up_mp3,send_notification


class Worker(QThread):
    def __init__(self, *,parent=None,app_mode=None,txt=None):
        super().__init__(parent=parent)
        self.video = None
        self.app_mode=app_mode
        self.txt=txt

    def srt2audio(self):
        try:
            config.btnkey="srt2wav"
            set_process('srt2wav', 'add_process')
            self.video = TransCreate({"subtitles": self.txt, 'app_mode': self.app_mode})
            st = time.time()
            set_process(config.transobj['kaishichuli'])
            self.video.run()
            # 成功完成
            config.params['line_roles'] = {}
            dur = int(time.time() - st)
            set_process(f"{self.video.target_dir}##{dur}", 'succeed')
            print('srt succeed')
            send_notification(config.transobj["zhixingwc"],
                              f'{self.video.source_mp4 if self.video.source_mp4 else "subtitles -> audio"}, {dur}s')

            
            try:
                if os.path.exists(self.video.novoice_mp4):
                    time.sleep(1)
                    os.unlink(self.video.novoice_mp4)
            except:
                pass
            # 全部完成
            print('beofre end')
            set_process(f"", 'end')
        except Exception as e:
            print(f'srt e {str(e)}')
            if str(e)!='stop':
                set_process(f"{str(e)}", 'error')
                send_notification("Error",  str(e) )
        finally:
            delete_temp(None)


    def run(self) -> None:
        # 字幕配音
        if self.app_mode=='peiyin':
            return self.srt2audio()

        #多个视频处理
        num = 0
        tasks=[]
        for it in config.queue_mp4:
            obj=TransCreate({'subtitles': self.txt, "source_mp4": it, 'app_mode': self.app_mode})
            tasks.append(obj)
            set_process(obj.btnkey, 'add_process')
        task_nums = len(tasks)


        while len(tasks)>0:
            num += 1
            set_process(f"Processing {num}/{task_nums}", 'statusbar')
            try:
                st = time.time()
                if len(tasks)<1:
                    break
                self.video = tasks.pop(0)
                config.btnkey=self.video.btnkey
                set_process(config.transobj['kaishichuli'])
                self.video.run()
                if config.current_status!='ing':
                    return None
                # 成功完成
                config.params['line_roles'] = {}
                dur=int(time.time() - st)
                set_process(f"{self.video.target_dir if not config.params['only_video'] else config.params['target_dir']}##{dur}", 'succeed')
                send_notification(config.transobj["zhixingwc"],f'{dur}s: {self.video.source_mp4}')
                try:
                    if os.path.exists(self.video.novoice_mp4):
                        time.sleep(1)
                        os.unlink(self.video.novoice_mp4)
                except:
                    pass
                if len(config.queue_mp4)>0:
                    config.queue_mp4.pop(0)
            except Exception as e:
                print(f"mainworker {str(e)}")
                if str(e)!='stop':
                    set_process(f"{str(e)}", 'error')
                    send_notification("Error",f"{str(e)}")
                return None
            finally:
                time.sleep(2)
                #if self.video and self.video.noextname:
                #    delete_temp(None)
                if self.video and self.video.del_sourcemp4 and self.video.source_mp4 and os.path.exists(self.video.source_mp4):
                    os.unlink(self.video.source_mp4)
        # 全部完成
        set_process("", 'end')


class Shiting(QThread):
    def __init__(self, obj, parent=None):
        super().__init__(parent=parent)
        self.obj = obj
        self.stop = False

    def run(self):
        # 获取字幕
        try:
            subs = get_subtitle_from_srt(self.obj['sub_name'])
        except Exception as e:
            set_process(f'{config.transobj["geshihuazimuchucuo"]}:{str(e)}')
            return False
        rate = int(str(config.params["voice_rate"]).replace('%', ''))
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        # 取出设置的每行角色
        line_roles = config.params["line_roles"] if "line_roles" in config.params else None
        for it in subs:
            if config.task_countdown <= 0 or self.stop:
                return
            if config.current_status != 'ing':
                return True
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice_role = config.params['voice_role']
            if line_roles and f'{it["line"]}' in line_roles:
                voice_role = line_roles[f'{it["line"]}']
            filename = self.obj['cache_folder'] + f"/{time.time()}.mp3"
            text_to_speech(text=it['text'],
                           role=voice_role,
                           rate=rate,
                           filename=filename,
                           tts_type=config.params['tts_type'],
                           set_p=False
                           )
            audio_data = AudioSegment.from_file(filename, format="mp3")
            mp3len = len(audio_data)

            wavlen = it['end_time'] - it['start_time']
            # 新配音大于原字幕里设定时长
            diff = mp3len - wavlen
            if diff > 0 and config.params["voice_autorate"]:
                speed = mp3len / wavlen if wavlen>0 else 1
                speed = round(speed, 2)
                set_process(f"dubbing speed {speed} ")
                tmp_mp3 = filename + "-speedup.mp3"
                speed_up_mp3(filename=filename, speed=speed, out=tmp_mp3)
                filename = tmp_mp3

            set_process(f'Listening:{it["text"]}')
            pygameaudio(filename)
            try:
                if os.path.exists(filename):
                    os.unlink(filename)
            except:
                pass
