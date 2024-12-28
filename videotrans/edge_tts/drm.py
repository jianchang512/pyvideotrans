"""DRM module for handling DRM operations with clock skew correction."""

import hashlib
from datetime import datetime as dt
from datetime import timezone as tz
from typing import Optional

import aiohttp

from .constants import TRUSTED_CLIENT_TOKEN
from .exceptions import SkewAdjustmentError

WIN_EPOCH = 11644473600
S_TO_NS = 1e9


class DRM:
    """
    Class to handle DRM operations with clock skew correction.
    """

    clock_skew_seconds: float = 0.0

    @staticmethod
    def adj_clock_skew_seconds(skew_seconds: float) -> None:
        """
        Adjust the clock skew in seconds in case the system clock is off.

        This method updates the `clock_skew_seconds` attribute of the DRM class
        to the specified number of seconds.

        Args:
            skew_seconds (float): The number of seconds to adjust the clock skew to.

        Returns:
            None
        """
        DRM.clock_skew_seconds += skew_seconds

    @staticmethod
    def get_unix_timestamp() -> float:
        """
        Gets the current timestamp in Windows file time format with clock skew correction.

        Returns:
            float: The current timestamp in Windows file time format.
        """
        return dt.now(tz.utc).timestamp() + DRM.clock_skew_seconds

    @staticmethod
    def parse_rfc2616_date(date: str) -> Optional[float]:
        """
        Parses an RFC 2616 date string into a Unix timestamp.

        This function parses an RFC 2616 date string into a Unix timestamp.

        Args:
            date (str): RFC 2616 date string to parse.

        Returns:
            Optional[float]: Unix timestamp of the parsed date string, or None if parsing failed.
        """
        try:
            return (
                dt.strptime(date, "%a, %d %b %Y %H:%M:%S %Z")
                .replace(tzinfo=tz.utc)
                .timestamp()
            )
        except ValueError:
            return None

    @staticmethod
    def handle_client_response_error(e: aiohttp.ClientResponseError) -> None:
        """
        Handle a client response error.

        This method adjusts the clock skew based on the server date in the response headers
        and raises a SkewAdjustmentError if the server date is missing or invalid.

        Args:
            e (Exception): The client response error to handle.

        Returns:
            None
        """
        if e.headers is None:
            raise SkewAdjustmentError("No server date in headers.") from e
        server_date: Optional[str] = e.headers.get("Date", None)
        if server_date is None or not isinstance(server_date, str):
            raise SkewAdjustmentError("No server date in headers.") from e
        server_date_parsed: Optional[float] = DRM.parse_rfc2616_date(server_date)
        if server_date_parsed is None or not isinstance(server_date_parsed, float):
            raise SkewAdjustmentError(
                f"Failed to parse server date: {server_date}"
            ) from e
        client_date = DRM.get_unix_timestamp()
        DRM.adj_clock_skew_seconds(server_date_parsed - client_date)

    @staticmethod
    def generate_sec_ms_gec() -> str:
        """
        Generates the Sec-MS-GEC token value.

        This function generates a token value based on the current time in Windows file time format,
        adjusted for clock skew, and rounded down to the nearest 5 minutes. The token is then hashed
        using SHA256 and returned as an uppercased hex digest.

        Returns:
            str: The generated Sec-MS-GEC token value.

        See Also:
            https://github.com/rany2/edge-tts/issues/290#issuecomment-2464956570
        """

        # Get the current timestamp in Windows file time format with clock skew correction
        ticks = DRM.get_unix_timestamp()

        # Switch to Windows file time epoch (1601-01-01 00:00:00 UTC)
        ticks += WIN_EPOCH

        # Round down to the nearest 5 minutes (300 seconds)
        ticks -= ticks % 300

        # Convert the ticks to 100-nanosecond intervals (Windows file time format)
        ticks *= S_TO_NS / 100

        # Create the string to hash by concatenating the ticks and the trusted client token
        str_to_hash = f"{ticks:.0f}{TRUSTED_CLIENT_TOKEN}"

        # Compute the SHA256 hash and return the uppercased hex digest
        return hashlib.sha256(str_to_hash.encode("ascii")).hexdigest().upper()
