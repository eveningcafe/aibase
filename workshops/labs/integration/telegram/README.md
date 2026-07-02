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
        │  each bot has PRIVACY ON (regular member, not admin) →
        ▼   it receives ONLY msgs that @mention/reply to it (never other chat)
┌──────────── bridge.py (one process, 4 async pollers) ─────────────┐
│  _addressed_to? (mention / reply / DM) — else stay quiet           │
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
`..._iac_guardrails_bot`, `..._cicd_risk_bot`.

**2. Keep group privacy ON** (BotFather default) so each bot receives *only*
messages that @mention it, reply to it, or are commands — never other chatter. If
you changed it earlier, set it back: @BotFather → `/setprivacy` → pick the bot →
**Enable**. Keep bots as **regular members**, not admins (admin bypasses privacy).

**3. Make a group** (a group/supergroup, *not* a channel — channels are broadcast
and bots can't read messages there). Add all 4 bots as members. **Telegram applies
a privacy change only when the bot (re)joins**, so if you just flipped
`/setprivacy`, remove and re-add each bot.

**4. Run the bridge:**

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

**Use `/ask@<bot>` — the reliable trigger.** Telegram always delivers a
slash-command addressed to a bot, even under privacy mode; a plain `@mention` is
*not* delivered to bots in a basic group (convert to a supergroup for that). Only
the addressed bot answers.

```
/ask@demo_incident_rca_bot   checkout-api is throwing 5xx, deal with it.
/ask@demo_rag_telemetry_bot  who owns checkout-api and what do we roll back to?
/ask@demo_iac_guardrails_bot write Terraform for an SSH SG + S3 bucket, approve only if it passes policy
/ask@demo_cicd_risk_bot      a PR changes db-pool-size on checkout-api — should it merge?
/reset@demo_incident_rca_bot # fresh incident before re-demoing case 1
```

A plain `@mention` (or a reply to the bot) also works where Telegram delivers it
(privacy off, supergroups, or 1:1 chats) — same handler underneath.

## Notes

- **ARNs** live in `config.py` (from `workshops/labs/.bedrock_agentcore.yaml`).
  After a redeploy, refresh them (`agentcore status`).
- **No secrets committed** — tokens are read from `TG_TOKEN_*` env vars only.
- **AWS creds**: the bridge signs `invoke_agent_runtime` with the host's creds. On
  SSO those expire after a few hours → replies fail with *"Token has expired"*; run
  `aws sso login` and restart the bridge. For a long-running bot, give the host a
  non-expiring identity (IAM role / instance profile) instead of SSO.
- **Latency**: a first mention may cold-start the microVM (a few seconds); the bot
  shows a "typing…" action while the Runtime works.
- **1-bot alternative**: you could run a single bot that routes by command
  (`/incident`, `/rag`, …). We use 4 bots so each `@mention` is self-routing via
  privacy mode.
```
