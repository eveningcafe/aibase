#!/usr/bin/env python3
"""Extract 'scene' frames: grab a frame whenever the picture changes enough.

For a whiteboard/animated explainer this captures each new state of the
drawing (a fresh diagram element, a new panel, etc.) rather than dumping a
frame every N seconds. Each saved frame is named with its timestamp so it can
be lined up against the transcript.

Strategy:
  - sample the video a few times per second (not every frame)
  - downscale + grayscale each sample
  - compare to the last *kept* frame via mean absolute pixel difference
  - keep it if the difference exceeds a threshold AND enough time has passed
  - also force-keep at a maximum interval so long static stretches still get one
"""
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
FRAMES = HERE / "frames"
OUT = HERE / "output"
VIDEO = OUT / "video.mp4"

# --- tunables ---
SAMPLE_HZ = 3.0          # how many samples per second to inspect
DIFF_THRESHOLD = 6.0     # mean abs gray diff (0-255) to call it a "new scene"
MIN_GAP_S = 1.2          # don't keep two frames closer than this
MAX_GAP_S = 18.0         # force a keep at least this often
SETTLE_S = 0.4           # after a change, wait this long then grab (let draw finish)


def fmt_ts(seconds: float) -> str:
    s = int(round(seconds))
    m, s = divmod(s, 60)
    return f"{m:02d}_{s:02d}"


def main():
    FRAMES.mkdir(exist_ok=True)
    for old in FRAMES.glob("*.jpg"):
        old.unlink()

    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {VIDEO}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps
    step = max(1, int(round(fps / SAMPLE_HZ)))

    last_kept_small = None
    last_kept_t = -1e9
    pending_change_t = None
    kept = []

    def grab(frame_idx):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        return frame if ok else None

    def small_gray(frame):
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.resize(g, (160, 90))

    def keep(t, frame):
        name = f"f_{fmt_ts(t)}.jpg"
        # downscale a touch for compact, legible thumbnails
        h, w = frame.shape[:2]
        scale = 854 / w if w > 854 else 1.0
        if scale != 1.0:
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        cv2.imwrite(str(FRAMES / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
        kept.append({"file": name, "t": round(t, 2)})

    idx = 0
    while idx < total:
        t = idx / fps
        frame = grab(idx)
        if frame is None:
            idx += step
            continue
        sg = small_gray(frame)

        if last_kept_small is None:
            keep(t, frame)
            last_kept_small = sg
            last_kept_t = t
            idx += step
            continue

        diff = float(np.mean(cv2.absdiff(sg, last_kept_small)))
        gap = t - last_kept_t

        changed = diff > DIFF_THRESHOLD
        if changed and pending_change_t is None and gap >= MIN_GAP_S:
            pending_change_t = t  # mark change, grab after SETTLE_S

        # time to commit a pending change?
        if pending_change_t is not None and (t - pending_change_t) >= SETTLE_S:
            keep(t, frame)
            last_kept_small = sg
            last_kept_t = t
            pending_change_t = None
        elif gap >= MAX_GAP_S:
            keep(t, frame)
            last_kept_small = sg
            last_kept_t = t
            pending_change_t = None

        idx += step

    cap.release()

    (OUT / "frames_index.json").write_text(
        json.dumps({"duration": round(duration, 2), "frames": kept}, indent=2)
    )
    print(f"Video {duration:.1f}s, sampled @ {SAMPLE_HZ}Hz")
    print(f"Kept {len(kept)} scene frames -> {FRAMES}")
    for k in kept:
        print(f"  {k['t']:7.2f}s  {k['file']}")


if __name__ == "__main__":
    main()
