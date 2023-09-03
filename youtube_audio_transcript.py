import os
import sys
import argparse
import logging
import shutil
import openai
from pathlib import Path
from pydub import AudioSegment
from pytube import YouTube

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level if log_level in {
                    'INFO', 'DEBUG'} else 'INFO')


class AudioTranscript:
    def __init__(self, source, output_name, open_api_key=''):
        self.source = source
        self.output_dir = Path(output_name)
        self.transcript_path = Path.cwd() / f'{output_name}.txt'
        self.output_prefix = self.output_dir / output_name
        self.chunk_dir = self.output_dir / 'chunks'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_dir.mkdir(parents=True, exist_ok=True)
        openai.api_key = os.environ.get('OPENAI_API_KEY', open_api_key)

    def get_transcript(self, wav_path=None, start_time=None, end_time=None, chunk_duration_in_sec=100, no_clean_up=True):
        if self.transcript_path.exists():
            return self.transcript_path.open().read()

        input_audio = self._get_input_audio(wav_path)
        start_time = self.convert_time_to_seconds(start_time) * 1000 if start_time is not None else None
        end_time = self.convert_time_to_seconds(end_time) * 1000 if end_time is not None else None
        input_audio = input_audio[start_time:end_time]

        chunks = self._split_audio_into_chunks(input_audio, chunk_duration_in_sec)
        transcript = self._generate_transcript(chunks)

        if transcript:
            self.transcript_path.write_text(transcript)
            logging.info(f'Saved transcript to {self.transcript_path}')
            if not no_clean_up:
                self._clean()
            print(transcript)

        return transcript

    def _clean(self):
        shutil.rmtree(self.output_dir)

    def _get_input_audio(self, wav_path=None):
        audio_path = wav_path if wav_path else self.output_prefix.with_suffix('.wav')            
        logging.info(f'Opening {audio_path}')
        return AudioSegment.from_wav(audio_path)

    def _split_audio_into_chunks(self, full_audio, chunk_duration_in_sec):
        chunk_size = chunk_duration_in_sec * 1000
        chunks = [full_audio[i:i + chunk_size]
                  for i in range(0, len(full_audio), chunk_size)]

        logging.info(f'Divided the file into {len(chunks)} chunks of {chunk_duration_in_sec} seconds each.')
        return chunks

    def _generate_transcript(self, chunks):
        transcript = ''
        for i, chunk in enumerate(chunks):
            chunk_file_path = self.chunk_dir / f'{self.output_dir.name}_chunk{i}.wav'
            transcript_file_path = self.chunk_dir / f'{self.output_dir.name}_chunk{i}.txt'

            if transcript_file_path.exists():
                transcript_chunk = self._read_transcript(transcript_file_path)
            else:
                self._export_chunk_to_file(chunk, chunk_file_path)
                transcript_chunk = self._transcribe_audio_chunk(chunk_file_path, transcript_file_path)

            transcript += transcript_chunk

        return transcript

    def _export_chunk_to_file(self, chunk, chunk_file_path):
        if not chunk_file_path.exists():
            logging.info(f'Exporting new chunk file {chunk_file_path}')
            chunk.export(chunk_file_path, format='wav')
        else:
            logging.info(f'Opening existing chunk file {chunk_file_path}')

    def _transcribe_audio_chunk(self, chunk_file_path, transcript_file_path):
        with open(chunk_file_path, 'rb') as audio_file:
            transcription_result = openai.Audio.transcribe('whisper-1', audio_file)
            transcript_text = transcription_result['text']
            transcript_file_path.write_text(transcript_text)
            logging.info('Transcribed:' + transcript_text)
            return transcript_text

    def _read_transcript(self, transcript_file_path):
        transcript_text = transcript_file_path.read_text()
        logging.info('Transcript: ' + transcript_text)
        return transcript_text

    def convert_time_to_seconds(self, time_str):
        if ':' in time_str:  # time is in "minute:second" format
            minutes, seconds = map(int, time_str.split(':'))
            return minutes * 60 + seconds
        else:  # time is in seconds
            return int(time_str)

class YouTubeAudioTranscript(AudioTranscript):
     def _get_input_audio(self, wav_path=None):
        audio_path = wav_path if wav_path else self.output_prefix.with_suffix('.wav')            

        if not audio_path.exists():
            yt = YouTube(self.source)
            audio_stream = yt.streams.filter(only_audio=True).first()

            logging.info(f'Downloading {self.output_prefix} from {self.source}')
            audio_stream.download(
                output_path=self.output_dir, filename=self.output_prefix.name)

            logging.info(f'Exporting {audio_path} from {self.output_prefix}')
            input_audio = AudioSegment.from_file(self.output_prefix)
            input_audio.export(audio_path, format='wav')

        logging.info(f'Opening {audio_path}')
        return AudioSegment.from_wav(audio_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=str)
    parser.add_argument('output_name', type=str, default='work-temp')
    parser.add_argument('--no_clean_up', action='store_true')
    args = parser.parse_args()
    if not args.source or not args.output_name:
        parser.print_usage()
        sys.exit(0)

    if os.path.exists(args.source):
        AudioTranscript(
            args.source, 
            args.output_name).get_transcript(
                wav_path=args.source, no_clean_up=args.no_clean_up)
    else:
        YouTubeAudioTranscript(
            args.source, 
            args.output_name).get_transcript(no_clean_up=args.no_clean_up)