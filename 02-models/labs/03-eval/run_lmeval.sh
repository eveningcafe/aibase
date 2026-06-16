#!/usr/bin/env bash
# Lab 3 — standardized benchmark via lm-evaluation-harness.
# Shows the "academic benchmark" side of eval next to our task eval.
# --limit keeps it classroom-fast (remove for a real run).
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-3B-Instruct}"
TASKS="${TASKS:-arc_easy}"     # try: hellaswag, gsm8k, mmlu (slower)
LIMIT="${LIMIT:-200}"          # cap examples for a quick demo

lm_eval --model hf \
  --model_args "pretrained=${MODEL},dtype=bfloat16" \
  --tasks "${TASKS}" \
  --device cuda:0 \
  --batch_size auto \
  --limit "${LIMIT}"

echo
echo "Teaching point: a leaderboard number (e.g. arc_easy acc) measures GENERAL"
echo "ability. Our task eval (eval_task.py) measures what WE actually care about."
echo "A fine-tune can lift the task metric while barely moving the benchmark —"
echo "and that's fine: trust the held-out task eval for YOUR job."
