import os
import subprocess
import argparse
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI, RateLimitError, OpenAIError
import time

SCOPES = ['https://www.googleapis.com/auth/documents']

def print_credentials_instructions():
    print("\nError: Google credentials file not found!")
    print("\nTo create Google credentials:")
    print("1. Go to https://console.cloud.google.com")
    print("2. Create a new project or select an existing one")
    print("3. Enable Google Docs API:")
    print("   - Go to 'APIs & Services' → 'Library'")
    print("   - Search for 'Google Docs API'")
    print("   - Click Enable")
    print("4. Create credentials:")
    print("   - Go to 'APIs & Services' → 'Credentials'")
    print("   - Click 'Create Credentials' → 'OAuth 2.0 Client ID'")
    print("   - Choose 'Desktop Application'")
    print("   - Give it a name")
    print("   - Download the JSON file")
    print("\nThen run this script with:")
    print("python script.py -c path/to/credentials.json -o path/to/openai_key.txt [-l language_code]")
    print("Example: python script.py -c credentials.json -o openai_key.txt -l en")

def print_openai_key_instructions():
    print("\nError: OpenAI API key file not found!")
    print("\nTo obtain an OpenAI API key:")
    print("1. Sign up or log in to your OpenAI account at https://platform.openai.com/")
    print("2. Navigate to the API section: https://platform.openai.com/account/api-keys")
    print("3. Click on 'Create new secret key'")
    print("4. Name your API key and click 'Create secret key'")
    print("5. Copy the generated API key")
    print("6. Save the API key to a file, for example, 'openai_key.txt'")
    print("\nThen run this script with:")
    print("python script.py -c path/to/credentials.json -o path/to/openai_key.txt [-l language_code]")
    print("Example: python script.py -c credentials.json -o openai_key.txt -l en")

def get_google_creds(credentials_path):
    """Gets valid user credentials from storage or initiates the OAuth2 flow."""
    if not os.path.exists(credentials_path):
        print_credentials_instructions()
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    creds = None
    token_path = 'token.json'
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)
        # Save credentials for future use
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_openai_api_key(openai_key_path):
    """Reads the OpenAI API key from a file."""
    if not os.path.exists(openai_key_path):
        print_openai_key_instructions()
        raise FileNotFoundError(f"OpenAI API key file not found: {openai_key_path}")
    
    try:
        with open(openai_key_path, 'r') as f:
            api_key = f.read().strip()
        if not api_key:
            raise ValueError("OpenAI API key file is empty.")
        return api_key
    except Exception as e:
        print(f"Error reading OpenAI API key: {e}")
        raise

def create_doc(creds, title, content):
    """Creates a new Google Doc with given title and content."""
    try:
        service = build('docs', 'v1', credentials=creds)
        doc = service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        return f"https://docs.google.com/document/d/{doc_id}/edit"
    except HttpError as error:
        print(f"An error occurred while creating the document: {error}")
        return None

def record_and_transcribe(filename="recording.wav", language=None):
    """Records audio and transcribes it using Whisper."""
    print("Recording... Press Ctrl+C to stop")
    try:
        subprocess.run(['rec', '-r', '44100', filename], check=True)
    except KeyboardInterrupt:
        print("\nRecording stopped")
    except FileNotFoundError:
        print("\nError: 'rec' command not found. Please install 'sox' to enable recording.")
        raise
    except subprocess.CalledProcessError as e:
        print(f"\nError during recording: {e}")
        raise
    
    print("Transcribing with Whisper...")
    try:
        whisper_command = [
            'whisper', 
            filename, 
            '--model', 'base',
            '--output_dir', '.', 
            '--output_format', 'txt'
        ]
        if language:
            whisper_command.extend(['--language', language])
            print(f"Specified language: {language}")
        else:
            print("No language specified. Whisper will auto-detect the language based on the first part of the audio.")
        
        subprocess.run(whisper_command, check=True)
        
        # Look for the transcription file
        base_filename = os.path.splitext(filename)[0]
        transcription_file = f"{base_filename}.txt"
        print(f"Looking for transcription in: {transcription_file}")
        
        if os.path.exists(transcription_file):
            with open(transcription_file, 'r') as f:
                transcription = f.read()
            return transcription
        else:
            print("Available txt files:", [f for f in os.listdir('.') if f.endswith('.txt')])
            raise FileNotFoundError(f"Could not find transcription file: {transcription_file}")
            
    except subprocess.CalledProcessError as e:
        print(f"Error running Whisper: {e}")
        raise

