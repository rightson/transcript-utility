# YouTube Transcript Generator

**Dependencies**: ChatGPT API.

**Prerequisites**: Ensure that your OpenAI API key is set as the `OPENAI_API_KEY` environment variable.

**Usage**:
```py
from youtube_audio_transcript import YouTubeAudioTranscript

url = 'https://www.youtube.com/watch?v=8p0oCUE3mWE'
output_name = 'jenson-2023-ntu-commencement'

yat = YouTubeAudioTranscript(url, output_name)

# Optional start_time and end_time parameters in seconds or "minutes:seconds" format
start_time = '16:10'  # Start at 16 minutes 10 seconds
end_time = '39:00'  # End at 39 minutes

yat.get_transcript(start_time=start_time, end_time=end_time)
```

Using the `yat` object, the video from the specified URL is downloaded into a folder named `output_name`. All intermediate files generated during the process are saved within this folder. The final transcript is stored as `{output_name}.txt` in the working directory.

The `start_time` and `end_time` parameters allow you to specify a segment of the video to transcribe. You can specify these times in seconds or as a string in the format "minutes:seconds". If these parameters are not provided, the entire video will be transcribed.

The `yat` object supports incremental transcription. If `yat.get_transcript()` gets interrupted unexpectedly, you can re-run the command and the transcription will resume where it left off.

Upon successful completion of the transcription, you can call `yat.clean()` to remove all intermediate files. Be aware, however, that once `yat.clean()` is called, all the intermediate files will be removed and the incremental transcription process will be reset.

```py
yat.clean()
```

# License
This utility is distributed under the MIT License.