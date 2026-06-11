# GenAI for SRE — case studies & the math

AI for platform reliability and SRE — *not* coding assistants (those help app
developers, a different job). This is the GenAI-for-SRE role: incident triage,
RCA, runbooks, observability, and CI/CD risk.

The punchline for this course: **an AI-SRE agent exercises the entire stack.**

```
5 · APPLICATION    Slack on-call copilot · NL query · Datadog/PagerDuty
4 · ORCHESTRATION  agent: query logs/metrics/traces → traverse deps → RCA → fix
3 · DATA           vector DB (FAISS/Weaviate): telemetry + incidents + runbooks
2 · MODELS         LLM, prompt-engineered/fine-tuned for logs & remediation
1 · INFRASTRUCTURE GPUs to run it
```

> Figures are as of mid-2026. The dollar math is illustrative — the method
> matters, not the exact numbers.

---

## 1. Incident triage, RCA & remediation

*JD: automate incident triage, remediation, postmortems; on-call copilots; RCA;
self-healing runbooks*

Autonomous AI-SRE agents watch alerts, pull logs/metrics/traces, traverse
dependency graphs, and reason across multiple steps to a root cause and a
proposed fix.

**Tools:** Cleric (Gartner Cool Vendor 2025), Resolve.ai (targets 80%
auto-resolution; $1B valuation, Dec 2025), Traversal, Rootly (Slack-native;
Canva, Grammarly, Squarespace), incident.io (Netflix, Etsy, 600+ companies),
Datadog Bits AI SRE.

**Credible, named numbers** (vs. self-reported marketing):

- **Traversal @ American Express** — **82% RCA accuracy**, **−32% MTTR**, across
  **250B log lines/day**.
- **Microsoft RCACopilot** — **~0.77 RCA accuracy** on a year of real incidents;
  diagnostic collection in use **4+ years** across **30+ teams**; adds retrieval
  augmentation + per-incident-type diagnostic workflows.

**Honest caveats:** vendor "38–90% MTTR reduction" claims are mostly
self-reported and not independently benchmarked. Autonomous remediation is still
**human-in-the-loop** — the AI proposes, a human approves production actions.

## 2. Observability & anomaly detection

*JD: integrate GenAI with Datadog/Prometheus/Grafana/OpenTelemetry; natural-
language querying of platform health; SLIs/SLOs*

- **Datadog Bits Assistant** — query dashboards, logs, traces, and incidents in
  plain language; no query-syntax expertise needed.
- **Grafana Assistant** — natural-language telemetry questions + ML-based
  correlation to flag anomalies.
- **Datadog Toto** — a timeseries foundation model powering anomaly detection
  and forecasting (Watchdog, Bits AI).

The shift: SLI/SLO and pipeline health become **queryable in natural language**,
and anomalies surface proactively instead of waiting on static thresholds.

## 3. RAG over telemetry & incident history

*JD: leverage vector databases (FAISS, Weaviate) to retrieve telemetry and
incident history for GenAI prompts*

AI-SRE grounds the LLM in **your** system via RAG: logs, metrics, traces,
runbooks, deployment metadata, and past postmortems are embedded and stored in a
**vector database (FAISS / Weaviate)**. At incident time the agent retrieves the
most relevant prior incidents and runbook steps and reasons over them — turning
scattered history into queryable **institutional memory**.

This is layer 3 doing real work: without grounding, the model only knows generic
text; with it, it knows *your* outages.

## 4. Infrastructure as Code with AI

*JD: design/operate platforms; automate with GenAI; risk of config/schema
changes*

LLMs now sit inside the Terraform / Pulumi workflow:

- **Generate** modules, resource blocks, and tfvars from a natural-language
  prompt.
- **Explain a plan** — ask *"why is this `terraform plan` destroying prod?"* and
  get a summary without leaving the editor.
- **Policy as code from plain English** — describe a rule; the AI emits a
  Checkov / OPA policy with contextual explanations.
- **Drift detection + remediation** — scheduled read-only `plan`, AI flags and
  suggests fixes.

**Tools:** Pulumi Neo (NL → Pulumi programs; Enterprise $400/mo adds drift +
remediation), env0, Spacelift (OPA policy + orchestration), Terraform MCP
server, Checkov with OpenAI remediation.

> Pair AI-generated IaC with scanners (tfsec ≈ 1000+ checks, Checkov) and
> policy-as-code — the model **hallucinates**. The rule: **AI drafts, the
> pipeline verifies.**

## 5. CI/CD risk & guardrails — the frontier

*JD: blast-radius analysis, deployment guardrails, risk of config/schema
changes, automated validation & rollback*

Emerging and less mature than incident response:

- **Blast-radius analysis** — predict what a change can break before merge.
- **Risk scoring** of config/schema changes prior to rollout.
- **Automated validation & rollback** informed by historical outcomes.

Honest take: far fewer proven products here than in RCA/observability —
greenfield, and strong project territory for a platform team.

## 6. The economics — net of the AI's own cost

```
ILLUSTRATIVE — AI-SRE for incident response
SAVINGS
  SRE time: 200 incidents/mo, MTTR 60→36 min (−40%), 2 SRE × $80/h
    $32,000 → $19,200/mo  → save $12,800/mo
  + downtime avoided (usually the bigger lever): 4 h/mo × $10k/h = $40,000/mo
  gross ≈ $52,800/mo

COST of the AI system:
  platform license (Datadog/Rootly/Resolve.ai)  ~$10–20k/mo
  tokens / inference                              ~$1–3k/mo
  setup & integration (one-time ~$60k → yr1)      ~$5k/mo
  tuning & maintenance (~0.3 FTE)                 ~$3k/mo
                                                  ───────────
  total ≈ ~$20–30k/mo

NET ≈ $52,800 − ~$25,000 ≈ ~$28k/mo  (improves as setup amortizes)
```

A "−40% MTTR" headline says nothing about ROI until you subtract what the system
costs to run: **license + tokens + setup + maintenance**.

---

## Sources

- [Best AI SRE tools 2026 — Prommer](https://prommer.net/en/tech/guides/best-ai-sre-tools-2026/)
- [Bits AI SRE — Datadog](https://www.datadoghq.com/blog/bits-ai-sre-deeper-reasoning/)
- [AI SRE guide — Rootly](https://rootly.com/ai-sre-guide)
- [Automatic RCA via LLMs for cloud incidents (RCACopilot) — Microsoft Research](https://www.microsoft.com/en-us/research/publication/automatic-root-cause-analysis-via-large-language-models-for-cloud-incidents/)
- [Using Terraform with AI — Spacelift](https://spacelift.io/blog/terraform-ai)
