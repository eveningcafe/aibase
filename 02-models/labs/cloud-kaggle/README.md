# Cloud smoke-test on Kaggle (free T4)

Run the Models runbook (fine-tune → eval) on a **free Kaggle T4 GPU**, pushed and
fetched **via the Kaggle API** — a cloud check alongside the 5090.

> This is a **smoke test**, not the real lab: smaller model (Qwen2.5-**1.5B**),
> capped steps, and **fp16** (T4 has no bf16). It proves the runbook *logic*; the
> 5090 labs are the teaching environment.

## One-time setup (~5 min)

1. **Create a Kaggle account** → https://www.kaggle.com.
2. **Phone-verify** (Settings → Phone). *Required* — without it, kernels can't use
   GPU or Internet, so pip-install and model download will fail.
3. **API token:** Settings → API → **Create New Token** → downloads
   `kaggle.json`. Put it at `~/.kaggle/kaggle.json` and `chmod 600` it.

## Run it

```bash
cd 02-models/labs/cloud-kaggle
./push.sh <your-kaggle-username>
```

`push.sh` writes `kernel-metadata.json`, pushes `run_lab.py` as a **GPU script
kernel** (Internet on), polls until it finishes, and downloads the output to
`./output/` (run log + `results.json`). You can also watch it live at
`https://www.kaggle.com/code/<username>/aibase-models-runbook`.

## What you get back

`results.json` — the held-out task eval, base vs fine-tuned:

```json
{ "base":  { "json_valid_%": .., "exact_match_%": .. },
  "tuned": { "json_valid_%": .., "exact_match_%": .. } }
```

Expect the **tuned** model to jump on exact-match — same story as Lab 2/3, just on
free cloud hardware.

## Notes / gotchas

- **Quota:** Kaggle gives ~30 GPU-h/week, ≤12 h/session. This run is minutes.
- **No persistent server:** Kaggle is batch — that's why we test fine-tune + eval
  here, not the Ollama/vLLM serving lab.
- **First run slow:** it pip-installs trl/peft/bitsandbytes and downloads the
  model. Re-runs reuse the image cache.
- The push CLI can run from your laptop (has internet) — you don't need the 5090
  for this path.
</content>
