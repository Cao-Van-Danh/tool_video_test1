import os
import random
import subprocess

# Đường dẫn đến các thư mục input và output
video_input_folder = "VideoInput/"
mp3_audio_folder = "Mp3Audio/"
audio_voice_folder = "AudioVoice/"
srt_voice_folder = "SrtVoice/"
cache_folder = "Cache/"
output_folder = "Output/"

# Đọc danh sách các file Srt từ thư mục SrtVoice
def read_srt_files():
    srt_files = []
    srt_voice_path = os.path.join(os.getcwd(), srt_voice_folder)
    if os.path.exists(srt_voice_path):
        for file_name in os.listdir(srt_voice_path):
            if file_name.endswith(".srt"):
                srt_files.append(os.path.join(srt_voice_path, file_name))
    else:
        print(f"Thư mục '{srt_voice_folder}' không tồn tại.")
    return srt_files

# Đọc danh sách timecode từ file Srt
def extract_timecodes(srt_file):
    timecodes = []
    with open(srt_file, "r") as file:
        lines = file.readlines()
        for line in lines:
            line = line.strip()
            if line.isdigit():
                timecodes.append(line)
    return timecodes

# Chọn ngẫu nhiên một file video từ thư mục VideoInput
def get_random_video():
    video_files = [file for file in os.listdir(video_input_folder) if file.endswith((".mp4", ".avi", ".mkv"))]
    random_video = random.choice(video_files)
    return os.path.join(video_input_folder, random_video)

# Cắt video thành đoạn thời gian cụ thể
def cut_video(input_file, output_file, start_time, end_time):
    subprocess.call([
        "ffmpeg",
        "-i", input_file,
        "-ss", start_time,
        "-to", end_time,
        "-c", "copy",
        "-avoid_negative_ts", "1",
        output_file
    ])

# Ghép video từ các đoạn video đã cắt
def concat_videos(input_files, output_file):
    with open("concat.txt", "w") as file:
        for i, file_path in enumerate(input_files):
            file.write(f"file '{file_path}'\n")
        subprocess.call([
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", "concat.txt",
            "-c", "copy",
            "-avoid_negative_ts", "1",
            output_file
        ])
    os.remove("concat.txt")

# Ghép audio voice vào video
def merge_audio_video(video_file, audio_file, output_file):
    subprocess.call([
        "ffmpeg",
        "-i", video_file,
        "-i", audio_file,
        "-c", "copy",
        "-map", "0:v",
        "-map", "1:a",
        "-shortest",
        output_file
    ])

# Ghép nội dung của file Srt vào video
def merge_subtitle_video(video_file, subtitle_file, output_file, position, font_size, font_color):
    subprocess.call([
        "ffmpeg",
        "-i", video_file,
        "-vf", f"subtitles='{subtitle_file}':force_style='Fontsize={font_size},PrimaryColour=&H{font_color[1:]}',drawtext=fontfile=arial.ttf:fontsize={font_size}:fontcolor={font_color}:x={position[0]}:y={position[1]}",
        "-c:a", "copy",
        output_file
    ])

# Ghép audio vào video
def merge_audio_video(video_file, audio_file, output_file, audio_volume):
    subprocess.call([
        "ffmpeg",
        "-i", video_file,
        "-i", audio_file,
        "-filter_complex", f"[0:a]volume={audio_volume}[v];[1:a]volume=1[a];[v][a]amix=inputs=2",
        "-c:v", "copy",
        "-map", "0:v",
        "-map", "[a]",
        output_file
    ])

# Tạo thư mục nếu chưa tồn tại
def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Xóa các file trong thư mục cache
def clear_cache():
    for file_name in os.listdir(cache_folder):
        file_path = os.path.join(cache_folder, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

# Bước 1: Đọc file Srt để lấy ra danh sách timecode từng dòng nội dung
srt_files = read_srt_files()
timecodes = []
for srt_file in srt_files:
    timecodes.extend(extract_timecodes(srt_file))

# Bước 2: Cắt các video ngẫu nhiên từ VideoInput và lưu vào Cache
clear_cache()
for i, timecode in enumerate(timecodes):
    video_file = get_random_video()
    output_file = os.path.join(cache_folder, f"{str(i+1).zfill(3)}.mp4")
    cut_video(video_file, output_file, "00:00:00", timecode)

# Bước 3: Ghép các video đã cắt thành một video dài trong Cache
concatenated_video = os.path.join(cache_folder, "VideoGhep.mp4")
concat_videos(sorted(os.listdir(cache_folder)), concatenated_video)

# Bước 4: Ghép audio voice vào video đã ghép trong Cache
audio_file = os.path.join(audio_voice_folder, os.path.splitext(os.path.basename(srt_files[0]))[0] + ".mp3")
video_voice = os.path.join(cache_folder, "VideoVoice.mp4")
merge_audio_video(concatenated_video, audio_file, video_voice)

# Bước 5: Ghép nội dung của file Srt vào video đã ghép trong Cache
subtitle_file = srt_files[0]
video_srt = os.path.join(cache_folder, "VideoSrt.mp4")
merge_subtitle_video(video_voice, subtitle_file, video_srt, (100, 100), 24, "#FF0000")

# Bước 6: Ghép audio vào video cuối cùng và lưu vào thư mục Output
final_audio_file = os.path.join(mp3_audio_folder, random.choice(os.listdir(mp3_audio_folder)))
final_video = os.path.join(output_folder, "Final.mp4")
merge_audio_video(video_srt, final_audio_file, final_video, "0.5")

print("Hoàn thành xử lý video!")
