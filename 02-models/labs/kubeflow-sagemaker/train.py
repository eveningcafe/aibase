"""
Shared fine-tune entrypoint — Qwen2.5-3B "order-parser" (QLoRA).

Same task and training logic as Kaggle Lab 2, repackaged as a *platform
entrypoint* so the two reference platforms can run it unchanged:

  - Amazon SageMaker  → Training Job, `entry_point="train.py"`; SageMaker calls
    `python train.py --epochs ...` and mounts channels per its container contract
    (SM_CHANNEL_TRAIN, SM_MODEL_DIR).
  - Kubeflow Trainer  → the `train()` body is also what a `CustomTrainer(func=...)`
    runs; the notebook either bakes this module into the runtime image and calls
    `from train import train`, or inlines the same body.

Hyperparameters arrive as CLI flags (SageMaker passes its `hyperparameters` dict
this way). Paths follow SageMaker's contract and fall back to local dirs, so the
script also runs under Kubeflow or on a laptop with no change.
"""
import argparse, json, os, random

# ── the dataset: free-text order message → strict JSON ───────────────────────
# Identical seeded generator to Lab 2, so results are reproducible across runs
# and platforms. Lives in the entrypoint so no external data channel is required;
# pass a real `--train_dir` (or SageMaker `train` channel) to override.
ITEMS = ["lavender shampoo", "green tea", "running shoes", "USB-C cable",
         "yoga mat", "coffee beans", "phone case", "water bottle",
         "notebook", "wireless mouse", "desk lamp", "protein powder"]
CITIES = ["Hanoi", "Ho Chi Minh City", "Da Nang", "Singapore", "Tokyo", "Seattle"]
INTENTS = {
    "order":  ["I'd like to order {q} {item}", "can I get {q} {item}",
               "please send me {q} {item}", "order {q} {item} for me",
               "buy {q} {item}", "I want {q} {item} shipped to {city}"],
    "cancel": ["cancel my order of {item}", "I want to cancel the {item}",
               "please cancel {q} {item}", "stop the {item} order"],
    "track":  ["where is my {item}", "track my {item} order",
               "status of my {item}", "has my {item} shipped yet"],
}
SYSTEM = ('You are an order-intent parser. Reply with ONLY a JSON object with keys '
          '"intent" (order|cancel|track), "item" (string), "qty" (integer), '
          '"city" (string or null). No prose, no code fences.')


def _example():
    intent = random.choice(list(INTENTS)); item = random.choice(ITEMS)
    qty = random.randint(1, 5); city = random.choice(CITIES)
    text = random.choice(INTENTS[intent]).format(q=qty, item=item, city=city)
    # only one phrasing mentions a city, so `city in text` is the gold signal
    target = {"intent": intent, "item": item,
              "qty": qty if intent != "track" else 1,
              "city": city if city in text else None}
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": text},
        {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)}]}


def build_dataset(out_dir, n_train=1000, n_test=180, seed=0):
    """Write train.jsonl + test.jsonl, de-duped on user text so test isn't leaked."""
    random.seed(seed)
    seen, rows = set(), []
    while len(rows) < n_train + n_test:
        ex = _example(); key = ex["messages"][1]["content"]
        if key in seen:
            continue
        seen.add(key); rows.append(ex)
    os.makedirs(out_dir, exist_ok=True)
    for name, chunk in [("train.jsonl", rows[:n_train]), ("test.jsonl", rows[n_train:])]:
        with open(os.path.join(out_dir, name), "w") as f:
            for r in chunk:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
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
        per_device_train_batch_size=2, gradient_accumulation_steps=4,
        num_train_epochs=args.epochs, learning_rate=args.lr,
        logging_steps=10, save_strategy="no", max_length=512, packing=False,
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
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--lora_r", type=int, default=16)
    p.add_argument("--lora_alpha", type=int, default=32)
    # SageMaker container contract; sensible local/Kubeflow fallbacks
    p.add_argument("--train_dir", default=os.environ.get("SM_CHANNEL_TRAIN", "data"))
    p.add_argument("--model_dir", default=os.environ.get("SM_MODEL_DIR", "adapters/lora"))
    return p.parse_args()


if __name__ == "__main__":
    train(_args())
