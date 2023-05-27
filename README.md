# YouTube Transcript Generator

**Dependencies**: ChatGPT API.

**Prerequisites**: Ensure that your OpenAI API key is set as the `OPENAI_API_KEY` environment variable.

**Usage**:
```py
from youtube_audio_transcript import YouTubeAudioTranscript

url = 'https://www.youtube.com/watch?v=8p0oCUE3mWE'
output_name = 'jenson-2023-ntu-commencement'

yat = YouTubeAudioTranscript(url, output_name)
yat.get_transcript()
```

Using the `yat` object, the video from the provided URL is downloaded with the name specified in `output_name`, and the transcript is saved as `{output_name}.txt`.

The `yat` object supports incremental transcription. If `yat.get_transcript()` gets interrupted unexpectedly, you can re-run the command and the transcription will resume where it left off.

Upon successful completion of the transcription, you can call `yat.clean()` to remove all intermediate files. Be aware, however, that once `yat.clean()` is called, all the intermediate files will be removed and the incremental transcription process will be reset.

```py
yat.clean()
```

# License
This utility is distributed under the MIT License.
