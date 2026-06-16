#!/usr/bin/env bash
# Lab 2 — DOWNLOAD phase (once, ahead of class). Cache the base model so the
# train/infer steps don't stall on a download. Same model as Labs 1 & 3.
set -euo pipefail
PY="${PYTHON:-$HOME/aibase-models-lab/.venv/bin/python}"
"$PY" - <<'PYCODE'
from huggingface_hub import snapshot_download
p = snapshot_download("Qwen/Qwen2.5-3B-Instruct")
print("cached:", p)
PYCODE
echo "base model cached. Now run make_data.py, then train.py."
