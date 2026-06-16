# Labs · Models layer (free Kaggle GPU)

Hands-on companion to [`../README.md`](../README.md). Three labs, ~3–4 hours, all
runnable on a **free Kaggle notebook GPU** — chosen so every student can
reproduce them with no hardware of their own.

| Lab | Topic | Notebook |
|-----|-------|----------|
| 1 | **Serving + quantization** | [`cloud-kaggle/lab1_serving_kaggle.ipynb`](cloud-kaggle/lab1_serving_kaggle.ipynb) |
| 2 | **Fine-tune** LoRA/QLoRA + MLflow | [`cloud-kaggle/lab2_finetune_kaggle.ipynb`](cloud-kaggle/lab2_finetune_kaggle.ipynb) |
| 3 | **Evaluation** | [`cloud-kaggle/lab3_eval_kaggle.ipynb`](cloud-kaggle/lab3_eval_kaggle.ipynb) |

Setup, chaining, and gotchas live in [`cloud-kaggle/README.md`](cloud-kaggle/README.md).

---

## The environment

**Kaggle Notebooks** — a free, browser-based VM with a GPU, ~30 GPU-h/week. We
use the **T4 (16 GB)** accelerator.

> **Why not a local/5090 box?** Reproducibility. A student with only a laptop can
> open these notebooks and run the exact same labs — no drivers, no CUDA install,
> no rented GPU.

One-time account setup (phone-verify for GPU + Internet, API token) is in
[`cloud-kaggle/README.md`](cloud-kaggle/README.md).

### What the T4 changes (vs. a high-end GPU)

- **16 GB VRAM** — plenty for a 3B model; use **QLoRA** (4-bit base) for fine-tune.
- **No bf16** → we use **fp16** everywhere (and `bnb_4bit_compute_dtype=float16`).
- **No int4/fp16 tensor acceleration** → quantization (Q4) still **halves VRAM**,
  but is **not** faster here (on a Blackwell GPU it would be ~1.5×). *Hardware
  decides whether quant buys speed.*

---

## Conventions used by every lab

- **One model across all labs: `Qwen2.5-3B-Instruct`** (Apache-2.0, ungated).
- **Accelerator = GPU, Internet = On** in the notebook settings (first cell
  installs deps + pulls the model — the only network step).
- **Labs chain:** Lab 2 writes its adapter + test set to `/kaggle/working`; Lab 3
  reads them by adding Lab 2's notebook output as an input (see Lab 3's intro).
- **Sessions are ephemeral** — outputs persist only if you "Save Version" or add
  them as a downstream input. Download `mlflow.db` to inspect runs locally.
</content>
