# Models labs on Kaggle (free T4 GPU)

The Models layer labs, as interactive **Kaggle notebooks** — free, browser-based,
and reproducible by any student. We use the **T4 (16 GB)** accelerator.

| Notebook | Lab |
|----------|-----|
| [`lab1_serving_kaggle.ipynb`](lab1_serving_kaggle.ipynb) | Serving + quantization (Ollama, fp16 vs Q4) |
| [`lab2_finetune_kaggle.ipynb`](lab2_finetune_kaggle.ipynb) | Fine-tune QLoRA + MLflow |
| [`lab3_eval_kaggle.ipynb`](lab3_eval_kaggle.ipynb) | Evaluation (task eval + lm-eval) |

One model throughout: **Qwen2.5-3B-Instruct**.

## One-time setup (~5 min)

1. **Create a Kaggle account** → https://www.kaggle.com.
2. **Phone-verify** (Settings → Phone). *Required* — without it, kernels can't use
   GPU or Internet, so pip-install and model download fail.
3. In each notebook: **Settings → Accelerator = GPU (T4)**, **Internet = On**.

## Running the labs

Upload each `.ipynb` to Kaggle (or import from this repo) and **Run All**.

1. **Lab 1 — serving.** Installs Ollama, pulls Qwen2.5-3B at Q4 + fp16, benchmarks
   each, checks VRAM. Self-contained.
2. **Lab 2 — fine-tune.** Builds the dataset, shows the base model, QLoRA-trains a
   strict-JSON order parser, logs to MLflow, shows before/after. Writes
   `adapters/lora`, `data/test.jsonl`, `mlflow.db` to `/kaggle/working`.
   **Save Version** so the output is reusable.
3. **Lab 3 — eval.** **Add Input → Notebook Output → pick your Lab 2 version**, so
   its adapter + test set mount under `/kaggle/input/`. Then base-vs-tuned task
   eval + an lm-eval benchmark.

## What the T4 changes

- **16 GB VRAM** → use **QLoRA** (4-bit base) for the fine-tune; a 3B fits easily.
- **No bf16** → **fp16** everywhere (`bnb_4bit_compute_dtype=float16`).
- **No int4 acceleration** → Q4 **halves VRAM** but isn't faster here (it would be
  on a Blackwell GPU). Quantization's *speed* win is hardware-dependent; its
  *memory* win is not.

## Notes / gotchas

- **Quota:** ~30 GPU-h/week, ≤12 h/session. Each lab is minutes.
- **Ephemeral sessions:** outputs vanish unless you Save Version or chain them as
  an input (that's how Lab 3 gets Lab 2's adapter).
- **First run slow:** installs deps + downloads the model; re-runs reuse the
  image/model cache.
- **MLflow:** Kaggle is batch (no live UI) — the run is logged to `mlflow.db`;
  download it and run `mlflow ui --backend-store-uri sqlite:///mlflow.db` locally.
</content>
