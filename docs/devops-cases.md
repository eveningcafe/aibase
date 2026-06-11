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

## 4. Infrastructure as Code with AI — and its biggest risk

*JD: design/operate platforms; automate with GenAI; risk of config/schema
changes*

AI can write a Terraform module in seconds. The danger isn't *bad* code — it's
**plausible** code: code that looks right, so nobody reads it line-by-line.

### The plausible-code problem

A 200-line AI-written module — network rules, IAM, storage — generated in ~30 s.
The dev skims the structure, sees no syntax errors, runs `terraform apply`. What
goes unchecked:

- Security group with ingress `0.0.0.0/0`?
- S3 bucket missing a public-access block?
- RDS without encryption-at-rest?
- IAM policy with `Resource: "*"`?
- Secrets hardcoded in `tfvars`?

Generate ~30 s, review <60 s. **Speed becomes a security hole when review turns
into "tick the box."**

Second risk — **mental-model loss**: when a team stops writing HCL by hand, it
loses the model of its own infrastructure. Quick test: ask someone to explain an
AI-generated module line-by-line with no docs. If >20% can't, that's a dangerous
gap.

**Anti-pattern (vibe-coding IaC to prod):** AI generates → `apply` → 💥, with no
review, no scan, no policy gate.

### What AI tends to get wrong (approx.)

| # | Misconfiguration | Seen in | Why |
|---|------------------|:------:|-----|
| 1 | Security group `0.0.0.0/0` on 22/3389 | ~25% | common demo examples |
| 2 | S3 missing public-access block | ~20% | not blocked by default |
| 3 | RDS not encrypted | ~18% | encryption is opt-in |
| 4 | IAM `Resource: "*"` | ~15% | convenient in demos |
| 5 | Secrets in `tfvars` (no SOPS) | ~12% | pattern is in training data |
| 6 | Missing tags | ~30% | tag policy is org-specific |
| 7 | Hardcoded creds in provider block | ~5% | rarer, but critical |

*(Frequencies are illustrative teaching figures, not a benchmark.)*

### The 3-layer defense

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

Why all three: **L1** is fast but plausible-but-wrong; **L2** catches *intent*
errors, but humans tire and skip; **L3** is automated and consistent — it catches
the misconfigurations humans miss. The hard rule lives in L3: a failing checkov
HIGH blocks `apply`, no exceptions.

## 5. CI/CD risk & guardrails — the frontier

*JD: blast-radius analysis, deployment guardrails, risk of config/schema
changes, automated validation & rollback*

Emerging and less mature than incident response:

- **Blast-radius analysis** — predict what a change can break before merge.
- **Risk scoring** of config/schema changes prior to rollout.
- **Automated validation & rollback** informed by historical outcomes.

Honest take: far fewer proven products here than in RCA/observability —
greenfield, and strong project territory for a platform team.

---

## Sources

- [Best AI SRE tools 2026 — Prommer](https://prommer.net/en/tech/guides/best-ai-sre-tools-2026/)
- [Bits AI SRE — Datadog](https://www.datadoghq.com/blog/bits-ai-sre-deeper-reasoning/)
- [AI SRE guide — Rootly](https://rootly.com/ai-sre-guide)
- [Automatic RCA via LLMs for cloud incidents (RCACopilot) — Microsoft Research](https://www.microsoft.com/en-us/research/publication/automatic-root-cause-analysis-via-large-language-models-for-cloud-incidents/)
- [Using Terraform with AI — Spacelift](https://spacelift.io/blog/terraform-ai)
