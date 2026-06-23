"""
Shared fine-tune entrypoint — Qwen2.5-3B Kubernetes Q&A (QLoRA).

Same task and training logic as Kaggle Lab 2, repackaged as a *platform
entrypoint* so the two reference platforms can run it unchanged:

  - Amazon SageMaker  → Training Job, `entry_point="train.py"`; SageMaker calls
    `python train.py --epochs ...` and mounts channels per its container contract
    (SM_CHANNEL_TRAIN, SM_MODEL_DIR).
  - Kubeflow Trainer  → the `train()` body is also what a `CustomTrainer(func=...)`
    runs; the notebook either bakes this module into the runtime image and calls
    `from train import train`, or inlines the same body.

The data is the **same public Kubernetes Q&A set the 03-data RAG lab uses**
(`ItshMoh/kubernetes_qa_pairs`): one source, two ways to use it — RAG retrieves it
at answer time, this fine-tune bakes it into the weights. Hyperparameters arrive as
CLI flags (SageMaker passes its `hyperparameters` dict this way). Paths follow
SageMaker's contract with local fallbacks, so the same file runs under Kubeflow or
on a laptop unchanged.
"""
import argparse, json, os

SYSTEM = "You are a Kubernetes expert. Answer the question clearly and concisely."


def build_dataset(out_dir, test_frac=0.1, seed=0):
    """Load kubernetes_qa_pairs → 3-message chat JSONL (train + test), de-duped."""
    import random
    from datasets import load_dataset

    raw = load_dataset("ItshMoh/kubernetes_qa_pairs", split="train")
    seen, pairs = set(), []
    for r in raw:
        q, a = (r.get("question") or "").strip(), (r.get("answer") or "").strip()
        if not q or not a or q.lower() in seen:
            continue
        seen.add(q.lower()); pairs.append((q, a))
    random.seed(seed); random.shuffle(pairs)
    cut = int(len(pairs) * (1 - test_frac))

    def to_chat(q, a):
        return {"messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": q},
                             {"role": "assistant", "content": a}]}

    os.makedirs(out_dir, exist_ok=True)
    for name, chunk in [("train.jsonl", pairs[:cut]), ("test.jsonl", pairs[cut:])]:
        with open(os.path.join(out_dir, name), "w") as f:
            for q, a in chunk:
                f.write(json.dumps(to_chat(q, a), ensure_ascii=False) + "\n")
    return os.path.join(out_dir, "train.jsonl")


# ── training: adaptive QLoRA / LoRA, fp16 ────────────────────────────────────
def train(args):
    import torch
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    from peft import LoraConfig
    from trl import SFTConfig, SFTTrainer
    from datasets import load_dataset

    train_file = os.path.join(args.train_dir, "train.jsonl")
    if not os.path.exists(train_file):
        train_file = build_dataset(args.train_dir)
    print("train file:", train_file, "| model dir:", args.model_dir)

    # 4-bit bitsandbytes is reliable on sm_75+ GPUs (T4 / A10G / L4 / L40S);
    # older sm_60 (P100) -> plain LoRA in fp16.
    use_qlora = torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 7
    method = "qlora" if use_qlora else "lora"
    quant = (BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
             bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
             if use_qlora else None)
    print(f"method: {method}  (base in {'4-bit' if use_qlora else 'fp16'})")

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name, quantization_config=quant,
        dtype=torch.float16, device_map="auto")
    lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])
    ds = load_dataset("json", data_files={"train": train_file})["train"]

    cfg = SFTConfig(
        output_dir=args.model_dir,
        per_device_train_batch_size=2, gradient_accumulation_steps=8,
        num_train_epochs=args.epochs, learning_rate=args.lr,
        logging_steps=5, save_strategy="no", max_length=1024, packing=False,
        fp16=False,  # trainable adapters are fp32; bnb computes the 4-bit base in fp16
        optim="paged_adamw_8bit" if use_qlora else "adamw_torch",
        report_to=("mlflow" if os.environ.get("MLFLOW_TRACKING_URI") else "none"))
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, peft_config=lora)
    trainer.train()

    trainer.save_model(args.model_dir)          # adapter -> model dir
    if torch.cuda.is_available():
        print("peak VRAM: %.1f GB" % (torch.cuda.max_memory_allocated() / 1e9))
    print("saved adapter to", args.model_dir)


def _args():
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", default=os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct"))
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--lora_r", type=int, default=16)
    p.add_argument("--lora_alpha", type=int, default=32)
    # SageMaker container contract; sensible local/Kubeflow fallbacks
    p.add_argument("--train_dir", default=os.environ.get("SM_CHANNEL_TRAIN", "data"))
    p.add_argument("--model_dir", default=os.environ.get("SM_MODEL_DIR", "adapters/lora"))
    return p.parse_args()


if __name__ == "__main__":
    train(_args())
