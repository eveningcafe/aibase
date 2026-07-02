"""Case 1 — SRE incident agent (triage → RCA → rollback) on AgentCore Runtime.

Tools simulated in-memory (no EKS/IAM). Model: OpenRouter. See README.md.
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

# Stateful within a session (one microVM per session_id): rollback flips state,
# the review re-measure sees it. A real deploy reads/writes EKS + CloudWatch here.
_STATE = {"image": "hashicorp/http-echo:1.1", "healthy": False}

_ROLLOUT_HISTORY = [
    "rev=1  2026-06-30T14:02Z  image=hashicorp/http-echo:1.0  cause='v2.2 baseline'  (last known good)",
    "rev=2  2026-06-30T14:30Z  image=hashicorp/http-echo:1.1  cause='v2.3 shrink DB pool'  (current)",
]


@tool
def query_5xx_rate(window_min: int = 15) -> str:
    """checkout-api 5xx error rate. Call to diagnose, and AGAIN after a fix to verify."""
    if _STATE["healthy"]:
        return f"5xx over last {window_min}m: 0.1% (nominal, < 0.5% SLO)."
    return (f"5xx over last {window_min}m: 6.2% (BREACHING SLO). "
            "Step-change began ~14:32, right after the 14:30 rollout.")


@tool
def get_rollout_history(service: str = "checkout-api") -> str:
    """Recent deployment revisions: image, timestamp, change-cause."""
    return f"Rollout history for {service}:\n" + "\n".join(_ROLLOUT_HISTORY)


@tool
def rollback_deployment(service: str = "checkout-api",
                        to_image: str = "hashicorp/http-echo:1.0") -> str:
    """Roll a service back to a known-good image. RISKY — affects live traffic."""
    _STATE.update(image=to_image, healthy=True)
    return f"Patched {service} → {to_image}. Re-measure 5xx before declaring resolved."


SYSTEM_PROMPT = (
    "You are an on-call SRE agent for checkout-api. Work the loop: PLAN — read the "
    "5xx rate and rollout history to reason out the cause; EXECUTE — if a bad deploy "
    "is the cause, roll back to the last known-good image; REVIEW — re-measure 5xx "
    "and only report 'resolved' once it is back under SLO. Never claim a fix you did "
    "not verify. Finish with a one-line RCA: cause, action, verified 5xx result."
)


@app.entrypoint
def invoke(payload, context):
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[query_5xx_rate, get_rollout_history, rollback_deployment],
    )
    result = agent(payload.get("prompt", "checkout-api is throwing 5xx, deal with it."))
    return {"response": result.message.get("content", [{}])[0].get("text", str(result))}


if __name__ == "__main__":
    app.run()
