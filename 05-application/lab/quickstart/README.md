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
```

### 1. Configure (writes Dockerfile + .bedrock_agentcore.yaml; auto-creates the exec role/ECR)
```bash
agentcore configure --entrypoint agent.py --region ap-southeast-1
```

### 2. Launch (CodeBuild → ECR → Runtime; no local Docker needed)
```bash
agentcore launch
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
Local still calls Bedrock, so it needs valid AWS creds in `ap-southeast-1`.

---

## Cleanup
```bash
agentcore destroy
```
