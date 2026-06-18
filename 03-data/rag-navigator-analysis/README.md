# RAG Navigator — video → redrawn transcript

Tooling to turn a whiteboard/lightboard explainer video into an **annotated
transcript** that lines up *what the presenter says* with *what she draws*.

Built for **IBM Technology — "RAG's Evolution: From Simple Retrieval to Agentic AI"**
(`https://www.youtube.com/watch?v=JB2P5Gk23VI`), but the pipeline works on any talking-
head / lightboard video.

## What's the idea

A lightboard explainer carries half its meaning in the drawing, which a plain transcript
throws away. This pipeline:

1. pulls the transcript (timestamped),
2. downloads the video,
3. extracts a frame every time the picture **changes** (i.e. each new bit of drawing),
4. tiles those frames into labeled **contact sheets** for fast review,

…then a human/LLM reviews the sheets and writes the **redrawn transcript**:
`output/annotated_transcript.md` — narration + a description and ASCII sketch of each
diagram, aligned by timestamp.

> The first four steps are fully automated. Step 5 (the visual analysis) is done by
> reading the contact sheets — that's the part that needs eyes/an LLM, not a script.

## Layout

```
rag-navigator-analysis/
├── .venv/                     # virtualenv (yt-dlp, youtube-transcript-api, opencv, pillow, numpy)
├── 01_get_transcript.py       # transcript -> output/transcript.txt + transcript_raw.json
├── 02_get_video.py            # video    -> output/video.mp4  (H.264, <=480p, single stream)
├── 03_extract_frames.py       # scene-change frames -> frames/ + output/frames_index.json
├── 04_make_contactsheets.py   # tiled, timestamp-labeled grids -> output/contactsheets/
├── frames/                    # one .jpg per detected scene change (named f_mm_ss.jpg)
└── output/
    ├── transcript.txt             # [mm:ss] one line per cue
    ├── transcript_raw.json        # {text,start,duration}
    ├── video.mp4
    ├── frames_index.json
    ├── contactsheets/sheet_*.jpg  # review these
    └── annotated_transcript.md    # ⭐ the deliverable: the "redrawn" transcript
```

## Run it

```bash
cd rag-navigator-analysis
python3 -m venv .venv && . .venv/bin/activate
pip install yt-dlp youtube-transcript-api opencv-python-headless numpy pillow

VID=JB2P5Gk23VI
python 01_get_transcript.py   $VID
python 02_get_video.py        $VID
python 03_extract_frames.py
python 04_make_contactsheets.py
# then open output/contactsheets/*.jpg and write up annotated_transcript.md
```

## Notes / gotchas

- **No system ffmpeg needed.** We grab a single video-only H.264 stream (no audio, no
  merge) and decode with OpenCV. OpenCV's bundled decoder can't do **AV1**, so
  `02_get_video.py` forces `vcodec^=avc1`.
- **Tuning frame extraction** (`03_extract_frames.py`): raise `DIFF_THRESHOLD` to keep
  fewer/more-distinct frames; lower it to catch subtle additions. `SETTLE_S` waits a beat
  after a change so a frame is grabbed *after* a stroke finishes, not mid-draw.
- This video is continuously animated, so ~188 frames are kept — the contact sheets
  (16/sheet) make that reviewable in ~12 images.
