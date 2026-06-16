# 02 · Models

The model is one important piece of the puzzle — not the whole thing. Builders
have enormous choice (2M+ models in catalogs like Hugging Face), and this layer
covers both **using** a model and **building** on one.

## The lifecycle

A model isn't a file you download once. It moves through a loop:

```
CHOOSE ─▶ REGISTER ─▶ SERVE ─▶ FINE-TUNE ─▶ EVALUATE ─▶ (loop back to serve)
                                  (when needed)
   MLOps wraps the whole loop: track · version · monitor
```

Two rules of thumb run through everything below:

1. Need new **knowledge** (recent or private data)? Use **RAG**
   ([`03-data/`](../03-data/)) — don't touch the model.
2. Need new **behaviour** (tone, format, a specific skill)? **Fine-tune.**
   Training from scratch is almost never the answer.

The phases below follow the loop, and map onto the three hands-on
[labs](#labs-run-on-a-free-kaggle-gpu): Serving (Lab 1), Fine-tuning (Lab 2),
Evaluation (Lab 3).

---

## Phase 1 · Choosing a model

You are rarely choosing "the best model" — you're choosing the best one for a
**task, a budget, and a piece of hardware**. Three axes:

### Open vs proprietary

| | Open-weights (Llama, Qwen, Mistral, Gemma…) | Proprietary API (GPT, Claude, Gemini…) |
|---|---|---|
| **Where it runs** | Your hardware / VPC / laptop | Vendor's cloud only |
| **Control & privacy** | Full — data never leaves | Data goes to the vendor |
| **Cost shape** | Capex/opex on GPUs you run | Per-token; zero idle cost |
| **Customization** | Fine-tune the actual weights | Limited (their fine-tune API) |
| **Ceiling** | Catching up fast | Usually the frontier |

"Open-weights" is not the same as "open-source": you get the weights, but not
always the training data or a permissive licence — so read the licence before you
commit (see Registry).

### Size — LLM vs SLM

Bigger models reason more generally but cost more VRAM, run slower, and cost more
per token. Smaller models are cheaper and faster, and are often **specialized** to
recover quality on a narrow task.

The number that governs what you can run is **VRAM**. A rough rule for weights
only (before KV cache and activations):

```
VRAM for weights ≈ params × bytes-per-param
  fp16/bf16 → 2 bytes   |   fp8 → 1 byte   |   int4 (Q4) → ~0.5 byte
```

On our lab GPU, a free Kaggle **T4 (16 GB)**:

| Model size | fp16 weights | int4 (Q4) weights | Fits at fp16? | Fits at Q4? |
|-----------:|-------------:|------------------:|:-------------:|:-----------:|
| 3B  | ~6 GB  | ~2 GB  | yes | yes |
| 7–8B | ~15 GB | ~4–5 GB | tight | yes |
| 14B | ~28 GB | ~8 GB  | no | yes |
| 32B | ~64 GB | ~18 GB | no | no (needs a bigger GPU) |

On a 16 GB card, quantization is what lets a 7B+ model fit with room for the KV
cache — proven in [Lab 1](labs/cloud-kaggle/lab1_serving_kaggle.ipynb).

### Specialization

A model tuned for a job often beats a larger generalist on that job:

- Reasoning (chain-of-thought, math, planning)
- Tool / function calling — the agentic layer depends on this
- Code generation
- Language / region strengths (e.g. strong Vietnamese)
- Multimodal (vision, audio)

A fine-tuned 3B can beat a generic 70B on its one task. That is the case for
small, specialized models.

---

## Phase 2 · Registry

Before serving anything, keep an honest catalog of the models in use — even a
single table counts; larger teams use a tool (MLflow Model Registry, the HF Hub,
a database).

| Field | Why it matters |
|-------|----------------|
| **id / version** | Reproducibility — "qwen2.5-3b-instruct @ <commit>" |
| **size & precision** | Drives the VRAM math above |
| **licence** | Commercial use? Apache-2.0 vs Llama community vs research-only |
| **context length** | How much it can read at once |
| **capabilities** | tools? vision? languages? |
| **source & checksum** | Provenance + integrity |

### Licences — "open" is a spectrum

"Open-weight" is not "open-source." You almost always get the weights, but rarely
the full training data or code — and the licence attached ranges from truly
permissive to commercial-use-with-strings.

| Tier | Licence | You may… | Examples |
|------|---------|----------|----------|
| **Permissive** | MIT, Apache-2.0 | use commercially, fine-tune, redistribute, self-host — no strings | Qwen2.5 (Apache-2.0), DeepSeek (MIT), Mistral (Apache-2.0) |
| **Conditional open-weight** | "community", "modified MIT", `license: other` | mostly — but with limits: user-count caps, attribution/branding, or written approval | Llama (community licence, 700M-MAU clause) |
| **Restricted** | custom / non-commercial | research and evaluation only | various research-only releases |

The economics behind permissive releases is *commoditize the complement*: give the
weights away, monetize the layer around them (API, enterprise support, cloud). A
free commodity model erodes closed-source vendors' pricing power and buys
developer mindshare. Practical caution: a model can ship permissive early and
**tighten its licence once it's valuable**, so read the licence on every release.
We default to Qwen2.5 (Apache-2.0) in the labs because it is ungated and
commercial-friendly.

---

## Phase 3 · Serving

Two questions decide your serving stack: **how fast** (latency vs throughput) and
**how big** (precision / quantization).

### Engines

| Engine | Best for | Notes |
|--------|----------|-------|
| **Ollama** / llama.cpp | Laptops, demos, single users | GGUF + quantization built in; simple; CPU+GPU |
| **vLLM** | Servers, many concurrent users | PagedAttention + continuous batching; high throughput; OpenAI-compatible API |
| **TGI** (HF) | Production HF stack | Similar niche to vLLM |

### Two memory costs

1. **Weights** — fixed (the sizing table above).
2. **KV cache** — grows with context length × concurrency. A 7B model at fp16 is
   ~15 GB, but serving many users at long context can add another 10 GB+. vLLM's
   PagedAttention exists to manage exactly this.

### Quantization

Storing weights in fewer bits. Quality drops a little; the memory footprint
shrinks a lot, and on the right hardware it also runs faster.

| Format | Bits | Where | Trade-off |
|--------|:----:|-------|-----------|
| **fp16/bf16** | 16 | training & high-fidelity serving | baseline quality, largest |
| **fp8** | 8 | Blackwell/Hopper serving | ~2× smaller, small quality loss |
| **GGUF Qk_*** | ~4–5 | Ollama/llama.cpp | great for local; Q4_K_M is a common sweet spot |
| **AWQ / GPTQ** | 4 | vLLM/GPU serving | 4-bit GPU inference, calibrated |

Latency is how fast one user gets one answer; throughput is total tokens/sec
across everyone. vLLM trades a little latency for much higher throughput via
batching; Ollama optimizes the single-user case.

**→ [Lab 1: Serving + quantization](labs/cloud-kaggle/lab1_serving_kaggle.ipynb)** —
serve Qwen2.5-3B at fp16 vs Q4 on Ollama and measure tokens/s and VRAM. Q4 uses
about half the memory. On the T4 it is not faster (no int4 acceleration); on a
Blackwell GPU it would be. The memory win is universal; the speed win is
hardware-dependent.

---

## Phase 4 · Fine-tuning

Use this when the base model has the raw ability but not the **tone, format, or
task behaviour** you need. It is far cheaper than training, and the most common
way to "build" today.

### Full vs parameter-efficient (PEFT)

Full fine-tuning updates every weight — for a 7B model in fp16 that needs the
weights plus gradients plus optimizer states, tens of GB beyond the model itself,
out of reach of a 16 GB GPU for anything but tiny models.

**LoRA** freezes the base model and trains small low-rank adapter matrices (often
under 1% of the parameters). **QLoRA** goes further: it loads the frozen base in
4-bit, then trains the adapter on top.

| Method | What trains | VRAM (7B) | When |
|--------|-------------|----------:|------|
| **Full FT** | all weights | very high | rarely; small models / large clusters |
| **LoRA** | small adapters, base in fp16/bf16 | ~18–24 GB | the default |
| **QLoRA** | small adapters, base in 4-bit | ~8–12 GB | tight VRAM or a larger base |

This is why a free 16 GB GPU can fine-tune a useful model: you are not moving the
base weights, only learning a few million adapter numbers, and with QLoRA the
frozen base is 4-bit so a 3B fits with room to spare. Afterwards you can merge the
adapter back into the weights, or keep it separate and swap adapters per task.

**→ [Lab 2: Fine-tune LoRA/QLoRA + MLflow](labs/cloud-kaggle/lab2_finetune_kaggle.ipynb)** —
turn Qwen2.5-3B-Instruct into a task specialist with TRL/PEFT, track the run in
MLflow, and compare before and after.

---

## Phase 5 · Evaluation

A demo that "felt good" is not evidence. You need numbers, before and after any
change — a new model, a quant level, or a fine-tune — which is why this phase
closes the loop by comparing the base model against the tuned one.

| Kind | What | Example |
|------|------|---------|
| **Benchmarks** | Standard academic tasks | MMLU, GSM8K, HumanEval, ARC |
| **Task eval** | Your held-out set with a metric | exact-match, F1, JSON-valid % |
| **LLM-as-judge** | A strong model scores outputs | rate helpfulness 1–5 |
| **Human eval** | People rate / prefer | A/B, pairwise preference |

Three things to watch:

- **Contamination** — benchmark answers can leak into training data, so a high
  MMLU may be memorization. Trust your own held-out task eval over leaderboards.
- **Quantization quality** — measure it; don't assume Q4 ≈ fp16 for your task.
- **No single number** — report quality together with speed and cost.

**→ [Lab 3: Evaluation](labs/cloud-kaggle/lab3_eval_kaggle.ipynb)** — `lm-eval-harness`
on a small benchmark plus a held-out task eval, comparing base vs fine-tuned.

---

## Phase 6 · Training

Pre-training a foundation model from scratch means trillions of tokens and a
cluster (recall [Layer 1](../01-infrastructure/) — the BasePOD exists for exactly
this), at a cost of millions of dollars and months of time.

It is justified only when:

- No existing model and no fine-tune can reach the goal.
- The domain, modality, or language genuinely has no coverage.
- **Continued pre-training** is a middle ground: take an open base and keep
  pre-training on a large domain corpus — far cheaper than starting from zero.

We explain training but don't run it — a free Kaggle GPU can't, and that is the
point. The decision path is almost always *use → fine-tune → (only then) train.*

---

## Phase 7 · MLOps

MLOps is the glue that wraps the whole loop. Its job is to give every step a
**versioned input and output** so the pipeline is reproducible, and to **gate**
the bad outputs before they ship.

| Step | In → Out | What MLOps does |
|------|----------|-----------------|
| **Register** | requirement → model id + licence | catalog & version it |
| **Fine-tune** | base + dataset → adapter + loss/metrics | track the run (params, curves); version the adapter + data |
| **Evaluate** | model + held-out set → metric scores | **gate: a regression blocks the deploy** |
| **Serve** | approved model → live endpoint | monitor latency, quality, drift |

The tooling underneath: experiment tracking (MLflow, W&B), model/dataset
versioning (MLflow Registry, HF Hub, DVC), eval gates in CI, and drift monitoring.
Without it a fine-tune is an unlabelled file on a laptop; with it the run is
logged, comparable, and the winning model is tagged and deployable — which is why
Lab 2 wires in MLflow from the start. The eval gate is the same idea as the DevOps
lecture's "checkov blocks `terraform apply`": a failing eval blocks the model
deploy.

---

## When to build vs buy

- **Use as-is** — a catalog model already fits. Fastest and cheapest; start here.
- **RAG** ([`03-data/`](../03-data/)) — you need fresh or private knowledge.
- **Fine-tune** — you need behaviour, format, or a skill the base lacks.
- **Train** — no model and no fine-tune will do. Rare and expensive.

In short: RAG for knowledge, fine-tune for behaviour, train almost never.

---

## Labs (run on a free Kaggle GPU)

Interactive Kaggle notebooks, so any student can reproduce them with no hardware
of their own. We use the **T4 (16 GB)** accelerator. Setup and chaining are in
[`labs/README.md`](labs/README.md) and [`labs/cloud-kaggle/`](labs/cloud-kaggle/).

| Lab | Phase | What you'll do | Time |
|-----|-------|----------------|------|
| **[1 · Serving](labs/cloud-kaggle/lab1_serving_kaggle.ipynb)** | serving + quant | Qwen2.5-3B fp16 vs Q4 on Ollama; tokens/s & VRAM | ~45 min |
| **[2 · Fine-tune](labs/cloud-kaggle/lab2_finetune_kaggle.ipynb)** | fine-tune + mlops | QLoRA on Qwen2.5-3B; MLflow tracking; before/after | ~60 min |
| **[3 · Eval](labs/cloud-kaggle/lab3_eval_kaggle.ipynb)** | evaluation | lm-eval + held-out task; base vs tuned | ~45 min |

Kaggle's free GPU has no bf16, so the labs use fp16 (and
`bnb_4bit_compute_dtype=float16`); with 16 GB of VRAM the fine-tune uses QLoRA.
The account must be phone-verified to enable GPU and Internet.

