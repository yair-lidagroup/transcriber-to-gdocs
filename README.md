# Audio Recording, Transcription and Summarization Tool

This tool allows you to record audio, transcribe it using Whisper, summarize the transcription using GPT-4, and upload the results to Google Docs.

## Features

- Audio recording using the `sox` command line tool
- Speech-to-text transcription using OpenAI's Whisper model
- Text summarization using GPT-4
- Automatic upload to Google Docs
- Local backup of both transcription and summary
- Support for multiple languages
- Error handling and retry logic

## Prerequisites

1. Python 3.8 or higher
2. OpenAI API key
3. Google Cloud Platform project with Google Docs API enabled
4. Command line audio recording tool (`sox`)

## Installation

1. Install system dependencies:

  **macOS (using Homebrew):**
  ```bash
  brew install sox
  ```

2. Install requirements:
```bash
pip install openai
pip install google-auth-oauthlib
pip install google-api-python-client
pip install openai-whisper
```

3. Set up Google Cloud credentials:
- Go to Google Cloud Console
- Create a new project or select existing one
- Enable Google Docs API
- Create OAuth 2.0 credentials (Desktop Application)
- Download credentials JSON file

4. Set up OpenAI API key:
- Get your API key from OpenAI's platform
- Save it to a text file

## Usage

python script.py -c path/to/credentials.json -o path/to/openai_key.txt

With language specification:
python script.py -c path/to/credentials.json -o path/to/openai_key.txt -l <language_code>

Arguments:

-c, --credentials: Path to Google OAuth credentials JSON file (default: credentials.json)
-o, --openai-key-file: Path to OpenAI API key file (default: openai_key.txt)
-l, --language: Language code for transcription (e.g., en, es). Optional - will auto-detect if not specified.


Output Files
-The script generates these files for each recording:
-recording_[timestamp].wav: The recorded audio (temporary)
-transcription_[timestamp].txt: The transcribed text
-summary_[timestamp].txt: The summarized text
-Google Doc with the summary

## Common Issues

- "rec" command not found: Install sox using the instructions above
- Google credentials errors: Make sure you've downloaded the correct credentials file and enabled the Google Docs API
- OpenAI API errors: Verify your API key and check your usage quota
