import copy
import re
import sys

from pathlib import Path
from typing import Union

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor

from videotrans import recognition
from videotrans.component.progressbar import ClickableProgressBar
from videotrans.configure.config import tr, settings, app_cfg
from videotrans.task.taskcfg import InputFile, SignMsg
from videotrans.util.help_misc import show_error, shutdown_system


class WinActionTaskMixin:

    def create_btns(self):
        from videotrans.util.help_ffmpeg import format_video
        self.main.show_tips.show()
        self.main.show_tips.setText(tr('Creating progress bar, please wait'))
        target_dir = (Path(
            self.queue_mp4[0]).parent / '_video_out').as_posix() if not self.main.target_dir else self.main.target_dir
        self.obj_list = []

        forbid_names = []
        for video_path in self.queue_mp4:
            obj: InputFile = format_video(video_path, target_dir)
            if sys.platform == "win32" and re.search(r'[?:<>*|/"]', obj['basename']):
                forbid_names.append(obj['basename'])
                continue
            self.obj_list.append(obj)

        if forbid_names:
            self.update_status("stop")
            show_error(tr('win-forbid-name', '?:<>*|/"') + "\n" + ("\n".join(forbid_names)))
            return

        txt = self.main.subtitle_area.toPlainText().strip()
        self.cfg.update(
            {'subtitles': txt, 'app_mode': self.main.app_mode}
        )
        cfg = copy.deepcopy(self.cfg)

        for obj in self.obj_list:
            self.add_process_btn(
                target_dir=Path(obj['target_dir']).as_posix() if cfg.get('app_mode') == 'tiqu' or not cfg.get(
                    'only_out_mp4') else target_dir,
                name=obj['name'],
                uuid=obj['uuid'])
            self.uuid_queue_mp4[obj['uuid']] = (obj['name'], target_dir)
        self.main.show_tips.setText('')
        if self.main.app_mode not in ['tiqu'] and len(self.obj_list) == 1:
            from videotrans.task.only_one import Worker
            task = Worker(
                parent=self.main,
                file=self.obj_list[0],
                cfg=cfg
            )
            task.uito.connect(self.update_data)
            task.start()
            return

        from videotrans.task.mult_video import MultVideo
        task = MultVideo(parent=self.main, cfg=cfg, input_file_list=self.obj_list)
        task.start()

    def retry(self):
        if not self.retry_queue_mp4:
            self.main.retrybtn.setVisible(False)
            return
        from videotrans.util.help_ffmpeg import format_video
        self._disabled_button(True)
        self.main.retrybtn.setVisible(False)
        self.main.subtitle_area.setReadOnly(True)
        self.delete_process()
        self.update_status('ing')
        self.obj_list = []

        cfg = copy.deepcopy(self.cfg)
        for v in self.retry_queue_mp4:
            obj: InputFile = format_video(v.get('name'), v.get('target_dir'))
            app_cfg.rm_uuid(obj['uuid'])
            self.obj_list.append(obj)
            self.add_process_btn(
                target_dir=Path(obj['target_dir']).as_posix() if cfg.get('app_mode') == 'tiqu' or not cfg.get(
                    'only_out_mp4') else v.get('target_dir'),
                name=obj['name'],
                uuid=obj['uuid'])

        cfg['clear_cache'] = False
        from videotrans.task.mult_video import MultVideo
        task = MultVideo(parent=self.main, cfg=cfg, input_file_list=self.obj_list)
        task.start()
        self.main.startbtn.setDisabled(False)
        self.retry_queue_mp4 = []

    def add_process_btn(self, *, target_dir: str = None, name: str = None, uuid=None):

        clickable_progress_bar = ClickableProgressBar(self)
        clickable_progress_bar.progress_bar.setValue(0)
        clickable_progress_bar.setText(tr("waitforstart"))
        clickable_progress_bar.setMinimumSize(500, 50)
        clickable_progress_bar.setToolTip(tr('mubiao'))
        if self.cfg.get('app_mode') == 'tiqu' and self.cfg.get('copysrt_rawvideo'):
            target_dir = Path(name).parent.as_posix()

        clickable_progress_bar.setTarget(
            target_dir=target_dir,
            name=name
        )
        clickable_progress_bar.setCursor(Qt.PointingHandCursor)
        self.main.processlayout.addWidget(clickable_progress_bar)
        if uuid:
            self.processbtns[uuid] = clickable_progress_bar

    def set_process_btn_text(self, d):
        text, uuid, _type = d['text'], d.get('uuid', ''), d.get('type', 'logs')
        if not uuid or uuid not in self.processbtns:
            return
        if _type == 'set_precent' and self.processbtns[uuid].precent < 100:
            t, precent = text.split('???')
            precent = int(float(precent) * 100) / 100
            self.processbtns[uuid].setPrecent(precent)
            self.processbtns[uuid].setText(f'{t}')
        elif _type == 'logs' and self.processbtns[uuid].precent < 100:
            self.processbtns[uuid].setText(text)
        elif _type == 'succeed':
            self.processbtns[uuid].setEnd()
            if self.processbtns[uuid].name in self.queue_mp4:
                self.queue_mp4.remove(self.processbtns[uuid].name)
        elif _type == 'error':
            self.processbtns[uuid].setError(text)
            self.processbtns[uuid].progress_bar.setStyleSheet('color:#ff0000')
            self.processbtns[uuid].setCursor(Qt.PointingHandCursor)

    def update_status(self, type):
        if self.had_click_btn: return
        self.had_click_btn = True
        app_cfg.current_status = type
        if type == 'ing':
            self.disabled_widget(True)
            self.main.startbtn.setText(tr("starting..."))
            self.had_click_btn = False
            return
        self.main.subtitle_area.clear()
        self.main.startbtn.setText(tr(type))

        self.disabled_widget(False)
        self._disabled_button(False)
        for it in self.obj_list:
            app_cfg.stoped_uuid_set.add(it['uuid'])

        if type == 'end':
            self.main.subtitle_area.clear()
            for prb in self.processbtns.values():
                prb.setEnd()
            if self.main.shutdown.isChecked():
                try:
                    shutdown_system()
                except Exception as e:
                    show_error(tr('shutdownerror') + str(e))
        else:
            app_cfg.set_countdown(-1)
            self.set_djs_timeout()
            for it in self.obj_list:
                if it['uuid'] in self.processbtns:
                    self.processbtns[it['uuid']].setPause()

        if self.main.app_mode == 'tiqu':
            self.set_tiquzimu()
        self._reset()
        self.had_click_btn = False

    def update_data(self, uuid: Union[str, None] = "", d: Union[SignMsg, None] = None):
        if uuid and uuid not in [it['uuid'] for it in self.obj_list]:
            return

        if d['type'] == 'ffmpeg':
            self.main.startbtn.setText(d['text'])
            self.main.startbtn.setDisabled(True)
            self.main.startbtn.setStyleSheet("""color:#ff0000""")
            return
        if d['type'] == 'refreshtts':
            currentIndex = self.main.tts_type.currentIndex()
            if currentIndex > 0:
                self.main.tts_type.setCurrentIndex(0)
                QTimer.singleShot(100, lambda: self.main.tts_type.setCurrentIndex(currentIndex))
            return
        if d['type'] == 'refreshmodel_list' and self.main.recogn_type.currentIndex() in [recognition.FASTER_WHISPER,
                                                                                         recognition.Faster_Whisper_XXL,
                                                                                         recognition.Whisper_CPP]:
            current_model_name = self.main.model_name.currentText()
            self.main.model_name.clear()
            self.main.model_name.addItems(
                settings.Whisper_CPP_MODEL_LIST if self.main.recogn_type.currentIndex() == recognition.Whisper_CPP else settings.WHISPER_MODEL_LIST)
            self.main.model_name.setCurrentText(current_model_name)
            return
        if d['type'] == 'shitingerror':
            show_error(d['text'])
            return

        if d['type'] in ['logs', 'error', 'succeed', 'set_precent']:
            self.set_process_btn_text(d)
            if uuid and d['type'] in ['error', 'succeed']:
                app_cfg.stoped_uuid_set.add(d['uuid'])
                self._check_all_done()

            if not uuid or d['type'] != 'error': return
            vdata = self.uuid_queue_mp4.get(uuid)
            if not vdata: return
            self.retry_queue_mp4.append(InputFile(name=vdata[0], target_dir=vdata[1]))
            return

        if d['type'] == 'end':
            self.update_status('end')
            self.main.retrybtn.setVisible(True if self.retry_queue_mp4 else False)
            return

        if d['type'] == 'edit_dubbing':
            from videotrans.component.onlyone_set_editdubb import EditDubbingResultDialog

            cache_folder, language = d['text'].split('<|>')
            dialog = EditDubbingResultDialog(
                novoice_mp4=app_cfg.onlyone_novoice_mp4,
                language=language,
                cache_folder=cache_folder,
                parent=self.main

            )
            if dialog.exec():
                self.set_djs_timeout()
            else:
                self.update_status('stop')
            return
        if d['type'] == 'edit_subtitle_source':
            from videotrans.component.onlyone_set_recogn import EditRecognResultDialog

            dialog = EditRecognResultDialog(
                source_sub=app_cfg.onlyone_source_sub,
                source_wav=app_cfg.onlyone_source_wav,
                novoice_mp4=app_cfg.onlyone_novoice_mp4,
                parent=self.main
            )

            if dialog.exec():
                self.set_djs_timeout()
            else:
                self.update_status('stop')
            dialog=None
            return
        if d['type'] == 'edit_recogn2_subtitle':
            from videotrans.component.onlyone_set_recogn2 import EditRecognResultDialog2

            dialog = EditRecognResultDialog2(
                target_sub=app_cfg.onlyone_target_sub, #二次识别后的字幕
                target_wav=app_cfg.onlyone_target_wav,#用于二次识别的完整音频，需要和 novoice_mp4 同步播放
                novoice_mp4=app_cfg.onlyone_novoice_mp4,# 处理后的无声视频，需要和 target_wav 同步播放
                parent=self.main
            )

            if dialog.exec():
                self.set_djs_timeout()
            else:
                self.update_status('stop')
            return
        if d['type'] == 'edit_subtitle_target':
            from videotrans.component.onlyone_set_role import SpeakerAssignmentDialog
            cache_folder, target_language, tts_type = d['text'].split('<|>')
            dialog = SpeakerAssignmentDialog(
                source_sub=None if not app_cfg.onlyone_trans else app_cfg.onlyone_source_sub,
                target_sub=app_cfg.onlyone_target_sub,
                target_language=target_language,
                source_wav=app_cfg.onlyone_source_wav,
                novoice_mp4=app_cfg.onlyone_novoice_mp4,
                all_voices=self.main.current_rolelist,
                cache_folder=cache_folder,
                tts_type=int(tts_type),
                parent=self.main
            )
            if dialog.exec():
                self.set_djs_timeout()
            else:
                self.update_status('stop')
            return
        if d['type'] == "subtitle" and app_cfg.current_status == 'ing':
            self.main.subtitle_area.moveCursor(QTextCursor.End)
            self.main.subtitle_area.insertPlainText(d['text'])
            return
        if d['type'] == 'replace_subtitle':
            self.main.subtitle_area.clear()
            self.main.subtitle_area.insertPlainText(d['text'])
            return
        if d['type'] == 'proxy_error':
            show_error(f"{tr('Proxy')}: {d['text']}\n{tr('The network proxy address you fill in seems to be incorrect')}")

    def _check_all_done(self):
        active = [obj for obj in self.obj_list if obj['uuid'] not in app_cfg.stoped_uuid_set]
        if not active:
            self.update_status('end')
            self.main.retrybtn.setVisible(bool(self.retry_queue_mp4))
