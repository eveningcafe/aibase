#!/usr/bin/env bash
# Lab 1 — OPTIONAL: vLLM serving the SAME model (Qwen2.5-3B) at fp16, to contrast
# Ollama's single-user serving with vLLM's continuous batching at concurrency.
# Needs the vLLM venv:  source ~/aibase-models-lab/.venv-vllm/bin/activate
# (skip if you didn't install vLLM — the Ollama path already teaches the point)
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-3B-Instruct}"

exec vllm serve "$MODEL" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  --port 8000
