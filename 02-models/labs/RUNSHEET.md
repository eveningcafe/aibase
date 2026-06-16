# Instructor runsheet — Models layer (half day, ~3.5 h)

A minute-by-minute spine. Slides = the standalone Models deck
[`../slides.md`](../slides.md) → `02-models/slides.pptx`. Labs run on **free
Kaggle notebooks** (T4 GPU) so every student can follow along.

> **Pre-class:** see [Pre-flight](#pre-flight). Each lab is its own notebook in
> [`cloud-kaggle/`](cloud-kaggle/).

| Time | Block | Slides | Lab / action |
|------|-------|--------|--------------|
| 0:00 | Intro + lifecycle | lead, "model lifecycle" | none — set the loop |
| 0:10 | Choosing + VRAM | "choosing", "the one number: VRAM" | 16 GB sizing math |
| 0:25 | **Lab 1 · Serving** | "serving" | `lab1_serving_kaggle.ipynb` — Run All; read Q4 vs fp16 VRAM |
| 1:10 | Break | — | — |
| 1:20 | Fine-tuning concept | "fine-tuning" | LoRA vs QLoRA |
| 1:35 | **Lab 2 · Fine-tune** | same | `lab2_finetune_kaggle.ipynb` — before → QLoRA train → after; Save Version |
| 2:35 | Evaluation concept | "evaluation" | held-out > leaderboard |
| 2:45 | **Lab 3 · Eval** | same | `lab3_eval_kaggle.ipynb` — add Lab 2 output as input; run task eval + lm-eval |
| 3:15 | Training + MLOps | "training & MLOps" | explain only |
| 3:25 | Takeaways + Q&A | "models — takeaways" | recap the loop |

---

## Pre-flight (do before class)

1. A **phone-verified Kaggle account** (Settings → Phone) — required for GPU +
   Internet.
2. Open each notebook → **Settings → Accelerator = GPU (T4)**, **Internet = On**.
3. **Dry-run Lab 1 and Lab 2 once** so the model + deps are cached and you've got
   a saved Lab 2 version to feed Lab 3. (First run downloads ~6 GB + installs
   deps; later runs are fast.)
4. For Lab 3: **Add Input → Notebook Output → your Lab 2 version**.

## Live flow

- **Lab 1:** Run All. Talk through Q4 (~½ VRAM) vs fp16. On T4 the *speed* is
  about the same — call that out: quantization's memory win is universal, its
  speed win is hardware-dependent.
- **Lab 2:** Run cells in order. Show the BEFORE (base rambles / breaks schema),
  the loss dropping, then AFTER (clean JSON). Peak VRAM prints at the end.
- **Lab 3:** Part A (task eval) is the money slide — exact-match jumps. Part B
  (lm-eval) is slower; skip if quota is tight.

## The five lines to land (one per phase)

1. **Choosing:** you pick for a *task + budget + GPU*, never "the best model."
2. **Serving:** VRAM governs everything; quantization halves it; speed-up is
   hardware-dependent; latency ≠ throughput.
3. **Fine-tune:** you learn a tiny adapter, not 3B weights — that's why it's cheap
   (and why QLoRA fits 16 GB).
4. **Eval:** trust your *held-out task* number over any leaderboard.
5. **MLOps:** the eval is the CI gate; the run is a tracked artifact, not a mystery file.

## If something breaks

| Symptom | Fix |
|---------|-----|
| No GPU / Internet option | account isn't phone-verified |
| `pip`/model download fails | Internet = On in notebook settings |
| OOM on T4 | use QLoRA (4-bit); lower batch size / `max_length` |
| Lab 3 can't find adapter | add Lab 2's **Notebook Output** as an input |
| bf16 error | use fp16 (`fp16=True, bf16=False`) — T4 has no bf16 |
</content>
