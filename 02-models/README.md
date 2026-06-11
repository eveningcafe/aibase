# 02 · Models

The model is one important piece of the puzzle — not the whole thing. Builders
have huge choice (2M+ models in catalogs like Hugging Face). This layer covers
both **using** models and **building** them.

## Choosing a model — three dimensions

- **Open vs proprietary** — control, cost, and where it can run.
- **Size** — large language models (LLM) vs small language models (SLM).
  Smaller = lighter hardware, but less general thinking capacity; often
  specialized instead.
- **Specialization** — reasoning, tool calling, code generation, specific
  language strengths. Often goes hand-in-hand with size.

## Use vs build

You can **consume** a model (registry → serving) or **build/adapt** one
(training, fine-tuning) — with **MLOps** tying the lifecycle together.

| Dir | Purpose |
|-----|---------|
| `registry/` | Catalog of models in use: id, size, license, capabilities, cost. |
| `serving/` | Inference servers (vLLM, TGI, Ollama), routing, quantization. |
| `evaluation/` | Benchmarks, eval harnesses, task-level comparisons. |
| `training/` | Pre-training / continued pre-training jobs, datasets, configs. |
| `fine-tuning/` | Task adaptation: SFT, LoRA/QLoRA, PEFT, RLHF/DPO recipes. |
| `mlops/` | Experiment tracking, model versioning & registry, CI/CD, monitoring, drift. |

## When to build vs buy

- **Use as-is** — a catalog model already fits your task. Fastest, cheapest.
- **Fine-tune** — you need a specific tone, format, domain, or task behavior
  the base model lacks. Cheaper than training from scratch.
- **Train** — rare; only when no existing model and no fine-tune will do.

> Note: if your goal is just to give the model *more knowledge* (e.g. recent
> documents), prefer **RAG** in [`03-data/`](../03-data/) over fine-tuning —
> it's cheaper and easier to keep fresh.