def summarize_text(text, api_key, max_retries=5, backoff_factor=2):
    """Generates a summary of the given text using OpenAI's ChatCompletion API with retry logic."""
    try:
        client = OpenAI(api_key=api_key)
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Create a concise, correct in grammar and punctuation summary of the text. If there are less than two sentences, just fix them according to grammar."},
            {"role": "user", "content": text}
        ]
        
        completion = client.chat.completions.create(
            model='gpt-4o',  # You can use 'gpt-3.5-turbo' if preferred
            messages=messages,
            max_tokens=500,  # Adjust as needed
            temperature=0.5,
        )
        
        summary = completion.choices[0].message.content
        return summary
    
    except RateLimitError as e:
        if max_retries > 0:
            wait_time = backoff_factor * (6 - max_retries)  # Exponential backoff
            print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            return summarize_text(text, api_key, max_retries - 1, backoff_factor)
        else:
            print("Max retries exceeded. Please check your OpenAI quota and billing details.")
            raise e
    
    except OpenAIError as e:
        print(f"An OpenAI API error occurred: {e}")
        raise e
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise e

def cleanup_files(*filenames):
    """Cleans up temporary files."""
    for filename in filenames:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"Cleaned up {filename}")
            except Exception as e:
                print(f"Warning: Could not remove {filename}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Record audio, transcribe, summarize, and upload to Google Docs')
    parser.add_argument('-c', '--credentials', 
                        help='Path to the Google OAuth credentials JSON file',
                        default='credentials.json')
    parser.add_argument('-o', '--openai-key-file',
                        help='Path to the OpenAI API key file',
                        default='openai_key.txt')
    parser.add_argument('-l', '--language',
                        help='Language code for transcription (e.g., en, es). If not specified, language will be auto-detected.',
                        default=None)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"recording_{timestamp}.wav"
    transcription_file = f"transcription_{timestamp}.txt"
    summary_file = f"summary_{timestamp}.txt"
    
    try:
        print("\n=== Starting Recording and Transcription ===")
        transcription = record_and_transcribe(filename, language=args.language)
        
        # Save local backup of transcription
        with open(transcription_file, 'w') as f:
            f.write(transcription)
        print(f"\nLocal transcription backup saved to: {transcription_file}")
        
        print("\n=== Generating Summary ===")
        openai_api_key = get_openai_api_key(args.openai_key_file)
        summary = summarize_text(transcription, openai_api_key)
        
        # Save local backup of summary
        with open(summary_file, 'w') as f:
            f.write(summary)
        print(f"Local summary backup saved to: {summary_file}")
        
        print("\n=== Uploading Summary to Google Docs ===")
        print("Getting Google credentials (browser will open for authentication)...")
        creds = get_google_creds(args.credentials)
        
        doc_title = f"Summary {timestamp}"
        print(f"Creating Google Doc: {doc_title}")
        doc_url = create_doc(creds, doc_title, summary)
        
        if doc_url:
            print(f"\nSuccess! Document available at: {doc_url}")
        
    except FileNotFoundError as e:
        if "Credentials file not found" in str(e):
            # Instructions already printed by get_google_creds
            return
        elif "OpenAI API key file not found" in str(e):
            # Instructions already printed by get_openai_api_key
            return
        else:
            print(f"\nError: {str(e)}")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except RateLimitError as e:
        print("\nError: Rate limit exceeded. Please check your OpenAI quota and billing details.")
    except OpenAIError as e:
        print(f"\nAn OpenAI API error occurred: {e}")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("\nFull error trace:")
        import traceback
        print(traceback.format_exc())
    finally:
        # Cleanup temporary files but keep the local backups
        print("\n=== Cleaning Up ===")
        cleanup_files(
            filename,
            f"{os.path.splitext(filename)[0]}.txt"
        )
        print(f"\nLocal transcription backup kept at: {transcription_file}")
        print(f"Local summary backup kept at: {summary_file}")

if __name__ == '__main__':
    print("=== Audio Recording, Transcription, Summary, and Upload Script ===")
    main()
