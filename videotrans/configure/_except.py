from videotrans.configure import config


class LogExcept(BaseException):

    def __init__(self, msg):
        super().__init__(msg)
        config.logger.error(msg, exc_info=True)

class IPLimitExceeded(BaseException):

    def __init__(self, msg='',name=""):
        super().__init__(msg)
        config.logger.error(msg)
        self.msg=msg
        self.name=name
    def __str__(self):
        return f'[{self.name}]: {self.msg} 连接服务失败' if config.defaulelang=='zh' else f'{self.msg} Current IP is restricted or cannot be connected'