---

## Aside · the other end of the axis: superintelligence

Everything above is about narrow, specialized intelligence — a 3B that beats a 70B
on one task. Nick Bostrom's *Superintelligence: Paths, Dangers, Strategies* (2014)
asks the opposite question: what if one system exceeds human ability across
virtually every domain?

- **Paths & forms** — most plausibly via better AI (rather than brain emulation or
  cognitive enhancement), and "super" in speed, collective scale, or quality of
  thinking.
- **Takeoff** — recursive self-improvement could compound into an intelligence
  explosion; whether that is slow or fast is debated.
- **Two core ideas:**
  - **Orthogonality** — intelligence and goals are independent; a more capable
    system is not automatically a nicer one.
  - **Instrumental convergence** — almost any final goal implies sub-goals like
    self-preservation and resource acquisition. Hence the paperclip maximizer: a
    system told to make paperclips, taken to the limit, consumes everything to do
    it — not malice, but competence aimed at the wrong objective.
- **Control / alignment** — loading human values into something smarter than us is
  hard, and "just switch it off" fails against a system that anticipates you (the
  treacherous turn).

### Controlling it — four forms of agency (Bostrom, Ch. 10)

If we did build one, what shape should it take? Bostrom frames four configurations,
from least to most autonomy:

| Form | How it works | Control upside | Core risk |
|------|--------------|----------------|-----------|
| **Oracle** | Answers questions only; no actions of its own. | Easiest to sandbox; doesn't touch the world. | The answer itself can manipulate — hidden code or persuasion to free it. |
| **Genie** | Executes one command, then waits for the next. | Bounded; a human approves each task. | Does what you literally said, not what you meant. |
| **Sovereign** | Pursues an open-ended goal autonomously. | Little — full autonomy (the singleton). | Maximal: if alignment isn't solved, there's no off-switch. |
| **Tool** | No goals of its own — software you drive. | No volition or self-preservation drive. | Open-ended optimization can still behave agentically. |

These map onto how we ship LLMs today: a Q&A chatbot is oracle-shaped, a
task-executing agent is a genie, an always-on autonomous agent edges toward
sovereign, and a plain function/tool call is tool-shaped. Bostrom's ordering
(oracle and tool safer, sovereign riskiest) is a useful heuristic for the
orchestration layer ([`04-orchestration/`](../04-orchestration/)): grant the least
autonomy that does the job, and keep a human in the approval loop.

Hold this lightly. Today's models are powerful but narrow — nowhere near this, and
the book predates the LLM era. Treat it as the ethical horizon that makes
alignment, evaluation, and human-in-the-loop matter in miniature now. It is a
lens, not a forecast, and the framing is contested.
</content>
