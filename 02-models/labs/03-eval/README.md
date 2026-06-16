# Lab 3 · Evaluation

**Goal:** stop saying "it feels better" and put **numbers** on it — both a
standard benchmark and a held-out task eval — comparing base vs fine-tuned.

Prereqs: Lab 2 done (you have `adapters/lora`); deps include `lm-eval`.
Run from `~/aibase-models-lab/labs/03-eval`. **No download phase** — this reuses
the same Qwen2.5-3B already cached in Lab 2 (and served in Lab 1).

| Phase concept | What we prove |
|---------------|---------------|
| Task eval | our held-out set + a metric we chose (JSON-valid, exact-match, field acc) |
| Benchmark | a standardized score (lm-eval-harness) for general ability |
| Why both | a fine-tune lifts the task metric, often barely moves the benchmark |

---

## Part A · Held-out task eval (the one that matters for us)

```bash
python eval_task.py --adapter ../02-finetune/adapters/lora \
                    --test ../02-finetune/data/test.jsonl
```

Prints a base-vs-tuned table on three metrics. Expect the fine-tuned model to
jump on **exact-match** and **JSON-valid** — the behavior we trained.

## Part B · Standardized benchmark

```bash
bash run_lmeval.sh                         # arc_easy, 200 examples, ~minutes
TASKS=gsm8k LIMIT=100 bash run_lmeval.sh   # try another
```

To benchmark the **fine-tuned** model, point lm-eval at the merged weights (or add
`peft=<adapter>` to `--model_args` on recent harness versions).

## Part C · (optional) Quantization quality

Re-run Part A against a quantized serve (e.g. the Ollama Q4 endpoint from Lab 1)
to see whether Q4 costs you task accuracy. Often it's nearly free — *measure,
don't assume.*

---

## What to expect (fill in live)

| metric | BASE | FINE-TUNED | Δ |
|--------|-----:|-----------:|---:|
| json_valid_% | _measure_ | _measure_ | _+_ |
| exact_match_% | _measure_ | _measure_ | _+_ |
| intent_acc_% | _measure_ | _measure_ | _+_ |

> **✅ Validated on the 5090** (0.5B smoke, QLoRA, 179 held-out examples):
> exact-match **30.2% → 86.6%** (+56), intent **52% → 100%**, city **80% → 100%**,
> json-valid **100%** both. The fine-tune mostly fixes *content* accuracy, not JSON
> well-formedness — a good discussion point. The 3B run lands even higher.

## Teaching points

- **Contamination:** a high MMLU can be memorized test data. Your *own* held-out
  task eval is harder to game — trust it more.
- **One number lies:** always report quality **and** speed **and** cost together
  (tie back to Lab 1's tokens/s and VRAM).
- **Eval gates CI:** in MLOps, this script becomes a pipeline gate — a regression
  on `exact_match_%` blocks the deploy, exactly like checkov blocks `apply` in the
  DevOps lecture.
</content>
