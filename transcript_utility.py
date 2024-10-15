import yt_dlp
import openai
import os
import sys
import math
import argparse
import logging
import glob
import whisper
import warnings
import torch
from pydub import AudioSegment

try:
    import whisper
except ImportError:
    whisper = None

openai.api_key = os.environ.get('OPENAI_API_KEY')

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def yt_url_to_audio(source_url, base_name='audio', force_download=False):
    output_dir = base_name
    ensure_dir(output_dir)
    output_file = os.path.join(output_dir, f'{base_name}.mp3')

    if os.path.exists(output_file) and not force_download:
        user_choice = input(f"{output_file} already exists. Do you want to use the existing file? (y/n): ").lower()
        if user_choice == 'y':
            logger.info(f"Using existing file: {output_file}")
            return output_file
        elif user_choice != 'n':
            logger.warning("Invalid input. Proceeding with download.")
    elif force_download:
        logger.info(f"Force download option is set. Redownloading {output_file}")


    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  # Changed this line
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': False,
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
        'logger': logger,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Downloading audio from: {source_url}")
            info = ydl.extract_info(source_url, download=True)
            if 'entries' in info:
                # Can be a playlist or a list of videos
                video = info['entries'][0]
            else:
                # Just a video
                video = info
            logger.info(f"Video title: {video.get('title')}")
            logger.info(f"Duration: {video.get('duration')} seconds")

            # Get the actual output filename
            output_file = ydl.prepare_filename(video)
            output_file = os.path.splitext(output_file)[0] + '.mp3'  # Ensure .mp3 extension

            # Rename the file if a base_name was provided
            if base_name != 'audio':
                new_output_file = os.path.join(output_dir, f'{base_name}.mp3')
                os.rename(output_file, new_output_file)
                output_file = new_output_file

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp download error: {e}")
        if "This video is not available" in str(e):
            logger.error("The video might be private or region-restricted.")
        elif "Video unavailable" in str(e):
            logger.error("The video might have been removed or is unavailable.")
        raise
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        raise

    if not os.path.exists(output_file):
        raise FileNotFoundError(f"Failed to download audio from {source_url}. Output file not found: {output_file}")

    logger.info(f"Audio file downloaded successfully: {output_file}")
    return output_file

def transcribe_audio(file_path, whisper_model=None):
    if whisper_model:
        if whisper is None:
            logger.error("Local Whisper model specified, but whisper module is not installed.")
            logger.info("Please install it with: pip install openai-whisper")
            raise ImportError("whisper module not found")

        logger.info(f"Transcribing with local Whisper model: {whisper_model}")
        try:
            # Suppress the FutureWarning
            warnings.filterwarnings("ignore", category=FutureWarning, module="torch.serialization")

            # Determine the device
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            logger.info(f"Using device: {device}")

            # Load the model with the appropriate device
            model = whisper.load_model(whisper_model, device=device)

            # Transcribe with appropriate device
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                result = model.transcribe(file_path, fp16=False)  # Force FP32

            return result["text"]
        except AttributeError:
            logger.error("The installed whisper module does not have the expected 'load_model' function.")
            logger.info("This might be a different 'whisper' module. Please ensure you have openai-whisper installed.")
            raise
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            raise
    else:
        logger.info("Transcribing with OpenAI API")
        with open(file_path, 'rb') as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript

