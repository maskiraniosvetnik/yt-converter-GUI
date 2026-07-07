#!/usr/bin/env bash
set -e

echo "Installing dependencies..."
if command -v apt >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y python3 python3-tk yt-dlp ffmpeg
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y python3 python3-tkinter yt-dlp ffmpeg
elif command -v pacman >/dev/null 2>&1; then
  sudo pacman -S --needed python python-tk yt-dlp ffmpeg
else
  echo "Unknown package manager. Install manually: python3, tkinter, yt-dlp, ffmpeg"
fi

echo "Done. Run ./run.sh"
