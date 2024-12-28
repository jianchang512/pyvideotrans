"""
Communicate package.
"""

import asyncio
import concurrent.futures
import json
import ssl
import time
import uuid
from contextlib import nullcontext
from io import TextIOWrapper
from queue import Queue
from typing import (
    Any,
    AsyncGenerator,
    ContextManager,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Union,
)
from xml.sax.saxutils import escape

import aiohttp
import certifi
import logging
import re
import math
import io # 导入 io 模块

from .constants import SEC_MS_GEC_VERSION, WSS_HEADERS, WSS_URL
from .drm import DRM
from .exceptions import (
    NoAudioReceived,
    UnexpectedResponse,
    UnknownResponse,
    WebSocketError,
)
from .models import TTSConfig


def get_headers_and_data(
    data: bytes, header_length: int
) -> Tuple[Dict[bytes, bytes], bytes]:
    """
    Returns the headers and data from the given data.

    Args:
        data (bytes): The data to be parsed.
        header_length (int): The length of the header.

    Returns:
        tuple: The headers and data to be used in the request.
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    headers = {}
    for line in data[:header_length].split(b"\r\n"):
        key, value = line.split(b":", 1)
        headers[key] = value

    return headers, data[header_length + 2 :]


def remove_incompatible_characters(string: Union[str, bytes]) -> str:
    """
    The service does not support a couple of character ranges.
    Most important being the vertical tab character which is
    commonly present in OCR-ed PDFs. Not doing this will
    result in an error from the service.

    Args:
        string (str or bytes): The string to be cleaned.

    Returns:
        str: The cleaned string.
    """
    if isinstance(string, bytes):
        string = string.decode("utf-8")
    if not isinstance(string, str):
        raise TypeError("string must be str or bytes")

    chars: List[str] = list(string)

    for idx, char in enumerate(chars):
        code: int = ord(char)
        if (0 <= code <= 8) or (11 <= code <= 12) or (14 <= code <= 31):
            chars[idx] = " "

    return "".join(chars)


def connect_id() -> str:
    """
    Returns a UUID without dashes.

    Returns:
        str: A UUID without dashes.
    """
    return str(uuid.uuid4()).replace("-", "")


def split_text_by_byte_length(
    text: Union[str, bytes], byte_length: int
) -> Generator[bytes, None, None]:
    """
    Splits a string into a list of strings of a given byte length
    while attempting to keep words together. This function assumes
    text will be inside of an XML tag.

    Args:
        text (str or bytes): The string to be split.
        byte_length (int): The maximum byte length of each string in the list.

    Yield:
        bytes: The next string in the list.
    """
    if isinstance(text, str):
        text = text.encode("utf-8")
    if not isinstance(text, bytes):
        raise TypeError("text must be str or bytes")

    if byte_length <= 0:
        raise ValueError("byte_length must be greater than 0")

    while len(text) > byte_length:
        # Find the last space in the string
        split_at = text.rfind(b" ", 0, byte_length)

        # If no space found, split_at is byte_length
        split_at = split_at if split_at != -1 else byte_length

        # Verify all & are terminated with a ;
        while b"&" in text[:split_at]:
            ampersand_index = text.rindex(b"&", 0, split_at)
            if text.find(b";", ampersand_index, split_at) != -1:
                break

            split_at = ampersand_index - 1
            if split_at < 0:
                raise ValueError("Maximum byte length is too small or invalid text")
            if split_at == 0:
                break

        # Append the string to the list
        new_text = text[:split_at].strip()
        if new_text:
            yield new_text
        if split_at == 0:
            split_at = 1
        text = text[split_at:]

    new_text = text.strip()
    if new_text:
        yield new_text


def mkssml(tc: TTSConfig, escaped_text: Union[str, bytes], voice: str) -> str:  # 添加 voice 参数
    """
    Creates a SSML string from the given parameters.

    Args:
        tc (TTSConfig): The TTS configuration.
        escaped_text (str or bytes): The escaped text. If bytes, it must be UTF-8 encoded.
        voice (str): The voice to use for this text.

    Returns:
        str: The SSML string.
    """

    # If the text is bytes, convert it to a string.
    if isinstance(escaped_text, bytes):
        escaped_text = escaped_text.decode("utf-8")

    # Return the SSML string.
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
        f"<voice name='{voice}'>"
        f"<prosody pitch='{tc.pitch}' rate='{tc.rate}' volume='{tc.volume}'>"
        f"{escaped_text}"
        "</prosody>"
        "</voice>"
        "</speak>"
    )


def date_to_string() -> str:
    """
    Return Javascript-style date string.

    Returns:
        str: Javascript-style date string.
    """
    # %Z is not what we want, but it's the only way to get the timezone
    # without having to use a library. We'll just use UTC and hope for the best.
    # For example, right now %Z would return EEST when we need it to return
    # Eastern European Summer Time.
    return time.strftime(
        "%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)", time.gmtime()
    )


def ssml_headers_plus_data(request_id: str, timestamp: str, ssml: str) -> str:
    """
    Returns the headers and data to be used in the request.

    Returns:
        str: The headers and data to be used in the request.
    """

    return (
        f"X-RequestId:{request_id}\r\n"
        "Content-Type:application/ssml+xml\r\n"
        f"X-Timestamp:{timestamp}Z\r\n"  # This is not a mistake, Microsoft Edge bug.
        "Path:ssml\r\n\r\n"
        f"{ssml}"
    )


def calc_max_mesg_size(tts_config: TTSConfig) -> int:
    """Calculates the maximum message size for the given voice, rate, and volume.

    Returns:
        int: The maximum message size.
    """
    websocket_max_size: int = 2**16
    overhead_per_message: int = (
        len(
            ssml_headers_plus_data(
                connect_id(),
                date_to_string(),
                mkssml(tts_config, "", "Microsoft Server Speech Text to Speech Voice (en-US, AriaNeural)"), # 修改：默认值
            )
        )
        + 50  # margin of error
    )
    return websocket_max_size - overhead_per_message



class Communicate:
    """
    Class for communicating with the service.
    """

    def __init__(
        self,
        text_list: List[Dict[str, str]],  # 修改：接受一个字典列表
        *,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        proxy: Optional[str] = None,
        connect_timeout: int = 10,
        receive_timeout: int = 60,
        max_retries: int = 5, # 新增最大重试次数
        retry_delay: int = 1, # 新增重试延迟
    ):
        """
        Initializes the Communicate class.

        Raises:
            ValueError: If the voice is not valid.
        """

        # Validate TTS settings and store the TTSConfig object.
        self.tts_config = TTSConfig(
          "Microsoft Server Speech Text to Speech Voice (en-US, AriaNeural)",
          rate, 
          volume, 
          pitch
          ) # 默认语音

        # Validate the text_list parameter.
        if not isinstance(text_list, list):
            raise TypeError("text_list must be list")
        
        for item in text_list:
          if not isinstance(item, dict):
              raise TypeError("text_list items must be dict")
          if "text" not in item or "filename" not in item or "role" not in item: # 检查 role 参数
            raise ValueError("text_list items must have 'text', 'filename' and 'role' keys")
          if not isinstance(item["text"], str) or not isinstance(item["filename"], str) or not isinstance(item["role"], str):
              raise TypeError("'text', 'filename' and 'role' values must be strings")


        # Store the text list for later use.
        self.text_list = text_list


        # Validate the proxy parameter.
        if proxy is not None and not isinstance(proxy, str):
            raise TypeError("proxy must be str")
        self.proxy: Optional[str] = proxy

        # Validate the timeout parameters.
        if not isinstance(connect_timeout, int):
            raise TypeError("connect_timeout must be int")
        if not isinstance(receive_timeout, int):
            raise TypeError("receive_timeout must be int")
        self.session_timeout = aiohttp.ClientTimeout(
            total=None,
            connect=None,
            sock_connect=connect_timeout,
            sock_read=receive_timeout,
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # Store current state of TTS.
        self.state: Dict[str, Any] = {
            "partial_text": None,
            "offset_compensation": 0,
            "last_duration_offset": 0,
            "stream_was_called": False,
        }

    def __parse_metadata(self, data: bytes) -> Dict[str, Any]:
        for meta_obj in json.loads(data)["Metadata"]:
            meta_type = meta_obj["Type"]
            if meta_type == "WordBoundary":
                current_offset = (
                    meta_obj["Data"]["Offset"] + self.state["offset_compensation"]
                )
                current_duration = meta_obj["Data"]["Duration"]
                return {
                    "type": meta_type,
                    "offset": current_offset,
                    "duration": current_duration,
                    "text": meta_obj["Data"]["text"]["Text"],
                }
            if meta_type in ("SessionEnd",):
                continue
            raise UnknownResponse(f"Unknown metadata type: {meta_type}")
        raise UnexpectedResponse("No WordBoundary metadata found")

    async def __stream(self, text:str, voice:str, retry_count:int=0) -> AsyncGenerator[Dict[str, Any], None]: #修改：传入要合成的文本 和 voice
        async def send_command_request() -> None:
            """Sends the request to the service."""
            
            # Prepare the request to be sent to the service.
            #
            # Note sentenceBoundaryEnabled and wordBoundaryEnabled are actually supposed
            # to be booleans, but Edge Browser seems to send them as strings.
            #
            # This is a bug in Edge as Azure Cognitive Services actually sends them as
            # bool and not string. For now I will send them as bool unless it causes
            # any problems.
            #
            # Also pay close attention to double { } in request (escape for f-string).
            await websocket.send_str(
                f"X-Timestamp:{date_to_string()}\r\n"
                "Content-Type:application/json; charset=utf-8\r\n"
                "Path:speech.config\r\n\r\n"
                '{"context":{"synthesis":{"audio":{"metadataoptions":{'
                '"sentenceBoundaryEnabled":false,"wordBoundaryEnabled":true},'
                '"outputFormat":"audio-24khz-48kbitrate-mono-mp3"'
                "}}}}\r\n"
            )
            logging.debug("Sent config command")

        async def send_ssml_request() -> None:
            """Sends the SSML request to the service."""

            # Send the request to the service.
            ssml = mkssml(self.tts_config, self.state["partial_text"], voice) # 使用传入的 voice 参数
            logging.debug(f"Sending SSML: {ssml}, retry_count: {retry_count}")
            await websocket.send_str(
                ssml_headers_plus_data(
                    connect_id(),
                    date_to_string(),
                    ssml,
                )
            )
            logging.debug("Sent SSML request")

        # audio_was_received indicates whether we have received audio data
        # from the websocket. This is so we can raise an exception if we
        # don't receive any audio data.
        audio_was_received = False
        
        
        
        
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        
        url = f"{WSS_URL}&Sec-MS-GEC={DRM.generate_sec_ms_gec()}" \
              f"&Sec-MS-GEC-Version={SEC_MS_GEC_VERSION}" \
              f"&ConnectionId={connect_id()}"
        
        logging.debug(f"Connecting to WSS URL: {url}")

        # Create a new connection to the service.
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=self.session_timeout,
        ) as session, session.ws_connect(
            url,
            compress=15,
            proxy=self.proxy,
            headers=WSS_HEADERS,
            ssl=ssl_ctx,
        ) as websocket:
            logging.debug("WebSocket connection established")
            # Send the request to the service.
            await send_command_request()

            # Send the SSML request to the service.
            await send_ssml_request()

            async for received in websocket:
                if received.type == aiohttp.WSMsgType.TEXT:
                    encoded_data: bytes = received.data.encode("utf-8")
                    parameters, data = get_headers_and_data(
                        encoded_data, encoded_data.find(b"\r\n\r\n")
                    )
                    logging.debug(f"Received text message, path: {parameters.get(b'Path', None)}")

                    path = parameters.get(b"Path", None)
                    if path == b"audio.metadata":
                        # Parse the metadata and yield it.
                        parsed_metadata = self.__parse_metadata(data)
                        yield parsed_metadata

                        # Update the last duration offset for use by the next SSML request.
                        self.state["last_duration_offset"] = (
                            parsed_metadata["offset"] + parsed_metadata["duration"]
                        )
                    elif path == b"turn.end":
                        # Update the offset compensation for the next SSML request.
                        self.state["offset_compensation"] = self.state[
                            "last_duration_offset"
                        ]

                        # Use average padding typically added by the service
                        # to the end of the audio data. This seems to work pretty
                        # well for now, but we might ultimately need to use a
                        # more sophisticated method like using ffmpeg to get
                        # the actual duration of the audio data.
                        self.state["offset_compensation"] += 8_750_000

                        # Exit the loop so we can send the next SSML request.
                        break
                    elif path not in (b"response", b"turn.start"):
                        raise UnknownResponse("Unknown path received")
                elif received.type == aiohttp.WSMsgType.BINARY:
                    # Message is too short to contain header length.
                    if len(received.data) < 2:
                        raise UnexpectedResponse(
                            "We received a binary message, but it is missing the header length."
                        )

                    # The first two bytes of the binary message contain the header length.
                    header_length = int.from_bytes(received.data[:2], "big")
                    if header_length > len(received.data):
                        raise UnexpectedResponse(
                            "The header length is greater than the length of the data."
                        )

                    # Parse the headers and data from the binary message.
                    parameters, data = get_headers_and_data(
                        received.data, header_length
                    )
                    logging.debug(f"Received binary message, path: {parameters.get(b'Path', None)}")

                    # Check if the path is audio.
                    if parameters.get(b"Path") != b"audio":
                        raise UnexpectedResponse(
                            "Received binary message, but the path is not audio."
                        )

                    # At termination of the stream, the service sends a binary message
                    # with no Content-Type; this is expected. What is not expected is for
                    # an MPEG audio stream to be sent with no data.
                    content_type = parameters.get(b"Content-Type", None)
                    if content_type not in [b"audio/mpeg", None]:
                        raise UnexpectedResponse(
                            "Received binary message, but with an unexpected Content-Type."
                        )

                    # We only allow no Content-Type if there is no data.
                    if content_type is None:
                        if len(data) == 0:
                            continue

                        # If the data is not empty, then we need to raise an exception.
                        raise UnexpectedResponse(
                            "Received binary message with no Content-Type, but with data."
                        )

                    # If the data is empty now, then we need to raise an exception.
                    if len(data) == 0:
                        raise UnexpectedResponse(
                            "Received binary message, but it is missing the audio data."
                        )

                    # Yield the audio data.
                    audio_was_received = True
                    
                    yield {"type": "audio", "data": data}
                       
                elif received.type == aiohttp.WSMsgType.ERROR:
                    logging.error(f"Received WebSocket error: {received.data if received.data else 'Unknown error'}")
                    raise WebSocketError(
                        received.data if received.data else "Unknown error"
                    )
                else:
                    logging.debug(f"Received message with type: {received.type}")

            if not audio_was_received:
                logging.debug("No audio was received, current retry_count is " + str(retry_count) )
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2**retry_count)) # 指数退避延迟
                    async for message in self.__stream(text, voice, retry_count + 1): #递归调用
                        yield message
                else:
                    raise NoAudioReceived(
                        "No audio was received after multiple retries. Please verify that your parameters are correct."
                    )


    async def stream( # 修改：不再返回generator，改为直接执行
        self,
    ) -> None:
        """
        Streams audio and metadata from the service.

        Raises:
            NoAudioReceived: If no audio is received from the service.
            UnexpectedResponse: If the response from the service is unexpected.
            UnknownResponse: If the response from the service is unknown.
            WebSocketError: If there is an error with the websocket.
        """
        # Check if stream was called before.
        if self.state["stream_was_called"]:
            raise RuntimeError("stream can only be called once.")
        self.state["stream_was_called"] = True
        
        for item in self.text_list: # 循环处理每个text
            texts = split_text_by_byte_length(
                escape(remove_incompatible_characters(item["text"])),
                calc_max_mesg_size(self.tts_config),
            )
            with open(item["filename"], "wb") as audio:
                for self.state["partial_text"] in texts:
                    try:
                        async for message in self.__stream(item["text"], item["role"]):# 修改：传入当前要合成的文本和 role
                            if message["type"] == "audio":
                                audio.write(message["data"])
                    except aiohttp.ClientResponseError as e:
                        if e.status != 403:
                            raise

                        DRM.handle_client_response_error(e)
                        async for message in self.__stream(item["text"], item["role"]):
                            if message["type"] == "audio":
                                audio.write(message["data"])
                    await asyncio.sleep(0.1)  # 添加请求频率控制

    async def save( # 修改：不再需要save方法
        self,
    ) -> None:
        """
        Save the audio and metadata to the specified files.
        """
        raise RuntimeError("save method is not supported")


    def stream_sync(self) -> None: #修改：同步方法也改成直接执行
        """Synchronous interface for async stream method"""
        
        def fetch_async_items() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.stream())
            loop.close()
            

        with concurrent.futures.ThreadPoolExecutor() as executor:
           executor.submit(fetch_async_items)

    def save_sync(
        self,
    ) -> None:
        """Synchronous interface for async save method."""
        raise RuntimeError("save_sync method is not supported")