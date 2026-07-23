import os
import shutil
import time
from pathlib import Path

from videotrans.configure.config import tr, logger
from videotrans.tts import EDGE_TTS, AZURE_TTS
from videotrans.util.help_ffmpeg import get_video_duration, runffmpeg
from videotrans.util.help_misc import vail_file, is_novoice_mp4
from videotrans.util.help_srt import ms_to_time_string, delete_punc


class AlignMixin:

    def align(self) -> None:
        _st=time.time()
        if self._exit() or self.cfg.app_mode == 'tiqu' or not self.should_dubbing or self.ignore_align:
            return

        self.signal(text=tr('duiqicaozuo'))
        self.precent += 3
        if self.cfg.voice_autorate or self.cfg.video_autorate:
            self.signal(text=tr("Sound & video speed alignment stage"))

        if self.cfg.video_autorate:
            is_novoice_mp4(self.cfg.novoice_mp4, self.uuid)
        if vail_file(self.cfg.novoice_mp4):
            self.video_time = get_video_duration(self.cfg.novoice_mp4)
        from videotrans.task._rate import SpeedRate
        print(f'{self.cfg.voice_autorate=},{self.cfg.video_autorate=}')
        rate_inst = SpeedRate(
            queue_tts=self.queue_tts,
            uuid=self.uuid,
            should_audiorate=self.cfg.voice_autorate,
            should_videorate=self.cfg.video_autorate if not self.is_audio_trans else False,
            novoice_mp4=self.cfg.novoice_mp4 if not self.is_audio_trans else None,
            raw_total_time=self.video_time,
            target_audio=self.cfg.target_wav,
            cache_folder=self.cfg.cache_folder,
            align_sub_audio=self.cfg.align_sub_audio and not self.cfg.voice_autorate and not self.cfg.video_autorate,
            remove_silent_mid=self.cfg.remove_silent_mid
        )
        self.queue_tts = rate_inst.run()

        if vail_file(self.cfg.novoice_mp4):
            self.video_time = get_video_duration(self.cfg.novoice_mp4)
        
        # 变速后更新字幕
        if self.cfg.voice_autorate or self.cfg.video_autorate or self.cfg.align_sub_audio:
            srt = ""
            for (idx, it) in enumerate(self.queue_tts):
                startraw = ms_to_time_string(ms=it['start_time'])
                endraw = ms_to_time_string(ms=it['end_time'])
                if self.cfg.fix_punc==2:
                    it['text']=delete_punc(it['text'])
                srt += f"{idx + 1}\n{startraw} --> {endraw}\n{it['text'].strip('...')}\n\n"
            with  Path(self.cfg.target_sub).open('w', encoding="utf-8") as f:
                f.write(srt.strip())

        if self.cfg.tts_type not in [EDGE_TTS, AZURE_TTS] and self.cfg.volume != '+0%' and vail_file(
                self.cfg.target_wav):
            volume = self.cfg.volume.replace('%', '').strip()
            try:
                volume = 1 + float(volume) / 100
                if volume != 1.0:
                    tmp_name = self.cfg.cache_folder + f'/volume-{volume}-{Path(self.cfg.target_wav).name}'
                    runffmpeg(['-y', '-i', os.path.basename(self.cfg.target_wav), '-af', f"volume={volume}",
                                     os.path.basename(tmp_name)], cmd_dir=self.cfg.cache_folder)
                    shutil.copy2(tmp_name, self.cfg.target_wav)
            except Exception as e:
                logger.exception(f'配音后调节音量失败，静默跳过 {e}', exc_info=True)

        self.signal(text=tr('Alignment phase complete, awaiting the next step'))
        logger.debug(f'[声画字幕对齐阶段结束耗时]:{time.time()-_st}s')
