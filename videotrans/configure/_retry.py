# -*- coding: utf-8 -*-
from tenacity.stop import stop_base


class stop_after_retry_nums(stop_base):
    """按设置中的重试次数停止重试。每次判断时实时读取设置，修改后无需重启即可生效"""

    def __init__(self, key: str = 'retry_nums'):
        self.key = key

    def __call__(self, retry_state) -> bool:
        from videotrans.configure.config import settings
        try:
            max_attempts = int(float(settings.get(self.key, 1) or 1))
        except (TypeError, ValueError):
            max_attempts = 1
        return retry_state.attempt_number >= max(max_attempts, 1)
