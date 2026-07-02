# Case 3 — IaC with AI, and the 3-layer defense

AI writes plausible Terraform fast — and plausible ≠ safe. This agent enforces
the **generate → review → policy gate** loop, with the hard rule *any HIGH
checkov finding blocks apply*. On AgentCore Runtime. Generate + scan simulated.

## Design

```
 operator ─"Terraform for an SSH security group + an S3 bucket"─┐
                                                               ▼
┌── AgentCore Runtime ───────────────────────────────────────────┐
│  @app.entrypoint invoke()                                      │      ┌ OpenRouter ┐
│      ▼                                                         │◀────▶│ LLM drives │
│   Strands Agent                                                │ HTTP │ the gate   │
│                                                                │      └────────────┘
│   L1 generate_terraform ──► L2 review ──► L3 checkov_scan      │
│         ▲                                      │               │
│         │  HIGH found → regenerate secure=True │ PASSED (0 HIGH)│
│         └──────────────────────────────────────┘  → safe to apply
│                                                                │
│   simulated resources ← swap for Terraform MCP + real checkov  │
└────────────────────────────────────────────────────────────────┘

 first pass: SG 0.0.0.0/0 + S3 no public-access-block → 2× HIGH → BLOCKED
 fix pass:  secure=True → 443 from 10.0.0.0/8 + public-access-block → PASSED
```

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install bedrock-agentcore-starter-toolkit -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...

# deploy (Runtime is ARM64 — CodeBuild builds it; no local build on amd64)
aws sso login --region ap-southeast-1
agentcore configure --entrypoint agent.py -n iac_guardrails --region ap-southeast-1 -ni
agentcore launch --env OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
agentcore invoke '{"prompt": "Write Terraform for an SSH security group and an S3 bucket, and only approve it if it passes policy."}'
```

Expect: first scan FAILS (2 HIGH), agent regenerates hardened HCL, re-scan
PASSES, then reports safe to apply. The 3-layer defense: [`../../devops-cases.md`](../../devops-cases.md).
