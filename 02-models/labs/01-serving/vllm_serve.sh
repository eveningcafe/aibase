#!/usr/bin/env bash
# Lab 1B — vLLM serving Qwen2.5-7B-Instruct at fp16, OpenAI-compatible API on :8000.
# Run inside the vLLM venv:  source ~/aibase-models-lab/.venv-vllm/bin/activate
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"

# --gpu-memory-utilization 0.85 leaves room; --max-model-len caps KV cache size.
# On a single 5090 (32 GB) fp16 7B (~15 GB) + KV cache fits with room to spare.
exec vllm serve "$MODEL" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  --port 8000
