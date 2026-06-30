import sys

from pathlib import Path

from videotrans import translator, recognition, tts
from videotrans.configure.config import tr, params, settings, app_cfg
from videotrans.util.help_misc import show_error


class WinActionCheckMixin:

    def set_translate_type(self, idx):
        try:
            t = self.main.target_language.currentText()
            if t not in ['-']:
                rs = translator.is_allow_translate(translate_type=idx, show_target=t)
                if rs is not True:
                    return False
        except Exception as e:
            show_error(str(e))

    def set_subtitle_type(self, idx):
        if idx < 3:
            self.main.output_srt.hide()
        else:
            self.main.output_srt.setCurrentIndex(2)
            self.main.output_srt.show()

    def shound_translate(self):
        if self.main.target_language.currentText() == '-' or self.main.source_language.currentText() == '-':
            return False
        if self.main.target_language.currentText() == self.main.source_language.currentText():
            return False
        return True

    def check_tts(self):
        if tts.is_input_api(tts_type=self.main.tts_type.currentIndex()) is not True:
            return False
        if self.main.target_language.currentText() == '-' and self.main.voice_role.currentText() not in ['No', '', ' ']:
            show_error(tr('wufapeiyin'))
            return False
        return True

    def check_reccogn(self):
        langcode = translator.get_code(show_text=self.main.source_language.currentText())
        recogn_type = self.main.recogn_type.currentIndex()
        model_name = self.main.model_name.currentText()
        res = recognition.is_allow_lang(langcode=langcode, recogn_type=recogn_type, model_name=model_name)
        self.main.show_tips.setText(res if res is not True else '')

        return recognition.is_input_api(recogn_type=recogn_type)

    def check_output(self):
        from PySide6.QtWidgets import QMessageBox
        input_folder = Path(self.queue_mp4[0]).parent
        output_folder = input_folder / '_video_out' if not self.main.target_dir else Path(self.main.target_dir)
        if not output_folder.exists():
            return True

        if self.main.only_out_mp4.isChecked() and input_folder.samefile(output_folder):
            show_error(
                tr("The output directory is not allowed to point to the input directory"))
            return False

        if not self.main.clear_cache.isChecked():
            return True
        for it in self.queue_mp4:
            p = Path(it)
            folder = output_folder / f'{p.stem}-{p.suffix.lower()[1:]}'
            if folder.exists():
                reply = QMessageBox.question(
                    self.main,
                    tr("Are you sure the cleanup has been output?"),
                    tr("If you confirm to clean up, all files in the output directory will be deleted. If you manually specify the output directory, please make sure there are no important files in the directory and back it up in advance to avoid data loss.",
                       folder.as_posix()),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply != QMessageBox.StandardButton.Yes:
                    return False
                return True
        return True

    def check_name_length(self):
        if sys.platform != 'win32':
            return True
        from PySide6.QtWidgets import QMessageBox
        for it in self.queue_mp4:
            _itlen = len(it)
            _namelen = len(Path(it).name)
            if _itlen >= 170 and _namelen >= 90:
                reply = QMessageBox.question(
                    self.main,
                    tr("The filename is too long"),
                    tr("Filename length check", _namelen, _itlen) + f"\n\n{it}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply != QMessageBox.StandardButton.Yes:
                    return False
                return True
        return True

    def check_start(self):
        from videotrans import recognition, translator
        if app_cfg.current_status == 'ing':
            self.update_status('stop')
            return
        self.main.startbtn.setDisabled(True)
        self.cfg = {}
        app_cfg.line_roles = {}
        self.is_render = False
        app_cfg.set_countdown(int(float(settings.get('countdown_sec', 1))))

        if len(self.queue_mp4) < 1:
            show_error(tr("Video file must be selected"))
            self.main.startbtn.setDisabled(False)
            return

        self.cfg['translate_type'] = self.main.translate_type.currentIndex()
        self.cfg['source_language'] = self.main.source_language.currentText()
        self.cfg['target_language'] = self.main.target_language.currentText()
        self.cfg['source_language_code'] = translator.get_code(show_text=self.cfg['source_language'])
        self.cfg['target_language_code'] = translator.get_code(show_text=self.cfg['target_language'])

        self.cfg['clear_cache'] = self.main.clear_cache.isChecked()
        self.cfg['only_out_mp4'] = self.main.only_out_mp4.isChecked()
        self.cfg['fix_punc'] = self.main.fix_punc.currentIndex()

        self.cfg['tts_type'] = self.main.tts_type.currentIndex()
        self.cfg['voice_role'] = self.main.voice_role.currentText()
        try:
            volume = int(self.main.volume_rate.value())
            pitch = int(self.main.pitch_rate.value())
        except (ValueError, TypeError):
            volume = 0
            pitch = 0
        self.cfg['volume'] = f'+{volume}%' if volume >= 0 else f'{volume}%'
        self.cfg['pitch'] = f'+{pitch}Hz' if pitch >= 0 else f'{pitch}Hz'

        self.cfg['recogn_type'] = self.main.recogn_type.currentIndex()
        if self.cfg['recogn_type'] == recognition.Faster_Whisper_XXL and not self.show_xxl_select():
            self.main.startbtn.setDisabled(False)
            return
        self.cfg['model_name'] = self.main.model_name.currentText()
        self.cfg['remove_noise'] = self.main.remove_noise.isChecked()

        self.cfg['subtitle_type'] = self.main.subtitle_type.currentIndex()

        self.cfg['voice_rate'] = self.main.voice_rate.value()
        try:
            voice_rate = int(self.main.voice_rate.value())
        except (TypeError, ValueError):
            voice_rate = 0
        self.cfg['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"{voice_rate}%"
        self.cfg['voice_autorate'] = self.main.voice_autorate.isChecked()
        self.cfg['video_autorate'] = self.main.video_autorate.isChecked()

        self.cfg['is_separate'] = self.main.is_separate.isChecked()
        self.cfg['embed_bgm'] = self.main.embed_bgm.isChecked()
        self.cfg['background_music'] = self.main.back_audio.text().strip()
        self.cfg['enable_diariz'] = self.main.enable_diariz.isChecked()
        self.cfg['recogn2pass'] = self.main.recogn2pass.isChecked()
        self.cfg['nums_diariz'] = self.main.nums_diariz.currentIndex()

        if self.check_reccogn() is not True:
            self.main.startbtn.setDisabled(False)
            return

        if self.shound_translate() and translator.is_allow_translate(
                translate_type=self.cfg['translate_type'],
                show_target=self.cfg['target_language_code']) is not True:
            self.main.startbtn.setDisabled(False)
            return
        txt = self.main.subtitle_area.toPlainText().strip()
        if self.check_txt(txt) is not True:
            self.main.startbtn.setDisabled(False)
            return

        if self.check_tts() is not True:
            self.main.tts_type.setCurrentIndex(0)
            self.main.startbtn.setDisabled(False)
            return

        self.cfg['rephrase'] = self.main.rephrase.currentIndex()
        self.cfg['is_cuda'] = self.main.enable_cuda.isChecked()
        self.cfg['remove_silent_mid'] = False
        self.cfg['align_sub_audio'] = True
        if not self.cfg['voice_autorate'] and not self.cfg['video_autorate']:
            self.cfg['remove_silent_mid'] = self.main.remove_silent_mid.isChecked()
            self.cfg['align_sub_audio'] = self.main.align_sub_audio.isChecked()
        if self.cuda_isok() is not True:
            self.main.startbtn.setDisabled(False)
            return

        if self.main.app_mode == 'biaozhun' and not self.cfg.get('target_language_code') and self.cfg['subtitle_type'] > 0:
            self.main.startbtn.setDisabled(False)
            return show_error(
                tr("Target language must be selected to embed subtitles"))

        if self.check_name() is not True:
            self.main.startbtn.setDisabled(False)
            return

        if self.main.rephrase.currentIndex() == 1:
            ai_type = settings.get('llm_ai_type', 'chatgpt')
            if (ai_type in ['chatgpt', 'openai'] and not params.get('chatgpt_key')) or (ai_type == 'deepseek' and not params.get('deepseek_key')):
                self.main.startbtn.setDisabled(False)
                show_error(tr('llmduanju'))
                from videotrans.winform import get_win
                get_win('deepseek' if ai_type == 'deepseek' else 'chatgpt').openwin()
                return

        if self.check_name_length() is not True:
            self.main.startbtn.setDisabled(False)
            return
        if self.check_output() is not True:
            self.main.startbtn.setDisabled(False)
            return

        self.set_mode()
        self.cfg['app_mode'] = self.main.app_mode
        self.cfg['output_srt'] = self.main.output_srt.currentIndex()

        if self.main.recogn_type.currentIndex() == recognition.FASTER_WHISPER or self.main.app_mode == 'biaozhun':
            self.cfg['loop_backaudio'] = self.main.is_loop_bgm.currentIndex()
            try:
                self.cfg['backaudio_volume'] = float(self.main.bgmvolume.text())
            except (TypeError, ValueError):
                pass

        params.getset_params(self.cfg | {"select_file_type": self.main.select_file_type.isChecked()})
        params.save()

        self.delete_process()

        self.update_status('ing')

        settings['aisendsrt'] = self.main.aisendsrt.isChecked()
        settings.save()

        self._disabled_button(True)
        self.main.subtitle_area.setReadOnly(True)
        self.main.startbtn.setDisabled(False)
        self.retry_queue_mp4 = []
        self.uuid_queue_mp4 = {}
        self.main.retrybtn.setVisible(False)
        self.create_btns()
