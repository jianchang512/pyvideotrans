from videotrans.configure import config


class LogExcept(Exception):

    def __init__(self, msg):
        super().__init__(msg)
        config.logger.error(msg, exc_info=True)

class IPLimitExceeded(Exception):

    def __init__(self, proxy=None,msg=''):
        super().__init__(msg)
        config.logger.error(msg)
        self.proxy=proxy if proxy else '-'
        self.msg=msg
    def __str__(self):
        return f'{self.msg} 当前IP受限或无法连接，请使用或更换代理地址，当前代理地址:{self.proxy}' if config.defaulelang=='zh' else f'IP is limited or cannot connect, please use or change the proxy address, current proxy address:{self.proxy}.{self.msg}'