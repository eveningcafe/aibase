# Case 4 — CI/CD risk & guardrails

Predict what a change can break *before* merge: blast-radius over the dependency
graph + a risk score from historical outcomes → a gate recommendation. On
AgentCore Runtime. Graph + history simulated.

## Design

```
 operator ─"PR changes db-pool-size on checkout-api. Merge?"─┐
                                                            ▼
┌── AgentCore Runtime ───────────────────────────────────────────┐
│  @app.entrypoint invoke()                                      │      ┌ OpenRouter ┐
│      ▼                                                         │◀────▶│ LLM decides│
│   Strands Agent                                                │ HTTP │ the gate   │
│                                                                │      └────────────┘
│   diff_impact(service) ──► blast radius (N dependents)         │
│   risk_score(service, change_kind) ──► score/100 ──► tier      │
│      │  _DEPENDENTS graph + _HISTORY (deploys, incidents)      │
│      │  ← swap for real dep graph + deploy history             │
│      ▼                                                         │
│   AUTO-MERGE (<25) · REVIEW (25–59) · BLOCK (≥60)              │
└────────────────────────────────────────────────────────────────┘

 checkout-api = 3 dependents · db-pool-size incident rate 33% → high score → BLOCK
 docs-site    = 0 dependents · docs incident rate 0%          → low score  → AUTO-MERGE
```

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install bedrock-agentcore-starter-toolkit -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...

# deploy (Runtime is ARM64 — CodeBuild builds it; no local build on amd64)
aws sso login --region ap-southeast-1
agentcore configure --entrypoint agent.py -n cicd_risk --region ap-southeast-1 -ni
agentcore launch --env OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
agentcore invoke '{"prompt": "A PR changes the db-pool-size on checkout-api. Score the risk and tell me the merge gate."}'
```

Try a `docs` change on `docs-site` to see it recommend AUTO-MERGE instead.
This is the frontier case — background in [`../../devops-cases.md`](../../devops-cases.md).
