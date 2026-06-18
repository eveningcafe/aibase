#!/usr/bin/env python3
"""Download the video at a modest resolution for frame analysis."""
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main():
    video_id = sys.argv[1] if len(sys.argv) > 1 else "JB2P5Gk23VI"
    url = f"https://www.youtube.com/watch?v={video_id}"
    out_tmpl = str(HERE / "output" / "video.%(ext)s")

    import yt_dlp

    opts = {
        # We only need frames (transcript covers audio). Pick a SINGLE stream so
        # no ffmpeg merge is required: a video-only mp4 <=480p, else 360p
        # progressive (fmt 18), else whatever single file is best.
        # Force H.264 (avc1) — OpenCV's bundled decoder can't do AV1.
        "format": (
            "bestvideo[vcodec^=avc1][height<=480]/"
            "best[vcodec^=avc1][height<=480]/18/best[ext=mp4]/best"
        ),
        "outtmpl": out_tmpl,
        "noplaylist": True,
        "quiet": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        print("Title:", info.get("title"))
        print("Duration (s):", info.get("duration"))
        print("Uploader:", info.get("uploader"))


if __name__ == "__main__":
    main()
