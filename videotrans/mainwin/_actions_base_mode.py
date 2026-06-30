import platform

from videotrans.configure.config import tr, defaulelang


class WinActionBaseModeMixin:

    def set_biaozhun(self):
        self.main.action_biaozhun.setChecked(True)
        self.main.splitter.setSizes([self.main.width - 300, 300])
        self.main.app_mode = 'biaozhun'
        self.main.show_tips.setText(
            tr("Customize each configuration to batch video translation. When selecting a single video, you can pause to edit subtitles during processing."))
        self.main.startbtn.setText(tr('kaishichuli'))
        self.main.action_tiquzimu.setChecked(False)

        self.main.copysrt_rawvideo.hide()

        self.main.label_9.show()
        self.main.recogn2pass.show()
        self.main.translate_type.show()
        self.main.label_2.show()
        self.main.source_language.show()
        self.main.label_3.show()
        self.main.target_language.show()
        self.main.label.show()
        if defaulelang == 'zh':
            self.main.proxy.show()

        self.main.tts_text.show()
        self.main.tts_type.show()
        self.main.tts_type.setDisabled(False)
        self.main.label_4.show()
        self.main.voice_role.show()
        self.main.listen_btn.show()
        self.main.volume_label.show()
        self.main.volume_rate.show()
        self.main.volume_rate.setDisabled(False)
        self.main.pitch_label.show()
        self.main.pitch_rate.show()
        self.main.pitch_rate.setDisabled(False)

        self.main.reglabel.show()
        self.main.only_out_mp4.show()
        self.main.recogn_type.show()
        self.main.model_name_help.show()
        self.main.model_name.show()
        self.main.subtitle_type.setCurrentIndex(1)
        self.main.subtitle_type.show()
        self.main.rephrase.show()

        self.main.align_btn.show()
        self.main.voice_rate.show()
        self.main.label_6.show()
        self.main.voice_autorate.show()
        self.main.video_autorate.show()

        self.main.output_srt_label.hide()
        self.main.output_srt.hide()
        if platform.system() != 'Darwin':
            self.main.enable_cuda.show()

        if not self.main.voice_autorate.isChecked() and not self.main.video_autorate.isChecked():
            self.main.remove_silent_mid.setVisible(True)
            self.main.align_sub_audio.setVisible(True)
        else:
            self.main.remove_silent_mid.setVisible(False)
            self.main.align_sub_audio.setVisible(False)

        self.show_adv_status = True
        self.toggle_adv()

    def set_tiquzimu(self):
        self.main.action_tiquzimu.setChecked(True)
        self.main.splitter.setSizes([self.main.width - 300, 300])
        self.main.app_mode = 'tiqu'
        self.main.show_tips.setText(tr('tiquzimu'))
        self.main.startbtn.setText(tr('kaishitiquhefanyi'))
        self.main.action_biaozhun.setChecked(False)

        self.main.copysrt_rawvideo.show()

        self.main.label_9.show()
        self.main.translate_type.show()
        self.main.label_2.show()
        self.main.source_language.show()
        self.main.label_3.show()
        self.main.target_language.show()
        self.main.label.show()
        if defaulelang == 'zh':
            self.main.proxy.show()

        self.main.recogn2pass.hide()
        self.main.only_out_mp4.hide()
        self.main.tts_text.hide()
        self.main.tts_type.hide()
        self.main.label_4.hide()
        self.main.voice_role.hide()
        self.main.listen_btn.hide()
        self.main.volume_label.hide()
        self.main.volume_rate.hide()
        self.main.pitch_label.hide()
        self.main.pitch_rate.hide()

        self.main.reglabel.show()
        self.main.recogn_type.show()
        self.main.model_name_help.show()
        self.main.model_name.show()
        self.main.subtitle_type.setCurrentIndex(1)
        self.main.subtitle_type.hide()
        self.main.rephrase.show()

        self.main.align_btn.hide()
        self.main.label_6.hide()
        self.main.voice_rate.hide()
        self.main.voice_autorate.hide()
        self.main.video_autorate.hide()
        self.main.output_srt.show()
        self.main.output_srt_label.show()

        self.main.remove_silent_mid.hide()
        self.main.align_sub_audio.hide()
        if platform.system() != 'Darwin':
            self.main.enable_cuda.show()

        self.show_adv_status = True
        self.toggle_adv()

    def toggle_adv(self):
        self.show_adv_status = not self.show_adv_status
        self.hide_show_element(self.main.bgm_layout, self.show_adv_status)
        self.hide_show_element(self.main.dubb_thread_layout, self.show_adv_status)
        self.main.advcontainer.setVisible(self.show_adv_status)

    def hide_show_element(self, wrap_layout, show_status):
        def hide_recursive(layout, show_status):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    if not show_status:
                        item.widget().hide()
                    else:
                        item.widget().show()
                elif item.layout():
                    hide_recursive(item.layout(), show_status)

        hide_recursive(wrap_layout, show_status)

    def set_mode(self):
        subtitle_type = self.main.subtitle_type.currentIndex()
        voice_role = self.main.voice_role.currentText()
        self.cfg['copysrt_rawvideo'] = False
        if self.main.app_mode == 'tiqu' or (subtitle_type < 1 and voice_role in ('No', '', " ")):
            self.main.app_mode = 'tiqu'
            self.cfg['subtitle_type'] = 0
            self.cfg['voice_role'] = 'No'
            self.cfg['voice_rate'] = '+0%'
            self.cfg['voice_autorate'] = False
            self.cfg['copysrt_rawvideo'] = self.main.copysrt_rawvideo.isChecked()

    def _disabled_button(self, disabled=True):
        for k, v in self.main.moshi.items():
            if k != self.main.app_mode:
                v.setDisabled(disabled)
                v.setChecked(False)
            else:
                v.setDisabled(False)
                v.setChecked(True)

    def disabled_widget(self, type):
        self.main.clear_cache.setDisabled(type)
        self.main.volume_rate.setDisabled(type)
        self.main.pitch_rate.setDisabled(type)
        self.main.only_out_mp4.setDisabled(type)
        self.main.recogn2pass.setDisabled(type)
        self.main.import_sub.setDisabled(type)
        self.main.btn_get_video.setDisabled(type)
        self.main.btn_save_dir.setDisabled(type)
        self.main.translate_type.setDisabled(type)
        self.main.proxy.setDisabled(type)
        self.main.source_language.setDisabled(type)
        self.main.target_language.setDisabled(type)
        self.main.tts_type.setDisabled(type)
        self.main.model_name.setDisabled(type)
        self.main.subtitle_type.setDisabled(type)
        self.main.enable_cuda.setDisabled(type)
        self.main.recogn_type.setDisabled(type)
        self.main.voice_autorate.setDisabled(type)
        self.main.video_autorate.setDisabled(type)
        self.main.voice_role.setDisabled(type)
        self.main.voice_rate.setDisabled(type)
        self.main.is_loop_bgm.setDisabled(type)
        self.main.aisendsrt.setDisabled(type)
        self.main.rephrase.setDisabled(type)
        self.main.remove_silent_mid.setDisabled(type)
        self.main.align_sub_audio.setDisabled(type)
        self.main.remove_noise.setDisabled(type)
        self.main.output_srt.setDisabled(type)

        self.main.bgmvolume.setDisabled(type)
        self.main.fix_punc.setDisabled(type)
        self.main.enable_diariz.setDisabled(type)
        self.main.nums_diariz.setDisabled(type)

        self.main.set_adv_status.setDisabled(type)
        self.main.select_file_type.setDisabled(type)
        self.main.is_separate.setDisabled(type)
        self.main.embed_bgm.setDisabled(type)
        self.main.addbackbtn.setDisabled(True if self.main.app_mode in ['tiqu'] else type)
        self.main.back_audio.setReadOnly(True if self.main.app_mode in ['tiqu'] else type)
