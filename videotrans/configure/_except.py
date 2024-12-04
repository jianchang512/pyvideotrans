from videotrans.configure import config


class LogExcept(Exception):

    def __init__(self, msg):
        super().__init__(msg)
        config.logger.error(msg, exc_info=True)

class IPLimitExceeded(Exception):

    def __init__(self, msg='',name=""):
        super().__init__(msg)
        config.logger.error(msg)
        self.msg=msg
        self.name=name
    def __str__(self):
        return f'[{self.name}]: 连接服务失败 {self.msg} ' if config.defaulelang=='zh' else f'Cannot be connected {self.msg} '

