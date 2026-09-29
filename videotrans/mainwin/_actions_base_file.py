from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer

from videotrans.configure.config import tr, settings, params, app_cfg, ROOT_DIR, TEMP_ROOT
from videotrans.configure import constants
from videotrans.util.help_misc import  set_proxy, set_process


class WinActionBaseFileMixin:

    def get_mp4(self):
        allowed_exts = constants.VIDEO_EXTS + constants.AUDIO_EXITS
        format_str = " ".join(['*.' + f for f in allowed_exts])
        mp4_list = []
        if self.main.select_file_type.isChecked():
            folder_path = QtWidgets.QFileDialog.getExistingDirectory(
                self.main,
                tr('Select folder'),
                params.get('last_opendir', '')
            )

            if not folder_path:
                return
            p = Path(folder_path)
            p_out = p.parent / '_video_out' / p.name

            mp4_list = [
                file.as_posix()
                for file in p.rglob('*')
                if file.is_file() and file.suffix[1:].lower() in allowed_exts
            ]

            params['last_opendir'] = p.as_posix()
            if not self.main.target_dir:
                self.main.target_dir = p_out.as_posix()
        else:
            fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(self.main,
                                                                tr("Select one or more files"),
                                                                params.get('last_opendir', ''),
                                                                f'Files({format_str})')
            if len(fnames) < 1:
                return
            for (i, it) in enumerate(fnames):
                mp4_list.append(Path(it).as_posix())
            params['last_opendir'] = Path(mp4_list[0]).parent.resolve().as_posix()

        if len(mp4_list) > 0:
            self.main.source_mp4.setText(f'{len(mp4_list)} videos')
            self.queue_mp4 = mp4_list

    def get_save_dir(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self.main, tr('selectsavedir'),'')
        if dirname:            
            dirname = Path(dirname).resolve().as_posix()
            self.main.target_dir = dirname
            self.main.output_dir.setText(tr('Translation results saved to:') + dirname)
        else:
            self.main.target_dir = None
            self.main.output_dir.setText('')
        
        self.main.btn_save_dir.setToolTip(dirname)
        params['output_dir'] = dirname
        params.save()

    def get_background(self):
        format_str = " ".join(['*.' + f for f in constants.AUDIO_EXITS])
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self.main, 'Background music', params.get('last_opendir', ''),
                                                          f"Audio files({format_str})")
        if not fname:
            return
        fname = Path(fname).as_posix()
        self.main.back_audio.setText(fname)

    def change_proxy(self, p):
        proxy = p.strip()
        if not proxy:
            settings['proxy'] = ''
            app_cfg.proxy = ''
            set_proxy('del')
        else:
            settings['proxy'] = proxy
            set_proxy(proxy)
            app_cfg.proxy = proxy
            self._proxy_test_version += 1
            current_version = self._proxy_test_version
            current_proxy = proxy
            QTimer.singleShot(10000, lambda v=current_version, p=current_proxy: self._test_proxy(v, p))
        settings.save()

    def _test_proxy(self, test_version, test_proxy):
        import requests,threading
        if not test_proxy or test_version != self._proxy_test_version:
            return
        def _curl():
            try:
                requests.head(test_proxy, timeout=8)
            except Exception:
                if test_version != self._proxy_test_version:
                    return
                if self.main.proxy.text().strip()==test_proxy:
                    set_process(text=test_proxy, type="proxy_error")
        threading.Thread(target=_curl).start()

    def import_srtfile(self,srt_type='spoken'):
        _title=tr('Import spoken SRT') if srt_type=='spoken' else tr('Import target language SRT')
        
        fname,_ = QtWidgets.QFileDialog.getOpenFileName(self.main,
                                                                _title,
                                                                params.get('last_opendir', ''),
                                                                f'Files(*.srt)')
        
        if srt_type=='spoken':
            app_cfg.onlyone_importsrtfile=fname if fname else None        
        else:
            app_cfg.onlyone_importsrtfile_target=fname if fname else None        
        
        
        self.main.subtitle_area.clear()
        _content=""
        if app_cfg.onlyone_importsrtfile:
            _content+=f'\n[{tr("Import spoken SRT")}]\n'+Path(app_cfg.onlyone_importsrtfile).read_text(encoding='utf-8')
        if app_cfg.onlyone_importsrtfile_target:
            _content+=f'\n[{tr("Import target language SRT")}]\n'+Path(app_cfg.onlyone_importsrtfile_target).read_text(encoding='utf-8')
        if _content:
            self.main.subtitle_area.insertPlainText(_content)
        
            
