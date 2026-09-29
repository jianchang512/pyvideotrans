# Developer Guide: Adding Custom Channels to `pyvideotrans`

> This guide provides step-by-step instructions for extending **pyvideotrans** with custom providers for **Speech-to-Text (STT)**, **Subtitle Translation (Trans)**, and **Text-to-Speech (TTS)**.

---

## Table of Contents
1. [Architecture Overview & Workflow](#1-architecture-overview--workflow)
2. [Step 1: Channel Registration & Constants](#2-step-1-channel-registration--constants)
3. [Step 2: Settings UI & Menu Integration (Optional)](#3-step-2-settings-ui--menu-integration-optional)
4. [Step 3: Core Provider Implementation](#4-step-3-core-provider-implementation)
   - [3.1 Subtitle Translation (`videotrans/translator`)](#31-subtitle-translation-videotranstranslator)
   - [3.2 Speech Recognition (`videotrans/recognition`)](#32-speech-recognition-videotransrecognition)
   - [3.3 Text-to-Speech (`videotrans/tts`)](#33-text-to-speech-videotranstts)
5. [Voice & Role Management (TTS Only)](#5-voice--role-management-tts-only)
6. [Best Practices & Caveats](#6-best-practices--caveats)

---

## 1. Architecture Overview & Workflow

`pyvideotrans` uses a modular plugin architecture. Extending any engine follows a standard 4-step workflow:

```text
[1. Register Constant & ChannelProvider]
    videotrans/{module}/_constants.py  --> Assign integer ID & declare ChannelProvider
              ↓
[2. UI & Param Configuration (if credentials needed)]
    videotrans/ui/{name}.py             --> UI widget layout
    videotrans/winform/{name}.py        --> Window controller & event handlers
    videotrans/configure/_app_params.py --> Default parameters
    videotrans/ui/menu_list.py          --> Register menu entry
              ↓
[3. Core Provider Implementation]
    videotrans/{module}/_{name}.py      --> Inherit base class and implement abstract methods
              ↓
[4. Voice Roles Definition (TTS Only)]
    videotrans/configure/constant.py OR videotrans/voicejson/{name}.json
```

Throughout this guide, `{name}` denotes your internal channel identifier (e.g., `newai`).

---

## 2. Step 1: Channel Registration & Constants

Module directories:
- **Speech Recognition (STT)**: `videotrans/recognition/`
- **Subtitle Translation**: `videotrans/translator/`
- **Text-to-Speech (TTS)**: `videotrans/tts/`

Open `_constants.py` inside the corresponding module directory:

### Naming & Rules
- **Constant ID**: Must be an incremented unique integer (e.g., `NEWAI_API = 32`).
- **Internal Identifier (`{name}`)**: Lowercase alphanumeric characters and underscores only, starting with an English letter (e.g., `newai`).
- **Implementation File**: Must be placed in the same folder and named `_{name}.py` (e.g., `_newai.py`).

### Registering with `ID_NAME_DICT`

```python
# videotrans/{module}/_constants.py

# 1. Define incremental ID
NEWAI_API = 32

# 2. Append to ID_NAME_DICT
ID_NAME_DICT[NEWAI_API] = ChannelProvider(
    name="NewAI Channel",     # Display name in the UI dropdown
    key_name="newai_key",     # Critical required param (used for pre-execution validation)
    win="newai",              # Window name (mapped to winform/{name}.py)
    imp="._newai"             # Relative import path for the provider class
)
```

> **Note on `key_name`**: Specify the primary credential name (e.g., API key or Base URL). If a user attempts to execute a task without configuring this parameter, the app will intercept the call and prompt the user to fill it out.

---

## 3. Step 2: Settings UI & Menu Integration (Optional)

If your channel does not require user credentials or configuration (e.g., a zero-config local model), you can skip this step.

### 1. Create UI Layout and Form Controller
- **UI File**: Create `videotrans/ui/{name}.py` (defines UI components such as QLineEdit, QPushButton; inspect existing files like `deepseek.py` for reference).
- **Form Controller**: Create `videotrans/winform/{name}.py` (handles config loading, saving, and connectivity tests).

### 2. Define Default Parameters (Optional)
In `videotrans/configure/_app_params.py`, add defaults inside `_get_defaults()`:

```python
# videotrans/configure/_app_params.py
def _get_defaults():
    return {
        # ...existing defaults
        "newai_key": "",
        "newai_url": "https://api.newai.com/v1",
        "newai_model": "newai-v1",
    }
```

### 3. Add to the Top Menu Bar
Add your channel to `videotrans/ui/menu_list.py` under the appropriate menu list:
- Translation: `MENU_CFG_TRANS`
- TTS: `MENU_CFG_TTS`
- STT: `MENU_CFG_STT`

Each menu item is a 3-element tuple: `("{name}", "Display Title", None)` (passing `None` as the 3rd element automatically routes clicks to `videotrans/winform/{name}.py`):

```python
# videotrans/ui/menu_list.py
MENU_CFG_TRANS = [
    # ...
    ("newai", "NewAI Settings", None),
]
```

---

## 4. Step 3: Core Provider Implementation

### 3.1 Subtitle Translation (`videotrans/translator`)

Create file: `videotrans/translator/_{name}.py`.
- **References**: OpenAI-compatible APIs can mirror `_deepseek.py`; standard REST APIs can mirror `_google.py`; local offline models can mirror `_hymt2.py`.

```python
from dataclasses import dataclass
from typing import Union
from videotrans.configure.config import ROOT_DIR, params
from videotrans.translator._base import BaseTrans

@dataclass
class NewAITrans(BaseTrans):
    """
    Custom Translation Provider implementation.
    """

    def _item_task(self, data: str) -> str:
        """
        Core translation task (MUST implement).

        :param data: Input text to translate.
                     - If 'Send full SRT' is checked: `data` is a full SRT-formatted string.
                     - If unchecked / traditional mode: `data` is a multiline plain text string.
        :return: Translated text strictly matching the input structure.
        """
        api_key = params.get("newai_key")

        # Always check for cancellation/exit signals
        if self._exit():
            return ""

        # TODO: Implement your network call or inference logic
        translated_text = self._request_translate(api_key, data)
        return translated_text

    def _download(self):
        """
        Optional: Download local model weights to:
        f"{ROOT_DIR}/models/{model_name}"
        """
        pass
```

---

### 3.2 Speech Recognition (`videotrans/recognition`)

Create file: `videotrans/recognition/_{name}.py`.
- **References**: Cloud API recognition can mirror `_openrouter.py`; lightweight local models can mirror `_fireredasr.py`; resource-intensive/PyTorch models can mirror `_whisper.py`.

```python
from dataclasses import dataclass
from typing import List, Union
from videotrans.configure.config import ROOT_DIR, params
from videotrans.recognition._base import BaseRecogn
from videotrans.util.tools import SrtItem

@dataclass
class NewAIRecogn(BaseRecogn):
    """
    Custom STT Provider implementation.
    """

    def _exec(self) -> Union[List[SrtItem], None]:
        """
        Core transcription logic (MUST implement).
        :return: List of SrtItem containing transcribed text, or None if aborted/failed.
        """
        if self._exit():
            return None

        # self.cut_audio() splits audio using VAD (Voice Activity Detection)
        # raws: List[SrtItem], each item contains 'filename' (path to chunk), 'start_time', 'end_time', etc.
        raws: List[SrtItem] = self.cut_audio()

        for it in raws:
            if self._exit():
                return None

            audio_file = it["filename"]
            it["text"] = self._transcribe_audio_chunk(audio_file)

        return raws

    def _download(self):
        """Download model files to {ROOT_DIR}/models if applicable."""
        pass

    def _transcribe_audio_chunk(self, audio_path: str) -> str:
        # TODO: Implement chunk transcription
        return ""
```

---

### 3.3 Text-to-Speech (`videotrans/tts`)

> **Crucial Audio Standardization Requirement**:
> After synthesizing each audio chunk, **you must convert the generated audio into `48000 Hz, Stereo (2 channels), pcm_s16le` format**. This guarantees proper audio alignment and video stitching.
> 
> Use the built-in helper method directly:
> ```python
> self.convert_to_wav(raw_synthesized_file, data_item["filename"])
> ```

Create file: `videotrans/tts/_{name}.py`. Select either **Pattern A** (API) or **Pattern B** (Local Engine):

#### Pattern A: Cloud API / Streaming Concurrent Requests (Implement `_run`)
References: `_openrouter.py`, `_xiaomi.py`.

```python
from dataclasses import dataclass
from typing import Dict, List, Union
from videotrans.configure.config import ROOT_DIR, params
from videotrans.tts._base import BaseTTS

@dataclass
class NewAITTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_key = params.get("newai_key")
        self.speed = self.get_speed()  # Retrieves speed multiplier set in UI

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        """
        Synthesizes a single subtitle segment.

        :param data_item: Dictionary containing:
                          {
                              "filename": "/path/to/target.wav",  # Expected output path
                              "role": "voice_role_id",            # Voice identity selected in UI
                              "text": "Text to synthesize"        # Text content
                          }
        :param idx: Segment index.
        :return: Absolute path to the generated .wav file, or None on failure.
        """
        if self._exit():
            return None

        target_file = data_item["filename"]
        role = data_item["role"]
        text = data_item["text"]

        # 1. Synthesize audio to a temporary file
        temp_audio = self._call_tts_api(text=text, role=role)

        # 2. Standardize audio to 48kHz / 16-bit / 2ch PCM WAV
        self.convert_to_wav(temp_audio, target_file)

        return target_file

    def _download(self):
        pass
```

#### Pattern B: Local Batch Inference Models (Implement `_exec`)
References: `_omnivoice.py`, `_zipvoice.py`.

```python
from dataclasses import dataclass
from videotrans.configure.config import ROOT_DIR
from videotrans.tts._base import BaseTTS

@dataclass
class NewAILocalTTS(BaseTTS):

    def _exec(self):
        """
        Batch processing method for local models.
        The queue of items to synthesize is available in `self.queue_tts`.
        """
        for item in self.queue_tts:
            if self._exit():
                break

            target_file = item["filename"]
            role = item["role"]
            text = item["text"]

            # Perform model inference
            raw_output = self.infer_audio(text, role)
            
            # Standardize output
            self.convert_to_wav(raw_output, target_file)

    def _download(self):
        # Download model weights to {ROOT_DIR}/models
        pass
```

---

## 5. Voice & Role Management (TTS Only)

`pyvideotrans` supports two strategies for populating voice role dropdown menus:

### Strategy 1: Universal Roles (Language-Independent)
If voice roles do not vary by target language:
1. Define the comma-separated role IDs in `videotrans/configure/constant.py`:
   ```python
   # videotrans/configure/constant.py
   NEWAITTS_ROLES = "alloy,ash,echo,fable,onyx,nova"
   ```
2. Return this list in `videotrans/util/help_role.py` inside `role_menu()`.

> **Best Practice**: Use the **exact sound ID** expected by the backend engine (e.g., `en-US-JennyNeural`) rather than descriptive natural language aliases to avoid unnecessary lookup tables.

### Strategy 2: Language-Dependent Roles
If each language has a specific set of available voices:
1. Create a JSON file: `videotrans/voicejson/{name}.json`.
2. Map standard language codes (defined in `EDGE_LANGUANGES_CODE` in `videotrans/configure/_languages_dict.py`) to lists of voice IDs:

```json
{
  "zh-cn": ["voice_zh_1", "voice_zh_2"],
  "en": ["voice_en_1", "voice_en_2"],
  "ja": ["voice_ja_1"]
}
```

---

## 6. Best Practices & Caveats

1. **Check for Exit Signals Frequently**:
   In loops and long-running HTTP/inference cycles, periodically evaluate `if self._exit(): return`. This ensures responsiveness when the user clicks the **Stop** button in the UI.
2. **Heavyweight Local Models**:
   Do **not** load large PyTorch models (e.g., Whisper large, F5-TTS, OmniVoice) directly in the main GUI thread/process. Follow the pattern in `_whisper.py` using `multiprocessing` or `subprocess` to prevent UI freezing and CUDA memory leaks.
3. **Model Storage Location**:
   Always place downloaded checkpoints inside `f"{ROOT_DIR}/models/{model_name}"`. Never create arbitrary paths relative to the current working directory.
4. **Resilient Downloads**:
   In `_download()`, implement retry logic with timeouts and resume capabilities to handle unstable network environments gracefully.
5. **Subtitle Integrity in LLM Translations**:
   When parsing translations with "Send full SRT" enabled, verify that the line count and SRT structure matches the original input before proceeding. Handle malformed responses defensively.