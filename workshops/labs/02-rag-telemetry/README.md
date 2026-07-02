# Case 2 — RAG over telemetry & incident history

Ground the agent in *your* outages: it retrieves past incidents + runbooks
before answering, and cites them. On AgentCore Runtime. In-memory corpus stands
in for the ch03 vector store → nothing to provision.

## Design

```
 operator ─"checkout-api latency is spiking — what do we know?"─┐
                                                               ▼
┌── AgentCore Runtime ───────────────────────────────────────────┐
│  @app.entrypoint invoke()                                      │
│      │                                                         │      ┌ OpenRouter ┐
│      ▼                                                         │◀────▶│ LLM answers│
│   Strands Agent                                                │ HTTP │ from context│
│      │  1. RETRIEVE          2. GROUND + CITE                  │      └────────────┘
│      ▼                                                         │
│   search_incidents(query, k) ──► rank corpus by overlap ──► top-k
│      │                                                         │
│      ▼   _CORPUS  (INC-4821, RUNBOOK-checkout, INC-4102, …)    │
│          ← swap for FAISS/Weaviate + real embeddings (ch03)    │
└────────────────────────────────────────────────────────────────┘

 answer only from retrieved snippets · cite [INC-4821] · else "I don't know"
```

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install bedrock-agentcore-starter-toolkit -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...

# deploy (Runtime is ARM64 — CodeBuild builds it; no local build on amd64)
aws sso login --region ap-southeast-1
agentcore configure --entrypoint agent.py -n rag_telemetry --region ap-southeast-1 -ni
agentcore launch --env OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
agentcore invoke '{"prompt": "checkout-api latency is spiking — who owns it and what do we roll back to?"}'
```

Expect it to cite `[RUNBOOK-checkout]` (Payments squad, roll back to last-good)
and `[INC-4821]` (v2.3 shrank the pool). Ask something off-corpus → "I don't know".

Full RAG pipeline (chunk → embed → vector store → eval): [`../../../03-data`](../../../03-data/).
Managed durable memory (AgentCore Memory): [`../../../05-application`](../../../05-application/).
