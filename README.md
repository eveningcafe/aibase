t# aibase

A full-stack AI platform — **from infrastructure to application**.

The repo is organized around the **5 layers of the AI stack**. Each choice you
make at any layer — from the hardware up to the user interface — has direct
implications on the solution's **quality, speed, cost, and safety**.

```
aibase/
├── 01-infrastructure/   # GPUs & compute: on-premise, cloud, local
├── 02-models/           # model registry, serving, evaluation
├── 03-data/             # sources, pipelines, vector store, RAG
├── 04-orchestration/    # planning, execution, review, MCP
├── 05-application/       # interfaces & integrations
├── shared/              # cross-cutting config & scripts
└── docs/                # design notes, references
```

## The 5 layers

| # | Layer | What it covers |
|---|-------|----------------|
| 1 | **Infrastructure** | AI hardware (GPUs). Deploy on-premise, in the cloud, or locally. |
| 2 | **Models** | Open vs proprietary, large vs small (LLM/SLM), specialization. |
| 3 | **Data** | Data sources, processing pipelines, vector databases, RAG. |
| 4 | **Orchestration** | Break tasks into thinking → execution → review. Protocols like MCP. |
| 5 | **Application** | Interfaces (text/image/audio…) and integrations with other tools. |

## Where the money is today — the revenue pyramid

Revenue across the stack is a pyramid: the closer a layer sits to the
**hardware at the base**, the more of today's money it captures (figures
mid-2026).

```
                    ┌──────────────┐
                    │     APPS     │  L5 · fragmented, many startups
                  ┌─┴──────────────┴─┐
                  │  ORCHESTRATION   │  L4 · LangChain ~$16M ARR — max hype, min revenue
                ┌─┴──────────────────┴─┐
                │        DATA          │  L3 · Scale AI ~$2B (Meta took 49%)
              ┌─┴──────────────────────┴─┐
              │   FOUNDATION MODELS      │  L2 · OpenAI ~$33B · Anthropic ~$45B*
            ┌─┴──────────────────────────┴─┐
            │   INFRASTRUCTURE / CHIPS     │  L1 · Nvidia ~$75B/qtr → ~$300B run-rate
            └──────────────────────────────┘
                    base = most $ captured today
```

| Layer | Who | Revenue (mid-2026) |
|-------|-----|----------------|
| **1 · Infrastructure / chips** | Nvidia data-center | ~$75B/qtr (Q1 FY27, +92% YoY) → ~$300B run-rate |
| **2 · Foundation models** | OpenAI / Anthropic | ~$33B / ~$45B ARR — Anthropic now leads* |
| **3 · Data** | Scale AI; vector DBs | ~$2B; Meta bought a 49% stake ($14.3B) |
| **4 · Orchestration** | LangChain | ~$16M ARR |
| **5 · Applications** | thousands of startups | fragmented, individually small |

\* Anthropic's ~$45B is gross (it books cloud-reseller end-customer spend as
revenue); on OpenAI's preferred net basis it's ~$22B. *Always ask: gross or net?*

Two things to notice: revenue concentrates at the base (Nvidia alone, ~$300B
run-rate, earns more than every model company combined), and **hype ≠ revenue**
— the orchestration layer gets the most attention but captures the least money
(LangChain is ~1/18,000th of Nvidia). Value is expected to shift up toward
applications over time, as it did when cloud value moved from AWS infrastructure
to SaaS apps.

## The three types of innovation

A lens for reading any AI product. Clayton Christensen (Harvard, *The
Innovator's Dilemma*) splits innovation into three types:

| Type | Idea | Effect on jobs | AI example |
|------|------|----------------|------------|
| **Market-creating** | Make something expensive/hard → cheap & easy for everyone, opening a *new* market | Creates jobs | Foundation models that put AI in everyone's hands |
| **Sustaining** | Make a good product *better* | Roughly neutral | Adding an AI feature to an app you already use |
| **Efficiency** | Do the *same work with less* | Tends to reduce jobs | AI coding assistants, automation, summarization |

The type is *not* decided by the layer — it's decided by *how the technology
gets used*. The same model can create a new market, improve a product, or cut
costs. Reading an AI launch, ask: *which of the three is this?*

## Case studies

### Sales / support chatbot — layers 4–5, grounded by 3

Klarna's AI assistant (built on OpenAI) handled 2.3M chats in its first month —
the work of **700 full-time agents** — automating **67%** of conversations,
cutting resolution from 11 min to under 2 min, and driving a **~$40M profit
improvement** in 2024. Caveat: in 2025 Klarna said it had cut human staff too
far and rehired for premium support — AI-first, not AI-only.

Others in the space: Sierra, Decagon, Ada, Intercom Fin (public price ~$0.99 per
resolution).

**CEO math** — a mid-size store, 100,000 support contacts/month:

```
human cost       ~$5 / contact      (fully loaded)
AI cost          ~$1 / resolution   (Intercom Fin public price)
AI deflection    67%                (Klarna / Fin benchmark)

AI handles       100,000 × 67%    = 67,000 contacts
  cost on AI     67,000 × $1      = $67,000 / mo
  same on humans 67,000 × $5      = $335,000 / mo
  ──────────────────────────────────────────────
  net saving     ≈ $268,000 / mo  ≈ $3.2M / yr
```

The lever is **volume × deflection rate × (human − AI cost)**, plus 24/7 and
multilingual coverage.

### RAG over internal documents — layer 3

Morgan Stanley indexed **350,000 research documents (40M words)** with RAG.
Before: a query meant 30+ minutes of manual search, and advisors reached only
~20% of the knowledge base. After: instant answers, **98% of advisor teams** use
it, and document access rose from 20% to 80% — freeing advisor time for
revenue-generating client work, with answers grounded in verified sources.

Similar: Glean (enterprise search), Harvey (legal), Hebbia (finance).

### Why these thrive even though the pyramid calls the top "thin"

The pyramid measures who earns money **selling** AI tooling — there the base
wins. These case studies measure value created by **applying** AI to your own
business — and that value lands on the operator's books, not an AI vendor's.
Klarna's $40M isn't any "AI app company" revenue; it's a line on Klarna's P&L.
So the application layer looks thin for vendors yet is where operators capture
the most. Two different questions, two different winners.

For GenAI-for-SRE cases (incident RCA, observability, CI/CD risk) with full
cost-and-savings math, see [`docs/devops-cases.md`](docs/devops-cases.md).

## Getting started

Each layer directory has its own `README.md` describing scope and intended
contents. Start at `01-infrastructure/` and work up, or jump to the layer you
need.
