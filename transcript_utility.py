import argparse
import glob
import logging
import math
import os
import sys
import warnings
import tempfile
from typing import Optional, Callable
from functools import wraps

import openai
import torch
import yt_dlp
from pydub import AudioSegment

try:
    import whisper
except ImportError:
    whisper = None

# Configuration
openai.api_key = os.environ.get('OPENAI_API_KEY')
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Decorators
def error_handler(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper

def ensure_directory(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the output directory from the function's arguments
        output_dir = next((arg for arg in args if isinstance(arg, str) and '/' in arg), None)
        if output_dir:
            ensure_dir(os.path.dirname(output_dir))
        return func(*args, **kwargs)
    return wrapper

# Helper functions
def ensure_dir(directory: str) -> None:
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def get_user_choice(prompt: str) -> bool:
    """Get user's yes/no choice."""
    return input(prompt).lower().strip() == 'y'

def get_output_file_path(output_dir: str, base_name: str, extension: str) -> str:
    """Generate output file path."""
    return os.path.join(output_dir, f"{base_name}.{extension}")

# YouTube downloader
class YouTubeDownloader:
    @staticmethod
    @error_handler
    @ensure_directory
    def download(source_url: str, base_name: str, force_download: bool = False) -> str:
        """Download audio from YouTube URL."""
        output_dir = base_name
        output_file = get_output_file_path(output_dir, base_name, "mp3")

        if os.path.exists(output_file) and not force_download:
            if get_user_choice(f"{output_file} already exists. Use existing file? (y/n): "):
                logger.info(f"Using existing file: {output_file}")
                return output_file

        ydl_opts = YouTubeDownloader._get_ydl_opts(output_dir)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Downloading audio from: {source_url}")
            info = ydl.extract_info(source_url, download=True)
            video = info['entries'][0] if 'entries' in info else info
            logger.info(f"Video title: {video.get('title')}")
            logger.info(f"Duration: {video.get('duration')} seconds")

            output_file = ydl.prepare_filename(video)
            output_file = os.path.splitext(output_file)[0] + '.mp3'

            if base_name != 'audio':
                new_output_file = get_output_file_path(output_dir, base_name, "mp3")
                os.rename(output_file, new_output_file)
                output_file = new_output_file

        if not os.path.exists(output_file):
            raise FileNotFoundError(f"Failed to download audio from {source_url}. Output file not found: {output_file}")

        logger.info(f"Audio file downloaded successfully: {output_file}")
        return output_file

    @staticmethod
    def _get_ydl_opts(output_dir: str) -> dict:
        """Get YouTube downloader options."""
        return {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
            'nocheckcertificate': True,
            'prefer_ffmpeg': True,
            'logger': logger,
        }

# Transcription
class Transcriber:
    @staticmethod
    @error_handler
    def transcribe(file_path: str, whisper_model: Optional[str] = None) -> str:
        """Transcribe audio using either local Whisper model or OpenAI API."""
        if whisper_model:
            return Transcriber._transcribe_with_whisper(file_path, whisper_model)
        else:
            return Transcriber._transcribe_with_openai(file_path)

    @staticmethod
    def _transcribe_with_whisper(file_path: str, model_name: str) -> str:
        """Transcribe using local Whisper model."""
        if whisper is None:
            raise ImportError("whisper module not found. Install with: pip install openai-whisper")

        logger.info(f"Transcribing with local Whisper model: {model_name}")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning, module="torch.serialization")
            warnings.filterwarnings("ignore", category=UserWarning)

            device = "mps" if torch.backends.mps.is_available() else "cpu"
            logger.info(f"Using device: {device}")

            model = whisper.load_model(model_name, device=device)
            result = model.transcribe(file_path, fp16=False)

        return result["text"]

    @staticmethod
    def _transcribe_with_openai(file_path: str) -> str:
        """Transcribe using OpenAI API."""
        logger.info("Transcribing with OpenAI API")
        with open(file_path, 'rb') as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript

# Main functions
@error_handler
@ensure_directory
def mp3_to_transcript(audio_file_path: str, base_name: str = '',
                      chunk_length_ms: int = 60000, whisper_model: Optional[str] = None) -> str:
    """Convert MP3, WAV, or M4A to transcript."""
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    base_name = base_name or os.path.splitext(os.path.basename(audio_file_path))[0]
    output_dir = base_name
    os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists
    final_transcript_file = get_output_file_path(output_dir, base_name, "txt")

    if os.path.exists(final_transcript_file):
        if get_user_choice(f"Transcript file {final_transcript_file} already exists. Use existing file? (y/n): "):
            logger.info(f"Using existing transcript file: {final_transcript_file}")
            return final_transcript_file

    logger.info(f"Processing audio file: {audio_file_path}")
    audio_format = os.path.splitext(audio_file_path)[1].lower()
    if audio_format in ['.mp3', '.wav', '.m4a']:
        audio = AudioSegment.from_file(audio_file_path, format=audio_format[1:])
    else:
        raise ValueError(f"Unsupported audio format: {audio_format}")

    chunks = math.ceil(len(audio) / chunk_length_ms)
    logger.info(f'Total chunks: {chunks}')

    existing_chunks = sorted(glob.glob(os.path.join(output_dir, f'{base_name}_chunk_*.txt')))
    start_chunk = len(existing_chunks)

    for i in range(start_chunk, chunks):
        process_audio_chunk(audio, i, chunk_length_ms, output_dir, base_name, whisper_model)

    combine_transcripts(output_dir, base_name, final_transcript_file)

    return final_transcript_file

def process_audio_chunk(audio: AudioSegment, chunk_index: int, chunk_length_ms: int,
                        output_dir: str, base_name: str, whisper_model: Optional[str]) -> None:
    """Process a single audio chunk."""
    start_time = chunk_index * chunk_length_ms
    end_time = start_time + chunk_length_ms
    chunk = audio[start_time:end_time]

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Use a temporary file with the original audio format
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        chunk_file_path = temp_file.name
        chunk.export(chunk_file_path, format="wav")

    chunk_transcript_path = get_output_file_path(output_dir, f'{base_name}_chunk_{chunk_index}', "txt")

    logger.debug(f'Processing chunk: {chunk_file_path}')

    transcript = Transcriber.transcribe(chunk_file_path, whisper_model)
    with open(chunk_transcript_path, 'w', encoding='utf-8') as f:
        f.write(transcript)

    print(f"Chunk {chunk_index} transcript:")
    print(transcript)
    print("------------------------")

    os.remove(chunk_file_path)

def combine_transcripts(output_dir: str, base_name: str, final_transcript_file: str) -> None:
    """Combine all chunk transcripts into a single file."""
    all_chunk_transcripts = sorted(glob.glob(os.path.join(output_dir, f'{base_name}_chunk_*.txt')))
    full_transcript = []
    for chunk_file in all_chunk_transcripts:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            full_transcript.append(f.read())

    with open(final_transcript_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(full_transcript))

    logger.info(f"Full transcript saved to {final_transcript_file}")

    for chunk_file in all_chunk_transcripts:
        os.remove(chunk_file)

@error_handler
@ensure_directory
def youtube_to_transcript(source_url: str, base_name: str = '',
                          whisper_model: Optional[str] = None, force_download: bool = False) -> str:
    """Convert YouTube video to transcript."""
    logger.info("Checking for existing transcript...")
    base_name = base_name or os.path.splitext(os.path.basename(source_url))[0]

    output_dir = base_name
    final_transcript_file = get_output_file_path(output_dir, base_name, "txt")

    if os.path.exists(final_transcript_file):
        if get_user_choice(f"Transcript file {final_transcript_file} already exists. Use existing file? (y/n): "):
            logger.info(f"Using existing transcript file: {final_transcript_file}")
            return final_transcript_file

    logger.info("Downloading and converting YouTube video to audio...")
    audio_file = YouTubeDownloader.download(source_url, base_name, force_download=force_download)
    logger.info(f"Audio file: {audio_file}")
    logger.info("Transcribing audio...")
    return mp3_to_transcript(audio_file, base_name, whisper_model=whisper_model)

def main():
    parser = argparse.ArgumentParser(description="Transcript Utility")
    parser.add_argument('action', choices=['y2a', 'a2t', 'y2t'],
                        help="Action to perform: y2a (YouTube to Audio), a2t (Audio to Transcript), or y2t (YouTube to Transcript)")
    parser.add_argument('source', help="YouTube URL or audio file path")
    parser.add_argument('base_name', nargs='?', default='', help="Base name for output files (optional)")
    parser.add_argument('--whisper', choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help="Use local Whisper model instead of OpenAI API")
    parser.add_argument('--force-download', action='store_true', help="Force download even if the file exists")
    parser.add_argument('--force-transcribe', action='store_true', help="Force transcription even if the transcript file exists")

    args = parser.parse_args()

    try:
        if args.action == 'y2a':
            audio_file = YouTubeDownloader.download(args.source, args.base_name, force_download=args.force_download)
            logger.info(f"Audio downloaded: {audio_file}")
            if get_user_choice("Do you want to transcribe this audio? (y/n): "):
                mp3_to_transcript(audio_file, args.base_name, whisper_model=args.whisper)
        elif args.action == 'a2t':
            transcript_file = mp3_to_transcript(args.source, args.base_name, whisper_model=args.whisper)
            logger.info(f"Transcript file: {transcript_file}")
        elif args.action == 'y2t':
            transcript_file = youtube_to_transcript(args.source, args.base_name, whisper_model=args.whisper, force_download=args.force_download)
            logger.info(f"Transcript file: {transcript_file}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()