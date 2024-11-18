import streamlit as st
import requests
import yt_dlp
import os
import subprocess
from pathlib import Path
import re

# Function to sanitize filenames
def sanitize_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

# Function to download video directly
def download_direct_video(url, save_path, progress_callback):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        bytes_downloaded = 0

        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    bytes_downloaded += len(chunk)
                    progress_callback(bytes_downloaded, total_size)
        
        return save_path
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# yt_dlp download function with progress callback
def download_with_ytdlp(url, save_path, progress_callback):
    def yt_dlp_progress_hook(d):
        if d['status'] == 'downloading':
            downloaded_bytes = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes', 1)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

            # Update the progress bar and status text with percentage, speed, and ETA
            progress_callback(downloaded_bytes, total_bytes, speed, eta)

    ydl_opts = {
        'outtmpl': f'{save_path}/%(title)s.%(ext)s',
        'progress_hooks': [yt_dlp_progress_hook],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Function to fix video timestamps
def fix_video_timestamps(input_file, output_file):
    # Ensure input and output are Path objects
    input_file = Path(input_file)
    output_file = Path(output_file)

    # Sanitize filename
    sanitized_name = sanitize_filename(input_file.stem)
    sanitized_output_file = input_file.with_name(f"fixed_{sanitized_name}.mp4")

    try:
        # Run ffmpeg command
        subprocess.run([
            "ffmpeg", "-i", str(input_file), "-c", "copy", str(sanitized_output_file), "-y"
        ], check=True)

        # Replace original file if successful
        os.remove(input_file)
        os.rename(sanitized_output_file, input_file)
        return input_file
    except subprocess.CalledProcessError as e:
        st.error(f"An error occurred while fixing timestamps: {e}")
        return None

# Streamlit UI
st.title("Video Downloader")

# Input box for URL
video_url = st.text_input("Enter the video URL")

# Input box for save directory with validation
save_dir = st.text_input("Enter save directory (e.g., /Users/mushr/Desktop)", value="/Users/mushr/Desktop")

# Validate the save directory
def validate_save_dir(path):
    try:
        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
        return save_path
    except Exception as e:
        st.error(f"Invalid save directory: {e}")
        return None

# Progress bar and status placeholders
progress_bar = st.progress(0)
status_text = st.empty()

# Progress update function
def update_progress_bar(current, total, speed=None, eta=None):
    progress = current / total if total else 0  # Calculate progress as a float between 0 and 1
    progress_bar.progress(min(max(progress, 0.0), 1.0))  # Streamlit expects a value from 0 to 1
    
    # Display percentage, speed, ETA, and total size in MB
    total_size_mb = total / 1024 / 1024 if total else 0
    downloaded_mb = current / 1024 / 1024
    
    # Format ETA to hours, minutes, and seconds
    if eta:
        hours, remainder = divmod(eta, 3600)
        minutes, seconds = divmod(remainder, 60)
        eta_formatted = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    else:
        eta_formatted = "Unknown"
    
    status_text.text(
        f"Download progress: {int(progress * 100)}% | "  # Convert progress to a percentage
        f"Downloaded: {downloaded_mb:.2f} MB / {total_size_mb:.2f} MB | " +
        (f"Speed: {speed / 1024 / 1024:.2f} MB/s | " if speed else "") +
        f"ETA: {eta_formatted}"  # Display formatted ETA
    )

# Download button
if st.button("Get Video"):
    if video_url:
        # Validate and process the save directory
        save_path = validate_save_dir(save_dir)
        if not save_path:
            st.warning("Please enter a valid save directory.")
        else:
            # Check if the URL is a direct link to a video file
            if any(video_url.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv"]):
                video_path = download_direct_video(video_url, save_path / "downloaded_video.mp4", lambda current, total: update_progress_bar(current, total))
            else:
                video_path = download_with_ytdlp(video_url, str(save_path), update_progress_bar)

            # Fix timestamps if a video was downloaded successfully
            if video_path:
                fixed_video_path = save_path / ("fixed_" + os.path.basename(video_path))
                video_path = fix_video_timestamps(video_path, fixed_video_path) or video_path  # Update path if fix successful

                # Notify user of download completion
                st.success("Download completed!")            

    else:
        st.warning("Please enter a video URL.")
