# Case 1 — Incident triage, RCA & remediation

The `checkout-api` 5xx incident, run by an agent on **AgentCore Runtime**. One
prompt drives the layer-04 loop. Tools simulated in-memory → no EKS/IAM.

## Design

```
 operator ─"checkout-api is throwing 5xx, deal with it."─┐
                                                         ▼
┌── AgentCore Runtime · one microVM per session_id ──────────────┐
│  @app.entrypoint invoke()                                      │
│      │                                                         │      ┌ OpenRouter ┐
│      ▼                                                         │◀────▶│ LLM reason │
│   Strands Agent loop                                           │ HTTP │ + tool call│
│      PLAN ──▶ EXECUTE ──▶ REVIEW ──┐                           │      └────────────┘
│       ▲                            │ 5xx<SLO → resolved+RCA    │
│       └──── 5xx still high ────────┘                           │
│      │            │            │                               │
│      ▼            ▼            ▼                               │
│ query_5xx_rate  get_rollout  rollback_deployment               │
│      └────────────┴────────────┘ read/write _STATE (in-mem)    │
│                                   ← swap for real EKS+CloudWatch│
└────────────────────────────────────────────────────────────────┘

 PLAN     query_5xx_rate → 6.2% breach · get_rollout_history → v2.3 @14:30 suspect
 EXECUTE  rollback_deployment(→ :1.0 last-good)      flips _STATE.healthy
 REVIEW   query_5xx_rate → 0.1% (<SLO) → report resolved
```

## Build the agent

`agent.py` is a **skeleton** — its tools and system prompt are `TODO`. Either fill
them in yourself, or start from the verified reference in `example/`:

```bash
cp example/agent.py agent.py     # the complete answer key — then edit as you like
```

The deploy below builds whatever is in `agent.py` (`configure -e agent.py`).

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install bedrock-agentcore-starter-toolkit -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...

# deploy (local build won't work — Runtime is ARM64; CodeBuild builds it)
aws sso login --region ap-southeast-1
agentcore configure --entrypoint agent.py -n incident_rca --region ap-southeast-1 -ni
agentcore launch --env OPENROUTER_API_KEY="$OPENROUTER_API_KEY"

# use a FRESH session-id each run — _STATE lives in the microVM, so replaying the
# same session shows "already healthy" (the rollback from the prior run persisted).
agentcore invoke --session-id "incident-checkout-5xx-$(date +%s)-00000000" \
  '{"prompt": "checkout-api is throwing 5xx, deal with it."}'
```

> The stateful re-use is the point: reuse the id → the warm microVM keeps context
> (a follow-up on the same incident); new id → a fresh incident. That's the
> AgentCore session model.

Real-EKS version + Memory/Observability: [`../../../05-application`](../../../05-application/).
Loop mechanics: [`../../../04-orchestration`](../../../04-orchestration/).
