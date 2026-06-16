# 02 · Models

The model is one important piece of the puzzle — not the whole thing. Builders
have huge choice (2M+ models in catalogs like Hugging Face). This layer covers
both **using** models and **building** them.

---

## The mental model: the lifecycle

A model isn't a file you download once — it's something you **choose → serve →
evaluate → (optionally) adapt → operate**. Everything below is a phase of that
loop.

```
            ┌──────────────────────── MLOps (glue: track, version, monitor) ───────────────────────────┐
            │                                                                                          │
  CHOOSE ──▶ REGISTRY ──▶ SERVING ──▶ EVALUATION ──┐                                                   │
   (open?     (what we    (run it,     (is it good   │  not good enough?                               │
    size?      have, ids,  fp16/Q4,     enough?)     ├──▶ FINE-TUNE (LoRA/QLoRA)  ──▶ back to SERVING ─┘
    spec?)     licenses)   tokens/s)                 └──▶ TRAIN (rare) ─────────────▶ back to SERVING
```

Two rules of thumb we keep coming back to:

1. **Need new *knowledge*?** → don't touch the model; use **RAG** ([`03-data/`](../03-data/)).
2. **Need new *behavior* (tone, format, a skill)?** → **fine-tune**. Train from
   scratch almost never.

---

## Phase 1 · Choosing a model — three dimensions

You are almost never choosing "the best model" — you're choosing the best model
**for a task, a budget, and a piece of hardware**. Three axes:

### 1. Open vs proprietary

| | Open-weights (Llama, Qwen, Mistral, Gemma…) | Proprietary API (GPT, Claude, Gemini…) |
|---|---|---|
| **Where it runs** | Your hardware / VPC / laptop | Vendor's cloud only |
| **Control & privacy** | Full — data never leaves | Data goes to the vendor |
| **Cost shape** | Capex/opex on GPUs you run | Per-token; zero idle cost |
| **Customization** | Fine-tune the actual weights | Limited (their fine-tune API) |
| **Ceiling** | Catching up fast | Usually the frontier |

> "Open-weights" ≠ "open-source": you get the weights, not always the training
> data or a permissive licence. **Always read the licence** (see Registry).

### 2. Size — LLM vs SLM

Bigger = more general reasoning, but more VRAM, slower, pricier. Smaller =
cheaper, faster, runs on modest hardware — and often **specialized** to claw back
quality on a narrow task.

**The one number that governs everything on the lab box: VRAM.** A rough sizing
rule for *weights only* (before KV cache / activations):

```
VRAM for weights ≈ params × bytes-per-param
  fp16/bf16 → 2 bytes   |   fp8 → 1 byte   |   int4 (Q4) → ~0.5 byte
```

**On our 32 GB RTX 5090:**

| Model size | fp16 weights | int4 (Q4) weights | Fits at fp16? | Fits at Q4? |
|-----------:|-------------:|------------------:|:-------------:|:-----------:|
| 3B  | ~6 GB  | ~2 GB  | ✅ easily | ✅ |
| 7–8B | ~15 GB | ~4–5 GB | ✅ (room for KV cache) | ✅ |
| 14B | ~28 GB | ~8 GB  | ⚠️ tight (little KV room) | ✅ |
| 32B | ~64 GB | ~18 GB | ❌ | ✅ |
| 70B | ~140 GB | ~40 GB | ❌ | ❌ (needs 2 GPUs) |

This single table is *why quantization exists* and why a 32 GB card can still run
a 32B model. We prove it live in **[Lab 1](labs/01-serving/)**.

### 3. Specialization

A model tuned for a job often beats a bigger generalist *on that job*:

- **Reasoning / "thinking"** (chain-of-thought, math, planning)
- **Tool / function calling** (the agentic layer depends on this)
- **Code** generation
- **Language / region** strengths (e.g. strong Vietnamese)
- **Multimodal** (vision, audio)

> Specialization and size go hand in hand: a fine-tuned 3B can beat a generic 70B
> *on its one task* — that's the whole pitch for SLMs.

---

## Phase 2 · Registry — what we have

Before serving anything, keep an honest catalog. Even a single table is a
registry; mature shops use a tool (MLflow Model Registry, HF Hub, a DB).

