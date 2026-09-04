from pathlib import Path

from videotrans import translator, recognition, tts
from videotrans.configure import contants
from videotrans.configure.config import tr, settings, app_cfg
from videotrans.recognition import ALLOW_CHANGE_MODEL, get_model_by_type
from videotrans.util.help_misc import show_error
from videotrans.util.help_role import role_menu


class WinActionConfigMixin:

    @staticmethod
    def show_xxl_select():
        import sys
        if sys.platform != 'win32':
            show_error(
                tr("faster-whisper-xxl.exe is only available on Windows"))
            return False
        xxl_path = settings.get('Faster_Whisper_XXL', '')
        if not xxl_path or not Path(xxl_path).exists():
            from videotrans.component.set_xxl import SetFasterXXL
            dialog = SetFasterXXL()
            if dialog.exec():
                xxl_path = dialog.get_values()
                if xxl_path and Path(xxl_path).is_file():
                    return True
            show_error(
                tr("Must be selected, otherwise it cannot be used"))
            return False
        return True

    def recogn_type_change(self):
        recogn_type = self.main.recogn_type.currentIndex()
        if recogn_type == recognition.Faster_Whisper_XXL and not self.show_xxl_select():
            return

        if recogn_type not in ALLOW_CHANGE_MODEL:

            self.main.model_name.setDisabled(True)
            self.main.model_name_help.setDisabled(True)
        else:
            self.main.model_name_help.setDisabled(False)
            self.main.model_name.setDisabled(False)
            self.main.model_name.clear()
            self.main.model_name.addItems(get_model_by_type(recogn_type))

        lang = translator.get_code(show_text=self.main.source_language.currentText())

        is_allow_lang = recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type,
                                                  model_name=self.main.model_name.currentText())
        
        self.main.show_tips.setText(str(is_allow_lang) if is_allow_lang is not True else '')

        if recognition.is_input_api(recogn_type=recogn_type) is not True:
            return

    def model_type_change(self):
        lang = translator.get_code(show_text=self.main.source_language.currentText())
        recogn_type = self.main.recogn_type.currentIndex()
        is_allow_lang = recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type,
                                                  model_name=self.main.model_name.currentText())
        self.main.show_tips.setText(str(is_allow_lang) if is_allow_lang is not True else '')

    def tts_type_change(self, type):

        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if lang and lang != '-':
            is_allow_lang = tts.is_allow_lang(langcode=lang, tts_type=type)            
            self.main.show_tips.setText(str(is_allow_lang) if is_allow_lang is not True else '')

        app_cfg.line_roles = {}
        _role_list = role_menu(type, lang if lang and lang != '-' else None)
        self.main.voice_role.clear()
        self.main.current_rolelist = _role_list
        self.main.voice_role.addItems(self.main.current_rolelist)
        if tts.is_input_api(tts_type=type) is not True:
            return

    def set_voice_role(self, t):
        role = self.main.voice_role.currentText()
        code = translator.get_code(show_text=t)
        if code and code not in ['-','No']:
            _tips=""
            is_allow_lang = tts.is_allow_lang(langcode=code, tts_type=self.main.tts_type.currentIndex())
            if is_allow_lang is not True:
                _tips+=f'{is_allow_lang} '

            rs=translator.is_allow_translate(translate_type=self.main.translate_type.currentIndex(),
                                             show_target=t)
            if rs is not True:
                _tips+=rs
            self.main.show_tips.setText(_tips)

        if self.main.tts_type.currentIndex() not in tts.CHANGE_BY_LANGUAGE:
            if role != 'No' and self.main.app_mode in ['biaozhun']:
                self.main.listen_btn.show()
                self.main.listen_btn.setDisabled(False)
            else:
                self.main.listen_btn.hide()
            return

        self.main.voice_role.clear()
        if t == '-' or not code:
            self.main.voice_role.addItems(['No'])
            return

        _role_list = role_menu(self.main.tts_type.currentIndex(), code.split('-')[0])
        self.main.current_rolelist = _role_list
        self.main.voice_role.addItems(_role_list)
