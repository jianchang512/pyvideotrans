"""
# License

This script for downloading/updating yt-dlp was created by Thiago Ramos.
Contact: thiagojramos@outlook.com

The yt-dlp executable is created and maintained by the yt-dlp developers.
For more information, visit the yt-dlp GitHub repository: https://github.com/yt-dlp/yt-dlp

This script is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the script or the use or other dealings in the script.
"""

import os
import platform

import requests

# Gets the current script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Defines the destination directory relative to the script directory
dest_dir = os.path.join(script_dir, "..", "..", "ffmpeg")
os.makedirs(dest_dir, exist_ok=True)

# Detects the system architecture
system_architecture = platform.architecture()[0]
if system_architecture == "64bit":
    yt_dlp_exe = "yt-dlp.exe"
    print("Detected system: 64-bit")
else:
    yt_dlp_exe = "yt-dlp_x86.exe"
    print("Detected system: 32-bit")

# GitHub API URL to get the latest yt-dlp version
api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
response = requests.get(api_url)
latest_release = response.json()
latest_version = latest_release["tag_name"]
download_url = (
    f"https://github.com/yt-dlp/yt-dlp/releases/download/{latest_version}/{yt_dlp_exe}"
)

# Destination path for the download
output_path = os.path.join(dest_dir, yt_dlp_exe)

# Download the executable
print(f"Downloading {yt_dlp_exe}...")
with requests.get(download_url, stream=True) as r:
    r.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

# Checks if the file ytwin32.exe already exists and removes it if necessary
renamed_path = os.path.join(dest_dir, "ytwin32.exe")
if os.path.exists(renamed_path):
    print("Removing existing ytwin32.exe file...")
    os.remove(renamed_path)

# Renames the downloaded file
print("Renaming the file to ytwin32.exe...")
os.rename(output_path, renamed_path)

print("Download and renaming completed!")
