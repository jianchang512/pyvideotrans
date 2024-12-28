"""Exceptions for the Edge TTS project."""


class BaseEdgeTTSException(Exception):
    """Base exception for the Edge TTS project."""


class UnknownResponse(BaseEdgeTTSException):
    """Raised when an unknown response is received from the server."""


class UnexpectedResponse(BaseEdgeTTSException):
    """Raised when an unexpected response is received from the server.

    This hasn't happened yet, but it's possible that the server will
    change its response format in the future."""


class NoAudioReceived(BaseEdgeTTSException):
    """Raised when no audio is received from the server."""


class WebSocketError(BaseEdgeTTSException):
    """Raised when a WebSocket error occurs."""


class SkewAdjustmentError(BaseEdgeTTSException):
    """Raised when an error occurs while adjusting the clock skew."""
