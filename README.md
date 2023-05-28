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

# Important Notice
**Legal and Responsible Usage of the YouTube Video Download Utility**:

It's important to emphasize that the utility I provided should only be used to download YouTube videos in compliance with YouTube's terms of service and applicable copyright laws. Before downloading any video, ensure that you have explicit permission from the video owner or that the video is licensed under a permissive Creative Commons license or similar open license.

Downloading videos from YouTube without permission from the content owner is generally prohibited and may infringe upon their rights. YouTube's terms of service explicitly state that users should not access, reproduce, download, distribute, or create derivative works from the content available on their platform, unless explicitly permitted by YouTube or the content owner.

Always respect the intellectual property rights of others and use this utility responsibly and legally.

# License
This utility is distributed under the MIT License.