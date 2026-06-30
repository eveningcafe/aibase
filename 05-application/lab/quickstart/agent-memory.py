"""AgentCore Runtime + Memory — a Strands SRE runbook-memory agent.

Same shape as agent.py (the calculator quickstart), but instead of a stateless
tool it carries **persistent memory**: an on-call SRE assistant that *remembers*
durable operational facts (service owners, known-good images, runbook steps)
and *recalls* them by meaning on a later call — even from a brand-new session.

Memory backend: **Amazon Bedrock AgentCore Memory**. The toolkit already
provisioned a memory resource for this project (see .bedrock_agentcore.yaml →
memory.memory_id). Its long-term SemanticFacts strategy extracts facts into the
namespace `/users/{actorId}/facts/`.

Two hard-won facts baked into the tools below (don't "simplify" them away):
  • Facts are extracted ONLY from USER-role events. The off-the-shelf
    `AgentCoreMemoryToolProvider.record` writes ASSISTANT-role events, so
    nothing is ever extracted — we call create_event with role USER instead.
  • `retrieve` must read the SAME namespace the strategy writes to,
    `/users/{actorId}/facts/`. Reading any other path returns empty.

Auth split (same as the sre-agent lab):
  • LLM   → OpenRouter, a plain API key (Bedrock on-demand Claude can't be
            enabled here — org SCP p-vhwtjx73 denies the Marketplace actions).
  • Memory→ pure IAM. The Runtime execution role is the identity for the
            bedrock-agentcore Memory APIs; locally it uses your AWS creds.

Env (all have lab defaults):
  OPENROUTER_API_KEY            OpenRouter key
  MODEL_ID                      google/gemma-4-31b-it:free
  AWS_REGION                    ap-southeast-1   (Memory lives here)
  BEDROCK_AGENTCORE_MEMORY_ID   quickstart_mem-E1ILI72q9N  (the provisioned resource)
"""
import os
from datetime import datetime, timezone

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models.openai import OpenAIModel

app = BedrockAgentCoreApp()

# --- LLM: OpenRouter (OpenAI-compatible), exactly as agent.py -----------------
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY  = os.getenv(
    "OPENROUTER_API_KEY",
    "sk-or-REPLACE-ME",   # set via env; do not commit real keys
)
MODEL_ID = os.getenv("MODEL_ID", "google/gemma-4-31b-it:free")

model = OpenAIModel(
    client_args={"api_key": OPENROUTER_API_KEY, "base_url": OPENROUTER_BASE_URL},
    model_id=MODEL_ID,
)

# --- Memory: AgentCore Memory (IAM-authenticated) -----------------------------
REGION    = os.getenv("AWS_REGION", "ap-southeast-1")
MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID", "quickstart_mem-E1ILI72q9N")

# The provisioned SemanticFacts strategy extracts into this namespace template.
# {actorId} is filled in per-invoke. Verify with:
#   aws bedrock-agentcore-control get-memory --memory-id $MEMORY_ID --region $REGION
FACTS_NAMESPACE = "/users/{actor_id}/facts/"

SYSTEM_PROMPT = (
    "You are an on-call SRE assistant with long-term memory of this team's "
    "operations. Two habits, every turn:\n"
    "1. RECALL first — before answering an operational question (a service's "
    "owner, its known-good image, a runbook step), call recall(query=...) and "
    "ground your answer in what comes back. Say so plainly if memory is empty.\n"
    "2. REMEMBER durable facts — when the user states something worth keeping "
    "(an owner, a rollback target, a runbook), call remember(fact=...) to save "
    "it for future sessions. Don't store transient chit-chat.\n"
    "Be concise. Cite the remembered fact you used."
)


def _memory_tools(actor_id: str, session_id: str):
    """Build remember/recall tools bound to this actor.

    Facts are stored per ACTOR (the team / on-call rotation), so a fact saved in
    one session is recalled from any later session for the same actor_id.
    """
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    namespace = FACTS_NAMESPACE.format(actor_id=actor_id)

    @tool
    def remember(fact: str) -> str:
        """Save a durable operational fact to long-term memory (e.g. a service
        owner, a known-good image, a runbook step). Use for facts worth recalling
        in future sessions, not transient conversation."""
        # role=USER is deliberate: the SemanticFacts strategy extracts facts only
        # from USER-role events. ASSISTANT-role events are never extracted.
        client.create_event(
            memoryId=MEMORY_ID,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=datetime.now(timezone.utc),
            payload=[{"conversational": {"content": {"text": fact}, "role": "USER"}}],
        )
        return f"Saved to team memory: {fact}"

    @tool
    def recall(query: str) -> str:
        """Search long-term memory for facts relevant to the query (semantic
        search). Call this before answering operational questions."""
        resp = client.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace=namespace,
            searchCriteria={"searchQuery": query},
            maxResults=5,
        )
        hits = [r.get("content", {}).get("text", "")
                for r in resp.get("memoryRecordSummaries", [])]
        if not hits:
            return "No relevant facts in team memory yet."
        return "Relevant facts from memory:\n" + "\n".join(f"- {h}" for h in hits)

    return [remember, recall]


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entry point."""
    # Facts are per-actor, so the recall step works across sessions as long as
    # the actor_id is stable. session_id only groups raw events.
    actor_id = payload.get("actor_id", "sre-team")
    session_id = (
        payload.get("session_id")
        or getattr(context, "session_id", None)
        or "default-session"
    )

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=_memory_tools(actor_id, session_id),
    )

    prompt = payload.get("prompt", "What do you remember about our services?")
    result = agent(prompt)

    return {
        "response": result.message.get("content", [{}])[0].get("text", str(result))
    }


if __name__ == "__main__":
    # `agentcore launch --local` serves this on :8080; the record→recall demo is
    # driven from the outside with `agentcore invoke` — see README.md.
    app.run()
