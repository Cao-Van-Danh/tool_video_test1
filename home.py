import os
import tkinter as tk
from tkinter import filedialog
import random
import subprocess
import shutil
import re
import json

# Đường dẫn tới file FFMPEG.exe
ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"


def process_subtitles(srt_path, cache_folder):
    with open(srt_path, "r") as file:
        srt_content = file.read()
    timecodes = []
    lines = srt_content.split("\n")
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if re.match(r"^\d+$", line):
            index += 1
            timecode_line = lines[index].strip()
            timecode_match = re.match(
                r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s-->\s(\d{2}):(\d{2}):(\d{2}),(\d{3})$",
                timecode_line,
            )
            if timecode_match:
                (
                    start_hour,
                    start_minute,
                    start_second,
                    start_millisecond,
                    end_hour,
                    end_minute,
                    end_second,
                    end_millisecond,
                ) = timecode_match.groups()
                start_time = (
                    int(start_hour) * 3600000
                    + int(start_minute) * 60000
                    + int(start_second) * 1000
                    + int(start_millisecond)
                )
                end_time = (
                    int(end_hour) * 3600000
                    + int(end_minute) * 60000
                    + int(end_second) * 1000
                    + int(end_millisecond)
                )
                if timecodes:
                    timecodes[-1][1] = start_time
                timecodes.append([start_time, end_time])
            index += 2
        else:
            index += 1

    if timecodes:
        timecodes[0][0] = 0

    if timecodes:
        timecodes[-1][1] += 5000

    with open(os.path.join(cache_folder, "timecodes.json"), "w") as f:
        json.dump(timecodes, f)

    return timecodes


def get_video_bitrate(video_file):
    command = f'{ffmpeg_path} -v error -select_streams v:0 -show_entries stream=bit_rate -of default=noprint_wrappers=1:nokey=1 "{video_file}"'
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
            videos.remove(last_video)

        if not videos:
            log_error("No video files found in the video folder", cache_folder)
            break

        video = random.choice(videos)
        last_video = video

        start_offset = min(random.randint(0, 300), (end - start))

        output_file = os.path.join(cache_folder, f"{idx:03}.mp4")

        command = f'{ffmpeg_path} -i "{video}" -ss {start_offset/1000} -to {(end - start + start_offset)/1000} -c:v libx264 -preset ultrafast -threads 4 -c:a aac "{output_file}"'
        subprocess.run(command, shell=True)

        output_files.append(output_file)

    return output_files


def merge_videos(video_files, cache_folder, output_file):
    video_list_file = os.path.join(cache_folder, "video_list.txt")

    with open(video_list_file, "w") as f:
        for video_file in video_files:
            f.write(f"file '{video_file}'\n")

    command = f'{ffmpeg_path} -f concat -safe 0 -i "{video_list_file}" -c copy "{output_file}"'
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
    command = f'{ffmpeg_path} -i "{video_file}" -i "{audio_file}" -c:v copy -c:a aac -strict experimental "{output_file}"'
    subprocess.run(command, shell=True)

    return output_file


def add_subs(video_file, srt_file, cache_folder):
    srt_path = "output_video.srt"
    output_file = os.path.join(cache_folder, "output_video.mp4")

    # Kiểm tra nếu srt_file và srt_path khác nhau mới thực hiện sao chép
    if srt_file != srt_path:
        shutil.copy2(srt_file, srt_path)

    command = (
        f'{ffmpeg_path} -i "{video_file}" -vf subtitles="{srt_path}" "{output_file}"'
    )
    subprocess.run(command, shell=True)

    return output_file


def add_music(video_file, music_folder, output_file):
    music_files = [
        os.path.join(music_folder, file)
        for file in os.listdir(music_folder)
        if file.endswith(".mp3")
    ]
    if not music_files:
        log_error("No music files found in the music folder", cache_folder)
        return None

    music_file = random.choice(music_files)
    command = f'{ffmpeg_path} -i "{video_file}" -i "{music_file}" -filter_complex "[0:a][1:a]amix=inputs=2:duration=shortest" -c:v copy "{output_file}"'
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
    srt_files = [file for file in os.listdir(srt_folder) if file.endswith(".srt")]
    if not srt_files:
        log_error("No SRT files found in the SRT folder", cache_folder)
        return

    for srt_file in srt_files:
        srt_path = os.path.join(srt_folder, srt_file)
        timecodes = process_subtitles(srt_path, cache_folder)

        # Copy file phụ đề vào thư mục cache
        cache_srt_path = os.path.join(cache_folder, "video_with_audio.srt")
        shutil.copy2(srt_path, cache_srt_path)

        video_files = process_videos(video_folder, timecodes, cache_folder)
        merged_video = merge_videos(
            video_files, cache_folder, os.path.join(cache_folder, "merged.mp4")
        )
        video_with_audio = add_audio(merged_video, audio_folder, cache_folder)
        if video_with_audio:
            video_with_subs = add_subs(
                video_with_audio, srt_path, cache_folder
            )  # Thêm đối số cache_folder vào đây
            if video_with_subs:
                final_video = add_music(
                    video_with_subs,
                    music_folder,
                    os.path.join(
                        cache_folder, f"final_{os.path.splitext(srt_file)[0]}.mp4"
                    ),
                )
                if final_video and os.path.exists(
                    final_video
                ):  # Ensure the file exists before renaming
                    os.rename(
                        final_video,
                        os.path.join(
                            output_folder, f"final_{os.path.splitext(srt_file)[0]}.mp4"
                        ),
                    )


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
