from pathlib import Path
import asyncio
import sys
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from PySide6.QtCore import QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow
from videotrans.configure import config
config.init_run()
from videotrans.configure.config import tr, params, settings, app_cfg, logger, ROOT_DIR
from videotrans import VERSION
from videotrans.util.checkgpu import AiLoaderThread
from videotrans.ui.en import Ui_MainWindow
from videotrans.task.simple_runnable_qt import run_in_threadpool

from videotrans.mainwin._bind_signals import BindSignalsMixin
from videotrans.mainwin._winform import WinformMixin
from videotrans.mainwin._lifecycle import LifecycleMixin


class MainWindow(BindSignalsMixin, WinformMixin, LifecycleMixin, QMainWindow, Ui_MainWindow):


    def __init__(self, parent=None, width=1200, height=650,callback=None):
        super().__init__(parent)
        self.callback=callback
        self.resize(width, height)
        self.setupUi(self)
        self.callback("SetupUI end...")

        self.worker_threads = []
        self.width = width
        self.height = height
        self.is_restarting = False
        self.win_action = None
        self.moshi = None
        self.target_dir = None
        self.app_mode = "biaozhun"
        self.current_rolelist = []
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.rawtitle = f"{tr('softname')} {VERSION} {tr('Documents')} pyvideotrans.com"
        self.setWindowTitle(self.rawtitle)

        self.moshi = {
            "biaozhun": self.action_biaozhun,
            "tiqu": self.action_tiquzimu
        }

        s = AiLoaderThread(self)
        s.gpu_io.connect(self._start_workers)
        self.startbtn.setDisabled(True)
        self.startbtn.setText(tr('Checking GPUs...'))
        s.start()
        self._set_default()

    def _set_default(self):
        self.callback('import recognition ...')
        from videotrans import recognition
        self.callback('import tts ...')
        from videotrans import tts
        self.callback('import translate ...')
        from videotrans.translator import TRANSLASTE_NAME_LIST,LANGNAME_DICT,get_code
        self.callback('Get cache  ...')
        self.languagename = list(LANGNAME_DICT.values())
        self.translate_type.addItems(TRANSLASTE_NAME_LIST)
        self.source_language.addItems(self.languagename)
        self.target_language.addItems(["-"] + self.languagename)

        self.tts_type.addItems(tts.TTS_NAME_LIST)
        self.recogn_type.addItems(recognition.RECOGN_NAME_LIST)

        self.subtitle_type.addItems(
            [
                tr('nosubtitle'),
                tr('embedsubtitle'),
                tr('softsubtitle'),
                tr('embedsubtitle2'),
                tr('softsubtitle2')
            ])

        _translate_type = int(params.get('translate_type', 0))
        _tts_type = int(params.get('tts_type', 0))
        _recogn_type = int(params.get('recogn_type', 0))
        _target_language = params.get('target_language')
        _source_language = params.get('source_language')
        _subtitle_type = int(params.get('subtitle_type', 0))
        _output_srt = int(params.get('output_srt', 0))
        _role = params.get('voice_role') or 'No'
        _model_name = params.get('model_name')

        self.translate_type.setCurrentIndex(_translate_type)
        self.tts_type.setCurrentIndex(_tts_type)
        self.recogn_type.setCurrentIndex(_recogn_type)
        self.voice_role.clear()
        self.model_name.clear()
        curr = recognition.get_model_by_type(_recogn_type)
        self.model_name.addItems(curr)
        if _model_name in curr:
            self.model_name.setCurrentText(_model_name)
        self.model_name.setDisabled(True if _recogn_type not in recognition.ALLOW_CHANGE_MODEL else False)

        if _source_language and _source_language in self.languagename:
            self.source_language.setCurrentText(_source_language)

        self.subtitle_type.setCurrentIndex(_subtitle_type)
        if _subtitle_type > 2:
            self.output_srt.setVisible(True)
            self.output_srt.setCurrentIndex(_output_srt if _output_srt > 0 else 2)

        if params['output_dir'].strip():
            Path(params['output_dir']).mkdir(parents=True, exist_ok=True)
            self.output_dir.setText(tr('Translation results saved to:') + params['output_dir'])
            self.target_dir = params['output_dir']

        from videotrans.util.help_misc import set_proxy
        if not app_cfg.proxy:
            app_cfg.proxy = set_proxy() or ''
            if app_cfg.proxy:
                os.environ['HTTP_PROXY'] = app_cfg.proxy
                os.environ['HTTPS_PROXY'] = app_cfg.proxy
        self.proxy.setText(app_cfg.proxy)
        if not params.get('voice_autorate') and not params.get('video_autorate'):
            self.remove_silent_mid.setVisible(True)
            self.align_sub_audio.setVisible(True)
        self.callback('Set default value ...')
        self.select_file_type.setChecked(bool(params.get('select_file_type', False)))
        self.voice_rate.setValue(int(params.get('voice_rate', '0').replace('%', '')))
        self.volume_rate.setValue(int(params.get('volume', '0').replace('%', '')))
        self.pitch_rate.setValue(int(params.get('pitch', '0').replace('Hz', '')))
        self.voice_autorate.setChecked(bool(params.get('voice_autorate', False)))
        self.video_autorate.setChecked(bool(params.get('video_autorate', False)))
        self.fix_punc.setCurrentIndex(int(params.get('fix_punc', 0)))
        self.recogn2pass.setChecked(bool(params.get('recogn2pass', False)))
        self.only_out_mp4.setChecked(bool(params.get('only_out_mp4', False)))
        self.remove_silent_mid.setChecked(bool(params.get('remove_silent_mid', False)))
        self.align_sub_audio.setChecked(bool(params.get('align_sub_audio', True)))
        self.clear_cache.setChecked(bool(params.get('clear_cache', False)))
        self.enable_cuda.setChecked(bool(params.get('is_cuda', False)))
        self.enable_diariz.setChecked(bool(params.get('enable_diariz', False)))
        self.nums_diariz.setCurrentIndex(int(params.get('nums_diariz', 0)))
        self.is_separate.setChecked(bool(params.get('is_separate', False)))
        self.embed_bgm.setChecked(bool(params.get('embed_bgm', True)))
        self.rephrase.setCurrentIndex(int(params.get('rephrase', 0)))
        self.remove_noise.setChecked(bool(params.get('remove_noise')))
        self.copysrt_rawvideo.setChecked(bool(params.get('copysrt_rawvideo', False)))
        self.bgmvolume.setText(str(settings.get('backaudio_volume', 0.8)))
        self.is_loop_bgm.setCurrentIndex(int(settings.get('loop_backaudio', 0)))

        _langcode = None
        if _target_language and _target_language in self.languagename:
            _langcode = get_code(show_text=_target_language)
        self.callback('import voices list ...')
        from videotrans.util.help_role import role_menu
        self.callback('Set tts voice ...')
        _rolelist = role_menu(_tts_type, _langcode)
        self.voice_role.addItems(_rolelist)
        self.current_rolelist = _rolelist
        logger.debug(f'上次缓存的角色:{_role},字幕嵌入类型:{_subtitle_type},发音语言:{_source_language},目标语言:{_target_language}，目标语言代码:{_langcode},模型:{_model_name},TTS渠道[{_tts_type}]')
        if _langcode:
            self.target_language.setCurrentText(_target_language)
            if _role in _rolelist:
                self.voice_role.setCurrentText(_role)
        self.callback('show main window ...')
        self.show()
        run_in_threadpool(self._daemon)
        self._bind_signal()

    def _daemon(self):
        from videotrans.util.help_ffmpeg import check_hw_on_start
        from videotrans.util.help_misc import check_new_version, is_connect_hf
        check_hw_on_start()
        check_new_version()
        is_connect_hf()

    def _start_workers(self, status):
        if status == 'end':
            from videotrans.task.job import start_thread
            from videotrans.configure.config import tr
            self.worker_threads = start_thread()
            self.startbtn.setDisabled(False)
            self.startbtn.setText(tr("Start"))
        else:
            from videotrans.util.help_misc import show_error
            show_error(status)

    def checkbox_state_changed(self, state):
        if state:
            settings['aisendsrt'] = True
        else:
            settings['aisendsrt'] = False
        settings.save()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.aisendsrt.setChecked(settings.get('aisendsrt'))