def mp3_to_transcript(audio_file_path='audio.mp3', base_name='', chunk_length_ms=60000, whisper_model=None):
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    if not base_name:
        base_name = os.path.splitext(os.path.basename(audio_file_path))[0]

    output_dir = base_name
    ensure_dir(output_dir)

    final_transcript_file = os.path.join(output_dir, f"{base_name}.txt")

    if os.path.exists(final_transcript_file):
        user_choice = input(f"Transcript file {final_transcript_file} already exists. Do you want to use the existing file? (y/n): ").lower()
        if user_choice == 'y':
            logger.info(f"Using existing transcript file: {final_transcript_file}")
            return final_transcript_file
        elif user_choice != 'n':
            logger.warning("Invalid input. Proceeding with transcription.")

    logger.info(f"Processing audio file: {audio_file_path}")
    try:
        audio = AudioSegment.from_mp3(audio_file_path)
    except Exception as e:
        logger.error(f"Error loading audio file: {e}")
        raise

    chunks = math.ceil(len(audio) / chunk_length_ms)
    logger.info(f'Total chunks: {chunks}')

    # Check for existing intermediate files
    existing_chunks = sorted(glob.glob(os.path.join(output_dir, f'{base_name}_chunk_*.txt')))
    start_chunk = len(existing_chunks)

    for i in range(start_chunk, chunks):
        start_time = i * chunk_length_ms
        end_time = start_time + chunk_length_ms
        chunk = audio[start_time:end_time]
        chunk_file_path = os.path.join(output_dir, f'{base_name}_chunk_{i}.mp3')
        chunk_transcript_path = os.path.join(output_dir, f'{base_name}_chunk_{i}.txt')

        logger.debug(f'Processing chunk: {chunk_file_path}')
        chunk.export(chunk_file_path, format='mp3')

        transcript = transcribe_audio(chunk_file_path, whisper_model)
        with open(chunk_transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript)

        print(f"Chunk {i} transcript:")
        print(transcript)
        print("------------------------")

        os.remove(chunk_file_path)  # Remove audio chunk after transcription

    # Combine all transcripts
    all_chunk_transcripts = sorted(glob.glob(os.path.join(output_dir, f'{base_name}_chunk_*.txt')))
    full_transcript = []
    for chunk_file in all_chunk_transcripts:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            full_transcript.append(f.read())

    output_file = os.path.join(output_dir, f"{base_name}.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(full_transcript))

    logger.info(f"Full transcript saved to {output_file}")

    # Remove intermediate transcript files
    for chunk_file in all_chunk_transcripts:
        os.remove(chunk_file)

def youtube_to_transcript(source_url, base_name='', whisper_model=None, force_download=False):
    logger.info("Checking for existing transcript...")
    if not base_name:
        base_name = os.path.splitext(os.path.basename(source_url))[0]

    output_dir = base_name
    ensure_dir(output_dir)
    final_transcript_file = os.path.join(output_dir, f"{base_name}.txt")

    if os.path.exists(final_transcript_file):
        user_choice = input(f"Transcript file {final_transcript_file} already exists. Do you want to use the existing file? (y/n): ").lower()
        if user_choice == 'y':
            logger.info(f"Using existing transcript file: {final_transcript_file}")
            return final_transcript_file
        elif user_choice != 'n':
            logger.warning("Invalid input. Proceeding with download and transcription.")

    logger.info("Downloading and converting YouTube video to audio...")
    try:
        audio_file = yt_url_to_audio(source_url, base_name, force_download=force_download)
        logger.info(f"Audio file: {audio_file}")
        logger.info("Transcribing audio...")
        return mp3_to_transcript(audio_file, base_name, whisper_model=whisper_model)
    except Exception as e:
        logger.error(f"Error in youtube_to_transcript: {e}")
        raise

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

    if not args.base_name:
        args.base_name = os.path.splitext(os.path.basename(args.source))[0]

    whisper_model = args.whisper if args.whisper else None

    try:
        if args.action == 'y2a':
            audio_file = yt_url_to_audio(args.source, args.base_name, force_download=args.force_download)
            logger.info(f"Audio downloaded: {audio_file}")
            if input("Do you want to transcribe this audio? (y/n): ").lower() == 'y':
                mp3_to_transcript(audio_file, args.base_name, whisper_model=whisper_model)
        elif args.action == 'a2t':
            if args.force_transcribe:
                mp3_to_transcript(args.source, args.base_name, whisper_model=whisper_model)
            else:
                transcript_file = mp3_to_transcript(args.source, args.base_name, whisper_model=whisper_model)
                if transcript_file:
                    logger.info(f"Transcript file: {transcript_file}")
        elif args.action == 'y2t':
            if args.force_transcribe:
                youtube_to_transcript(args.source, args.base_name, whisper_model=whisper_model, force_download=args.force_download)
            else:
                transcript_file = youtube_to_transcript(args.source, args.base_name, whisper_model=whisper_model, force_download=args.force_download)
                if transcript_file:
                    logger.info(f"Transcript file: {transcript_file}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()