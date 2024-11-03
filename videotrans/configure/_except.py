from videotrans.configure import config


class LogExcept(Exception):

    def __init__(self, msg):
        super().__init__(msg)
        config.logger.error(msg, exc_info=True)

class IPLimitExceeded(Exception):

    def __init__(self, proxy=None,msg='',name=""):
        super().__init__(msg)
        config.logger.error(msg)
        self.proxy=proxy
        self.msg=msg
        self.name=name
    def __str__(self):
        if self.proxy and (self.proxy.startswith('http') or self.proxy.startswith('sock')):
            return f'[{self.name}]: {self.msg}. 当前代理地址:{self.proxy}, 请更换代理' if config.defaulelang=='zh' else f'{self.msg} Current proxy address {self.proxy} cannot be connected, please replace or try to turn off the proxy'
        return f'[{self.name}]: {self.msg} 无法连接，请使用代理' if config.defaulelang=='zh' else f'{self.msg} Current IP is restricted or cannot be connected, please use proxy'

