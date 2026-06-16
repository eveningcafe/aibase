#!/usr/bin/env bash
# Lab 1 — DOWNLOAD phase (run once, ahead of class). Pulls ONE model at two
# precisions so we can compare fp16 vs Q4 on identical weights.
set -euo pipefail

pgrep -x ollama >/dev/null || { echo "starting ollama..."; nohup ollama serve >/tmp/ollama.log 2>&1 & sleep 4; }

echo ">> Qwen2.5-3B  Q4_K_M  (~1.9 GB)"
ollama pull qwen2.5:3b
echo ">> Qwen2.5-3B  fp16    (~6.2 GB)"
ollama pull qwen2.5:3b-instruct-fp16

ollama list | grep -E "NAME|qwen2.5:3b"
echo "download done — models cached in ~/.ollama. Now run ./serve_bench.sh"
