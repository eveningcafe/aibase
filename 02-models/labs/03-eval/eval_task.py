#!/usr/bin/env python3
"""Lab 3 — held-out task eval for the order-parser. Puts numbers on "better".

Compares BASE vs FINE-TUNED on the Lab 2 test set with three metrics:
  - JSON-valid %   : did it emit parseable JSON at all?
  - exact-match %  : does the JSON exactly equal the gold?
  - field accuracy : per-key correctness (intent/item/qty/city)

  python eval_task.py --adapter ../02-finetune/adapters/lora \
                      --test ../02-finetune/data/test.jsonl
"""
import argparse, json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

FIELDS = ["intent", "item", "qty", "city"]


def load(base, adapter=None):
    tok = AutoTokenizer.from_pretrained(base)
    m = AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16, device_map="auto")
    if adapter:
        m = PeftModel.from_pretrained(m, adapter)
    return tok, m.eval()


def gen(tok, model, messages):
    enc = tok.apply_chat_template(messages, add_generation_prompt=True,
                                  return_tensors="pt", return_dict=True)
    enc = {k: v.to(model.device) for k, v in enc.items()}
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=128, do_sample=False)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def try_parse(text):
    # tolerate a stray code fence
    t = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(t)
    except Exception:
        return None


def score(tok, model, tests):
    valid = exact = 0
    field_hits = {f: 0 for f in FIELDS}
    for t in tests:
        gold = json.loads(t["messages"][2]["content"])
        pred = try_parse(gen(tok, model, t["messages"][:2]))
        if pred is None:
            continue
        valid += 1
        if pred == gold:
            exact += 1
        for f in FIELDS:
            if pred.get(f) == gold.get(f):
                field_hits[f] += 1
    n = len(tests)
    return {
        "json_valid_%": 100 * valid / n,
        "exact_match_%": 100 * exact / n,
        **{f"{f}_acc_%": 100 * field_hits[f] / n for f in FIELDS},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", default="../02-finetune/adapters/lora")
    ap.add_argument("--test", default="../02-finetune/data/test.jsonl")
    args = ap.parse_args()
    tests = [json.loads(l) for l in open(args.test)]
    print(f"base: {args.base}  test set: {len(tests)} examples\n")

    tok, base = load(args.base, None)
    base_m = score(tok, base, tests)
    del base; torch.cuda.empty_cache()

    tok, ft = load(args.base, args.adapter)
    ft_m = score(tok, ft, tests)

    keys = list(base_m)
    print(f"{'metric':<16}{'BASE':>10}{'FINE-TUNED':>14}{'Δ':>10}")
    print("-" * 50)
    for k in keys:
        print(f"{k:<16}{base_m[k]:>9.1f}%{ft_m[k]:>13.1f}%{ft_m[k]-base_m[k]:>+9.1f}")


if __name__ == "__main__":
    main()
