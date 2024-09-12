from videotrans.configure import config


class LogExcept(Exception):

    def __init__(self, msg):
        super().__init__(msg)
        config.logger.error(msg, exc_info=True)
