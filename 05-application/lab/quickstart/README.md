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

Same shape as `agent.py`, but the tool is **persistent memory** instead of a
calculator: an on-call SRE assistant that *records* durable operational facts
and *retrieves* them by meaning on a later call — even from a fresh session.

It uses the Strands `AgentCoreMemoryToolProvider` over **Amazon Bedrock
AgentCore Memory** (the resource the toolkit already provisioned for this
project — `memory.memory_id` in `.bedrock_agentcore.yaml`). The LLM is still
OpenRouter (plain API key); the Memory APIs are pure IAM (the Runtime exec role,
or your local creds).

### Configure + launch it as its own runtime
```bash
agentcore configure --entrypoint agent-memory.py --region ap-southeast-1
# local needs the key exported (step 0); the deployed microVM needs it via --env:
agentcore launch --local        # or: agentcore launch --env OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
```

### The record → recall demo (two invokes, with a wait between)

**1. Teach it some facts** — the agent calls `agent_core_memory(action="record")`:
```bash
agentcore invoke --local '{"prompt": "Record these for the team: checkout-api is owned by the Payments squad, its last known-good image is nginx:1.27-alpine, and on high latency the runbook is roll back to that image."}'
```

**2. Wait ~2 minutes.** `record` only stores a raw event; AgentCore's long-term
memory *strategies* run asynchronously to extract durable, searchable records.
Ask too soon and `retrieve` comes back empty.

**3. Ask a related question** — the agent calls `agent_core_memory(action="retrieve")`
and grounds its answer in what it stored:
```bash
agentcore invoke --local '{"prompt": "checkout-api latency is spiking. Who owns it and what image do I roll back to?"}'
```
Expect it to recall *Payments squad* and *nginx:1.27-alpine* — facts it was
never told in this second call.

> **Namespace gotcha:** `record` and `retrieve` must share a namespace
> (`MEMORY_NAMESPACE`, default `/sre/runbook`) and the memory's LTM strategy
> must extract into that same path, or searches return nothing.

---

## Cleanup
```bash
agentcore destroy
```
