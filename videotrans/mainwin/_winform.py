class WinformMixin:

    def open_winform(self, name):
        from videotrans.configure.config import app_cfg
        from videotrans.util.help_misc import show_refaudio_win

        if name == 'set_ass':
            from videotrans.component.set_ass import ASSStyleDialog
            dialog = ASSStyleDialog()
            dialog.exec()
            return
        if name == 'refaudio':
            show_refaudio_win()
            return
        if name == 'xxl':
            from videotrans.component.set_xxl import SetFasterXXL
            dialog = SetFasterXXL()
            dialog.exec()
            return

        if name == 'cpp':
            from videotrans.component.set_cpp import SetWhisperCPP
            dialog = SetWhisperCPP()
            dialog.exec()
            return

        winobj = app_cfg.child_forms.get(name)
        if winobj:
            if hasattr(winobj, 'update_ui'):
                winobj.update_ui()

            winobj.show()
            winobj.activateWindow()
            return

        if name == 'clipvideo':
            from videotrans.component.clip_video import ClipVideoWindow
            window = ClipVideoWindow()
            app_cfg.child_forms[name] = window
            window.show()
            return
        if name == 'textmatching':
            from videotrans.component.textmatching import TextmatchingWindow
            window = TextmatchingWindow()
            app_cfg.child_forms[name] = window
            window.show()
            return
        if name == 'realtime_stt':
            from videotrans.component.realtime_stt import RealTimeWindow
            window = RealTimeWindow()
            app_cfg.child_forms[name] = window
            window.show()
            return
        if name == 'format_srtfiles_folders':
            from videotrans.component.format_srtfiles_folders import FormatSrtFilesFolders
            window = FormatSrtFilesFolders()
            app_cfg.child_forms[name] = window
            window.show()
            return
        from videotrans import winform
        return winform.get_win(name).openwin()
