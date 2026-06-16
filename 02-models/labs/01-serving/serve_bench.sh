#!/usr/bin/env bash
# Lab 1 — RUN phase. Serve the ONE model (Qwen2.5-3B) at Q4 then fp16, and
# benchmark each. Assumes ./download.sh already pulled both tags.
set -euo pipefail
cd "$(dirname "$0")"

pgrep -x ollama >/dev/null || { nohup ollama serve >/tmp/ollama.log 2>&1 & sleep 4; }
vram() { nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader; }

run() {  # $1 = ollama tag, $2 = label
  echo; echo "==================== $2 ===================="
  python3 bench.py --base-url http://localhost:11434/v1 --model "$1" --concurrency 8 --max-tokens 128
  echo -n "VRAM used: "; vram
  ollama stop "$1" 2>/dev/null || true   # unload so the next measurement is clean
  sleep 3
}

run "qwen2.5:3b"               "Qwen2.5-3B  Q4_K_M"
run "qwen2.5:3b-instruct-fp16" "Qwen2.5-3B  fp16"

cat <<'EOF'

Read the two blocks together:
  Q4   -> ~2x smaller VRAM AND faster tokens/s than fp16, SAME model.
  fp16 -> baseline quality, biggest footprint.
The cost of Q4 is a little quality — measure it in Lab 3 (optional Part C),
don't assume it's free.
EOF
