"""Confucius4-TTS: a multilingual and cross-lingual zero-shot TTS engine."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("confuciustts")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
