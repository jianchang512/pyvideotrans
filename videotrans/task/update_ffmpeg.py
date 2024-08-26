"""
# License

This script for downloading/updating ffmpeg was created by Thiago Ramos.
Contact: thiagojramos@outlook.com

The ffmpeg executables (ffmpeg.exe and ffprobe.exe) are created and maintained by the FFmpeg developers.
For more information, visit the FFmpeg GitHub repository: https://github.com/BtbN/FFmpeg-Builds

This script is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the script or the use or other dealings in the script.
"""

import os
import shutil
import zipfile

import requests

# Gets the current script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Defines the destination directory and temporary directory relative to the script directory
dest_dir = os.path.join(script_dir, "..", "..", "ffmpeg")
temp_dir = os.path.join(dest_dir, "temp_ffmpeg")
os.makedirs(dest_dir, exist_ok=True)

# GitHub API URL to get the latest ffmpeg version
api_url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
response = requests.get(api_url)
latest_release = response.json()
latest_version = latest_release["tag_name"]
download_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n7.0-latest-win64-gpl-7.0.zip"

# Destination path for the download
zip_path = os.path.join(dest_dir, "ffmpeg.zip")

# Download the zip file
print("Downloading ffmpeg.zip...")
with requests.get(download_url, stream=True) as r:
    r.raise_for_status()
    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

# Extract the contents of the zip file
print("Extracting the contents of ffmpeg.zip...")
with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(temp_dir)

# Paths to the binaries within the extracted zip file
ffmpeg_exe = os.path.join(
    temp_dir, "ffmpeg-n7.0-latest-win64-gpl-7.0", "bin", "ffmpeg.exe"
)
ffprobe_exe = os.path.join(
    temp_dir, "ffmpeg-n7.0-latest-win64-gpl-7.0", "bin", "ffprobe.exe"
)

# Checks if the files already exist and removes them if necessary
if os.path.exists(os.path.join(dest_dir, "ffmpeg.exe")):
    print("Removing existing ffmpeg.exe file...")
    os.remove(os.path.join(dest_dir, "ffmpeg.exe"))
if os.path.exists(os.path.join(dest_dir, "ffprobe.exe")):
    print("Removing existing ffprobe.exe file...")
    os.remove(os.path.join(dest_dir, "ffprobe.exe"))

# Moves the new binaries to the destination directory
print("Moving new binaries to the destination directory...")
shutil.move(ffmpeg_exe, os.path.join(dest_dir, "ffmpeg.exe"))
shutil.move(ffprobe_exe, os.path.join(dest_dir, "ffprobe.exe"))

# Clean up temporary files
print("Cleaning up temporary files...")
os.remove(zip_path)
shutil.rmtree(temp_dir)

print("Download, extraction, and replacement completed!")