| Field | Why it matters |
|-------|----------------|
| **id / version** | Reproducibility — "qwen2.5-3b-instruct @ <commit>" |
| **size & precision** | Drives VRAM and the sizing table above |
| **licence** | Can you use it commercially? Apache-2.0 vs Llama community vs research-only |
| **context length** | How much it can read at once |
| **capabilities** | tools? vision? languages? |
| **source & checksum** | Provenance + integrity |

> Licence traps we'll mention: Llama's "community" licence has a 700M-MAU clause;
> some "open" models are research-only. Qwen2.5 (Apache-2.0) is why we default to
> it in the labs — no gating, commercial-friendly.

---

## Phase 3 · Serving — actually running it

Two questions decide your serving stack: **how fast** (latency vs throughput) and
**how big** (precision / quantization).

### Engines

| Engine | Best for | Notes |
|--------|----------|-------|
| **Ollama** / llama.cpp | Laptops, demos, single users | GGUF + quantization built in; dead simple; CPU+GPU |
| **vLLM** | Servers, many concurrent users | PagedAttention KV cache, continuous batching — high throughput; OpenAI-compatible API |
| **TGI** (HF) | Production HF stack | Similar niche to vLLM |

### The two memory costs

1. **Weights** — fixed (the sizing table above).
2. **KV cache** — grows with **context length × concurrency**. This is the part
   beginners forget: a 7B model at fp16 is ~15 GB, but serve 50 users at 8k
   context and the KV cache can eat another 10 GB+. vLLM's PagedAttention exists
   precisely to manage this.

### Quantization — the lever

Storing weights in fewer bits. Quality drops a little; VRAM and speed improve a
lot.

| Format | Bits | Where | Trade-off |
|--------|:----:|-------|-----------|
| **fp16/bf16** | 16 | training & high-fidelity serving | baseline quality, biggest |
| **fp8** | 8 | Blackwell/Hopper serving | ~2× smaller, tiny quality loss |
| **GGUF Qk_*** | ~4–5 | Ollama/llama.cpp | great for local; Q4_K_M is the sweet spot |
| **AWQ / GPTQ** | 4 | vLLM/GPU serving | 4-bit GPU inference, calibrated |

> **Latency vs throughput**, said once: *latency* = how fast one user gets one
> answer; *throughput* = total tokens/sec across everyone. vLLM trades a little
> latency for big throughput via batching. Ollama optimizes the single-user feel.

**→ [Lab 1: Serving + quantization](labs/01-serving/)** — run Qwen2.5-7B on
Ollama (Q4) and vLLM (fp16), measure tokens/s and VRAM, and watch a 14B model
*only* fit once quantized.

---

## Phase 4 · Evaluation — is it actually good?

"It felt good in the demo" is not evaluation. You need numbers, before and after
any change (a new model, a quant level, a fine-tune).

### Kinds of eval

| Kind | What | Example |
|------|------|---------|
| **Benchmarks** | Standard academic tasks | MMLU, GSM8K, HumanEval, ARC |
| **Task eval** | *Your* held-out set with a metric | exact-match, F1, JSON-valid % |
| **LLM-as-judge** | A strong model scores outputs | rate helpfulness 1–5 |
| **Human eval** | People rate / prefer | A/B, pairwise preference |

### Pitfalls we'll call out

- **Contamination** — benchmark answers leaked into training data. A high MMLU
  can be memorization. Trust *your* held-out task eval more than leaderboard
  numbers.
- **Quantization quality** — measure it; don't assume Q4 ≈ fp16 for *your* task.
- **One number lies** — report quality *and* speed *and* cost together.

**→ [Lab 3: Evaluation](labs/03-eval/)** — `lm-eval-harness` on a small benchmark
plus a custom held-out task, comparing base vs fine-tuned vs quantized.

---

## Phase 5 · Fine-tuning — teaching new behavior

When a base model has the raw ability but not the **tone, format, or task
behavior** you need. Cheaper than training; the workhorse of "build" today.

### Full vs parameter-efficient (PEFT)

Full fine-tuning updates *all* weights — for a 7B model in fp16 that needs the
weights + gradients + optimizer states ≈ **tens of GB beyond the model**, far past
a single 5090 for anything but tiny models.

