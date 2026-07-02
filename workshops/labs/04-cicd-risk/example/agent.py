"""Case 4 — CI/CD blast-radius + risk scoring, on AgentCore Runtime.

Simulated dependency graph + historical risk (no live CI/deploy). Model:
OpenRouter. See README.md.
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

# Stand-in for a service dependency graph + change-history stats.
_DEPENDENTS = {
    "checkout-api": ["web-frontend", "mobile-bff", "orders-worker"],
    "auth-service": ["checkout-api", "web-frontend", "mobile-bff", "admin-portal"],
    "docs-site": [],
}
_HISTORY = {  # past changes of this kind: (deploys, incidents)
    "db-pool-size": (12, 4),
    "config-only":  (80, 1),
    "docs":         (200, 0),
}


@tool
def diff_impact(service: str) -> str:
    """Blast radius: which services depend on the one being changed."""
    deps = _DEPENDENTS.get(service, [])
    return (f"{service} has {len(deps)} downstream dependents: {', '.join(deps) or 'none'}.")


@tool
def risk_score(service: str, change_kind: str) -> str:
    """Score a change from blast radius + historical incident rate of this change kind."""
    fanout = len(_DEPENDENTS.get(service, []))
    deploys, incidents = _HISTORY.get(change_kind, (10, 1))
    rate = incidents / deploys
    score = min(100, round(fanout * 12 + rate * 100))
    tier = "BLOCK — require senior review" if score >= 60 else \
           "REVIEW — one approval" if score >= 25 else "AUTO-MERGE ok"
    return (f"blast_radius={fanout} dependents · historical_incident_rate={rate:.0%} "
            f"({incidents}/{deploys}) · risk_score={score}/100 → {tier}")


SYSTEM_PROMPT = (
    "You are a CI/CD risk agent. Before a change merges: call diff_impact for the "
    "blast radius, then risk_score for the change kind. Recommend a gate "
    "(auto-merge / require review / block) using the returned score, and justify it "
    "in one line from the numbers. Do not invent numbers — use the tools."
)


@app.entrypoint
def invoke(payload, context):
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT,
                  tools=[diff_impact, risk_score])
    result = agent(payload.get(
        "prompt", "PR changes the db-pool-size on checkout-api. Should it merge?"))
    return {"response": result.message.get("content", [{}])[0].get("text", str(result))}


if __name__ == "__main__":
    app.run()
