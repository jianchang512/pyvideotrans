from elevenlabs.core import ApiError as ApiError_11
from openai import AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError, RateLimitError,  APIConnectionError, APIError
from requests.exceptions import TooManyRedirects, MissingSchema, InvalidSchema, InvalidURL, ProxyError, SSLError, Timeout, ConnectionError, RetryError

from deepgram.clients.common.v1.errors import DeepgramApiError
from videotrans.configure import config

import httpx

from tenacity import RetryError as TenRetryError


class VideoTransError(Exception):
    def __init__(self,ex=None,message=''):
        super().__init__(message)
        self.ex=None
        if ex and isinstance(ex,Exception):
            self.ex=ex
        elif ex and isinstance(ex,str):
            message=f'{ex} {message}'
        self.message=message
    def __str__(self):
        return f'{str(self.ex) if self.ex else ""} {str(self.message)}'

class TranslateSrtError(VideoTransError):
    pass


class DubbSrtError(VideoTransError):
    pass


class SpeechToTextError(VideoTransError):
    pass


class StopRetry(VideoTransError):
    pass


# 无需继续重试的异常
NO_RETRY_EXCEPT = (
    TooManyRedirects,  # 重定向次数过多
    MissingSchema,  # URL 缺少协议 (如 "http://")
    InvalidSchema,  # URL 协议无效
    InvalidURL,  # URL 格式无效
    SSLError,  # SSL 证书验证失败

    # 连接问题，检查网络或尝试设置代理
    RetryError,
    ConnectionError,
    ConnectionRefusedError,  # 连接被拒绝
    ConnectionResetError,  # 连接被重置
    ConnectionAbortedError,  #

    # 代理错误
    ProxyError,

    # openai 库的永久性错误 (通常是 4xx 状态码)
    AuthenticationError,  # 401 认证失败 (API Key 错误)
    PermissionDeniedError,  # 403 无权限访问该模型
    NotFoundError,  # 404 找不到资源 (例如模型名称错误)
    BadRequestError,  # 400 错误请求 (例如输入内容过长、参数无效等)
    DeepgramApiError,
    StopRetry
)


# 根据异常类型，返回整理后的可读性错误消息
def get_msg_from_except(ex):
    lang = config.defaulelang
    if isinstance(ex,TenRetryError):
        try:
            ex=ex.last_attempt.exception()
        except:
            pass
    if isinstance(ex,VideoTransError) and ex.ex:
        ex=ex.ex
    
    # 键是异常类型（或类型的元组），值是一个处理函数（lambda），用于生成特定的错误消息。
    exception_handlers = {
        RateLimitError:
            lambda
                e: f"{'请求频繁触发429，请调大暂停时间:' if lang == 'zh' else 'Request triggered 429, please increase the pause time:'} {getattr(e, 'message', e)}",

        NotFoundError:
            lambda
                e: f"{'请求API地址不存在或模型名称错误:' if lang == 'zh' else 'API address does not exist or model name is wrong:'} {getattr(e, 'message', e)}",

        APIConnectionError:
            lambda
                e: f"{'连接API地址失败，请检查网络或代理:' if lang == 'zh' else 'Failed to connect to API, check network or proxy:'} {getattr(e, 'message', e)}",



        ProxyError: lambda e: '代理地址错误或代理不可用，请尝试关闭或切换代理' if lang == 'zh' else 'Cannot connect to proxy address or proxy is unavailable, please try to close or switch proxy.',
        ApiError_11: lambda e: e.body.get('detail',{}).get('message',e.body),

        APIError: lambda e: getattr(e, 'message', 'An unknown API error occurred.'),

        (TooManyRedirects, MissingSchema, InvalidSchema, InvalidURL, SSLError): lambda
            e: '请检查请求API地址是否正确' if lang == 'zh' else 'Please check whether the request address is correct.',

        # 连接问题，检查网络或尝试设置代理
        (Timeout,RetryError, ConnectionError, ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError): lambda
            e: '无法连接到请求API地址，请检查网络或代理设置是否正确' if lang == 'zh' else 'Cannot connect to request address, please check network or proxy settings.',

        # openai 库的永久性错误 (通常是 4xx 状态码)
        AuthenticationError: lambda
            e: f"{'密钥错误或无权限访问该模型 ' if lang == 'zh' else 'Secret key error or no permission to access the model '}",
        # 401 认证失败 (API Key 错误)
        PermissionDeniedError: lambda
            e: f"{'无访问权限或模型名称错误 ' if lang == 'zh' else 'No access permission or model name error '}",  # 403 无权限访问该模型
        BadRequestError: lambda
            e: f"{'请求参数错误' if lang == 'zh' else 'Request parameter error or input content is too long '}",
        # 400 错误请求 (例如输入内容过长、参数无效等)
        
    }
    

    # 遍历映射，查找匹配的处理器
    for exc_types, handler in exception_handlers.items():
        if isinstance(ex, exc_types):
            return handler(ex)

    # --- 如果以上特定异常都未匹配，则执行以下通用后备逻辑 ---
    if hasattr(ex, 'error'):
        return str(ex.error.get('message', ex.error))
    if hasattr(ex, 'message'):
        return str(ex.message)
    if hasattr(ex, 'detail'):
        if ex.detail.get('message'):
            return str(ex.detail.get('message'))
        if ex.detail.get('error'):
            return str(ex.detail.get('error').get('message', ex.detail.get('error')))
        return str(ex.detail)
    if hasattr(ex, 'body') and ex.body:
        if ex.body.get('message'):
            return str(ex.body.get('message', ex.body))
        if ex.body.get('error'):
            return str(ex.body.get('error').get('message', ex.body.get('error')))
        return str(ex.body)

    # 如果没有任何匹配项，则直接重新抛出原始异常的字符串形式
    return str(ex)
