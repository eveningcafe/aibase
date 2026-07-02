"""Case 3 — IaC generate → review → policy gate. WORKSHOP SKELETON.

Fill in the TODOs, or copy the reference:  cp example/agent.py agent.py
Boilerplate is done; you write the two tools and the system prompt. The hard
rule to enforce in the prompt: any HIGH finding blocks 'apply'.
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


# --- TODO: implement the two tools -------------------------------------------
@tool
def generate_terraform(request: str, secure: bool = False) -> str:
    """Generate a Terraform snippet for the request. secure=False emits the fast,
    plausible-but-risky version; secure=True applies constraint-first hardening."""
    # TODO: return risky HCL (e.g. SG ingress 0.0.0.0/0 on 22, S3 with no
    #       public-access block) when secure=False; return the hardened version
    #       (restricted CIDR + aws_s3_bucket_public_access_block) when secure=True.
    ...


@tool
def checkov_scan(terraform: str) -> str:
    """Static policy scan. Returns findings by severity. Any HIGH blocks apply."""
    # TODO: inspect the HCL string and report HIGH findings (0.0.0.0/0 ingress,
    #       S3 missing public-access block); return PASSED when there are none.
    ...


# TODO: write the system prompt — drive the loop L1 generate → L2 review →
# L3 checkov_scan. HARD RULE: any HIGH finding → do NOT approve; regenerate with
# secure=True and re-scan. Only report "safe to apply" on a clean (0 HIGH) scan.
SYSTEM_PROMPT = "TODO"


@app.entrypoint
def invoke(payload, context):
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT,
                  tools=[generate_terraform, checkov_scan])
    result = agent(payload.get("prompt", "Write Terraform for an SSH security group and an S3 bucket."))
    return {"response": result.message.get("content", [{}])[0].get("text", str(result))}


if __name__ == "__main__":
    app.run()
