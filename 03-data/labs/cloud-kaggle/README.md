# Data labs on Kaggle (free T4 GPU)

The Data layer as two interactive **Kaggle notebooks** — free, browser-based, and
reproducible by any student. We use the **T4 (16 GB)** accelerator and the same
**Qwen2.5-3B-Instruct** as the Models labs.

| Notebook | Lab |
|----------|-----|
| [`lab1_simple_rag_kaggle.ipynb`](lab1_simple_rag_kaggle.ipynb) | **Simple RAG, made visible** (Chapter 1) over a tidy k8s Q&A dataset: print the chunks a query loads, top-k, chunk size, then a grounded + cited Qwen answer and a refusal |
| [`lab2_advanced_rag_kaggle.ipynb`](lab2_advanced_rag_kaggle.ipynb) | **Advanced RAG over the real k8s docs** (Chapter 2): clean + 128-token chunk the `kubernetes/website` docs, add metadata filtering, hybrid (BM25), and a reranker, then measure them on an independent eval set (hit@3, MRR) |

Data: Lab 1 — **`ItshMoh/kubernetes_qa_pairs`** (HF Hub); Lab 2 — the real
**`kubernetes/website`** docs (cloned in-notebook). LLM: **Qwen2.5-3B-Instruct** (T4).
Embedder **`bge-small-en-v1.5`** + reranker **`bge-reranker-base`** (both on CPU).
Vector store: **FAISS**.

## One-time setup (~5 min)

1. **Create a Kaggle account** → https://www.kaggle.com.
2. **Phone-verify** (Settings → Phone). *Required* — without it, kernels can't use
   GPU or Internet, so pip-install and model download fail.
3. In the notebook: **Settings → Accelerator = GPU T4 x2** (not P100),
   **Internet = On**.

## Running it

Upload either notebook to Kaggle (or import from this repo) and **Run All** — each is
fully self-contained. **Lab 1** pulls the Q&A dataset, embeds + indexes the answers,
walks retrieval (which chunks load, top-k, chunk size), and finishes with a grounded +
cited Qwen answer and a refusal. **Lab 2** clones the real k8s docs, cleans + 128-token
chunks them (~9k chunks), then adds metadata filtering, hybrid (BM25), and a reranker,
and evaluates on an independent set (hit@3, MRR). Lab 1 ~25 min; Lab 2 ~12 min
(most of it embedding ~9k chunks on CPU + the one-time model download).

## Notes / gotchas

- **Pick T4, not P100** — the preinstalled PyTorch doesn't support Kaggle's older
  P100 (CUDA `sm_60`); on a P100 the LLM cell errors with `no kernel image`. The labs
  put the LLM cell **last and guard it**, so on P100 the CPU core (chunk/index/eval)
  still completes — but set **Accelerator = GPU T4 x2** to get the grounded answer.
- **Embedder + reranker on CPU** — both are tiny; only the LLM uses the GPU. Lab 2
  embeds ~9k chunks on CPU in ~6 min.
- **No bf16 on T4** → the LLM loads in **fp16**.
- **Quota:** ~30 GPU-h/week, ≤12 h/session. The lab is minutes.
- **First run slow:** installs deps + downloads the model; re-runs reuse the cache.
