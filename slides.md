---
marp: true
theme: default
paginate: true
size: 16:9
header: 'The AI Stack — from infrastructure to application'
style: |
  section { font-size: 26px; }
  h1 { font-size: 44px; }
  h2 { font-size: 34px; }
  code { font-size: 0.8em; }
  pre { font-size: 0.7em; line-height: 1.25; }
  table { font-size: 0.78em; }
  section.lead h1 { font-size: 52px; }
  section.lead { text-align: center; }
  footer, header { color: #888; font-size: 14px; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# The AI Stack

### From infrastructure to application

A map of how AI systems are built — and where the money, the work,
and the value actually are.

<!--
Open: a model is just one piece. Today we map the whole stack, then look at the
money and what it means for DevOps. Figures are as of mid-2026; the CEO-math
numbers are illustrative — the method matters, not the exact dollars.
-->

---

## Agenda

1. **Why a stack?** — a model is one piece
2. **The 5 layers** — infra → models → data → orchestration → application
3. **The business view** — revenue pyramid · 3 types of innovation
4. **Case studies** — chatbot · RAG · the vendor-vs-operator trap
5. **GenAI for SRE** — incident RCA · observability · CI/CD risk · DORA
6. **Takeaways**

<!--
~35-45 min. Stop me with questions during the layers; hold strategy questions
for the business section where they'll be answered.
-->

---

## Why a "stack"?

A model is **one piece**, not the whole system.

To solve a real problem you also need: **compute** to run it, **data** to
ground it, **orchestration** to coordinate it, and an **application** for the
user.

Every choice across the stack drives **quality · speed · cost · safety**.

<!--
Concrete example: a research assistant for new scientific papers. The model
alone can't help — it has a knowledge cutoff, needs GPUs, needs the papers as
data, needs steps to plan/summarize, and a UI. That's the whole stack.
-->

---

## The 5 layers

```
  5 · APPLICATION     interfaces & integrations — the user
  4 · ORCHESTRATION   plan → execute → review — the "brain" (agentic)
  3 · DATA            sources, pipelines, vector store, RAG
  2 · MODELS          open/proprietary · size · specialization
  1 · INFRASTRUCTURE  GPUs — on-premise, cloud, local
```

We'll go bottom → top, then look at the **business** picture.

<!--
You can buy a managed service that hides several layers, or build each yourself.
Either way you should know all five exist — that's how you debug cost/quality.
-->

---

## 1 · Infrastructure

LLMs need **AI-specific hardware (GPUs)**.

Three ways to deploy:

- **On-premise** — own it; full control, high upfront cost
- **Cloud** — rent it; scale up/down on demand
- **Local** — laptop; only the smaller models

> The hardware you can access decides what models you can run at all.

<!--
DevOps tie-in: this is the layer your audience provisions — GPU nodes on k8s,
autoscaling, cost control. The capex here is what feeds the revenue pyramid later.
-->

---

## 2 · Models

Pick along three dimensions:

- **Open vs proprietary** — control, cost, where it runs
- **Size** — large (LLM) vs small (SLM)
- **Specialization** — reasoning, tool-calling, code, language

**Use vs build:** consume a model, **fine-tune** it, or (rarely) **train** it.
Lifecycle glue = **MLOps**.

> Need fresh knowledge, not new behavior? Prefer RAG over fine-tuning.

<!--
Common student misconception: "we must train our own model." Almost never. Use
an existing one; fine-tune for behavior/format; RAG for knowledge. MLOps is the
DevOps of this layer.
-->

---

## 3 · Data

Base models have a **knowledge cutoff** and don't know your private data.

```
sources → pipelines (clean/chunk) → embed → vector store → RAG → model
```

**RAG** retrieves relevant context and augments the prompt — fresh & private
knowledge without retraining.

<!--
RAG = open-book exam vs memorizing. The model looks things up at answer time.
This is what powers the Morgan Stanley case later.
-->

---

## 4 · Orchestration — the agentic layer

One prompt in / one answer out = a **chat box**.
Add the loop and it becomes an **agent**:

```
plan ──▶ execute (tools) ──▶ review ──▶ (loop)
   ▲                                      │
   └──────────── memory / state ◀─────────┘
```

Two kinds: **static** (reliable workflows) + **agentic** (autonomous decisions).
Fastest-moving layer — agents, MCP.

<!--
Key line: orchestration is the mechanism, "agentic" is the behavior. This is the
most hyped layer — remember that when we hit the revenue pyramid (it earns the
least).
-->

---

## 5 · Application

Where AI meets the user. Two questions:

- **Interfaces** — text / image / audio · revisions · citations ·
  *conversational UI replacing forms*
- **Integrations** — inbound (tools feed AI) & outbound (AI output → tools)

> "What the AI *does*" is orchestration. "What the user sees / where the result
> lands" is the application layer.

<!--
Examples: summarize email, text→report, chat replacing a shopping/fintech form.
The brain is layer 4; fitting it into screens + business flow is layer 5.
-->

---

<!-- _class: lead -->

# The business view

Where is the money — and where is the value?

<!--
Shift gears. Students entering AI need orientation: where dollars flow today vs
where value is created. These are two different questions.
-->

---

## Revenue pyramid (mid-2026)

```
              ┌──────────────┐
              │     APPS     │  fragmented startups
            ┌─┴──────────────┴─┐
            │  ORCHESTRATION   │  LangChain ~$16M ARR
          ┌─┴──────────────────┴─┐
          │        DATA          │  Scale AI ~$2B
        ┌─┴──────────────────────┴─┐
        │   FOUNDATION MODELS      │  OpenAI ~$33B · Anthropic ~$45B*
      ┌─┴──────────────────────────┴─┐
      │   INFRASTRUCTURE / CHIPS      │  Nvidia ~$75B/qtr → ~$300B run-rate
      └──────────────────────────────┘
```

Revenue concentrates at the **base** (Nvidia alone > all model companies).
**Hype ≠ revenue** — orchestration gets the most attention, the least money
(LangChain ≈ 1/18,000 of Nvidia).

<!--
Figures mid-2026. *Anthropic ~$45B is gross (books cloud-reseller spend);
~$22B net — always ask gross or net. Anthropic just passed OpenAI. Punchline:
the most-talked-about layer earns the least.
-->

---

## Three types of innovation

*Clayton Christensen — a lens for any AI product*

| Type | Idea | Jobs | AI example |
|------|------|------|------------|
| **Market-creating** | expensive/hard → cheap for all | creates | foundation models for everyone |
| **Sustaining** | make a good product better | neutral | an AI feature in your app |
| **Efficiency** | same work, less cost | reduces | coding assistants, automation |

The type isn't the *layer* — it's how the tech is **used**.

<!--
Ask the room: "Copilot — which type?" Efficiency. "ChatGPT launch?"
Market-creating. Same LLM, different use → different type. AI coding = efficiency
= cost-cutting, which sets up the math.
-->

---

## Case · sales / support chatbot

**Klarna × OpenAI:** 2.3M chats in month 1 = **700 agents'** work,
**67%** automated, 11 min → **<2 min**, **~$40M** profit (2024).
*Caveat: cut too deep, rehired in 2025 — AI-first, not AI-only.*

```
ILLUSTRATIVE — 100,000 contacts/mo · human $5 · AI $1 · 67% deflection
  AI handles  67,000 × $1 = $67k/mo
  vs humans   67,000 × $5 = $335k/mo
  net saving  ≈ $268k/mo  ≈ $3.2M/yr
```

Players: Sierra · Decagon · Ada · Intercom Fin

<!--
Say out loud: these dollar numbers are illustrative, not Klarna's books. The
$0.99/resolution is Intercom Fin's real public price. The Klarna rehire is the
honest part — don't sell AI as headcount-zero.
-->

---

## Case · RAG over internal docs

**Morgan Stanley × OpenAI**

- Indexed **350,000 documents (40M words)** with RAG
- Before: **30+ min** manual search · advisors reached **~20%** of knowledge
- After: instant · **98%** of teams use it · access **20% → 80%**

Frees advisor time for client work; answers grounded in verified sources.

Similar: Glean · Harvey · Hebbia

<!--
This is layer 3 (data/RAG) in production. Value here is time saved + better
answers, not a flashy chatbot. Real, measured adoption (98%).
-->

---

## The trap: vendor value vs operator value

The pyramid measures who earns money **selling** AI → base wins.

Case studies measure value from **applying** AI → lands on the *operator's*
books.

> Klarna's $40M isn't an "AI app company" revenue line — it's on **Klarna's**
> P&L. The app layer looks thin for vendors, yet is where operators win.

<!--
This resolves the apparent contradiction: pyramid says app layer is thin, but
case studies show huge value. Two different questions. Most students in this
room will be operators, not AI vendors — the value is on their side.
-->

---

<!-- _class: lead -->

# GenAI for SRE

Not coding assistants — reliability, observability, and incident response.

<!--
Reframe: coding assistants help app devs, not platform/SRE. This section is the
GenAI-for-SRE job: triage, RCA, runbooks, observability, CI/CD risk. And it's
the capstone — it uses every layer we just covered.
-->

---

## An AI-SRE agent = the whole stack

```
  5 · APPLICATION    Slack on-call copilot · NL query · Datadog/PagerDuty
  4 · ORCHESTRATION  agent: query logs/metrics/traces → traverse deps → RCA
  3 · DATA           vector DB (FAISS/Weaviate): telemetry + incidents + runbooks
  2 · MODELS         LLM, prompt-engineered/fine-tuned for logs & remediation
  1 · INFRASTRUCTURE GPUs to run it
```

This is *why* we learned the stack: a production SRE assistant exercises **all
five layers** at once.

<!--
Payoff slide. Tie the whole lecture together. Walk bottom-up: the agent runs on
GPUs, uses an LLM, grounds on a vector DB of your telemetry + past incidents +
runbooks (RAG), orchestrates multi-step investigation, and meets the on-call
engineer in Slack. Map each to the JD they'll be hiring against.
-->

---

## Incident triage, RCA & remediation

Autonomous AI-SRE agents investigate alerts, correlate signals, and propose root
cause + fix:

- **Cleric** · **Resolve.ai** (targets 80% auto-resolution) · **Traversal**
- **Rootly** · **incident.io** (Netflix, Etsy, 600+) · **Datadog Bits AI SRE**

Credible numbers (named, not just marketing):
- **Traversal @ American Express**: **82% RCA accuracy**, **−32% MTTR**, 250B log lines/day
- **Microsoft RCACopilot**: **~0.77 RCA accuracy**, in use 4 yrs across 30+ teams

> Most vendor "38–90% MTTR" claims are self-reported. Autonomous remediation is
> still **human-in-the-loop**.

<!--
Area 1+2 of the JD. Stress: the credible numbers come with a named customer or a
published study; treat vendor ranges skeptically. Self-healing exists but humans
approve production actions.
-->

---

## Observability: ask telemetry in English

NL querying + anomaly detection on top of your existing tools (Datadog,
Prometheus, Grafana, OpenTelemetry):

- **Datadog Bits Assistant** — query dashboards/logs/traces in plain language
- **Grafana Assistant** — NL telemetry questions + ML correlation
- **Datadog Toto** — timeseries foundation model powering anomaly forecasting

Grounding = **RAG over telemetry + incident history + runbooks** in a vector DB
(FAISS / Weaviate), so the LLM reasons over *your* system, not generic text.

<!--
Areas 2+3 of the JD. The big shift: SLI/SLO and platform health become
queryable in natural language. The vector DB of incident history is the
"institutional memory" — this is layer 3 doing real work in SRE.
-->

---

## CI/CD risk & guardrails (the frontier)

Emerging, less mature than incident response:

- **Blast-radius analysis** — LLM predicts what a change can break
- **Risk scoring** of config/schema changes *before* rollout
- **Auto validation & rollback** informed by historical outcomes

> Honest take: fewer proven products here than in RCA/observability. This is
> where a platform team can build real differentiation — and where the DORA
> warning bites hardest.

<!--
Area 4 of the JD. Be candid: this is greenfield. Great project territory for
students. Naturally leads into DORA — speed at the deploy gate without
discipline is dangerous.
-->

---

## The economics (net of the AI's own cost)

```
ILLUSTRATIVE — AI-SRE for incident response
SAVINGS  SRE time ~$12.8k/mo + downtime avoided ~$40k/mo ≈ $52.8k/mo
COST     license + tokens + setup + maintenance       ≈ $20–30k/mo
NET                                                    ≈ ~$28k/mo
```

A "−40% MTTR" headline says nothing about ROI until you **subtract the AI's own
cost**: license + tokens + setup + maintenance.

<!--
Same discipline as the chatbot math. Vendors quote only savings. Downtime
avoided is usually the biggest line but hardest to estimate honestly. Numbers
illustrative.
-->

---

## The counterpoint (DORA 2024)

- **75.9%** of devs use AI daily · ~75% feel more productive
- **But:** delivery **throughput −1.5%**, **stability −7.2%** as adoption rose
- Cause: batch sizes grow, trust in AI output rises

> **Individual speed ≠ delivery performance.** Without small batches, testing,
> and disciplined CI/CD, AI can make shipping *worse*. That gap is where DevOps
> creates value.

<!--
The most important slide for this audience. AI is not a silver bullet. Your job
— pipelines, testing, small batches — matters MORE in the AI era, not less. End
the DevOps section on this.
-->

---

## Takeaways

1. AI is a **stack**, not a model — infra → models → data → orchestration → app
2. Money sits at the **base**; **value** from *applying* AI sits with the
   **operator**
3. Name the innovation type: **market-creating / sustaining / efficiency**
4. Always do the math with **both sides** — savings *and* the AI's own cost
5. In DevOps, **fundamentals still win**

<!--
Recap in 30 seconds, then open Q&A. If short on time, slides 5 (layers),
pyramid, and DORA are the must-keeps.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Thank you

Questions?

*Speaker notes & full numbers: `README.md` and `docs/devops-cases.md`*

<!--
Likely questions: "should we train our own model?" (no — use/fine-tune/RAG);
"will AI replace devs?" (Klarna rehired; DORA shows fundamentals win);
"gross vs net revenue?" (Anthropic example).
-->
