"""AgentCore Runtime quickstart — a Strands calculator agent.

The smallest useful Runtime agent: one tool (calculator), wrapped in the
BedrockAgentCore `@app.entrypoint`, deployable with the bedrock-agentcore
starter toolkit (`agentcore configure / launch / invoke`).

Model: OpenRouter (OpenAI-compatible API). We use OpenRouter instead of Bedrock
because the org SCP `p-vhwtjx73` denies the AWS Marketplace actions Bedrock's new
model-access flow needs, so on-demand Claude can't be enabled in this account.

Env:
  OPENROUTER_API_KEY   OpenRouter key (defaults to the lab key below)
  MODEL_ID             google/gemma-4-31b-it:free
"""
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.openai import OpenAIModel
from strands_tools import calculator

app = BedrockAgentCoreApp()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY  = os.getenv(
    "OPENROUTER_API_KEY",
    "sk-or-REPLACE-ME",   # set via env; do not commit real keys
)
# Backups if the demo fails (all free, reasoning + tool-calling, verified working
# through this agent). Swap with: export MODEL_ID="...". Pick a different provider
# so one upstream outage/rate-limit doesn't take out both:
#   openai/gpt-oss-120b:free                 # OpenAI OSS, different stack
#   nvidia/nemotron-3-super-120b-a12b:free   # strongest, NVIDIA infra, 1M ctx
MODEL_ID = os.getenv("MODEL_ID", "google/gemma-4-31b-it:free")

# OpenRouter speaks the OpenAI chat-completions API; Strands' OpenAIModel just
# needs the base_url + key pointed at it.
model = OpenAIModel(
    client_args={"api_key": OPENROUTER_API_KEY, "base_url": OPENROUTER_BASE_URL},
    model_id=MODEL_ID,
)


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entry point"""
    agent = Agent(
        model=model,
        system_prompt="You are a helpful assistant that can perform calculations. Use the calculate tool for any math problems.",
        tools=[calculator],
    )

    prompt = payload.get("prompt", "Hello!")
    result = agent(prompt)

    return {
        "response": result.message.get("content", [{}])[0].get("text", str(result))
    }


if __name__ == "__main__":
    app.run()
