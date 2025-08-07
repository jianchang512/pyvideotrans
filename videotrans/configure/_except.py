from videotrans.configure import config
from requests.exceptions import TooManyRedirects, MissingSchema, InvalidSchema, InvalidURL, ProxyError, SSLError,Timeout,ConnectionError
from openai import AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError,RateLimitError,APIConnectionError,APIError

from elevenlabs.core import ApiError as ApiError_11

class RetryRaise:
    # 定义一个类属性，属于这些异常的是永久性错误，无法通过重试恢复，直接不重试
    # retry=retry_if_not_exception_type(RetryRaise.),
    NO_RETRY_EXCEPT = (
        TooManyRedirects,  # 重定向次数过多
        MissingSchema,  # URL 缺少协议 (如 "http://")
        InvalidSchema,  # URL 协议无效
        InvalidURL,  # URL 格式无效
        ProxyError,  # 代理配置错误
        SSLError,  # SSL 证书验证失败

        # openai 库的永久性错误 (通常是 4xx 状态码)
        AuthenticationError,  # 401 认证失败 (API Key 错误)
        PermissionDeniedError,  # 403 无权限访问该模型
        NotFoundError,  # 404 找不到资源 (例如模型名称错误)
        BadRequestError,  # 400 错误请求 (例如输入内容过长、参数无效等)

    )

    @classmethod
    def _raise(cls, retry_state):
        ex = retry_state.outcome.exception()
        if ex:
            config.logger.exception(f'重试{retry_state.attempt_number}次后失败：{ex}', exc_info=True)

            if isinstance(ex, (AuthenticationError, PermissionDeniedError)):
                raise RuntimeError((
                                       '密钥错误或无权限访问该模型:' if config.defaulelang == 'zh' else 'Secret key error or no permission to access the model:') + ex.message)
            if isinstance(ex, RateLimitError):
                raise RuntimeError((
                                       '请求频繁触发429，请调大暂停时间:' if config.defaulelang == 'zh' else 'Request triggered 429, please increase the pause time:') + ex.message)
            if isinstance(ex, NotFoundError):
                raise RuntimeError(
                    ('请求API地址不存在:' if config.defaulelang == 'zh' else 'API address does not exist:') + ex.message)
            if isinstance(ex, APIConnectionError):
                raise RuntimeError(
                    ('连接失败，请检查网络或代理' if config.defaulelang == 'zh' else 'Connection timed out') + f': {ex.message}')
            if isinstance(ex, APIError):
                raise RuntimeError(ex.message)
            if isinstance(ex, ApiError_11):
                raise RuntimeError(ex.body.get('detail',{}).get('message',''))

            if isinstance(ex, (Timeout, ConnectionError)):
                raise RuntimeError(
                    ('连接失败，请检查网络或代理' if config.defaulelang == 'zh' else 'Connection timed out') + f': {ex.args}')
            if isinstance(ex, BaseException):
                raise RuntimeError(ex.args)

        raise RuntimeError(f"Error:{retry_state.attempt_number} retries")
