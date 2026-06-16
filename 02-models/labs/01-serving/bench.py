#!/usr/bin/env python3
"""Tiny, dependency-free benchmark for any OpenAI-compatible chat endpoint.

Works against vLLM (:8000/v1) and Ollama (:11434/v1). Reports single-request
latency + tokens/s, and aggregate throughput at a chosen concurrency.

  python bench.py --base-url http://localhost:8000/v1 --model Qwen/Qwen2.5-7B-Instruct --concurrency 16
"""
import argparse, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

PROMPT = "Write a clear 150-word explanation of what a GPU does in an AI system."


def call(base_url, model, max_tokens):
    """One non-streaming chat completion. Returns (latency_s, completion_tokens)."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body, headers={"Content-Type": "application/json",
                            "Authorization": "Bearer none"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    dt = time.time() - t0
    usage = data.get("usage") or {}
    toks = usage.get("completion_tokens") or len(data["choices"][0]["message"]["content"].split())
    return dt, toks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--max-tokens", type=int, default=256)
    args = ap.parse_args()

    print(f"endpoint: {args.base_url}  model: {args.model}")

    # 0) warmup — load weights into VRAM so the first timed call isn't a cold start
    print("warming up (loading model into VRAM)...")
    call(args.base_url, args.model, 8)

    # 1) single request — latency + single-stream tokens/s
    dt, toks = call(args.base_url, args.model, args.max_tokens)
    print(f"\n[single]      latency {dt:5.2f}s  | {toks} tok | {toks/dt:6.1f} tok/s")

    # 2) concurrency — aggregate throughput
    n = args.concurrency
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=n) as ex:
        results = list(ex.map(lambda _: call(args.base_url, args.model, args.max_tokens), range(n)))
    wall = time.time() - t0
    total_toks = sum(t for _, t in results)
    avg_lat = sum(d for d, _ in results) / n
    print(f"[concurrency {n:>2}] wall {wall:5.2f}s | {total_toks} tok total "
          f"| {total_toks/wall:6.1f} tok/s aggregate | avg req latency {avg_lat:5.2f}s")


if __name__ == "__main__":
    main()
