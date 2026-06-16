#!/usr/bin/env python3
"""Lab 2 — LoRA / QLoRA fine-tune of Qwen2.5-3B-Instruct with TRL, tracked in MLflow.

  python train.py                # LoRA  (base in bf16)
  python train.py --qlora        # QLoRA (base in 4-bit) — lower VRAM

Run `make_data.py` first. View runs with: mlflow ui --port 5000
"""
import argparse, os
os.environ.setdefault("MLFLOW_TRACKING_URI", "sqlite:///" + os.path.abspath("mlflow.db"))
os.environ.setdefault("MLFLOW_EXPERIMENT_NAME", "qwen-order-parser")

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--qlora", action="store_true", help="load base in 4-bit (QLoRA)")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    method = "qlora" if args.qlora else "lora"
    out = args.out or f"adapters/{method}"

    tok = AutoTokenizer.from_pretrained(args.model)

    quant = None
    if args.qlora:
        quant = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)

    model = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=quant,
        dtype=torch.bfloat16, device_map="auto")

    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])

    ds = load_dataset("json", data_files={"train": "data/train.jsonl"})["train"]

    cfg = SFTConfig(
        output_dir=out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=2,
        learning_rate=2e-4,
        warmup_ratio=0.03,
        logging_steps=5,
        bf16=True,
        max_length=512,
        report_to="mlflow",
        run_name=f"{method}-r16",
        save_strategy="epoch",
    )

    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, peft_config=lora)
    print(f"== training {method} on {len(ds)} examples ==")
    trainer.train()
    trainer.save_model(out)
    tok.save_pretrained(out)
    print(f"adapter saved to {out}")
    print(f"VRAM peak: {torch.cuda.max_memory_allocated()/1e9:.1f} GB")


if __name__ == "__main__":
    main()
