#!/usr/bin/env python3
"""Generate a small, synthetic instruction dataset: free-text order -> strict JSON.

Teaches the model ONE specific behavior (emit exactly our JSON schema), so the
before/after is obvious and the result is measurable in Lab 3.

Output: data/train.jsonl, data/test.jsonl  (chat format: {"messages":[...]})
"""
import json, os, random

random.seed(0)  # deterministic — same dataset every class

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


def make_example():
    intent = random.choice(list(INTENTS))
    item = random.choice(ITEMS)
    qty = random.randint(1, 5)
    city = random.choice(CITIES)
    text = random.choice(INTENTS[intent]).format(q=qty, item=item, city=city)
    has_city = "{city}" in text or random.random() < 0.3
    if "{city}" not in text and has_city:
        text += f" to {city}"
    target = {"intent": intent, "item": item,
              "qty": qty if intent != "track" else 1,
              "city": city if has_city else None}
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": text},
        {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)},
    ]}


def main():
    os.makedirs("data", exist_ok=True)
    rows = [make_example() for _ in range(3000)]
    # dedupe on user text to avoid trivial leakage between splits
    seen, uniq = set(), []
    for r in rows:
        key = r["messages"][1]["content"]
        if key not in seen:
            seen.add(key); uniq.append(r)
    random.shuffle(uniq)
    split = int(len(uniq) * 0.85)
    for name, part in [("train", uniq[:split]), ("test", uniq[split:])]:
        with open(f"data/{name}.jsonl", "w") as f:
            for r in part:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"data/{name}.jsonl: {len(part)} examples")


if __name__ == "__main__":
    main()
