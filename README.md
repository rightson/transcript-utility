# Transcript Utility

This utility allows you to download audio from YouTube videos and generate transcripts. It supports incremental processing and can handle interruptions gracefully.

**Dependencies**:
- OpenAI API (for transcription)
- yt-dlp (for YouTube video download)
- pydub (for audio processing)

**Prerequisites**:
Ensure that your OpenAI API key is set as the `OPENAI_API_KEY` environment variable.

**Installation**:
```
pip install openai yt-dlp pydub
```

**Usage**:
The script supports three modes of operation:

1. YouTube to Audio (y2a):
```
python transcript_utility.py y2a <YT_URL> [BASE_NAME]
```

2. Audio to Transcript (a2t):
```
python transcript_utility.py a2t <AUDIO_FILE_PATH> [BASE_NAME]
```

3. YouTube to Transcript (y2t):
```
python transcript_utility.py y2t <YT_URL> [BASE_NAME]
```

If `BASE_NAME` is not provided, it will be derived from the source URL or file name.

**Examples**:

1. Download audio from a YouTube video:
```
python transcript_utility.py y2a https://www.youtube.com/watch?v=rC2hBUhOqag gooaye-ep352
```

2. Transcribe an existing audio file:
```
python transcript_utility.py a2t gooaye-ep352/gooaye-ep352.mp3
```

3. Download a YouTube video and generate a transcript in one go:
```
python transcript_utility.py y2t https://www.youtube.com/watch?v=8p0oCUE3mWE jenson-2023-ntu-commencement
```

**Output**:
All output files, including the downloaded audio, intermediate chunks, and the final transcript, are saved in a folder named after the `BASE_NAME`. The final transcript is saved as `{BASE_NAME}.txt` within this folder.

**Incremental Processing**:
The utility supports incremental processing. If the script is interrupted, you can rerun the command, and it will resume from where it left off.

**Logging**:
You can control the verbosity of the output by setting the `LOG_LEVEL` environment variable:
```
LOG_LEVEL=debug python transcript_utility.py ...
```

# Important Notice
**Legal and Responsible Usage of the YouTube Video Download Utility**:

It's important to emphasize that this utility should only be used to download YouTube videos in compliance with YouTube's terms of service and applicable copyright laws. Before downloading any video, ensure that you have explicit permission from the video owner or that the video is licensed under a permissive Creative Commons license or similar open license.

Downloading videos from YouTube without permission from the content owner is generally prohibited and may infringe upon their rights. YouTube's terms of service explicitly state that users should not access, reproduce, download, distribute, or create derivative works from the content available on their platform, unless explicitly permitted by YouTube or the content owner.

Always respect the intellectual property rights of others and use this utility responsibly and legally.

# License
This utility is distributed under the MIT License.