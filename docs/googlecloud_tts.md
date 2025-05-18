# Google Cloud Text-to-Speech Integration

## Overview
This integration adds Google Cloud Text-to-Speech as a new TTS provider in VideoTrans. It offers high-quality voice synthesis with support for multiple languages and voices.

## Features
- Support for 16+ languages including:
  - Portuguese (Brazil)
  - English (US/GB)
  - Spanish
  - French
  - German
  - Italian
  - Japanese
  - Korean
  - Chinese
  - Russian
  - Hindi
  - Arabic
  - Turkish
  - Thai
  - Vietnamese
  - Indonesian
- Multiple voice options per language
- Adjustable speaking rate and pitch
- Support for multiple audio formats (MP3, LINEAR16, OGG_OPUS)
- User-friendly configuration interface

## Requirements
1. Python package:
   ```bash
   pip install google-cloud-texttospeech>=2.14.0
   ```

2. Google Cloud Project:
   - Create a project in [Google Cloud Console](https://console.cloud.google.com)
   - Enable the Cloud Text-to-Speech API
   - Create a service account and download the credentials JSON file

## Configuration
1. In VideoTrans, go to Settings > Google Cloud TTS
2. Configure the following settings:
   - **Credential JSON**: Path to your Google Cloud service account credentials file
   - **Language**: Select the target language (e.g., "pt-BR" for Brazilian Portuguese)
   - **Voice**: Choose from available voices for the selected language
   - **Audio Encoding**: Select output format (MP3, LINEAR16, or OGG_OPUS)

## Usage
1. Select "Google Cloud TTS" as your TTS provider
2. Choose your target language
3. Select a voice from the available options
4. Adjust speaking rate and pitch if needed
5. Proceed with your video translation as usual

## Troubleshooting
Common issues and solutions:

1. **"Credentials not found"**
   - Verify the path to your credentials JSON file
   - Ensure the file has proper read permissions

2. **"No voices available"**
   - Check if your credentials have Text-to-Speech API access
   - Verify if the selected language is supported
   - Check the logs for detailed error messages

3. **"Invalid speaking rate"**
   - Speaking rate should be a percentage (e.g., "+10%", "-5%")
   - Default is "+0%"

4. **"Invalid pitch"**
   - Pitch should be in Hz (e.g., "+2Hz", "-1Hz")
   - Default is "+0Hz"

## Contributing
Feel free to:
- Report bugs
- Suggest improvements
- Add support for more languages
- Enhance the configuration interface

## License
This integration follows the same license as the main VideoTrans project.

## Credits
- Google Cloud Text-to-Speech API
- VideoTrans team for the base project
- Contributors who helped with this integration 