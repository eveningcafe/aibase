#!/usr/bin/env python3
"""Before/after: run the base model vs the fine-tuned adapter on test prompts.

  python infer_compare.py --adapter adapters/lora
"""
import argparse, json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def load(base, adapter=None):
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16, device_map="auto")
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return tok, model


def gen(tok, model, messages):
    enc = tok.apply_chat_template(messages, add_generation_prompt=True,
                                  return_tensors="pt", return_dict=True)
    enc = {k: v.to(model.device) for k, v in enc.items()}
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=128, do_sample=False)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", default="adapters/lora")
    ap.add_argument("--n", type=int, default=5)
    args = ap.parse_args()

    tests = [json.loads(l) for l in open("data/test.jsonl")][: args.n]

    print("== BASE model ==")
    tok, base = load(args.base, None)
    for t in tests:
        msgs = t["messages"][:2]
        print(f"IN : {msgs[1]['content']}")
        print(f"OUT: {gen(tok, base, msgs)}")
        print(f"GOLD: {t['messages'][2]['content']}\n")
    del base; torch.cuda.empty_cache()

    print("== FINE-TUNED ==")
    tok, ft = load(args.base, args.adapter)
    for t in tests:
        msgs = t["messages"][:2]
        print(f"IN : {msgs[1]['content']}")
        print(f"OUT: {gen(tok, ft, msgs)}")
        print(f"GOLD: {t['messages'][2]['content']}\n")


if __name__ == "__main__":
    main()
