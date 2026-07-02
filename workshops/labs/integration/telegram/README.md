# Telegram bridge — 4 bots, one group, each fronting a Runtime

Make the labs interactive: put four bots in one Telegram **group** and `@`-mention
one to talk to its agent. The bridge is a thin client — reasoning stays in the
deployed AgentCore Runtimes.

## Design

```
┌──────────────── Telegram group ─────────────────┐
│  you: "@incident_rca_bot checkout-api 5xx!"      │
│  you: "@rag_telemetry_bot who owns checkout-api?"│
└──────────────────────────────────────────────────┘
        │  each bot has PRIVACY MODE ON (default) →
        │  it ONLY receives msgs that @mention it, reply to it, or /cmd
        ▼   (that IS the router — no central dispatch)
┌──────────── bridge.py (one process, 4 async pollers) ─────────────┐
│  on @mention → strip mention → prompt                              │
│  session_id = tg-<bot>-<chat_id>-e<epoch>   (PER GROUP, ≥33 chars) │
│  boto3 invoke_agent_runtime(ARN, session_id, {"prompt": ...})      │
│  post {"response"} back as a threaded reply                        │
└──────┬──────────────┬──────────────┬──────────────┬───────────────┘
       ▼              ▼              ▼              ▼
 incident_rca   rag_telemetry   iac_guardrails   cicd_risk   (AgentCore Runtimes, live)
```

## Session model (per group)

One conversation = **one group, per bot**. Everyone in the room shares the same
context with each bot; the durable identity (`actor_id`) is the room.

| ID | Value | Why |
|----|-------|-----|
| `session_id` | `tg-<bot>-<chat_id>-e<epoch>` (padded ≥33) | one microVM per (room, bot); deterministic → resumes the warm VM |
| `actor_id` | `tg-room-<chat_id>` | the room as a shared identity (used if a bot enables Memory) |
| epoch | bumped by **`/reset`** | starts a fresh session — needed for the stateful `incident_rca` bot (once it resolves the incident in a session, re-asking shows "already healthy"; `/reset` = fresh incident) |

> `/reset` (unaddressed) is delivered to all four bots → each clears its own room
> session. Use `/reset@incident_rca_bot` to reset just one.

## Setup

**1. Create 4 bots** with [@BotFather](https://t.me/BotFather) (`/newbot` ×4) — keep
each token. Suggested usernames: `..._incident_rca_bot`, `..._rag_telemetry_bot`,
`..._iac_guardrails_bot`, `..._cicd_risk_bot`. Leave **group privacy ON** (default)
— that's what makes `@mention` routing work.

**2. Make a group** (a group/supergroup, *not* a channel — channels are broadcast
and bots can't read mentions there). Add all 4 bots as members.

**3. Run the bridge:**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# tokens from BotFather → a gitignored .env (auto-loaded via python-dotenv)
cp .env.example .env && $EDITOR .env     # paste the four TG_TOKEN_* values

# AWS creds for the Runtimes (same account/region as the labs)
aws sso login --region ap-southeast-1

python bridge.py        # starts one poller per bot with a token set
```

## Try it (in the group)

```
@incident_rca_bot   checkout-api is throwing 5xx, deal with it.
@rag_telemetry_bot  checkout-api latency is spiking — who owns it, what do we roll back to?
@iac_guardrails_bot write Terraform for an SSH SG + S3 bucket, approve only if it passes policy
@cicd_risk_bot      a PR changes db-pool-size on checkout-api — should it merge?
/reset@incident_rca_bot   # fresh incident before re-demoing case 1
```

## Notes

- **ARNs** live in `config.py` (from `workshops/labs/.bedrock_agentcore.yaml`).
  After a redeploy, refresh them (`agentcore status`).
- **No secrets committed** — tokens are read from `TG_TOKEN_*` env vars only.
- **Latency**: a first mention may cold-start the microVM (a few seconds); the bot
  shows a "typing…" action while the Runtime works.
- **1-bot alternative**: you could run a single bot that routes by command
  (`/incident`, `/rag`, …). We use 4 bots so each `@mention` is self-routing via
  privacy mode.
```
