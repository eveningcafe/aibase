#!/usr/bin/env python3
"""Tile the extracted frames into labeled contact sheets for review.

Each thumbnail gets its timestamp [mm:ss] burned into the corner so a frame
can be referenced precisely against the transcript.
"""
import json
from pathlib import Path

import cv2

HERE = Path(__file__).parent
FRAMES = HERE / "frames"
OUT = HERE / "output"
SHEETS = OUT / "contactsheets"

COLS, ROWS = 4, 4          # 16 thumbs per sheet
THUMB_W = 360              # thumbnail width px
PAD = 8


def label_from_file(name: str) -> str:
    # f_01_29.jpg -> 01:29
    stem = name[2:-4]
    m, s = stem.split("_")
    return f"{m}:{s}"


def main():
    SHEETS.mkdir(parents=True, exist_ok=True)
    for old in SHEETS.glob("*.jpg"):
        old.unlink()

    idx = json.loads((OUT / "frames_index.json").read_text())
    frames = idx["frames"]

    per_sheet = COLS * ROWS
    sheet_no = 0
    for start in range(0, len(frames), per_sheet):
        chunk = frames[start:start + per_sheet]
        thumbs = []
        thumb_h = None
        for fr in chunk:
            img = cv2.imread(str(FRAMES / fr["file"]))
            h, w = img.shape[:2]
            th = int(h * THUMB_W / w)
            thumb_h = th
            img = cv2.resize(img, (THUMB_W, th))
            label = label_from_file(fr["file"])
            cv2.rectangle(img, (0, 0), (96, 26), (0, 0, 0), -1)
            cv2.putText(img, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX,
                        0.62, (0, 255, 255), 2, cv2.LINE_AA)
            thumbs.append(img)

        # build grid
        import numpy as np
        blank = None
        grid_rows = []
        for r in range(ROWS):
            row_imgs = []
            for c in range(COLS):
                i = r * COLS + c
                if i < len(thumbs):
                    row_imgs.append(thumbs[i])
                else:
                    if blank is None:
                        blank = (thumbs[0] * 0)
                    row_imgs.append(blank)
                if c < COLS - 1:
                    row_imgs.append(255 + (thumbs[0][:, :PAD] * 0))  # white pad
            grid_rows.append(cv2.hconcat(row_imgs))
            if r < ROWS - 1:
                pad_row = grid_rows[-1][:PAD, :] * 0 + 255
                grid_rows.append(pad_row)
        sheet = cv2.vconcat(grid_rows)

        sheet_no += 1
        name = f"sheet_{sheet_no:02d}.jpg"
        cv2.imwrite(str(SHEETS / name), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(f"{name}: frames {start}..{start+len(chunk)-1} "
              f"({label_from_file(chunk[0]['file'])}–{label_from_file(chunk[-1]['file'])})")

    print(f"\n{sheet_no} sheets -> {SHEETS}")


if __name__ == "__main__":
    main()
