"""Case 2 — RAG over incident history + runbooks, on AgentCore Runtime.

In-memory corpus + naive semantic search (no vector DB to run). Model: OpenRouter.
See README.md.
"""
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models.openai import OpenAIModel

app = BedrockAgentCoreApp()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "sk-or-REPLACE-ME")
MODEL_ID = os.getenv("MODEL_ID", "google/gemma-4-31b-it")

model = OpenAIModel(
    client_args={"api_key": OPENROUTER_API_KEY, "base_url": OPENROUTER_BASE_URL},
    model_id=MODEL_ID,
)

# Stand-in for the vector store from ch03: past incidents + runbooks. A real
# build embeds these and does ANN search; here we keyword-overlap rank.
_CORPUS = [
    ("INC-4821", "checkout-api 5xx spike on 2026-06-30: deploy v2.3 shrank the DB "
                 "connection pool to 5. Fix: rolled back to v2.2 (image :1.0)."),
    ("RUNBOOK-checkout", "checkout-api is owned by the Payments squad. On high "
                         "latency or 5xx, roll back to the last known-good image "
                         "and page Payments on-call."),
    ("INC-4102", "payments-worker OOMKilled after a memory-limit drop; restored by "
                 "raising limits.memory to 512Mi."),
    ("RUNBOOK-db", "Aurora connection exhaustion: check pool size in the app config; "
                   "default healthy pool for checkout-api is 20."),
]


@tool
def search_incidents(query: str, k: int = 3) -> str:
    """Retrieve the most relevant past incidents / runbook snippets for a query."""
    q = set(query.lower().split())
    ranked = sorted(_CORPUS, key=lambda d: len(q & set(d[1].lower().split())), reverse=True)
    hits = [(i, t) for i, t in ranked if q & set(t.lower().split())][:k]
    if not hits:
        return "No relevant records found."
    return "\n".join(f"[{i}] {t}" for i, t in hits)


SYSTEM_PROMPT = (
    "You are an on-call SRE assistant. Answer ONLY from records returned by "
    "search_incidents — call it first, ground every claim in a retrieved snippet, "
    "and cite the record id like [INC-4821]. If the records don't contain the "
    "answer, say you don't know. Be concise."
)


@app.entrypoint
def invoke(payload, context):
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=[search_incidents])
    result = agent(payload.get("prompt", "checkout-api latency is spiking — what do we know?"))
    return {"response": result.message.get("content", [{}])[0].get("text", str(result))}


if __name__ == "__main__":
    app.run()
