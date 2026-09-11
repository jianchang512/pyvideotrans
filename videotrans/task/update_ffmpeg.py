"""
# License

This script for downloading/updating ffmpeg was created by Thiago Ramos.
Contact: thiagojramos@outlook.com

The ffmpeg executables (ffmpeg.exe and ffprobe.exe) are created and maintained by the FFmpeg developers.
For more information, visit the FFmpeg GitHub repository: https://github.com/BtbN/FFmpeg-Builds

This script is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the script or the use or other dealings in the script.
"""

import glob
import hashlib
import os
import re
import shutil
import sys
import zipfile

import requests

RELEASE_API = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest"
CHECKSUM_FILE = "checksums.sha256"
FALLBACK_ZIP = "ffmpeg-master-latest-win64-gpl.zip"


def _stable_version(name):
    # 形如 ffmpeg-n8.1-latest-win64-gpl-8.1.zip 的稳定版（非 shared）
    m = re.match(r"ffmpeg-n(\d+)\.(\d+)-latest-win64-gpl-\1\.\2\.zip$", name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _expected_sha256(checksums_text, zip_name):
    for line in checksums_text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == zip_name:
            return parts[0].lower()
    return None


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dest_dir = os.path.join(script_dir, "..", "..", "ffmpeg")
    temp_dir = os.path.join(dest_dir, "temp_ffmpeg")
    os.makedirs(dest_dir, exist_ok=True)

    response = requests.get(RELEASE_API, timeout=30)
    response.raise_for_status()
    assets = {a["name"]: a["browser_download_url"] for a in response.json().get("assets", [])}

    stable = sorted((n for n in assets if _stable_version(n)), key=_stable_version)
    zip_name = stable[-1] if stable else FALLBACK_ZIP
    if zip_name not in assets or CHECKSUM_FILE not in assets:
        sys.exit(f"Release assets not found: {zip_name} / {CHECKSUM_FILE}")

    checksums = requests.get(assets[CHECKSUM_FILE], timeout=30)
    checksums.raise_for_status()
    expected = _expected_sha256(checksums.text, zip_name)
    if not expected:
        sys.exit(f"No sha256 checksum found for {zip_name}")

    zip_path = os.path.join(dest_dir, "ffmpeg.zip")
    print(f"Downloading {zip_name}...")
    sha256 = hashlib.sha256()
    with requests.get(assets[zip_name], stream=True, timeout=(15, 60)) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                sha256.update(chunk)

    # 校验下载文件的 sha256，不一致则删除并退出，避免替换为被篡改的可执行文件
    if sha256.hexdigest().lower() != expected:
        os.remove(zip_path)
        sys.exit(f"sha256 mismatch for {zip_name}, download discarded")
    print("sha256 verified")

    print("Extracting the contents of ffmpeg.zip...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    bin_dirs = glob.glob(os.path.join(temp_dir, "*", "bin"))
    if not bin_dirs:
        sys.exit("bin directory not found in the downloaded archive")
    ffmpeg_exe = os.path.join(bin_dirs[0], "ffmpeg.exe")
    ffprobe_exe = os.path.join(bin_dirs[0], "ffprobe.exe")

    for exe in ("ffmpeg.exe", "ffprobe.exe"):
        target = os.path.join(dest_dir, exe)
        if os.path.exists(target):
            print(f"Removing existing {exe} file...")
            os.remove(target)

    print("Moving new binaries to the destination directory...")
    shutil.move(ffmpeg_exe, os.path.join(dest_dir, "ffmpeg.exe"))
    shutil.move(ffprobe_exe, os.path.join(dest_dir, "ffprobe.exe"))

    print("Cleaning up temporary files...")
    os.remove(zip_path)
    shutil.rmtree(temp_dir)

    print("Download, verification, extraction, and replacement completed!")


if __name__ == "__main__":
    main()
