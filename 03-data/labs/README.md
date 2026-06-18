# Labs · Data layer (free Kaggle GPU)

Hands-on companion to [`../README.md`](../README.md). Two labs, ~1.5 hours, both
runnable on a **free Kaggle notebook GPU** — the same **T4 (16 GB)** and the same
**Qwen2.5-3B-Instruct** as the [Models labs](../../02-models/labs/), so the layers
chain: the model you served and tuned in Layer 2 now gets *grounded* in Layer 3.
The corpus is a small **Kubernetes/SRE knowledge base** (runbooks, cluster policy,
on-call rules, a postmortem), so the demo stays on the repo's DevOps theme.

| Lab | Topic | Notebook |
|-----|-------|----------|
| 1 | **Build a RAG pipeline** (synthetic runbooks) | [`cloud-kaggle/lab1_rag_kaggle.ipynb`](cloud-kaggle/lab1_rag_kaggle.ipynb) |
| 1b | **RAG on real public k8s data** (bonus) | [`cloud-kaggle/lab1b_realdata_kaggle.ipynb`](cloud-kaggle/lab1b_realdata_kaggle.ipynb) |
| 2 | **Evaluate RAG** | [`cloud-kaggle/lab2_rageval_kaggle.ipynb`](cloud-kaggle/lab2_rageval_kaggle.ipynb) |

Setup, chaining, and gotchas live in [`cloud-kaggle/README.md`](cloud-kaggle/README.md).

---

## The environment

**Kaggle Notebooks** — a free, browser-based VM with a GPU, ~30 GPU-h/week. We
use the **T4 (16 GB)** accelerator, exactly as the Models labs.

Reproducibility is the point: a student with only a laptop can open these
notebooks and run the same RAG pipeline — no drivers, no CUDA install, no rented
GPU. One-time account setup (phone-verify for GPU + Internet, API token) is in
[`cloud-kaggle/README.md`](cloud-kaggle/README.md).

### What the T4 changes (vs. a high-end GPU)

- **16 GB VRAM** — a 3B LLM (fp16, ~6 GB) plus a small embedding model fit with
  room to spare; RAG adds almost no VRAM (the index lives in RAM).
- **No bf16** → we load the LLM in **fp16**, same as the Models labs.
- The heavy cost in RAG is **retrieval quality**, not GPU — most of each lab is
  CPU-side (embedding, indexing, scoring).

---

## Conventions used by every lab

- **One LLM throughout: `Qwen2.5-3B-Instruct`** (Apache-2.0, ungated) — the same
  model as the Models labs.
- **Embedding model: `BAAI/bge-small-en-v1.5`** (384-dim, fast, CPU-friendly).
- **Vector store: FAISS** — in-process, no server, perfect for a notebook.
- **Accelerator = GPU, Internet = On** in the notebook settings (the first cell
  installs deps + pulls the embedder and LLM — the only network step).
- **Labs chain:** Lab 1 writes its FAISS index + chunked corpus + a small Q&A set
  to `/kaggle/working`; Lab 2 reads them by adding Lab 1's notebook output as an
  input (see Lab 2's intro), or rebuilds them inline if absent.
- **Sessions are ephemeral** — outputs persist only if you "Save Version" or add
  them as a downstream input.
