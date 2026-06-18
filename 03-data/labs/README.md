# Lab · Data layer (free Kaggle GPU)

Hands-on companion to [`../README.md`](../README.md). **One focused lab (~35 min)**,
runnable on a **free Kaggle notebook GPU** — the same **T4 (16 GB)** and the same
**Qwen2.5-3B-Instruct** as the [Models labs](../../02-models/labs/), so the layers
chain: the model you served and tuned in Layer 2 now gets *grounded* in Layer 3.
The corpus is a **real public Kubernetes Q&A dataset**
([`kubernetes_qa_pairs`](https://huggingface.co/datasets/ItshMoh/kubernetes_qa_pairs),
~500 tagged Q&A pairs), keeping the demo on the repo's DevOps theme.

| Lab | Topic | Notebook |
|-----|-------|----------|
| RAG | **RAG retrieval, made visible** | [`cloud-kaggle/lab_rag_kaggle.ipynb`](cloud-kaggle/lab_rag_kaggle.ipynb) |

It centers on **retrieval** — the part that decides RAG quality: **print the exact
chunks** a query loads, vary **top-k**, compare **chunk sizes**, add a
**cross-encoder reranker** (watch it reorder), then feed the top chunks to
Qwen2.5-3B for a **grounded, cited** answer plus a *"I don't know"* refusal.
Setup and gotchas are in [`cloud-kaggle/README.md`](cloud-kaggle/README.md).

---

## The environment

**Kaggle Notebooks** — a free, browser-based VM with a GPU, ~30 GPU-h/week. We
use the **T4 (16 GB)** accelerator (pick **GPU T4 x2**, not P100). Reproducibility
is the point: a student with only a laptop can open the notebook and run the same
RAG pipeline — no drivers, no CUDA install, no rented GPU. One-time account setup
is in [`cloud-kaggle/README.md`](cloud-kaggle/README.md).

## Conventions

- **Data: `ItshMoh/kubernetes_qa_pairs`** — a real public dataset of ~500 k8s Q&A
  pairs (with `topic`/`difficulty` tags), pulled from the Hugging Face Hub.
- **LLM: `Qwen2.5-3B-Instruct`** (fp16, ~6 GB) on the **T4** — same model as the
  Models labs.
- **Embedder: `BAAI/bge-small-en-v1.5`** + **reranker: `BAAI/bge-reranker-base`** —
  both tiny, run on **CPU** (instant at this scale; only the LLM needs the GPU).
- **Vector store: FAISS** (flat, in-process) — no server, perfect for a notebook.
- **Accelerator = GPU T4, Internet = On** — the first cell installs deps and pulls
  the dataset, embedder, reranker, and LLM (the only network step).
- **Sessions are ephemeral** — the notebook is self-contained, so just **Run All**.
