"""
list_voices package for edge_tts.
"""

import json
import ssl
from typing import Any, Dict, List, Optional

import aiohttp
import certifi

from .constants import SEC_MS_GEC_VERSION, VOICE_HEADERS, VOICE_LIST
from .drm import DRM


async def __list_voices(
    session: aiohttp.ClientSession, ssl_ctx: ssl.SSLContext, proxy: Optional[str]
) -> Any:
    """
    Private function that makes the request to the voice list URL and parses the
    JSON response. This function is used by list_voices() and makes it easier to
    handle client response errors related to clock skew.

    Args:
        session (aiohttp.ClientSession): The aiohttp session to use for the request.
        ssl_ctx (ssl.SSLContext): The SSL context to use for the request.
        proxy (Optional[str]): The proxy to use for the request.

    Returns:
        dict: A dictionary of voice attributes.
    """
    async with session.get(
        f"{VOICE_LIST}&Sec-MS-GEC={DRM.generate_sec_ms_gec()}"
        f"&Sec-MS-GEC-Version={SEC_MS_GEC_VERSION}",
        headers=VOICE_HEADERS,
        proxy=proxy,
        ssl=ssl_ctx,
        raise_for_status=True,
    ) as url:
        data = json.loads(await url.text())
    return data


async def list_voices(*, proxy: Optional[str] = None) -> Any:
    """
    List all available voices and their attributes.

    This pulls data from the URL used by Microsoft Edge to return a list of
    all available voices.

    Args:
        proxy (Optional[str]): The proxy to use for the request.

    Returns:
        dict: A dictionary of voice attributes.
    """
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    async with aiohttp.ClientSession(trust_env=True) as session:
        try:
            data = await __list_voices(session, ssl_ctx, proxy)
        except aiohttp.ClientResponseError as e:
            if e.status != 403:
                raise

            DRM.handle_client_response_error(e)
            data = await __list_voices(session, ssl_ctx, proxy)
    return data


class VoicesManager:
    """
    A class to find the correct voice based on their attributes.
    """

    def __init__(self) -> None:
        self.voices: List[Dict[str, Any]] = []
        self.called_create: bool = False

    @classmethod
    async def create(
        cls: Any, custom_voices: Optional[List[Dict[str, Any]]] = None
    ) -> Any:
        """
        Creates a VoicesManager object and populates it with all available voices.
        """
        self = VoicesManager()
        self.voices = await list_voices() if custom_voices is None else custom_voices
        self.voices = [
            {**voice, **{"Language": voice["Locale"].split("-")[0]}}
            for voice in self.voices
        ]
        self.called_create = True
        return self

    def find(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Finds all matching voices based on the provided attributes.
        """
        if not self.called_create:
            raise RuntimeError(
                "VoicesManager.find() called before VoicesManager.create()"
            )

        matching_voices = [
            voice for voice in self.voices if kwargs.items() <= voice.items()
        ]
        return matching_voices
