# Instructor runsheet — Models layer (half day, ~3.5 h)

A minute-by-minute spine. Slides = the "Models — deep dive" section of
[`../../slides.md`](../../slides.md). Commands assume you're on the node in
`~/aibase-models-lab/labs/<lab>` with the venv active.

> **Pre-class (do before students arrive):** confirm the env is warm — see
> [Pre-flight](#pre-flight). Pre-pull all models so no live download stalls.

| Time | Block | Slides | Lab / action |
|------|-------|--------|--------------|
| 0:00 | Intro + lifecycle | lead, "model lifecycle" | none — set the loop |
| 0:10 | Choosing + VRAM | "choosing", "the one number: VRAM" | show `nvidia-smi`; do the VRAM math live |
| 0:25 | **Lab 1 · Serving** | "serving — two engines" | `01-serving/` Part A (Ollama), then B (vLLM) + `bench.py` |
| 1:10 | Break | — | — |
| 1:20 | Fine-tuning concept | "fine-tuning — teach behavior" | walk LoRA vs QLoRA |
| 1:35 | **Lab 2 · Fine-tune** | same | `02-finetune/`: make_data → infer (before) → train → infer (after) → MLflow |
| 2:35 | Evaluation concept | "evaluation — numbers not vibes" | why held-out > leaderboard |
| 2:45 | **Lab 3 · Eval** | same | `03-eval/`: `eval_task.py` (before/after table), `run_lmeval.sh` |
| 3:15 | Training + MLOps | "training & MLOps — bookends" | explain only (can't run on 1 GPU) |
| 3:25 | Takeaways + Q&A | "models — takeaways" | recap the loop |

---

## Pre-flight (run once, before class)

```bash
ssh -p 234 hoanq333@61.28.228.70
cd ~/aibase-models-lab && source .venv/bin/activate

# torch sees the GPU?
python -c "import torch;print(torch.__version__, torch.cuda.get_device_name(0))"
# models cached?
ollama list                       # expect qwen2.5:7b, qwen2.5:14b
ls labs/02-finetune/data          # expect train.jsonl, test.jsonl
```

If a model is missing: `ollama pull qwen2.5:7b qwen2.5:14b`. The HF model for
Labs 2–3 (`Qwen/Qwen2.5-3B-Instruct`) downloads on first `train.py`/`infer_*`
run — **pre-run `infer_compare.py` once** so class doesn't wait on it.

## Live demo order (copy-paste)

```bash
# --- Lab 1 ---
cd ~/aibase-models-lab/labs/01-serving
bash ollama_demo.sh                                   # Q4 7B + 14B, VRAM snapshots
# (new tmux pane) vLLM:
source ~/aibase-models-lab/.venv-vllm/bin/activate && bash vllm_serve.sh
# (another pane)
python bench.py --base-url http://localhost:8000/v1  --model Qwen/Qwen2.5-7B-Instruct --concurrency 16
python bench.py --base-url http://localhost:11434/v1 --model qwen2.5:7b               --concurrency 16

# --- Lab 2 ---
cd ~/aibase-models-lab/labs/02-finetune && source ~/aibase-models-lab/.venv/bin/activate
python make_data.py
python infer_compare.py --adapter adapters/lora      # BEFORE (base rambles)
python train.py                                       # ~minutes; watch nvidia-smi
python infer_compare.py --adapter adapters/lora      # AFTER (clean JSON)
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000   # tunnel: ssh -L 5000:localhost:5000

# --- Lab 3 ---
cd ~/aibase-models-lab/labs/03-eval
python eval_task.py --adapter ../02-finetune/adapters/lora --test ../02-finetune/data/test.jsonl
bash run_lmeval.sh
```

## The five lines to land (one per phase)

1. **Choosing:** you pick for a *task + budget + GPU*, never "the best model."
2. **Serving:** VRAM governs everything; quantization is the lever; latency ≠ throughput.
3. **Fine-tune:** you learn a tiny adapter, not 7B weights — that's why it's cheap.
4. **Eval:** trust your *held-out task* number over any leaderboard.
5. **MLOps:** the eval is the CI gate; the run is a tracked artifact, not a mystery file.

## If something breaks

| Symptom | Fix |
|---------|-----|
| `no kernel image ... device` | wrong torch — must be cu128 build (Lab 0) |
| vLLM OOM | lower `--gpu-memory-utilization` or `--max-model-len` in `vllm_serve.sh` |
| HF download stalls | model caches in `~/.cache/huggingface`; pre-pull before class |
| bitsandbytes 4-bit error | ensure recent `bitsandbytes`; QLoRA needs Blackwell-capable build |
| SSH drops mid-train | always train inside `tmux` |
</content>
