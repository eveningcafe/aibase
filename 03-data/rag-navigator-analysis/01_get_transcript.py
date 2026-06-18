#!/usr/bin/env python3
"""Download the transcript for a YouTube video.

Writes two files in output/:
  - transcript_raw.json : list of {text, start, duration}
  - transcript.txt      : human-readable, one [mm:ss] line per cue
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)


def fmt_ts(seconds: float) -> str:
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def fetch(video_id: str):
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    # Prefer manually-created English, fall back to anything / auto-generated.
    transcripts = api.list(video_id)
    chosen = None
    for getter in (
        lambda: transcripts.find_manually_created_transcript(["en", "en-US", "en-GB"]),
        lambda: transcripts.find_transcript(["en", "en-US", "en-GB"]),
    ):
        try:
            chosen = getter()
            break
        except Exception:
            continue
    if chosen is None:
        # Last resort: first available, translated to English if possible.
        chosen = next(iter(transcripts))
        try:
            chosen = chosen.translate("en")
        except Exception:
            pass

    print(f"Using transcript: lang={chosen.language_code} "
          f"generated={chosen.is_generated}")
    fetched = chosen.fetch()
    return [
        {"text": s.text, "start": s.start, "duration": s.duration}
        for s in fetched
    ]


def main():
    video_id = sys.argv[1] if len(sys.argv) > 1 else "JB2P5Gk23VI"
    cues = fetch(video_id)

    (OUT / "transcript_raw.json").write_text(
        json.dumps(cues, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = []
    for c in cues:
        text = " ".join(c["text"].split())
        lines.append(f"[{fmt_ts(c['start'])}] {text}")
    (OUT / "transcript.txt").write_text("\n".join(lines), encoding="utf-8")

    dur = cues[-1]["start"] + cues[-1]["duration"] if cues else 0
    print(f"Wrote {len(cues)} cues, video length ~{fmt_ts(dur)}")
    print(f"  -> {OUT/'transcript_raw.json'}")
    print(f"  -> {OUT/'transcript.txt'}")


if __name__ == "__main__":
    main()
