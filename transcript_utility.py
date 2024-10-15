import yt_dlp
import openai
import os
from pydub import AudioSegment
import math
import argparse
import logging

openai.api_key = os.environ.get('OPENAI_API_KEY')

# Set up logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

def yt_url_to_audio(source_url, base_name='audio'):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{base_name}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': logger,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.debug(f"Downloading audio from: {source_url}")
        ydl.download([source_url])

    return f'{base_name}.mp3'

def mp3_to_transcript(audio_file_path='audio.mp3', base_name='', chunk_length_ms=60000):
    if not base_name:
        base_name = os.path.splitext(os.path.basename(audio_file_path))[0]

    logger.debug(f"Processing audio file: {audio_file_path}")
    audio = AudioSegment.from_mp3(audio_file_path)
    chunks = math.ceil(len(audio) / chunk_length_ms)
    logger.debug(f'Total chunks: {chunks}')
    chunk_files = []

    for i in range(chunks):
        start_time = i * chunk_length_ms
        end_time = start_time + chunk_length_ms
        chunk = audio[start_time:end_time]
        chunk_file_path = f'{base_name}_chunk_{i}.mp3'
        logger.debug(f'Processing chunk: {chunk_file_path}')
        if not os.path.exists(chunk_file_path):
            logger.debug(f'Exporting: {chunk_file_path}')
            chunk.export(chunk_file_path, format='mp3')
        else:
            logger.debug(f'Found existing chunk: {chunk_file_path}')
        chunk_files.append(chunk_file_path)

    def transcribe_audio(file_path):
        logger.debug(f"Transcribing: {file_path}")
        with open(file_path, 'rb') as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript

    transcripts = []
    for chunk_file in chunk_files:
        transcript = transcribe_audio(chunk_file)
        print(transcript)  # Always print intermediate transcripts
        transcripts.append(transcript)
        os.remove(chunk_file)

    full_transcript = '\n'.join(transcripts)

    output_file = f"{base_name}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_transcript)

    logger.info(f"Full transcript saved to {output_file}")

    for chunk_file in chunk_files:
        if os.path.exists(chunk_file):
            os.remove(chunk_file)

def youtube_to_transcript(source_url, base_name=''):
    logger.info("Downloading and converting YouTube video to audio...")
    audio_file = yt_url_to_audio(source_url, base_name)
    logger.info(f"Audio downloaded: {audio_file}")
    logger.info("Transcribing audio...")
    mp3_to_transcript(audio_file, base_name)

def main():
    parser = argparse.ArgumentParser(description="Transcript Utility")
    parser.add_argument('action', choices=['y2a', 'a2t', 'y2t'],
                        help="Action to perform: y2a (YouTube to Audio), a2t (Audio to Transcript), or y2t (YouTube to Transcript)")
    parser.add_argument('source', help="YouTube URL or audio file path")
    parser.add_argument('base_name', nargs='?', default='', help="Base name for output files (optional)")

    args = parser.parse_args()

    if args.action == 'y2a':
        audio_file = yt_url_to_audio(args.source, args.base_name)
        logger.info(f"Audio downloaded: {audio_file}")
        if input("Do you want to transcribe this audio? (y/n): ").lower() == 'y':
            mp3_to_transcript(audio_file, args.base_name)
    elif args.action == 'a2t':
        mp3_to_transcript(args.source, args.base_name)
    elif args.action == 'y2t':
        youtube_to_transcript(args.source, args.base_name)

if __name__ == '__main__':
    main()