**LoRA** freezes the base model and trains tiny low-rank "adapter" matrices
(often <1% of params). **QLoRA** goes further: load the base model in **4-bit**,
train the LoRA adapter on top.

| Method | What trains | VRAM (7B) | When |
|--------|-------------|----------:|------|
| **Full FT** | all weights | 🔴 huge | rarely; small models / big clusters |
| **LoRA** | small adapters, base in fp16/bf16 | ~18–24 GB | the default |
| **QLoRA** | small adapters, base in 4-bit | ~8–12 GB | when VRAM is tight / bigger base |

> This is *the* reason a $2k GPU can fine-tune a useful model in 2026: you're not
> moving 7B weights, you're learning a few million adapter numbers. After
> training you can **merge** the adapter back into the weights, or keep it
> separate and hot-swap adapters per task.

**→ [Lab 2: Fine-tune LoRA/QLoRA + MLflow](labs/02-finetune/)** — turn
Qwen2.5-3B-Instruct into a task-specialist with TRL/PEFT, track the run in MLflow,
and compare before/after.

---

## Phase 6 · Training — rarely, and why

Pre-training a foundation model from scratch means **trillions of tokens** and a
**cluster** (recall [Layer 1](../01-infrastructure/) — the BasePOD exists for
exactly this). Cost: millions of dollars and months.

When it's *actually* justified:
- No existing model and no fine-tune can reach the goal.
- A genuinely novel domain/modality or language with no coverage.
- **Continued pre-training** (a softer middle ground): take an open base and keep
  pre-training on a big domain corpus — far cheaper than from zero.

> In class we **explain** training but **don't run it** — a single 5090 can't, and
> that's the point. The decision tree is almost always: *use → fine-tune → (only
> then) train.*

---

## Phase 7 · MLOps — the glue

The DevOps of this layer: makes everything above **reproducible, versioned, and
observable**.

| Concern | Tool examples | What it buys you |
|---------|---------------|------------------|
| **Experiment tracking** | MLflow, Weights & Biases | every run's params, metrics, loss curves |
| **Model & dataset versioning** | MLflow Registry, HF Hub, DVC | "which weights are in prod?" answerable |
| **CI/CD for models** | eval gates in the pipeline | don't ship a regression |
| **Monitoring & drift** | latency, quality, input drift | catch silent decay in prod |

> Without MLOps, a fine-tune is a mystery `.bin` on someone's laptop. With it, the
> run is logged, the metrics are comparable, and the winning model is tagged and
> deployable. We wire **MLflow** into the fine-tune lab so tracking isn't a
> separate chore — it's how we *do* the experiment.

---

## When to build vs buy — the decision in one place

- **Use as-is** — a catalog model already fits. Fastest, cheapest. *Start here.*
- **RAG** ([`03-data/`](../03-data/)) — you need fresh/private **knowledge**.
- **Fine-tune** — you need specific **behavior/format/skill** the base lacks.
- **Train** — no model + no fine-tune will do. Rare and expensive.

> Note: if your goal is to give the model *more knowledge* (e.g. recent
> documents), prefer **RAG** over fine-tuning — cheaper and easier to keep fresh.
> Fine-tune for *behavior*, RAG for *knowledge*.

---

## Labs (run on the RTX 5090)

| Lab | Phase | What you'll do | Time |
|-----|-------|----------------|------|
| **[0 · Bootstrap](labs/README.md)** | env | uv + Python 3.11 + torch (cu128 for Blackwell); GPU sanity | ~10 min |
| **[1 · Serving](labs/01-serving/)** | serving + quant | Ollama Q4 vs vLLM fp16; tokens/s & VRAM; fit a 14B via Q4 | ~45 min |
| **[2 · Fine-tune](labs/02-finetune/)** | fine-tune + mlops | LoRA/QLoRA on Qwen2.5-3B; MLflow tracking; before/after | ~60 min |
| **[3 · Eval](labs/03-eval/)** | evaluation | lm-eval + held-out task; base vs tuned vs quantized | ~45 min |

> All labs assume the bootstrap in [`labs/README.md`](labs/README.md). The 5090 is
> Blackwell (sm_120) — torch must be a **cu128** build, or you'll hit
> "no kernel image available for execution on the device."
</content>
