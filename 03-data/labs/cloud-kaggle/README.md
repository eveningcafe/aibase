# Data lab on Kaggle (free T4 GPU)

The Data layer lab, as one interactive **Kaggle notebook** — free, browser-based,
and reproducible by any student. We use the **T4 (16 GB)** accelerator and the same
**Qwen2.5-3B-Instruct** as the Models labs.

| Notebook | Lab |
|----------|-----|
| [`lab_rag_kaggle.ipynb`](lab_rag_kaggle.ipynb) | **RAG retrieval, made visible** over a real public k8s Q&A dataset: print the chunks a query loads, top-k, chunk size, a cross-encoder reranker, then a grounded + cited Qwen answer and a refusal |

Data: **`ItshMoh/kubernetes_qa_pairs`** (HF Hub). LLM: **Qwen2.5-3B-Instruct** (T4).
Embedder **`bge-small-en-v1.5`** + reranker **`bge-reranker-base`** (both on CPU).
Vector store: **FAISS**.

## One-time setup (~5 min)

1. **Create a Kaggle account** → https://www.kaggle.com.
2. **Phone-verify** (Settings → Phone). *Required* — without it, kernels can't use
   GPU or Internet, so pip-install and model download fail.
3. In the notebook: **Settings → Accelerator = GPU T4 x2** (not P100),
   **Internet = On**.

## Running it

Upload `lab_rag_kaggle.ipynb` to Kaggle (or import from this repo) and **Run All**.
It is fully self-contained: pulls the dataset, embeds + indexes the answers, then
walks retrieval (which chunks load, top-k, chunk size, reranker) and finishes with
a grounded + cited Qwen answer and a refusal. ~35 minutes, most of it the one-time
model download.

## Notes / gotchas

- **Pick T4, not P100** — the preinstalled PyTorch doesn't support Kaggle's older
  P100 (CUDA `sm_60`); on a P100 the LLM cell errors with `no kernel image`. Set
  **Accelerator = GPU T4 x2** before running.
- **Embedder + reranker on CPU** — both are tiny; running them on CPU is instant
  for this corpus. Only the LLM uses the GPU.
- **No bf16 on T4** → the LLM loads in **fp16**.
- **Quota:** ~30 GPU-h/week, ≤12 h/session. The lab is minutes.
- **First run slow:** installs deps + downloads the model; re-runs reuse the cache.
