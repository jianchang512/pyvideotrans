import time
from pathlib import Path


class DiarizMixin:

    def diariz(self):
        _st=time.time()
        # 只要 do_diarize 是 False,无论是否选中都不分离说话人
        if self._exit() or not self.should_dubbing or not self.do_diarize or not self.cfg.enable_diariz or self.max_speakers == 1 or Path(
                self.cfg.cache_folder + "/speaker.json").exists():
            return

        self._diariz_common()