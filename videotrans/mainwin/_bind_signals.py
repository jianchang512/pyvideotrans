from videotrans.winform import get_win


class BindSignalsMixin:

    def _bind_signal(self):
        self.callback('Bind signal...')
        from PySide6.QtCore import QTimer
        from PySide6.QtCore import Qt
        from videotrans.mainwin._actions import WinAction
        from videotrans.configure.signal_hub import SignalHub
        from videotrans.configure.config import settings, params
        from videotrans.util.help_misc import open_url, show_glossary_editor

        self.win_action = WinAction(self)
        self.restart_btn.clicked.connect(self.restart_app)
        self.addbackbtn.clicked.connect(self.win_action.get_background)
        self.voice_autorate.toggled.connect(self.win_action.check_voice_autorate)
        self.video_autorate.toggled.connect(self.win_action.check_video_autorate)
        self.enable_cuda.toggled.connect(self.win_action.check_cuda)
        self.tts_type.currentIndexChanged.connect(self.win_action.tts_type_change)

        self.translate_type.currentIndexChanged.connect(self.win_action.set_translate_type)
        self.subtitle_type.currentIndexChanged.connect(self.win_action.set_subtitle_type)
        self.voice_role.currentTextChanged.connect(self.win_action.show_listen_btn)
        self.target_language.currentTextChanged.connect(self.win_action.set_voice_role)

        self.proxy.textChanged.connect(self.win_action.change_proxy)

        self.startbtn.clicked.connect(self.win_action.check_start)
        self.retrybtn.clicked.connect(self.win_action.retry)
        self.btn_save_dir.clicked.connect(self.win_action.get_save_dir)
        self.set_adv_status.clicked.connect(self.win_action.toggle_adv)
        self.btn_get_video.clicked.connect(self.win_action.get_mp4)
        self.listen_btn.clicked.connect(self.win_action.listen_voice_fun)
        self.recogn_type.currentIndexChanged.connect(self.win_action.recogn_type_change)
        self.model_name.currentIndexChanged.connect(self.win_action.model_type_change)

        self.label.clicked.connect(lambda: open_url(url='https://pyvideotrans.com/proxy'))
        self.glossary.clicked.connect(lambda: show_glossary_editor(self))
        self.action_biaozhun.triggered.connect(self.win_action.set_biaozhun)
        self.action_tiquzimu.triggered.connect(self.win_action.set_tiquzimu)
        self.set_ass.clicked.connect(lambda: get_win('set_ass'))
        self.import_subtitle.clicked.connect(self.win_action.import_srtfile)


        self.aisendsrt.toggled.connect(self.checkbox_state_changed)
        self.rightbottom.clicked.connect(lambda : get_win('info'))
        self.statusLabel.clicked.connect(lambda: open_url('https://pyvideotrans.com'))

        def _setcursor():
            self.callback('set cursor...')
            self.startbtn.setCursor(Qt.PointingHandCursor)
            self.btn_get_video.setCursor(Qt.PointingHandCursor)
            self.btn_save_dir.setCursor(Qt.PointingHandCursor)
            self.listen_btn.setCursor(Qt.PointingHandCursor)
            self.statusLabel.setCursor(Qt.PointingHandCursor)
            self.rightbottom.setCursor(Qt.PointingHandCursor)
            self.restart_btn.setCursor(Qt.PointingHandCursor)

            SignalHub.instance().new_message.connect(self.win_action.update_data)
            if settings.get('show_more_settings'):
                self.win_action.toggle_adv()

            self.win_action.tts_type_change(self.tts_type.currentIndex())
            _role = params.get('voice_role') or 'No'
            if _role in self.current_rolelist:
                self.voice_role.setCurrentText(_role)
            self.callback('end')
        QTimer.singleShot(10,_setcursor)