import os
import shutil
import openai
from pytube import YouTube
from pydub import AudioSegment


class YouTubeTranscript:
    def __init__(self, url, output_name, open_api_key=''):
        self.url = url
        self.output_name = output_name
        self.output_transcript = f'{output_name}.txt'
        if not os.path.exists(output_name):
            os.makedirs(output_name)
            os.makedirs(os.path.join(output_name, 'chunks'))
        self.audio = f'{output_name}/{output_name}'
        self.audio_file_name = f'{self.audio}.wav'
        openai.api_key = os.environ.get('OPENAI_API_KEY') or open_api_key

    def get_transcript(self, chunk_second=100):
        input_audio = self.get_input_audio()
        transcript = ''
        chunks = self.get_chunks_by_seconds(input_audio, chunk_second)
        for i, chunk in enumerate(chunks):
            chunk_transcript_path = f'{self.output_name}/chunks/{self.output_name}_chunk{i}.txt'
            exists = os.path.exists(chunk_transcript_path)
            print(f'Finding {chunk_transcript_path}', exists)
            if not exists:
                chunk_audio = self.get_chunk_file(i, chunk)
                if not chunk_audio:
                    break
                chunk_transcript = self.transcribe(chunk_audio, chunk_transcript_path)
            else:
                chunk_transcript = self.read_transcript(chunk_transcript_path)
            transcript += chunk_transcript
        if transcript:
            with open(self.output_transcript, 'w') as f:
                f.write(transcript)
            print(f'Saved transcript to {self.output_transcript}')
        return transcript

    def get_input_audio(self):
        if not os.path.exists(self.audio):
            yt = YouTube(self.url)
            audio_stream = yt.streams.filter(only_audio=True).first()
            print(f'Downloading {self.audio} from {self.url}')
            audio_stream.download(output_path=self.output_name, filename=self.output_name)
        if not os.path.exists(self.audio_file_name):
            print(f'Exporting {self.audio_file_name} from {self.audio}')
            input_audio = AudioSegment.from_file(self.audio)
            input_audio.export(self.audio_file_name, format='wav')
        print(f'Opening {self.audio_file_name}')
        input_audio = AudioSegment.from_wav(self.audio_file_name)
        return input_audio

    def get_chunks_by_seconds(self, full_data, chunk_second):
        chunk_size = chunk_second * 1000
        chunks = [full_data[i:i+chunk_size] for i in range(0, len(full_data), chunk_size)]
        print(f'Dividing the file into {len(chunks)} {chunk_second}-second chunks')
        return chunks

    def get_chunk_file(self, i, chunk):
        prefix_name = f'{self.output_name}/chunks/{self.output_name}_chunk{i}'
        full_name = f'{prefix_name}.wav'
        if not os.path.exists(full_name):
            print(f'Exporting new chunk file {full_name}')
            chunk_file = chunk.export(prefix_name, format='wav')
        else:
            print(f'Opening existing chunk file {full_name}')
            chunk_file = open(full_name, 'rb')
        return chunk_file

    def transcribe(self, input_audio, output_file):
        with input_audio as f:
            result = openai.Audio.transcribe('whisper-1', f)
            text = result['text']
            with open(output_file, 'w') as f:
                f.write(text)
            print('Transcribed:', text)
            return text

    def read_transcript(self, path):
        with open(path, 'r') as f:
            text = f.read()
            print('Transcript:', text)
            return text

    def clean(self):
        shutil.rmtree(self.output_name)