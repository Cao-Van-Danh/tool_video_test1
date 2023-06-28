import os
import tkinter as tk
from tkinter import filedialog
import random
import subprocess
import pysrt
import shutil
import ffmpeg


# FFMPEG processing functions
def process_subtitles(srt_path):
    subs = pysrt.open(srt_path, encoding="utf-8")
    return [(sub.start.ordinal, sub.end.ordinal) for sub in subs]


def get_video_bitrate(video_file):
    command = f"ffprobe -v error -select_streams v:0 -show_entries stream=bit_rate -of default=noprint_wrappers=1:nokey=1 {video_file}"
    result = subprocess.check_output(command, shell=True)
    bitrate = int(result)
    return bitrate


def process_videos(video_folder, timecodes, cache_folder):
    output_files = []
    last_video = None

    for idx, (start, end) in enumerate(timecodes):
        videos = [
            os.path.join(video_folder, file)
            for file in os.listdir(video_folder)
            if file.endswith(".mp4")
        ]

        if last_video and last_video in videos:
            videos.remove(
                last_video
            )  # Ensure the same video is not chosen consecutively

        if not videos:
            log_error("No video files found in the video folder", cache_folder)
            break

        video = random.choice(videos)  # Choose a random video from the list
        last_video = video  # Store the last video chosen

        # Calculate random start offset
        start_offset = min(
            random.randint(0, 300), (end - start)
        )  # Random value between 0 and 3 seconds (in milliseconds), but not exceeding the timecode span

        output_file = os.path.join(cache_folder, f"{idx:03}.mp4")

        # Cut the re-encoded video
        command = f"ffmpeg -i {video} -ss {start_offset/1000} -to {(end - start + start_offset)/1000} -c:v libx264 -preset ultrafast -threads 4 -c:a aac {output_file}"
        subprocess.run(command, shell=True)

        output_files.append(output_file)

    return output_files


def merge_videos(video_files, cache_folder, output_file):
    video_list_file = os.path.join(cache_folder, "video_list.txt")

    with open(video_list_file, "w") as f:
        for video_file in video_files:
            f.write(f"file '{video_file}'\n")

    command = f"ffmpeg -f concat -safe 0 -i {video_list_file} -c copy {output_file}"
    subprocess.run(command, shell=True)

    return output_file


def extract_audio(video_file, output_file):
    stream = ffmpeg.input(video_file)
    stream = ffmpeg.output(stream.audio, output_file)
    ffmpeg.run(stream)


def add_audio(video_file, audio_folder, cache_folder):
    audio_files = [
        os.path.join(audio_folder, file)
        for file in os.listdir(audio_folder)
        if file.endswith(".mp3")
    ]
    if not audio_files:
        log_error("No audio files found in the audio folder", cache_folder)
        return None

    audio_file = random.choice(audio_files)
    output_file = os.path.join(cache_folder, "video_with_audio.mp4")
    command = f"ffmpeg -i {video_file} -i {audio_file} -c:v copy -c:a aac -strict experimental -map 0:v:0 -map 1:a:0 {output_file}"
    subprocess.run(command, shell=True)

    return output_file


def add_subs(video_with_audio, srt_file, cache_folder):
    output_file = os.path.join(cache_folder, "video_with_subs.mp4")
    command = f"ffmpeg -i '{video_with_audio}' -vf subtitles='{srt_file}' -c:v libx264 -crf 23 -c:a aac -strict experimental '{output_file}'"
    subprocess.run(command, shell=True)

    return output_file


def add_music(video_file, music_folder, cache_folder, output_file):
    music_files = [
        os.path.join(music_folder, file)
        for file in os.listdir(music_folder)
        if file.endswith(".mp3")
    ]
    if not music_files:
        log_error("No music files found in the music folder", cache_folder)
        return None

    music_file = random.choice(music_files)
    command = f"ffmpeg -i {video_file} -i {music_file} -filter_complex '[0:a][1:a]amix=inputs=2:duration=shortest' -c:v copy {output_file}"
    subprocess.run(command, shell=True)

    return output_file


def log_error(error_message, cache_folder):
    log_file = os.path.join(cache_folder, "Log.txt")
    with open(log_file, "a") as f:
        f.write(error_message + "\n")


def select_folder(label):
    folder = filedialog.askdirectory()
    label.config(text=folder)


def process(
    video_folder, srt_folder, audio_folder, music_folder, cache_folder, output_folder
):
    timecodes = process_subtitles(os.path.join(srt_folder, "subtitles.srt"))
    video_files = process_videos(video_folder, timecodes, cache_folder)
    merged_video = merge_videos(
        video_files, cache_folder, os.path.join(cache_folder, "merged.mp4")
    )
    video_with_audio = add_audio(merged_video, audio_folder, cache_folder)
    if video_with_audio:
        extracted_audio = os.path.join(cache_folder, "extracted_audio.aac")
        extract_audio(video_with_audio, extracted_audio)
        video_with_subs = add_subs(
            video_with_audio, os.path.join(srt_folder, "subtitles.srt"), cache_folder
        )
        if video_with_subs:
            final_video = os.path.join(output_folder, "final.mp4")
            shutil.move(video_with_subs, final_video)
            print(f"Final video saved to: {final_video}")


root = tk.Tk()
root.title("Video Processing Tool")

video_label = tk.Label(root, text="Video folder")
video_label.pack()
video_button = tk.Button(
    root, text="Select video folder", command=lambda: select_folder(video_label)
)
video_button.pack()

srt_label = tk.Label(root, text="SRT folder")
srt_label.pack()
srt_button = tk.Button(
    root, text="Select SRT folder", command=lambda: select_folder(srt_label)
)
srt_button.pack()

audio_label = tk.Label(root, text="Audio folder")
audio_label.pack()
audio_button = tk.Button(
    root, text="Select audio folder", command=lambda: select_folder(audio_label)
)
audio_button.pack()

music_label = tk.Label(root, text="Music folder")
music_label.pack()
music_button = tk.Button(
    root, text="Select music folder", command=lambda: select_folder(music_label)
)
music_button.pack()

cache_label = tk.Label(root, text="Cache folder")
cache_label.pack()
cache_button = tk.Button(
    root, text="Select cache folder", command=lambda: select_folder(cache_label)
)
cache_button.pack()

output_label = tk.Label(root, text="Output folder")
output_label.pack()
output_button = tk.Button(
    root, text="Select output folder", command=lambda: select_folder(output_label)
)
output_button.pack()

process_button = tk.Button(
    root,
    text="Process",
    command=lambda: process(
        video_label.cget("text"),
        srt_label.cget("text"),
        audio_label.cget("text"),
        music_label.cget("text"),
        cache_label.cget("text"),
        output_label.cget("text"),
    ),
)
process_button.pack()

root.mainloop()
