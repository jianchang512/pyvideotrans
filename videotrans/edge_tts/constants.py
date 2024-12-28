"""
Constants for the Edge TTS project.
"""

BASE_URL = "speech.platform.bing.com/consumer/speech/synthesize/readaloud"
TRUSTED_CLIENT_TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4"

WSS_URL = f"wss://{BASE_URL}/edge/v1?TrustedClientToken={TRUSTED_CLIENT_TOKEN}"
VOICE_LIST = f"https://{BASE_URL}/voices/list?trustedclienttoken={TRUSTED_CLIENT_TOKEN}"

CHROMIUM_FULL_VERSION = "130.0.2849.68"
CHROMIUM_MAJOR_VERSION = CHROMIUM_FULL_VERSION.split(".", maxsplit=1)[0]
SEC_MS_GEC_VERSION = f"1-{CHROMIUM_FULL_VERSION}"
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    f" (KHTML, like Gecko) Chrome/{CHROMIUM_MAJOR_VERSION}.0.0.0 Safari/537.36"
    f" Edg/{CHROMIUM_MAJOR_VERSION}.0.0.0",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}
WSS_HEADERS = {
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Origin": "chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold",
}
WSS_HEADERS.update(BASE_HEADERS)
VOICE_HEADERS = {
    "Authority": "speech.platform.bing.com",
    "Sec-CH-UA": f'" Not;A Brand";v="99", "Microsoft Edge";v="{CHROMIUM_MAJOR_VERSION}",'
    f' "Chromium";v="{CHROMIUM_MAJOR_VERSION}"',
    "Sec-CH-UA-Mobile": "?0",
    "Accept": "*/*",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}
VOICE_HEADERS.update(BASE_HEADERS)
