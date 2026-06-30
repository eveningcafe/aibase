"""AgentCore Runtime + Memory — a Strands SRE runbook-memory agent.

Same shape as agent.py (the calculator quickstart), but instead of a stateless
tool it carries **persistent memory**: an on-call SRE assistant that *records*
durable operational facts (service owners, known-good images, incident
postmortems, runbook steps) and *retrieves* them by meaning on the next call —
even in a brand-new session / microVM.

Memory backend: **Amazon Bedrock AgentCore Memory** via the Strands
`AgentCoreMemoryToolProvider`. The provider exposes one `agent_core_memory`
tool with actions record / retrieve / list / get / delete. `record` stores a
raw event; AgentCore's long-term-memory strategies extract durable records that
`retrieve` then semantically searches. The toolkit already provisioned a memory
resource for this project (see .bedrock_agentcore.yaml → memory.memory_id).

Auth split (same as the sre-agent lab):
  • LLM   → OpenRouter, a plain API key (Bedrock on-demand Claude can't be
            enabled here — org SCP p-vhwtjx73 denies the Marketplace actions).
  • Memory→ pure IAM. The Runtime execution role is the identity for the
            bedrock-agentcore Memory APIs; locally it uses your AWS creds.

Env (all have lab defaults):
  OPENROUTER_API_KEY            OpenRouter key
  MODEL_ID                      openai/gpt-oss-120b:free
  AWS_REGION                    ap-southeast-1   (Memory lives here)
  BEDROCK_AGENTCORE_MEMORY_ID   quickstart_mem-E1ILI72q9N  (the provisioned resource)
  MEMORY_NAMESPACE              /sre/runbook     (LTM namespace records are read from)
"""
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.openai import OpenAIModel
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider

app = BedrockAgentCoreApp()

# --- LLM: OpenRouter (OpenAI-compatible), exactly as agent.py -----------------
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY  = os.getenv(
    "OPENROUTER_API_KEY",
    "sk-or-REPLACE-ME",   # set via env; do not commit real keys
)
MODEL_ID = os.getenv("MODEL_ID", "openai/gpt-oss-120b:free")

model = OpenAIModel(
    client_args={"api_key": OPENROUTER_API_KEY, "base_url": OPENROUTER_BASE_URL},
    model_id=MODEL_ID,
)

# --- Memory: AgentCore Memory (IAM-authenticated) -----------------------------
REGION    = os.getenv("AWS_REGION", "ap-southeast-1")
MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID", "quickstart_mem-E1ILI72q9N")
# Namespace the LTM strategy writes extracted records into; `retrieve` reads the
# same path. Keep record + retrieve on one namespace or searches come back empty.
NAMESPACE = os.getenv("MEMORY_NAMESPACE", "/sre/runbook")

SYSTEM_PROMPT = (
    "You are an on-call SRE assistant with long-term memory of this team's "
    "operations. Two habits, every turn:\n"
    "1. RETRIEVE first — before answering an operational question (a service's "
    "owner, its known-good image, a past incident, a runbook step), call "
    "agent_core_memory(action='retrieve', query=...) and ground your answer in "
    "what comes back. Say so if memory is empty.\n"
    "2. RECORD durable facts — when the user states something worth keeping "
    "(an owner, a rollback target, a postmortem, a runbook), call "
    "agent_core_memory(action='record', content=...) to save it for future "
    "sessions. Don't record transient chit-chat.\n"
    "Be concise. Cite the remembered fact you used."
)


def _memory_tools(actor_id: str, session_id: str):
    """Build the AgentCore Memory tool for this actor/session.

    actor_id  = whose memories these are (the team / on-call rotation).
    session_id= the conversation thread (groups events of one incident).
    Both scope where records are written and read; reuse them to recall later.
    """
    provider = AgentCoreMemoryToolProvider(
        memory_id=MEMORY_ID,
        actor_id=actor_id,
        session_id=session_id,
        namespace=NAMESPACE,
        region=REGION,
    )
    return provider.tools


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entry point."""
    # Memories belong to an actor and a session. Default to the SRE team rotation
    # and the Runtime's session id so a follow-up invoke recalls the same thread.
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
    # `agentcore launch` runs the server; locally `agentcore launch --local`
    # serves this on :8080. The record→recall demo is driven from the outside
    # with `agentcore invoke` — see README.md.
    app.run()
