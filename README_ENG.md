# [简体中文](./README.md)

This is a video translation tool that can translate videos from one language to another and create dubbed videos in another language. Speech recognition is based on the `openai-whisper` offline model, text translation uses `google|baidu|chatGPT|DeepL` translation interfaces, and text-to-speech synthesis uses `Microsoft Edge tts`.

[Discord](https://discord.gg/evkPeKJddD)

https://github.com/jianchang512/pyvideotrans/assets/3378335/544409e1-4cec-45b9-ad5b-34b68170147d


*youtube*

[![在youtube上观看](https://img.youtube.com/vi/skLtE1XnO6Q/hqdefault.jpg)](https://www.youtube.com/watch?v=skLtE1XnO6Q)

# Instructions for Using Precompiled Versions

0. Only available for Windows 10 and Windows 11 systems. Compilation from source is required for macOS.
1. Download the latest release from the releases page, unzip it, and double-click on `sp.exe`.
2. Original video directory: Select the mp4/avi/mov/mpg/mkv video,one or most.
3. Output video directory: If not selected, it will default to generating in the same directory under `_video_out`.
4. Translation selection: Choose Google, Baidu, ChatGPT, or DeepL. For Baidu/ChatGPT/DeepL, click "Set key" to input the corresponding information.
5. Network proxy address: If you cannot directly access Google/ChatGPT in your region, set the proxy in the software interface under "Network Proxy." For example, if using V2Ray, enter `http://127.0.0.1:10809`, or for Clash, enter `http://127.0.0.1:7890`. If you have changed the default port or are using other proxy software, enter accordingly.
6. Video original language: Choose the language of the video to be translated.
7. Target translation language: Choose the language to translate into.
8. Dubbing selection: After choosing the target translation language, select a dubbing role.

   Hard subtitles: These are subtitles that are always displayed and cannot be hidden. If you want subtitles to be visible when playing on a webpage, select hard subtitles embedding.

   Soft subtitles: If the player supports subtitle management, you can show or hide subtitles. Soft subtitles will not be displayed when playing on a webpage, and some domestic players may not support them. To display soft subtitles, the generated video and the subtitle file should have the same name and be placed in the same directory.

   **if "neither embed subtitles nor select a dubbing role."** will create srt files

9. Text recognition model: Choose base/small/medium/large/large-v3. The recognition effect improves with larger models, but recognition speed becomes slower, and more memory is required. The model will need to be downloaded the first time; by default, use base. You can pre-download the model and place it in the `current software directory/models` directory.

   **whole all**: not split audio before send to model

   **split**: split 10s secs audio before send to model

   **Model download links:**

   [Tiny model](https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt)

   [Base model](https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt)

   [Small model](https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt)

   [Medium model](https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt)

   [Large model](https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large.pt)

   [Large-v3 model](https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt)

   [VLC decoder download](https://www.videolan.org/vlc/)

   [FFmpeg download (included in the compiled version)](https://www.ffmpeg.org/)

10. Dubbing speed: Enter a number between -90 and +90. The time required for a sentence may vary with different language voices, causing the audio and subtitles to be out of sync. You can adjust the speed here. A negative number slows down the speed, while a positive number speeds it up.

11. Auto speed up: If the translated audio duration is longer than the original, and this option is selected, the software will forcefully accelerate playback to shorten the duration.

12. Silent segments: Enter a number between 100 and 2000, representing milliseconds. The default is 500, indicating the minimum duration of a silent segment for segmenting speech.

13. CUDA acceleration: If your computer's graphics card is an Nvidia card and CUDA environment and driver are configured, enabling this option will significantly improve speed.

14. TTS:  edgeTTS & openai TTS select role use dubbing

15. Click the "Start" button. The bottom will display the current progress and log, and the right text box will show the subtitles.

16. **After the subtitles are parsed, pause and wait to modify the subtitles. If no action is taken, it will automatically continue to the next step after 60 seconds. You can also edit subtitles in the right subtitle area and manually click "Continue to Synthesize."**

> All original videos are uniformly in mp4 format for fast processing and good network compatibility.
>
> Soft subtitle embedding: Subtitles are embedded as separate files in the video, which can be extracted again. If the player supports it, you can enable or disable subtitles in the player's subtitle management. Note that many domestic players require the srt subtitle file and video to be in the same directory and have the same name to display soft subtitles. Additionally, the srt file may need to be converted to GBK encoding to avoid displaying garbled text.

By default, a subtitle file with the same name as the video will be generated in the "srt" folder under the target output video directory.

For speech that cannot be recognized, the original audio will be copied directly.

# Source Code Deployment

1. Set up a Python 3.9+ environment.
2. Clone the repository: `git clone https://github.com/jianchang512/pyvideotrans`
3. Navigate to the project directory: `cd pyvideotrans`
4. Install the required dependencies: `pip install -r requirements.txt`
5. Unzip `ffmpeg.zip` to the root directory (contains `ffmpeg.exe`).
6. Run the software interface: `python sp.py`. For command line execution: `python cli.py`.
7. If you want to package it as an exe, use the command `pyinstaller sp.py`. Do not add `-w -F` parameters; otherwise, it may crash (due to TensorFlow).

# CLI (Command Line Interface) Usage

After deploying the source code, execute `python cli.py` from the command line.

### Supported Parameters

- **--source_mp4**: [Required] Path to the video to be translated, ending in .mp4.
- **--target_dir**: Location where the translated video will be saved. Defaults to the `_video_out` folder in the source video directory.
- **--source_language**: Video language code. Defaults to `en` (zh-cn | zh-tw | en | fr | de | ja | ko | ru | es | th | it | pt | vi | ar).
- **--target_language**: Target language code. Defaults to `zh-cn` (zh-cn | zh-tw | en | fr | de | ja | ko | ru | es | th | it | pt | vi | ar).
- **--proxy**: HTTP proxy address. Defaults to None. If unable to access Google, fill in the proxy, e.g., `http://127.0.0.1:10809`.
- **--subtitle_type**: 1 for embedding hard subtitles, 2 for embedding soft subtitles.
- **--voice_role**: Depending on the selected target language code, enter the corresponding role name. Use `python cli.py show_voice` to display available role names for each language.
- **--voice_rate**: Negative number to decrease dubbing speed, positive number to increase it. Defaults to `0`.
- **--voice_silence**: Enter a number between 100 and 2000, representing the minimum milliseconds of silent segments. Defaults to `500`.
- **--voice_autorate**: If the translated audio duration exceeds the original, force speeding up the translated audio for alignment.
- **--whisper_model**: Defaults to `base`. Options are `base`, `small`, `medium`, `large`. The larger the model, the better the effect, but the slower the speed.

### CLI Example

```bash
python cli.py --source_mp4 "D:/video/ex.mp4" --source_language en --target_language zh-cn --proxy "http://127.0.0.1:10809" --voice_replace zh-CN-XiaoxiaoNeural
```

This example translates the video located at `D:/video/ex.mp4` from English to Chinese, sets the proxy to `http://127.0.0.1:10809`, and uses the dubbing role `zh-CN-XiaoxiaoNeural`.

```bash
python cli.py --source_mp4 "D:/video/ex.mp4" --source_language zh-cn --target_language en --proxy "http://127.0.0.1:10809" --voice_replace en-US-AriaNeural --voice_autorate --whisper_model small
```

This example translates the video located at `D:/video/ex.mp4` from Chinese to English, sets the proxy to `http://127.0.0.1:10809`, uses the dubbing role `en-US-AriaNeural`, and if the translated audio duration is longer than the original, it will automatically accelerate playback. The text recognition model used is `small`.

# Software Preview Screenshots

![Screenshot 1](./images/pen1.png?b)
![Screenshot 2](./images/pen2.png?b)
![Screenshot 3](./images/pen3.png?b)
![Screenshot 4](./images/pen4.png?b)
![Screenshot 5](./images/pen5.png?b)
![CLI Screenshot](./images/cli.png?c)

# Video Before and After Comparison

[Demo Original Video and Translated Video](https://www.wonyes.org/demo.html)

[Youtube Demo](https://youtu.be/skLtE1XnO6Q)

# CUDA Acceleration Support

1. Precompiled versions partially support CUDA, especially if your GPU is an Nvidia card. You can install the corresponding [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) based on your graphics card driver version and operating system. It's recommended to upgrade your graphics card driver to the latest version before installing. For full CUDA support, you need to use the source code version and deploy it on your computer.

2. Using CUDA in the source code version: You need to install the dependencies for GPU support using `pip install -r requirements-gpu.txt` instead of `requirements.txt`.

3. Configuring the CUDA environment can be relatively complex, and you may encounter various issues, so be prepared to search for solutions.

# Acknowledgments

This program relies on several open-source projects:

1. pydub
2. ffmpeg
3. PyQt5
4. SpeechRecognition
5. edge-tts
6. openai-whisper
7. opencv-python
