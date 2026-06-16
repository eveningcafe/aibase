#!/usr/bin/env bash
# Lab 1A — Ollama (Q4) serving demo. Shows quantization fitting a 14B on 32 GB.
set -euo pipefail

snap() { echo "--- VRAM: $1 ---"; nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader; }

# Ollama runs as a background server; start it if not already up.
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "starting ollama server..."; nohup ollama serve >/tmp/ollama.log 2>&1 & sleep 3
fi

echo "== 7B at Q4_K_M (~4.7 GB on disk) =="
ollama pull qwen2.5:7b
snap "after loading 7B"
echo ">> prompt: explain a GPU to a 10-year-old in 2 sentences"
ollama run qwen2.5:7b "Explain what a GPU is to a 10-year-old in 2 sentences."
snap "7B loaded + ran"

echo
echo "== 14B at Q4 (~9 GB) — fp16 would be ~28 GB and barely fit =="
ollama pull qwen2.5:14b
ollama run qwen2.5:14b "In one sentence: why does quantization let a big model fit on a small GPU?"
snap "14B Q4 loaded + ran"

echo
echo "Punchline: a 14B model whose fp16 weights are ~28 GB runs comfortably here"
echo "at Q4 (~10-11 GB used). That headroom is what quantization buys you."
