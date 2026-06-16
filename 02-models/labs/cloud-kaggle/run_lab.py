#!/usr/bin/env python3
"""Kaggle smoke-test of the Models runbook: data-gen -> QLoRA fine-tune -> eval.

Self-contained (no repo deps). Tuned for a Kaggle T4 (16 GB, fp16 — NO bf16).
Mirrors labs 2+3 with a smaller model + capped steps so it finishes in minutes.
Differences vs the 5090 labs are flagged with [T4].
"""
import json, os, random, time
random.seed(0)

# ---- 0. deps (Kaggle base image has torch+transformers; add the rest) --------
os.system("pip -q install -U trl peft bitsandbytes datasets accelerate >/dev/null 2>&1")

import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, PeftModel
from trl import SFTConfig, SFTTrainer

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"   # [T4] smaller than the 5090's 3B, for speed
OUT = "/kaggle/working/adapter"
print("CUDA:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")

# ---- 1. dataset (same task as lab 2: free text -> strict JSON) ---------------
ITEMS = ["lavender shampoo","green tea","running shoes","USB-C cable","yoga mat",
         "coffee beans","phone case","water bottle","notebook","wireless mouse"]
CITIES = ["Hanoi","Ho Chi Minh City","Da Nang","Singapore","Tokyo","Seattle"]
TPL = {"order":["I'd like to order {q} {item}","can I get {q} {item}","buy {q} {item}",
                "please send me {q} {item}","I want {q} {item} shipped to {city}"],
       "cancel":["cancel my order of {item}","I want to cancel the {item}","stop the {item} order"],
       "track":["where is my {item}","track my {item} order","status of my {item}"]}
SYS = ('You are an order-intent parser. Reply with ONLY a JSON object with keys '
       '"intent" (order|cancel|track), "item" (string), "qty" (integer), '
       '"city" (string or null). No prose, no code fences.')

def ex():
    intent = random.choice(list(TPL)); item = random.choice(ITEMS)
    q = random.randint(1,5); city = random.choice(CITIES)
    text = random.choice(TPL[intent]).format(q=q, item=item, city=city)
    has_city = "{city}" in text or random.random() < 0.3
    if "{city}" not in text and has_city: text += f" to {city}"
    tgt = {"intent": intent, "item": item, "qty": q if intent!="track" else 1,
           "city": city if has_city else None}
    return {"messages":[{"role":"system","content":SYS},
                        {"role":"user","content":text},
                        {"role":"assistant","content":json.dumps(tgt, ensure_ascii=False)}]}

rows, seen = [], set()
while len(rows) < 800:
    r = ex(); k = r["messages"][1]["content"]
    if k not in seen: seen.add(k); rows.append(r)
random.shuffle(rows); split = int(len(rows)*0.85)
train, test = rows[:split], rows[split:]
print(f"data: {len(train)} train / {len(test)} test")

# ---- 2. QLoRA fine-tune ------------------------------------------------------
tok = AutoTokenizer.from_pretrained(MODEL)
quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)  # [T4] fp16 compute
model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=quant,
        torch_dtype=torch.float16, device_map="auto")
lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"])
cfg = SFTConfig(output_dir=OUT, max_steps=80, per_device_train_batch_size=4,
        gradient_accumulation_steps=2, learning_rate=2e-4, warmup_ratio=0.03,
        logging_steps=10, fp16=True, bf16=False, max_length=512, report_to="none")  # [T4] fp16
t0 = time.time()
SFTTrainer(model=model, args=cfg, train_dataset=Dataset.from_list(train), peft_config=lora).train()
model.save_pretrained(OUT); tok.save_pretrained(OUT)
print(f"trained in {time.time()-t0:.0f}s | peak VRAM {torch.cuda.max_memory_allocated()/1e9:.1f} GB")

# ---- 3. eval: base vs fine-tuned --------------------------------------------
def gen(m, msgs):
    enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
    enc = {k: v.to(m.device) for k, v in enc.items()}
    with torch.no_grad(): out = m.generate(**enc, max_new_tokens=96, do_sample=False)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()

def parse(t):
    t = t.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try: return json.loads(t)
    except Exception: return None

def score(m):
    v = e = 0
    for t in test:
        gold = json.loads(t["messages"][2]["content"]); p = parse(gen(m, t["messages"][:2]))
        if p is None: continue
        v += 1; e += (p == gold)
    n = len(test); return {"json_valid_%": 100*v/n, "exact_match_%": 100*e/n}

base = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="auto").eval()
base_m = score(base); del base; torch.cuda.empty_cache()
ft = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="auto"), OUT).eval()
ft_m = score(ft)

print("\n=== RESULTS (held-out task eval) ===")
print(f"{'metric':<16}{'BASE':>8}{'TUNED':>8}{'Δ':>8}")
for k in base_m:
    print(f"{k:<16}{base_m[k]:>7.1f}%{ft_m[k]:>7.1f}%{ft_m[k]-base_m[k]:>+7.1f}")
json.dump({"base": base_m, "tuned": ft_m}, open("/kaggle/working/results.json","w"), indent=2)
print("\nwrote /kaggle/working/results.json — KAGGLE_LAB_DONE")
