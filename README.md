# Discovery+ Commercial Detector

Detects commercial breaks in TV Shows downloaded from Discovery+, and adds them as chapters.

This script is primarily for users of [ErsatzTV](https://ersatztv.org/), but it may also suit your own use case.

## Usage
Add chapters to a single video:
```
python detect-commercials.py "file.mp4"
```
Add chapters to all videos in a directory:
```
python detect-commercials.py -r "/mnt/videos"
```

## How does this work?
This script requires subtitles to be downloaded along with your TV shows. 

Discovery+ seems to be adding the text `X-TIMESTAMP-MAP=MPEGTS:900000,LOCAL:00:00:00.000` to the subtitle file whenever a commercial is to be inserted. This script detects those entries and adds their related timestamps to the video file's metadata as chapters.