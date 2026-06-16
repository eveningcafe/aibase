# Lab 1 · Serving + quantization

**One model — Qwen2.5-3B — served at two precisions.** Same weights, so the only
variable is **fp16 vs Q4**: watch VRAM halve and tokens/s rise.

Prereqs: Lab 0 bootstrap; Ollama installed (see [`../README.md`](../README.md)).

| Phase concept | What we prove |
|---------------|---------------|
| Precision / VRAM | Q4 ≈ ½ the VRAM of fp16 — *identical model* |
| Throughput | Q4 is also *faster* (fewer bytes to move) |
| Quality cost | Q4 isn't free — measured in Lab 3 |
| Latency vs throughput | one fast answer vs total tokens/sec |

---

## Phase 1 · Download (once, ahead of class)

```bash
bash download.sh
```

Pulls the same model twice — `qwen2.5:3b` (Q4_K_M, ~1.9 GB) and
`qwen2.5:3b-instruct-fp16` (~6.2 GB). This is the only network step; keep it
separate so class time is spent *running*, not waiting.

## Phase 2 · Serve & benchmark

```bash
bash serve_bench.sh
```

Serves each precision in turn and runs `bench.py` (single-request latency,
single-stream tokens/s, and aggregate throughput at concurrency 8), printing the
VRAM used for each. `bench.py` does a **warmup** call first so the first timed
request isn't a cold model-load.

To benchmark by hand against either tag:

```bash
python3 bench.py --base-url http://localhost:11434/v1 --model qwen2.5:3b               --concurrency 8
python3 bench.py --base-url http://localhost:11434/v1 --model qwen2.5:3b-instruct-fp16 --concurrency 8
```

---

## Validated on the 5090 ✅

| Qwen2.5-3B | VRAM used | tokens/s (1 req, warm) | tokens/s (aggregate, c8) |
|------------|----------:|-----------------------:|-------------------------:|
| **Q4_K_M** | **3.8 GB** | **~199** | **~268** |
| **fp16**   | **7.8 GB** | **~137** | **~170** |

Read it out loud: **Q4 ≈ half the VRAM and ~1.5× the speed** of fp16 — same model.
That's the lever the whole VRAM sizing table (in [`../README.md`](../README.md))
is built on. The first cold request took ~56 s just to load weights into VRAM —
a good "what's happening?" beat (the warmup hides it from the measurement).

---

## Optional · vLLM throughput contrast

Ollama is single-user oriented; its aggregate barely beats single-stream. **vLLM**
adds continuous batching + PagedAttention, so aggregate throughput climbs steeply
with concurrency. If you installed the vLLM venv:

```bash
source ~/aibase-models-lab/.venv-vllm/bin/activate
bash vllm_serve.sh                                    # same 3B model, fp16, :8000
# new pane:
python3 bench.py --base-url http://localhost:8000/v1 --model Qwen/Qwen2.5-3B-Instruct --concurrency 16
```

Skip it if you didn't install vLLM — the Ollama fp16-vs-Q4 comparison already
makes the quantization point.

## Cleanup

```bash
ollama stop qwen2.5:3b 2>/dev/null; ollama stop qwen2.5:3b-instruct-fp16 2>/dev/null
```
</content>
