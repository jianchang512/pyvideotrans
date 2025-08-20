from elevenlabs.core import ApiError as ApiError_11
from openai import AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError, RateLimitError, \
    APIConnectionError, APIError
from requests.exceptions import TooManyRedirects, MissingSchema, InvalidSchema, InvalidURL, ProxyError, SSLError, \
    Timeout, ConnectionError, RetryError

from videotrans.configure import config


class RetryRaise:
    # 定义一个类属性，属于这些异常的是永久性错误，无法通过重试恢复，直接不重试
    # retry=retry_if_not_exception_type(RetryRaise.),
    NO_RETRY_EXCEPT = (
        TooManyRedirects,  # 重定向次数过多
        MissingSchema,  # URL 缺少协议 (如 "http://")
        InvalidSchema,  # URL 协议无效
        InvalidURL,  # URL 格式无效
        SSLError,  # SSL 证书验证失败
        RetryError,
        ConnectionError,

        # openai 库的永久性错误 (通常是 4xx 状态码)
        AuthenticationError,  # 401 认证失败 (API Key 错误)
        PermissionDeniedError,  # 403 无权限访问该模型
        NotFoundError,  # 404 找不到资源 (例如模型名称错误)
        BadRequestError,  # 400 错误请求 (例如输入内容过长、参数无效等)

    )

    @classmethod
    def _raise(cls, retry_state):
        ex = retry_state.outcome.exception()
        if not ex:
            raise RuntimeError(f"Retry failed after {retry_state.attempt_number} attempts without a final exception.")

        config.logger.exception(f'重试{retry_state.attempt_number}次后失败：{ex}', exc_info=True)
        lang = config.defaulelang

        # 键是异常类型（或类型的元组），值是一个处理函数（lambda），用于生成特定的错误消息。
        exception_handlers = {
            (AuthenticationError, PermissionDeniedError):
                lambda
                    e: f"{'密钥错误或无权限访问该模型:' if lang == 'zh' else 'Secret key error or no permission to access the model:'} {getattr(e, 'message', e)}",

            RateLimitError:
                lambda
                    e: f"{'请求频繁触发429，请调大暂停时间:' if lang == 'zh' else 'Request triggered 429, please increase the pause time:'} {getattr(e, 'message', e)}",

            NotFoundError:
                lambda
                    e: f"{'请求API地址不存在或模型名称错误:' if lang == 'zh' else 'API address does not exist or model name is wrong:'} {getattr(e, 'message', e)}",

            APIConnectionError:
                lambda
                    e: f"{'连接API失败，请检查网络或代理:' if lang == 'zh' else 'Failed to connect to API, check network or proxy:'} {getattr(e, 'message', e)}",

            (Timeout, ConnectionError):
                lambda
                    e: f"{'连接超时，请检查网络或代理:' if lang == 'zh' else 'Connection timed out, check network or proxy:'} {e.args}",
            ProxyError:'无法连接代理地址或代理不可用，请尝试关闭或切换带来' if lang == 'zh' else 'Cannot connect to proxy address or proxy is unavailable, please try to close or switch proxy.',
            ApiError_11:
                lambda e: e.body.get('detail', {}).get('message', 'ElevenLabs API error without detailed message.'),

            APIError:
                lambda e: getattr(e, 'message', 'An unknown API error occurred.')
        }

        # 遍历映射，查找匹配的处理器
        for exc_types, handler in exception_handlers.items():
            if isinstance(ex, exc_types):
                raise RuntimeError(handler(ex))

        # --- 如果以上特定异常都未匹配，则执行以下通用后备逻辑 ---

        if hasattr(ex, 'error'):
            raise RuntimeError(str(ex.error.get('message', ex.error)))
        if hasattr(ex, 'detail'):
            raise RuntimeError(str(ex.detail))
        if hasattr(ex, 'body') and ex.body:
            raise RuntimeError(str(ex.body))
        if hasattr(ex, 'args') and ex.args:
            raise RuntimeError(ex.args)

        # 如果没有任何匹配项，则直接重新抛出原始异常的字符串形式
        raise RuntimeError(str(ex))


class TranslateSrtError(Exception):
    pass


class DubbSrtError(Exception):
    pass


class SpeechToTextError(Exception):
    pass
