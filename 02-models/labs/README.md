# Labs · Models layer (RTX 5090)

Hands-on companion to [`../README.md`](../README.md). Four labs, ~3–4 hours.

| Lab | Topic | Folder |
|-----|-------|--------|
| 0 | **Bootstrap** the node (this file) | — |
| 1 | **Serving + quantization** | [`01-serving/`](01-serving/) |
| 2 | **Fine-tune** LoRA/QLoRA + MLflow | [`02-finetune/`](02-finetune/) |
| 3 | **Evaluation** | [`03-eval/`](03-eval/) |

---

## The lab node

`hoanq-5090-lab-mlops` — **RTX 5090, 32 GB**, Blackwell (sm_120), driver 580,
16 cores, 62 GB RAM, Ubuntu 22.04.

> **Blackwell gotcha (read this).** The 5090 is compute capability **sm_120**.
> PyTorch must be a **cu128** build (torch ≥ 2.7). An older `pip install torch`
> gives the classic error:
> `CUDA error: no kernel image available for execution on the device`.
> Everything below installs the right build.

---

## Lab 0 · Bootstrap

We use **[uv](https://docs.astral.sh/uv/)** (one static binary, no root, no conda)
to manage Python and every dependency.

```bash
# 1. uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"        # add to ~/.bashrc too

# 2. project + Python 3.11 venv
mkdir -p ~/aibase-models-lab && cd ~/aibase-models-lab
uv venv --python 3.11 .venv

# 3. PyTorch for Blackwell (cu128) — the one that matters
uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cu128

# 4. sanity check
.venv/bin/python - <<'PY'
import torch
print("torch", torch.__version__, "| cuda", torch.version.cuda, "| avail", torch.cuda.is_available())
print("device:", torch.cuda.get_device_name(0))
x = torch.randn(4096, 4096, device="cuda"); print("matmul ok:", float((x @ x).sum()) != 0.0)
PY
```

Expected: `torch 2.11.0+cu128 | cuda 12.8 | avail True`, `device: NVIDIA GeForce
RTX 5090`, `matmul ok: True`.

### Per-lab dependencies

Installed once into the same venv (Labs 2 & 3 share these):

```bash
cd ~/aibase-models-lab
uv pip install --python .venv/bin/python \
  transformers accelerate datasets peft trl bitsandbytes \
  mlflow lm-eval "huggingface_hub[cli]"
```

**Ollama** (Lab 1) is a separate server binary:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**vLLM** (Lab 1, *optional*) gets its **own** venv — it pins its own torch and we
don't want it disturbing the training venv. Skip unless you want the throughput
contrast; the Ollama path already teaches serving + quantization:

```bash
uv venv --python 3.11 .venv-vllm
uv pip install --python .venv-vllm/bin/python vllm
```

> **One model across all labs: `Qwen2.5-3B-Instruct`** (Apache-2.0, ungated). Each
> lab has a **download phase** (run once, ahead of class) kept separate from its
> **run phase**, so class time isn't spent waiting on downloads.

---

## Getting the lab scripts onto the node

From your laptop, in the repo root:

```bash
rsync -avz -e 'ssh -p 234' 02-models/labs/ \
  hoanq333@61.28.228.70:~/aibase-models-lab/labs/
```

Then on the node everything runs from `~/aibase-models-lab`.

---

## Teaching from JupyterLab (optional)

A full PyTorch Docker image (NGC / `pytorch/pytorch`) is 7–20 GB — impractical to
pull on a slow link. Instead JupyterLab installs into the **same venv** (~50 MB),
so notebooks share the exact torch/transformers we tested.

On the node:

```bash
cd ~/aibase-models-lab
.venv/bin/jupyter lab --no-browser --port 8888 --ip 127.0.0.1
```

From your laptop, tunnel and open the printed `http://127.0.0.1:8888/?token=…`:

```bash
ssh -p 234 -L 8888:localhost:8888 hoanq333@61.28.228.70
```

Inside a notebook, run any lab script with `%run make_data.py` or open a Jupyter
**terminal** and run them as shown in each lab. (The `.py` scripts are the source
of truth; notebooks are just a friendlier classroom front-end.)

## Conventions used by every lab

- **Run from** `~/aibase-models-lab`; activate with `source .venv/bin/activate`
  (or `.venv-vllm/bin/activate` for vLLM).
- **Long jobs in `tmux`** so an SSH drop doesn't kill training:
  `tmux new -s lab` … detach `Ctrl-b d` … reattach `tmux attach -t lab`.
- **Watch the GPU** in a second pane: `watch -n1 nvidia-smi`.
- **Default model:** Qwen2.5 (Apache-2.0, ungated — no HF login needed).
  A Hugging Face token is optional: `huggingface-cli login` only if you switch to
  a gated model (e.g. Llama).
- **Model cache** lives in `~/.cache/huggingface` (HF) and `~/.ollama` (Ollama).
</content>
