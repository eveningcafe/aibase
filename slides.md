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
5. **GenAI for DevOps** — incident RCA · observability · IaC · CI/CD risk
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

# GenAI for DevOps

<!--
The platform/DevOps job: incident triage, RCA, runbooks, observability, IaC, and
CI/CD risk. It's the capstone — it uses every layer we just covered. (Coding
assistants are dev productivity — a different thing.)
-->

---

## An AI agent for ops = the whole stack

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

An AI agent watches alerts, reads logs / metrics / traces, and proposes a root
cause and a fix.

**Tools:** Cleric · Resolve.ai · Traversal · Rootly · incident.io · Datadog Bits AI

**Proven in production:**

| Where | Result |
|-------|--------|
| Traversal @ American Express | 82% RCA accuracy · −32% MTTR |
| Microsoft RCACopilot | ~0.77 RCA accuracy · 4 yrs, 30+ teams |

> Vendor "38–90% MTTR" claims are self-reported. Remediation stays
> **human-in-the-loop**.

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

## IaC with AI — the real risk

The problem isn't *bad* code. It's **plausible** code — code nobody reads
line-by-line anymore.

A 200-line Terraform module, AI-written in **30 s**. The dev skims it, sees no
syntax errors, runs `apply`. What goes unchecked:

- Security group with ingress `0.0.0.0/0`?
- S3 bucket missing a public-access block?
- RDS without encryption-at-rest? · IAM policy with `Resource: "*"`?
- Secrets hardcoded in `tfvars`?

> **Anti-pattern:** AI generates Terraform → `apply` → 💥
> (no review, no scan, no policy gate)

<!--
Core message of this part. Generate ~30s, review <60s — speed becomes a security
hole when review turns into "tick the box." Second risk: mental-model loss. If a
team stops writing HCL by hand, ask someone to explain an AI module line-by-line
with no docs — if >20% can't, that's a dangerous gap.
-->

---

## What AI tends to get wrong

Common misconfigurations in AI-generated Terraform (approx.):

| # | Misconfiguration | Seen in | Why |
|---|------------------|:------:|-----|
| 1 | Security group `0.0.0.0/0` on 22/3389 | ~25% | common demo examples |
| 2 | S3 missing public-access block | ~20% | not blocked by default |
| 3 | RDS not encrypted | ~18% | encryption is opt-in |
| 4 | IAM `Resource: "*"` | ~15% | convenient in demos |
| 5 | Secrets in `tfvars` (no SOPS) | ~12% | pattern is in training data |
| 6 | Missing tags | ~30% | tag policy is org-specific |
| 7 | Hardcoded creds in provider block | ~5% | rarer, but critical |

<!--
Frequencies are illustrative teaching figures, not a benchmark. The pattern is
real: the model reproduces demo-grade defaults, which are exactly wrong for prod.
-->

---

## The 3-layer defense

```
1 · AI GENERATE    Claude Code + Terraform MCP
                   constraint-first, security-first prompts
        ↓
2 · HUMAN REVIEW   read the plan, understand every resource
                   ask the agent what you don't get — never approve blindly
        ↓
3 · POLICY GATE    tflint → checkov → terraform plan → conftest
                   → AI explains the diff → human approves → apply
                   RULE: checkov not clean (any HIGH) → no apply
```

L1 is fast but **plausible-but-wrong** · L2 catches *intent*, but humans tire ·
L3 is automated & consistent — it catches what humans miss.

<!--
This is the payoff pattern. No single layer is enough: speed (L1) needs judgment
(L2) needs an automated gate (L3). The hard rule lives in L3 — a failing checkov
HIGH blocks apply, no exceptions. That's how you keep AI's speed without its risk.
-->

---

## CI/CD risk & guardrails (the frontier)

Emerging, less mature than incident response:

- **Blast-radius analysis** — LLM predicts what a change can break
- **Risk scoring** of config / schema changes *before* rollout
- **Auto validation & rollback** informed by historical outcomes

> Honest take: fewer proven products here than in RCA/observability — strong
> territory for a platform team to build real differentiation.

<!--
Area 4 of the JD. Be candid: this is greenfield. Great project territory for
students — risk scoring and auto-rollback from historical outcomes.
-->

---

## Takeaways

1. AI is a **stack**, not a model — infra → models → data → orchestration → app
2. Money sits at the **base**; **value** from *applying* AI sits with the
   **operator**
3. Name the innovation type: **market-creating / sustaining / efficiency**
4. Always do the math with **both sides** — savings *and* the AI's own cost
5. In DevOps, **AI drafts — your pipeline verifies**

<!--
Recap in 30 seconds, then open Q&A. If short on time, slides 5 (layers),
the pyramid, and the AI-agent-as-whole-stack are the must-keeps.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Thank you

Questions?

*Speaker notes & full numbers: `README.md` and `docs/devops-cases.md`*

<!--
Likely questions: "should we train our own model?" (no — use/fine-tune/RAG);
"will AI replace devs?" (Klarna rehired; remediation stays human-in-the-loop);
"gross vs net revenue?" (Anthropic example).
-->
