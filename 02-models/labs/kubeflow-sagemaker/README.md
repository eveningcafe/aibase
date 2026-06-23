# Lab · Fine-tune on a platform — Kubeflow & SageMaker

The **same fine-tune as [Kaggle Lab 2](../cloud-kaggle/lab2_finetune_kaggle.ipynb)**
— QLoRA on `Qwen2.5-3B-Instruct` to turn a free-text order message into strict
JSON — but written in the language of the two reference platforms from the
[Systematic view](../../README.md#systematic-view--kubeflow---sagemaker):
**Kubeflow Trainer** (open, on your Kubernetes) and **Amazon SageMaker** (managed).

The point isn't a new model — it's the shift in *shape*. Lab 2 ran everything
inline in one cell. A platform splits the same work into a **training entrypoint**,
a **job you submit**, a **registered model**, and an **endpoint**. The training
code never changes; only how you launch, version, and serve it does.

## Files

| File | What it is |
|------|------------|
| [`train.py`](train.py) | The shared **entrypoint** — the exact QLoRA logic from Lab 2, repackaged. SageMaker runs it as a script; Kubeflow's `CustomTrainer` runs the same `train()` body. |
| [`lab_finetune_kubeflow_sagemaker.ipynb`](lab_finetune_kubeflow_sagemaker.ipynb) | Submits the fine-tune two ways — **Track A: Kubeflow Trainer**, **Track B: SageMaker** — then registers and serves it. |

## How each platform launches `train.py`

| | Kubeflow Trainer | Amazon SageMaker |
|---|---|---|
| Launch idiom | a **function** → `CustomTrainer(func=…)` | a **script** → `HuggingFace(entry_point="train.py")` |
| Hyperparameters | function args | `hyperparameters={…}` → `--flags` |
| Data in | a PVC / volume | `train` channel → `SM_CHANNEL_TRAIN` |
| Model out | a volume → **Kubeflow Hub** | `SM_MODEL_DIR` → S3 → **Model Registry** |
| Serve | **KServe** `InferenceService` | **SageMaker Endpoint** |
| Runs on | **Kubernetes** | **Amazon EKS / EC2** |

`train.py` reads SageMaker's env vars (`SM_CHANNEL_TRAIN`, `SM_MODEL_DIR`) with
local fallbacks, so the *same file* runs under either platform — or on a laptop —
unchanged.

## Prerequisites — read first

> **This is a reference/translation lab, not a free one.** Unlike the Kaggle labs,
> it needs real infrastructure:
>
> - **Track A** — a Kubeflow cluster with **Kubeflow Trainer** installed, run from
>   a **Kubeflow Notebook** (in-cluster credentials). `pip install kubeflow`.
> - **Track B** — an **AWS account** with SageMaker, run from **SageMaker Studio**
>   (or any host with AWS creds). `pip install 'sagemaker>=2.220'`. GPU training
>   instances and endpoints **cost money** — delete the endpoint when done.
>
> The **runnable, free** version of this exact fine-tune is
> [`../cloud-kaggle/lab2_finetune_kaggle.ipynb`](../cloud-kaggle/lab2_finetune_kaggle.ipynb).
> Run whichever track you have access to; read the other to compare idioms.

## The takeaway

Kaggle Lab 2 taught *what* fine-tuning does. This lab shows *how the same step
lives inside a platform*: a registry makes the artifact versioned instead of a
file on a laptop, an eval gate (Lab 3's numbers, as a pipeline step) blocks a
regression before it ships, and a serving surface (KServe / Endpoint) puts it
online — the loop from the [Systematic view](../../README.md#systematic-view--kubeflow---sagemaker),
made real on a cluster.
