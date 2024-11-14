import streamlit as st
import requests
import yt_dlp
import os
import subprocess
from pathlib import Path

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
    try:
        subprocess.run([
            "ffmpeg", "-i", input_file, "-c", "copy", output_file, "-y"
        ], check=True)
        os.remove(input_file)
        os.rename(output_file, input_file)
        return input_file
    except subprocess.CalledProcessError as e:
        st.error(f"An error occurred while fixing timestamps: {e}")
        return None

# Streamlit UI
st.title("Video Downloader")

# Input box for URL and save path
video_url = st.text_input("Enter the video URL")
save_dir = st.text_input("Enter save directory (e.g., downloads)", value="downloads")

# Progress bar and status placeholders
progress_bar = st.progress(0)
status_text = st.empty()

# Progress update function
def update_progress_bar(current, total, speed=None, eta=None):
    progress = current / total if total else 0  # Calculate progress as a float between 0 and 1
    progress_bar.progress(min(max(progress, 0.0), 1.0))  # Streamlit expects a value from 0 to 1
    
    # Display percentage, speed, and ETA without decimals for ETA
    status_text.text(
        f"Download progress: {int(progress * 100)}% | "  # Convert progress to a percentage
        f"Speed: {speed / 1024 / 1024:.2f} MB/s | " if speed else "" +
        f"ETA: {int(eta)} seconds" if eta else ""  # Display ETA as an integer
    )


# Download button
if st.button("Download"):
    if video_url and save_dir:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Check if the URL is a direct link to a video file
        if any(video_url.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv"]):
            video_path = download_direct_video(video_url, save_dir / "downloaded_video.mp4", lambda current, total: update_progress_bar(current, total))
        else:
            video_path = download_with_ytdlp(video_url, str(save_dir), update_progress_bar)
        
        # Fix timestamps if a video was downloaded successfully
        if video_path:
            fixed_video_path = save_dir / ("fixed_" + os.path.basename(video_path))
            video_path = fix_video_timestamps(video_path, fixed_video_path) or video_path  # Update path if fix successful

            st.success("Download completed!")
            with open(video_path, "rb") as video_file:
                st.download_button(
                    label="Click here to download the video",
                    data=video_file,
                    file_name=os.path.basename(video_path),
                    mime="video/mp4"
                )
            
            # Reset progress bar
            progress_bar.empty()
            status_text.empty()
    else:
        st.warning("Please enter a video URL and save directory.")
