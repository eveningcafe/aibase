# AI in DevOps — case studies & the math

How AI lands on the DevOps/SRE workflow, with real numbers and honest economics
(both the savings *and* the cost of running the AI). Maps to the stack:
**coding assistants** live in the application layer; **AIOps** spans
orchestration + application.

> Every figure below is illustrative unless cited. The point is the *method* of
> reasoning, not the exact numbers.

## Two cost models

| | Coding assistant (SaaS) | AIOps / a system you operate |
|---|---|---|
| Main cost | **Subscription** ($19–39/user/mo) | Platform license + **tokens** + setup + maintenance |
| Tokens | Bundled; overage billed on top | Pay per volume (input/output) |
| Training | None — model is pre-built | Usually *tuning/integration*, not training from scratch |

---

## 1. Coding assistant — GitHub Copilot

*Application layer · efficiency innovation (cost-cutting)*

In a randomized trial with Accenture, GitHub Copilot let developers code **~55%
faster**, with **+8.7% pull requests**, a **+15% merge rate**, and **+84%
successful builds**. 90% of developers reported feeling more fulfilled; 81%
installed it the same day.

### The math — this is cost-cutting, not revenue growth

If productivity rises but company revenue is flat, the gain is **efficiency**:
freed engineering capacity. That capacity is only money if you convert it.

```
Team: 100 devs, fully-loaded ~$120k/dev/yr

BENEFIT (real only if realized):
  coding ≈ 30% of a dev's time · Copilot ~55% faster at coding
  freed capacity ≈ 30% × 55% ≈ ~16% per dev
  ≈ 16 devs' worth ≈ ~$1.9M/yr
  → becomes money only via fewer/deferred hires OR more revenue-driving output

COST:
  Copilot Business  $19 × 100 × 12        = $22,800/yr
  + token overage (usage-based billing)   = variable
                                            ─────────────
                                            ~$25–30k/yr

NET (if realized) ≈ $1.9M − ~$30k ≈ ~$1.87M/yr
```

The subscription is cheap; the real risk is **non-realization** — freed time
becomes slack, not savings. Revenue flat + headcount flat ⇒ the saving exists
only on paper.

## 2. AIOps — incident response

*Orchestration + application · efficiency innovation*

- **PagerDuty AIOps**: cuts alert noise by up to **91%** (correlates thousands
  of alerts into one "situation").
- **PagerDuty + Rundeck**: MTTR for a K8s pod failure dropped from **20 min to
  under 3 min** via automatic pod restarts.
- **HCL + Moogsoft**: MTTR **−33%**, 85% event consolidation, help-desk tickets
  **−62%**.
- **CMC Networks**: MTTR **−38%**. SolarWinds: AI saves an average of **4.87
  hours per incident**.

### The math — count the AI's own cost too

```
SAVINGS:
  SRE time: 200 incidents/mo, MTTR 60→36 min (−40%), 2 SRE × $80/h
    $32,000 → $19,200/mo  → save $12,800/mo
  + downtime avoided (usually the bigger lever): 4 h/mo × $10k/h = $40,000/mo
  gross ≈ $52,800/mo

COST of the AI system:
  platform license (PagerDuty / Moogsoft)   ~$10–20k/mo
  tokens / inference                          ~$1–3k/mo
  setup & integration (one-time ~$60k → yr1)  ~$5k/mo
  tuning & maintenance (~0.3 FTE)             ~$3k/mo
                                              ───────────
  total ≈ ~$20–30k/mo

NET ≈ $52,800 − ~$25,000 ≈ ~$28k/mo  (improves as setup amortizes)
```

A "40% MTTR cut" headline says nothing about ROI until you subtract what the
system costs to run: license + tokens + setup + maintenance.

## 3. The counterpoint — DORA 2024

*Why fundamentals still win*

- **75.9%** of developers use AI daily; ~75% report individual productivity
  gains.
- **But** as AI adoption rose, delivery **throughput fell ~1.5%** and delivery
  **stability fell ~7.2%**.
- Cause: batch sizes grow and trust in AI output rises — so small batches,
  testing, and disciplined CI/CD matter *more*, not less.

The lesson for a DevOps engineer: **individual speed ≠ delivery performance.**
AI speeds up writing code; without the fundamentals, it can make shipping
*worse*. That gap is exactly where DevOps creates value.

---

## Sources

- [Copilot × Accenture study — GitHub Blog](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-in-the-enterprise-with-accenture/)
- [Copilot plans & pricing — GitHub](https://github.com/features/copilot/plans)
- [AIOps incident resolution — PagerDuty](https://www.pagerduty.com/resources/aiops/learn/aiops-use-cases-incident-resolution/)
- [Accelerate State of DevOps Report 2024 — DORA](https://dora.dev/research/2024/dora-report/)
