# Lab 1 · Serving + quantization

**Goal:** serve the same model two ways, *measure* the difference, and watch
quantization turn a "doesn't fit" model into a "fits" one.

Prereqs: Lab 0 bootstrap done; Ollama installed; `.venv-vllm` created
(see [`../README.md`](../README.md)).

| Phase concept | What we prove |
|---------------|---------------|
| Engines | Ollama (single-user simplicity) vs vLLM (throughput) |
| Precision / VRAM | fp16 vs Q4 weights → the sizing table is real |
| KV cache | concurrency eats VRAM, not just weights |
| Latency vs throughput | one fast answer vs many tokens/sec total |

---

## Part A · Ollama (Q4, the easy path)

```bash
bash ollama_demo.sh
```

What it does: pulls `qwen2.5:7b` (ships **Q4_K_M**, ~4.7 GB), runs a prompt, and
snapshots VRAM. Then it pulls **`qwen2.5:14b`** (Q4, ~9 GB) — a model whose *fp16*
weights (~28 GB) would barely fit, but at Q4 sits comfortably. **This is the
punchline of the quantization story.**

Talk track while it runs:
- 7B Q4 uses ~5–6 GB → tons of headroom on 32 GB.
- 14B Q4 uses ~10–11 GB → still fine. The same 14B at fp16 would leave almost no
  room for KV cache.
- Ollama is great for *one* user. Now contrast throughput with vLLM.

## Part B · vLLM (fp16, the throughput path)

In a `tmux` pane, start the server:

```bash
source ~/aibase-models-lab/.venv-vllm/bin/activate
bash vllm_serve.sh            # serves Qwen2.5-7B-Instruct at :8000 (OpenAI API)
```

Wait for `Application startup complete`. In another pane, benchmark both engines
with the **same** script:

```bash
source ~/aibase-models-lab/.venv/bin/activate   # bench.py is stdlib-only, any venv works

# vLLM (fp16) — OpenAI-compatible on :8000
python bench.py --base-url http://localhost:8000/v1 --model Qwen/Qwen2.5-7B-Instruct --concurrency 16

# Ollama (Q4) — OpenAI-compatible on :11434
python bench.py --base-url http://localhost:11434/v1 --model qwen2.5:7b --concurrency 16
```

`bench.py` reports **single-request latency**, **single-stream tokens/s**, and
**aggregate throughput** at the given concurrency.

---

## What to expect (fill in live)

| Engine / precision | VRAM used | tokens/s (1 req, warm) | tokens/s (aggregate) | notes |
|--------------------|----------:|-----------------------:|---------------------:|-------|
| Ollama Qwen2.5-7B **Q4** | **6.9 GB** ✅ | **~143** ✅ | **~192** (conc. 8) ✅ | single-user friendly |
| vLLM Qwen2.5-7B **fp16** | ~15 GB | _measure_ | _measure_ | batching wins at concurrency |

> ✅ = validated on the 5090. Ollama's aggregate only edges past single-stream
> (it's single-user oriented); vLLM's continuous batching should pull *far* ahead
> at concurrency 16 — that's the contrast to show. `bench.py` does a **warmup**
> first so the single-request number isn't a cold-start (the first cold call took
> 56 s just to load weights into VRAM — a good "what's happening?" teaching beat).

> Teaching point: vLLM's aggregate throughput should pull *well* ahead of Ollama
> as concurrency rises — that's **continuous batching + PagedAttention**. Ollama
> may feel snappier for a single prompt. Different tools, different jobs.

## Cleanup

```bash
# stop vLLM: Ctrl-C in its pane
ollama stop qwen2.5:7b 2>/dev/null; ollama stop qwen2.5:14b 2>/dev/null
```
</content>
