# Lab · Data layer (free Kaggle GPU)

Hands-on companion to [`../README.md`](../README.md). **Two labs (~25 min each)** that
mirror the README's chapters — **Lab 1 = simple pipeline, Lab 2 = advanced pipeline** —
runnable on a **free Kaggle notebook GPU** — the same **T4 (16 GB)** and the same
**Qwen2.5-3B-Instruct** as the [Models labs](../../02-models/labs/), so the layers
chain: the model you served and tuned in Layer 2 now gets *grounded* in Layer 3.
Both labs stay on the repo's DevOps theme — Lab 1 on a tidy **Kubernetes Q&A set**,
Lab 2 on the **real Kubernetes documentation**.

| Lab | Chapter | Topic | Notebook |
|-----|---------|-------|----------|
| 1 | Simple pipeline | **Simple RAG, made visible** | [`cloud-kaggle/lab1_simple_rag_kaggle.ipynb`](cloud-kaggle/lab1_simple_rag_kaggle.ipynb) |
| 2 | Advanced pipeline | **Advanced RAG over real k8s docs** | [`cloud-kaggle/lab2_advanced_rag_kaggle.ipynb`](cloud-kaggle/lab2_advanced_rag_kaggle.ipynb) |

**Lab 1** builds naive RAG end-to-end on a tidy
[Q&A set](https://huggingface.co/datasets/ItshMoh/kubernetes_qa_pairs) and makes
**retrieval** visible — **print the exact chunks** a query loads, vary **top-k**,
compare **chunk sizes** — then feeds the top chunks to Qwen2.5-3B for a **grounded,
cited** answer plus a *"I don't know"* refusal. **Lab 2** points the pipeline at the
**real [`kubernetes/website`](https://github.com/kubernetes/website) docs** (hundreds
of messy markdown pages): clean + **128-token chunk**, add **metadata filtering**,
**hybrid (BM25)**, and a **reranker**, then **measure** them with an **independent**
eval set (40 hand-written questions → gold doc; **hit@3** / **MRR**).
Setup and gotchas are in [`cloud-kaggle/README.md`](cloud-kaggle/README.md).

---

## The environment

**Kaggle Notebooks** — a free, browser-based VM with a GPU, ~30 GPU-h/week. We
use the **T4 (16 GB)** accelerator (pick **GPU T4 x2**, not P100). Reproducibility
is the point: a student with only a laptop can open the notebook and run the same
RAG pipeline — no drivers, no CUDA install, no rented GPU. One-time account setup
is in [`cloud-kaggle/README.md`](cloud-kaggle/README.md).

## Conventions

- **Data:** Lab 1 — `ItshMoh/kubernetes_qa_pairs` (~500 tagged k8s Q&A pairs, HF Hub);
  Lab 2 — the real `kubernetes/website` docs (`content/en/docs/{tasks,concepts}`,
  ~400 pages → ~9k chunks), cloned in-notebook at a pinned commit.
- **LLM: `Qwen2.5-3B-Instruct`** (fp16, ~6 GB) on the **T4** — same model as the
  Models labs. *Needs T4* (Kaggle's P100 can't run the prebuilt fp16 kernels), so the
  LLM cell is last and guarded; the chunk/index/eval core is CPU-only and runs anywhere.
- **Embedder: `BAAI/bge-small-en-v1.5`** + **reranker: `BAAI/bge-reranker-base`** —
  both tiny, run on **CPU** (Lab 2 embeds ~9k chunks on CPU in ~6 min).
- **Vector store: FAISS** (flat, in-process) — no server, exact up to ~100k vectors.
- **Accelerator = GPU T4, Internet = On** — the first cell installs deps; Lab 2 also
  clones the docs from GitHub.
- **Sessions are ephemeral** — the notebook is self-contained, so just **Run All**.
