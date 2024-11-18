import streamlit as st
import requests
import yt_dlp
import os
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup

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

# yt-dlp download function with progress callback
def download_with_ytdlp(url, save_path, progress_callback):
    def yt_dlp_progress_hook(d):
        if d['status'] == 'downloading':
            downloaded_bytes = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes', 1)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

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

# Function to extract direct video URL
def get_direct_video_url(page_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(page_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        video_tag = soup.find('video')
        
        if video_tag and video_tag.get('src'):
            return video_tag['src']
        else:
            raise ValueError("Direct video URL not found on the page.")
    except Exception as e:
        st.error(f"An error occurred while fetching the direct video URL: {e}")
        return None

# Function to validate video file integrity
def is_valid_video_file(file_path):
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(file_path), "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except Exception as e:
        st.error(f"Error during file validation: {e}")
        return False

# Function to fix video timestamps
def fix_video_timestamps(input_file, output_file):
    input_file = Path(input_file)
    output_file = Path(output_file)
    sanitized_name = input_file.stem
    sanitized_output_file = input_file.with_name(f"fixed_{sanitized_name}.mp4")

    if not is_valid_video_file(input_file):
        st.error(f"The input file '{input_file}' is not a valid video file.")
        return None

    try:
        subprocess.run([
            "ffmpeg", "-i", str(input_file), "-c", "copy", str(sanitized_output_file), "-y"
        ], check=True)
        os.remove(input_file)
        os.rename(sanitized_output_file, input_file)
        return input_file
    except subprocess.CalledProcessError as e:
        st.error(f"An error occurred while fixing timestamps: {e}")
        return None

# Function to validate save directory
def validate_save_dir(directory):
    try:
        save_path = Path(directory)
        save_path.mkdir(parents=True, exist_ok=True)
        return save_path
    except Exception as e:
        st.error(f"An error occurred while creating save directory: {e}")
        return None

# Streamlit UI
st.title("Video Downloader")

video_url = st.text_input("Enter the video URL")
save_dir = st.text_input("Enter save directory", value=str(Path.home() / "Downloads"))

progress_bar = st.progress(0)
status_text = st.empty()

# Progress update function
def update_progress_bar(current, total, speed=None, eta=None):
    progress = current / total if total else 0
    progress_bar.progress(min(max(progress, 0.0), 1.0))
    total_size_mb = total / 1024 / 1024 if total else 0
    downloaded_mb = current / 1024 / 1024
    eta_formatted = "Unknown"
    if eta:
        hours, remainder = divmod(eta, 3600)
        minutes, seconds = divmod(remainder, 60)
        eta_formatted = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    status_text.text(
        f"Progress: {int(progress * 100)}% | "
        f"Downloaded: {downloaded_mb:.2f} MB / {total_size_mb:.2f} MB | " +
        (f"Speed: {speed / 1024 / 1024:.2f} MB/s | " if speed else "") +
        f"ETA: {eta_formatted}"
    )

# Download button
if st.button("Get Video"):
    if video_url:
        save_path = validate_save_dir(save_dir)
        if not save_path:
            st.warning("Please enter a valid save directory.")
        else:
            # Attempt to download with yt-dlp
            video_path = download_with_ytdlp(video_url, str(save_path), update_progress_bar)

            # Fallback to direct download if yt-dlp fails
            if not video_path:
                st.info("Trying to fetch the direct video URL...")
                direct_video_url = get_direct_video_url(video_url)
                if direct_video_url:
                    video_path = download_direct_video(direct_video_url, save_path / "downloaded_video.mp4", update_progress_bar)

            # Validate and fix timestamps if a video was downloaded
            if video_path:
                if is_valid_video_file(video_path):
                    fixed_video_path = save_path / ("fixed_" + os.path.basename(video_path))
                    video_path = fix_video_timestamps(video_path, fixed_video_path) or video_path
                    st.success("Download completed!")
                else:
                    st.error(f"The video file '{video_path}' is corrupted or invalid.")
    else:
        st.warning("Please enter a video URL.")
