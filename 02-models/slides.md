---
marp: true
theme: default
paginate: true
size: 16:9
header: 'Models · Layer 2 — choose · serve · evaluate · fine-tune'
style: |
  section { font-size: 26px; }
  h1 { font-size: 44px; }
  h2 { font-size: 34px; }
  code { font-size: 0.8em; }
  pre { font-size: 0.7em; line-height: 1.25; }
  table { font-size: 0.78em; }
  section.lead h1 { font-size: 52px; }
  section.lead { text-align: center; }
  footer, header { color: #888; font-size: 14px; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# Models — deep dive

### Layer 2, hands-on (lab day)

Choose → serve → evaluate → fine-tune → operate, on one RTX 5090.

<!--
This is the half-day deep dive on the Models layer. Same lab box throughout:
RTX 5090, 32 GB. Everything here maps to 02-models/README.md and the labs/.
Pace: ~4 slides of concept, then go to the terminal.
-->

---

## The model lifecycle

A model isn't a file you download once — it's a loop:

```
CHOOSE → REGISTRY → SERVING → EVALUATION ─┐ not good enough?
                                          ├─▶ FINE-TUNE ─┐
                                          └─▶ TRAIN (rare)│
        └──────── MLOps: track · version · monitor ───────┘ back to serving
```

Two rules we keep returning to:

- Need new **knowledge**? → **RAG** (layer 3), not the model.
- Need new **behavior**? → **fine-tune**. Train from scratch almost never.

<!--
Set the frame: most "AI model work" is choosing and serving, not training. The
arrows are the agenda for the rest of the deck.
-->

---

## Choosing — three dimensions

- **Open vs proprietary** — runs on your hardware vs vendor API; control & privacy vs frontier ceiling
- **Size (LLM vs SLM)** — bigger = smarter but heavier; smaller = cheaper + often specialized
- **Specialization** — reasoning · tool-calling · code · language · multimodal

> "Open-weights" ≠ "open-source" — you get weights, not always data or a free
> licence. **Read the licence.**

<!--
You're never picking "the best model" — you're picking the best for a task, a
budget, and a GPU. Qwen2.5 is our default: Apache-2.0, ungated.
-->

---

## The one number: VRAM

```
VRAM(weights) ≈ params × bytes   (fp16=2 · fp8=1 · int4≈0.5)
```

On our **32 GB** RTX 5090:

| size | fp16 | int4 (Q4) | fp16 fits? | Q4 fits? |
|-----:|-----:|----------:|:---------:|:--------:|
| 7–8B | ~15 GB | ~5 GB | ✅ | ✅ |
| 14B | ~28 GB | ~8 GB | ⚠️ tight | ✅ |
| 32B | ~64 GB | ~18 GB | ❌ | ✅ |

This table *is* why quantization exists — and why a 32 GB card runs a 32B model.

<!--
Burn this in. Every "will it fit?" question answers from here. Plus the hidden
cost: KV cache grows with context × concurrency — weights aren't the whole story.
-->

---

## Aside · superintelligence

The far end of the axis: one system above humans in *every* domain.
*(Nick Bostrom, _Superintelligence_, 2014)*

- **Orthogonality** — intelligence and goals are independent. *Smarter ≠ nicer.*
- **Instrumental convergence** — almost any goal → self-preserve + grab resources.
  The **paperclip maximizer**: superb at the *wrong* objective.

> Today's models are *narrow* — hold this as an ethical **horizon**, not a
> forecast. It's why alignment + human-in-the-loop matter in miniature *now*.

<!--
The mirror of the SLM argument: we just praised narrow, specialized models; this
is the opposite pole. Don't sell it as prediction — the book predates LLMs. The
two theses are the keepers: smart doesn't mean safe, and competence at the wrong
goal is the danger. Paperclip maximizer = the one-line icon.
-->

---

## If we built one — four forms of agency

*Bostrom Ch. 10 — least → most autonomy. Maps onto how we ship LLMs today.*

| Form | Core risk | ≈ today |
|------|-----------|---------|
| **Oracle** — answers only | the answer itself manipulates | Q&A chatbot |
| **Genie** — one task, then stops | literal ≠ intended ("be careful what you wish for") | task agent |
| **Sovereign** — open-ended, 24/7 | no off-switch if misaligned | autonomous agent |
| **Tool** — no goals, you drive | optimization can still go agentic | function / tool call |

> Design heuristic for **L4 orchestration**: grant the *least* autonomy that does
> the job, and keep a human in the approval loop.

<!--
This is the part builders can actually use. Walk the right column: students are
already building oracles and genies. Bostrom's safety ranking (oracle/tool safe,
sovereign risky) is a real choice they make when wiring up agents in layer 4.
-->

