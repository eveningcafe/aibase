# Lab 2 · Fine-tune (LoRA / QLoRA) + MLflow

**Goal:** teach Qwen2.5-3B-Instruct a *specific behavior* it doesn't reliably do —
parse a free-text order into **strict JSON** — and track the whole thing in MLflow.

Prereqs: Lab 0 bootstrap + per-lab deps (`transformers trl peft bitsandbytes
datasets mlflow`). Run from `~/aibase-models-lab/labs/02-finetune`.

| Phase concept | What we prove |
|---------------|---------------|
| Fine-tune = behavior | base model rambles / breaks schema → tuned model emits clean JSON |
| LoRA vs QLoRA | adapter trains in minutes; QLoRA halves VRAM |
| MLOps | every run logged: params, loss curve, metrics — reproducible |

---

## Step 0 · Download the base model (once, ahead of class)

```bash
bash download.sh        # caches Qwen/Qwen2.5-3B-Instruct (~6 GB) — the only network step
```

Same 3B model as Labs 1 and 3. Keep this separate so train/infer time isn't spent
waiting on a download.

## Step 1 · Make the dataset

```bash
python make_data.py        # -> data/train.jsonl (~1000), data/test.jsonl (~180)
```

Synthetic, seeded (same every class). Task: *"can I get 3 lavender shampoo to
Hanoi"* → `{"intent":"order","item":"lavender shampoo","qty":3,"city":"Hanoi"}`.

## Step 2 · See the BEFORE

```bash
python infer_compare.py --adapter adapters/lora    # adapter missing yet → base only section is the point
```

The base model often adds prose, code fences, or wrong keys. That's the gap we
close.

## Step 3 · Train

```bash
# LoRA (base in bf16) — the default
python train.py

# QLoRA (base in 4-bit) — lower VRAM, same recipe
python train.py --qlora
```

Watch `nvidia-smi` in another pane. Expect LoRA ≈ a few GB of trainable state on
top of the 3B; QLoRA noticeably less. The script prints **peak VRAM** at the end.

## Step 4 · See the AFTER + track

```bash
python infer_compare.py --adapter adapters/lora    # base vs tuned, side by side
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000   # loss curve, params
```

> SSH port-forward to view MLflow locally:
> `ssh -p 234 -L 5000:localhost:5000 hoanq333@61.28.228.70` then open
> `http://localhost:5000`.

---

## What to expect (fill in live)

| Run | Trainable params | Peak VRAM | Final loss | JSON-valid % after |
|-----|-----------------:|----------:|-----------:|-------------------:|
| LoRA r=16 | ~0.5–1% of 3B | _measure_ | _measure_ | _Lab 3_ |
| QLoRA r=16 | same adapters | _lower_ | _measure_ | _Lab 3_ |

> **✅ Validated on the 5090** (0.5B smoke run, QLoRA, 2 epochs): ~**85 s**, peak
> VRAM **2.5 GB**, final loss ~**0.085**, token-acc ~**0.97**. The class 3B run is
> bigger but the same shape — expect single-digit GB VRAM, a few minutes.

## Teaching points

- **You are not moving 3B weights** — you learn a few million adapter numbers.
  That's why this finishes in minutes on one GPU.
- **QLoRA** loads the frozen base in 4-bit, so the big cost (the base) shrinks
  ~4×; the trainable adapter is unchanged. Use it when VRAM is tight or the base
  is bigger.
- **MLflow** makes the run an artifact, not a memory: params, loss, and the
  adapter are all recoverable and comparable across runs.
- Merge for deployment (optional): `PeftModel.merge_and_unload()` folds the
  adapter into the weights so serving needs no PEFT at runtime.

Then take both models to **[Lab 3](../03-eval/)** and put real numbers on
"better".
</content>
