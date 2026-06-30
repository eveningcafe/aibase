# Quickstart — a calculator agent on AgentCore Runtime

The smallest end-to-end Runtime lab, run before we dig into part 1 (Runtime).
A one-tool Strands agent (`calculator`), wrapped in `@app.entrypoint`, deployed
with the **bedrock-agentcore starter toolkit** — `configure → launch → invoke`.

```
agent.py  ──agentcore configure──▶  Dockerfile + .bedrock_agentcore.yaml
          ──agentcore launch─────▶  CodeBuild (ARM64) → ECR → Runtime
          ──agentcore invoke─────▶  {"prompt": "..."} → microVM → Bedrock (Claude)
```

## Files

| File | What |
|------|------|
| `agent.py` | the agent: `BedrockModel` + `calculator` tool, wrapped in `@app.entrypoint` |
| `requirements.txt` | container deps (the toolkit itself is a dev/CLI dep, not in here) |

---

## Environment notes (this account)

- **Region: `ap-southeast-1`.** An org SCP blocks Bedrock in `us-west-2` and
  `ap-northeast-1`, and the newer Sonnet models are inference-profile-only (the
  `apac.*` profile load-balances into the blocked `ap-northeast-1`). So we pin
  the in-region, on-demand model **`anthropic.claude-3-5-sonnet-20240620-v1:0`**.
- ⚠️ **Bedrock Anthropic use-case form** (Console → Bedrock → Model access →
  Anthropic) must be submitted once, or every Claude call fails with *"Model use
  case details have not been submitted for this account."* (~15 min to propagate).

---

## Run it

### 0. Auth + tooling (one-time)
```bash
aws sso login                      # refresh creds for ap-southeast-1
python3 -m venv .venv && source .venv/bin/activate
pip install bedrock-agentcore-starter-toolkit \
            bedrock-agentcore strands-agents strands-agents-tools
export OPENROUTER_API_KEY=sk-or-... # YOUR real key — the code default is only a placeholder
```

### 1. Configure (writes Dockerfile + .bedrock_agentcore.yaml; auto-creates the exec role/ECR)
```bash
agentcore configure --entrypoint agent.py --region ap-southeast-1
```

### 2. Launch (CodeBuild → ECR → Runtime; no local Docker needed)
```bash
# MUST inject the key, or the deployed agent has only the placeholder and invokes 401:
agentcore launch --env OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
```

### 3. Invoke
```bash
agentcore invoke '{"prompt": "What is 17 * 23 + 5?"}'
```

### Local loop (optional, before deploying)
```bash
agentcore launch --local        # runs the container on :8080
agentcore invoke --local '{"prompt": "What is 12 squared?"}'
```
Local calls **OpenRouter**, so `OPENROUTER_API_KEY` must be exported (step 0); no
AWS Bedrock model access is involved.


## Bonus — an agent with memory (`agent-memory.py`)

Same shape as `agent.py`, but the tools are **persistent memory** instead of a
calculator: an on-call SRE assistant with two tools — `remember(fact)` and
`recall(query)` — that saves durable operational facts and recalls them by
meaning on a later call, even from a fresh session.

It talks directly to **Amazon Bedrock AgentCore Memory** (the resource the
toolkit already provisioned for this project — `memory.memory_id` in
`.bedrock_agentcore.yaml`). Its long-term *SemanticFacts* strategy extracts
facts into the namespace `/users/{actorId}/facts/`. The LLM is still OpenRouter
(plain API key); the Memory APIs are pure IAM (the Runtime exec role, or your
local creds).

### Configure + launch it as its own runtime
```bash
agentcore configure --entrypoint agent-memory.py --region ap-southeast-1
# builds natively on ARM CodeBuild; MUST inject the key or invokes 401:
agentcore launch --env OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
```

### The remember → recall demo (two invokes, with a wait between)

**1. Teach it some facts** — the agent calls `remember(fact=...)`:
```bash
agentcore invoke '{"prompt": "Remember for the team: checkout-api is owned by the Payments squad, its last known-good image is nginx:1.27-alpine, and on high latency the runbook is roll back to that image."}'
```

**2. Wait ~1–2 minutes.** `remember` only stores a raw USER event; AgentCore's
SemanticFacts strategy runs asynchronously to extract durable, searchable facts
into `/users/sre-team/facts/`. Ask too soon and `recall` comes back empty.

**3. Ask a related question** — the agent calls `recall(query=...)` and grounds
its answer in what it stored:
```bash
agentcore invoke '{"prompt": "checkout-api latency is spiking. Who owns it and what image do I roll back to?"}'
```
Expect it to recall *Payments squad* and *nginx:1.27-alpine* — facts it was
never told in this second call.

**Watch it work from the AWS side:**
```bash
# the raw events your remember() wrote (note role=USER):
aws bedrock-agentcore list-events --memory-id quickstart_mem-E1ILI72q9N \
  --actor-id sre-team --session-id <session> --region ap-southeast-1
# the extracted facts recall() reads (empty until extraction finishes):
aws bedrock-agentcore retrieve-memory-records --memory-id quickstart_mem-E1ILI72q9N \
  --namespace "/users/sre-team/facts/" \
  --search-criteria '{"searchQuery":"checkout-api owner"}' --region ap-southeast-1
```

> **Two gotchas this lab already hit** (both fixed in `agent-memory.py`):
> 1. **Role** — facts are extracted only from `USER`-role events, so `remember`
>    writes `role: USER`, not `ASSISTANT`.
> 2. **Namespace** — `recall` must read the exact path the strategy writes to,
>    `/users/{actorId}/facts/`. Any other namespace returns nothing. Confirm the
>    strategies on your memory with `aws bedrock-agentcore-control get-memory
>    --memory-id quickstart_mem-E1ILI72q9N --region ap-southeast-1`.

---

## Cleanup
```bash
agentcore destroy
```