---

## Serving — two engines, measure the difference

| | Ollama / llama.cpp | vLLM |
|---|---|---|
| Best for | one user, demos | many users, throughput |
| Trick | GGUF + Q4 built in | PagedAttention + batching |
| Feel | snappy single answer | wins at concurrency |

> **Latency** = one fast answer · **throughput** = total tokens/s for everyone.

**Lab 1:** one model (Qwen2.5-3B) at **fp16 vs Q4** on Ollama — Q4 ≈ ½ VRAM,
~1.5× speed. (vLLM optional, for the batching contrast.)

<!--
Go to terminal: download.sh (once) then serve_bench.sh. Validated on the 5090:
Q4 3.8 GB / ~199 tok-s vs fp16 7.8 GB / ~137 tok-s — same model. vLLM is an
optional add to show continuous batching pulling ahead at concurrency.
-->

---

## Fine-tuning — teach behavior, cheaply

Full fine-tune of 7B = weights + grads + optimizer ≈ tens of GB → not on one card.

- **LoRA** — freeze the base, train tiny adapters (<1% of params)
- **QLoRA** — load the base in **4-bit**, train the adapter on top

| method | base | VRAM (7B) |
|--------|------|----------:|
| LoRA | bf16 | ~18–24 GB |
| QLoRA | 4-bit | ~8–12 GB |

> You're not moving 7B weights — you learn a few million adapter numbers.

**Lab 2:** turn Qwen2.5-3B into a strict-JSON order parser; track in **MLflow**.

<!--
This is the headline lab. Before/after is dramatic: base rambles, tuned emits
clean JSON. MLflow makes the run reproducible — params, loss curve, adapter.
-->

---

## Evaluation — numbers, not vibes

| kind | what |
|------|------|
| **Benchmark** | MMLU / GSM8K / ARC — general ability |
| **Task eval** | *your* held-out set + a metric you chose |
| **LLM-judge / human** | preference, helpfulness |

> Pitfalls: **contamination** (memorized benchmarks), Q4 quality (measure it),
> and "one number lies" — report quality **+** speed **+** cost together.

**Lab 3:** base vs fine-tuned on JSON-valid % / exact-match / field accuracy.

<!--
Trust your held-out task eval over leaderboards. This script becomes a CI gate —
a regression blocks deploy, just like checkov blocks terraform apply.
-->

---

## Training & MLOps — the bookends

- **Training from scratch:** trillions of tokens + a cluster (that's why Layer 1
  exists). Millions of dollars, months. We *explain*, we don't run it.
- **MLOps** is the glue: experiment tracking, model/dataset versioning, eval
  gates in CI, drift monitoring.

> Decision tree, almost always: **use → fine-tune → (only then) train.**

<!--
Close the loop. A 5090 can't pre-train — and that's the lesson. MLOps turns a
mystery .bin into a tracked, versioned, deployable artifact.
-->

---

## Models — takeaways

1. It's a **lifecycle**, not a download: choose → serve → eval → adapt → operate
2. **VRAM** governs what runs; **quantization** is the lever
3. **Fine-tune for behavior, RAG for knowledge** — train almost never
4. **Measure** everything — quality *and* speed *and* cost
5. **MLOps** makes it reproducible

<!--
Recap, then hands-on time. If short: VRAM table, LoRA, and the eval-as-CI-gate
are the must-keeps.
-->
