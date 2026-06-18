# Data labs on Kaggle (free T4 GPU)

The Data layer labs, as interactive **Kaggle notebooks** — free, browser-based,
and reproducible by any student. We use the **T4 (16 GB)** accelerator and the same
**Qwen2.5-3B-Instruct** as the Models labs.

| Notebook | Lab |
|----------|-----|
| [`lab1_rag_kaggle.ipynb`](lab1_rag_kaggle.ipynb) | Build a RAG pipeline over synthetic SRE runbooks (chunk → embed → FAISS → retrieve → generate) |
| [`lab1b_realdata_kaggle.ipynb`](lab1b_realdata_kaggle.ipynb) | **Bonus:** the same pipeline on 30k real Stack Overflow k8s Q&A (HTML cleaning, HNSW, retrieval at scale) |
| [`lab2_rageval_kaggle.ipynb`](lab2_rageval_kaggle.ipynb) | Evaluate RAG (faithfulness + retrieval metrics; sweep the knobs) |

One LLM throughout: **Qwen2.5-3B-Instruct**. Embedder: **`bge-small-en-v1.5`**.
Vector store: **FAISS**.

## One-time setup (~5 min)

1. **Create a Kaggle account** → https://www.kaggle.com.
2. **Phone-verify** (Settings → Phone). *Required* — without it, kernels can't use
   GPU or Internet, so pip-install and model download fail.
3. In each notebook: **Settings → Accelerator = GPU (T4)**, **Internet = On**.

## Running the labs

Upload each `.ipynb` to Kaggle (or import from this repo) and **Run All**.

1. **Lab 1 — build RAG.** Installs deps, builds a small **Kubernetes/SRE runbook**
   corpus (runbooks, cluster policy, on-call rules, a postmortem), chunks + embeds
   it, indexes in FAISS, and answers ops questions with Qwen2.5-3B. Shows the same
   question **without** retrieval (hallucinated) vs **with** retrieval (grounded +
   cited). Writes `index.faiss`, `chunks.jsonl`, and `qa.jsonl` to
   `/kaggle/working`. **Save Version** so the output is reusable.
2. **Lab 2 — eval.** **Add Input → Notebook Output → pick your Lab 1 version**, so
   its index + chunks + Q&A set mount under `/kaggle/input/`. Then it scores
   retrieval (recall@k, MRR) and generation (faithfulness, answer relevance) and
   sweeps chunk-size / top-k / reranker. If no Lab 1 input is attached, the first
   cell rebuilds the corpus inline so the lab is self-contained.

## What the T4 changes

- **16 GB VRAM** → the 3B LLM (fp16) + the small embedder fit easily; the FAISS
  index lives in RAM, not VRAM.
- **No bf16** → load the LLM in **fp16**.
- RAG's cost is **retrieval quality and tokens**, not GPU horsepower — most of each
  lab runs CPU-side.

## Notes / gotchas

- **Quota:** ~30 GPU-h/week, ≤12 h/session. Each lab is minutes.
- **Embed once:** building embeddings is the slow step; we cache them to disk so
  re-runs are fast. Change the embedding model → delete the cache and re-embed.
- **Same embedder for docs and queries** — the labs enforce this; it's the most
  common RAG bug.
- **Ephemeral sessions:** outputs vanish unless you Save Version or chain them as
  an input (that's how Lab 2 gets Lab 1's index).
- **LLM-as-judge:** Lab 2's faithfulness score uses Qwen itself as a small judge —
  cheap and offline, but treat it as indicative, not ground truth.
