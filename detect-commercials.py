import getopt
import glob
import os
import subprocess
import sys
import datetime
import re


def print_usage():
    print('Usage: detect-commercials.py -r [input file.mp4 or directory]')


def get_video_length(input_video):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
         input_video], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return str(datetime.timedelta(seconds=float(result.stdout)))


def timestamp_to_timebase(timestamp):
    if timestamp == "00:00:00":
        return 0
    x = re.match(r"(\d+):(\d{2}):(\d{2})", timestamp)
    hrs = int(x.group(1))
    mins = int(x.group(2))
    secs = int(x.group(3))
    minutes = (hrs * 60) + mins
    seconds = secs + (minutes * 60)
    timestamp = (seconds * 1000)
    return timestamp


def parse_commercials(video_file):
    # Ensure file is a video file
    ext = os.path.splitext(video_file)
    if ext[1] not in [".mp4", ".mkv", ".ts"]:
        print('Not a video file: ' + video_file)
        return

    # Look for corresponding srt file in the directory
    dirname = os.path.dirname(video_file)
    srt_files = glob.glob(os.path.join(dirname, ext[0] + '*.srt'))

    # Make sure srt file exists
    if not srt_files:
        print('Could not find .srt file for : ' + video_file)
        return

    print("Processing " + video_file)

    srt_file = srt_files[0]
    commercial_found = False
    commercials = []

    # Read srt file
    with open(srt_file) as f:
        for line in f:
            # Found commercial
            if line.startswith("X-TIMESTAMP-MAP=MPEGTS"):
                commercial_found = True
                continue
            # Found timestamp for commercial
            if commercial_found and " --> " in line:
                # Add timestamps to commercials array
                commercials.append(line.rstrip().split(" --> "))
                commercial_found = False
                continue

    # Find video length (hh:mm:ss.ss)
    video_length = get_video_length(video_file)

    # Now turn these commercial breaks into chapters
    chapters = []

    for index, commercial in enumerate(commercials):
        # First chapter always needs to start with 00:00:00
        if index == 0:
            # Add the first chapter, goes from 00:00:00 -> first commercial start
            chapters.append(('00:00:00', commercial[0]))

        if index + 1 < len(commercials):
            next_commercial = commercials[index + 1]
            chapters.append((commercial[0], next_commercial[0]))
        else:
            # No more commercials, next chapter ends at the end of the video
            chapters.append((commercial[0], video_length))

    print(chapters)

    # Convert chapters to ffmpeg format
    ffmpeg_metadata = ";FFMETADATA1\n"

    for index, chapter in enumerate(chapters):
        start = timestamp_to_timebase(chapter[0])
        end = timestamp_to_timebase(chapter[1])
        title = "Chapter " + str(index + 1)
        ffmpeg_metadata += f"""
[CHAPTER]
TIMEBASE=1/1000
START={start}
END={end}
title={title}
"""
    # Write to file
    metadata_file_path = os.path.join(dirname, ext[0] + "_METADATA.txt")
    metadata_file = open(metadata_file_path, "w")
    metadata_file.write(ffmpeg_metadata)
    metadata_file.close()

    # Add to video
    video_file_temp = os.path.join(dirname, ext[0] + "_TEMP" + ext[1])
    subprocess.run(
        ['ffmpeg', '-i', video_file, '-i', metadata_file_path, '-map_metadata', '1', '-codec', 'copy',
         '-movflags', '+faststart', video_file_temp],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Remove metadata file
    os.remove(metadata_file_path)

    # Delete old video file
    os.remove(video_file)

    # Rename new video file
    os.rename(video_file_temp, video_file)


# Search recursive in directory
recursive = False

# Parse arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "hr")
except getopt.GetoptError:
    print_usage()
    sys.exit(2)

# Make sure a file name is given
if not args:
    print_usage()
    sys.exit(2)

target_file = args[0]

for opt, arg in opts:
    if opt == '-h':
        print_usage()
        sys.exit()
    elif opt == "-r":
        recursive = True

# Test if ffmpeg and ffprobe exists
try:
    subprocess.run(['ffmpeg'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
except FileNotFoundError:
    print("ffmpeg must be installed in your PATH")
    sys.exit(2)
try:
    subprocess.run(['ffprobe'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
except FileNotFoundError:
    print("ffprobe must be installed in your PATH")
    sys.exit(2)

if recursive:
    # Ensure target is a directory
    if not os.path.isdir(target_file):
        print("Path must be a directory if using -r")
        sys.exit(2)
    # Loop directory
    for root, dirs, files in os.walk(target_file):
        for file in files:
            parse_commercials(os.path.join(root, file))
else:
    parse_commercials(target_file)
